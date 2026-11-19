"""Unit tests for SpecCraft AI core data models."""

import unittest
from speccraft.models import (
    HTTPMethod,
    ParameterLocation,
    ParameterModel,
    RequestBodyModel,
    ResponseModel,
    APIEndpoint,
    SourceFile,
    ExtractionWarning,
    ExtractionResult,
)


class TestModels(unittest.TestCase):
    """Test suite for core Pydantic intermediate representation models."""

    def test_parameter_model_creation(self):
        param = ParameterModel(
            name="item_id",
            location=ParameterLocation.PATH,
            required=True,
            param_type="integer",
            description="Unique identifier of item",
        )
        self.assertEqual(param.name, "item_id")
        self.assertEqual(param.location, ParameterLocation.PATH)
        self.assertTrue(param.required)
        self.assertEqual(param.param_type, "integer")

    def test_parameter_alias_serialization(self):
        param = ParameterModel(
            name="filter",
            location=ParameterLocation.QUERY,
            required=False,
            default="",
        )
        data = param.model_dump(by_alias=True)
        self.assertIn("in", data)
        self.assertEqual(data["in"], "query")

    def test_api_endpoint_with_extension_slot(self):
        endpoint = APIEndpoint(
            path="/api/v1/items",
            method=HTTPMethod.POST,
            operation_id="create_item",
            summary="Create a new item",
            tags=["items"],
            source_file="routers/items.py",
            line_number=42,
            request_body=RequestBodyModel(
                schema_name="ItemCreate",
                schema_ref="#/components/schemas/ItemCreate",
            ),
            responses={
                "201": ResponseModel(
                    status_code="201",
                    description="Item created successfully",
                    schema_ref="#/components/schemas/ItemResponse",
                )
            },
            enrichment_metadata={"ai_generated_tags": ["ecommerce", "crud"]},
        )
        self.assertEqual(endpoint.method, HTTPMethod.POST)
        self.assertEqual(endpoint.path, "/api/v1/items")
        self.assertEqual(len(endpoint.responses), 1)
        self.assertIn("201", endpoint.responses)
        self.assertEqual(endpoint.enrichment_metadata["ai_generated_tags"], ["ecommerce", "crud"])

    def test_extraction_result_defaults(self):
        result = ExtractionResult(
            endpoints=[],
            files_scanned=5,
            total_loc=1200,
            parse_duration_ms=45.2,
        )
        self.assertEqual(result.files_scanned, 5)
        self.assertEqual(result.total_loc, 1200)
        self.assertEqual(len(result.warnings), 0)
        self.assertEqual(len(result.schemas), 0)

    def test_source_file_and_warning(self):
        sf = SourceFile(
            relative_path="main.py",
            content="from fastapi import FastAPI\napp = FastAPI()",
            loc=2,
        )
        self.assertEqual(sf.loc, 2)
        warning = ExtractionWarning(
            file="main.py",
            line=10,
            code="UNRESOLVED_IMPORT",
            message="Module xyz could not be resolved",
        )
        self.assertEqual(warning.code, "UNRESOLVED_IMPORT")


if __name__ == "__main__":
    unittest.main()

