import React from "react";

/**
 * ValidationPanel component displaying real-time OpenAPI 3.0 validation report.
 * Shows structural errors, missing path parameters, and broken $ref pointers.
 */
export default function ValidationPanel({
  report = null,
  isValidating = false,
  onRevalidate,
}) {
  if (isValidating) {
    return (
      <div className="alert alert-info py-2 px-3 small d-flex align-items-center gap-2 mb-3">
        <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
        <span>Validating OpenAPI specification against schema rules...</span>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="alert alert-secondary py-2 px-3 small d-flex justify-content-between align-items-center mb-3">
        <span>Specification validation has not run yet.</span>
        {onRevalidate && (
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary py-0"
            onClick={onRevalidate}
          >
            Run Validator
          </button>
        )}
      </div>
    );
  }

  const { is_valid = false, errors = [], warnings = [], stats = {} } = report;

  return (
    <div className="mb-3">
      {/* Status Banner */}
      <div
        className={`alert ${
          is_valid ? "alert-success" : "alert-danger"
        } py-2 px-3 d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2`}
        role="alert"
      >
        <div className="d-flex align-items-center gap-2">
          <span className="fs-5">{is_valid ? "✓" : "⚠️"}</span>
          <div>
            <strong className="d-block small">
              {is_valid
                ? "OpenAPI 3.0.3 Validated — 0 Errors Detected"
                : `Schema Validation Failed (${errors.length} error${errors.length === 1 ? "" : "s"})`}
            </strong>
            <span className="text-muted" style={{ fontSize: "11px" }}>
              {is_valid
                ? `Specification complies with OpenAPI 3.0.3 standard and internal $ref references resolve correctly.`
                : `Review the errors below to correct invalid constructs or missing parameters.`}
            </span>
          </div>
        </div>

        {/* Stats Pills */}
        <div className="d-flex align-items-center gap-2 small">
          {stats.operations_count !== undefined && (
            <span className="badge bg-light text-dark border">
              {stats.operations_count} operation{stats.operations_count === 1 ? "" : "s"}
            </span>
          )}
          {stats.schemas_count !== undefined && (
            <span className="badge bg-light text-dark border">
              {stats.schemas_count} schema{stats.schemas_count === 1 ? "" : "s"}
            </span>
          )}
          {onRevalidate && (
            <button
              type="button"
              className="btn btn-sm btn-light border py-0 px-2 small text-secondary"
              onClick={onRevalidate}
              title="Re-run validation"
            >
              🔄 Revalidate
            </button>
          )}
        </div>
      </div>

      {/* Error Details Table */}
      {!is_valid && errors.length > 0 && (
        <div className="border rounded bg-white p-2 small mb-2 shadow-sm">
          <div className="table-responsive">
            <table className="table table-sm table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th style={{ width: "160px" }}>Error Code</th>
                  <th>Message</th>
                  <th>Location / Path</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((err, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className="badge bg-danger-subtle text-danger border border-danger-subtle font-monospace">
                        {err.code || "ERR_VALIDATION"}
                      </span>
                    </td>
                    <td>{err.message}</td>
                    <td>
                      <code className="text-secondary small">{err.path || "root"}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Warning Details */}
      {warnings.length > 0 && (
        <div className="alert alert-warning py-2 px-3 small mb-2">
          <div className="fw-bold mb-1">Validation Warnings ({warnings.length}):</div>
          <ul className="mb-0 ps-3">
            {warnings.map((w, idx) => (
              <li key={idx}>
                <code>{w.code}</code>: {w.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

