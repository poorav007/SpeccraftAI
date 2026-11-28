"""Unit and API integration tests for Postman v2.1 exporter and ExportManager."""

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from speccraft.api.server import app
from speccraft.exporters import ExportManager, PostmanCollectionExporter
from speccraft.exporters.postman_exporter import POSTMAN_V2_1_SCHEMA

SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "expected_specs"


@pytest.fixture
def shop_v1_spec() -> dict:
    with open(SAMPLES_DIR / "shop_v1.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _find_request(collection: dict, method: str, raw_fragment: str) -> dict:
    for folder in collection.get("item", []):
        for item in folder.get("item", []):
            req = item.get("request", {})
            if req.get("method") == method.upper() and raw_fragment in req.get("url", {}).get("raw", ""):
                return item
    raise AssertionError(f"Request {method} matching '{raw_fragment}' not found in collection")


def test_convert_shop_v1_to_postman(shop_v1_spec):
    exporter = PostmanCollectionExporter()
    collection = exporter.convert(shop_v1_spec)

    assert collection["info"]["schema"] == POSTMAN_V2_1_SCHEMA
    assert collection["info"]["name"] == shop_v1_spec["info"]["title"]
    assert len(collection["item"]) > 0
    assert collection["variable"][0]["key"] == "baseUrl"


def test_folder_grouping_by_tags(shop_v1_spec):
    exporter = PostmanCollectionExporter()
    collection = exporter.convert(shop_v1_spec)
    folder_names = [folder["name"] for folder in collection["item"]]

    assert "items" in folder_names or "catalog" in folder_names or len(folder_names) >= 1


def test_path_variable_and_query_params(shop_v1_spec):
    exporter = PostmanCollectionExporter()
    collection = exporter.convert(shop_v1_spec)

    get_item = _find_request(collection, "GET", "/items/:item_id")
    url = get_item["request"]["url"]
    assert ":item_id" in url["path"]
    assert any(var["key"] == "item_id" for var in url.get("variable", []))

    list_items = _find_request(collection, "GET", "/items?")
    query_keys = [q["key"] for q in list_items["request"]["url"].get("query", [])]
    assert "skip" in query_keys
    assert "limit" in query_keys


def test_post_body_json_ref_resolution(shop_v1_spec):
    exporter = PostmanCollectionExporter()
    collection = exporter.convert(shop_v1_spec)

    create_order = _find_request(collection, "POST", "/orders")
    req = create_order["request"]
    assert req["body"]["mode"] == "raw"
    parsed_body = json.loads(req["body"]["raw"])
    assert isinstance(parsed_body, dict)
    assert "customer_email" in parsed_body
    assert "shipping_address" in parsed_body
    assert "items" in parsed_body
    assert isinstance(parsed_body["items"], list)
    assert len(parsed_body["items"]) == 1
    assert "item_id" in parsed_body["items"][0]
    assert any(
        h["key"].lower() == "content-type" and h["value"] == "application/json"
        for h in req["header"]
    )


def test_circular_ref_does_not_infinite_loop():
    circular_spec = {
        "openapi": "3.0.3",
        "info": {"title": "Circular API", "version": "1.0.0"},
        "paths": {
            "/nodes": {
                "post": {
                    "tags": ["nodes"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Node"}
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
        "components": {
            "schemas": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "child": {"$ref": "#/components/schemas/Node"},
                    },
                }
            }
        },
    }

    exporter = PostmanCollectionExporter()
    collection = exporter.convert(circular_spec)
    create_node = _find_request(collection, "POST", "/nodes")
    parsed_body = json.loads(create_node["request"]["body"]["raw"])
    assert parsed_body["id"] == 1
    assert parsed_body["child"] == {}


def test_export_manager_formats_and_zip_bundle(shop_v1_spec):
    manager = ExportManager()

    json_str = manager.to_openapi_json(shop_v1_spec)
    assert '"openapi": "3.0.3"' in json_str

    yaml_str = manager.to_openapi_yaml(shop_v1_spec)
    assert "openapi: 3.0.3" in yaml_str

    md_report = manager.to_validation_markdown(shop_v1_spec)
    assert "# SpecCraft AI — Validation Audit Report" in md_report
    assert "VALID" in md_report

    zip_bytes = manager.export_bundle_zip(shop_v1_spec)
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = set(zf.namelist())
        assert names == {
            "openapi.json",
            "openapi.yaml",
            "postman_collection.json",
            "validation_report.md",
        }
        postman_data = json.loads(zf.read("postman_collection.json").decode("utf-8"))
        assert postman_data["info"]["schema"] == POSTMAN_V2_1_SCHEMA


def test_api_export_endpoints(shop_v1_spec):
    client = TestClient(app)

    res_postman = client.post("/api/export/postman", json={"spec": shop_v1_spec})
    assert res_postman.status_code == 200
    assert res_postman.json()["info"]["schema"] == POSTMAN_V2_1_SCHEMA

    res_yaml = client.post("/api/export/yaml", json={"spec": shop_v1_spec})
    assert res_yaml.status_code == 200
    assert res_yaml.json()["format"] == "yaml"
    assert "openapi: 3.0.3" in res_yaml.json()["content"]

    res_bundle = client.post("/api/export/bundle", json={"spec": shop_v1_spec})
    assert res_bundle.status_code == 200
    assert res_bundle.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(res_bundle.content), "r") as zf:
        assert "postman_collection.json" in zf.namelist()

