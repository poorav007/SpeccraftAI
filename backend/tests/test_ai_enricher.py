"""Unit and API integration tests for AI Documentation Assistant (F16)."""

import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from speccraft.ai import AIEnricherService
from speccraft.api.server import app


def _sample_endpoint() -> dict:
    return {
        "method": "post",
        "path": "/orders",
        "operation_id": "create_order",
        "tags": ["orders"],
        "parameters": [{"name": "dry_run", "location": "query", "param_type": "boolean", "required": False}],
        "request_body": {"content_type": "application/json", "schema_ref": "OrderCreate"},
    }


def test_offline_fallback_when_unconfigured(monkeypatch):
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    service = AIEnricherService()
    assert service.active_provider == "offline"

    ep = asyncio.run(service.enrich_endpoint_docs(_sample_endpoint()))
    assert ep.provider == "offline"
    assert ep.ast_facts_locked is True
    assert ep.summary
    assert "/orders" in ep.description

    field = asyncio.run(
        service.explain_schema_field(
            {
                "field_name": "customer_email",
                "field_type": "string",
                "location": "body",
                "required": True,
            }
        )
    )
    assert field.provider == "offline"
    assert field.field_name == "customer_email"
    assert "@" in str(field.example)


def test_gemini_json_mode_success():
    captured_request = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["headers"] = dict(request.headers)
        captured_request["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "summary": "Create customer order",
                                            "description": "Validates items and creates a new order.",
                                            "suggested_tags": ["orders", "checkout"],
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    service = AIEnricherService(
        ai_base_url="",
        api_key="test-gemini-key",
        model="gemini-2.5-flash",
        transport=httpx.MockTransport(handler),
    )
    assert service.active_provider == "gemini"

    proposal = asyncio.run(service.enrich_endpoint_docs(_sample_endpoint()))
    assert proposal.provider == "gemini"
    assert proposal.summary == "Create customer order"
    assert proposal.ast_facts_locked is True
    assert captured_request["headers"]["x-goog-api-key"] == "test-gemini-key"
    assert captured_request["body"]["generationConfig"]["responseMimeType"] == "application/json"


def test_local_ai_base_url_without_key_and_fenced_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://localhost:11434/v1/chat/completions"
        assert "authorization" not in request.headers
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '```json\n{"explanation": "Postal code for tax calculation.", "example": "94103"}\n```'
                        }
                    }
                ]
            },
        )

    service = AIEnricherService(
        ai_base_url="http://localhost:11434/v1",
        api_key="",
        model="llama3.2",
        transport=httpx.MockTransport(handler),
    )
    assert service.active_provider == "local"

    field_info = asyncio.run(
        service.explain_schema_field(
            {"field_name": "billing_zip", "field_type": "string", "required": True}
        )
    )
    assert field_info.provider == "local"
    assert "Postal code" in field_info.explanation
    assert field_info.example == "94103"


def test_http_error_and_invalid_json_fall_back_to_offline():
    def failing_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "upstream unavailable"})

    service = AIEnricherService(
        ai_base_url="",
        api_key="key",
        transport=httpx.MockTransport(failing_handler),
    )
    res = asyncio.run(service.enrich_endpoint_docs(_sample_endpoint()))
    assert res.provider == "offline"
    assert res.ast_facts_locked is True


def test_summarize_diff_caps_payload_prioritizes_breaking_and_builds_mobile_cards():
    changes = [
        {
            "change_type": "parameter_added",
            "path": f"/nonbreaking/{i}",
            "method": "get",
            "is_breaking": False,
            "description": f"Optional query param added {i}",
            "location": f"paths./nonbreaking/{i}.get",
            "old_value": None,
            "new_value": {"name": "filter"},
        }
        for i in range(60)
    ]
    changes.append(
        {
            "change_type": "endpoint_removed",
            "path": "/legacy/orders",
            "method": "delete",
            "is_breaking": True,
            "description": "Removed legacy order deletion endpoint.",
            "location": "paths./legacy/orders.delete",
            "old_value": {"summary": "Legacy delete"},
            "new_value": None,
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "executive_summary": "1 breaking removal and 60 optional updates.",
                                    "risk_level": "medium",
                                    "migration_steps": ["Stop calling DELETE /legacy/orders."],
                                    "card_impacts": ["Clients calling DELETE /legacy/orders will receive 404."],
                                }
                            )
                        }
                    }
                ]
            },
        )

    service = AIEnricherService(
        ai_base_url="http://localhost:11434/v1",
        transport=httpx.MockTransport(handler),
    )
    report = asyncio.run(
        service.summarize_diff(
            {"summary": {"total_changes": len(changes), "breaking_changes": 1}, "changes": changes}
        )
    )

    assert report.truncated is True
    assert report.provider == "local"
    assert report.risk_level == "medium"
    assert len(report.cards) == 50
    # Breaking change must be prioritized first
    first_card = report.cards[0]
    assert first_card.endpoint == "DELETE /legacy/orders"
    assert first_card.severity == "breaking"
    assert first_card.one_line_impact == "Clients calling DELETE /legacy/orders will receive 404."
    assert "Legacy delete" in first_card.before
    assert first_card.after == "none"


def test_api_ai_endpoints_offline_mode(monkeypatch):
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    client = TestClient(app)

    r1 = client.post("/api/ai/enrich-endpoint", json=_sample_endpoint())
    assert r1.status_code == 200
    assert r1.json()["provider"] == "offline"
    assert r1.json()["ast_facts_locked"] is True

    r2 = client.post(
        "/api/ai/explain-schema",
        json={"field_name": "price", "field_type": "number", "required": True},
    )
    assert r2.status_code == 200
    assert r2.json()["example"] == 19.99

    r3 = client.post(
        "/api/ai/summarize-diff",
        json={
            "summary": {"total_changes": 1, "breaking_changes": 1},
            "changes": [
                {
                    "change_type": "parameter_added",
                    "path": "/orders",
                    "method": "post",
                    "is_breaking": True,
                    "description": "Added required billing_zip",
                    "location": "paths./orders.post",
                    "old_value": None,
                    "new_value": {"name": "billing_zip", "required": True},
                }
            ],
        },
    )
    assert r3.status_code == 200
    body = r3.json()
    assert body["risk_level"] == "medium"
    assert len(body["cards"]) == 1
    assert body["cards"][0]["endpoint"] == "POST /orders"
    assert body["cards"][0]["severity"] == "breaking"

