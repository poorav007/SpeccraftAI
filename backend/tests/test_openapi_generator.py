"""Unit tests for OpenAPI 3.0.3 generator (F08)."""

import json
import unittest
from speccraft.models import (
    APIEndpoint,
    ExtractionResult,
    HTTPMethod,
    ParameterLocation,
    ParameterModel,
    RequestBodyModel,
    ResponseModel,
)
from speccraft.openapi_generator import OpenAPIGenerator


class TestOpenAPIGenerator(unittest.TestCase):
    """Test suite verifying OpenAPI 3.0.3 specification generation."""

    def setUp(self):
        self.generator = OpenAPIGenerator(
            title="Shop API",
            version="1.0.0",
            description="Sample Shop API Spec",
        )

    def test_generate_basic_spec_structure(self):
        ep_get = APIEndpoint(
            path="/items",
            method=HTTPMethod.GET,
            operation_id="list_items",
            summary="List all items",
            description="Retrieve catalog items",
            tags=["items"],
            source_file="routers/items.py",
        )
        ep_post = APIEndpoint(
            path="/items",
            method=HTTPMethod.POST,
            operation_id="create_item",
            summary="Create an item",
            tags=["items"],
            source_file="routers/items.py",
        )
        result = ExtractionResult(endpoints=[ep_get, ep_post])
        spec = self.generator.generate(result)

        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertEqual(spec["info"]["title"], "Shop API")
        self.assertEqual(spec["info"]["version"], "1.0.0")
        self.assertIn("/items", spec["paths"])
        self.assertIn("get", spec["paths"]["/items"])
        self.assertIn("post", spec["paths"]["/items"])

        get_op = spec["paths"]["/items"]["get"]
        self.assertEqual(get_op["operationId"], "list_items")
        self.assertEqual(get_op["tags"], ["items"])
        self.assertIn("200", get_op["responses"])

        post_op = spec["paths"]["/items"]["post"]
        self.assertEqual(post_op["operationId"], "create_item")
        self.assertIn("201", post_op["responses"])

    def test_path_and_query_parameters(self):
        p_path = ParameterModel(
            name="item_id",
            location=ParameterLocation.PATH,
            required=True,
            param_type="integer",
            description="Unique Item ID",
        )
        p_query = ParameterModel(
            name="skip",
            location=ParameterLocation.QUERY,
            required=False,
            param_type="integer",
            default=0,
        )
        ep = APIEndpoint(
            path="/items/{item_id}",
            method=HTTPMethod.GET,
            operation_id="get_item",
            parameters=[p_path, p_query],
            source_file="routers/items.py",
        )
        result = ExtractionResult(endpoints=[ep])
        spec = self.generator.generate(result)

        op = spec["paths"]["/items/{item_id}"]["get"]
        self.assertEqual(len(op["parameters"]), 2)

        param_map = {p["name"]: p for p in op["parameters"]}
        self.assertEqual(param_map["item_id"]["in"], "path")
        self.assertTrue(param_map["item_id"]["required"])
        self.assertEqual(param_map["item_id"]["schema"]["type"], "integer")

        self.assertEqual(param_map["skip"]["in"], "query")
        self.assertFalse(param_map["skip"]["required"])
        self.assertEqual(param_map["skip"]["schema"]["default"], 0)

        # 404 response attached when path parameters are present
        self.assertIn("404", op["responses"])

    def test_request_body_with_schema_ref(self):
        req_body = RequestBodyModel(
            schema_name="ItemCreate",
            required=True,
            description="Item payload",
        )
        ep = APIEndpoint(
            path="/items",
            method=HTTPMethod.POST,
            operation_id="create_item",
            request_body=req_body,
            source_file="routers/items.py",
        )
        schemas = {
            "ItemCreate": {
                "title": "ItemCreate",
                "type": "object",
                "properties": {"name": {"type": "string"}},
            }
        }
        result = ExtractionResult(endpoints=[ep], schemas=schemas)
        spec = self.generator.generate(result)

        op = spec["paths"]["/items"]["post"]
        self.assertIn("requestBody", op)
        rb = op["requestBody"]
        self.assertTrue(rb["required"])
        self.assertEqual(
            rb["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ItemCreate",
        )
        self.assertIn("ItemCreate", spec["components"]["schemas"])

    def test_204_no_content_response(self):
        resp_204 = ResponseModel(status_code="204", description="Item Deleted")
        ep = APIEndpoint(
            path="/items/{item_id}",
            method=HTTPMethod.DELETE,
            operation_id="delete_item",
            responses={"204": resp_204},
            source_file="routers/items.py",
        )
        result = ExtractionResult(endpoints=[ep])
        spec = self.generator.generate(result)

        op = spec["paths"]["/items/{item_id}"]["delete"]
        self.assertIn("204", op["responses"])
        # 204 response must not have content schema
        self.assertNotIn("content", op["responses"]["204"])
        self.assertEqual(op["responses"]["204"]["description"], "No Content")

    def test_generic_list_response_model(self):
        resp_list = ResponseModel(
            status_code="200",
            schema_name="List[ItemResponse]",
            description="List of Items",
        )
        ep = APIEndpoint(
            path="/items",
            method=HTTPMethod.GET,
            operation_id="list_items",
            responses={"200": resp_list},
            source_file="routers/items.py",
        )
        schemas = {
            "ItemResponse": {
                "title": "ItemResponse",
                "type": "object",
                "properties": {"id": {"type": "integer"}},
            }
        }
        result = ExtractionResult(endpoints=[ep], schemas=schemas)
        spec = self.generator.generate(result)

        schema = spec["paths"]["/items"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(schema["type"], "array")
        self.assertEqual(schema["items"]["$ref"], "#/components/schemas/ItemResponse")

    def test_json_and_yaml_serialization(self):
        ep = APIEndpoint(
            path="/health",
            method=HTTPMethod.GET,
            operation_id="health_check",
            source_file="main.py",
        )
        result = ExtractionResult(endpoints=[ep])

        json_out = self.generator.to_json(result)
        self.assertIsInstance(json_out, str)
        parsed = json.loads(json_out)
        self.assertEqual(parsed["openapi"], "3.0.3")

        yaml_out = self.generator.to_yaml(result)
        self.assertIsInstance(yaml_out, str)
        self.assertIn("openapi: 3.0.3", yaml_out)
        self.assertIn("/health:", yaml_out)


if __name__ == "__main__":
    unittest.main()

