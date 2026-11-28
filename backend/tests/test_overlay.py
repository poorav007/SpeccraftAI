"""Unit and integration tests for non-destructive speccraft.overlay.json persistence."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from speccraft.api.server import app
from speccraft.overlay import OverlayEntry, OverlayStore
from speccraft.route_extractor import RouteExtractor


def test_overlay_saves_alphabetically_and_preserves_docs_across_reparse(tmp_path: Path):
    overlay_file = tmp_path / "speccraft.overlay.json"
    store = OverlayStore(overlay_path=overlay_file)

    # Save Z before A to verify alphabetical key sorting on disk
    store.upsert_entry(
        "POST",
        "/orders",
        OverlayEntry(
            summary="AI Approved Order Summary",
            description="Creates an order with full inventory check.",
            tags=["checkout"],
            source="ai-accepted",
        ),
    )
    store.upsert_entry(
        "GET",
        "/health",
        OverlayEntry(summary="Health Probe", source="human"),
    )

    raw_json = json.loads(overlay_file.read_text(encoding="utf-8"))
    assert list(raw_json["entries"].keys()) == ["GET /health", "POST /orders"]

    # Re-parse updated Python code with a newly added query parameter
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def check_health():
    return {"ok": True}

@app.post("/orders")
def make_order(priority: bool = False):
    return {"priority": priority}
'''
    extracted = RouteExtractor().extract_from_code_string(code, filename="main.py")
    merged = store.apply_to_extraction_result(extracted)

    assert merged.orphaned_overlay_keys == []
    orders_ep = next(ep for ep in merged.endpoints if ep.path == "/orders")
    # Documentation came from overlay, while new AST parameter & method stay accurate
    assert orders_ep.summary == "AI Approved Order Summary"
    assert orders_ep.description == "Creates an order with full inventory check."
    assert orders_ep.tags == ["checkout"]
    assert orders_ep.enrichment_metadata["overlay_source"] == "ai-accepted"
    assert any(p.name == "priority" for p in orders_ep.parameters)


def test_overlay_detects_orphaned_keys_when_route_renamed_or_deleted(tmp_path: Path, monkeypatch):
    overlay_file = tmp_path / "speccraft.overlay.json"
    monkeypatch.setenv("SPECCRAFT_OVERLAY_PATH", str(overlay_file))

    client = TestClient(app)

    # Save overlay for POST /orders
    put_res = client.put(
        "/api/overlay/entry",
        json={
            "method": "post",
            "path": "/orders",
            "summary": "Create Order",
            "source": "human",
        },
    )
    assert put_res.status_code == 200
    assert put_res.json()["key"] == "POST /orders"

    # Parse updated codebase where POST /orders was renamed to POST /v2/orders
    renamed_code = '''
from fastapi import FastAPI
app = FastAPI()

@app.post("/v2/orders")
def create_order_v2():
    return {"ok": True}
'''
    parse_res = client.post("/api/parse/json", json={"code": renamed_code, "filename": "main.py"})
    assert parse_res.status_code == 200
    body = parse_res.json()
    assert body["orphaned_overlay_keys"] == ["POST /orders"]

    # Delete orphaned entry via API
    del_res = client.delete("/api/overlay/entry", params={"key": "POST /orders"})
    assert del_res.status_code == 200
    assert del_res.json()["overlay"]["entries"] == {}

