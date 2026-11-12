# SpecCraft AI — Project Directory Structure

> **PRD Reference:** `PST_PD_142` (`2026 Level 4 (Stretch)`) · **Team:** Kushaal Thota & Poorav · **Mentor:** Tanishka

This document defines the directory layout for **SpecCraft AI**, mapped directly to the screens, components, data entities, and deliverables in the mentor-given PRD—while keeping clean extension slots for **future AI integration** and **optional stretch features**.

---

## 1. Complete Folder & File Tree

```text
SpeccraftAI/
├── .gitignore                            # Ignores Python/Node caches, .env secrets, data/generated/, exports/, tmp/
├── .env.example                          # Root environment variables template (ports, CORS, future AI keys)
├── README.md                             # Setup instructions, supported constructs, benchmark & limitations (PRD §19)
├── package.json                          # Root convenience scripts (frontend dev/build, backend/frontend tests)
│
├── .github/
│   └── workflows/
│       └── ci.yml                        # Stretch: GitHub Actions workflow for tests & spec validation
│
├── docs/                                 # Project & PRD deliverable documentation (PRD §19)
│   ├── directory_structure.md            # This file — full repo layout and PRD mapping
│   ├── PRD_Checklist.md                  # 4-week milestone tracker & open PRD student tasks
│   ├── data_dictionary.md                # Metadata mapping docs for extracted API elements
│   ├── benchmark_report.md               # 10,000-line parse speed (< 2s) & OpenAPI validity report
│   └── findings_report.md                # Test coverage, evaluation findings & known limitations
│
├── data/                                 # Dedicated dataset & sample input folder (tracked in Git)
│   ├── README.md                         # Explains what belongs in data/ vs. data/generated/
│   ├── user-stories-dataset.json         # Sample Agile/user-story dataset
│   └── generated/                        # (Gitignored) Runtime outputs & temporary exports
│
├── backend/                              # Python 3 Static Analysis, OpenAPI & Diff Engine
│   ├── .env.example                      # Backend env template (host, port, upload caps, future AI_* vars)
│   ├── pyproject.toml                    # Python project & test discovery configuration (>= 3.10)
│   ├── requirements.txt                  # Python dependencies (pydantic, PyYAML, jsonschema, starlette, uvicorn, etc.)
│   │
│   ├── speccraft/                        # Core Python package
│   │   ├── __init__.py
│   │   ├── config.py                     # File-size caps, ignored dirs, supported framework extensions
│   │   ├── models.py                     # PRD §10 entities (Project, SourceFile, APIEndpoint, OpenAPISpec, etc.)
│   │   ├── reader.py                     # Safe static source-file reader (directory, zip, upload payload)
│   │   ├── route_extractor.py            # RouteExtractor: normalizes routes, chains router prefixes & warnings
│   │   ├── metadata_mapper.py            # MetadataMapper: AST facts -> framework-neutral APIEndpoint IR
│   │   ├── schema_builder.py             # SchemaBuilder: Pydantic models, Enums & validation constraints
│   │   ├── openapi_generator.py          # OpenAPIGenerator: IR -> OpenAPI 3.0 YAML/JSON document
│   │   ├── schema_validator.py           # SchemaValidator: OpenAPI 3.0 validation + actionable errors/warnings
│   │   ├── spec_diff_engine.py           # SpecDiffEngine: deterministic v1 vs. v2 spec comparison
│   │   ├── cli.py                        # CLI runner for testing, automation & 10k-line benchmarks
│   │   │
│   │   ├── parser/                       # Pluggable AST Parser Adapters (PRD §9 ASTParser)
│   │   │   ├── __init__.py
│   │   │   ├── base.py                   # FrameworkAdapter abstract contract & ASTParser dispatcher
│   │   │   ├── fastapi_adapter.py        # MVP primary: Python built-in `ast` FastAPI extractor
│   │   │   └── express_adapter.py        # Good-to-have: Node.js/Express `tree-sitter` adapter slot
│   │   │
│   │   ├── ai/                           # Future AI Integration Layer (No-op by default in MVP)
│   │   │   ├── __init__.py
│   │   │   ├── enricher.py               # Enricher interface + deterministic NoOpEnricher
│   │   │   └── prompts/                  # Future LLM prompt templates (docs, schemas, diff summaries)
│   │   │       └── .gitkeep
│   │   │
│   │   ├── exporters/                    # Extensible ExportManager plugins
│   │   │   ├── __init__.py
│   │   │   ├── export_manager.py         # ExportManager registry (OpenAPI JSON/YAML + future formats)
│   │   │   └── postman_exporter.py       # Good-to-have / Stretch: Postman Collection export
│   │   │
│   │   ├── api/                          # Local HTTP API connecting Python engine to React frontend
│   │   │   ├── __init__.py
│   │   │   ├── server.py                 # App server setup, CORS & error handlers
│   │   │   └── routes.py                 # Endpoints for /analyze, /validate, /diff, /export, /samples
│   │   │
│   │   └── utils/                        # Pure shared helpers
│   │       ├── __init__.py
│   │       ├── path_safety.py            # Traversal guards, path normalization, URL joining
│   │       └── timing.py                 # High-resolution perf_counter timer for benchmarks
│   │
│   ├── samples/                          # Representative sample backend projects & expected outputs
│   │   ├── fastapi_shop_api/             # Sample FastAPI project (multi-file routers + Pydantic models)
│   │   │   ├── main.py
│   │   │   ├── models/
│   │   │   │   └── schemas.py
│   │   │   └── routers/
│   │   │       ├── items.py
│   │   │       └── orders.py
│   │   └── expected_specs/               # Sample OpenAPI v1 & v2 specs for diff testing
│   │       ├── shop_v1.json
│   │       └── shop_v2.json
│   │
│   └── tests/                            # Automated Python test suite & benchmark (PRD §17 & §19)
│       ├── __init__.py
│       ├── test_reader.py
│       ├── test_fastapi_parser.py
│       ├── test_openapi_generator.py
│       ├── test_validator.py
│       ├── test_diff_engine.py
│       └── test_benchmark.py             # Verifies < 2s parse speed for 10,000-line codebase
│
└── frontend/                             # React + Vite + Bootstrap 5 Web App (PRD §12–14)
    ├── .env.example                      # Frontend public config (VITE_API_BASE_URL)
    ├── README.md
    ├── index.html                        # Lean HTML entry point (mount div + module script only)
    ├── package.json                      # React 18, Vite, Bootstrap 5, React Router, Swagger UI, Vitest
    ├── vite.config.js                    # Vite build & /api dev proxy
    ├── public/
    │   └── favicon.svg
    ├── src/
    │   ├── main.jsx                      # React mount & Bootstrap CSS import
    │   ├── App.jsx                       # Layout shell & screen routing
    │   ├── assets/
    │   │   └── logo.svg
    │   ├── styles/                       # Separated CSS & WCAG 2.2 AA contrast tokens
    │   │   ├── variables.css
    │   │   └── main.css
    │   ├── config/
    │   │   └── constants.js              # Supported frameworks, UI labels & route paths
    │   ├── state/
    │   │   └── AppContext.jsx            # Project, Parser, Specification, Diff & UI states
    │   ├── services/                     # Client API & local persistence boundary
    │   │   ├── apiClient.js              # Talks to backend HTTP API
    │   │   └── ProjectStorage.js         # PRD ProjectStorage (LocalStorage metadata + JSON export)
    │   ├── utils/
    │   │   ├── fileHelpers.js
    │   │   └── diffHelpers.js
    │   ├── pages/                        # PRD §8 Screen Inventory
    │   │   ├── DashboardPage.jsx         # Dashboard
    │   │   ├── CodebaseImportPage.jsx    # Codebase Import
    │   │   ├── AstAnalysisPage.jsx       # AST Analysis
    │   │   ├── SpecificationEditorPage.jsx # Specification Editor
    │   │   ├── ValidationResultsPage.jsx # Validation Results
    │   │   ├── InteractiveViewerPage.jsx # Interactive API Viewer
    │   │   ├── SpecificationDiffPage.jsx # Specification Diff
    │   │   ├── ExportCenterPage.jsx      # Export Center
    │   │   └── SettingsHistoryPage.jsx   # Settings / History
    │   └── components/                   # PRD §9 Component Breakdown
    │       ├── common/
    │       │   ├── SidebarNav.jsx        # Responsive navigation (collapsible on mobile)
    │       │   ├── StateBanner.jsx       # Loading/Empty/Error/Partial/Unsupported states (PRD §11)
    │       │   └── StatusBadge.jsx       # Color + text badges (never color-only, PRD §13)
    │       ├── import/
    │       │   ├── ProjectUploader.jsx   # PRD ProjectUploader
    │       │   └── FrameworkSelector.jsx # PRD FrameworkSelector
    │       ├── analysis/
    │       │   ├── RouteTable.jsx        # Extracted routes, methods, params & warnings
    │       │   └── MetadataEditor.jsx    # Manual metadata review + future AI suggestion controls
    │       ├── viewer/
    │       │   ├── SwaggerPreview.jsx    # PRD SwaggerPreview (Swagger UI)
    │       │   └── ValidationPanel.jsx   # Validation errors, warnings & line/path refs
    │       ├── diff/
    │       │   └── SpecDiffViewer.jsx    # Added / removed / modified comparison table
    │       └── export/
    │           └── ExportControls.jsx    # OpenAPI YAML/JSON (+ future Postman/SDK) downloads
    └── tests/
        └── .gitkeep
```

---

## 2. Optional Stretch Extension (Added Post-MVP)

Per PRD §16 (*"Complete one supported framework end to end before adding a second framework or mobile companion app"*), the optional React Native (**Expo Go**) companion is kept out of the initial repository until the core web MVP is complete:

```text
mobile/                                   # Added later as an isolated Expo Go workspace
├── .env.example
├── app.json
├── package.json
└── src/
    ├── App.jsx
    ├── screens/
    │   └── MobileReviewScreen.jsx        # PRD §8 Mobile Review
    ├── components/
    │   ├── ReviewCard.jsx                # PRD §9 ReviewCard
    │   └── SwipeReviewer.jsx             # PRD §9 SwipeReviewer (swipe + accessible button controls)
    └── services/
        └── reviewStorage.js              # Local device ReviewRecord storage
```

---

## 3. PRD Mapping Quick Reference

| PRD Requirement | Where It Lives in the Repo |
| :--- | :--- |
| **§8 Screen Inventory** (`9` web screens) | `frontend/src/pages/*Page.jsx` |
| **§9 Core Components** (`ASTParser` → `ExportManager`) | `backend/speccraft/` + `frontend/src/components/` |
| **§10 Data Entities** (`Project` → `ReviewRecord`) | `backend/speccraft/models.py` |
| **§11 UI States** (`11` states) | `frontend/src/components/common/StateBanner.jsx` |
| **§13 Safety & Accessibility** | `backend/speccraft/utils/path_safety.py`, `frontend/src/styles/` |
| **§17 Benchmark (`< 2s` / 10k LOC)** | `backend/tests/test_benchmark.py`, `docs/benchmark_report.md` |
| **Future AI Integration** | `backend/speccraft/ai/enricher.py` + `prompts/` |

