"""Static route scanner for Node.js Express.js / TypeScript files (zero code execution)."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

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

_USE_PREFIX_RE = re.compile(
    r"""\b\w+\.use\(\s*['"`]([^'"`]+)['"`]\s*,\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\)"""
)
_ROUTE_CALL_RE = re.compile(
    r"""([a-zA-Z_$][a-zA-Z0-9_$]*)\.(get|post|put|patch|delete)\(\s*['"`]([^'"`]+)['"`]""",
    re.IGNORECASE,
)
_EXPRESS_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


def _normalize_express_path(raw_path: str) -> Tuple[str, List[ParameterModel]]:
    params: List[ParameterModel] = []

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        params.append(
            ParameterModel(
                name=name,
                location=ParameterLocation.PATH,
                required=True,
                param_type="string",
            )
        )
        return f"{{{name}}}"

    return _EXPRESS_PARAM_RE.sub(_replace, raw_path), params


def _extract_preceding_comment(lines: List[str], zero_based_line: int) -> str:
    """Extract a crisp summary from // or /** ... */ immediately above a route."""
    idx = zero_based_line - 1
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx < 0:
        return ""
    line = lines[idx].strip()
    if line.startswith("//"):
        return line.lstrip("/").strip()
    if line.endswith("*/"):
        collected: List[str] = []
        while idx >= 0:
            cur = lines[idx].strip()
            cleaned = cur.strip("/*").strip()
            if cleaned and not cleaned.startswith("@"):
                collected.append(cleaned)
            if "/*" in cur:
                break
            idx -= 1
        return " ".join(reversed(collected)).strip()
    return ""


class ExpressParser(BaseParser):
    """Pure static parser for Express.js (`app.get`, `router.post`, `app.use`)."""

    def can_parse(self, source_file: SourceFile) -> bool:
        return source_file.relative_path.lower().endswith((".js", ".mjs", ".ts"))

    def parse_files(self, source_files: List[SourceFile]) -> ExtractionResult:
        endpoints: List[APIEndpoint] = []
        total_loc = 0

        # Collect router mount prefixes across scanned JS/TS files
        mount_prefixes: Dict[str, str] = {}
        for sf in source_files:
            if not self.can_parse(sf):
                continue
            for match in _USE_PREFIX_RE.finditer(sf.content):
                prefix, router_var = match.group(1), match.group(2)
                mount_prefixes[router_var] = prefix

        for sf in source_files:
            if not self.can_parse(sf):
                continue
            total_loc += sf.loc
            lines = sf.content.splitlines()

            for line_idx, line in enumerate(lines):
                for match in _ROUTE_CALL_RE.finditer(line):
                    owner_var = match.group(1)
                    method_str = match.group(2).lower()
                    raw_path = match.group(3)

                    prefix = mount_prefixes.get(owner_var, "")
                    full_raw = f"{prefix.rstrip('/')}/{raw_path.lstrip('/')}" if prefix else raw_path
                    if not full_raw.startswith("/"):
                        full_raw = f"/{full_raw}"

                    norm_path, path_params = _normalize_express_path(full_raw)
                    comment_summary = _extract_preceding_comment(lines, line_idx)
                    op_id = re.sub(
                        r"[^a-zA-Z0-9]+", "_", f"{method_str}_{norm_path}"
                    ).strip("_").lower()

                    endpoints.append(
                        APIEndpoint(
                            path=norm_path,
                            method=HTTPMethod(method_str),
                            operation_id=op_id,
                            summary=comment_summary or f"{method_str.upper()} {norm_path}",
                            description=comment_summary or None,
                            tags=[owner_var] if owner_var not in {"app", "server"} else [],
                            parameters=path_params,
                            responses={"200": ResponseModel(status_code="200", description="Successful Response")},
                            source_file=sf.relative_path,
                            line_number=line_idx + 1,
                        )
                    )

        return ExtractionResult(
            endpoints=endpoints,
            schemas={},
            diagnostics=[],
            files_scanned=len(source_files),
            total_loc=total_loc,
        )

