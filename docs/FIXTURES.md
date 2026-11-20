# SpecCraft AI — Test Fixtures & Golden Output Documentation

This directory (`backend/samples/fixtures/`) contains isolated test codebases used to verify static AST parsing, route extraction, and PRD Section 8 diagnostic reporting.

---

## Fixture Catalog

| Fixture Directory | Purpose | Expected Endpoints | Expected Diagnostics | Golden Output File |
| :--- | :--- | :---: | :---: | :--- |
| `basic_crud/` | Verifies standard GET, POST, GET/{id}, DELETE routes and Pydantic request bodies. | 4 | None | `expected_routes.json` |
| `dynamic_route/` | Verifies detection of non-literal/runtime-computed route paths. | 1 (valid only) | `SC-W001` (Non-Literal Route Path) | `expected_routes.json` |
| `unsupported_registration/` | Verifies detection of legacy `app.add_api_route()` or `mount()`. | 1 (valid only) | `SC-W003` (Unsupported Registration) | `expected_routes.json` |
| `syntax_error/` | Verifies that a syntax error does not crash the pipeline and emits partial state. | 0 | `SC-W008` (File Failed to Parse) | `expected_routes.json` |
| `unsupported_framework/` | Verifies detection of non-FastAPI Python projects. | 0 | `SC-E001` (Unsupported Framework) | `expected_routes.json` |

---

## Running the Automated Fixture Verification

Run the test suite from the backend directory:
```bash
python -m unittest tests/test_fixtures.py -v
```
All fixture expectations are verified automatically on every CI run.

