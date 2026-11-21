"""SpecCraft AI formal diagnostics and warnings catalog.

Implements PRD Section 8 error codes (SC-W001 to SC-E002) with the standard
PRD copy pattern: what failed, why, and what to do next.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class DiagnosticSeverity(str, Enum):
    """Severity levels for pipeline diagnostics."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DiagnosticCode(str, Enum):
    """Official PRD Section 8 Diagnostic Codes."""
    # Warnings (Non-fatal, extraction continues)
    SC_W001 = "SC-W001"  # Route path is not a literal; route skipped
    SC_W002 = "SC-W002"  # Router prefix or include target could not be resolved
    SC_W003 = "SC-W003"  # Unsupported registration (add_api_route, mount)
    SC_W004 = "SC-W004"  # Parameter has no annotation; assumed string
    SC_W005 = "SC-W005"  # Depends not expanded; parameters may be missing
    SC_W006 = "SC-W006"  # Response schema not declared
    SC_W007 = "SC-W007"  # Model reference unresolved; empty schema used
    SC_W008 = "SC-W008"  # File failed to parse; skipped

    # Errors (Fatal for project/archive)
    SC_E001 = "SC-E001"  # Unsupported framework
    SC_E002 = "SC-E002"  # Archive rejected (size, count, traversal)


# Standard PRD descriptions and actionable hints following the PRD copy pattern
DIAGNOSTIC_CATALOG: Dict[DiagnosticCode, Dict[str, str]] = {
    DiagnosticCode.SC_W001: {
        "title": "Non-Literal Route Path",
        "description": "Route path expression is dynamic or computed at runtime (e.g. f-string or variable).",
        "hint": "Replace dynamic path expressions with string literals like '/api/v1/items/{id}'.",
    },
    DiagnosticCode.SC_W002: {
        "title": "Unresolved Router Prefix",
        "description": "The prefix or target of APIRouter / include_router could not be resolved statically.",
        "hint": "Define APIRouter prefixes with literal strings (e.g. prefix='/items').",
    },
    DiagnosticCode.SC_W003: {
        "title": "Unsupported Route Registration",
        "description": "Route was registered using add_api_route() or app.mount() instead of decorators.",
        "hint": "Use standard route decorators like @app.get() or @router.post().",
    },
    DiagnosticCode.SC_W004: {
        "title": "Unannotated Parameter",
        "description": "A route parameter does not have a Python type annotation.",
        "hint": "Add a type annotation (e.g. item_id: int) so OpenAPI schema types can be inferred.",
    },
    DiagnosticCode.SC_W005: {
        "title": "Unexpanded Dependency",
        "description": "FastAPI Depends(...) was detected but not expanded into query/header parameters.",
        "hint": "Dependencies are recorded without inlining internal parameters into OpenAPI specs.",
    },
    DiagnosticCode.SC_W006: {
        "title": "Undeclared Response Schema",
        "description": "Route does not specify a response_model or return type annotation.",
        "hint": "Add response_model=MyModel or a return type annotation to document output schemas.",
    },
    DiagnosticCode.SC_W007: {
        "title": "Unresolved Model Reference",
        "description": "The referenced Pydantic model could not be found in the scanned files.",
        "hint": "Ensure the model is defined in a scanned Python file inheriting from BaseModel.",
    },
    DiagnosticCode.SC_W008: {
        "title": "Syntax Error in Source File",
        "description": "File failed Python AST parsing due to invalid syntax; file was skipped.",
        "hint": "Check the indicated line in your file and correct the Python syntax error.",
    },
    DiagnosticCode.SC_E001: {
        "title": "Unsupported Framework",
        "description": "No FastAPI imports were detected in the uploaded project.",
        "hint": "Ensure your project imports 'fastapi' or select the sample project to get started.",
    },
    DiagnosticCode.SC_E002: {
        "title": "Archive Rejected",
        "description": "Uploaded archive exceeded size caps, file count limits, or attempted path traversal.",
        "hint": "Ensure the archive is under 10MB, has <2000 files, and contains no '../' traversal paths.",
    },
}


class Diagnostic(BaseModel):
    """Structured diagnostic representation following PRD Section 8."""
    model_config = ConfigDict(populate_by_name=True)

    code: DiagnosticCode = Field(description="Standardized code, e.g. SC-W001")
    severity: DiagnosticSeverity = Field(default=DiagnosticSeverity.WARNING)
    message: str = Field(description="Contextual explanation of what failed")
    file: str = Field(description="Relative path of file where diagnostic occurred")
    line: Optional[int] = Field(default=None, description="Line number if known")
    hint: Optional[str] = Field(default=None, description="Actionable recommendation on how to fix")

    @classmethod
    def create(
        cls,
        code: DiagnosticCode,
        file: str,
        line: Optional[int] = None,
        custom_message: Optional[str] = None,
        custom_hint: Optional[str] = None,
    ) -> Diagnostic:
        """Factory helper creating a diagnostic pre-filled from the PRD catalog."""
        info = DIAGNOSTIC_CATALOG.get(code, {})
        severity = DiagnosticSeverity.ERROR if code.value.startswith("SC-E") else DiagnosticSeverity.WARNING
        message = custom_message or f"{info.get('title', code.value)}: {info.get('description', '')}"
        hint = custom_hint or info.get("hint")
        return cls(
            code=code,
            severity=severity,
            message=message,
            file=file,
            line=line,
            hint=hint,
        )

    def format_terminal(self) -> str:
        """Format as human-readable terminal line."""
        loc = f"{self.file}:{self.line}" if self.line else self.file
        return f"[{self.severity.value.upper()}] {self.code.value} at {loc}: {self.message} (Hint: {self.hint})"
