# SpecCraft AI — Mentor PRD Alignment & Open Tasks Checklist

Source: PST_PD_142 (2026 Level 4 (Stretch)) · Team: Kushaal Thota & Poorav · Mentor: Tanishka
Accelerated Timeline: 10–12 Days Target

## Daily Milestone Tracker

### Day 1: Project Setup & Frontend Screen 1 (COMPLETE)
- [x] GitHub repo setup, branch protection, CI GitHub Actions (`.github/workflows/ci.yml`)
- [x] Frontend Screen 1 scaffold (`ProjectUploader.jsx`, `CodebaseImportPage.jsx`)
- [x] LocalStorage persistence engine (`localStorage.js`, Vitest suite 9/9 passing)
- [x] Regex client-side parser stub with `performance.now()` timing

### Day 2: Core Backend AST Engine & Sample Codebase (COMPLETE)
- [x] Core data models (`backend/speccraft/models.py`): `APIEndpoint`, `SourceFile`, `ExtractionWarning`, `ParameterModel`, `RequestBodyModel`, `ResponseModel`, `ExtractionResult` with `enrichment_metadata` extension slots
- [x] Safe source file reader & security guards (`backend/speccraft/reader.py`, `utils/path_safety.py`): path traversal guards, file size limits, directory crawler
- [x] FastAPI AST Visitor (`backend/speccraft/parser/fastapi_adapter.py`): `@app.*`, `@router.*`, path params, query params, request bodies, docstring summaries, status codes
- [x] Pydantic Schema Extractor (`backend/speccraft/schema_builder.py`): static AST inspection of `BaseModel` classes into OpenAPI JSON Schemas
- [x] Sample multi-file FastAPI codebase (`backend/samples/fastapi_shop_api/`): `main.py`, `models/schemas.py`, `routers/items.py`, `routers/orders.py`
- [x] Unit test suite: 20/20 backend unit tests passing in ~0.12s (`test_models.py`, `test_reader.py`, `test_fastapi_parser.py`, `test_fastapi_shop_sample.py`)

### Day 3: Diagnostics, Extraction Pipeline, CLI & 10k-LOC Benchmark (COMPLETE)
- [x] F07: Standard Diagnostics & Warnings System (`backend/speccraft/diagnostics.py`, PRD Section 8 codes `SC-W001` to `SC-E002`, unit tests passing)
- [x] F02: Safe Zip Ingestion & Framework Detection (`backend/speccraft/reader.py`, Zip-Slip defense, file/size caps, unit tests passing)
- [x] F03: Test Fixtures Suite (`backend/samples/fixtures/`, golden comparisons, `docs/FIXTURES.md`)
- [x] F04, F05, F07: Static AST Parser enhancements (unannotated params, Depends, undeclared schemas, syntax errors, non-literal paths)
- [x] F06: Pipeline orchestrator (`backend/speccraft/route_extractor.py`) & metadata mapper (`backend/speccraft/metadata_mapper.py`, path normalization, operationId collision resolution, deterministic sorting)
- [x] Command Line Interface (`backend/speccraft/cli.py`, ASCII table, JSON output, diagnostics integration)
- [x] F20: 10,000-line synthetic FastAPI benchmark test harness (`backend/tests/test_benchmark.py`) verifying `< 2.0s` parse time (achieved ~0.95s / 10,674 lines/sec)
- [x] Backend unit test suite: 38/38 passing across all test modules

### Day 4: OpenAPI 3.0 Generation & Schema Validation (COMPLETE)
- [x] F08: OpenAPI 3.0.3 YAML & JSON generator (`backend/speccraft/openapi_generator.py`, paths, components, $ref links, deterministic sorting)
- [x] F09: Schema validator (`backend/speccraft/schema_validator.py`, structural, broken $ref detection, path param parity, status code verification)
- [x] Golden reference spec verification (`backend/samples/expected_specs/shop_v1.json`, 100% compliant, 0 errors)
- [x] Unit test suites: 53/53 backend unit tests passing in ~2.5s (`test_openapi_generator.py`, `test_validator.py`)

### Day 5: Backend API Bridge & Frontend Screen 1 Integration (COMPLETE)
- [x] FastAPI HTTP server (`backend/speccraft/api/server.py`, `backend/speccraft/api/routes.py`, `/api/health`, `/api/parse`, `/api/generate`, `/api/validate`)
- [x] Safe multipart file and zip upload with Zip-Slip defense and PRD diagnostic rejections
- [x] Frontend API Client (`frontend/src/services/apiClient.js` with timeout & offline fallback detection)
- [x] Connected React Screen 1 (`ProjectUploader.jsx`) with archive upload, code snippet mode, AST metrics card, and PRD diagnostic badges
- [x] Unit test suites: 61/61 backend tests passing, 15/15 frontend tests passing

### Day 6: Frontend Screen 2 (AST Analysis & Review)
- [ ] Route Table component (`RouteTable.jsx`), Method filter badges, parameter inspector, editable metadata

### Day 7: Frontend Screen 3 (Swagger UI & Spec Editor)
- [ ] Swagger UI preview component (`SwaggerPreview.jsx`) & live Spec Editor (`SpecificationEditorPage.jsx`)

### Day 8: Spec Diff Engine
- [ ] Breaking vs non-breaking change detection engine (`spec_diff_engine.py`)
- [ ] Spec Diff Viewer UI (`SpecDiffViewer.jsx`, `SpecificationDiffPage.jsx`)

### Day 9: Export Center & Session Persistence
- [ ] ExportManager (JSON, YAML, Postman v2.1 collection export)
- [ ] Project session save/load/export

### Day 10: Performance Benchmarking, WCAG 2.2 AA Audit & E2E Polish
- [ ] 10k-LOC benchmark performance report
- [ ] WCAG 2.2 AA accessibility audit (contrast, keyboard navigation, screen reader ARIA)
- [ ] E2E integration test pass

### Day 11–12: Buffer, Demo Video & Final Presentation
- [ ] Live demo walkthrough video
- [ ] Final architecture and rubric compliance documentation

