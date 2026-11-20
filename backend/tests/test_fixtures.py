"""Automated test runner verifying all test fixtures against their golden expected_routes.json."""

import json
import unittest
from pathlib import Path

from speccraft.route_extractor import RouteExtractor


class TestFixturesGoldenComparison(unittest.TestCase):
    """Verifies that all supported and negative fixtures match their committed golden outputs."""

    def setUp(self):
        self.fixtures_dir = Path(__file__).parent.parent / "samples" / "fixtures"
        self.extractor = RouteExtractor()

    def test_basic_crud_fixture(self):
        fixture_path = self.fixtures_dir / "basic_crud"
        result = self.extractor.extract_from_path(fixture_path)

        with open(fixture_path / "expected_routes.json", "r", encoding="utf-8") as f:
            expected = json.load(f)

        self.assertEqual(len(result.endpoints), len(expected))
        for actual_ep, exp_dict in zip(result.endpoints, expected):
            self.assertEqual(actual_ep.path, exp_dict["path"])
            self.assertEqual(actual_ep.method.value, exp_dict["method"])
            self.assertEqual(actual_ep.operation_id, exp_dict["operation_id"])

    def test_dynamic_route_fixture_emits_sc_w001(self):
        fixture_path = self.fixtures_dir / "dynamic_route"
        result = self.extractor.extract_from_path(fixture_path)

        with open(fixture_path / "expected_routes.json", "r", encoding="utf-8") as f:
            expected = json.load(f)

        # Verify only valid endpoint extracted
        self.assertEqual(len(result.endpoints), len(expected["expected_endpoints"]))
        self.assertEqual(result.endpoints[0].path, expected["expected_endpoints"][0]["path"])

        # Verify SC-W001 diagnostic emitted
        codes = [d.code.value for d in result.diagnostics]
        for exp_code in expected["expected_diagnostic_codes"]:
            self.assertIn(exp_code, codes)

    def test_syntax_error_fixture_emits_sc_w008(self):
        fixture_path = self.fixtures_dir / "syntax_error"
        result = self.extractor.extract_from_path(fixture_path)

        with open(fixture_path / "expected_routes.json", "r", encoding="utf-8") as f:
            expected = json.load(f)

        self.assertEqual(len(result.endpoints), 0)
        codes = [d.code.value for d in result.diagnostics]
        for exp_code in expected["expected_diagnostic_codes"]:
            self.assertIn(exp_code, codes)

    def test_unsupported_registration_emits_sc_w003(self):
        fixture_path = self.fixtures_dir / "unsupported_registration"
        result = self.extractor.extract_from_path(fixture_path)

        with open(fixture_path / "expected_routes.json", "r", encoding="utf-8") as f:
            expected = json.load(f)

        self.assertEqual(len(result.endpoints), len(expected["expected_endpoints"]))
        codes = [d.code.value for d in result.diagnostics]
        for exp_code in expected["expected_diagnostic_codes"]:
            self.assertIn(exp_code, codes)

    def test_unsupported_framework_emits_sc_e001(self):
        fixture_path = self.fixtures_dir / "unsupported_framework"
        result = self.extractor.extract_from_path(fixture_path)

        with open(fixture_path / "expected_routes.json", "r", encoding="utf-8") as f:
            expected = json.load(f)

        codes = [d.code.value for d in result.diagnostics]
        for exp_code in expected["expected_diagnostic_codes"]:
            self.assertIn(exp_code, codes)


if __name__ == "__main__":
    unittest.main()

