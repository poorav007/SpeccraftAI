import React, { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import Navbar from "./components/common/Navbar.jsx";
import AstAnalysisPage from "./pages/AstAnalysisPage.jsx";
import CodebaseImportPage from "./pages/CodebaseImportPage.jsx";
import ExportCenterPage from "./pages/ExportCenterPage.jsx";
import SpecificationDiffPage from "./pages/SpecificationDiffPage.jsx";
import SpecificationEditorPage from "./pages/SpecificationEditorPage.jsx";
import { checkBackendHealth, deleteOverlayEntry, saveOverlayEntry } from "./services/apiClient.js";
import { STORAGE_KEY, loadState, resetState, saveState } from "./utils/localStorage.js";
import { updateEndpointMetadata } from "./utils/routeHelpers.js";

const WAKE_BUDGET_SECONDS = 50;

export default function App() {
  const [state, setState] = useState(() => loadState());
  const [activeScreen, setActiveScreen] = useState("import");
  const [parseMetadata, setParseMetadata] = useState({
    schemas: {},
    metrics: null,
    diagnostics: [],
    orphanedOverlayKeys: [],
  });
  const [backendStatus, setBackendStatus] = useState({
    checked: false,
    online: false,
    waking: false,
    hasConnectedOnce: false,
    manualLocalMode: false,
  });
  const [wakeElapsedSeconds, setWakeElapsedSeconds] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;
    let wakeInterval = null;

    checkBackendHealth({
      retryOnColdStart: true,
      maxWaitMs: WAKE_BUDGET_SECONDS * 1000,
      signal: controller.signal,
      onWaking: () => {
        if (!mounted) return;
        setWakeElapsedSeconds(0);
        setBackendStatus((prev) => ({
          ...prev,
          checked: false,
          online: false,
          waking: true,
        }));
        const startedAt = Date.now();
        wakeInterval = setInterval(() => {
          if (mounted) {
            setWakeElapsedSeconds(
              Math.min(WAKE_BUDGET_SECONDS, Math.floor((Date.now() - startedAt) / 1000))
            );
          }
        }, 1000);
      },
    }).then((res) => {
      if (wakeInterval) clearInterval(wakeInterval);
      if (!mounted || res.aborted) return;
      setBackendStatus((prev) => ({
        ...prev,
        checked: true,
        online: res.ok,
        waking: false,
        hasConnectedOnce: prev.hasConnectedOnce || res.ok,
      }));
      if (res.ok && res.wakingAttempted) {
        toast.success("Cloud API connected and ready.");
      } else if (!res.ok && res.wakingAttempted) {
        toast.warning("Cloud API timed out after 50s. Switched to Local Mode.");
      }
    });

    return () => {
      mounted = false;
      if (wakeInterval) clearInterval(wakeInterval);
      controller.abort();
    };
  }, []);

  function handleToggleManualLocalMode() {
    setBackendStatus((prev) => {
      if (!prev.hasConnectedOnce) return prev;
      const nextManual = !prev.manualLocalMode;
      toast.info(nextManual ? "Switched to Local Mode." : "Switched back to Cloud API.");
      return { ...prev, manualLocalMode: nextManual };
    });
  }

  function handleBackendConfirmedOnline() {
    setBackendStatus((prev) => ({
      ...prev,
      checked: true,
      online: true,
      waking: false,
      hasConnectedOnce: true,
      manualLocalMode: false,
    }));
  }

  const effectiveBackendOnline = backendStatus.manualLocalMode ? false : backendStatus.online;

  function handleParseSuccess({
    endpoints = [],
    openApiSpec = null,
    schemas = {},
    metrics = null,
    diagnostics = [],
    orphanedOverlayKeys = [],
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
      orphanedOverlayKeys: orphanedOverlayKeys || [],
    });

    const result = saveState(nextState);
    if (result.ok) {
      setState(nextState);
    }
    return result;
  }

  function handleUpdateEndpoint(updatedEndpoint) {
    const { _overlaySource = "human", ...cleanEndpoint } = updatedEndpoint;
    const updatedEndpoints = updateEndpointMetadata(state.endpoints, cleanEndpoint);
    const nextState = {
      ...state,
      endpoints: updatedEndpoints,
    };
    const result = saveState(nextState);
    if (result.ok) {
      setState(nextState);
    }
    // Persist non-destructive documentation overlay asynchronously when backend is online
    saveOverlayEntry(cleanEndpoint, _overlaySource);
    return result;
  }

  function handleDismissOrphanedKey(key) {
    setParseMetadata((prev) => ({
      ...prev,
      orphanedOverlayKeys: (prev.orphanedOverlayKeys || []).filter((k) => k !== key),
    }));
    deleteOverlayEntry(key);
  }

  function handleReset() {
    const fresh = resetState();
    setState(fresh);
    setParseMetadata({ schemas: {}, metrics: null, diagnostics: [], orphanedOverlayKeys: [] });
    setActiveScreen("import");
  }

  return (
    <div className="container-xl py-3">
      <Toaster position="bottom-right" richColors />
      {/* Global Application Navigation Bar */}
      <Navbar
        activeScreen={activeScreen}
        onSelectScreen={setActiveScreen}
        endpointCount={(state.endpoints || []).length}
        hasSpec={Boolean(state.specs?.["parsed-preview"])}
        backendStatus={{ ...backendStatus, online: effectiveBackendOnline }}
        onToggleLocalMode={handleToggleManualLocalMode}
        onReset={handleReset}
      />

      {/* Screen Router */}
      <main>
        {activeScreen === "import" && (
          <div>
            <CodebaseImportPage
              endpoints={state.endpoints}
              backendStatus={{ ...backendStatus, online: effectiveBackendOnline }}
              wakeElapsedSeconds={wakeElapsedSeconds}
              wakeBudgetSeconds={WAKE_BUDGET_SECONDS}
              onBackendConfirmedOnline={handleBackendConfirmedOnline}
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
            orphanedOverlayKeys={parseMetadata.orphanedOverlayKeys}
            onDismissOrphanedKey={handleDismissOrphanedKey}
            onUpdateEndpoint={handleUpdateEndpoint}
            onNavigate={(screenId) => setActiveScreen(screenId)}
          />
        )}

        {activeScreen === "editor" && (
          <SpecificationEditorPage
            endpoints={state.endpoints || []}
            schemas={parseMetadata.schemas}
            initialSpec={state.specs?.["parsed-preview"] || null}
            onSaveSpec={(spec, format) => {
              const nextState = {
                ...state,
                specs: {
                  ...state.specs,
                  "parsed-preview": spec,
                },
              };
              saveState(nextState);
              setState(nextState);
            }}
            onNavigate={(screenId) => setActiveScreen(screenId)}
          />
        )}

        {activeScreen === "diff" && (
          <SpecificationDiffPage
            currentSpec={state.specs?.["parsed-preview"] || null}
            onNavigate={(screenId) => setActiveScreen(screenId)}
          />
        )}

        {activeScreen === "export" && (
          <ExportCenterPage
            spec={state.specs?.["parsed-preview"] || null}
            endpoints={state.endpoints || []}
            diagnostics={parseMetadata.diagnostics}
            onLoadSampleSpec={(sampleSpec) => {
              const nextState = {
                ...state,
                specs: {
                  ...state.specs,
                  "parsed-preview": sampleSpec,
                },
              };
              saveState(nextState);
              setState(nextState);
            }}
            onNavigate={(screenId) => setActiveScreen(screenId)}
          />
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
