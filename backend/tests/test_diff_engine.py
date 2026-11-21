"""Unit tests for SpecCraft AI OpenAPI Specification Diff Engine."""

import json
from pathlib import Path
import unittest

from speccraft.diff_engine import SpecDiffEngine
from speccraft.models import ChangeType


class TestSpecDiffEngine(unittest.TestCase):
    """Test suite verifying deterministic OpenAPI 3.0 diffing and breaking change detection."""

    def setUp(self):
        self.engine = SpecDiffEngine()

    def test_identical_specs_yield_zero_changes(self):
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "get_users",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        report = self.engine.compare(spec, spec)
        self.assertEqual(report.summary.total_changes, 0)
        self.assertEqual(report.summary.breaking_changes, 0)
        self.assertEqual(report.summary.non_breaking_changes, 0)
        self.assertEqual(len(report.changes), 0)

    def test_detect_added_endpoint_non_breaking(self):
        v1 = {
            "openapi": "3.0.3",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {"operationId": "get_users", "responses": {"200": {"description": "OK"}}}
                }
            },
        }
        v2 = {
            "openapi": "3.0.3",
            "info": {"title": "Test API", "version": "1.1.0"},
            "paths": {
                "/users": {
                    "get": {"operationId": "get_users", "responses": {"200": {"description": "OK"}}}
                },
                "/users": {
                    "get": {"operationId": "get_users", "responses": {"200": {"description": "OK"}}},
                    "post": {"operationId": "create_user", "responses": {"201": {"description": "Created"}}},
                },
            },
        }
        report = self.engine.compare(v1, v2)
        self.assertEqual(report.summary.added_endpoints, 1)
        self.assertEqual(report.summary.breaking_changes, 0)
        self.assertEqual(report.summary.non_breaking_changes, 1)

        change = report.changes[0]
        self.assertEqual(change.change_type, ChangeType.ENDPOINT_ADDED)
        self.assertEqual(change.path, "/users")
        self.assertEqual(change.method, "post")
        self.assertFalse(change.is_breaking)

    def test_detect_removed_endpoint_breaking(self):
        v1 = {
            "openapi": "3.0.3",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users/{id}": {
                    "delete": {"operationId": "delete_user", "responses": {"204": {"description": "Deleted"}}}
                }
            },
        }
        v2 = {
            "openapi": "3.0.3",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {},
        }
        report = self.engine.compare(v1, v2)
        self.assertEqual(report.summary.removed_endpoints, 1)
        self.assertEqual(report.summary.breaking_changes, 1)

        change = report.changes[0]
        self.assertEqual(change.change_type, ChangeType.ENDPOINT_REMOVED)
        self.assertEqual(change.path, "/users/{id}")
        self.assertEqual(change.method, "delete")
        self.assertTrue(change.is_breaking)

    def test_added_required_parameter_is_breaking(self):
        v1 = {
            "openapi": "3.0.3",
            "paths": {
                "/items": {
                    "get": {"operationId": "get_items", "parameters": [], "responses": {"200": {"description": "OK"}}}
                }
            },
        }
        v2 = {
            "openapi": "3.0.3",
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "get_items",
                        "parameters": [
                            {"name": "api_key", "in": "query", "required": True, "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        report = self.engine.compare(v1, v2)
        self.assertEqual(report.summary.breaking_changes, 1)
        change = report.changes[0]
        self.assertEqual(change.change_type, ChangeType.PARAMETER_ADDED)
        self.assertTrue(change.is_breaking)
        self.assertIn("api_key", change.description)

    def test_added_optional_parameter_is_non_breaking(self):
        v1 = {
            "openapi": "3.0.3",
            "paths": {
                "/items": {
                    "get": {"operationId": "get_items", "parameters": [], "responses": {"200": {"description": "OK"}}}
                }
            },
        }
        v2 = {
            "openapi": "3.0.3",
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "get_items",
                        "parameters": [
                            {"name": "skip", "in": "query", "required": False, "schema": {"type": "integer"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        report = self.engine.compare(v1, v2)
        self.assertEqual(report.summary.breaking_changes, 0)
        self.assertEqual(report.summary.non_breaking_changes, 1)
        change = report.changes[0]
        self.assertEqual(change.change_type, ChangeType.PARAMETER_ADDED)
        self.assertFalse(change.is_breaking)

    def test_parameter_type_alteration_is_breaking(self):
        v1 = {
            "openapi": "3.0.3",
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "query", "required": False, "schema": {"type": "integer"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        v2 = {
            "openapi": "3.0.3",
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "query", "required": False, "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        report = self.engine.compare(v1, v2)
        self.assertEqual(report.summary.breaking_changes, 1)
        change = report.changes[0]
        self.assertEqual(change.change_type, ChangeType.PARAMETER_MODIFIED)
        self.assertTrue(change.is_breaking)
        self.assertIn("integer", change.description)
        self.assertIn("string", change.description)

    def test_removed_200_response_code_is_breaking(self):
        v1 = {
            "openapi": "3.0.3",
            "paths": {
                "/ping": {
                    "get": {"responses": {"200": {"description": "OK"}, "400": {"description": "Bad"}}}
                }
            },
        }
        v2 = {
            "openapi": "3.0.3",
            "paths": {
                "/ping": {
                    "get": {"responses": {"400": {"description": "Bad"}}}
                }
            },
        }
        report = self.engine.compare(v1, v2)
        self.assertEqual(report.summary.breaking_changes, 1)
        change = report.changes[0]
        self.assertEqual(change.change_type, ChangeType.RESPONSE_CODE_REMOVED)
        self.assertTrue(change.is_breaking)

    def test_diff_golden_shop_v1_vs_v2(self):
        expected_dir = Path(__file__).parent.parent / "samples" / "expected_specs"
        v1_path = expected_dir / "shop_v1.json"
        v2_path = expected_dir / "shop_v2.json"

        self.assertTrue(v1_path.exists())
        self.assertTrue(v2_path.exists())

        v1_spec = json.loads(v1_path.read_text(encoding="utf-8"))
        v2_spec = json.loads(v2_path.read_text(encoding="utf-8"))

        report = self.engine.compare(v1_spec, v2_spec)

        # Expected differences:
        # 1. Removed DELETE /items/{item_id} (Breaking)
        # 2. Added GET /items/search (Non-breaking)
        # 3. Added required header X-Vendor-ID on POST /items (Breaking)
        # 4. Added optional query category on GET /items (Non-breaking)
        self.assertEqual(report.summary.removed_endpoints, 1)
        self.assertEqual(report.summary.added_endpoints, 1)
        self.assertEqual(report.summary.breaking_changes, 2)
        self.assertEqual(report.summary.non_breaking_changes, 2)
        self.assertEqual(report.summary.total_changes, 4)


if __name__ == "__main__":
    unittest.main()
