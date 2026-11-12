"""FastAPI static AST parser adapter for SpecCraft AI.

Statically analyzes FastAPI source code, route decorators, router prefixes,
function parameters, docstrings, and response models without executing any code.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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

    def parse_files(self, source_files: List[SourceFile]) -> ExtractionResult:
        """Parse multiple Python source files and aggregate extracted endpoints and schemas.

        Args:
            source_files: Ingested source files to analyze.

        Returns:
            ExtractionResult containing endpoints, schemas, warnings, and metrics.
        """
        all_endpoints: List[APIEndpoint] = []
        all_warnings: List[ExtractionWarning] = []
        total_loc = sum(sf.loc for sf in source_files)

        with Timer() as timer:
            # First pass: Parse ASTs and extract Pydantic schemas across all files
            parsed_trees: List[Tuple[SourceFile, ast.AST]] = []
            for sf in source_files:
                try:
                    tree = ast.parse(sf.content, filename=sf.relative_path)
                    parsed_trees.append((sf, tree))
                    self.schema_extractor.extract_from_ast(tree)
                except SyntaxError as syn_err:
                    all_warnings.append(
                        ExtractionWarning(
                            file=sf.relative_path,
                            line=syn_err.lineno,
                            code="SYNTAX_ERROR",
                            message=f"Failed to parse AST: {syn_err.msg}",
                        )
                    )

            # Second pass: Extract router prefixes and route handlers
            for sf, tree in parsed_trees:
                endpoints, warnings = self._parse_single_tree(tree, sf)
                all_endpoints.extend(endpoints)
                all_warnings.extend(warnings)

        return ExtractionResult(
            endpoints=all_endpoints,
            schemas=self.schema_extractor.schemas,
            warnings=all_warnings,
            files_scanned=len(source_files),
            total_loc=total_loc,
            parse_duration_ms=timer.duration_ms,
        )

    def _parse_single_tree(
        self,
        tree: ast.AST,
        source_file: SourceFile,
    ) -> Tuple[List[APIEndpoint], List[ExtractionWarning]]:
        """Extract routes and router prefixes from a single file's AST."""
        endpoints: List[APIEndpoint] = []
        warnings: List[ExtractionWarning] = []

        # Find APIRouter prefix definitions, e.g. router = APIRouter(prefix="/items", tags=["items"])
        router_prefixes, router_tags = self._extract_router_metadata(tree)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                route_data_list = self._extract_route_decorators(node, router_prefixes, router_tags)
                for route_info in route_data_list:
                    endpoint = self._build_endpoint(node, route_info, source_file)
                    endpoints.append(endpoint)

        return endpoints, warnings

    def _extract_router_metadata(self, tree: ast.AST) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """Detect APIRouter declarations and extract prefix and default tags."""
        router_prefixes: Dict[str, str] = {}
        router_tags: Dict[str, List[str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    call_name = ""
                    if isinstance(node.value.func, ast.Name):
                        call_name = node.value.func.id
                    elif isinstance(node.value.func, ast.Attribute):
                        call_name = node.value.func.attr

                    if call_name == "APIRouter":
                        # Check target variable name
                        var_name = ""
                        if node.targets and isinstance(node.targets[0], ast.Name):
                            var_name = node.targets[0].id

                        if var_name:
                            prefix = ""
                            tags: List[str] = []
                            for kw in node.value.keywords:
                                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                    prefix = str(kw.value.value)
                                elif kw.arg == "tags" and isinstance(kw.value, ast.List):
                                    tags = [str(_ast_to_literal(elt)) for elt in kw.value.elts if _ast_to_literal(elt)]

                            router_prefixes[var_name] = prefix
                            router_tags[var_name] = tags

        return router_prefixes, router_tags

    def _extract_route_decorators(
        self,
        func_node: ast.AST,
        router_prefixes: Dict[str, str],
        router_tags: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        """Identify if a function is decorated with FastAPI route decorators."""
        routes: List[Dict[str, Any]] = []

        for decorator in func_node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue

            # Must be an attribute call like app.get or router.post
            if not isinstance(decorator.func, ast.Attribute):
                continue

            method_name = decorator.func.attr.lower()
            if method_name not in HTTP_METHODS:
                continue

            # Extract caller object name (e.g. 'app', 'router', 'api_router')
            caller_name = ""
            if isinstance(decorator.func.value, ast.Name):
                caller_name = decorator.func.value.id

            base_prefix = router_prefixes.get(caller_name, "")
            default_tags = router_tags.get(caller_name, [])

            # Extract path from first argument or keyword 'path'
            path = ""
            if decorator.args:
                lit = _ast_to_literal(decorator.args[0])
                if lit is not None:
                    path = str(lit)
            else:
                for kw in decorator.keywords:
                    if kw.arg == "path":
                        lit = _ast_to_literal(kw.value)
                        if lit is not None:
                            path = str(lit)

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
                        # Handle status.HTTP_201_CREATED -> extract trailing digits
                        match = re.search(r"\d{3}", kw.value.attr)
                        if match:
                            status_code = match.group(0)
                elif kw.arg == "deprecated" and isinstance(kw.value, ast.Constant):
                    deprecated = bool(kw.value.value)

            routes.append({
                "method": HTTPMethod(method_name),
                "path": full_path,
                "summary": summary,
                "description": description,
                "tags": list(dict.fromkeys(tags)),  # deduplicate preserving order
                "response_model": response_model,
                "status_code": status_code,
                "deprecated": deprecated,
            })

        return routes

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
    ) -> APIEndpoint:
        """Construct a complete APIEndpoint model from AST inspection."""
        path = route_info["path"]
        path_tokens = _extract_path_tokens(path)
        docstring = ast.get_docstring(func_node)

        # Summary fallback to docstring first line, then function name
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

        # Extract parameters and request body from function signature
        parameters, request_body = self._parse_function_parameters(func_node, path_tokens)

        # Build responses map
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

        return APIEndpoint(
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

    def _parse_function_parameters(
        self,
        func_node: ast.AST,
        path_tokens: Set[str],
    ) -> Tuple[List[ParameterModel], Optional[RequestBodyModel]]:
        """Categorize function arguments into path params, query params, or request bodies."""
        parameters: List[ParameterModel] = []
        request_body: Optional[RequestBodyModel] = None

        args = func_node.args.args
        # Map default values to arguments from the right
        defaults = func_node.args.defaults
        num_args = len(args)
        num_defaults = len(defaults)
        default_offset = num_args - num_defaults

        for idx, arg in enumerate(args):
            arg_name = arg.arg
            if arg_name in ("self", "cls"):
                continue

            default_node = defaults[idx - default_offset] if idx >= default_offset else None
            type_name = self._extract_type_name(arg.annotation) or "str"

            # Check if injected dependency (Depends, Request, Session, etc.)
            if self._is_dependency(type_name, default_node):
                continue

            # Check if parameter is a request body (Pydantic model or explicit Body)
            if self._is_request_body(type_name, default_node):
                schema_name = type_name.split("[")[-1].rstrip("]")
                schema_ref = f"#/components/schemas/{schema_name}" if schema_name in self.schema_extractor.known_model_names else None
                request_body = RequestBodyModel(
                    schema_name=schema_name,
                    schema_ref=schema_ref,
                    required=default_node is None,
                )
                continue

            # Classify path parameter vs query parameter vs header
            location = ParameterLocation.QUERY
            is_required = default_node is None
            if arg_name in path_tokens:
                location = ParameterLocation.PATH
                is_required = True

            default_val = _ast_to_literal(default_node) if default_node else None

            # Map Python type to OpenAPI primitive
            clean_type = PYTHON_TYPE_MAP.get(type_name, "string")

            param = ParameterModel(
                name=arg_name,
                location=location,
                required=is_required,
                param_type=clean_type,
                default=default_val,
            )
            parameters.append(param)

        return parameters, request_body

    def _is_dependency(self, type_name: str, default_node: Optional[ast.AST]) -> bool:
        """Check if an argument represents an injected FastAPI dependency."""
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
        """Check if argument represents a Pydantic model payload or explicit Body()."""
        # Explicit Body(...)
        if default_node and isinstance(default_node, ast.Call):
            call_name = ""
            if isinstance(default_node.func, ast.Name):
                call_name = default_node.func.id
            elif isinstance(default_node.func, ast.Attribute):
                call_name = default_node.func.attr
            if call_name == "Body":
                return True

        # Recognized Pydantic model name in AST
        clean_name = type_name.split("[")[-1].rstrip("]")
        if clean_name in self.schema_extractor.known_model_names:
            return True

        # Common naming heuristic for request body schemas (e.g. ItemCreate, UserPayload, OrderRequest)
        if clean_name.endswith(("Create", "Update", "Request", "Payload", "In", "Schema")):
            return True

        return False
