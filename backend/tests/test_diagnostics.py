"""Unit tests for the PRD Section 8 diagnostics system."""

import unittest
from speccraft.diagnostics import DIAGNOSTIC_CATALOG, Diagnostic, DiagnosticCode, DiagnosticSeverity


class TestDiagnostics(unittest.TestCase):
    """Test suite for formal diagnostic error and warning reporting."""

    def test_catalog_completeness(self):
        """Ensure all 10 PRD diagnostic codes are defined in the catalog with title, description, and hint."""
        expected_codes = [
            DiagnosticCode.SC_W001,
            DiagnosticCode.SC_W002,
            DiagnosticCode.SC_W003,
            DiagnosticCode.SC_W004,
            DiagnosticCode.SC_W005,
            DiagnosticCode.SC_W006,
            DiagnosticCode.SC_W007,
            DiagnosticCode.SC_W008,
            DiagnosticCode.SC_E001,
            DiagnosticCode.SC_E002,
        ]
        for code in expected_codes:
            self.assertIn(code, DIAGNOSTIC_CATALOG, f"Missing catalog entry for {code}")
            info = DIAGNOSTIC_CATALOG[code]
            self.assertIn("title", info)
            self.assertIn("description", info)
            self.assertIn("hint", info)

    def test_create_warning_diagnostic(self):
        diag = Diagnostic.create(
            code=DiagnosticCode.SC_W001,
            file="routers/items.py",
            line=42,
        )
        self.assertEqual(diag.code, DiagnosticCode.SC_W001)
        self.assertEqual(diag.severity, DiagnosticSeverity.WARNING)
        self.assertEqual(diag.file, "routers/items.py")
        self.assertEqual(diag.line, 42)
        self.assertIn("Non-Literal", diag.message)
        self.assertIsNotNone(diag.hint)

    def test_create_error_diagnostic(self):
        diag = Diagnostic.create(
            code=DiagnosticCode.SC_E001,
            file="main.py",
            custom_message="No FastAPI imports found in repository",
        )
        self.assertEqual(diag.code, DiagnosticCode.SC_E001)
        self.assertEqual(diag.severity, DiagnosticSeverity.ERROR)
        self.assertEqual(diag.file, "main.py")
        self.assertIn("fastapi", diag.hint.lower())

    def test_format_terminal_output(self):
        diag = Diagnostic.create(
            code=DiagnosticCode.SC_W008,
            file="broken.py",
            line=12,
        )
        output = diag.format_terminal()
        self.assertIn("[WARNING]", output)
        self.assertIn("SC-W008", output)
        self.assertIn("broken.py:12", output)
        self.assertIn("Hint:", output)


if __name__ == "__main__":
    unittest.main()
