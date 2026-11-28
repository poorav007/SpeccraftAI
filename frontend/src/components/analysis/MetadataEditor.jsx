import React, { useEffect, useRef, useState } from "react";
import { enrichEndpointDocs } from "../../services/apiClient.js";
import {
  buildOfflineEndpointSuggestion,
  getEndpointKey,
  getProviderBadge,
  isResponseForActiveEndpoint,
} from "../../utils/aiHelpers.js";
import { getMethodBadgeClass } from "../../utils/routeHelpers.js";

/**
 * In-Place Metadata Editor Drawer for endpoints.
 * Keeps mounted with `inert` when closed for symmetric transitions and
 * guards AI suggestions with AbortController + active endpoint key check.
 */
export default function MetadataEditor({
  endpoint,
  isOpen = Boolean(endpoint),
  onSave,
  onClose,
}) {
  const [operationId, setOperationId] = useState(endpoint?.operation_id || "");
  const [summary, setSummary] = useState(endpoint?.summary || "");
  const [description, setDescription] = useState(endpoint?.description || "");
  const [tagsStr, setTagsStr] = useState((endpoint?.tags || []).join(", "));
  const [error, setError] = useState(null);

  const [aiLoading, setAiLoading] = useState(false);
  const [aiProposal, setAiProposal] = useState(null);

  const activeEndpointRef = useRef(endpoint);
  const abortRef = useRef(null);

  useEffect(() => {
    activeEndpointRef.current = endpoint;
    abortRef.current?.abort();
    abortRef.current = null;
    setAiLoading(false);
    setAiProposal(null);
    setError(null);

    if (endpoint) {
      setOperationId(endpoint.operation_id || "");
      setSummary(endpoint.summary || "");
      setDescription(endpoint.description || "");
      setTagsStr((endpoint.tags || []).join(", "));
    }
  }, [endpoint, isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;
    function handleKeyDown(e) {
      if (e.key === "Escape") onClose?.();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => () => abortRef.current?.abort(), []);

  if (!endpoint) return null;

  const methodBadgeClass = getMethodBadgeClass(endpoint.method);

  async function handleAiSuggest() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestKey = getEndpointKey(endpoint);

    setAiLoading(true);
    const res = await enrichEndpointDocs(endpoint, { signal: controller.signal });

    if (controller.signal.aborted || !isResponseForActiveEndpoint(requestKey, activeEndpointRef.current)) {
      return;
    }

    setAiLoading(false);
    if (res.ok && res.proposal) {
      setAiProposal(res.proposal);
    } else if (!res.aborted) {
      setAiProposal(buildOfflineEndpointSuggestion(endpoint));
    }
  }

  function handleAcceptProposal(includeTags = true) {
    if (!aiProposal) return;
    if (aiProposal.summary) setSummary(aiProposal.summary);
    if (aiProposal.description) setDescription(aiProposal.description);
    if (includeTags && Array.isArray(aiProposal.suggested_tags) && aiProposal.suggested_tags.length > 0) {
      setTagsStr(aiProposal.suggested_tags.join(", "));
    }
    setAiProposal(null);
  }

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

  const providerBadge = aiProposal ? getProviderBadge(aiProposal.provider) : null;

  return (
    <div
      className="drawer-backdrop"
      data-open={isOpen ? "true" : "false"}
      inert={!isOpen ? "" : undefined}
      onClick={onClose}
    >
      <div
        className="drawer-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-hidden={!isOpen}
        aria-labelledby="editor-title"
      >
        <div className="p-3 border-bottom d-flex justify-content-between align-items-center drawer-header-frosted">
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

          {/* AI Documentation Assistant Trigger */}
          <div className="d-flex justify-content-between align-items-center mb-3">
            <span className="small text-muted">Need cleaner OpenAPI docs?</span>
            <button
              type="button"
              className="btn btn-sm btn-outline-primary"
              onClick={handleAiSuggest}
              disabled={aiLoading}
            >
              {aiLoading ? "Drafting..." : "✨ AI Suggest Docs"}
            </button>
          </div>

          {/* Human-in-the-Loop AI Proposal Review Card */}
          {aiProposal && (
            <div className="card border-primary mb-3 ai-proposal-card">
              <div className="card-header bg-primary-subtle py-2 px-3 d-flex justify-content-between align-items-center">
                <span className="small fw-bold text-primary-emphasis">
                  ✨ Proposed AI Documentation
                </span>
                <span className={`badge ${providerBadge.badgeClass}`}>
                  {providerBadge.label}
                </span>
              </div>
              <div className="card-body p-3 small">
                <div className="mb-2">
                  <span className="text-muted fw-semibold">Summary:</span>{" "}
                  <span>{aiProposal.summary}</span>
                </div>
                <div className="mb-2">
                  <span className="text-muted fw-semibold">Description:</span>{" "}
                  <span>{aiProposal.description}</span>
                </div>
                {aiProposal.suggested_tags?.length > 0 && (
                  <div className="mb-3">
                    <span className="text-muted fw-semibold">Suggested Tags:</span>{" "}
                    {aiProposal.suggested_tags.map((t) => (
                      <span key={t} className="badge bg-secondary-subtle text-secondary me-1">
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <div className="d-flex gap-2 flex-wrap">
                  <button
                    type="button"
                    className="btn btn-success btn-sm"
                    onClick={() => handleAcceptProposal(true)}
                  >
                    ✓ Accept All
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline-primary btn-sm"
                    onClick={() => handleAcceptProposal(false)}
                  >
                    ✏️ Apply &amp; Edit Docs Only
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setAiProposal(null)}
                  >
                    ✕ Reject
                  </button>
                </div>
              </div>
            </div>
          )}

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
