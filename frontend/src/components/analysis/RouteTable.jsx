import React, { useMemo, useState } from "react";
import {
  computeMethodStats,
  extractAllTags,
  filterEndpoints,
  getMethodBadgeClass,
} from "../../utils/routeHelpers.js";

/**
 * Interactive Route Table component with method badges, live search,
 * tag filters, parameter inspection, and metadata editing triggers.
 */
export default function RouteTable({
  endpoints = [],
  onInspectEndpoint,
  onEditEndpoint,
  onNavigateToImport,
}) {
  const [search, setSearch] = useState("");
  const [selectedMethod, setSelectedMethod] = useState("ALL");
  const [selectedTag, setSelectedTag] = useState("ALL");
  const [hasWarningsOnly, setHasWarningsOnly] = useState(false);

  // Compute stats and tags dynamically from current endpoints
  const methodStats = useMemo(() => computeMethodStats(endpoints), [endpoints]);
  const allTags = useMemo(() => extractAllTags(endpoints), [endpoints]);

  // Compute total warnings across all endpoints
  const totalWarnings = useMemo(
    () =>
      endpoints.reduce(
        (sum, ep) => sum + ((ep.warnings && ep.warnings.length) || 0),
        0
      ),
    [endpoints]
  );

  // Filtered endpoints based on current controls
  const filtered = useMemo(
    () =>
      filterEndpoints(endpoints, {
        search,
        method: selectedMethod,
        tag: selectedTag,
        hasWarningsOnly,
      }),
    [endpoints, search, selectedMethod, selectedTag, hasWarningsOnly]
  );

  function resetFilters() {
    setSearch("");
    setSelectedMethod("ALL");
    setSelectedTag("ALL");
    setHasWarningsOnly(false);
  }

  // Helper to render path with highlighted parameters e.g. /items/{item_id}
  function renderPath(path = "") {
    const parts = path.split(/(\{[^}]+\})/g);
    return parts.map((part, i) => {
      if (part.startsWith("{") && part.endsWith("}")) {
        return (
          <span key={i} className="path-param-highlight">
            {part}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  }

  if (endpoints.length === 0) {
    return (
      <div className="card text-center p-5 border-dashed">
        <div className="card-body">
          <div className="display-6 mb-3">🔍</div>
          <h5 className="card-title fw-bold">No Extracted Routes Yet</h5>
          <p className="card-text text-muted mb-4">
            Upload a FastAPI project (.zip) or paste a code snippet in Screen 1 to extract
            API routes, schemas, and diagnostics.
          </p>
          {onNavigateToImport && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={onNavigateToImport}
            >
              Go to Codebase Importer (Screen 1) →
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="card shadow-sm border-0">
      {/* Controls Bar */}
      <div className="card-header bg-white border-bottom p-3">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-3">
          {/* Method Filter Buttons */}
          <div className="btn-group btn-group-sm flex-wrap" role="group" aria-label="Method filter">
            {["ALL", "GET", "POST", "PUT", "DELETE", "PATCH"].map((m) => {
              const count = methodStats[m] || 0;
              const isActive = selectedMethod === m;
              return (
                <button
                  key={m}
                  type="button"
                  className={`btn ${
                    isActive ? "btn-dark fw-bold" : "btn-outline-secondary"
                  }`}
                  onClick={() => setSelectedMethod(m)}
                >
                  {m} <span className="badge bg-light text-dark ms-1">{count}</span>
                </button>
              );
            })}
          </div>

          {/* Quick Warning Filter */}
          {totalWarnings > 0 && (
            <div className="form-check form-switch mb-0 small">
              <input
                className="form-check-input"
                type="checkbox"
                id="warningFilterToggle"
                checked={hasWarningsOnly}
                onChange={(e) => setHasWarningsOnly(e.target.checked)}
              />
              <label className="form-check-label fw-semibold text-warning-emphasis" htmlFor="warningFilterToggle">
                ⚠️ Warnings only ({totalWarnings})
              </label>
            </div>
          )}
        </div>

        {/* Search & Tag Filter Inputs */}
        <div className="row g-2 align-items-center">
          <div className="col-12 col-md-7 col-lg-8">
            <div className="input-group input-group-sm">
              <span className="input-group-text bg-light">🔎</span>
              <input
                type="text"
                className="form-control"
                placeholder="Search by path, operation ID, summary, or tags..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {search && (
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={() => setSearch("")}
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          <div className="col-12 col-md-5 col-lg-4">
            <select
              className="form-select form-select-sm"
              value={selectedTag}
              onChange={(e) => setSelectedTag(e.target.value)}
              aria-label="Filter by tag"
            >
              <option value="ALL">All Tags ({allTags.length})</option>
              {allTags.map((t) => (
                <option key={t} value={t}>
                  Tag: {t}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Results Header Count */}
      <div className="bg-light px-3 py-2 border-bottom d-flex justify-content-between align-items-center small text-muted">
        <span>
          Showing <strong>{filtered.length}</strong> of <strong>{endpoints.length}</strong> route(s)
        </span>
        {(search || selectedMethod !== "ALL" || selectedTag !== "ALL" || hasWarningsOnly) && (
          <button
            type="button"
            className="btn btn-link btn-sm p-0 text-decoration-none"
            onClick={resetFilters}
          >
            Clear all filters
          </button>
        )}
      </div>

      {/* Table Body */}
      {filtered.length === 0 ? (
        <div className="card-body text-center py-5">
          <p className="text-muted mb-2">No endpoints match the active filters.</p>
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={resetFilters}>
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light small text-uppercase text-secondary">
              <tr>
                <th style={{ width: "90px" }}>Method</th>
                <th>Route Path</th>
                <th>Operation ID</th>
                <th>Tags</th>
                <th style={{ width: "100px" }}>Params</th>
                <th style={{ width: "90px" }}>Status</th>
                <th style={{ width: "130px" }} className="text-end">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((ep, idx) => {
                const methodBadge = getMethodBadgeClass(ep.method);
                const hasWarnings = (ep.warnings || []).length > 0;
                const paramCount = (ep.parameters || []).length;

                return (
                  <tr key={`${ep.path}-${ep.method}-${idx}`} className="route-row">
                    <td>
                      <span className={`badge ${methodBadge} px-2 py-1`}>
                        {(ep.method || "").toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <code className="text-dark fw-semibold">{renderPath(ep.path)}</code>
                      {ep.summary && (
                        <div className="small text-muted text-truncate" style={{ maxWidth: "340px" }}>
                          {ep.summary}
                        </div>
                      )}
                    </td>
                    <td>
                      <code className="small text-secondary">{ep.operation_id || "—"}</code>
                    </td>
                    <td>
                      {(ep.tags || []).length > 0 ? (
                        ep.tags.map((t) => (
                          <span key={t} className="badge bg-secondary me-1 small">
                            {t}
                          </span>
                        ))
                      ) : (
                        <span className="text-muted small">—</span>
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-sm btn-light border py-0 px-2 small"
                        onClick={() => onInspectEndpoint?.(ep)}
                        title="View parameters"
                      >
                        {paramCount} {paramCount === 1 ? "param" : "params"}
                      </button>
                    </td>
                    <td>
                      {hasWarnings ? (
                        <span
                          className="badge bg-warning text-dark"
                          title={ep.warnings.map((w) => w.code).join(", ")}
                        >
                          ⚠️ {ep.warnings[0]?.code || "Warn"}
                        </span>
                      ) : (
                        <span className="badge bg-success-subtle text-success border border-success-subtle">
                          ✓ AST Valid
                        </span>
                      )}
                    </td>
                    <td className="text-end">
                      <div className="btn-group btn-group-sm">
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          onClick={() => onInspectEndpoint?.(ep)}
                          title="Inspect full details"
                        >
                          🔍
                        </button>
                        <button
                          type="button"
                          className="btn btn-outline-primary"
                          onClick={() => onEditEndpoint?.(ep)}
                          title="Edit metadata"
                        >
                          ✏️
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

