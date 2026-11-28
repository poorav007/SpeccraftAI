"""Structured prompt builders for SpecCraft AI documentation enrichment."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def build_endpoint_docs_prompt(endpoint_data: Dict[str, Any]) -> Tuple[str, str]:
    """Return (system_prompt, user_prompt) for endpoint documentation generation."""
    system_prompt = (
        "You are an API technical writer for SpecCraft AI. "
        "Generate concise OpenAPI 3.0 documentation strictly from the provided AST facts. "
        "NEVER invent or alter route paths, HTTP methods, parameter names, or data types. "
        "Respond ONLY with valid JSON matching: "
        '{"summary": "<max 60 chars>", "description": "<1-3 crisp sentences>", "suggested_tags": ["<tag>"]}.'
    )
    safe_context = {
        "method": endpoint_data.get("method", "get"),
        "path": endpoint_data.get("path", "/"),
        "operation_id": endpoint_data.get("operation_id") or "",
        "existing_summary": endpoint_data.get("summary") or "",
        "existing_description": endpoint_data.get("description") or "",
        "tags": endpoint_data.get("tags") or [],
        "parameters": [
            {
                "name": p.get("name"),
                "in": p.get("location") or p.get("in") or "query",
                "type": p.get("param_type") or p.get("type_annotation") or p.get("type") or "string",
                "required": bool(p.get("required", False)),
            }
            for p in (endpoint_data.get("parameters") or [])[:20]
        ],
        "has_request_body": bool(endpoint_data.get("request_body")),
    }
    user_prompt = f"AST Endpoint Facts:\n{json.dumps(safe_context, indent=2)}"
    return system_prompt, user_prompt


def build_schema_field_prompt(field_data: Dict[str, Any]) -> Tuple[str, str]:
    """Return (system_prompt, user_prompt) for explaining a Pydantic/parameter field."""
    system_prompt = (
        "You are an API technical writer for SpecCraft AI. "
        "Explain the purpose of an API field in plain developer language and suggest one realistic example value. "
        "NEVER alter the field name or type. "
        "Respond ONLY with valid JSON matching: "
        '{"explanation": "<1-2 crisp sentences>", "example": <JSON primitive or array/object matching type>}.'
    )
    safe_context = {
        "field_name": field_data.get("field_name", ""),
        "field_type": field_data.get("field_type", "string"),
        "location": field_data.get("location", "body"),
        "required": bool(field_data.get("required", False)),
        "endpoint_path": field_data.get("endpoint_path", ""),
        "endpoint_method": field_data.get("endpoint_method", ""),
        "existing_description": field_data.get("existing_description") or "",
    }
    user_prompt = f"Schema Field Context:\n{json.dumps(safe_context, indent=2)}"
    return system_prompt, user_prompt


def build_diff_summary_prompt(
    summary_stats: Dict[str, Any],
    capped_changes: List[Dict[str, Any]],
    truncated: bool,
) -> Tuple[str, str]:
    """Return (system_prompt, user_prompt) for summarizing OpenAPI spec diffs."""
    system_prompt = (
        "You are an API release engineer for SpecCraft AI. "
        "Summarize OpenAPI specification differences for developers and mobile reviewers. "
        "Do NOT alter endpoints, methods, or before/after facts. "
        "Respond ONLY with valid JSON matching: "
        '{"executive_summary": "<concise overview>", '
        '"risk_level": "low"|"medium"|"high", '
        '"migration_steps": ["<step>"], '
        '"card_impacts": ["<1 short sentence per input change index in same order>"]}.'
    )
    payload = {
        "stats": summary_stats,
        "truncated_for_context": truncated,
        "changes": [
            {
                "index": idx,
                "method": c.get("method", ""),
                "path": c.get("path", ""),
                "is_breaking": bool(c.get("is_breaking", False)),
                "change_type": c.get("change_type", ""),
                "description": c.get("description", ""),
            }
            for idx, c in enumerate(capped_changes)
        ],
    }
    user_prompt = f"Diff Changes:\n{json.dumps(payload, indent=2)}"
    return system_prompt, user_prompt

