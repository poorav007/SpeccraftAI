import React, { useState } from "react";
import Navbar from "./components/common/Navbar.jsx";
import AstAnalysisPage from "./pages/AstAnalysisPage.jsx";
import CodebaseImportPage from "./pages/CodebaseImportPage.jsx";
import { STORAGE_KEY, loadState, resetState, saveState } from "./utils/localStorage.js";
import { updateEndpointMetadata } from "./utils/routeHelpers.js";

export default function App() {
  const [state, setState] = useState(() => loadState());
  const [activeScreen, setActiveScreen] = useState("import");
  const [parseMetadata, setParseMetadata] = useState({
    schemas: {},
    metrics: null,
    diagnostics: [],
  });

  function handleParseSuccess({
    endpoints = [],
    openApiSpec = null,
    schemas = {},
    metrics = null,
    diagnostics = [],
  }) {
    const nextState = {
      ...state,
      endpoints,
      specs: openApiSpec
        ? {
            ...state.specs,
            "parsed-preview": openApiSpec,
          }
        : state.specs,
    };

    setParseMetadata({
      schemas: schemas || {},
      metrics: metrics || null,
      diagnostics: diagnostics || [],
    });

    const result = saveState(nextState);
    if (result.ok) {
      setState(nextState);
    }
    return result;
  }

  function handleUpdateEndpoint(updatedEndpoint) {
    const updatedEndpoints = updateEndpointMetadata(state.endpoints, updatedEndpoint);
    const nextState = {
      ...state,
      endpoints: updatedEndpoints,
    };
    const result = saveState(nextState);
    if (result.ok) {
      setState(nextState);
    }
    return result;
  }

  function handleReset() {
    const fresh = resetState();
    setState(fresh);
    setParseMetadata({ schemas: {}, metrics: null, diagnostics: [] });
    setActiveScreen("import");
  }

  return (
    <div className="container-xl py-3">
      {/* Global Application Navigation Bar */}
      <Navbar
        activeScreen={activeScreen}
        onSelectScreen={setActiveScreen}
        endpointCount={(state.endpoints || []).length}
        hasSpec={Boolean(state.specs?.["parsed-preview"])}
        onReset={handleReset}
      />

      {/* Screen Router */}
      <main>
        {activeScreen === "import" && (
          <div>
            <CodebaseImportPage
              endpoints={state.endpoints}
              onParseSuccess={handleParseSuccess}
            />

            {(state.endpoints || []).length > 0 && (
              <div className="row justify-content-center mt-3">
                <div className="col-12 col-md-10 col-lg-8 text-end">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setActiveScreen("analysis")}
                  >
                    Review {state.endpoints.length} Extracted Route(s) in Screen 2 →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {activeScreen === "analysis" && (
          <AstAnalysisPage
            endpoints={state.endpoints || []}
            schemas={parseMetadata.schemas}
            metrics={parseMetadata.metrics}
            diagnostics={parseMetadata.diagnostics}
            onUpdateEndpoint={handleUpdateEndpoint}
            onNavigate={(screenId) => setActiveScreen(screenId)}
          />
        )}

        {activeScreen === "editor" && (
          <div className="card shadow-sm border-0 text-center py-5 my-4">
            <div className="card-body">
              <span className="badge bg-primary-subtle text-primary mb-2">Milestone: Day 7</span>
              <h3 className="h4 fw-bold">Screen 3: Swagger UI Preview & Spec Editor</h3>
              <p className="text-muted small mx-auto" style={{ maxWidth: "520px" }}>
                Interactive documentation preview through Swagger UI and live specification
                editing with real-time validation will be unlocked in Day 7.
              </p>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={() => setActiveScreen("analysis")}
              >
                ← Back to AST Analysis (Screen 2)
              </button>
            </div>
          </div>
        )}

        {activeScreen === "diff" && (
          <div className="card shadow-sm border-0 text-center py-5 my-4">
            <div className="card-body">
              <span className="badge bg-warning-subtle text-warning-emphasis mb-2">Milestone: Day 8</span>
              <h3 className="h4 fw-bold">Screen 4: Specification Diff Viewer</h3>
              <p className="text-muted small mx-auto" style={{ maxWidth: "520px" }}>
                Compare two OpenAPI specifications, detect breaking vs non-breaking changes,
                and inspect diff reports in Day 8.
              </p>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={() => setActiveScreen("analysis")}
              >
                ← Back to AST Analysis (Screen 2)
              </button>
            </div>
          </div>
        )}

        {activeScreen === "export" && (
          <div className="card shadow-sm border-0 text-center py-5 my-4">
            <div className="card-body">
              <span className="badge bg-success-subtle text-success mb-2">Milestone: Day 9</span>
              <h3 className="h4 fw-bold">Screen 5: Export Center</h3>
              <p className="text-muted small mx-auto" style={{ maxWidth: "520px" }}>
                Download validated OpenAPI 3.0 specs in YAML/JSON and Postman v2.1 collections.
              </p>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={() => setActiveScreen("analysis")}
              >
                ← Back to AST Analysis (Screen 2)
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Developer State Inspector Footer */}
      <footer className="mt-5 pt-3 border-top">
        <details className="text-muted small">
          <summary className="cursor-pointer user-select-none">
            Developer Persisted State (<code>localStorage[&apos;{STORAGE_KEY}&apos;]</code>)
          </summary>
          <div className="card mt-2 bg-light">
            <div className="card-body p-2">
              <pre className="mb-0 font-monospace" style={{ maxHeight: "200px", overflow: "auto", fontSize: "11px" }}>
                {JSON.stringify(state, null, 2)}
              </pre>
            </div>
          </div>
        </details>
      </footer>
    </div>
  );
}
