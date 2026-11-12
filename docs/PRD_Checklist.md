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

### Day 3: Extraction Pipeline, CLI & 10k-LOC Benchmark (NEXT)
- [ ] Pipeline orchestrator (`backend/speccraft/route_extractor.py`) & metadata mapper (`backend/speccraft/metadata_mapper.py`)
- [ ] Command Line Interface (`backend/speccraft/cli.py`)
- [ ] 10,000-line synthetic FastAPI benchmark test harness (`backend/tests/test_benchmark.py`) verifying `< 2.0s` parse time

### Day 4: OpenAPI 3.0 Generation & Schema Validation
- [ ] OpenAPI 3.0.3 YAML & JSON generator (`backend/speccraft/openapi_generator.py`)
- [ ] Schema validator (`backend/speccraft/schema_validator.py` with `jsonschema` / `openapi-spec-validator`)

### Day 5: Backend API Bridge & Frontend Screen 1 Integration
- [ ] FastAPI HTTP server (`backend/speccraft/api/server.py`, `/api/parse`, `/api/generate`)
- [ ] Connect React Screen 1 to Python backend API

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

