"""Unit and integration tests for SpecCraft AI FastAPI HTTP bridge."""

import io
import unittest
import zipfile
from starlette.testclient import TestClient

from speccraft.api.server import app


class TestAPIServer(unittest.TestCase):
    """Test suite verifying FastAPI endpoints for parsing, generation, and validation."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("/api/health", data["endpoints"]["health"])

    def test_health_check_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("fastapi", data["supported_frameworks"])

    def test_parse_code_snippet_json(self):
        code = """
from fastapi import FastAPI
app = FastAPI()

@app.get('/users/{user_id}')
def get_user(user_id: int):
    '''Fetch user details.'''
    return {'id': user_id}
"""
        response = self.client.post(
            "/api/parse/json",
            json={"code": code, "filename": "users.py"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["endpoints"]), 1)
        endpoint = data["endpoints"][0]
        self.assertEqual(endpoint["path"], "/users/{user_id}")
        self.assertEqual(endpoint["method"], "get")
        self.assertEqual(endpoint["operation_id"], "get_user")
        self.assertEqual(data["files_scanned"], 1)

    def test_parse_code_snippet_multipart_form(self):
        code = """
from fastapi import FastAPI
app = FastAPI()

@app.post('/items', status_code=201)
def create_item(name: str):
    return {'name': name}
"""
        response = self.client.post(
            "/api/parse",
            data={"code": code, "filename": "items.py"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["endpoints"]), 1)
        self.assertEqual(data["endpoints"][0]["path"], "/items")
        self.assertEqual(data["endpoints"][0]["method"], "post")

    def test_parse_zip_upload(self):
        # Create an in-memory zip archive with FastAPI code
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr(
                "main.py",
                "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/ping')\ndef ping(): return {'msg': 'pong'}",
            )
        zip_buf.seek(0)

        response = self.client.post(
            "/api/parse",
            files={"file": ("project.zip", zip_buf, "application/zip")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data["endpoints"]), 1)
        self.assertEqual(data["endpoints"][0]["path"], "/ping")
        self.assertEqual(data["endpoints"][0]["operation_id"], "ping")

    def test_generate_spec_endpoint(self):
        code = """
from fastapi import FastAPI
app = FastAPI()

@app.get('/health')
def health(): return {'status': 'ok'}
"""
        # Test JSON format
        resp_json = self.client.post(
            "/api/generate",
            json={
                "code": code,
                "title": "Generated API",
                "version": "2.0.0",
                "format": "json",
            },
        )
        self.assertEqual(resp_json.status_code, 200)
        json_data = resp_json.json()
        self.assertEqual(json_data["format"], "json")
        spec = json_data["spec"]
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertEqual(spec["info"]["title"], "Generated API")
        self.assertIn("/health", spec["paths"])

        # Test YAML format
        resp_yaml = self.client.post(
            "/api/generate",
            json={
                "code": code,
                "title": "YAML Spec",
                "format": "yaml",
            },
        )
        self.assertEqual(resp_yaml.status_code, 200)
        yaml_data = resp_yaml.json()
        self.assertEqual(yaml_data["format"], "yaml")
        self.assertIn("openapi: 3.0.3", yaml_data["spec"])

    def test_validate_spec_endpoint(self):
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Valid API", "version": "1.0.0"},
            "paths": {
                "/ping": {
                    "get": {
                        "operationId": "ping",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        response = self.client.post(
            "/api/validate",
            json={"spec": spec},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_valid"])
        self.assertEqual(len(data["errors"]), 0)

    def test_zip_slip_rejected_over_api(self):
        # Create malicious zip with traversal path
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("../../etc/malicious.py", "x = 1")
        zip_buf.seek(0)

        response = self.client.post(
            "/api/parse",
            files={"file": ("exploit.zip", zip_buf, "application/zip")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Security Guard", response.json()["detail"])


    def test_diff_spec_endpoint(self):
        s1 = {
            "openapi": "3.0.3",
            "paths": {
                "/users/{id}": {
                    "delete": {"operationId": "delete_user", "responses": {"204": {"description": "OK"}}}
                }
            },
        }
        s2 = {
            "openapi": "3.0.3",
            "paths": {
                "/users": {
                    "get": {"operationId": "list_users", "responses": {"200": {"description": "OK"}}}
                }
            },
        }

        response = self.client.post(
            "/api/diff",
            json={"baseline_spec": s1, "target_spec": s2},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        summary = data["summary"]
        self.assertEqual(summary["total_changes"], 2)
        self.assertEqual(summary["breaking_changes"], 1)  # deleted endpoint is breaking
        self.assertEqual(summary["non_breaking_changes"], 1)  # added endpoint is non-breaking
        self.assertEqual(summary["removed_endpoints"], 1)
        self.assertEqual(summary["added_endpoints"], 1)


if __name__ == "__main__":
    unittest.main()

