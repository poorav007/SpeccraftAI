"""Unit tests for metadata mapper and path normalization."""

import unittest
from speccraft.metadata_mapper import (
    map_and_normalize_endpoints,
    normalize_route_path,
    resolve_operation_id,
)
from speccraft.models import APIEndpoint, HTTPMethod


class TestMetadataMapper(unittest.TestCase):
    """Test suite for path normalization, operation ID generation, and deterministic sorting."""

    def test_normalize_route_path_converters(self):
        self.assertEqual(normalize_route_path("/items/{item_id:int}"), "/items/{item_id}")
        self.assertEqual(normalize_route_path("/files/{file_path:path}"), "/files/{file_path}")
        self.assertEqual(normalize_route_path("//api//v1/items/"), "/api/v1/items")
        self.assertEqual(normalize_route_path("/"), "/")
        self.assertEqual(normalize_route_path("users"), "/users")

    def test_resolve_operation_id_collisions(self):
        used_ids = set()
        op1 = resolve_operation_id("get_items", used_ids)
        op2 = resolve_operation_id("get_items", used_ids)
        op3 = resolve_operation_id("get_items", used_ids)

        self.assertEqual(op1, "get_items")
        self.assertEqual(op2, "get_items_1")
        self.assertEqual(op3, "get_items_2")

    def test_deterministic_sorting_and_tags(self):
        # Create un-sorted endpoints
        ep1 = APIEndpoint(
            path="/users",
            method=HTTPMethod.POST,
            operation_id="create_user",
            source_file="users.py",
            line_number=10,
        )
        ep2 = APIEndpoint(
            path="/items",
            method=HTTPMethod.POST,
            operation_id="create_item",
            source_file="items.py",
            line_number=5,
        )
        ep3 = APIEndpoint(
            path="/items",
            method=HTTPMethod.GET,
            operation_id="create_item",  # Collision with ep2!
            source_file="items.py",
            line_number=1,
        )

        result = map_and_normalize_endpoints([ep1, ep2, ep3])

        # Verify ordering: /items (GET), /items (POST), /users (POST)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].path, "/items")
        self.assertEqual(result[0].method, HTTPMethod.GET)
        self.assertEqual(result[1].path, "/items")
        self.assertEqual(result[1].method, HTTPMethod.POST)
        self.assertEqual(result[2].path, "/users")

        # Verify collision was resolved
        self.assertNotEqual(result[0].operation_id, result[1].operation_id)
        self.assertEqual(result[1].operation_id, "create_item_1")

        # Verify tag fallback to first path segment
        self.assertEqual(result[0].tags, ["items"])
        self.assertEqual(result[2].tags, ["users"])


if __name__ == "__main__":
    unittest.main()

