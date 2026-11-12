import { useState } from "react";
import { parseRouteCode } from "../../utils/parser.js";

const ALLOWED_EXTENSIONS = /\.(js|mjs|py)$/i;

export default function ProjectUploader({ initialEndpoints = [], onParseSuccess }) {
  const [code, setCode] = useState("");
  const [fileName, setFileName] = useState("");
  const [endpoints, setEndpoints] = useState(initialEndpoints);
  const [status, setStatus] = useState(null);

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    if (!ALLOWED_EXTENSIONS.test(file.name)) {
      setStatus({
        type: "danger",
        message: `Unsupported file "${file.name}". Please upload a .js or .py file.`,
      });
      return;
    }

    try {
      const content = await file.text();
      setCode(content);
      setFileName(file.name);
      setStatus({
        type: "info",
        message: `Loaded "${file.name}" (${file.size} bytes). Click "Generate OpenAPI" to parse.`,
      });
    } catch {
      setStatus({
        type: "danger",
        message: `Could not read "${file.name}". Please check the file and try again.`,
      });
    }
  }

  function handleParseSubmit(event) {
    event.preventDefault();
    const result = parseRouteCode(code);

    if (result.error) {
      setEndpoints([]);
      setStatus({
        type: "danger",
        message: `${result.error} (${result.parseTimeMs} ms)`,
      });
      return;
    }

    setEndpoints(result.endpoints);
    const saveOutcome = onParseSuccess?.(result);

    if (saveOutcome && !saveOutcome.ok) {
      setStatus({
        type: "warning",
        message: `Parsed ${result.endpoints.length} route(s) in ${result.parseTimeMs} ms, but localStorage save failed: ${saveOutcome.error}`,
      });
      return;
    }

    setStatus({
      type: "success",
      message: `Parsed ${result.endpoints.length} route(s) in ${result.parseTimeMs} ms and saved to localStorage.`,
    });
  }

  return (
    <div className="card shadow-sm">
      <div className="card-header bg-body-tertiary">
        <h2 className="h5 mb-0">Spec Uploader</h2>
      </div>
      <div className="card-body">
        <form onSubmit={handleParseSubmit} noValidate>
          <div className="mb-3">
            <label htmlFor="route-code-input" className="form-label fw-semibold">
              Paste your Express/Flask route code
            </label>
            <textarea
              id="route-code-input"
              className="form-control font-monospace"
              rows={8}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="// Example: app.get('/api/users', ...)"
            />
          </div>

          <div className="d-flex flex-column flex-md-row align-items-stretch align-items-md-end justify-content-between gap-3 mt-3">
            <div className="flex-grow-1">
              <label htmlFor="route-file-input" className="form-label mb-1">
                Upload .js or .py file
              </label>
              <input
                id="route-file-input"
                type="file"
                accept=".js,.mjs,.py"
                className="form-control"
                onChange={handleFileChange}
              />
              {fileName && (
                <div className="form-text">Selected file: {fileName}</div>
              )}
            </div>

            <button type="submit" className="btn btn-primary text-nowrap">
              Generate OpenAPI
            </button>
          </div>
        </form>

        {status && (
          <div className={`alert alert-${status.type} mt-3 mb-0`} role="status">
            {status.message}
          </div>
        )}

        {endpoints.length > 0 && (
          <section className="mt-3" aria-label="Parsed routes">
            <h3 className="h6 text-muted mb-2">Extracted Routes ({endpoints.length})</h3>
            <ul className="list-group">
              {endpoints.map((ep) => (
                <li
                  key={`${ep.method}-${ep.path}`}
                  className="list-group-item d-flex align-items-center gap-2 font-monospace"
                >
                  <span className="badge text-bg-primary">{ep.method}</span>
                  <span className="text-break">{ep.path}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

