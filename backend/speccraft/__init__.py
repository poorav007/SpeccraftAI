"""SpecCraft AI — Automated API documentation and OpenAPI 3.0 specification generator.

Static AST parser, schema extractor, validator, and spec diff engine.
"""

__version__ = "0.1.0"

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
from speccraft.reader import SourceFileReader

__all__ = [
    "__version__",
    "APIEndpoint",
    "ExtractionResult",
    "ExtractionWarning",
    "HTTPMethod",
    "ParameterLocation",
    "ParameterModel",
    "RequestBodyModel",
    "ResponseModel",
    "SourceFile",
    "SourceFileReader",
]

