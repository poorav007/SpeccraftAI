"""Multi-format export manager for SpecCraft AI.

Produces OpenAPI JSON, OpenAPI YAML, Postman Collection v2.1 JSON,
Markdown validation audit reports, and bundled ZIP archives.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any, Dict, Optional, Union

import yaml
from speccraft.exporters.postman_exporter import (
    PostmanCollectionExporter,
    parse_openapi_input,
)
from speccraft.schema_validator import OpenAPISchemaValidator


class ExportManager:
    """Coordinates exporting OpenAPI specs across supported developer formats."""

    def __init__(self) -> None:
        self._postman_exporter = PostmanCollectionExporter()
        self._validator = OpenAPISchemaValidator()

    def to_openapi_json(self, spec: Union[Dict[str, Any], str], indent: int = 2) -> str:
        """Serialize an OpenAPI specification into formatted JSON."""
        spec_dict = parse_openapi_input(spec)
        return json.dumps(spec_dict, indent=indent, ensure_ascii=False)

    def to_openapi_yaml(self, spec: Union[Dict[str, Any], str]) -> str:
        """Serialize an OpenAPI specification into clean YAML."""
        spec_dict = parse_openapi_input(spec)
        return yaml.safe_dump(spec_dict, sort_keys=False, allow_unicode=True)

    def to_postman_json(self, spec: Union[Dict[str, Any], str], indent: int = 2) -> str:
        """Convert an OpenAPI specification into Postman Collection v2.1 JSON."""
        return self._postman_exporter.to_json(spec, indent=indent)

    def to_validation_markdown(
        self,
        spec: Union[Dict[str, Any], str],
        validation_report: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a Markdown schema validation audit report."""
        spec_dict = parse_openapi_input(spec)
        if validation_report is None:
            validation_report = self._validator.validate(spec_dict).model_dump()

        info = spec_dict.get("info") or {}
        title = info.get("title") or "SpecCraft API"
        version = info.get("version") or "1.0.0"
        is_valid = bool(validation_report.get("is_valid", False))
        errors = validation_report.get("errors") or []
        warnings = validation_report.get("warnings") or []
        stats = validation_report.get("stats") or {}

        lines = [
            f"# SpecCraft AI — Validation Audit Report",
            "",
            f"- **API Title**: {title}",
            f"- **Version**: {version}",
            f"- **OpenAPI Version**: {spec_dict.get('openapi', '3.0.3')}",
            f"- **Status**: {'VALID' if is_valid else 'INVALID'}",
            f"- **Paths**: {stats.get('paths_count', len(spec_dict.get('paths') or {}))}",
            f"- **Operations**: {stats.get('operations_count', 0)}",
            f"- **Schemas**: {stats.get('schemas_count', len((spec_dict.get('components') or {}).get('schemas') or {}))}",
            "",
            f"## Errors ({len(errors)})",
            "",
        ]

        if errors:
            for err in errors:
                lines.append(
                    f"- **[{err.get('code', 'ERROR')}]** `{err.get('path', 'root')}`: {err.get('message', '')}"
                )
        else:
            lines.append("- None")

        lines.extend(["", f"## Warnings ({len(warnings)})", ""])
        if warnings:
            for warn in warnings:
                lines.append(
                    f"- **[{warn.get('code', 'WARN')}]** `{warn.get('path', 'root')}`: {warn.get('message', '')}"
                )
        else:
            lines.append("- None")

        lines.append("")
        return "\n".join(lines)

    def export_bundle_zip(
        self,
        spec: Union[Dict[str, Any], str],
        validation_report: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Package OpenAPI JSON/YAML, Postman v2.1 JSON, and audit report into a ZIP."""
        spec_dict = parse_openapi_input(spec)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("openapi.json", self.to_openapi_json(spec_dict))
            zf.writestr("openapi.yaml", self.to_openapi_yaml(spec_dict))
            zf.writestr("postman_collection.json", self.to_postman_json(spec_dict))
            zf.writestr(
                "validation_report.md",
                self.to_validation_markdown(spec_dict, validation_report),
            )
        return buf.getvalue()

