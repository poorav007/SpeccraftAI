"""Core data models for SpecCraft AI static AST analysis pipeline.

These models represent the internal intermediate representation (IR) extracted
from source code before being transformed into OpenAPI 3.0 specifications.
Designed following mentor Stretch PRD specifications with extension slots for
future AI enrichers without rewriting internal interfaces.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from speccraft.diagnostics import Diagnostic


class HTTPMethod(str, Enum):
    """Supported HTTP request methods."""
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"
    PATCH = "patch"
    OPTIONS = "options"
    HEAD = "head"


class ParameterLocation(str, Enum):
    """OpenAPI 3.0 parameter locations."""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"


class ParameterModel(BaseModel):
    """Represents an extracted path, query, header, or cookie parameter."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(description="Parameter name as used in code or path")
    location: ParameterLocation = Field(
        default=ParameterLocation.QUERY,
        alias="in",
        description="Location of the parameter (path, query, header, cookie)",
    )
    required: bool = Field(default=False, description="Whether parameter is required")
    param_type: str = Field(default="string", description="Primitive data type")
    description: Optional[str] = Field(default=None, description="Extracted parameter docstring or description")
    default: Optional[Any] = Field(default=None, description="Default value if not provided")
    example: Optional[Any] = Field(default=None, description="Example value")
    schema_dict: Optional[Dict[str, Any]] = Field(default=None, description="Full JSON Schema dictionary if complex")


class RequestBodyModel(BaseModel):
    """Represents an extracted HTTP request body and schema."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    content_type: str = Field(default="application/json", description="MIME content type")
    schema_ref: Optional[str] = Field(default=None, description="OpenAPI reference, e.g. '#/components/schemas/Item'")
    schema_name: Optional[str] = Field(default=None, description="Model class name, e.g. 'ItemCreate'")
    schema_dict: Optional[Dict[str, Any]] = Field(default=None, description="Inlined JSON Schema definition")
    required: bool = Field(default=True, description="Whether request body is required")
    description: Optional[str] = Field(default=None, description="Description or docstring of request payload")


class ResponseModel(BaseModel):
    """Represents an extracted HTTP response specification."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    status_code: str = Field(default="200", description="HTTP status code (e.g. '200', '201', '404')")
    description: str = Field(default="Successful Response", description="Response description")
    content_type: str = Field(default="application/json", description="MIME content type")
    schema_ref: Optional[str] = Field(default=None, description="OpenAPI reference, e.g. '#/components/schemas/Item'")
    schema_name: Optional[str] = Field(default=None, description="Response model class name")
    schema_dict: Optional[Dict[str, Any]] = Field(default=None, description="Inlined JSON Schema definition")


class APIEndpoint(BaseModel):
    """Core intermediate representation of a single extracted API route.

    Contains full route metadata extracted statically via Python AST analysis,
    with an 'enrichment_metadata' slot for future AI/enricher plugins.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    path: str = Field(description="URL path template, e.g. '/api/v1/items/{item_id}'")
    method: HTTPMethod = Field(description="HTTP method in lowercase")
    operation_id: Optional[str] = Field(default=None, description="Unique operation ID derived from handler function")
    summary: Optional[str] = Field(default=None, description="Short human-readable summary of the route")
    description: Optional[str] = Field(default=None, description="Full route description or docstring")
    tags: List[str] = Field(default_factory=list, description="Categorization tags (e.g. ['items', 'catalog'])")
    parameters: List[ParameterModel] = Field(default_factory=list, description="List of path/query/header parameters")
    request_body: Optional[RequestBodyModel] = Field(default=None, description="Extracted request body model")
    responses: Dict[str, ResponseModel] = Field(default_factory=dict, description="Mapped status codes to responses")
    deprecated: bool = Field(default=False, description="Whether route is flagged as deprecated")
    source_file: str = Field(description="Relative path of file containing the route handler")
    line_number: int = Field(default=1, description="Line number of handler definition in source file")
    enrichment_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extension hook for AI enricher, custom tags, or manual overrides",
    )


class SourceFile(BaseModel):
    """Represents a safely read source code file."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    relative_path: str = Field(description="Sanitized relative path within the scanned repository")
    absolute_path: Optional[str] = Field(default=None, description="Absolute system path")
    content: str = Field(description="Full text content of the source file")
    loc: int = Field(default=0, description="Lines of code count")


class ExtractionWarning(BaseModel):
    """Non-fatal warning encountered during AST parsing or metadata mapping."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    file: str = Field(description="Source file where warning occurred")
    line: Optional[int] = Field(default=None, description="Line number if known")
    code: str = Field(description="Machine-readable warning code, e.g. 'UNRESOLVED_TYPE'")
    message: str = Field(description="Actionable explanation of the warning")


class ExtractionResult(BaseModel):
    """Aggregate result returned by the AST parsing pipeline."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    endpoints: List[APIEndpoint] = Field(default_factory=list, description="Extracted API endpoints")
    schemas: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Extracted Pydantic models converted to JSON Schema dictionaries",
    )
    warnings: List[ExtractionWarning] = Field(default_factory=list, description="Non-fatal parsing warnings")
    diagnostics: List[Diagnostic] = Field(
        default_factory=list, description="Formal PRD Section 8 diagnostics (SC-W001 to SC-E002)"
    )
    files_scanned: int = Field(default=0, description="Total count of files parsed")
    total_loc: int = Field(default=0, description="Total lines of code scanned across all files")
    parse_duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")


class ChangeType(str, Enum):
    """Classification of OpenAPI specification changes."""
    ENDPOINT_ADDED = "endpoint_added"
    ENDPOINT_REMOVED = "endpoint_removed"
    PARAMETER_ADDED = "parameter_added"
    PARAMETER_REMOVED = "parameter_removed"
    PARAMETER_MODIFIED = "parameter_modified"
    REQUEST_BODY_MODIFIED = "request_body_modified"
    RESPONSE_CODE_ADDED = "response_code_added"
    RESPONSE_CODE_REMOVED = "response_code_removed"
    METADATA_MODIFIED = "metadata_modified"


class DiffChangeRecord(BaseModel):
    """Represents a single detected difference between two OpenAPI specifications."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    change_type: ChangeType = Field(description="Machine-readable change category")
    path: str = Field(description="Endpoint URL path")
    method: str = Field(description="HTTP method (e.g. 'get', 'post')")
    is_breaking: bool = Field(description="True if change breaks backward compatibility for API consumers")
    description: str = Field(description="Human-readable explanation of the change")
    location: str = Field(description="JSON pointer or structural path in specification")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed before/after metadata")


class DiffSummary(BaseModel):
    """Aggregate statistics for a specification diff comparison."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    total_changes: int = 0
    breaking_changes: int = 0
    non_breaking_changes: int = 0
    added_endpoints: int = 0
    removed_endpoints: int = 0
    modified_endpoints: int = 0


class DiffReport(BaseModel):
    """Full report returned by the SpecDiffEngine."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    summary: DiffSummary = Field(default_factory=DiffSummary)
    changes: List[DiffChangeRecord] = Field(default_factory=list)


