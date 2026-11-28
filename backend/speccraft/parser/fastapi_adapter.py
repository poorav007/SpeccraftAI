"""FastAPI static AST parser adapter for SpecCraft AI.

Statically analyzes FastAPI source code, route decorators, router prefixes,
function parameters, docstrings, response models, and diagnostics without executing code.
"""

from __future__ import annotations

import ast
import re
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from speccraft.diagnostics import Diagnostic, DiagnosticCode
from speccraft.models import (
    APIEndpoint,
    ExtractionResult,
    ExtractionWarning,
    HTTPMethod,
    ParameterLocation,
    ParameterModel,
    RequestBodyModel,
    ResponseModel,
    SourceFile,
)
from speccraft.parser.base import BaseParser
from speccraft.schema_builder import PYTHON_TYPE_MAP, PydanticSchemaExtractor, _ast_to_literal
from speccraft.utils.timing import Timer

# Recognized FastAPI HTTP decorator names
HTTP_METHODS: Set[str] = {"get", "post", "put", "delete", "patch", "options", "head"}

# Injected framework parameter types that should not be treated as user parameters
FRAMEWORK_TYPES: Set[str] = {
    "Request",
    "Response",
    "BackgroundTasks",
    "WebSocket",
    "Session",
    "AsyncSession",
    "DBSession",
}


def _extract_path_tokens(path: str) -> Set[str]:
    """Extract variable names enclosed in curly braces from a URL template."""
    return set(re.findall(r"\{([a-zA-Z0-9_]+)\}", path))


def _clean_path(path: str) -> str:
    """Normalize route path to have leading slash, no redundant slashes, and trim trailing slash."""
    if not path.startswith("/"):
        path = "/" + path
    cleaned = re.sub(r"/+", "/", path)
    if len(cleaned) > 1 and cleaned.endswith("/"):
        cleaned = cleaned.rstrip("/")
    return cleaned


class FastAPIParser(BaseParser):
    """AST parser for FastAPI projects and files."""

    def __init__(self) -> None:
        self.schema_extractor = PydanticSchemaExtractor()

    def can_parse(self, source_file: SourceFile) -> bool:
        """Check if source file is a Python file that can be parsed by this adapter."""
        return source_file.relative_path.endswith(".py")

    @staticmethod
    def _scan_module_statements(tree: ast.AST, mod_name: str, is_init: bool) -> Dict[str, Any]:
        """Scan module statement blocks once for imports, routers, mounts, diagnostics, and handlers."""
        router_prefixes: Dict[str, str] = {}
        router_tags: Dict[str, List[str]] = {}
        imports_map: Dict[str, Tuple[str, Optional[str]]] = {}
        include_calls: List[ast.Call] = []
        unsupported_calls: List[ast.Call] = []
        function_nodes: List[ast.AST] = []

        pkg_parts = mod_name.split(".") if is_init else mod_name.split(".")[:-1]
        stack: List[ast.stmt] = list(reversed(getattr(tree, "body", [])))

        while stack:
            stmt = stack.pop()
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_nodes.append(stmt)
                if stmt.body:
                    stack.extend(reversed(stmt.body))
            elif isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    local_name = alias.asname or alias.name.split(".")[-1]
                    imports_map[local_name] = (alias.name, None)
            elif isinstance(stmt, ast.ImportFrom):
                base_mod = stmt.module or ""
                if stmt.level > 0:
                    keep_count = max(0, len(pkg_parts) - (stmt.level - 1))
                    prefix_mod = ".".join(pkg_parts[:keep_count])
                    full_mod = f"{prefix_mod}.{base_mod}".strip(".") if base_mod else prefix_mod
                else:
                    full_mod = base_mod
                for alias in stmt.names:
                    local_name = alias.asname or alias.name
                    imports_map[local_name] = (full_mod, alias.name)
            elif isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                call_name = ""
                if isinstance(call.func, ast.Name):
                    call_name = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    call_name = call.func.attr
                    if call_name in ("add_api_route", "mount"):
                        unsupported_calls.append(call)
                if call_name in ("APIRouter", "Router") and stmt.targets and isinstance(stmt.targets[0], ast.Name):
                    var_name = stmt.targets[0].id
                    prefix = ""
                    tags: List[str] = []
                    for kw in call.keywords:
                        if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                            prefix = str(kw.value.value)
                        elif kw.arg == "tags" and isinstance(kw.value, ast.List):
                            tags = [str(_ast_to_literal(elt)) for elt in kw.value.elts if _ast_to_literal(elt)]
                    router_prefixes[var_name] = prefix
                    router_tags[var_name] = tags
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Attribute):
                    attr_name = call.func.attr
                    if attr_name == "include_router":
                        include_calls.append(call)
                    elif attr_name in ("add_api_route", "mount"):
                        unsupported_calls.append(call)
            elif isinstance(stmt, (ast.ClassDef, ast.With, ast.AsyncWith, ast.For, ast.AsyncFor, ast.While)):
                if stmt.body:
                    stack.extend(reversed(stmt.body))
            elif isinstance(stmt, ast.If):
                if stmt.orelse:
                    stack.extend(reversed(stmt.orelse))
                if stmt.body:
                    stack.extend(reversed(stmt.body))
            elif isinstance(stmt, ast.Try) or (hasattr(ast, "TryStar") and isinstance(stmt, ast.TryStar)):
                if stmt.finalbody:
                    stack.extend(reversed(stmt.finalbody))
                if stmt.orelse:
                    stack.extend(reversed(stmt.orelse))
                for handler in reversed(stmt.handlers):
                    if handler.body:
                        stack.extend(reversed(handler.body))
                if stmt.body:
                    stack.extend(reversed(stmt.body))

        return {
            "router_prefixes": router_prefixes,
            "router_tags": router_tags,
            "imports_map": imports_map,
            "include_calls": include_calls,
            "unsupported_calls": unsupported_calls,
            "function_nodes": function_nodes,
        }

    def parse_files(self, source_files: List[SourceFile]) -> ExtractionResult:
        """Parse multiple Python source files and aggregate extracted endpoints, schemas, and diagnostics."""
        all_endpoints: List[APIEndpoint] = []
        all_diagnostics: List[Diagnostic] = []
        all_warnings: List[ExtractionWarning] = []
        total_loc = sum(sf.loc for sf in source_files)

        with Timer() as timer:
            # First pass: Parse ASTs, collect schemas, and scan statements once per file
            parsed_entries: List[Tuple[SourceFile, ast.AST, Dict[str, Any]]] = []
            for sf in source_files:
                try:
                    tree = ast.parse(sf.content, filename=sf.relative_path)
                    mod_name = self._file_to_module(sf.relative_path)
                    scan = self._scan_module_statements(
                        tree, mod_name, is_init=sf.relative_path.endswith("__init__.py")
                    )
                    parsed_entries.append((sf, tree, scan))
                    self.schema_extractor.extract_from_ast(tree, finalize=False)
                except SyntaxError as syn_err:
                    diag = Diagnostic.create(
                        code=DiagnosticCode.SC_W008,
                        file=sf.relative_path,
                        line=syn_err.lineno,
                        custom_message=f"File failed to parse: {syn_err.msg}",
                    )
                    all_diagnostics.append(diag)

            self.schema_extractor.finalize_schemas()

            # Second pass: Resolve cross-file nested include_router prefixes & tags
            mounted_prefixes, mounted_tags = self._resolve_cross_file_mounts(parsed_entries)

            # Third pass: Extract routes using composed cross-file router prefixes
            for sf, tree, scan in parsed_entries:
                endpoints, diags = self._parse_single_tree(
                    tree,
                    sf,
                    mounted_prefixes=mounted_prefixes.get(sf.relative_path),
                    mounted_tags=mounted_tags.get(sf.relative_path),
                    scan=scan,
                )
                all_endpoints.extend(endpoints)
                all_diagnostics.extend(diags)

        # Sync warnings for backward compatibility
        for d in all_diagnostics:
            all_warnings.append(
                ExtractionWarning(
                    file=d.file,
                    line=d.line,
                    code=d.code.value,
                    message=d.message,
                )
            )

        return ExtractionResult(
            endpoints=all_endpoints,
            schemas=self.schema_extractor.schemas,
            warnings=all_warnings,
            diagnostics=all_diagnostics,
            files_scanned=len(source_files),
            total_loc=total_loc,
            parse_duration_ms=timer.duration_ms,
        )

    @staticmethod
    def _file_to_module(rel_path: str) -> str:
        """Convert POSIX relative file path into a Python dotted module name."""
        pure = PurePosixPath(rel_path.replace("\\", "/"))
        parts = list(pure.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def _resolve_cross_file_mounts(
        self,
        parsed_entries: List[Tuple[SourceFile, ast.AST, Dict[str, Any]]],
    ) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, List[str]]]]:
        """Resolve multi-level cross-file FastAPI include_router() prefix & tag chains."""
        module_to_file: Dict[str, str] = {}
        local_prefixes: Dict[Tuple[str, str], str] = {}
        local_tags: Dict[Tuple[str, str], List[str]] = {}
        file_imports: Dict[str, Dict[str, Tuple[str, Optional[str]]]] = {}

        for sf, _tree, scan in parsed_entries:
            rel = sf.relative_path
            mod = self._file_to_module(rel)
            if mod:
                module_to_file[mod] = rel
            for var_name, pref in scan["router_prefixes"].items():
                local_prefixes[(rel, var_name)] = pref
            for var_name, tgs in scan["router_tags"].items():
                local_tags[(rel, var_name)] = tgs
            file_imports[rel] = scan["imports_map"]

        def _find_file_by_module(mod_name: str) -> Optional[str]:
            if not mod_name:
                return None
            if mod_name in module_to_file:
                return module_to_file[mod_name]
            # Suffix match handles sub-root layouts (e.g. `src/app/routers/items.py` vs `routers.items`)
            for candidate_mod, rel in module_to_file.items():
                if candidate_mod.endswith(f".{mod_name}"):
                    return rel
            return None

        # parent_edge[(child_rel, child_var)] = (parent_rel, parent_var, mount_prefix, mount_tags)
        parent_edges: Dict[Tuple[str, str], Tuple[str, str, str, List[str]]] = {}

        for sf, _tree, scan in parsed_entries:
            rel = sf.relative_path
            imports_map = file_imports.get(rel, {})
            for node in scan["include_calls"]:
                if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name) or not node.args:
                    continue
                parent_var = node.func.value.id
                child_arg = node.args[0]
                target_key: Optional[Tuple[str, str]] = None

                if isinstance(child_arg, ast.Name):
                    cname = child_arg.id
                    if (rel, cname) in local_prefixes:
                        target_key = (rel, cname)
                    elif cname in imports_map:
                        mod_name, sym = imports_map[cname]
                        target_file = _find_file_by_module(mod_name)
                        if target_file and sym:
                            target_key = (target_file, sym)
                        elif sym:
                            # Package re-export (e.g. from .items import router)
                            nested_file = _find_file_by_module(f"{mod_name}.{sym}")
                            if nested_file:
                                target_key = (nested_file, "router")
                elif isinstance(child_arg, ast.Attribute) and isinstance(child_arg.value, ast.Name):
                    mod_alias = child_arg.value.id
                    attr_var = child_arg.attr
                    if mod_alias in imports_map:
                        mod_name, sym = imports_map[mod_alias]
                        target_file = _find_file_by_module(mod_name)
                        if target_file is None and sym:
                            target_file = _find_file_by_module(f"{mod_name}.{sym}")
                        if target_file:
                            target_key = (target_file, attr_var)

                if target_key is None:
                    continue

                mount_prefix = ""
                mount_tags: List[str] = []
                for kw in node.keywords:
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                        mount_prefix = str(kw.value.value)
                    elif kw.arg == "tags" and isinstance(kw.value, ast.List):
                        mount_tags = [
                            str(_ast_to_literal(elt))
                            for elt in kw.value.elts
                            if _ast_to_literal(elt)
                        ]
                parent_edges[target_key] = (rel, parent_var, mount_prefix, mount_tags)

        resolved_prefixes: Dict[str, Dict[str, str]] = {}
        resolved_tags: Dict[str, Dict[str, List[str]]] = {}

        def _compute(key: Tuple[str, str], seen: Set[Tuple[str, str]]) -> Tuple[str, List[str]]:
            own_pref = local_prefixes.get(key, "")
            own_tags = list(local_tags.get(key, []))
            if key in seen or key not in parent_edges:
                return own_pref, own_tags
            p_rel, p_var, mount_pref, mount_tgs = parent_edges[key]
            parent_pref, parent_tgs = _compute((p_rel, p_var), seen | {key})
            full_pref = _clean_path(f"{parent_pref}/{mount_pref}/{own_pref}") if (
                parent_pref or mount_pref or own_pref
            ) else ""
            combined_tags = list(dict.fromkeys([*parent_tgs, *mount_tgs, *own_tags]))
            return full_pref, combined_tags

        for key in set(local_prefixes.keys()) | set(parent_edges.keys()):
            pref, tgs = _compute(key, set())
            rel, var_name = key
            resolved_prefixes.setdefault(rel, {})[var_name] = pref
            resolved_tags.setdefault(rel, {})[var_name] = tgs

        return resolved_prefixes, resolved_tags

    def _parse_single_tree(
        self,
        tree: ast.AST,
        source_file: SourceFile,
        mounted_prefixes: Optional[Dict[str, str]] = None,
        mounted_tags: Optional[Dict[str, List[str]]] = None,
        scan: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[APIEndpoint], List[Diagnostic]]:
        """Extract routes, unsupported registrations, and diagnostics from a single file's AST."""
        endpoints: List[APIEndpoint] = []
        diagnostics: List[Diagnostic] = []

        if scan is None:
            scan = self._scan_module_statements(
                tree,
                self._file_to_module(source_file.relative_path),
                is_init=source_file.relative_path.endswith("__init__.py"),
            )

        router_prefixes: Dict[str, str] = dict(scan["router_prefixes"])
        router_tags: Dict[str, List[str]] = dict(scan["router_tags"])
        function_nodes: List[ast.AST] = scan["function_nodes"]

        for call in scan["unsupported_calls"]:
            if isinstance(call.func, ast.Attribute):
                diagnostics.append(
                    Diagnostic.create(
                        code=DiagnosticCode.SC_W003,
                        file=source_file.relative_path,
                        line=getattr(call, "lineno", None),
                        custom_message=f"Unsupported route registration '{call.func.attr}()' skipped.",
                    )
                )

        if mounted_prefixes:
            router_prefixes.update(mounted_prefixes)
        if mounted_tags:
            router_tags.update(mounted_tags)

        # Extract routes from function definitions
        for func_node in function_nodes:
            route_data_list, route_diags = self._extract_route_decorators(
                func_node, router_prefixes, router_tags, source_file
            )
            diagnostics.extend(route_diags)

            for route_info in route_data_list:
                endpoint, param_diags = self._build_endpoint(func_node, route_info, source_file)
                endpoints.append(endpoint)
                diagnostics.extend(param_diags)

        return endpoints, diagnostics

    def _extract_router_metadata(self, tree: ast.AST) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """Detect APIRouter declarations and extract prefix and default tags."""
        scan = self._scan_module_statements(tree, "", is_init=False)
        return scan["router_prefixes"], scan["router_tags"]

    def _extract_route_decorators(
        self,
        func_node: ast.AST,
        router_prefixes: Dict[str, str],
        router_tags: Dict[str, List[str]],
        source_file: SourceFile,
    ) -> Tuple[List[Dict[str, Any]], List[Diagnostic]]:
        """Identify if a function is decorated with FastAPI route decorators."""
        routes: List[Dict[str, Any]] = []
        diagnostics: List[Diagnostic] = []

        for decorator in func_node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue

            method_name = decorator.func.attr.lower()
            if method_name not in HTTP_METHODS:
                continue

            caller_name = ""
            if isinstance(decorator.func.value, ast.Name):
                caller_name = decorator.func.value.id

            base_prefix = router_prefixes.get(caller_name, "")
            default_tags = router_tags.get(caller_name, [])

            # Extract raw path node
            raw_path_node = decorator.args[0] if decorator.args else None
            if raw_path_node is None:
                for kw in decorator.keywords:
                    if kw.arg == "path":
                        raw_path_node = kw.value
                        break

            # Check if path is non-literal (f-string, variable) -> SC-W001
            path = None
            if raw_path_node is not None:
                lit = _ast_to_literal(raw_path_node)
                if lit is not None and isinstance(lit, str):
                    path = lit
                else:
                    diagnostics.append(
                        Diagnostic.create(
                            code=DiagnosticCode.SC_W001,
                            file=source_file.relative_path,
                            line=getattr(decorator, "lineno", func_node.lineno),
                            custom_message=f"Non-literal route path expression in function '{func_node.name}'; route skipped.",
                        )
                    )
                    continue

            if path is None:
                continue

            full_path = _clean_path(f"{base_prefix}/{path}")

            # Extract decorator keywords
            summary = None
            description = None
            tags = list(default_tags)
            response_model = None
            status_code = "200" if method_name != "post" else "201"
            deprecated = False

            for kw in decorator.keywords:
                if kw.arg == "summary":
                    summary = _ast_to_literal(kw.value)
                elif kw.arg == "description":
                    description = _ast_to_literal(kw.value)
                elif kw.arg == "tags" and isinstance(kw.value, ast.List):
                    extracted_tags = [_ast_to_literal(elt) for elt in kw.value.elts]
                    tags.extend([str(t) for t in extracted_tags if t])
                elif kw.arg == "response_model":
                    response_model = self._extract_type_name(kw.value)
                elif kw.arg == "status_code":
                    sc = _ast_to_literal(kw.value)
                    if sc is not None:
                        status_code = str(sc)
                    elif isinstance(kw.value, ast.Attribute):
                        match = re.search(r"\d{3}", kw.value.attr)
                        if match:
                            status_code = match.group(0)
                elif kw.arg == "deprecated" and isinstance(kw.value, ast.Constant):
                    deprecated = bool(kw.value.value)

            # Check for undeclared response schema (SC-W006)
            if not response_model and getattr(func_node, "returns", None) is None and status_code != "204":
                diagnostics.append(
                    Diagnostic.create(
                        code=DiagnosticCode.SC_W006,
                        file=source_file.relative_path,
                        line=func_node.lineno,
                        custom_message=f"Response schema not declared for route '{full_path}' ({func_node.name}).",
                    )
                )

            routes.append({
                "method": HTTPMethod(method_name),
                "path": full_path,
                "summary": summary,
                "description": description,
                "tags": list(dict.fromkeys(tags)),
                "response_model": response_model,
                "status_code": status_code,
                "deprecated": deprecated,
            })

        return routes, diagnostics

    def _extract_type_name(self, node: Optional[ast.AST]) -> Optional[str]:
        """Extract a readable type or class name from an AST annotation node."""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Subscript):
            base = self._extract_type_name(node.value)
            inner = self._extract_type_name(node.slice)
            return f"{base}[{inner}]"
        return None

    def _build_endpoint(
        self,
        func_node: ast.AST,
        route_info: Dict[str, Any],
        source_file: SourceFile,
    ) -> Tuple[APIEndpoint, List[Diagnostic]]:
        """Construct a complete APIEndpoint model from AST inspection."""
        path = route_info["path"]
        path_tokens = _extract_path_tokens(path)
        docstring = ast.get_docstring(func_node)

        summary = route_info["summary"]
        description = route_info["description"]
        if not summary and docstring:
            lines = [line.strip() for line in docstring.splitlines() if line.strip()]
            if lines:
                summary = lines[0]
                if not description and len(lines) > 1:
                    description = "\n".join(lines[1:])
        if not summary:
            summary = func_node.name.replace("_", " ").title()

        parameters, request_body, param_diags = self._parse_function_parameters(
            func_node, path_tokens, source_file
        )

        responses: Dict[str, ResponseModel] = {}
        status_code = route_info["status_code"]
        resp_model_name = route_info["response_model"]

        resp_schema_ref = f"#/components/schemas/{resp_model_name}" if resp_model_name else None
        responses[status_code] = ResponseModel(
            status_code=status_code,
            description="Successful Response",
            schema_name=resp_model_name,
            schema_ref=resp_schema_ref,
        )

        endpoint = APIEndpoint(
            path=path,
            method=route_info["method"],
            operation_id=func_node.name,
            summary=summary,
            description=description,
            tags=route_info["tags"],
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            deprecated=route_info["deprecated"],
            source_file=source_file.relative_path,
            line_number=func_node.lineno,
        )
        return endpoint, param_diags

    def _parse_function_parameters(
        self,
        func_node: ast.AST,
        path_tokens: Set[str],
        source_file: SourceFile,
    ) -> Tuple[List[ParameterModel], Optional[RequestBodyModel], List[Diagnostic]]:
        """Categorize function arguments into path params, query params, or request bodies."""
        parameters: List[ParameterModel] = []
        request_body: Optional[RequestBodyModel] = None
        diagnostics: List[Diagnostic] = []

        args = func_node.args.args
        defaults = func_node.args.defaults
        num_args = len(args)
        num_defaults = len(defaults)
        default_offset = num_args - num_defaults

        for idx, arg in enumerate(args):
            arg_name = arg.arg
            if arg_name in ("self", "cls"):
                continue

            default_node = defaults[idx - default_offset] if idx >= default_offset else None

            # Check unannotated parameter (SC-W004)
            if arg.annotation is None:
                diagnostics.append(
                    Diagnostic.create(
                        code=DiagnosticCode.SC_W004,
                        file=source_file.relative_path,
                        line=func_node.lineno,
                        custom_message=f"Parameter '{arg_name}' in '{func_node.name}' has no type annotation; assumed string.",
                    )
                )
                type_name = "str"
            else:
                type_name = self._extract_type_name(arg.annotation) or "str"

            # Check if injected dependency (Depends, Request, etc.) -> SC-W005
            if self._is_dependency(type_name, default_node):
                if default_node and isinstance(default_node, ast.Call) and getattr(default_node.func, "id", "") == "Depends":
                    diagnostics.append(
                        Diagnostic.create(
                            code=DiagnosticCode.SC_W005,
                            file=source_file.relative_path,
                            line=func_node.lineno,
                            custom_message=f"Depends(...) detected on '{arg_name}' in '{func_node.name}'; parameters not expanded into OpenAPI.",
                        )
                    )
                continue

            # Check if parameter is a request body (Pydantic model)
            if self._is_request_body(type_name, default_node):
                schema_name = type_name.split("[")[-1].rstrip("]")
                schema_ref = f"#/components/schemas/{schema_name}" if schema_name in self.schema_extractor.known_model_names else None
                request_body = RequestBodyModel(
                    schema_name=schema_name,
                    schema_ref=schema_ref,
                    required=default_node is None,
                )
                continue

            # Classify path vs query parameter
            location = ParameterLocation.QUERY
            is_required = default_node is None
            if arg_name in path_tokens:
                location = ParameterLocation.PATH
                is_required = True

            default_val = _ast_to_literal(default_node) if default_node else None
            clean_type = PYTHON_TYPE_MAP.get(type_name, "string")

            param = ParameterModel(
                name=arg_name,
                location=location,
                required=is_required,
                param_type=clean_type,
                default=default_val,
            )
            parameters.append(param)

        return parameters, request_body, diagnostics

    def _is_dependency(self, type_name: str, default_node: Optional[ast.AST]) -> bool:
        if type_name in FRAMEWORK_TYPES:
            return True
        if default_node and isinstance(default_node, ast.Call):
            call_name = ""
            if isinstance(default_node.func, ast.Name):
                call_name = default_node.func.id
            elif isinstance(default_node.func, ast.Attribute):
                call_name = default_node.func.attr
            if call_name in ("Depends", "Security"):
                return True
        return False

    def _is_request_body(self, type_name: str, default_node: Optional[ast.AST]) -> bool:
        if default_node and isinstance(default_node, ast.Call):
            call_name = ""
            if isinstance(default_node.func, ast.Name):
                call_name = default_node.func.id
            elif isinstance(default_node.func, ast.Attribute):
                call_name = default_node.func.attr
            if call_name == "Body":
                return True

        clean_name = type_name.split("[")[-1].rstrip("]")
        if clean_name in self.schema_extractor.known_model_names:
            return True

        if clean_name.endswith(("Create", "Update", "Request", "Payload", "In", "Schema")):
            return True

        return False
