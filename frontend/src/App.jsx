import { useState } from "react";
import CodebaseImportPage from "./pages/CodebaseImportPage.jsx";
import { STORAGE_KEY, loadState, resetState, saveState } from "./utils/localStorage.js";

export default function App() {
  const [state, setState] = useState(() => loadState());

  function handleParseSuccess({ endpoints, openApiSpec }) {
    const nextState = {
      ...state,
      endpoints,
      specs: {
        ...state.specs,
        "parsed-preview": openApiSpec,
      },
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
  }

  return (
    <main className="container py-4">
      <header className="text-center mb-4">
        <h1 className="h3 mb-1">SpecCraft AI</h1>
        <p className="text-muted mb-0">
          Automated OpenAPI 3.0 Generator · Screen 1: Spec Uploader
        </p>
      </header>

      <CodebaseImportPage
        endpoints={state.endpoints}
        onParseSuccess={handleParseSuccess}
      />

      <div className="row justify-content-center mt-4">
        <div className="col-12 col-md-10 col-lg-8">
          <div className="card">
            <div className="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
              <span className="small fw-semibold">
                Persisted State (<code>localStorage[&apos;{STORAGE_KEY}&apos;]</code>)
              </span>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                onClick={handleReset}
              >
                Reset Seed State
              </button>
            </div>
            <div className="card-body">
              <pre className="mb-0 small" style={{ maxHeight: "260px", overflow: "auto" }}>
                {JSON.stringify(state, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
