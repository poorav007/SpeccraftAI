import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  checkBackendHealth,
  parseCodeSnippet,
  parseGithubRepo,
  uploadAndParseArchive,
} from "../../services/apiClient.js";
import { parseRouteCode } from "../../utils/parser.js";

const SAMPLE_FASTAPI_CODE = `from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Shop API", version="1.0.0")

class Item(BaseModel):
    name: str
    price: float
    category: Optional[str] = "general"

@app.get("/items", tags=["catalog"], summary="List Catalog Items")
def list_items(skip: int = 0, limit: int = 20):
    """Retrieve paginated items from inventory."""
    return []

@app.post("/items", status_code=201, tags=["catalog"], summary="Create Item")
def create_item(payload: Item):
    """Add a new item to catalog."""
    return payload

@app.get("/items/{item_id}", tags=["catalog"], summary="Get Single Item")
def get_item(item_id: int):
    """Fetch item by unique identifier."""
    return {"id": item_id, "name": "Sample", "price": 10.0}
`;

export default function ProjectUploader({ initialEndpoints = [], onParseSuccess }) {
  const [mode, setMode] = useState("github"); // 'github', 'file', or 'code'
  const [githubUrl, setGithubUrl] = useState("");
  const [githubRef, setGithubRef] = useState("");
  const [code, setCode] = useState(SAMPLE_FASTAPI_CODE);
  const [selectedFile, setSelectedFile] = useState(null);
  const [endpoints, setEndpoints] = useState(initialEndpoints);
  const [metrics, setMetrics] = useState(null);
  const [diagnostics, setDiagnostics] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [backendOnline, setBackendOnline] = useState(null); // true, false, 'waking', or null

  // Probe backend health on mount with cold-start wake handling
  useEffect(() => {
    let mounted = true;
    async function probeBackend() {
      const health = await checkBackendHealth({
        retryOnColdStart: true,
        onWaking: () => {
          if (mounted) {
            setBackendOnline("waking");
            toast.info("Waking up cloud backend (free tier cold start)...");
          }
        },
      });
      if (mounted) {
        setBackendOnline(health.ok);
        if (health.ok && health.wakingAttempted) {
          toast.success("Cloud API connected and ready.");
        }
      }
    }
    probeBackend();
    return () => {
      mounted = false;
    };
  }, []);

  function handleFileSelected(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".zip") && !lowerName.endsWith(".py") && !lowerName.endsWith(".js")) {
      setStatus({
        type: "danger",
        message: `Unsupported file "${file.name}". Please upload a .zip archive, .py file, or .js file.`,
      });
      return;
    }

    setSelectedFile(file);
    setStatus({
      type: "info",
      message: `Selected "${file.name}" (${(file.size / 1024).toFixed(1)} KB). Click "Run AST Extraction" to process.`,
    });
  }

  async function handleExtract(event) {
    event.preventDefault();
    setIsLoading(true);
    setStatus(null);
    setDiagnostics([]);

    try {
      let extractedData = null;

      // 1. If backend is online (or user submitted a GitHub URL requiring backend), call FastAPI bridge
      if (mode === "github") {
        if (!githubUrl.trim()) {
          throw new Error("Please enter a public GitHub repository URL.");
        }
        const res = await parseGithubRepo(githubUrl.trim(), githubRef.trim() || null);
        if (!res.ok) {
          throw new Error(res.error);
        }
        extractedData = res.result;
        setBackendOnline(true);
      }

      if (extractedData || backendOnline === true) {
        if (!extractedData) {
          if (mode === "file" && selectedFile) {
            const res = await uploadAndParseArchive(selectedFile);
            if (!res.ok) {
              throw new Error(res.error);
            }
            extractedData = res.result;
          } else if (code.trim()) {
            const res = await parseCodeSnippet(code, "snippet.py");
            if (!res.ok) {
              throw new Error(res.error);
            }
            extractedData = res.result;
          } else {
            throw new Error("Please select a file or enter code to extract.");
          }
        }

        // Set state from backend response
        setEndpoints(extractedData.endpoints || []);
        setDiagnostics(extractedData.diagnostics || []);
        setMetrics({
          filesScanned: extractedData.files_scanned,
          totalLoc: extractedData.total_loc,
          durationMs: extractedData.parse_duration_ms,
          engine: "SpecCraft Multi-Framework Analyzer",
        });

        // Pass up for localStorage persistence
        onParseSuccess?.({
          endpoints: extractedData.endpoints || [],
          openApiSpec: null,
          schemas: extractedData.schemas || {},
          diagnostics: extractedData.diagnostics || [],
          orphanedOverlayKeys: extractedData.orphaned_overlay_keys || [],
          metrics: {
            filesScanned: extractedData.files_scanned,
            totalLoc: extractedData.total_loc,
            durationMs: extractedData.parse_duration_ms,
          },
        });

        const okMsg = `Discovered ${extractedData.endpoints.length} endpoint(s) across ${extractedData.files_scanned} file(s) in ${extractedData.parse_duration_ms.toFixed(1)} ms.`;
        setStatus({ type: "success", message: okMsg });
        toast.success(okMsg);
      } else {
        // 2. Client-side fallback if backend is offline
        const localRes = parseRouteCode(code);
        if (localRes.error) {
          throw new Error(localRes.error);
        }

        setEndpoints(localRes.endpoints);
        setMetrics({
          filesScanned: 1,
          totalLoc: code.split("\n").length,
          durationMs: localRes.parseTimeMs,
          engine: "Client-side Regex Fallback",
        });

        onParseSuccess?.(localRes);

        setStatus({
          type: "warning",
          message: `Backend API offline. Extracted ${localRes.endpoints.length} route(s) via client fallback in ${localRes.parseTimeMs} ms.`,
        });
      }
    } catch (err) {
      setStatus({
        type: "danger",
        message: err.message || "Failed to extract routes.",
      });
    } finally {
      setIsLoading(false);
    }
  }

  function getMethodBadgeClass(method) {
    const m = (method || "").toUpperCase();
    if (m === "GET") return "text-bg-primary";
    if (m === "POST") return "text-bg-success";
    if (m === "PUT" || m === "PATCH") return "text-bg-warning";
    if (m === "DELETE") return "text-bg-danger";
    return "text-bg-secondary";
  }

  return (
    <div className="card shadow-sm border-0">
      {/* Header with Backend Status Badge & Outcome-Focused Copy */}
      <div className="card-header bg-body-tertiary d-flex flex-wrap justify-content-between align-items-center gap-2 py-3">
        <div>
          <h2 className="h5 mb-0 fw-bold">Import API Project</h2>
          <small className="text-muted">
            Connect a GitHub repo or upload FastAPI / Flask / Express code → generate OpenAPI docs &amp; breaking-change checks in under 1 second
          </small>
        </div>
        <div>
          {backendOnline === true && (
            <span className="badge text-bg-success d-inline-flex align-items-center gap-1.5 px-2.5 py-1.5 shadow-xs">
              <span className="spinner-grow spinner-grow-sm" style={{ width: "8px", height: "8px" }} />
              Cloud API Connected
            </span>
          )}
          {backendOnline === "waking" && (
            <span className="badge text-bg-info d-inline-flex align-items-center gap-1.5 px-2.5 py-1.5 shadow-xs">
              ⏳ Waking up backend...
            </span>
          )}
          {backendOnline === false && (
            <span className="badge text-bg-warning d-inline-flex align-items-center gap-1.5 px-2.5 py-1.5 shadow-xs">
              Local Mode
            </span>
          )}
          {backendOnline === null && (
            <span className="badge text-bg-secondary px-2.5 py-1.5">Connecting...</span>
          )}
        </div>
      </div>

      <div className="card-body p-4">
        {/* Mode Selector Tabs */}
        <ul className="nav nav-pills mb-3 flex-wrap gap-1" role="tablist">
          <li className="nav-item" role="presentation">
            <button
              type="button"
              className={`nav-link ${mode === "github" ? "active" : ""}`}
              onClick={() => { setMode("github"); setStatus(null); }}
            >
              🔗 Paste GitHub Repo URL
            </button>
          </li>
          <li className="nav-item" role="presentation">
            <button
              type="button"
              className={`nav-link ${mode === "file" ? "active" : ""}`}
              onClick={() => { setMode("file"); setStatus(null); }}
            >
              📦 Project Archive (.zip / .py / .js)
            </button>
          </li>
          <li className="nav-item" role="presentation">
            <button
              type="button"
              className={`nav-link ${mode === "code" ? "active" : ""}`}
              onClick={() => { setMode("code"); setStatus(null); }}
            >
              📝 Code Snippet
            </button>
          </li>
        </ul>

        <form onSubmit={handleExtract} noValidate>
          {/* GitHub Repo URL Mode */}
          {mode === "github" && (
            <div className="mb-3">
              <div className="row g-2">
                <div className="col-12 col-md-8">
                  <label htmlFor="github-repo-input" className="form-label fw-semibold">
                    Public GitHub Repository URL
                  </label>
                  <input
                    id="github-repo-input"
                    type="url"
                    className="form-control"
                    placeholder="https://github.com/owner/fastapi-service"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                  />
                </div>
                <div className="col-12 col-md-4">
                  <label htmlFor="github-ref-input" className="form-label fw-semibold">
                    Branch / Tag (Optional)
                  </label>
                  <input
                    id="github-ref-input"
                    type="text"
                    className="form-control"
                    placeholder="main"
                    value={githubRef}
                    onChange={(e) => setGithubRef(e.target.value)}
                  />
                </div>
              </div>
              <div className="form-text small mt-1">
                Analyzes FastAPI, Flask, and Express.js repositories without executing your code (up to 10 MB).
              </div>
            </div>
          )}

          {/* File Upload Mode */}
          {mode === "file" && (
            <div className="mb-3">
              <label htmlFor="project-file-input" className="form-label fw-semibold">
                Upload Project Archive (.zip) or API Route File (.py / .js / .ts)
              </label>
              <div className="border border-2 border-dashed rounded p-4 text-center bg-light">
                <input
                  id="project-file-input"
                  type="file"
                  accept=".zip,.py,.js,.ts"
                  className="form-control mb-2"
                  onChange={handleFileSelected}
                />
                <div className="small text-muted">
                  Drop a project .zip or single route file (max 10 MB). Analyzed statically — your code is never executed.
                </div>
                {selectedFile && (
                  <div className="mt-2 fw-semibold text-primary">
                    ✓ Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Code Editor Mode */}
          {mode === "code" && (
            <div className="mb-3">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <label htmlFor="route-code-input" className="form-label fw-semibold mb-0">
                  FastAPI Route Code Snippet
                </label>
                <button
                  type="button"
                  className="btn btn-sm btn-link text-decoration-none p-0"
                  onClick={() => setCode(SAMPLE_FASTAPI_CODE)}
                >
                  Reset Sample Code
                </button>
              </div>
              <textarea
                id="route-code-input"
                className="form-control font-monospace"
                rows={10}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="from fastapi import FastAPI..."
              />
            </div>
          )}

          {/* Action Bar */}
          <div className="d-flex justify-content-end gap-2 mt-4">
            <button
              type="submit"
              className="btn btn-primary px-4 py-2 fw-semibold d-inline-flex align-items-center gap-2"
              disabled={isLoading}
            >
              {isLoading && <span className="spinner-border spinner-border-sm" role="status" />}
              {isLoading ? "Running AST Analysis..." : "🚀 Run AST Extraction"}
            </button>
          </div>
        </form>

        {/* Status Alerts */}
        {status && (
          <div className={`alert alert-${status.type} mt-4 mb-0 d-flex align-items-center gap-2`} role="alert">
            <span>{status.message}</span>
          </div>
        )}

        {/* AST Metrics Dashboard */}
        {metrics && (
          <div className="row g-3 mt-3">
            <div className="col-6 col-md-3">
              <div className="p-3 bg-body-tertiary rounded border text-center">
                <div className="text-muted small text-uppercase fw-semibold">Files Scanned</div>
                <div className="h4 mb-0 fw-bold">{metrics.filesScanned}</div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="p-3 bg-body-tertiary rounded border text-center">
                <div className="text-muted small text-uppercase fw-semibold">Total LOC</div>
                <div className="h4 mb-0 fw-bold">{metrics.totalLoc}</div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="p-3 bg-body-tertiary rounded border text-center">
                <div className="text-muted small text-uppercase fw-semibold">Parse Duration</div>
                <div className="h4 mb-0 fw-bold text-success">
                  {metrics.durationMs < 1 ? "< 1" : metrics.durationMs.toFixed(1)} ms
                </div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="p-3 bg-body-tertiary rounded border text-center">
                <div className="text-muted small text-uppercase fw-semibold">Endpoints</div>
                <div className="h4 mb-0 fw-bold text-primary">{endpoints.length}</div>
              </div>
            </div>
          </div>
        )}

        {/* PRD Diagnostics Warnings */}
        {diagnostics.length > 0 && (
          <div className="mt-4">
            <h3 className="h6 fw-bold text-warning-emphasis mb-2">
              Diagnostics & Warnings ({diagnostics.length})
            </h3>
            <div className="list-group">
              {diagnostics.map((diag, idx) => (
                <div key={idx} className="list-group-item list-group-item-warning">
                  <div className="d-flex w-100 justify-content-between align-items-center">
                    <strong className="badge bg-warning text-dark font-monospace">{diag.code}</strong>
                    <small className="text-muted">Line {diag.line || "N/A"}</small>
                  </div>
                  <p className="mb-1 mt-1 small">{diag.message}</p>
                  {diag.hint && <small className="text-muted fst-italic">💡 Hint: {diag.hint}</small>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Extracted Routes List */}
        {endpoints.length > 0 && (
          <section className="mt-4" aria-label="Extracted API routes">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <h3 className="h6 fw-bold mb-0">Discovered Routes ({endpoints.length})</h3>
              <span className="badge bg-success-subtle text-success border border-success-subtle">
                Ready for OpenAPI Export
              </span>
            </div>
            <ul className="list-group shadow-xs">
              {endpoints.map((ep, idx) => (
                <li
                  key={`${ep.method}-${ep.path}-${idx}`}
                  className="list-group-item d-flex align-items-center justify-content-between font-monospace"
                >
                  <div className="d-flex align-items-center gap-2">
                    <span className={`badge ${getMethodBadgeClass(ep.method)} px-2 py-1`}>
                      {(ep.method || "").toUpperCase()}
                    </span>
                    <span className="fw-semibold text-break">{ep.path}</span>
                  </div>
                  {ep.operation_id && (
                    <span className="badge bg-light text-dark border font-monospace small">
                      {ep.operation_id}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
