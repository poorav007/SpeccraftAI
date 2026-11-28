import React, { useEffect, useRef, useState } from "react";
import { summarizeSpecDiff } from "../../services/apiClient.js";
import { buildOfflineDiffSummary, getProviderBadge } from "../../utils/aiHelpers.js";
import {
  getBreakingBadge,
  getChangeBadge,
  getMethodBadgeClass,
} from "../../utils/diffHelpers.js";

/**
 * SpecDiffViewer component renders an accessible, responsive diff comparison table
 * plus an optional AI Migration Summary banner backed by mobile-ready diff cards.
 */
export default function SpecDiffViewer({ changes = [] }) {
  const [expandedRows, setExpandedRows] = useState({});
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSummary, setAiSummary] = useState(null);
  const [showCardsPreview, setShowCardsPreview] = useState(false);
  const abortRef = useRef(null);

  useEffect(() => {
    abortRef.current?.abort();
    setAiLoading(false);
    setAiSummary(null);
    setShowCardsPreview(false);
  }, [changes]);

  useEffect(() => () => abortRef.current?.abort(), []);

  async function handleSummarizeDiff() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const payload = {
      summary: {
        total_changes: changes.length,
        breaking_changes: changes.filter((c) => c.is_breaking).length,
      },
      changes,
    };

    setAiLoading(true);
    const res = await summarizeSpecDiff(payload, { signal: controller.signal });
    if (controller.signal.aborted) return;

    setAiLoading(false);
    if (res.ok && res.report) {
      setAiSummary(res.report);
    } else if (!res.aborted) {
      setAiSummary(buildOfflineDiffSummary(payload));
    }
  }

  function toggleRow(idx) {
    setExpandedRows((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  }

  if (!changes || changes.length === 0) {
    return (
      <div className="card border-0 shadow-sm text-center py-5 bg-light my-3">
        <div className="card-body">
          <span className="display-6">🔍</span>
          <h4 className="h5 fw-bold mt-2">No Specification Changes Found</h4>
          <p className="text-muted small mb-0">
            No changes match the selected filter criteria, or the two specifications are identical.
          </p>
        </div>
      </div>
    );
  }

  const providerBadge = aiSummary ? getProviderBadge(aiSummary.provider) : null;

  return (
    <div>
      {/* AI Changelog & Mobile Cards Summary Bar */}
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
        <span className="small text-muted">
          Showing {changes.length} structural change(s)
        </span>
        <button
          type="button"
          className="btn btn-sm btn-outline-primary"
          onClick={handleSummarizeDiff}
          disabled={aiLoading}
        >
          {aiLoading ? "Summarizing..." : "✨ AI Summarize Changes"}
        </button>
      </div>

      {aiSummary && (
        <div className="card border-primary mb-3 ai-proposal-card">
          <div className="card-header bg-primary-subtle py-2 px-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div className="d-flex align-items-center gap-2">
              <span className="small fw-bold text-primary-emphasis">
                ✨ AI Migration &amp; Release Summary
              </span>
              <span
                className={`badge ${
                  aiSummary.risk_level === "high"
                    ? "bg-danger"
                    : aiSummary.risk_level === "medium"
                    ? "bg-warning text-dark"
                    : "bg-success"
                }`}
              >
                Risk: {String(aiSummary.risk_level || "low").toUpperCase()}
              </span>
              {aiSummary.truncated && (
                <span className="badge bg-secondary-subtle text-secondary">
                  Capped (Top 50)
                </span>
              )}
            </div>
            <div className="d-flex align-items-center gap-2">
              <span className={`badge ${providerBadge.badgeClass}`}>
                {providerBadge.label}
              </span>
              <button
                type="button"
                className="btn-close btn-sm"
                aria-label="Dismiss AI diff summary"
                onClick={() => setAiSummary(null)}
              />
            </div>
          </div>
          <div className="card-body py-2 px-3 small">
            <p className="mb-2 fw-medium">{aiSummary.executive_summary}</p>
            {aiSummary.migration_steps?.length > 0 && (
              <ul className="mb-2 ps-3">
                {aiSummary.migration_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ul>
            )}
            {aiSummary.cards?.length > 0 && (
              <div>
                <button
                  type="button"
                  className="btn btn-link btn-sm p-0 text-decoration-none"
                  onClick={() => setShowCardsPreview((v) => !v)}
                >
                  {showCardsPreview ? "Hide" : "Preview"} Mobile Review Cards ({aiSummary.cards.length})
                </button>
                {showCardsPreview && (
                  <div className="row g-2 mt-1">
                    {aiSummary.cards.slice(0, 6).map((card, i) => (
                      <div key={i} className="col-12 col-md-6">
                        <div className="border rounded p-2 bg-light">
                          <div className="d-flex justify-content-between align-items-center mb-1">
                            <code className="fw-bold">{card.endpoint}</code>
                            <span
                              className={`badge ${
                                card.severity === "breaking" ? "bg-danger" : "bg-success"
                              }`}
                            >
                              {card.severity}
                            </span>
                          </div>
                          <div className="mb-1">{card.one_line_impact}</div>
                          <div className="text-muted font-monospace" style={{ fontSize: "11px" }}>
                            {card.before} → {card.after}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <div
        className="table-responsive rounded border shadow-sm bg-white"
        tabIndex={0}
        role="region"
        aria-labelledby="diff-viewer-heading"
        style={{ maxHeight: "620px", overflow: "auto" }}
      >
      <h2 id="diff-viewer-heading" className="visually-hidden">
        API Specification Differences Table
      </h2>

      <table className="table table-hover align-middle mb-0" style={{ minWidth: "820px" }}>
        <thead
          className="table-light text-muted small user-select-none"
          style={{ position: "sticky", top: 0, zIndex: 2 }}
        >
          <tr>
            <th scope="col" style={{ width: "160px" }}>Classification</th>
            <th scope="col" style={{ width: "120px" }}>Change Type</th>
            <th scope="col" style={{ width: "240px" }}>Endpoint / Operation</th>
            <th scope="col">Description &amp; Path Location</th>
            <th scope="col" className="text-end" style={{ width: "100px" }}>Details</th>
          </tr>
        </thead>
        <tbody className="small">
          {changes.map((change, idx) => {
            const breakingBadge = getBreakingBadge(change.is_breaking);
            const changeBadge = getChangeBadge(change.change_type);
            const methodClass = getMethodBadgeClass(change.method);
            const isExpanded = Boolean(expandedRows[idx]);

            return (
              <React.Fragment key={`${change.location || "loc"}-${change.change_type}-${idx}`}>
                <tr className={change.is_breaking ? "table-danger-subtle" : ""}>
                  {/* Breaking vs Non-Breaking Classification */}
                  <td>
                    <span
                      className={`badge ${breakingBadge.bgClass} px-2 py-1 fw-bold`}
                      aria-label={breakingBadge.ariaLabel}
                      title={breakingBadge.ariaLabel}
                    >
                      {breakingBadge.label}
                    </span>
                  </td>

                  {/* Added / Removed / Modified */}
                  <td>
                    <span className={`badge ${changeBadge.bgClass} px-2 py-1`}>
                      {changeBadge.label}
                    </span>
                  </td>

                  {/* Endpoint & Method */}
                  <td>
                    <div className="d-flex align-items-center gap-2">
                      {change.method && (
                        <span className={`badge ${methodClass} font-monospace py-1 px-2`}>
                          {change.method}
                        </span>
                      )}
                      <span className="font-monospace fw-semibold text-break" title={change.path}>
                        {change.path || "/"}
                      </span>
                    </div>
                  </td>

                  {/* Description & Location */}
                  <td>
                    <div className="fw-semibold text-dark">{change.description}</div>
                    <div className="text-muted font-monospace mt-1" style={{ fontSize: "11px" }}>
                      📍 <code>{change.location}</code>
                    </div>
                  </td>

                  {/* Expand/Collapse JSON button */}
                  <td className="text-end">
                    {(change.old_value !== null || change.new_value !== null) ? (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-secondary py-0 px-2"
                        onClick={() => toggleRow(idx)}
                        aria-expanded={isExpanded}
                        title="Toggle before/after JSON snapshot"
                      >
                        {isExpanded ? "Hide" : "Diff"}
                      </button>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                </tr>

                {/* Expanded Details Row */}
                {isExpanded && (
                  <tr className="bg-light">
                    <td colSpan={5} className="p-3">
                      <div className="row g-2">
                        <div className="col-12 col-md-6">
                          <div className="text-muted fw-bold small mb-1">
                            Baseline ($S_1$) Value:
                          </div>
                          <pre
                            className="p-2 rounded border bg-white mb-0 font-monospace text-danger"
                            style={{ maxHeight: "160px", overflow: "auto", fontSize: "11px" }}
                          >
                            {change.old_value !== null
                              ? JSON.stringify(change.old_value, null, 2)
                              : "<none / not present>"}
                          </pre>
                        </div>
                        <div className="col-12 col-md-6">
                          <div className="text-muted fw-bold small mb-1">
                            Target ($S_2$) Value:
                          </div>
                          <pre
                            className="p-2 rounded border bg-white mb-0 font-monospace text-success"
                            style={{ maxHeight: "160px", overflow: "auto", fontSize: "11px" }}
                          >
                            {change.new_value !== null
                              ? JSON.stringify(change.new_value, null, 2)
                              : "<deleted / not present>"}
                          </pre>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
    </div>
  );
}

