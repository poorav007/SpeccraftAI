"""Static Python AST parser adapter for Flask applications & Blueprints."""

from __future__ import annotations

import ast
import re
from typing import Dict, List, Optional, Tuple

from speccraft.diagnostics import Diagnostic, DiagnosticCode
from speccraft.models import (
    APIEndpoint,
    ExtractionResult,
    HTTPMethod,
    ParameterLocation,
    ParameterModel,
    ResponseModel,
    SourceFile,
)
from speccraft.parser.base import BaseParser

FLASK_ROUTE_SHORTCUTS = {"get", "post", "put", "patch", "delete"}
FLASK_PARAM_RE = re.compile(r"<(?:([a-zA-Z_][a-zA-Z0-9_]*):)?([a-zA-Z_][a-zA-Z0-9_]*)>")
FLASK_TYPE_MAP = {
    "int": "integer",
    "float": "number",
    "string": "string",
    "path": "string",
    "uuid": "string",
}


def _normalize_flask_path(raw_path: str) -> Tuple[str, List[ParameterModel]]:
    params: List[ParameterModel] = []

    def _replace(match: re.Match[str]) -> str:
        conv, name = match.group(1), match.group(2)
        params.append(
            ParameterModel(
                name=name,
                location=ParameterLocation.PATH,
                required=True,
                param_type=FLASK_TYPE_MAP.get(conv or "string", "string"),
            )
        )
        return f"{{{name}}}"

    normalized = FLASK_PARAM_RE.sub(_replace, raw_path)
    return normalized, params


def _extract_str_constant(node: Optional[ast.AST]) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_methods_list(decorator: ast.Call) -> List[str]:
    for kw in decorator.keywords:
        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
            methods = [
                str(el.value).lower()
                for el in kw.value.elts
                if isinstance(el, ast.Constant) and isinstance(el.value, str)
            ]
            if methods:
                return methods
    return ["get"]


class FlaskParser(BaseParser):
    """Static AST parser for Flask `@app.route`, `@bp.get`, `@bp.post`, etc."""

    def can_parse(self, source_file: SourceFile) -> bool:
        if not source_file.relative_path.endswith(".py"):
            return False
        lower = source_file.content.lower()
        return "flask" in lower or "blueprint" in lower

    def parse_files(self, source_files: List[SourceFile]) -> ExtractionResult:
        endpoints: List[APIEndpoint] = []
        diagnostics: List[Diagnostic] = []
        total_loc = 0

        for sf in source_files:
            if not self.can_parse(sf):
                continue
            total_loc += sf.loc
            try:
                tree = ast.parse(sf.content, filename=sf.relative_path)
            except SyntaxError as err:
                diagnostics.append(
                    Diagnostic.create(
                        code=DiagnosticCode.SC_W008,
                        file=sf.relative_path,
                        line=err.lineno or 1,
                        custom_message=f"Syntax error in {sf.relative_path}: {err.msg}",
                    )
                )
                continue

            bp_prefixes = self._collect_blueprint_prefixes(tree)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for dec in node.decorator_list:
                    if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                        continue
                    attr = dec.func.attr.lower()
                    if attr != "route" and attr not in FLASK_ROUTE_SHORTCUTS:
                        continue

                    raw_path = _extract_str_constant(dec.args[0] if dec.args else None)
                    if not raw_path:
                        continue

                    owner_name = dec.func.value.id if isinstance(dec.func.value, ast.Name) else ""
                    prefix = bp_prefixes.get(owner_name, "")
                    full_raw = f"{prefix.rstrip('/')}/{raw_path.lstrip('/')}" if prefix else raw_path
                    if not full_raw.startswith("/"):
                        full_raw = f"/{full_raw}"

                    norm_path, path_params = _normalize_flask_path(full_raw)
                    methods = _extract_methods_list(dec) if attr == "route" else [attr]
                    doc = ast.get_docstring(node) or ""
                    summary = doc.splitlines()[0].strip() if doc else node.name.replace("_", " ").title()

                    for method_str in methods:
                        if method_str not in {m.value for m in HTTPMethod}:
                            continue
                        endpoints.append(
                            APIEndpoint(
                                path=norm_path,
                                method=HTTPMethod(method_str),
                                operation_id=node.name if len(methods) == 1 else f"{node.name}_{method_str}",
                                summary=summary,
                                description=doc or None,
                                tags=[owner_name] if owner_name and owner_name != "app" else [],
                                parameters=list(path_params),
                                responses={"200": ResponseModel(status_code="200", description="Successful Response")},
                                source_file=sf.relative_path,
                                line_number=node.lineno,
                            )
                        )

        return ExtractionResult(
            endpoints=endpoints,
            schemas={},
            diagnostics=diagnostics,
            files_scanned=len(source_files),
            total_loc=total_loc,
        )

    @staticmethod
    def _collect_blueprint_prefixes(tree: ast.AST) -> Dict[str, str]:
        prefixes: Dict[str, str] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            call = node.value
            fn_name = (
                call.func.id
                if isinstance(call.func, ast.Name)
                else (call.func.attr if isinstance(call.func, ast.Attribute) else "")
            )
            if fn_name != "Blueprint":
                continue
            for kw in call.keywords:
                if kw.arg == "url_prefix":
                    prefix = _extract_str_constant(kw.value)
                    if prefix:
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                prefixes[target.id] = prefix
        return prefixes

