"""Shared deterministic OpenAPI JSON Schema sample-value generator.

Reused across PostmanCollectionExporter and MockServerGenerator to avoid
duplicating $ref traversal and circular reference guards.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set


def sample_value_from_schema(
    schema: Dict[str, Any],
    schemas: Dict[str, Any],
    visited: Optional[Set[str]] = None,
) -> Any:
    """Generate a deterministic sample value from an OpenAPI JSON Schema."""
    if not isinstance(schema, dict):
        return None

    seen = set(visited or set())

    if "$ref" in schema:
        ref = str(schema["$ref"])
        if ref in seen:
            return {}
        seen.add(ref)
        ref_name = ref.split("/")[-1]
        target = schemas.get(ref_name)
        return sample_value_from_schema(target, schemas, seen) if isinstance(target, dict) else {}

    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if isinstance(schema.get("enum"), list) and schema["enum"]:
        return schema["enum"][0]

    for combiner in ("anyOf", "oneOf"):
        variants = schema.get(combiner)
        if isinstance(variants, list):
            for variant in variants:
                if isinstance(variant, dict) and variant.get("type") != "null":
                    return sample_value_from_schema(variant, schemas, seen)

    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        return {
            prop_name: sample_value_from_schema(prop_schema, schemas, seen)
            for prop_name, prop_schema in props.items()
        }
    if schema_type == "array":
        item_schema = schema.get("items") or {"type": "string"}
        return [sample_value_from_schema(item_schema, schemas, seen)]
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.0
    if schema_type == "boolean":
        return True
    if schema_type == "string":
        fmt = schema.get("format")
        if fmt == "email":
            return "user@example.com"
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        return "string"
    return "string"

