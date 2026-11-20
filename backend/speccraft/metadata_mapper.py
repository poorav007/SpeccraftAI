"""Metadata mapper and normalization pipeline for SpecCraft AI.

Normalizes URL paths (converting Starlette path converters like {path:path}),
generates unique operationIds with collision resolution, assigns default tags,
and enforces deterministic sorting for reproducible specs and stable diffs.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from speccraft.models import APIEndpoint, HTTPMethod

# Priority order for HTTP methods during deterministic sorting
METHOD_ORDER: Dict[HTTPMethod, int] = {
    HTTPMethod.GET: 1,
    HTTPMethod.POST: 2,
    HTTPMethod.PUT: 3,
    HTTPMethod.PATCH: 4,
    HTTPMethod.DELETE: 5,
    HTTPMethod.OPTIONS: 6,
    HTTPMethod.HEAD: 7,
}


def normalize_route_path(path: str) -> str:
    """Normalize route path and strip Starlette/FastAPI path converters.

    Examples:
        '/items/{item_id:int}' -> '/items/{item_id}'
        '/files/{file_path:path}' -> '/files/{file_path}'
        '//api//v1/items/' -> '/api/v1/items'
        '/' -> '/'
    """
    if not path:
        return "/"

    # Ensure leading slash
    if not path.startswith("/"):
        path = "/" + path

    # Deduplicate consecutive slashes
    cleaned = re.sub(r"/+", "/", path)

    # Convert Starlette converters like {name:converter} -> {name}
    cleaned = re.sub(r"\{([a-zA-Z0-9_]+):[a-zA-Z0-9_]+\}", r"{\1}", cleaned)

    # Strip trailing slash unless it's the root '/'
    if len(cleaned) > 1 and cleaned.endswith("/"):
        cleaned = cleaned.rstrip("/")

    return cleaned


def resolve_operation_id(name: str, used_ids: Set[str]) -> str:
    """Generate a clean, unique operationId resolving collisions with numbered suffixes."""
    # Convert camelCase or hyphen-separated to clean snake_case identifier
    base = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_")
    if not base:
        base = "operation"

    candidate = base
    suffix = 1
    while candidate in used_ids:
        candidate = f"{base}_{suffix}"
        suffix += 1

    used_ids.add(candidate)
    return candidate


def map_and_normalize_endpoints(endpoints: List[APIEndpoint]) -> List[APIEndpoint]:
    """Map, normalize, and deterministically sort extracted API endpoints.

    Sorts endpoints by path, then method priority before resolving operationId collisions
    to guarantee consistent, reproducible operation IDs across runs.

    Args:
        endpoints: Raw list of extracted APIEndpoint models.

    Returns:
        List of normalized APIEndpoint models sorted by path, then method.
    """
    # Pre-sort by normalized path and HTTP method priority so operation IDs are deterministic
    sorted_endpoints = sorted(
        endpoints,
        key=lambda ep: (normalize_route_path(ep.path), METHOD_ORDER.get(ep.method, 99)),
    )

    used_operation_ids: Set[str] = set()
    normalized: List[APIEndpoint] = []

    for ep in sorted_endpoints:
        clean_path = normalize_route_path(ep.path)

        # Derive base operation id from existing ID, summary, or method+path
        raw_op_id = ep.operation_id
        if not raw_op_id:
            # Fallback: get_items or post_orders
            path_slug = re.sub(r"\{[a-zA-Z0-9_]+\}", "", clean_path).strip("/").replace("/", "_")
            raw_op_id = f"{ep.method.value}_{path_slug}" if path_slug else f"{ep.method.value}_root"

        unique_op_id = resolve_operation_id(raw_op_id, used_operation_ids)

        # Ensure at least one tag
        tags = list(ep.tags)
        if not tags:
            # Fall back to first segment of path (e.g. /items/{id} -> 'items')
            segments = [s for s in clean_path.split("/") if s and not s.startswith("{")]
            tags = [segments[0]] if segments else ["default"]

        updated_ep = ep.model_copy(
            update={
                "path": clean_path,
                "operation_id": unique_op_id,
                "tags": tags,
            }
        )
        normalized.append(updated_ep)

    return normalized
