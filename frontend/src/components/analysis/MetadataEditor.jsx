import React, { useState } from "react";
import { getMethodBadgeClass } from "../../utils/routeHelpers.js";

/**
 * In-Place Metadata Editor Modal/Drawer for endpoints.
 * Allows updating operation_id, summary, description, and tags
 * while strictly preserving AST code facts.
 */
export default function MetadataEditor({ endpoint, onSave, onClose }) {
  if (!endpoint) return null;

  const [operationId, setOperationId] = useState(endpoint.operation_id || "");
  const [summary, setSummary] = useState(endpoint.summary || "");
  const [description, setDescription] = useState(endpoint.description || "");
  const [tagsStr, setTagsStr] = useState((endpoint.tags || []).join(", "));
  const [error, setError] = useState(null);

  const methodBadgeClass = getMethodBadgeClass(endpoint.method);

  function handleSubmit(e) {
    e.preventDefault();
    if (!operationId.trim()) {
      setError("Operation ID cannot be blank.");
      return;
    }

    const parsedTags = tagsStr
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    onSave({
      ...endpoint,
      operation_id: operationId.trim(),
      summary: summary.trim(),
      description: description.trim(),
      tags: parsedTags,
    });
  }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div
        className="drawer-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="editor-title"
      >
        <div className="p-3 border-bottom d-flex justify-content-between align-items-center bg-light">
          <div className="d-flex align-items-center gap-2">
            <span className={`badge ${methodBadgeClass} px-2 py-1`}>
              {(endpoint.method || "").toUpperCase()}
            </span>
            <h6 id="editor-title" className="mb-0 fw-bold">
              Edit Metadata: <code>{endpoint.path}</code>
            </h6>
          </div>
          <button
            type="button"
            className="btn-close"
            aria-label="Close"
            onClick={onClose}
          />
        </div>

        <form onSubmit={handleSubmit} className="p-4 flex-grow-1 overflow-auto d-flex flex-column">
          {/* Security & Integrity Notice */}
          <div className="alert alert-info py-2 px-3 small mb-3">
            <strong>🔒 AST Fact Protection:</strong> Route path, HTTP method, and parameter types are
            extracted directly from source code and locked. You can safely refine documentation metadata below.
          </div>

          {error && <div className="alert alert-danger py-2 small mb-3">{error}</div>}

          {/* Locked AST Fields (Read Only) */}
          <div className="row g-2 mb-3 bg-light p-2 rounded small text-muted">
            <div className="col-sm-6">
              <span>Path:</span> <code>{endpoint.path}</code>
            </div>
            <div className="col-sm-6">
              <span>Method:</span> <code>{(endpoint.method || "").toUpperCase()}</code>
            </div>
            <div className="col-sm-6">
              <span>Parameters:</span> {(endpoint.parameters || []).length} declared
            </div>
            <div className="col-sm-6">
              <span>Source File:</span> <code>{endpoint.source_file || "inline"}</code>
            </div>
          </div>

          {/* Field: Operation ID */}
          <div className="mb-3">
            <label className="form-label small fw-bold">
              Operation ID <span className="text-danger">*</span>
            </label>
            <input
              type="text"
              className="form-control form-control-sm font-monospace"
              value={operationId}
              onChange={(e) => {
                setOperationId(e.target.value);
                setError(null);
              }}
              placeholder="e.g. get_user_by_id"
              required
            />
            <div className="form-text small">
              Unique identifier used in generated SDK client methods.
            </div>
          </div>

          {/* Field: Summary */}
          <div className="mb-3">
            <label className="form-label small fw-bold">Summary</label>
            <input
              type="text"
              className="form-control form-control-sm"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="e.g. Fetch user by primary key"
            />
            <div className="form-text small">
              Short one-line synopsis shown in Swagger UI overview.
            </div>
          </div>

          {/* Field: Description */}
          <div className="mb-3">
            <label className="form-label small fw-bold">Description / Markdown</label>
            <textarea
              className="form-control form-control-sm"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed explanation, acceptance criteria, or authentication requirements..."
            />
          </div>

          {/* Field: Tags */}
          <div className="mb-4">
            <label className="form-label small fw-bold">Tags (comma-separated)</label>
            <input
              type="text"
              className="form-control form-control-sm"
              value={tagsStr}
              onChange={(e) => setTagsStr(e.target.value)}
              placeholder="e.g. items, inventory, public"
            />
            <div className="form-text small">
              Groups endpoints logically into Swagger UI sections.
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-auto pt-3 border-top d-flex justify-content-end gap-2">
            <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary btn-sm">
              Save Metadata
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

