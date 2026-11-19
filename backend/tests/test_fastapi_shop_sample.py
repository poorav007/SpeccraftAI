"""Integration test verifying AST parsing on the multi-file sample FastAPI shop codebase."""

import unittest
from pathlib import Path

from speccraft.models import HTTPMethod
from speccraft.parser.fastapi_adapter import FastAPIParser
from speccraft.reader import SourceFileReader


class TestFastAPIShopSample(unittest.TestCase):
    """End-to-end verification of static AST parsing on fastapi_shop_api."""

    @classmethod
    def setUpClass(cls):
        cls.sample_dir = Path(__file__).parent.parent / "samples" / "fastapi_shop_api"
        cls.reader = SourceFileReader()
        cls.parser = FastAPIParser()

        cls.source_files = cls.reader.read_directory(cls.sample_dir)
        cls.result = cls.parser.parse_files(cls.source_files)

    def test_files_discovered_and_scanned(self):
        self.assertGreaterEqual(self.result.files_scanned, 4)
        self.assertGreater(self.result.total_loc, 100)
        self.assertEqual(len(self.result.warnings), 0, "Expected zero parsing warnings")

    def test_routes_extracted(self):
        routes_map = {(ep.path, ep.method): ep for ep in self.result.endpoints}

        # Verify key endpoints exist
        self.assertIn(("/health", HTTPMethod.GET), routes_map)
        self.assertIn(("/items", HTTPMethod.GET), routes_map)
        self.assertIn(("/items", HTTPMethod.POST), routes_map)
        self.assertIn(("/items/{item_id}", HTTPMethod.GET), routes_map)
        self.assertIn(("/items/{item_id}", HTTPMethod.PUT), routes_map)
        self.assertIn(("/items/{item_id}", HTTPMethod.DELETE), routes_map)
        self.assertIn(("/orders", HTTPMethod.GET), routes_map)
        self.assertIn(("/orders", HTTPMethod.POST), routes_map)
        self.assertIn(("/orders/{order_id}", HTTPMethod.GET), routes_map)

        self.assertEqual(len(self.result.endpoints), 9)

    def test_schemas_extracted(self):
        schemas = self.result.schemas
        self.assertIn("ItemBase", schemas)
        self.assertIn("ItemCreate", schemas)
        self.assertIn("ItemResponse", schemas)
        self.assertIn("OrderItem", schemas)
        self.assertIn("OrderCreate", schemas)
        self.assertIn("OrderResponse", schemas)

        # Inspect ItemResponse schema properties
        item_resp = schemas["ItemResponse"]
        self.assertEqual(item_resp["type"], "object")
        self.assertIn("id", item_resp["properties"])
        self.assertIn("in_stock", item_resp["properties"])
        self.assertEqual(item_resp["properties"]["id"]["type"], "integer")

    def test_parse_speed(self):
        # Parsing a multi-file project should take only a few milliseconds
        self.assertLess(self.result.parse_duration_ms, 500.0)


if __name__ == "__main__":
    unittest.main()

