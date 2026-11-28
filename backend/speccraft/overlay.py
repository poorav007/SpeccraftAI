"""Non-destructive documentation overlay store (speccraft.overlay.json).

Persists human-edited and AI-accepted endpoint documentation keyed by
`METHOD /path` with alphabetically sorted keys and atomic temp-file writes,
so re-running the static AST parser never overwrites documentation while
AST code facts (path, method, parameter models) remain strictly protected.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from speccraft.models import ExtractionResult

DEFAULT_OVERLAY_FILENAME = "speccraft.overlay.json"


class OverlayEntry(BaseModel):
    """Documentation overrides saved for a single `METHOD /path` route."""

    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Literal["human", "ai-accepted"] = "human"
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OverlayDocument(BaseModel):
    """Top-level schema for speccraft.overlay.json."""

    version: int = 1
    entries: Dict[str, OverlayEntry] = Field(default_factory=dict)


def make_overlay_key(method: str, path: str) -> str:
    """Build canonical route overlay key (`METHOD /path`)."""
    return f"{str(method or '').strip().upper()} {str(path or '').strip()}"


class OverlayStore:
    """Manages reading, sorting, atomic writing, and applying route overlays."""

    def __init__(self, overlay_path: Optional[Path] = None) -> None:
        env_path = os.getenv("SPECCRAFT_OVERLAY_PATH", "").strip()
        if overlay_path is not None:
            self.overlay_path = Path(overlay_path)
        elif env_path:
            self.overlay_path = Path(env_path)
        else:
            self.overlay_path = Path(DEFAULT_OVERLAY_FILENAME)

    def load(self) -> OverlayDocument:
        """Load overlay document safely; return empty doc if absent or invalid."""
        if not self.overlay_path.exists():
            return OverlayDocument()
        try:
            raw = self.overlay_path.read_text(encoding="utf-8")
            if not raw.strip():
                return OverlayDocument()
            data = json.loads(raw)
            return OverlayDocument.model_validate(data)
        except Exception:
            return OverlayDocument()

    def save(self, doc: OverlayDocument) -> OverlayDocument:
        """Write overlay document atomically with alphabetically sorted keys."""
        sorted_entries = {
            k: doc.entries[k].model_dump() for k in sorted(doc.entries.keys())
        }
        serialized = json.dumps(
            {"version": doc.version, "entries": sorted_entries},
            indent=2,
            ensure_ascii=False,
        ) + "\n"

        self.overlay_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(self.overlay_path.parent),
                prefix=".speccraft.overlay.",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.write(serialized)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_path, self.overlay_path)
        except Exception:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        return OverlayDocument(
            version=doc.version,
            entries={k: doc.entries[k] for k in sorted(doc.entries.keys())},
        )

    def upsert_entry(
        self,
        method: str,
        path: str,
        entry: OverlayEntry,
    ) -> OverlayDocument:
        """Insert or update a route overlay entry and persist atomically."""
        doc = self.load()
        key = make_overlay_key(method, path)
        doc.entries[key] = entry
        return self.save(doc)

    def delete_entry(self, key: str) -> OverlayDocument:
        """Remove an overlay entry by canonical key (`METHOD /path`) if present."""
        doc = self.load()
        if key in doc.entries:
            del doc.entries[key]
            return self.save(doc)
        return doc

    def apply_to_extraction_result(self, result: ExtractionResult) -> ExtractionResult:
        """Merge saved documentation overlays onto freshly parsed AST endpoints.

        Never alters route path, HTTP method, or parameter models. Records any
        saved keys that no longer match any extracted route in `orphaned_overlay_keys`.
        """
        doc = self.load()
        if not doc.entries:
            result.orphaned_overlay_keys = []
            return result

        matched_keys = set()
        for endpoint in result.endpoints:
            key = make_overlay_key(endpoint.method.value, endpoint.path)
            entry = doc.entries.get(key)
            if entry is None:
                continue

            matched_keys.add(key)
            if entry.operation_id:
                endpoint.operation_id = entry.operation_id
            if entry.summary is not None:
                endpoint.summary = entry.summary
            if entry.description is not None:
                endpoint.description = entry.description
            if entry.tags is not None:
                endpoint.tags = list(entry.tags)
            endpoint.enrichment_metadata["overlay_source"] = entry.source
            endpoint.enrichment_metadata["overlay_updated_at"] = entry.updated_at

        result.orphaned_overlay_keys = sorted(
            k for k in doc.entries.keys() if k not in matched_keys
        )
        return result


def get_overlay_store() -> OverlayStore:
    """Factory returning an OverlayStore configured from SPECCRAFT_OVERLAY_PATH or cwd."""
    return OverlayStore()

