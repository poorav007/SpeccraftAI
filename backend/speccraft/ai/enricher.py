"""Production-safe AI Documentation Assistant for SpecCraft AI.

Supports:
- Local / Air-Gapped OpenAI-compatible or Ollama servers via AI_BASE_URL
- Google Gemini native JSON mode via AI_API_KEY / GEMINI_API_KEY
- Deterministic OfflineFallbackEnricher when unconfigured or on any error

Pure AST facts (path, method, parameter names, types) are strictly immutable
and never altered by AI suggestions.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, TypeVar

import httpx
from pydantic import BaseModel, Field, ValidationError

from speccraft.ai.prompts import (
    build_diff_summary_prompt,
    build_endpoint_docs_prompt,
    build_schema_field_prompt,
)

ProviderMode = Literal["gemini", "local", "offline"]
TModel = TypeVar("TModel", bound=BaseModel)

DEFAULT_TIMEOUT_SECONDS = 12.0
MAX_DIFF_CHANGES_FOR_LLM = 50
MAX_DIFF_CONTEXT_CHARS = 16000
MAX_MOBILE_CARDS = 50


class EnrichedEndpointProposal(BaseModel):
    """Proposed documentation metadata for a single API endpoint."""

    summary: str
    description: str
    suggested_tags: List[str] = Field(default_factory=list)
    provider: ProviderMode = "offline"
    ast_facts_locked: bool = True


class SchemaFieldExplanation(BaseModel):
    """Plain-language explanation and example for a parameter or schema attribute."""

    field_name: str
    explanation: str
    example: Any
    provider: ProviderMode = "offline"


class DiffChangeCard(BaseModel):
    """Mobile-ready swipe review card derived deterministically from DiffChangeRecord."""

    endpoint: str
    severity: Literal["breaking", "non_breaking"]
    one_line_impact: str
    before: str
    after: str


class DiffSummaryProposal(BaseModel):
    """Executive diff summary plus mobile-ready cards array."""

    executive_summary: str
    risk_level: Literal["low", "medium", "high"]
    migration_steps: List[str] = Field(default_factory=list)
    cards: List[DiffChangeCard] = Field(default_factory=list)
    truncated: bool = False
    provider: ProviderMode = "offline"


class _LLMEndpointJSON(BaseModel):
    summary: str = Field(..., min_length=1, max_length=140)
    description: str = Field(..., min_length=1, max_length=1500)
    suggested_tags: List[str] = Field(default_factory=list)


class _LLMFieldJSON(BaseModel):
    explanation: str = Field(..., min_length=1, max_length=800)
    example: Any = None


class _LLMDiffJSON(BaseModel):
    executive_summary: str = Field(..., min_length=1, max_length=1500)
    risk_level: Literal["low", "medium", "high"] = "low"
    migration_steps: List[str] = Field(default_factory=list)
    card_impacts: List[str] = Field(default_factory=list)


def _strip_json_fences(raw_text: str) -> str:
    """Remove optional markdown ```json fences emitted by local models."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _humanize_identifier(name: str) -> str:
    """Turn snake_case / camelCase / path segments into readable words."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name or "")
    spaced = spaced.replace("_", " ").replace("-", " ").strip()
    return spaced or "resource"


def _format_value_preview(val: Any) -> str:
    """Format a compact deterministic string for before/after card slots."""
    if val is None or val == "":
        return "none"
    if isinstance(val, (dict, list)):
        text = json.dumps(val, ensure_ascii=False)
        return text if len(text) <= 140 else f"{text[:137]}..."
    text = str(val)
    return text if len(text) <= 140 else f"{text[:137]}..."


def _extract_before_after(change: Dict[str, Any]) -> Tuple[str, str]:
    """Derive deterministic before/after strings from DiffChangeRecord variants."""
    if "old_value" in change or "new_value" in change:
        return (
            _format_value_preview(change.get("old_value")),
            _format_value_preview(change.get("new_value")),
        )

    details = change.get("details") or {}
    if isinstance(details, dict):
        if "old" in details or "new" in details:
            return (
                _format_value_preview(details.get("old")),
                _format_value_preview(details.get("new")),
            )
        if "old_type" in details or "new_type" in details:
            return (
                _format_value_preview(details.get("old_type")),
                _format_value_preview(details.get("new_type")),
            )
        if "old_required" in details or "new_required" in details:
            return (
                f"required={details.get('old_required')}",
                f"required={details.get('new_required')}",
            )

    change_type = str(change.get("change_type") or "")
    if "added" in change_type:
        return "not present", _format_value_preview(change.get("location") or "added")
    if "removed" in change_type:
        return _format_value_preview(change.get("location") or "present"), "removed"
    return "previous spec", "updated spec"


def _cap_diff_changes(
    changes: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], bool]:
    """Prioritize breaking changes and cap diff items & serialized size for LLM safety."""
    prioritized = sorted(
        changes,
        key=lambda c: (0 if c.get("is_breaking") else 1, str(c.get("path", ""))),
    )

    capped: List[Dict[str, Any]] = []
    running_chars = 0
    truncated = len(prioritized) > MAX_DIFF_CHANGES_FOR_LLM

    for item in prioritized[:MAX_DIFF_CHANGES_FOR_LLM]:
        serialized_len = len(json.dumps(item, default=str))
        if capped and (running_chars + serialized_len) > MAX_DIFF_CONTEXT_CHARS:
            truncated = True
            break
        capped.append(item)
        running_chars += serialized_len

    return capped, truncated


class OfflineFallbackEnricher:
    """Deterministic heuristic documentation generator (zero external calls)."""

    def enrich_endpoint_docs(self, endpoint_data: Dict[str, Any]) -> EnrichedEndpointProposal:
        method = str(endpoint_data.get("method") or "get").upper()
        path = str(endpoint_data.get("path") or "/")
        op_id = str(endpoint_data.get("operation_id") or "")
        existing_desc = str(endpoint_data.get("description") or "").strip()
        existing_summary = str(endpoint_data.get("summary") or "").strip()
        existing_tags = [str(t) for t in (endpoint_data.get("tags") or []) if t]

        segments = [s for s in path.strip("/").split("/") if s and not s.startswith("{")]
        resource = _humanize_identifier(segments[-1] if segments else "root")

        action_verb = {
            "GET": "Retrieve" if "{" in path else "List",
            "POST": "Create",
            "PUT": "Replace",
            "PATCH": "Update",
            "DELETE": "Delete",
        }.get(method, "Handle")

        summary = existing_summary or (
            _humanize_identifier(op_id).title() if op_id else f"{action_verb} {resource}"
        )
        summary = summary[:60]

        params = endpoint_data.get("parameters") or []
        param_names = [str(p.get("name")) for p in params if p.get("name")]
        param_clause = (
            f" Accepts parameters: {', '.join(param_names)}."
            if param_names
            else ""
        )
        body_clause = (
            " Expects a validated JSON request payload."
            if endpoint_data.get("request_body")
            else ""
        )

        description = existing_desc or (
            f"{action_verb} `{path}` via `{method}`.{param_clause}{body_clause}"
        )

        suggested_tags = existing_tags or ([segments[0]] if segments else ["general"])

        return EnrichedEndpointProposal(
            summary=summary,
            description=description,
            suggested_tags=suggested_tags,
            provider="offline",
            ast_facts_locked=True,
        )

    def explain_schema_field(self, field_data: Dict[str, Any]) -> SchemaFieldExplanation:
        field_name = str(field_data.get("field_name") or "field")
        field_type = str(field_data.get("field_type") or "string").lower()
        location = str(field_data.get("location") or "body")
        required = bool(field_data.get("required", False))
        existing_desc = str(field_data.get("existing_description") or "").strip()

        readable = _humanize_identifier(field_name)
        req_text = "Required" if required else "Optional"
        explanation = existing_desc or (
            f"{req_text} {location} field representing the {readable} ({field_type})."
        )

        example: Any = f"sample_{field_name}"
        if "int" in field_type:
            example = 1
        elif "float" in field_type or "number" in field_type:
            example = 19.99
        elif "bool" in field_type:
            example = True
        elif "list" in field_type or "array" in field_type:
            example = ["example_item"]
        elif "email" in field_name.lower():
            example = "user@example.com"

        return SchemaFieldExplanation(
            field_name=field_name,
            explanation=explanation,
            example=example,
            provider="offline",
        )

    def summarize_diff(
        self,
        summary_stats: Dict[str, Any],
        capped_changes: List[Dict[str, Any]],
        truncated: bool,
    ) -> DiffSummaryProposal:
        total = int(summary_stats.get("total_changes", len(capped_changes)))
        breaking = int(
            summary_stats.get(
                "breaking_changes",
                sum(1 for c in capped_changes if c.get("is_breaking")),
            )
        )
        non_breaking = max(0, total - breaking)

        if breaking > 0:
            risk_level: Literal["low", "medium", "high"] = "high" if breaking >= 3 else "medium"
            exec_summary = (
                f"Detected {total} API changes including {breaking} breaking change(s) "
                f"and {non_breaking} non-breaking update(s). Consumer coordination is required."
            )
            migration_steps = [
                f"Review breaking change on {c.get('method', '').upper()} {c.get('path', '/')}: "
                f"{c.get('description', '')}"
                for c in capped_changes
                if c.get("is_breaking")
            ][:5]
        elif total > 0:
            risk_level = "low"
            exec_summary = (
                f"Detected {total} non-breaking API change(s). Backward compatibility is preserved."
            )
            migration_steps = ["No breaking client updates required; regenerate SDKs if desired."]
        else:
            risk_level = "low"
            exec_summary = "No specification differences detected between baseline and target."
            migration_steps = []

        cards = _build_deterministic_cards(capped_changes, card_impacts=None)
        return DiffSummaryProposal(
            executive_summary=exec_summary,
            risk_level=risk_level,
            migration_steps=migration_steps,
            cards=cards,
            truncated=truncated,
            provider="offline",
        )


def _build_deterministic_cards(
    capped_changes: List[Dict[str, Any]],
    card_impacts: Optional[List[str]] = None,
) -> List[DiffChangeCard]:
    """Build mobile swipe cards with AST/diff-locked endpoint, severity, before, and after."""
    cards: List[DiffChangeCard] = []
    for idx, change in enumerate(capped_changes[:MAX_MOBILE_CARDS]):
        method = str(change.get("method") or "").upper()
        path = str(change.get("path") or "/")
        endpoint = f"{method} {path}".strip()
        severity: Literal["breaking", "non_breaking"] = (
            "breaking" if change.get("is_breaking") else "non_breaking"
        )
        before, after = _extract_before_after(change)

        ai_impact = ""
        if card_impacts and idx < len(card_impacts) and card_impacts[idx]:
            ai_impact = str(card_impacts[idx]).strip()
        one_line = ai_impact or str(change.get("description") or f"{severity} change on {endpoint}")

        cards.append(
            DiffChangeCard(
                endpoint=endpoint,
                severity=severity,
                one_line_impact=one_line,
                before=before,
                after=after,
            )
        )
    return cards


class AIEnricherService:
    """Production-safe AI enrichment orchestrator with Gemini, Local, and Offline modes."""

    def __init__(
        self,
        ai_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        ai_provider: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.ai_base_url = (
            ai_base_url if ai_base_url is not None else os.getenv("AI_BASE_URL", "")
        ).strip()
        self.api_key = (
            api_key
            if api_key is not None
            else (os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or "")
        ).strip()
        self.ai_provider_hint = (
            ai_provider if ai_provider is not None else os.getenv("AI_PROVIDER", "")
        ).strip().lower()
        self.model = (model if model is not None else os.getenv("AI_MODEL", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self._offline = OfflineFallbackEnricher()

    @property
    def active_provider(self) -> ProviderMode:
        """Select provider deterministically: Local (AI_BASE_URL) -> Gemini -> Offline."""
        if self.ai_base_url and self.ai_provider_hint != "gemini":
            return "local"
        if self.api_key:
            return "gemini"
        return "offline"

    async def enrich_endpoint_docs(
        self, endpoint_data: Dict[str, Any]
    ) -> EnrichedEndpointProposal:
        """Generate documentation proposal for an endpoint, falling back cleanly offline."""
        provider = self.active_provider
        if provider == "offline":
            return self._offline.enrich_endpoint_docs(endpoint_data)

        system_prompt, user_prompt = build_endpoint_docs_prompt(endpoint_data)
        parsed = await self._call_llm_json(provider, system_prompt, user_prompt, _LLMEndpointJSON)
        if parsed is None:
            return self._offline.enrich_endpoint_docs(endpoint_data)

        return EnrichedEndpointProposal(
            summary=parsed.summary,
            description=parsed.description,
            suggested_tags=parsed.suggested_tags or list(endpoint_data.get("tags") or []),
            provider=provider,
            ast_facts_locked=True,
        )

    async def explain_schema_field(
        self, field_data: Dict[str, Any]
    ) -> SchemaFieldExplanation:
        """Generate plain-language field explanation, falling back cleanly offline."""
        provider = self.active_provider
        if provider == "offline":
            return self._offline.explain_schema_field(field_data)

        system_prompt, user_prompt = build_schema_field_prompt(field_data)
        parsed = await self._call_llm_json(provider, system_prompt, user_prompt, _LLMFieldJSON)
        if parsed is None:
            return self._offline.explain_schema_field(field_data)

        return SchemaFieldExplanation(
            field_name=str(field_data.get("field_name") or "field"),
            explanation=parsed.explanation,
            example=parsed.example if parsed.example is not None else "sample_value",
            provider=provider,
        )

    async def summarize_diff(self, diff_report: Dict[str, Any]) -> DiffSummaryProposal:
        """Summarize spec diffs with capped context and mobile-ready cards array."""
        changes = list(diff_report.get("changes") or [])
        summary_stats = dict(diff_report.get("summary") or {})
        capped_changes, truncated = _cap_diff_changes(changes)

        provider = self.active_provider
        if provider == "offline" or not capped_changes:
            proposal = self._offline.summarize_diff(summary_stats, capped_changes, truncated)
            if provider != "offline" and not capped_changes:
                proposal.provider = provider
            return proposal

        system_prompt, user_prompt = build_diff_summary_prompt(
            summary_stats, capped_changes, truncated
        )
        parsed = await self._call_llm_json(provider, system_prompt, user_prompt, _LLMDiffJSON)
        if parsed is None:
            return self._offline.summarize_diff(summary_stats, capped_changes, truncated)

        cards = _build_deterministic_cards(capped_changes, card_impacts=parsed.card_impacts)
        return DiffSummaryProposal(
            executive_summary=parsed.executive_summary,
            risk_level=parsed.risk_level,
            migration_steps=parsed.migration_steps,
            cards=cards,
            truncated=truncated,
            provider=provider,
        )

    async def _call_llm_json(
        self,
        provider: ProviderMode,
        system_prompt: str,
        user_prompt: str,
        schema_cls: Type[TModel],
    ) -> Optional[TModel]:
        """Call Gemini or Local AI_BASE_URL using httpx.AsyncClient with safe JSON validation."""
        client_kwargs: Dict[str, Any] = {"timeout": self.timeout_seconds}
        if self.transport is not None:
            client_kwargs["transport"] = self.transport

        try:
            async with httpx.AsyncClient(**client_kwargs) as client:
                if provider == "local":
                    raw_content = await self._request_openai_compatible(
                        client, system_prompt, user_prompt
                    )
                else:
                    raw_content = await self._request_gemini(
                        client, system_prompt, user_prompt
                    )
            if not raw_content:
                return None
            payload = json.loads(_strip_json_fences(raw_content))
            return schema_cls.model_validate(payload)
        except (httpx.HTTPError, json.JSONDecodeError, ValidationError, KeyError, ValueError):
            return None

    async def _request_gemini(
        self,
        client: httpx.AsyncClient,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        model = self.model or "gemini-2.5-flash"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        return str(data["candidates"][0]["content"]["parts"][0]["text"])

    async def _request_openai_compatible(
        self,
        client: httpx.AsyncClient,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        base = self.ai_base_url.rstrip("/")
        url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body: Dict[str, Any] = {
            "model": self.model or "llama3.2",
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"])


def get_enricher_service() -> AIEnricherService:
    """Create a fresh environment-configured AIEnricherService instance."""
    return AIEnricherService()

