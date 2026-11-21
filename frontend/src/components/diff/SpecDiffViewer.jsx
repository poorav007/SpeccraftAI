import React, { useState } from "react";
import {
  getBreakingBadge,
  getChangeBadge,
  getMethodBadgeClass,
} from "../../utils/diffHelpers.js";

/**
 * SpecDiffViewer component renders an accessible, responsive diff comparison table.
 * Adheres to Modern Web Guidance:
 * - Table wrapped in scrollable container with tabindex="0", role="region", aria-labelledby.
 * - Sticky table header for seamless context during vertical scrolling.
 * - Dual-channel indicators (icons + explicit text labels) ensuring color-blind accessibility.
 *
 * @param {object} props
 * @param {Array<object>} props.changes - List of DiffChangeRecord items to render.
 */
export default function SpecDiffViewer({ changes = [] }) {
  const [expandedRows, setExpandedRows] = useState({});

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

  return (
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
  );
}

