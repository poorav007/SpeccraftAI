"""OpenAPI 3.0.3 specification validator for SpecCraft AI.

Performs static validation of generated OpenAPI specifications, checking structure,
$ref pointer integrity, path parameter consistency, status code formats, and schema compliance.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from pydantic import BaseModel, Field

# Recognized OpenAPI 3.0 HTTP methods
VALID_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}


class ValidationDiagnostic(BaseModel):
    """Represents a single validation error or warning."""

    code: str = Field(description="Unique validation error code, e.g. 'ERR_BROKEN_REF'")
    message: str = Field(description="Human-readable description of the error")
    path: str = Field(description="JSONPath-like location of the error, e.g. 'paths./items.get'")
    severity: str = Field(default="error", description="'error' or 'warning'")
    hint: Optional[str] = Field(default=None, description="Suggested resolution action")


class ValidationReport(BaseModel):
    """Summary report produced by OpenAPI specification validation."""

    is_valid: bool = Field(description="True if 0 errors were encountered")
    errors: List[ValidationDiagnostic] = Field(default_factory=list, description="Critical validation errors")
    warnings: List[ValidationDiagnostic] = Field(default_factory=list, description="Non-blocking warnings")
    stats: Dict[str, int] = Field(default_factory=dict, description="Specification metrics (paths, operations, schemas)")


class OpenAPISchemaValidator:
    """Validates OpenAPI 3.0.3 specifications against structural rules and schema standards."""

    def validate(self, spec: Union[Dict[str, Any], str]) -> ValidationReport:
        """Validate an OpenAPI specification dictionary or JSON/YAML string.

        Args:
            spec: OpenAPI spec as dictionary, JSON string, or YAML string.

        Returns:
            ValidationReport with is_valid, list of errors, warnings, and stats.
        """
        # Parse string input if needed
        spec_dict: Dict[str, Any]
        if isinstance(spec, str):
            try:
                spec_dict = json.loads(spec)
            except Exception:
                try:
                    spec_dict = yaml.safe_load(spec)
                except Exception as ex:
                    return ValidationReport(
                        is_valid=False,
                        errors=[
                            ValidationDiagnostic(
                                code="ERR_PARSE_FAILED",
                                message=f"Failed to parse specification string as JSON or YAML: {ex}",
                                path="$",
                            )
                        ],
                    )
        else:
            spec_dict = spec

        errors: List[ValidationDiagnostic] = []
        warnings: List[ValidationDiagnostic] = []

        # 1. Structural checks
        self._check_top_level_structure(spec_dict, errors)

        # 2. Extract schemas and check $ref integrity
        schemas = spec_dict.get("components", {}).get("schemas", {}) if isinstance(spec_dict.get("components"), dict) else {}
        self._check_ref_pointers(spec_dict, schemas, errors)

        # 3. Path parameter consistency & operations
        operation_ids: Set[str] = set()
        paths_count = 0
        operations_count = 0

        paths_obj = spec_dict.get("paths")
        if isinstance(paths_obj, dict):
            paths_count = len(paths_obj)
            for path_str, path_item in paths_obj.items():
                if not isinstance(path_item, dict):
                    errors.append(
                        ValidationDiagnostic(
                            code="ERR_INVALID_PATH_ITEM",
                            message=f"Path item '{path_str}' must be an object.",
                            path=f"paths.{path_str}",
                        )
                    )
                    continue

                path_tokens = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", path_str))

                for method_str, op in path_item.items():
                    # Skip parameters defined at path level
                    if method_str == "parameters":
                        continue

                    if method_str.lower() not in VALID_METHODS:
                        errors.append(
                            ValidationDiagnostic(
                                code="ERR_INVALID_HTTP_METHOD",
                                message=f"Invalid HTTP method '{method_str}' under path '{path_str}'.",
                                path=f"paths.{path_str}.{method_str}",
                                hint=f"Use one of: {', '.join(sorted(VALID_METHODS))}",
                            )
                        )
                        continue

                    operations_count += 1
                    op_path = f"paths.{path_str}.{method_str}"

                    if not isinstance(op, dict):
                        errors.append(
                            ValidationDiagnostic(
                                code="ERR_INVALID_OPERATION",
                                message=f"Operation for '{method_str.upper()} {path_str}' must be an object.",
                                path=op_path,
                            )
                        )
                        continue

                    # Check duplicate operationId
                    op_id = op.get("operationId")
                    if op_id:
                        if op_id in operation_ids:
                            errors.append(
                                ValidationDiagnostic(
                                    code="ERR_DUPLICATE_OPERATION_ID",
                                    message=f"Duplicate operationId '{op_id}' detected at '{op_path}'.",
                                    path=f"{op_path}.operationId",
                                    hint="Ensure all operations have unique operationIds.",
                                )
                            )
                        else:
                            operation_ids.add(op_id)

                    # Check path parameter parity
                    params = op.get("parameters", [])
                    declared_path_params: Set[str] = set()
                    if isinstance(params, list):
                        for p_idx, p in enumerate(params):
                            if isinstance(p, dict) and p.get("in") == "path":
                                p_name = p.get("name")
                                if p_name:
                                    declared_path_params.add(p_name)
                                    if not p.get("required"):
                                        errors.append(
                                            ValidationDiagnostic(
                                                code="ERR_PATH_PARAM_NOT_REQUIRED",
                                                message=f"Path parameter '{p_name}' must have required=true.",
                                                path=f"{op_path}.parameters[{p_idx}]",
                                                hint="Set 'required: true' for all path parameters.",
                                            )
                                        )

                    # Verify every token in URL path is declared
                    for token in path_tokens:
                        if token not in declared_path_params:
                            errors.append(
                                ValidationDiagnostic(
                                    code="ERR_MISSING_PATH_PARAM",
                                    message=f"Path template parameter '{{{token}}}' has no matching parameter definition.",
                                    path=op_path,
                                    hint=f"Add a parameter with name='{token}' and in='path'.",
                                )
                            )

                    # Check responses
                    responses = op.get("responses")
                    if not responses or not isinstance(responses, dict):
                        errors.append(
                            ValidationDiagnostic(
                                code="ERR_MISSING_RESPONSES",
                                message=f"Operation '{op_path}' must have a non-empty 'responses' object.",
                                path=f"{op_path}.responses",
                            )
                        )
                    else:
                        for sc_str in responses.keys():
                            if sc_str != "default" and not (sc_str.isdigit() and len(sc_str) == 3):
                                errors.append(
                                    ValidationDiagnostic(
                                        code="ERR_INVALID_STATUS_CODE",
                                        message=f"Status code '{sc_str}' is not a valid 3-digit HTTP status or 'default'.",
                                        path=f"{op_path}.responses.{sc_str}",
                                    )
                                )

        # Stats
        stats = {
            "paths_count": paths_count,
            "operations_count": operations_count,
            "schemas_count": len(schemas) if isinstance(schemas, dict) else 0,
        }

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats,
        )

    def _check_top_level_structure(self, spec: Dict[str, Any], errors: List[ValidationDiagnostic]) -> None:
        """Validate required top-level OpenAPI 3.0 fields."""
        # 1. openapi version
        openapi_ver = spec.get("openapi")
        if not openapi_ver:
            errors.append(
                ValidationDiagnostic(
                    code="ERR_MISSING_FIELD",
                    message="Missing required top-level field 'openapi'.",
                    path="openapi",
                    hint="Set openapi: '3.0.3'",
                )
            )
        elif not str(openapi_ver).startswith("3.0."):
            errors.append(
                ValidationDiagnostic(
                    code="ERR_INVALID_VERSION",
                    message=f"Unsupported OpenAPI version '{openapi_ver}'; expected '3.0.x'.",
                    path="openapi",
                    hint="Use OpenAPI version '3.0.3'.",
                )
            )

        # 2. info object
        info = spec.get("info")
        if not info or not isinstance(info, dict):
            errors.append(
                ValidationDiagnostic(
                    code="ERR_MISSING_FIELD",
                    message="Missing required top-level object 'info'.",
                    path="info",
                    hint="Include an 'info' object with 'title' and 'version'.",
                )
            )
        else:
            if not info.get("title"):
                errors.append(
                    ValidationDiagnostic(
                        code="ERR_MISSING_FIELD",
                        message="Missing required field 'info.title'.",
                        path="info.title",
                    )
                )
            if not info.get("version"):
                errors.append(
                    ValidationDiagnostic(
                        code="ERR_MISSING_FIELD",
                        message="Missing required field 'info.version'.",
                        path="info.version",
                    )
                )

        # 3. paths object
        if "paths" not in spec or not isinstance(spec.get("paths"), dict):
            errors.append(
                ValidationDiagnostic(
                    code="ERR_MISSING_FIELD",
                    message="Missing required top-level object 'paths'.",
                    path="paths",
                    hint="Include a 'paths' dictionary mapping routes to operations.",
                )
            )

    def _check_ref_pointers(
        self,
        node: Any,
        known_schemas: Dict[str, Any],
        errors: List[ValidationDiagnostic],
        current_path: str = "$",
    ) -> None:
        """Recursively search for $ref pointers and verify target schemas exist."""
        if isinstance(node, dict):
            if "$ref" in node and isinstance(node["$ref"], str):
                ref_val = node["$ref"]
                if ref_val.startswith("#/components/schemas/"):
                    target_name = ref_val.replace("#/components/schemas/", "")
                    if target_name not in known_schemas:
                        errors.append(
                            ValidationDiagnostic(
                                code="ERR_BROKEN_REF",
                                message=f"Unresolved reference '{ref_val}': schema '{target_name}' not found in components.schemas.",
                                path=current_path,
                                hint=f"Ensure schema '{target_name}' is declared in components.schemas.",
                            )
                        )
            for k, v in node.items():
                self._check_ref_pointers(v, known_schemas, errors, f"{current_path}.{k}")
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                self._check_ref_pointers(item, known_schemas, errors, f"{current_path}[{idx}]")

