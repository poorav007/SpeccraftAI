"""OpenAPI 3.0.3 specification generator for SpecCraft AI.

Transforms static AST ExtractionResult models into fully compliant,
deterministically ordered OpenAPI 3.0.3 specifications in JSON and YAML formats.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
from speccraft.models import (
    APIEndpoint,
    ExtractionResult,
    HTTPMethod,
    ParameterLocation,
    ParameterModel,
    RequestBodyModel,
    ResponseModel,
)

# Standard HTTP method ordering for deterministic output
METHOD_ORDER = ["get", "post", "put", "patch", "delete", "options", "head"]

# Standard FastAPI / OpenAPI error schemas
STANDARD_ERROR_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "ValidationError": {
        "title": "ValidationError",
        "type": "object",
        "required": ["loc", "msg", "type"],
        "properties": {
            "loc": {
                "title": "Location",
                "type": "array",
                "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
            },
            "msg": {"title": "Message", "type": "string"},
            "type": {"title": "Error Type", "type": "string"},
        },
    },
    "HTTPValidationError": {
        "title": "HTTPValidationError",
        "type": "object",
        "properties": {
            "detail": {
                "title": "Detail",
                "type": "array",
                "items": {"$ref": "#/components/schemas/ValidationError"},
            }
        },
    },
}


class OpenAPIGenerator:
    """Transforms ExtractionResult into a valid, deterministically ordered OpenAPI 3.0.3 document."""

    def __init__(
        self,
        title: str = "SpecCraft API",
        version: str = "1.0.0",
        description: Optional[str] = "Auto-generated OpenAPI 3.0.3 specification via SpecCraft AI static AST analysis.",
        servers: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        self.title = title
        self.version = version
        self.description = description
        self.servers = servers or [{"url": "/", "description": "Default server"}]

    def generate(self, result: ExtractionResult) -> Dict[str, Any]:
        """Generate an OpenAPI 3.0.3 dictionary from extraction results.

        Guarantees deterministic key ordering across info, paths, methods,
        and schemas to support stable diff engines.
        """
        # 1. Info object
        info: Dict[str, Any] = {
            "title": self.title,
            "version": self.version,
        }
        if self.description:
            info["description"] = self.description

        # 2. Group endpoints by path
        endpoints_by_path: Dict[str, List[APIEndpoint]] = {}
        for ep in result.endpoints:
            endpoints_by_path.setdefault(ep.path, []).append(ep)

        # Sort paths alphabetically
        sorted_paths = sorted(endpoints_by_path.keys())

        # 3. Build paths object
        paths_obj: Dict[str, Any] = {}
        all_tags: Set[str] = set()
        needs_validation_error = False

        for path in sorted_paths:
            path_ops: Dict[str, Any] = {}
            # Sort operations by method rank
            eps = endpoints_by_path[path]
            eps.sort(key=lambda x: METHOD_ORDER.index(x.method.value) if x.method.value in METHOD_ORDER else 99)

            for ep in eps:
                op, uses_422 = self._build_operation(ep, result.schemas)
                path_ops[ep.method.value] = op
                if uses_422:
                    needs_validation_error = True
                for t in ep.tags:
                    all_tags.add(t)

            paths_obj[path] = path_ops

        # 4. Build components schemas
        components_schemas: Dict[str, Any] = {}
        # Copy extracted Pydantic schemas sorted alphabetically
        for schema_name in sorted(result.schemas.keys()):
            components_schemas[schema_name] = result.schemas[schema_name]

        # Add standard validation error schemas if referenced
        if needs_validation_error:
            for err_name, err_def in STANDARD_ERROR_SCHEMAS.items():
                if err_name not in components_schemas:
                    components_schemas[err_name] = err_def

        # 5. Build tags list sorted alphabetically
        tags_list = [{"name": t} for t in sorted(all_tags)]

        # 6. Assemble complete document in deterministic top-level order
        spec: Dict[str, Any] = {
            "openapi": "3.0.3",
            "info": info,
            "servers": self.servers,
        }
        if tags_list:
            spec["tags"] = tags_list

        spec["paths"] = paths_obj

        if components_schemas:
            spec["components"] = {"schemas": components_schemas}

        return spec

    def _build_operation(
        self,
        ep: APIEndpoint,
        known_schemas: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], bool]:
        """Build an OpenAPI operation object for a single endpoint."""
        op: Dict[str, Any] = {}

        if ep.tags:
            op["tags"] = ep.tags

        if ep.summary:
            op["summary"] = ep.summary

        if ep.description:
            op["description"] = ep.description

        if ep.operation_id:
            op["operationId"] = ep.operation_id

        # Parameters
        parameters = self._build_parameters(ep.parameters)
        if parameters:
            op["parameters"] = parameters

        # Request Body
        if ep.request_body and ep.method in (HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH):
            op["requestBody"] = self._build_request_body(ep.request_body, known_schemas)

        # Responses
        responses, uses_422 = self._build_responses(ep, known_schemas)
        op["responses"] = responses

        if ep.deprecated:
            op["deprecated"] = True

        return op, uses_422

    def _build_parameters(self, params: List[ParameterModel]) -> List[Dict[str, Any]]:
        """Construct OpenAPI parameter list from parameter models."""
        out: List[Dict[str, Any]] = []
        for p in params:
            param_dict: Dict[str, Any] = {
                "name": p.name,
                "in": p.location.value,
                "required": p.required if p.location != ParameterLocation.PATH else True,
            }
            if p.description:
                param_dict["description"] = p.description

            schema: Dict[str, Any] = {"type": p.param_type}
            if p.default is not None:
                schema["default"] = p.default
            if p.example is not None:
                param_dict["example"] = p.example
            if p.schema_dict:
                schema.update(p.schema_dict)

            param_dict["schema"] = schema
            out.append(param_dict)

        return out

    def _build_request_body(
        self,
        body: RequestBodyModel,
        known_schemas: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Construct OpenAPI requestBody object."""
        schema: Dict[str, Any]

        if body.schema_name and body.schema_name in known_schemas:
            schema = {"$ref": f"#/components/schemas/{body.schema_name}"}
        elif body.schema_ref:
            schema = {"$ref": body.schema_ref}
        elif body.schema_dict:
            schema = body.schema_dict
        else:
            schema = {"type": "object"}

        rb_dict: Dict[str, Any] = {
            "required": body.required,
            "content": {
                body.content_type: {
                    "schema": schema,
                }
            },
        }
        if body.description:
            rb_dict["description"] = body.description

        return rb_dict

    def _build_responses(
        self,
        ep: APIEndpoint,
        known_schemas: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], bool]:
        """Construct OpenAPI responses dictionary and flag if 422 error response was attached."""
        responses: Dict[str, Any] = {}
        uses_422 = False

        # Status code from endpoint or default
        status_code = "200"
        if ep.method == HTTPMethod.POST:
            status_code = "201"

        resp_model: Optional[ResponseModel] = None
        if ep.responses:
            for sc, rm in ep.responses.items():
                status_code = sc
                resp_model = rm
                break

        # Primary Response
        if status_code == "204":
            responses["204"] = {"description": "No Content"}
        else:
            schema = self._resolve_response_schema(resp_model, known_schemas)
            resp_dict: Dict[str, Any] = {
                "description": resp_model.description if resp_model else "Successful Response",
            }
            if schema:
                resp_dict["content"] = {
                    "application/json": {
                        "schema": schema,
                    }
                }
            responses[status_code] = resp_dict

        # Path parameter 404
        has_path_params = any(p.location == ParameterLocation.PATH for p in ep.parameters)
        if has_path_params:
            responses["404"] = {"description": "Not Found"}

        # Validation error 422 if parameters or request body exist
        has_query_or_body = any(p.location in (ParameterLocation.QUERY, ParameterLocation.PATH) for p in ep.parameters) or (ep.request_body is not None)
        if has_query_or_body:
            responses["422"] = {
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/HTTPValidationError"},
                    }
                },
            }
            uses_422 = True

        return responses, uses_422

    def _resolve_response_schema(
        self,
        resp_model: Optional[ResponseModel],
        known_schemas: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Resolve response schema, parsing generic List[T] and direct model references."""
        if not resp_model:
            return {"type": "object"}

        if resp_model.schema_dict:
            return resp_model.schema_dict

        schema_name = resp_model.schema_name or ""

        # Check for generic List[ModelName]
        list_match = re.match(r"(?:List|list)\[([a-zA-Z0-9_]+)\]", schema_name)
        if list_match:
            inner_name = list_match.group(1)
            if inner_name in known_schemas:
                return {
                    "type": "array",
                    "items": {"$ref": f"#/components/schemas/{inner_name}"},
                }
            primitive_type = {"str": "string", "int": "integer", "float": "number", "bool": "boolean"}.get(inner_name, "object")
            return {
                "type": "array",
                "items": {"type": primitive_type},
            }

        if schema_name in known_schemas:
            return {"$ref": f"#/components/schemas/{schema_name}"}

        # Check primitive type mapping
        if schema_name in ("str", "int", "float", "bool", "dict", "Any"):
            ptype = {"str": "string", "int": "integer", "float": "number", "bool": "boolean", "dict": "object"}.get(schema_name, "object")
            return {"type": ptype}

        return {"type": "object"}

    def to_json(self, result: ExtractionResult, indent: int = 2) -> str:
        """Serialize generated spec to deterministically ordered JSON."""
        spec_dict = self.generate(result)
        return json.dumps(spec_dict, indent=indent, ensure_ascii=False)

    def to_yaml(self, result: ExtractionResult) -> str:
        """Serialize generated spec to clean, deterministically ordered YAML."""
        spec_dict = self.generate(result)
        # sort_keys=False preserves our deterministic key hierarchy
        return yaml.dump(spec_dict, sort_keys=False, allow_unicode=True, default_flow_style=False)

