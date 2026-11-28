"""Static route scanner for Node.js Express.js / TypeScript files (zero code execution)."""

from __future__ import annotations

import posixpath
import re
from typing import Dict, List, Optional, Set, Tuple

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
    r"""\b([a-zA-Z_$][a-zA-Z0-9_$]*)\.use\(\s*['"`]([^'"`]+)['"`]\s*,\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\)"""
)
_REQUIRE_RE = re.compile(
    r"""\b(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*require\(\s*['"`](\.[^'"`]+)['"`]\s*\)"""
)
_ESM_IMPORT_RE = re.compile(
    r"""\bimport\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s+from\s+['"`](\.[^'"`]+)['"`]"""
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


def _resolve_relative_js_file(
    from_file: str,
    rel_import: str,
    known_files: Set[str],
) -> Optional[str]:
    """Resolve relative JS/TS import (`./routes/users`) to scanned relative_path."""
    base_dir = posixpath.dirname(from_file.replace("\\", "/"))
    joined = posixpath.normpath(posixpath.join(base_dir, rel_import))
    candidates = [
        joined,
        f"{joined}.js",
        f"{joined}.mjs",
        f"{joined}.ts",
        posixpath.join(joined, "index.js"),
        posixpath.join(joined, "index.ts"),
    ]
    for cand in candidates:
        if cand in known_files:
            return cand
    return None


class ExpressParser(BaseParser):
    """Pure static multi-file parser for Express.js (`app.get`, `router.post`, nested `use`)."""

    def can_parse(self, source_file: SourceFile) -> bool:
        return source_file.relative_path.lower().endswith((".js", ".mjs", ".ts"))

    def parse_files(self, source_files: List[SourceFile]) -> ExtractionResult:
        js_files = [sf for sf in source_files if self.can_parse(sf)]
        known_paths = {sf.relative_path.replace("\\", "/") for sf in js_files}
        total_loc = sum(sf.loc for sf in js_files)

        # Resolve per-file imports and cross-file router.use('/prefix', childRouter) graph
        file_imports: Dict[str, Dict[str, str]] = {}
        parent_edges: Dict[Tuple[str, str], Tuple[str, str, str]] = {}
        file_level_mounts: Dict[str, Tuple[str, str, str]] = {}

        for sf in js_files:
            rel = sf.relative_path.replace("\\", "/")
            imports_map: Dict[str, str] = {}
            for regex in (_REQUIRE_RE, _ESM_IMPORT_RE):
                for m in regex.finditer(sf.content):
                    resolved = _resolve_relative_js_file(rel, m.group(2), known_paths)
                    if resolved:
                        imports_map[m.group(1)] = resolved
            file_imports[rel] = imports_map

        for sf in js_files:
            rel = sf.relative_path.replace("\\", "/")
            imports_map = file_imports.get(rel, {})
            for match in _USE_PREFIX_RE.finditer(sf.content):
                parent_var, prefix, child_var = match.group(1), match.group(2), match.group(3)
                if child_var in imports_map:
                    target_file = imports_map[child_var]
                    file_level_mounts[target_file] = (rel, parent_var, prefix)
                else:
                    parent_edges[(rel, child_var)] = (rel, parent_var, prefix)

        def _composed_prefix(file_rel: str, var_name: str, seen: Set[Tuple[str, str]]) -> str:
            key = (file_rel, var_name)
            if key in seen:
                return ""
            next_seen = seen | {key}

            if key in parent_edges:
                p_file, p_var, mount_pref = parent_edges[key]
                return f"{_composed_prefix(p_file, p_var, next_seen).rstrip('/')}/{mount_pref.lstrip('/')}"
            if file_rel in file_level_mounts:
                p_file, p_var, mount_pref = file_level_mounts[file_rel]
                return f"{_composed_prefix(p_file, p_var, next_seen).rstrip('/')}/{mount_pref.lstrip('/')}"
            return ""

        endpoints: List[APIEndpoint] = []
        for sf in js_files:
            rel = sf.relative_path.replace("\\", "/")
            lines = sf.content.splitlines()

            for line_idx, line in enumerate(lines):
                for match in _ROUTE_CALL_RE.finditer(line):
                    owner_var = match.group(1)
                    method_str = match.group(2).lower()
                    raw_path = match.group(3)

                    prefix = _composed_prefix(rel, owner_var, set())
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
                            tags=[owner_var] if owner_var not in {"app", "server", "router"} else [],
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
            files_scanned=len(js_files),
            total_loc=total_loc,
        )
