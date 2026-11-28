"""API routes for SpecCraft AI HTTP bridge.

Provides REST endpoints for codebase upload, static AST route extraction,
OpenAPI 3.0 generation, and specification validation.
"""

from __future__ import annotations

import io
import json
import os
import re
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from speccraft.ai import get_enricher_service
from speccraft.diff_engine import SpecDiffEngine
from speccraft.exporters import (
    ExportManager,
    MockServerGenerator,
    PostmanCollectionExporter,
    SDKGenerator,
)
from speccraft.models import ExtractionResult
from speccraft.openapi_generator import OpenAPIGenerator
from speccraft.overlay import OverlayEntry, get_overlay_store, make_overlay_key
from speccraft.reader import MAX_ARCHIVE_SIZE_BYTES, ArchiveSecurityError
from speccraft.route_extractor import RouteExtractor
from speccraft.schema_validator import OpenAPISchemaValidator, ValidationReport
from speccraft.utils.path_safety import FileTooLargeError, PathSecurityError

api_router = APIRouter()


class CodeParseRequest(BaseModel):
    """Payload for direct code snippet extraction."""
    code: str = Field(..., description="Raw Python/FastAPI route code")
    filename: str = Field(default="main.py", description="Virtual file name for AST parsing")


class GitHubParseRequest(BaseModel):
    """Payload for fetching and parsing a public GitHub repository."""
    repo_url: str = Field(..., description="Public GitHub repo URL, e.g. https://github.com/owner/repo")
    ref: Optional[str] = Field(default=None, description="Optional branch, tag, or commit ref")


class GitHubPRReviewRequest(BaseModel):
    """Payload for posting Mobile Approve/Block decisions back to a GitHub Pull Request."""
    owner: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    pr_number: int = Field(..., ge=1)
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    summary_note: Optional[str] = Field(default=None)
    github_token: Optional[str] = Field(default=None)


_GITHUB_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def parse_github_repo_url(repo_url: str, explicit_ref: Optional[str] = None) -> Tuple[str, str, Optional[str]]:
    """Validate and extract (owner, repo, ref) from a GitHub HTTPS URL (prevents SSRF)."""
    parsed = urlparse(str(repo_url or "").strip())
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {"github.com", "www.github.com"}:
        raise ValueError("URL must be a public https://github.com/<owner>/<repo> URL.")

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError("URL must include both owner and repository name.")

    owner = parts[0]
    repo = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    if not _GITHUB_SEGMENT_RE.match(owner) or not _GITHUB_SEGMENT_RE.match(repo):
        raise ValueError("Invalid GitHub owner or repository characters.")

    ref = (explicit_ref or "").strip() or None
    if ref is None and len(parts) >= 4 and parts[2] == "tree":
        ref = "/".join(parts[3:])
    return owner, repo, ref


def format_pr_review_markdown(
    decisions: List[Dict[str, Any]],
    summary_note: Optional[str] = None,
) -> str:
    """Format mobile swipe Approve/Block decisions into a clean GitHub PR comment."""
    approved = sum(1 for d in decisions if str(d.get("decision")).lower() == "approved")
    blocked = sum(1 for d in decisions if str(d.get("decision")).lower() == "blocked")
    status_line = "🚨 **API Review Blocked**" if blocked > 0 else "✅ **API Changes Approved**"

    lines = [
        f"## SpecCraft AI — Mobile Spec Review",
        "",
        f"{status_line} · **Approved**: `{approved}` | **Blocked**: `{blocked}`",
        "",
    ]
    if summary_note:
        lines.extend([summary_note, ""])
    if decisions:
        lines.extend(
            [
                "| Decision | Endpoint | Severity | Impact |",
                "| :--- | :--- | :--- | :--- |",
            ]
        )
        for item in decisions:
            dec = "🚨 BLOCKED" if str(item.get("decision")).lower() == "blocked" else "✅ APPROVED"
            ep = str(item.get("endpoint") or "/")
            sev = str(item.get("severity") or "non_breaking").upper()
            imp = str(item.get("one_line_impact") or "").replace("|", "\\|")
            lines.append(f"| {dec} | `{ep}` | `{sev}` | {imp} |")
        lines.append("")
    return "\n".join(lines)


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
    brand_name: str = Field(
        default="SpecCraft AI",
        description="Optional client or agency brand name for white-label handoff exports",
    )


class ExportSDKRequest(BaseModel):
    """Request payload for generating TypeScript or Python client SDKs."""
    spec: Union[Dict[str, Any], str] = Field(..., description="OpenAPI 3.0 specification")
    language: Literal["typescript", "python"] = Field(default="typescript")


class OverlayUpsertRequest(BaseModel):
    """Request payload for saving non-destructive endpoint documentation."""
    method: str = Field(..., description="HTTP method (used in METHOD /path key)")
    path: str = Field(..., description="Endpoint path template (used in METHOD /path key)")
    operation_id: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    source: str = Field(default="human", description="'human' or 'ai-accepted'")


class EnrichEndpointRequest(BaseModel):
    """Request payload for AI endpoint documentation enrichment."""
    method: str = Field(..., description="HTTP method (immutable AST fact)")
    path: str = Field(..., description="Endpoint path template (immutable AST fact)")
    operation_id: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = Field(default=None)


class ExplainSchemaFieldRequest(BaseModel):
    """Request payload for plain-language explanation of a schema/parameter field."""
    field_name: str = Field(..., description="Field or parameter name")
    field_type: str = Field(default="string", description="Data type")
    location: str = Field(default="body", description="Parameter or body location")
    required: bool = Field(default=False)
    endpoint_path: str = Field(default="")
    endpoint_method: str = Field(default="")
    existing_description: Optional[str] = Field(default=None)


class SummarizeDiffRequest(BaseModel):
    """Request payload for AI diff summarization and mobile card generation."""
    summary: Dict[str, Any] = Field(default_factory=dict)
    changes: List[Dict[str, Any]] = Field(default_factory=list)


@api_router.get("/health", summary="Health Check")
async def health_check() -> Dict[str, Any]:
    """Returns backend service health status, version, and supported framework capabilities."""
    return {
        "status": "healthy",
        "service": "speccraft-api-bridge",
        "version": "0.1.0",
        "supported_frameworks": ["fastapi", "flask", "express"],
        "capabilities": [
            "ast_extraction",
            "openapi_generation",
            "schema_validation",
            "postman_export",
            "ai_enrichment",
            "sdk_generation",
            "mock_server_generation",
            "incremental_caching",
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

    result = get_overlay_store().apply_to_extraction_result(result)
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
    result = get_overlay_store().apply_to_extraction_result(result)
    return result.model_dump()


@api_router.post(
    "/parse/github",
    summary="Fetch & Parse Public GitHub Repository",
    response_model=Dict[str, Any],
)
async def parse_github_repo(payload: GitHubParseRequest) -> Dict[str, Any]:
    """Safely download a public GitHub repo archive (<=10MB) and run static analysis."""
    try:
        owner, repo, ref = parse_github_repo_url(payload.repo_url, payload.ref)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    if ref:
        zip_url = f"{zip_url}/{ref}"

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "SpecCraft-AI"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(zip_url, headers=headers)
    except httpx.HTTPError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download GitHub repository: {err}",
        )

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GitHub repository '{owner}/{repo}' (or branch '{ref or 'default'}') was not found or is private.",
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API returned HTTP {resp.status_code}.",
        )
    if len(resp.content) > MAX_ARCHIVE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Repository archive exceeds 10 MB limit ({len(resp.content)} bytes).",
        )

    result = RouteExtractor().extract_from_zip(resp.content)
    for d in result.diagnostics:
        if d.code.value == "SC-E002":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=d.message)

    result = get_overlay_store().apply_to_extraction_result(result)
    return result.model_dump()


@api_router.post(
    "/github/pr-review",
    summary="Post Mobile Approve/Block Decisions to a GitHub Pull Request",
    response_model=Dict[str, Any],
)
async def post_github_pr_review(payload: GitHubPRReviewRequest) -> Dict[str, Any]:
    """Post formatted Markdown Approve/Block summary back to a GitHub PR comment thread."""
    if not _GITHUB_SEGMENT_RE.match(payload.owner) or not _GITHUB_SEGMENT_RE.match(payload.repo):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid owner or repo name.")

    comment_md = format_pr_review_markdown(payload.decisions, payload.summary_note)
    token = (payload.github_token or os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        return {
            "posted": False,
            "reason": "Missing GITHUB_TOKEN (preview generated safely without posting).",
            "comment_markdown": comment_md,
        }

    url = f"https://api.github.com/repos/{payload.owner}/{payload.repo}/issues/{payload.pr_number}/comments"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "SpecCraft-AI",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, headers=headers, json={"body": comment_md})
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub PR comment failed (HTTP {resp.status_code}): {resp.text[:200]}",
            )
        data = resp.json()
        return {
            "posted": True,
            "comment_url": data.get("html_url"),
            "comment_markdown": comment_md,
        }
    except httpx.HTTPError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to contact GitHub API: {err}",
        )


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


@api_router.post(
    "/ai/enrich-endpoint",
    summary="Suggest OpenAPI Endpoint Documentation with AI",
    response_model=Dict[str, Any],
)
async def ai_enrich_endpoint(payload: EnrichEndpointRequest) -> Dict[str, Any]:
    """Generate human-reviewable summary, description, and tag suggestions without altering AST facts."""
    service = get_enricher_service()
    proposal = await service.enrich_endpoint_docs(payload.model_dump())
    return proposal.model_dump()


@api_router.post(
    "/ai/explain-schema",
    summary="Explain a Schema Field or Parameter with AI",
    response_model=Dict[str, Any],
)
async def ai_explain_schema_field(payload: ExplainSchemaFieldRequest) -> Dict[str, Any]:
    """Generate a plain-language explanation and example value for a field."""
    service = get_enricher_service()
    explanation = await service.explain_schema_field(payload.model_dump())
    return explanation.model_dump()


@api_router.post(
    "/ai/summarize-diff",
    summary="Summarize OpenAPI Spec Changes & Generate Mobile Review Cards",
    response_model=Dict[str, Any],
)
async def ai_summarize_diff(payload: SummarizeDiffRequest) -> Dict[str, Any]:
    """Generate an executive diff summary plus mobile-ready cards array with payload size caps."""
    service = get_enricher_service()
    summary = await service.summarize_diff(payload.model_dump())
    return summary.model_dump()


@api_router.post(
    "/export/handoff-html",
    summary="Generate White-Label Printable Client Handoff Report (HTML/PDF)",
)
async def export_handoff_html(payload: ExportSpecRequest) -> Response:
    """Generate a self-contained @media print HTML client handoff report with XSS escaping."""
    manager = ExportManager()
    try:
        html_doc = manager.to_handoff_html(
            payload.spec,
            validation_report=payload.validation_report,
            brand_name=payload.brand_name,
        )
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate handoff HTML: {ex}",
        )

    return Response(
        content=html_doc,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="client-api-handoff.html"'
        },
    )


@api_router.get(
    "/overlay",
    summary="Read Saved Non-Destructive Documentation Overlay",
    response_model=Dict[str, Any],
)
async def get_overlay() -> Dict[str, Any]:
    """Return all saved entries from speccraft.overlay.json."""
    return get_overlay_store().load().model_dump()


@api_router.put(
    "/overlay/entry",
    summary="Save Documentation Override for a Route",
    response_model=Dict[str, Any],
)
async def upsert_overlay_entry(payload: OverlayUpsertRequest) -> Dict[str, Any]:
    """Persist human-edited or AI-accepted docs keyed by METHOD /path."""
    source_val = "ai-accepted" if payload.source == "ai-accepted" else "human"
    entry = OverlayEntry(
        operation_id=payload.operation_id,
        summary=payload.summary,
        description=payload.description,
        tags=payload.tags,
        source=source_val,
    )
    doc = get_overlay_store().upsert_entry(payload.method, payload.path, entry)
    return {
        "key": make_overlay_key(payload.method, payload.path),
        "overlay": doc.model_dump(),
    }


@api_router.delete(
    "/overlay/entry",
    summary="Remove an Orphaned or Stale Overlay Entry",
    response_model=Dict[str, Any],
)
async def delete_overlay_entry(key: str) -> Dict[str, Any]:
    """Delete an overlay entry by canonical key (`METHOD /path`)."""
    doc = get_overlay_store().delete_entry(key)
    return {"deleted_key": key, "overlay": doc.model_dump()}


@api_router.post(
    "/export/sdk",
    summary="Generate TypeScript or Python API Client SDK",
    response_model=Dict[str, Any],
)
async def export_sdk_code(payload: ExportSDKRequest) -> Dict[str, Any]:
    """Generate a typed TypeScript or Python client SDK from an OpenAPI specification."""
    generator = SDKGenerator()
    try:
        files = generator.generate(payload.spec, language=payload.language)
        return {"language": payload.language, "files": files}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate SDK: {ex}",
        )


@api_router.post(
    "/export/mock-server",
    summary="Generate Standalone FastAPI Mock API Server",
    response_model=Dict[str, Any],
)
async def export_mock_server(payload: ExportSpecRequest) -> Dict[str, Any]:
    """Generate a runnable mock_server.py from an OpenAPI specification."""
    generator = MockServerGenerator()
    try:
        code = generator.to_fastapi_mock_code(payload.spec)
        return {"filename": "mock_server.py", "code": code}
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate mock server: {ex}",
        )

