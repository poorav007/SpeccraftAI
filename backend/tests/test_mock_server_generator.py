"""Tests for standalone FastAPI Mock API Server generation."""

import ast
import json
from pathlib import Path

from fastapi.testclient import TestClient

from speccraft.api.server import app
from speccraft.cli import run_cli
from speccraft.exporters import MockServerGenerator

SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "expected_specs"


def test_mock_server_generates_valid_python_syntax(tmp_path: Path):
    spec = json.loads((SAMPLES_DIR / "shop_v1.json").read_text(encoding="utf-8"))
    code = MockServerGenerator().to_fastapi_mock_code(spec)

    ast.parse(code)
    assert "app = FastAPI(" in code
    assert "@app.get('/items'" in code
    assert "@app.post('/orders'" in code

    out_mock = tmp_path / "mock_server.py"
    assert run_cli(["mock", str(SAMPLES_DIR / "shop_v1.json"), "--out", str(out_mock)]) == 0
    assert out_mock.exists()


def test_api_export_mock_server_endpoint():
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Mock Demo", "version": "1.0.0"},
        "paths": {
            "/ping": {
                "get": {
                    "operationId": "ping",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"ok": {"type": "boolean"}},
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }
    client = TestClient(app)
    res = client.post("/api/export/mock-server", json={"spec": spec})
    assert res.status_code == 200
    body = res.json()
    assert body["filename"] == "mock_server.py"
    ast.parse(body["code"])
    assert "{'ok': True}" in body["code"]

