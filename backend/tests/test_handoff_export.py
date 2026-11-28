"""Unit and API tests for white-label @media print Client Handoff HTML/PDF export."""

from fastapi.testclient import TestClient

from speccraft.api.server import app
from speccraft.exporters import ExportManager


def test_handoff_html_escapes_xss_and_includes_brand_and_print_media():
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": 'Shop & <API>',
            "version": "2.0.0",
            "description": '<script>alert("xss")</script> Safe docs',
        },
        "paths": {
            "/orders": {
                "post": {
                    "summary": 'Create <Order> & "Pay"',
                    "description": '<img src=x onerror=alert(1)>',
                    "tags": ["orders<script>"],
                    "parameters": [
                        {"name": "dry_run<x>", "in": "query", "required": False}
                    ],
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
        "components": {
            "schemas": {
                "Order": {
                    "type": "object",
                    "properties": {"total": {"type": "number"}},
                }
            }
        },
    }

    manager = ExportManager()
    html_out = manager.to_handoff_html(spec, brand_name='Acme & <Partners>')

    assert "Acme &amp; &lt;Partners&gt;" in html_out
    assert "Shop &amp; &lt;API&gt;" in html_out
    assert "<script>alert" not in html_out
    assert "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;" in html_out
    assert "&lt;img src=x onerror=alert(1)&gt;" in html_out
    assert "@media print" in html_out
    assert "page-break-inside: avoid" in html_out


def test_api_export_handoff_html_endpoint():
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Agency Spec", "version": "1.0.0"},
        "paths": {
            "/ping": {
                "get": {
                    "summary": "Ping",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    client = TestClient(app)
    res = client.post(
        "/api/export/handoff-html",
        json={"spec": spec, "brand_name": "Northstar Studio"},
    )
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Northstar Studio" in res.text
    assert "@media print" in res.text

