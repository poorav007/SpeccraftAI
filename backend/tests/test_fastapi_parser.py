"""Unit tests for FastAPI static AST parser and Pydantic schema extractor."""

import unittest
from speccraft.models import HTTPMethod, ParameterLocation, SourceFile
from speccraft.parser.fastapi_adapter import FastAPIParser
from speccraft.reader import SourceFileReader


class TestFastAPIParser(unittest.TestCase):
    """Test suite for FastAPI AST extraction."""

    def setUp(self):
        self.parser = FastAPIParser()
        self.reader = SourceFileReader()

    def test_parse_get_with_path_and_query_params(self):
        code = """
from fastapi import FastAPI
from typing import Optional

app = FastAPI()

@app.get("/items/{item_id}", summary="Get Single Item")
def read_item(item_id: int, q: Optional[str] = None, limit: int = 10):
    \"\"\"Retrieve an item by its unique ID.\"\"\"
    return {"item_id": item_id, "q": q, "limit": limit}
"""
        source = self.reader.read_code_string(code, "main.py")
        result = self.parser.parse_files([source])

        self.assertEqual(len(result.endpoints), 1)
        endpoint = result.endpoints[0]

        self.assertEqual(endpoint.path, "/items/{item_id}")
        self.assertEqual(endpoint.method, HTTPMethod.GET)
        self.assertEqual(endpoint.operation_id, "read_item")
        self.assertEqual(endpoint.summary, "Get Single Item")

        # Verify parameters
        params = {p.name: p for p in endpoint.parameters}
        self.assertIn("item_id", params)
        self.assertIn("q", params)
        self.assertIn("limit", params)

        # item_id is path param (required)
        self.assertEqual(params["item_id"].location, ParameterLocation.PATH)
        self.assertTrue(params["item_id"].required)
        self.assertEqual(params["item_id"].param_type, "integer")

        # q is query param (optional)
        self.assertEqual(params["q"].location, ParameterLocation.QUERY)
        self.assertFalse(params["q"].required)

        # limit is query param with default 10
        self.assertEqual(params["limit"].location, ParameterLocation.QUERY)
        self.assertEqual(params["limit"].default, 10)

    def test_parse_post_with_pydantic_body_and_schema(self):
        code = """
from fastapi import FastAPI, status
from pydantic import BaseModel, Field

app = FastAPI()

class ItemCreate(BaseModel):
    name: str = Field(..., description="Item title")
    price: float = Field(default=0.0, description="Item price in USD")
    is_active: bool = True

@app.post("/items", status_code=status.HTTP_201_CREATED, tags=["items"])
def create_item(payload: ItemCreate):
    return payload
"""
        source = self.reader.read_code_string(code, "routes.py")
        result = self.parser.parse_files([source])

        self.assertEqual(len(result.endpoints), 1)
        endpoint = result.endpoints[0]

        self.assertEqual(endpoint.path, "/items")
        self.assertEqual(endpoint.method, HTTPMethod.POST)
        self.assertEqual(endpoint.tags, ["items"])
        self.assertIn("201", endpoint.responses)

        # Verify request body
        self.assertIsNotNone(endpoint.request_body)
        self.assertEqual(endpoint.request_body.schema_name, "ItemCreate")

        # Verify extracted JSON schema for ItemCreate
        self.assertIn("ItemCreate", result.schemas)
        schema = result.schemas["ItemCreate"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("name", schema["properties"])
        self.assertEqual(schema["properties"]["name"]["type"], "string")
        self.assertEqual(schema["properties"]["name"]["description"], "Item title")
        self.assertIn("name", schema.get("required", []))
        self.assertNotIn("is_active", schema.get("required", []))

    def test_router_prefix_and_tags(self):
        code = """
from fastapi import APIRouter

router = APIRouter(prefix="/v1/users", tags=["users"])

@router.delete("/{user_id}", deprecated=True)
def delete_user(user_id: str):
    pass
"""
        source = self.reader.read_code_string(code, "users.py")
        result = self.parser.parse_files([source])

        self.assertEqual(len(result.endpoints), 1)
        endpoint = result.endpoints[0]

        self.assertEqual(endpoint.path, "/v1/users/{user_id}")
        self.assertEqual(endpoint.method, HTTPMethod.DELETE)
        self.assertTrue(endpoint.deprecated)
        self.assertEqual(endpoint.tags, ["users"])

    def test_syntax_error_yields_warning(self):
        broken_code = "def broken_route( : return 1"
        source = self.reader.read_code_string(broken_code, "broken.py")
        result = self.parser.parse_files([source])

        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].code, "SYNTAX_ERROR")
        self.assertEqual(len(result.endpoints), 0)


if __name__ == "__main__":
    unittest.main()

