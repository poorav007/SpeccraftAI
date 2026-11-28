"""Multi-format export manager for SpecCraft AI.

Produces OpenAPI JSON, OpenAPI YAML, Postman Collection v2.1 JSON,
Markdown validation audit reports, and bundled ZIP archives.
"""

from __future__ import annotations

import html
import io
import json
import zipfile
from typing import Any, Dict, List, Optional, Union

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
            zf.writestr(
                "client_handoff.html",
                self.to_handoff_html(spec_dict, validation_report),
            )
        return buf.getvalue()

    def to_handoff_html(
        self,
        spec: Union[Dict[str, Any], str],
        validation_report: Optional[Dict[str, Any]] = None,
        brand_name: str = "SpecCraft AI",
    ) -> str:
        """Render a self-contained, XSS-escaped @media print HTML client handoff report."""
        spec_dict = parse_openapi_input(spec)
        if validation_report is None:
            validation_report = self._validator.validate(spec_dict).model_dump()

        info = spec_dict.get("info") or {}
        paths = spec_dict.get("paths") or {}
        schemas = (spec_dict.get("components") or {}).get("schemas") or {}
        errors = validation_report.get("errors") or []
        warnings = validation_report.get("warnings") or []
        is_valid = bool(validation_report.get("is_valid", len(errors) == 0))

        safe_brand = html.escape(str(brand_name or "SpecCraft AI"), quote=True)
        safe_title = html.escape(str(info.get("title") or "API Documentation"), quote=True)
        safe_version = html.escape(str(info.get("version") or "1.0.0"), quote=True)
        safe_desc = html.escape(
            str(info.get("description") or "Generated statically from codebase AST."),
            quote=True,
        )

        endpoint_blocks: List[str] = []
        op_count = 0
        for raw_path in sorted(paths.keys()):
            path_item = paths.get(raw_path)
            if not isinstance(path_item, dict):
                continue
            for method in ("get", "post", "put", "patch", "delete", "options", "head"):
                op = path_item.get(method)
                if not isinstance(op, dict):
                    continue
                op_count += 1
                safe_method = html.escape(method.upper(), quote=True)
                safe_path = html.escape(str(raw_path), quote=True)
                safe_summary = html.escape(
                    str(op.get("summary") or op.get("operationId") or "No summary"),
                    quote=True,
                )
                safe_op_desc = html.escape(str(op.get("description") or ""), quote=True)
                tags_html = "".join(
                    f'<span class="tag">{html.escape(str(t), quote=True)}</span>'
                    for t in (op.get("tags") or [])
                )
                params = op.get("parameters") or []
                params_html = ""
                if params:
                    param_items = "".join(
                        f"<li><code>{html.escape(str(p.get('name', '')), quote=True)}</code> "
                        f"({html.escape(str(p.get('in', 'query')), quote=True)}, "
                        f"{'required' if p.get('required') else 'optional'})</li>"
                        for p in params
                        if isinstance(p, dict)
                    )
                    params_html = f'<div class="meta"><strong>Parameters:</strong><ul>{param_items}</ul></div>'

                desc_html = f'<p class="op-desc">{safe_op_desc}</p>' if safe_op_desc else ""
                endpoint_blocks.append(
                    f"""
                    <article class="endpoint-card">
                      <div class="ep-head">
                        <span class="method method-{safe_method.lower()}">{safe_method}</span>
                        <code class="ep-path">{safe_path}</code>
                        <div class="tags">{tags_html}</div>
                      </div>
                      <div class="ep-summary">{safe_summary}</div>
                      {desc_html}
                      {params_html}
                    </article>
                    """
                )

        schema_rows = []
        for schema_name in sorted(schemas.keys()):
            schema_obj = schemas.get(schema_name) or {}
            props = schema_obj.get("properties") or {}
            prop_list = ", ".join(
                html.escape(str(prop_key), quote=True) for prop_key in props.keys()
            )
            schema_rows.append(
                f"<tr><td><code>{html.escape(str(schema_name), quote=True)}</code></td>"
                f"<td>{len(props)}</td><td><code>{prop_list or '—'}</code></td></tr>"
            )

        status_label = "VALID OPENAPI 3.0.3" if is_valid else f"INVALID ({len(errors)} ERRORS)"
        status_class = "status-valid" if is_valid else "status-invalid"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_brand} — {safe_title} Client Handoff</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: #0f172a;
      background: #f8fafc;
      margin: 0;
      padding: 24px;
      line-height: 1.5;
    }}
    .sheet {{
      max-width: 960px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 32px;
    }}
    header {{
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 16px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .brand {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #2563eb; }}
    h1 {{ margin: 4px 0; font-size: 26px; }}
    .subtitle {{ color: #475569; margin: 0; font-size: 14px; }}
    .status-pill {{
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }}
    .status-valid {{ background: #dcfce7; color: #166534; }}
    .status-invalid {{ background: #fee2e2; color: #991b1b; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 28px;
    }}
    .metric {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px;
    }}
    .metric-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; }}
    .metric-val {{ font-size: 20px; font-weight: 700; }}
    .endpoint-card {{
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 12px;
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    .ep-head {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }}
    .method {{ font-family: monospace; font-weight: 700; font-size: 12px; padding: 2px 8px; border-radius: 4px; color: #fff; background: #475569; }}
    .method-get {{ background: #0d6efd; }}
    .method-post {{ background: #198754; }}
    .method-put {{ background: #fd7e14; }}
    .method-delete {{ background: #dc3545; }}
    .method-patch {{ background: #6f42c1; }}
    .ep-path {{ font-weight: 700; font-size: 14px; }}
    .tag {{ background: #e2e8f0; color: #334155; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 4px; }}
    .ep-summary {{ font-weight: 600; margin-bottom: 4px; }}
    .op-desc {{ color: #475569; font-size: 13px; margin: 4px 0 0; }}
    .meta {{ margin-top: 8px; font-size: 12px; color: #334155; }}
    .meta ul {{ margin: 4px 0 0; padding-left: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; }}
    th {{ background: #f8fafc; }}
    .print-bar {{ margin-bottom: 16px; text-align: right; }}
    .print-btn {{
      background: #0f172a; color: #fff; border: 0; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 600;
    }}
    @media print {{
      body {{ background: #ffffff; padding: 0; }}
      .sheet {{ border: 0; padding: 0; }}
      .no-print {{ display: none !important; }}
    }}
  </style>
</head>
<body>
  <div class="sheet">
    <div class="print-bar no-print">
      <button type="button" class="print-btn" onclick="window.print()">Print / Save as PDF</button>
    </div>
    <header>
      <div>
        <div class="brand">{safe_brand} · Client API Handoff</div>
        <h1>{safe_title} <small style="font-weight:400;color:#64748b;">v{safe_version}</small></h1>
        <p class="subtitle">{safe_desc}</p>
      </div>
      <span class="status-pill {status_class}">{status_label}</span>
    </header>

    <section class="metrics">
      <div class="metric"><div class="metric-label">Paths</div><div class="metric-val">{len(paths)}</div></div>
      <div class="metric"><div class="metric-label">Operations</div><div class="metric-val">{op_count}</div></div>
      <div class="metric"><div class="metric-label">Schemas</div><div class="metric-val">{len(schemas)}</div></div>
      <div class="metric"><div class="metric-label">Warnings</div><div class="metric-val">{len(warnings)}</div></div>
    </section>

    <section>
      <h2>Endpoints ({op_count})</h2>
      {"".join(endpoint_blocks) if endpoint_blocks else "<p>No endpoints defined.</p>"}
    </section>

    <section style="margin-top:28px;">
      <h2>Data Schemas ({len(schemas)})</h2>
      <table>
        <thead><tr><th>Model</th><th>Fields</th><th>Attributes</th></tr></thead>
        <tbody>
          {"".join(schema_rows) if schema_rows else '<tr><td colspan="3">No component schemas.</td></tr>'}
        </tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""


