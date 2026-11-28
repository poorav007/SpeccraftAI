"""API routes for SpecCraft AI HTTP bridge.

Provides REST endpoints for codebase upload, static AST route extraction,
OpenAPI 3.0 generation, and specification validation.
"""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from speccraft.diff_engine import SpecDiffEngine
from speccraft.exporters import ExportManager, PostmanCollectionExporter
from speccraft.models import ExtractionResult
from speccraft.openapi_generator import OpenAPIGenerator
from speccraft.reader import ArchiveSecurityError
from speccraft.route_extractor import RouteExtractor
from speccraft.schema_validator import OpenAPISchemaValidator, ValidationReport
from speccraft.utils.path_safety import FileTooLargeError, PathSecurityError

api_router = APIRouter()


class CodeParseRequest(BaseModel):
    """Payload for direct code snippet extraction."""
    code: str = Field(..., description="Raw Python/FastAPI route code")
    filename: str = Field(default="main.py", description="Virtual file name for AST parsing")


class GenerateSpecRequest(BaseModel):
    """Request payload for OpenAPI 3.0 generation."""
    extraction_result: Optional[Dict[str, Any]] = Field(default=None, description="Extracted AST data")
    code: Optional[str] = Field(default=None, description="Direct code snippet if not pre-extracted")
    filename: Optional[str] = Field(default="main.py", description="Virtual filename if code provided")
    title: str = Field(default="SpecCraft API", description="API Title for OpenAPI info")
    version: str = Field(default="1.0.0", description="API Version")
    description: Optional[str] = Field(default=None, description="API Description")
    format: str = Field(default="json", description="Output format ('json' or 'yaml')")


class ValidateSpecRequest(BaseModel):
    """Request payload for OpenAPI 3.0 specification validation."""
    spec: Union[Dict[str, Any], str] = Field(..., description="OpenAPI specification as dictionary, JSON, or YAML string")


class DiffRequest(BaseModel):
    """Request payload for comparing two OpenAPI specifications."""
    baseline_spec: Union[Dict[str, Any], str] = Field(..., description="Baseline OpenAPI specification (S1)")
    target_spec: Union[Dict[str, Any], str] = Field(..., description="Target OpenAPI specification (S2)")


class ExportSpecRequest(BaseModel):
    """Request payload for exporting an OpenAPI specification to another format."""
    spec: Union[Dict[str, Any], str] = Field(..., description="OpenAPI 3.0 specification dictionary, JSON, or YAML string")
    validation_report: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional pre-computed validation report to include in bundle exports",
    )


@api_router.get("/health", summary="Health Check")
async def health_check() -> Dict[str, Any]:
    """Returns backend service health status, version, and supported framework capabilities."""
    return {
        "status": "healthy",
        "service": "speccraft-api-bridge",
        "version": "0.1.0",
        "supported_frameworks": ["fastapi", "express"],
        "capabilities": [
            "ast_extraction",
            "openapi_generation",
            "schema_validation",
            "postman_export",
        ],
    }


@api_router.post(
    "/parse",
    summary="Extract API Routes and Schemas",
    response_model=Dict[str, Any],
)
async def parse_codebase(
    file: Optional[UploadFile] = File(None),
    code: Optional[str] = Form(None),
    filename: Optional[str] = Form("main.py"),
) -> Dict[str, Any]:
    """Statically parse uploaded code or archive and return normalized routes and diagnostics.

    Supports multipart file upload (.zip archive or .py file) or form field 'code'.
    Never executes uploaded code — pure static AST analysis only.
    """
    extractor = RouteExtractor()

    # 1. Archive or file upload
    if file is not None:
        file_bytes = await file.read()
        fname = file.filename or "uploaded_file"

        try:
            if fname.lower().endswith(".zip"):
                result = extractor.extract_from_zip(file_bytes)
            else:
                code_str = file_bytes.decode("utf-8", errors="replace")
                result = extractor.extract_from_code_string(code_str, filename=fname)
        except ArchiveSecurityError as sec_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Archive rejected (Security Guard): {sec_err}",
            )
        except FileTooLargeError as size_err:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds size limit: {size_err}",
            )
        except Exception as ex:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse source: {ex}",
            )
    # 2. Raw code snippet passed in form
    elif code:
        result = extractor.extract_from_code_string(code, filename=filename or "main.py")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either an uploaded 'file' (.zip/.py) or 'code' parameter.",
        )

    # Reject if critical security error (Zip-Slip or archive limits) was flagged
    for d in result.diagnostics:
        if d.code.value == "SC-E002":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Archive rejected (Security Guard): {d.message}",
            )

    return result.model_dump()


@api_router.post(
    "/parse/json",
    summary="Parse Code from JSON body",
    response_model=Dict[str, Any],
)
async def parse_code_json(payload: CodeParseRequest) -> Dict[str, Any]:
    """Extract routes from a JSON body containing code string."""
    extractor = RouteExtractor()
    result = extractor.extract_from_code_string(payload.code, filename=payload.filename)
    return result.model_dump()


@api_router.post(
    "/generate",
    summary="Generate OpenAPI 3.0.3 Specification",
    response_model=Dict[str, Any],
)
async def generate_openapi_spec(payload: GenerateSpecRequest) -> Dict[str, Any]:
    """Generate OpenAPI 3.0.3 JSON or YAML specification from extracted routes or code."""
    extractor = RouteExtractor()

    if payload.extraction_result:
        try:
            extraction_res = ExtractionResult.model_validate(payload.extraction_result)
        except Exception as val_err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid extraction_result schema: {val_err}",
            )
    elif payload.code:
        extraction_res = extractor.extract_from_code_string(payload.code, filename=payload.filename or "main.py")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'extraction_result' or 'code' to generate OpenAPI specification.",
        )

    generator = OpenAPIGenerator(
        title=payload.title,
        version=payload.version,
        description=payload.description,
    )

    if payload.format.lower() == "yaml":
        spec_yaml = generator.to_yaml(extraction_res)
        return {
            "format": "yaml",
            "spec": spec_yaml,
        }
    else:
        spec_dict = generator.generate(extraction_res)
        return {
            "format": "json",
            "spec": spec_dict,
        }


@api_router.post(
    "/validate",
    summary="Validate OpenAPI Specification",
    response_model=Dict[str, Any],
)
async def validate_openapi_spec(payload: ValidateSpecRequest) -> Dict[str, Any]:
    """Validate an OpenAPI 3.0 specification for structure, $ref integrity, and path parameter parity."""
    validator = OpenAPISchemaValidator()
    report = validator.validate(payload.spec)
    return report.model_dump()


@api_router.post(
    "/diff",
    summary="Compare OpenAPI Specifications",
    response_model=Dict[str, Any],
)
async def diff_openapi_specs(payload: DiffRequest) -> Dict[str, Any]:
    """Compare baseline and target OpenAPI specifications and classify breaking vs non-breaking changes."""
    engine = SpecDiffEngine()
    try:
        report = engine.compare(payload.baseline_spec, payload.target_spec)
        return report.model_dump()
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to compare specifications: {ex}",
        )


@api_router.post(
    "/export/postman",
    summary="Convert OpenAPI to Postman Collection v2.1",
    response_model=Dict[str, Any],
)
async def export_postman_collection(payload: ExportSpecRequest) -> Dict[str, Any]:
    """Convert an OpenAPI 3.0 specification into a Postman Collection v2.1 JSON document."""
    exporter = PostmanCollectionExporter()
    try:
        return exporter.convert(payload.spec)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to export Postman collection: {ex}",
        )


@api_router.post(
    "/export/yaml",
    summary="Convert OpenAPI Specification to YAML",
    response_model=Dict[str, Any],
)
async def export_openapi_yaml(payload: ExportSpecRequest) -> Dict[str, Any]:
    """Serialize an OpenAPI 3.0 specification into clean YAML."""
    manager = ExportManager()
    try:
        return {"format": "yaml", "content": manager.to_openapi_yaml(payload.spec)}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to serialize YAML: {ex}",
        )


@api_router.post(
    "/export/bundle",
    summary="Download Complete API Documentation Bundle (.zip)",
)
async def export_documentation_bundle(payload: ExportSpecRequest) -> Response:
    """Package OpenAPI JSON/YAML, Postman v2.1 collection, and validation report into a ZIP."""
    manager = ExportManager()
    try:
        bundle_bytes = manager.export_bundle_zip(payload.spec, payload.validation_report)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate export bundle: {ex}",
        )

    return Response(
        content=bundle_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="speccraft-export-bundle.zip"'
        },
    )

