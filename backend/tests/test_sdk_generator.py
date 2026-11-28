"""Tests for TypeScript and Python SDK generation."""

import ast
import json
from pathlib import Path

from fastapi.testclient import TestClient

from speccraft.api.server import app
from speccraft.cli import run_cli
from speccraft.exporters import SDKGenerator

SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "expected_specs"


def test_generate_typescript_and_python_sdk_from_shop_v1(tmp_path: Path):
    spec = json.loads((SAMPLES_DIR / "shop_v1.json").read_text(encoding="utf-8"))
    gen = SDKGenerator()

    ts_files = gen.generate(spec, language="typescript")
    assert "client.ts" in ts_files
    ts_code = ts_files["client.ts"]
    assert "export class SpecCraftClient" in ts_code
    assert "export interface OrderCreate" in ts_code
    assert "fetch(" in ts_code

    py_files = gen.generate(spec, language="python")
    assert "client.py" in py_files
    py_code = py_files["client.py"]
    assert "class SpecCraftClient:" in py_code
    assert "class OrderCreate(BaseModel):" in py_code
    ast.parse(py_code)

    out_ts = tmp_path / "client.ts"
    assert run_cli(["sdk", str(SAMPLES_DIR / "shop_v1.json"), "--lang", "typescript", "--out", str(out_ts)]) == 0
    assert out_ts.exists()


def test_api_export_sdk_endpoint():
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "SDK API", "version": "1.0.0"},
        "paths": {
            "/users/{user_id}": {
                "get": {
                    "operationId": "get_user",
                    "parameters": [{"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
    client = TestClient(app)
    res = client.post("/api/export/sdk", json={"spec": spec, "language": "typescript"})
    assert res.status_code == 200
    assert "client.ts" in res.json()["files"]
    assert "getUser(user_id: number)" in res.json()["files"]["client.ts"]

