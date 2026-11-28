"""Postman Collection v2.1 exporter for SpecCraft AI.

Converts OpenAPI 3.0.x specifications into Postman Collection v2.1.0 JSON
documents grouped by OpenAPI tags with path variables, query parameters,
and sample JSON request bodies derived statically from component schemas.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional, Union

import yaml

from speccraft.exporters.schema_sampler import sample_value_from_schema

POSTMAN_V2_1_SCHEMA = (
    "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
)
HTTP_METHODS_ORDER = ("get", "post", "put", "patch", "delete", "options", "head")
_PATH_PARAM_PATTERN = re.compile(r"^\{([^}]+)\}$")


def parse_openapi_input(spec: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """Parse an OpenAPI spec dictionary, JSON string, or YAML string."""
    if isinstance(spec, dict):
        return spec
    if isinstance(spec, str):
        stripped = spec.strip()
        if not stripped:
            raise ValueError("Specification string is empty.")
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = yaml.safe_load(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("Parsed specification must be a JSON/YAML object.")
        return parsed
    raise TypeError(f"Unsupported specification type: {type(spec).__name__}")


class PostmanCollectionExporter:
    """Converts OpenAPI 3.0 specifications into Postman Collection v2.1 format."""

    def convert(self, spec: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Convert an OpenAPI 3.0 specification into a Postman v2.1 dictionary."""
        spec_dict = parse_openapi_input(spec)
        info = spec_dict.get("info") or {}
        components = spec_dict.get("components") or {}
        schemas = components.get("schemas") or {}

        servers = spec_dict.get("servers") or []
        base_url = "http://localhost:8000"
        if isinstance(servers, list) and servers and isinstance(servers[0], dict):
            base_url = str(servers[0].get("url") or base_url).rstrip("/")

        grouped_items: Dict[str, List[Dict[str, Any]]] = {}
        paths = spec_dict.get("paths") or {}

        for raw_path in sorted(paths.keys()):
            path_item = paths.get(raw_path)
            if not isinstance(path_item, dict):
                continue

            path_level_params = path_item.get("parameters") or []
            for method in HTTP_METHODS_ORDER:
                operation = path_item.get(method)
                if not isinstance(operation, dict):
                    continue

                item_entry = self._build_request_item(
                    raw_path=raw_path,
                    method=method,
                    operation=operation,
                    path_level_params=path_level_params,
                    schemas=schemas,
                )
                tags = operation.get("tags") or ["General"]
                folder_name = str(tags[0]) if tags else "General"
                grouped_items.setdefault(folder_name, []).append(item_entry)

        collection_items = [
            {"name": folder, "item": items}
            for folder, items in grouped_items.items()
        ]

        return {
            "info": {
                "_postman_id": str(uuid.uuid5(uuid.NAMESPACE_URL, str(info.get("title", "speccraft")))),
                "name": str(info.get("title") or "SpecCraft API"),
                "description": str(info.get("description") or ""),
                "version": str(info.get("version") or "1.0.0"),
                "schema": POSTMAN_V2_1_SCHEMA,
            },
            "item": collection_items,
            "variable": [
                {
                    "key": "baseUrl",
                    "value": base_url,
                    "type": "string",
                }
            ],
        }

    def to_json(self, spec: Union[Dict[str, Any], str], indent: int = 2) -> str:
        """Convert an OpenAPI 3.0 specification into a formatted Postman JSON string."""
        collection = self.convert(spec)
        return json.dumps(collection, indent=indent, ensure_ascii=False)

    def _build_request_item(
        self,
        raw_path: str,
        method: str,
        operation: Dict[str, Any],
        path_level_params: List[Dict[str, Any]],
        schemas: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a single Postman request item from an OpenAPI operation."""
        merged_params = self._merge_parameters(
            path_level_params, operation.get("parameters") or []
        )
        url_obj = self._build_url(raw_path, merged_params, schemas)
        headers = self._build_headers(merged_params, operation)
        body = self._build_body(operation, schemas)

        request_obj: Dict[str, Any] = {
            "method": method.upper(),
            "header": headers,
            "url": url_obj,
            "description": str(operation.get("description") or operation.get("summary") or ""),
        }
        if body is not None:
            request_obj["body"] = body

        item_name = str(
            operation.get("summary")
            or operation.get("operationId")
            or f"{method.upper()} {raw_path}"
        )

        return {
            "name": item_name,
            "request": request_obj,
            "response": [],
        }

    def _merge_parameters(
        self,
        path_params: List[Dict[str, Any]],
        op_params: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merge path-level and operation-level parameters with operation override."""
        merged: Dict[tuple[str, str], Dict[str, Any]] = {}
        for param in [*path_params, *op_params]:
            if not isinstance(param, dict):
                continue
            key = (str(param.get("name", "")), str(param.get("in", "query")))
            if key[0]:
                merged[key] = param
        return list(merged.values())

    def _build_url(
        self,
        raw_path: str,
        parameters: List[Dict[str, Any]],
        schemas: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert OpenAPI path + params into Postman URL with :var syntax."""
        segments = [seg for seg in raw_path.strip("/").split("/") if seg]
        postman_segments: List[str] = []
        path_vars: List[Dict[str, Any]] = []
        param_lookup = {
            (str(p.get("name", "")), str(p.get("in", ""))): p for p in parameters
        }

        for seg in segments:
            match = _PATH_PARAM_PATTERN.match(seg)
            if match:
                var_name = match.group(1)
                postman_segments.append(f":{var_name}")
                p_def = param_lookup.get((var_name, "path"), {})
                p_schema = p_def.get("schema") or {}
                sample_val = sample_value_from_schema(p_schema, schemas)
                path_vars.append(
                    {
                        "key": var_name,
                        "value": str(sample_val if sample_val is not None else "1"),
                        "description": str(p_def.get("description") or ""),
                    }
                )
            else:
                postman_segments.append(seg)

        query_params: List[Dict[str, Any]] = []
        for param in parameters:
            if param.get("in") != "query":
                continue
            p_schema = param.get("schema") or {}
            sample_val = sample_value_from_schema(p_schema, schemas)
            query_params.append(
                {
                    "key": str(param.get("name", "")),
                    "value": "" if sample_val is None else str(sample_val),
                    "description": str(param.get("description") or ""),
                    "disabled": not bool(param.get("required", False)),
                }
            )

        postman_path = "/" + "/".join(postman_segments) if postman_segments else ""
        raw_url = f"{{{{baseUrl}}}}{postman_path}"
        if query_params:
            query_str = "&".join(f"{q['key']}={q['value']}" for q in query_params)
            raw_url = f"{raw_url}?{query_str}"

        url_obj: Dict[str, Any] = {
            "raw": raw_url,
            "host": ["{{baseUrl}}"],
            "path": postman_segments,
        }
        if path_vars:
            url_obj["variable"] = path_vars
        if query_params:
            url_obj["query"] = query_params
        return url_obj

    def _build_headers(
        self,
        parameters: List[Dict[str, Any]],
        operation: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build Postman header entries from header parameters and JSON request bodies."""
        headers: List[Dict[str, Any]] = []
        has_content_type = False

        for param in parameters:
            if param.get("in") != "header":
                continue
            name = str(param.get("name", ""))
            if name.lower() == "content-type":
                has_content_type = True
            headers.append(
                {
                    "key": name,
                    "value": str(param.get("example") or ""),
                    "description": str(param.get("description") or ""),
                }
            )

        request_body = operation.get("requestBody") or {}
        content = request_body.get("content") or {}
        if "application/json" in content and not has_content_type:
            headers.append(
                {
                    "key": "Content-Type",
                    "value": "application/json",
                }
            )
        return headers

    def _build_body(
        self,
        operation: Dict[str, Any],
        schemas: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Build a raw JSON Postman request body from an OpenAPI requestBody schema."""
        request_body = operation.get("requestBody")
        if not isinstance(request_body, dict):
            return None

        content = request_body.get("content") or {}
        json_media = content.get("application/json")
        if not isinstance(json_media, dict):
            return None

        schema = json_media.get("schema") or {}
        example_payload = json_media.get("example")
        if example_payload is None:
            example_payload = sample_value_from_schema(schema, schemas)
        if example_payload is None:
            example_payload = {}

        return {
            "mode": "raw",
            "raw": json.dumps(example_payload, indent=2, ensure_ascii=False),
            "options": {"raw": {"language": "json"}},
        }

