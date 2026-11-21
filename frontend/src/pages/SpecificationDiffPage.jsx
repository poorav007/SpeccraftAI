import React, { useEffect, useMemo, useState } from "react";
import SpecDiffViewer from "../components/diff/SpecDiffViewer.jsx";
import { SAMPLE_SHOP_V1, SAMPLE_SHOP_V2 } from "../config/sampleSpecs.js";
import { compareOpenApiSpecs } from "../services/apiClient.js";
import {
  compareSpecsClientSide,
  computeDiffStats,
  filterChanges,
} from "../utils/diffHelpers.js";

/**
 * Screen 4: Specification Diff Viewer Page (F14 & F15).
 * Enables developers to deterministically compare two OpenAPI 3.0 specs,
 * inspect breaking vs non-breaking changes, filter changes, and view deep diffs.
 */
export default function SpecificationDiffPage({
  currentSpec = null,
  onNavigate,
}) {
  const [baselineText, setBaselineText] = useState(() =>
    JSON.stringify(SAMPLE_SHOP_V1, null, 2)
  );
  const [targetText, setTargetText] = useState(() =>
    JSON.stringify(SAMPLE_SHOP_V2, null, 2)
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [diffReport, setDiffReport] = useState(null);
  const [filterType, setFilterType] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isClientFallback, setIsClientFallback] = useState(false);

  // Automatically perform initial diff on mount with sample specs
  useEffect(() => {
    handleRunDiff();
  }, []);

  async function handleRunDiff(customBaseline, customTarget) {
    setLoading(true);
    setError(null);
    setIsClientFallback(false);

    const bText = customBaseline ?? baselineText;
    const tText = customTarget ?? targetText;

    let bParsed, tParsed;
    try {
      bParsed = JSON.parse(bText);
    } catch {
      setError("Baseline Spec (S1) contains invalid JSON syntax.");
      setLoading(false);
      return;
    }

    try {
      tParsed = JSON.parse(tText);
    } catch {
      setError("Target Spec (S2) contains invalid JSON syntax.");
      setLoading(false);
      return;
    }

    try {
      const apiRes = await compareOpenApiSpecs(bParsed, tParsed);
      if (apiRes.ok && apiRes.report) {
        setDiffReport(apiRes.report);
      } else {
        // Fallback to client-side diff engine
        const fallback = compareSpecsClientSide(bParsed, tParsed);
        setDiffReport(fallback);
        setIsClientFallback(true);
      }
    } catch {
      const fallback = compareSpecsClientSide(bParsed, tParsed);
      setDiffReport(fallback);
      setIsClientFallback(true);
    } finally {
      setLoading(false);
    }
  }

  function handleLoadPreset() {
    const s1 = JSON.stringify(SAMPLE_SHOP_V1, null, 2);
    const s2 = JSON.stringify(SAMPLE_SHOP_V2, null, 2);
    setBaselineText(s1);
    setTargetText(s2);
    handleRunDiff(s1, s2);
  }

  function handleUseCurrentAsBaseline() {
    if (!currentSpec) return;
    const s1 = typeof currentSpec === "string" ? currentSpec : JSON.stringify(currentSpec, null, 2);
    setBaselineText(s1);
    handleRunDiff(s1, targetText);
  }

  const allChanges = diffReport?.changes || [];
  const stats = useMemo(() => computeDiffStats(allChanges), [allChanges]);
  const filteredChanges = useMemo(
    () => filterChanges(allChanges, { filterType, search: searchQuery }),
    [allChanges, filterType, searchQuery]
  );

  return (
    <div className="specification-diff-page pb-5">
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <span className="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle">
              Milestone: Day 8
            </span>
            <span className="badge bg-secondary-subtle text-secondary small">
              F14 &amp; F15
            </span>
          </div>
          <h2 className="h3 fw-bold mb-1 mt-1">Screen 4: Specification Diff Viewer</h2>
          <p className="text-muted small mb-0">
            Compare two OpenAPI 3.0 specification documents and detect breaking changes for API consumers.
          </p>
        </div>

        <div className="d-flex align-items-center gap-2">
          {onNavigate && (
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={() => onNavigate("editor")}
            >
              ← Back to Spec Editor (Screen 3)
            </button>
          )}
          <button
            type="button"
            className="btn btn-sm btn-outline-primary"
            onClick={handleLoadPreset}
            title="Load demo shop specs with deliberate breaking changes"
          >
            Load Shop API Preset (v1 vs v2)
          </button>
        </div>
      </div>

      {/* Offline Fallback Banner */}
      {isClientFallback && (
        <div className="alert alert-info py-2 px-3 small d-flex align-items-center justify-content-between mb-3">
          <span>
            ℹ️ <strong>Client Fallback Engine Active:</strong> Computed diff using in-browser AST comparator.
          </span>
          <span className="badge bg-info text-dark">Offline Mode</span>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="alert alert-danger py-2 px-3 small d-flex align-items-center justify-content-between mb-3">
          <span>⚠️ {error}</span>
          <button
            type="button"
            className="btn-close btn-close-white"
            onClick={() => setError(null)}
          />
        </div>
      )}

      {/* Accordion / Drawer for Spec Inputs */}
      <details className="card shadow-sm border-0 mb-4 bg-light">
        <summary className="card-header py-2 px-3 bg-white border-0 fw-semibold user-select-none cursor-pointer d-flex justify-content-between align-items-center">
          <span>⚙️ Specification Inputs (Baseline $S_1$ vs Target $S_2$)</span>
          <span className="text-muted small">Click to Expand / Edit Specs</span>
        </summary>
        <div className="card-body p-3">
          <div className="row g-3">
            {/* Baseline Spec S1 */}
            <div className="col-12 col-lg-6">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <label className="form-label fw-bold small text-muted mb-0">
                  Baseline Spec ($S_1$) — Older Version
                </label>
                {currentSpec && (
                  <button
                    type="button"
                    className="btn btn-link btn-sm p-0 text-decoration-none small"
                    onClick={handleUseCurrentAsBaseline}
                  >
                    Use Parsed Spec
                  </button>
                )}
              </div>
              <textarea
                className="form-control font-monospace small bg-white"
                rows={8}
                value={baselineText}
                onChange={(e) => setBaselineText(e.target.value)}
                placeholder="Paste baseline OpenAPI 3.0 JSON here..."
              />
            </div>

            {/* Target Spec S2 */}
            <div className="col-12 col-lg-6">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <label className="form-label fw-bold small text-muted mb-0">
                  Target Spec ($S_2$) — Newer / Candidate Version
                </label>
                <span className="badge bg-secondary-subtle text-secondary small">JSON</span>
              </div>
              <textarea
                className="form-control font-monospace small bg-white"
                rows={8}
                value={targetText}
                onChange={(e) => setTargetText(e.target.value)}
                placeholder="Paste target OpenAPI 3.0 JSON here..."
              />
            </div>
          </div>

          <div className="mt-3 text-end">
            <button
              type="button"
              className="btn btn-primary btn-sm px-4"
              onClick={() => handleRunDiff()}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-1" role="status" />
                  Comparing...
                </>
              ) : (
                "⚡ Re-Run Specification Diff"
              )}
            </button>
          </div>
        </div>
      </details>

      {/* Summary KPI Cards */}
      <div className="row g-3 mb-4">
        {/* Total Changes */}
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 h-100">
            <div className="card-body p-3">
              <div className="text-muted small fw-semibold text-uppercase">Total Changes</div>
              <div className="display-6 fw-bold text-dark mt-1">{stats.total}</div>
              <div className="text-muted small mt-1">across endpoints &amp; params</div>
            </div>
          </div>
        </div>

        {/* Breaking Changes */}
        <div className="col-6 col-md-3">
          <div
            className={`card shadow-sm h-100 ${
              stats.breaking > 0 ? "border-danger bg-danger-subtle" : "border-0"
            }`}
          >
            <div className="card-body p-3">
              <div
                className={`small fw-bold text-uppercase ${
                  stats.breaking > 0 ? "text-danger" : "text-muted"
                }`}
              >
                🚨 Breaking Changes
              </div>
              <div
                className={`display-6 fw-bold mt-1 ${
                  stats.breaking > 0 ? "text-danger" : "text-muted"
                }`}
              >
                {stats.breaking}
              </div>
              <div className="small mt-1 text-danger-emphasis">
                {stats.breaking > 0 ? "Action required: breaks clients" : "Zero breaking changes"}
              </div>
            </div>
          </div>
        </div>

        {/* Non-Breaking Changes */}
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 h-100">
            <div className="card-body p-3">
              <div className="text-muted small fw-semibold text-uppercase">🟢 Non-Breaking</div>
              <div className="display-6 fw-bold text-success mt-1">{stats.nonBreaking}</div>
              <div className="text-muted small mt-1">backwards compatible</div>
            </div>
          </div>
        </div>

        {/* Change Breakdown */}
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 h-100">
            <div className="card-body p-3">
              <div className="text-muted small fw-semibold text-uppercase">Operation Drift</div>
              <div className="d-flex align-items-center gap-2 mt-2">
                <span className="badge bg-success text-white small" title="Added operations">
                  +{stats.added} Added
                </span>
                <span className="badge bg-danger text-white small" title="Removed operations">
                  -{stats.removed} Removed
                </span>
                <span className="badge bg-warning text-dark small" title="Modified operations">
                  ~{stats.modified} Mod
                </span>
              </div>
              <div className="text-muted small mt-2">v{diffReport?.baseline_version || "1.0"} → v{diffReport?.target_version || "2.0"}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card shadow-sm border-0 mb-3">
        <div className="card-body p-2 d-flex flex-wrap align-items-center justify-content-between gap-2">
          {/* Filter Pills */}
          <div className="nav nav-pills gap-1">
            <button
              type="button"
              className={`btn btn-sm ${
                filterType === "all" ? "btn-dark" : "btn-outline-secondary"
              }`}
              onClick={() => setFilterType("all")}
            >
              All Changes ({stats.total})
            </button>
            <button
              type="button"
              className={`btn btn-sm ${
                filterType === "breaking" ? "btn-danger text-white" : "btn-outline-danger"
              }`}
              onClick={() => setFilterType("breaking")}
            >
              🚨 Breaking ({stats.breaking})
            </button>
            <button
              type="button"
              className={`btn btn-sm ${
                filterType === "non_breaking" ? "btn-success text-white" : "btn-outline-success"
              }`}
              onClick={() => setFilterType("non_breaking")}
            >
              ✓ Non-Breaking ({stats.nonBreaking})
            </button>
            <button
              type="button"
              className={`btn btn-sm ${
                filterType === "added" ? "btn-primary text-white" : "btn-outline-primary"
              }`}
              onClick={() => setFilterType("added")}
            >
              + Added ({stats.added})
            </button>
            <button
              type="button"
              className={`btn btn-sm ${
                filterType === "removed" ? "btn-danger text-white" : "btn-outline-danger"
              }`}
              onClick={() => setFilterType("removed")}
            >
              - Removed ({stats.removed})
            </button>
            <button
              type="button"
              className={`btn btn-sm ${
                filterType === "modified" ? "btn-warning text-dark" : "btn-outline-warning"
              }`}
              onClick={() => setFilterType("modified")}
            >
              ~ Modified ({stats.modified})
            </button>
          </div>

          {/* Search Box */}
          <div className="input-group input-group-sm" style={{ maxWidth: "260px" }}>
            <span className="input-group-text bg-white border-end-0">🔍</span>
            <input
              type="search"
              className="form-control border-start-0"
              placeholder="Search path, param, method..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Filter diff changes"
            />
            {searchQuery && (
              <button
                type="button"
                className="btn btn-outline-secondary border-start-0"
                onClick={() => setSearchQuery("")}
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Diff Table */}
      <SpecDiffViewer changes={filteredChanges} />
    </div>
  );
}

