"""Standalone FastAPI Mock API Server generator from OpenAPI 3.0 specifications."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union

from speccraft.exporters.postman_exporter import HTTP_METHODS_ORDER, parse_openapi_input
from speccraft.exporters.schema_sampler import sample_value_from_schema


def _safe_handler_name(method: str, path: str, op_id: str | None) -> str:
    raw = op_id or f"{method}_{path}"
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", raw).strip("_").lower()
    return f"mock_{cleaned or 'endpoint'}"


class MockServerGenerator:
    """Generates a self-contained runnable FastAPI mock_server.py from OpenAPI specs."""

    def to_fastapi_mock_code(self, spec: Union[Dict[str, Any], str]) -> str:
        """Render standalone FastAPI mock server Python source code."""
        spec_dict = parse_openapi_input(spec)
        info = spec_dict.get("info") or {}
        schemas = (spec_dict.get("components") or {}).get("schemas") or {}
        paths = spec_dict.get("paths") or {}

        lines: List[str] = [
            f'"""Auto-generated Mock API Server for {info.get("title", "SpecCraft API")}."""',
            "",
            "from fastapi import FastAPI, Response",
            "",
            f'app = FastAPI(title={str(info.get("title") or "Mock API")!r}, version={str(info.get("version") or "1.0.0")!r})',
            "",
        ]

        seen_names = set()
        for raw_path in sorted(paths.keys()):
            path_item = paths.get(raw_path) or {}
            for method in HTTP_METHODS_ORDER:
                op = path_item.get(method)
                if not isinstance(op, dict):
                    continue

                base_name = _safe_handler_name(method, raw_path, op.get("operationId"))
                fn_name = base_name
                idx = 2
                while fn_name in seen_names:
                    fn_name = f"{base_name}_{idx}"
                    idx += 1
                seen_names.add(fn_name)

                responses = op.get("responses") or {}
                chosen_code = "200"
                for code in sorted(responses.keys()):
                    if code.startswith("2"):
                        chosen_code = code
                        break
                status_int = int(chosen_code) if chosen_code.isdigit() else 200

                resp_obj = responses.get(chosen_code) or {}
                json_schema = (
                    (resp_obj.get("content") or {})
                    .get("application/json", {})
                    .get("schema")
                )
                sample_payload = (
                    sample_value_from_schema(json_schema, schemas)
                    if isinstance(json_schema, dict)
                    else {"status": "ok", "mock": True}
                )

                path_params = re.findall(r"\{([^}]+)\}", raw_path)
                sig_args = ", ".join(f"{p}: str" for p in path_params)

                lines.append(
                    f'@app.{method}({raw_path!r}, status_code={status_int})'
                )
                lines.append(f"async def {fn_name}({sig_args}):")
                if status_int == 204:
                    lines.append("    return Response(status_code=204)")
                else:
                    lines.append(f"    return {sample_payload!r}")
                lines.append("")

        lines.extend(
            [
                'if __name__ == "__main__":',
                "    import uvicorn",
                "    uvicorn.run(app, host='127.0.0.1', port=8001)",
                "",
            ]
        )
        return "\n".join(lines)

