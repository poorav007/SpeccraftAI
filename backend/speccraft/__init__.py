"""SpecCraft AI — Automated API documentation and OpenAPI 3.0 specification generator.

Static AST parser, schema extractor, validator, and spec diff engine.
"""

__version__ = "0.1.0"

from speccraft.diagnostics import (
    DIAGNOSTIC_CATALOG,
    Diagnostic,
    DiagnosticCode,
    DiagnosticSeverity,
)
from speccraft.metadata_mapper import (
    map_and_normalize_endpoints,
    normalize_route_path,
    resolve_operation_id,
)
from speccraft.models import (
    APIEndpoint,
    ExtractionResult,
    ExtractionWarning,
    HTTPMethod,
    ParameterLocation,
    ParameterModel,
    RequestBodyModel,
    ResponseModel,
    SourceFile,
)
from speccraft.openapi_generator import OpenAPIGenerator
from speccraft.reader import SourceFileReader
from speccraft.route_extractor import RouteExtractor
from speccraft.schema_validator import (
    OpenAPISchemaValidator,
    ValidationDiagnostic,
    ValidationReport,
)

__all__ = [
    "__version__",
    "APIEndpoint",
    "DIAGNOSTIC_CATALOG",
    "Diagnostic",
    "DiagnosticCode",
    "DiagnosticSeverity",
    "ExtractionResult",
    "ExtractionWarning",
    "HTTPMethod",
    "OpenAPIGenerator",
    "OpenAPISchemaValidator",
    "ParameterLocation",
    "ParameterModel",
    "RequestBodyModel",
    "ResponseModel",
    "RouteExtractor",
    "SourceFile",
    "SourceFileReader",
    "ValidationDiagnostic",
    "ValidationReport",
    "map_and_normalize_endpoints",
    "normalize_route_path",
    "resolve_operation_id",
]

