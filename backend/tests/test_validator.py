"""Unit tests for OpenAPI 3.0.3 schema validator (F09)."""

import unittest
from speccraft.schema_validator import OpenAPISchemaValidator


class TestOpenAPISchemaValidator(unittest.TestCase):
    """Test suite verifying OpenAPI specification structural and integrity validation."""

    def setUp(self):
        self.validator = OpenAPISchemaValidator()

    def test_valid_specification_passes(self):
        valid_spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "list_items",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        report = self.validator.validate(valid_spec)
        self.assertTrue(report.is_valid)
        self.assertEqual(len(report.errors), 0)
        self.assertEqual(report.stats["paths_count"], 1)
        self.assertEqual(report.stats["operations_count"], 1)

    def test_missing_required_top_level_fields(self):
        bad_spec = {
            "info": {"title": "No Version"},
            # Missing openapi, version, and paths
        }
        report = self.validator.validate(bad_spec)
        self.assertFalse(report.is_valid)
        error_codes = [e.code for e in report.errors]
        self.assertIn("ERR_MISSING_FIELD", error_codes)

    def test_invalid_openapi_version(self):
        bad_spec = {
            "openapi": "2.0",
            "info": {"title": "Swagger 2.0", "version": "1.0.0"},
            "paths": {},
        }
        report = self.validator.validate(bad_spec)
        self.assertFalse(report.is_valid)
        error_codes = [e.code for e in report.errors]
        self.assertIn("ERR_INVALID_VERSION", error_codes)

    def test_broken_ref_pointer_detected(self):
        spec_with_broken_ref = {
            "openapi": "3.0.3",
            "info": {"title": "Broken Ref API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "post": {
                        "operationId": "create_item",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/NonExistentModel"}
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                }
            },
            "components": {"schemas": {"OtherModel": {"type": "object"}}},
        }
        report = self.validator.validate(spec_with_broken_ref)
        self.assertFalse(report.is_valid)
        error_codes = [e.code for e in report.errors]
        self.assertIn("ERR_BROKEN_REF", error_codes)
        broken_err = [e for e in report.errors if e.code == "ERR_BROKEN_REF"][0]
        self.assertIn("NonExistentModel", broken_err.message)

    def test_missing_path_parameter_detected(self):
        spec_with_missing_path_param = {
            "openapi": "3.0.3",
            "info": {"title": "Missing Param API", "version": "1.0.0"},
            "paths": {
                "/items/{item_id}": {
                    "get": {
                        "operationId": "get_item",
                        "parameters": [],  # item_id is missing from parameters!
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
        report = self.validator.validate(spec_with_missing_path_param)
        self.assertFalse(report.is_valid)
        error_codes = [e.code for e in report.errors]
        self.assertIn("ERR_MISSING_PATH_PARAM", error_codes)
        param_err = [e for e in report.errors if e.code == "ERR_MISSING_PATH_PARAM"][0]
        self.assertIn("item_id", param_err.message)

    def test_duplicate_operation_id_detected(self):
        spec_with_duplicate_op_id = {
            "openapi": "3.0.3",
            "info": {"title": "Duplicate OpId API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "same_operation",
                        "responses": {"200": {"description": "OK"}},
                    },
                    "post": {
                        "operationId": "same_operation",  # Collision!
                        "responses": {"201": {"description": "Created"}},
                    },
                }
            },
        }
        report = self.validator.validate(spec_with_duplicate_op_id)
        self.assertFalse(report.is_valid)
        error_codes = [e.code for e in report.errors]
        self.assertIn("ERR_DUPLICATE_OPERATION_ID", error_codes)

    def test_invalid_status_code_detected(self):
        spec_with_bad_status = {
            "openapi": "3.0.3",
            "info": {"title": "Bad Status API", "version": "1.0.0"},
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "get_items",
                        "responses": {"invalid_code": {"description": "Bad"}},
                    }
                }
            },
        }
        report = self.validator.validate(spec_with_bad_status)
        self.assertFalse(report.is_valid)
        error_codes = [e.code for e in report.errors]
        self.assertIn("ERR_INVALID_STATUS_CODE", error_codes)

    def test_yaml_string_input_validation(self):
        yaml_content = """
openapi: 3.0.3
info:
  title: YAML API
  version: 1.0.0
paths:
  /ping:
    get:
      operationId: ping
      responses:
        '200':
          description: Pong
"""
        report = self.validator.validate(yaml_content)
        self.assertTrue(report.is_valid)
        self.assertEqual(len(report.errors), 0)

    def test_validate_fastapi_shop_golden_spec(self):
        import json
        from pathlib import Path
        golden_path = Path(__file__).parent.parent / "samples" / "expected_specs" / "shop_v1.json"
        self.assertTrue(golden_path.exists(), f"Golden spec missing at {golden_path}")
        spec_data = json.loads(golden_path.read_text(encoding="utf-8"))

        report = self.validator.validate(spec_data)
        self.assertTrue(report.is_valid, f"Validation failed with errors: {report.errors}")
        self.assertEqual(len(report.errors), 0)
        self.assertEqual(report.stats["operations_count"], 9)
        self.assertEqual(report.stats["schemas_count"], 9)


if __name__ == "__main__":
    unittest.main()
