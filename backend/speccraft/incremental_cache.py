"""Incremental SHA-256 per-file AST cache for large codebases."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from speccraft.diagnostics import Diagnostic
from speccraft.models import APIEndpoint, SourceFile

DEFAULT_CACHE_FILENAME = ".speccraft_cache.json"


def compute_sha256(content: str) -> str:
    """Compute SHA-256 hex digest of source file text."""
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


class IncrementalParseCache:
    """Caches per-file extracted endpoints, schemas, and diagnostics by SHA-256."""

    def __init__(self, cache_path: Optional[Path] = None) -> None:
        self.cache_path = Path(cache_path or DEFAULT_CACHE_FILENAME)

    def load(self) -> Dict[str, Dict[str, Any]]:
        """Load cached file entries safely; return empty dict if absent or corrupt."""
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            files = data.get("files")
            return files if isinstance(files, dict) else {}
        except Exception:
            return {}

    def save(self, files_map: Dict[str, Dict[str, Any]]) -> None:
        """Persist cache atomically with sorted relative_path keys."""
        ordered = {k: files_map[k] for k in sorted(files_map.keys())}
        payload = json.dumps({"version": 1, "files": ordered}, indent=2) + "\n"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(self.cache_path.parent),
                prefix=".speccraft_cache.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp_path = tmp.name
                tmp.write(payload)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, self.cache_path)
        except Exception:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def partition(
        self, source_files: List[SourceFile]
    ) -> Tuple[List[Dict[str, Any]], List[SourceFile], Dict[str, Dict[str, Any]]]:
        """Split source files into cache hits and files requiring fresh parsing."""
        cached_db = self.load()
        hits: List[Dict[str, Any]] = []
        misses: List[SourceFile] = []
        hashes: Dict[str, str] = {}

        for sf in source_files:
            digest = compute_sha256(sf.content)
            hashes[sf.relative_path] = digest
            entry = cached_db.get(sf.relative_path)
            if isinstance(entry, dict) and entry.get("sha256") == digest:
                hits.append(entry)
            else:
                misses.append(sf)

        # Keep only active files for next save
        surviving_db: Dict[str, Dict[str, Any]] = {
            sf.relative_path: cached_db[sf.relative_path]
            for sf in source_files
            if sf.relative_path in cached_db and cached_db[sf.relative_path].get("sha256") == hashes[sf.relative_path]
        }
        return hits, misses, surviving_db

    @staticmethod
    def serialize_file_result(
        sf: SourceFile,
        endpoints: List[APIEndpoint],
        schemas: Dict[str, Dict[str, Any]],
        diagnostics: List[Diagnostic],
    ) -> Dict[str, Any]:
        """Serialize one file's extraction output for cache storage."""
        return {
            "sha256": compute_sha256(sf.content),
            "loc": sf.loc,
            "endpoints": [ep.model_dump(mode="json") for ep in endpoints],
            "schemas": schemas,
            "diagnostics": [d.model_dump(mode="json") for d in diagnostics],
        }

