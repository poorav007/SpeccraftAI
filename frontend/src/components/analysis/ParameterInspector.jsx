import React, { useEffect, useRef, useState } from "react";
import { explainSchemaField } from "../../services/apiClient.js";
import {
  buildOfflineFieldExplanation,
  getEndpointKey,
  getProviderBadge,
  isResponseForActiveEndpoint,
} from "../../utils/aiHelpers.js";
import { getMethodBadgeClass } from "../../utils/routeHelpers.js";

/**
 * Slide-out Parameter & Schema Inspector Drawer.
 * Stays mounted with `inert` when closed for symmetric animations and guards
 * AI field explanations with AbortController + active route check.
 */
export default function ParameterInspector({
  endpoint,
  schemas = {},
  isOpen = Boolean(endpoint),
  onClose,
  onEdit,
}) {
  const [explainingKey, setExplainingKey] = useState(null);
  const [fieldExplanation, setFieldExplanation] = useState(null);

  const activeEndpointRef = useRef(endpoint);
  const abortRef = useRef(null);

  useEffect(() => {
    activeEndpointRef.current = endpoint;
    abortRef.current?.abort();
    abortRef.current = null;
    setExplainingKey(null);
    setFieldExplanation(null);
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

  async function handleExplainField(fieldPayload) {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestKey = getEndpointKey(endpoint);

    setExplainingKey(fieldPayload.field_name);
    const res = await explainSchemaField(
      {
        ...fieldPayload,
        endpoint_path: endpoint.path,
        endpoint_method: endpoint.method,
      },
      { signal: controller.signal }
    );

    if (controller.signal.aborted || !isResponseForActiveEndpoint(requestKey, activeEndpointRef.current)) {
      return;
    }

    setExplainingKey(null);
    if (res.ok && res.explanation) {
      setFieldExplanation(res.explanation);
    } else if (!res.aborted) {
      setFieldExplanation(buildOfflineFieldExplanation(fieldPayload));
    }
  }

  const methodUpper = (endpoint.method || "").toUpperCase();
  const methodBadgeClass = getMethodBadgeClass(endpoint.method);

  // Lookup schema definitions if available
  const requestSchemaRef = endpoint.request_body?.schema_ref;
  const requestSchemaObj = requestSchemaRef ? schemas[requestSchemaRef] : null;

  const responses = endpoint.responses || {};
  const responseEntries = Object.entries(responses);

  // Extract warning items
  const warnings = endpoint.warnings || [];

  return (
    <div
      className="drawer-backdrop"
      data-open={isOpen ? "true" : "false"}
      inert={!isOpen ? "" : undefined}
      onClick={onClose}
    >
      <aside
        className="drawer-panel"
        onClick={(e) => e.stopPropagation()}
        aria-labelledby="inspector-title"
        role="dialog"
        aria-modal="true"
        aria-hidden={!isOpen}
      >
        {/* Drawer Header */}
        <div className="p-3 border-bottom d-flex justify-content-between align-items-center drawer-header-frosted">
          <div className="d-flex align-items-center gap-2">
            <span className={`badge ${methodBadgeClass} px-2 py-1`}>
              {methodUpper}
            </span>
            <code id="inspector-title" className="h6 mb-0 text-dark fw-bold">{endpoint.path}</code>
          </div>
          <div className="d-flex align-items-center gap-2">
            <button
              type="button"
              className="btn btn-sm btn-outline-primary"
              onClick={() => onEdit?.(endpoint)}
            >
              ✏️ Edit Metadata
            </button>
            <button
              type="button"
              className="btn-close"
              aria-label="Close"
              onClick={onClose}
            />
          </div>
        </div>

        {/* Drawer Content */}
        <div className="p-4 flex-grow-1 overflow-auto">
          {/* Overview Card */}
          <div className="card mb-3 border-0 bg-light">
            <div className="card-body py-2 px-3 small">
              <div className="row g-2">
                <div className="col-sm-6">
                  <span className="text-muted">Operation ID:</span>{" "}
                  <code>{endpoint.operation_id || "—"}</code>
                </div>
                <div className="col-sm-6">
                  <span className="text-muted">Source:</span>{" "}
                  <code>
                    {endpoint.source_file || "inline"}
                    {endpoint.line_number ? `:${endpoint.line_number}` : ""}
                  </code>
                </div>
                <div className="col-12">
                  <span className="text-muted">Tags:</span>{" "}
                  {(endpoint.tags || []).length > 0 ? (
                    endpoint.tags.map((t) => (
                      <span key={t} className="badge bg-secondary me-1">
                        {t}
                      </span>
                    ))
                  ) : (
                    <span className="text-muted fst-italic">None</span>
                  )}
                </div>
                {endpoint.summary && (
                  <div className="col-12">
                    <span className="text-muted">Summary:</span> {endpoint.summary}
                  </div>
                )}
                {endpoint.description && (
                  <div className="col-12">
                    <span className="text-muted">Description:</span> {endpoint.description}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Section: Warnings / Diagnostics */}
          {warnings.length > 0 && (
            <div className="alert alert-warning mb-4" role="alert">
              <h6 className="alert-heading fw-bold mb-2">
                ⚠️ Parser Diagnostics ({warnings.length})
              </h6>
              <ul className="mb-0 ps-3 small">
                {warnings.map((w, idx) => (
                  <li key={idx} className="mb-1">
                    <strong>{w.code || "SC-W001"}</strong>: {w.message}
                    {w.suggestion && (
                      <div className="text-muted fst-italic">💡 Suggestion: {w.suggestion}</div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Inline AI Field Explanation Card */}
          {fieldExplanation && (() => {
            const badge = getProviderBadge(fieldExplanation.provider);
            return (
              <div className="card border-info mb-4 ai-proposal-card" role="status">
                <div className="card-header bg-info-subtle py-2 px-3 d-flex justify-content-between align-items-center">
                  <span className="small fw-bold text-info-emphasis">
                    ✨ Field Explanation: <code>{fieldExplanation.field_name}</code>
                  </span>
                  <div className="d-flex align-items-center gap-2">
                    <span className={`badge ${badge.badgeClass}`}>{badge.label}</span>
                    <button
                      type="button"
                      className="btn-close btn-sm"
                      aria-label="Dismiss explanation"
                      onClick={() => setFieldExplanation(null)}
                    />
                  </div>
                </div>
                <div className="card-body py-2 px-3 small">
                  <p className="mb-1">{fieldExplanation.explanation}</p>
                  <div className="text-muted">
                    Example: <code>{JSON.stringify(fieldExplanation.example)}</code>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Section: Parameters */}
          <div className="mb-4">
            <h6 className="fw-bold mb-2 text-primary">
              Parameters ({(endpoint.parameters || []).length})
            </h6>
            {(endpoint.parameters || []).length === 0 ? (
              <p className="text-muted small fst-italic mb-0">
                No path, query, or header parameters declared for this route.
              </p>
            ) : (
              <div className="table-responsive">
                <table className="table table-sm table-bordered align-middle mb-0">
                  <thead className="table-light small">
                    <tr>
                      <th>Name</th>
                      <th>In</th>
                      <th>Type</th>
                      <th>Required</th>
                      <th>Default</th>
                      <th className="text-end">AI</th>
                    </tr>
                  </thead>
                  <tbody className="small">
                    {endpoint.parameters.map((p, idx) => (
                      <tr key={idx}>
                        <td>
                          <code>{p.name}</code>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              p.location === "path"
                                ? "bg-info text-dark"
                                : p.location === "query"
                                ? "bg-light text-dark border"
                                : "bg-secondary"
                            }`}
                          >
                            {p.location || "query"}
                          </span>
                        </td>
                        <td>
                          <code>{p.type_annotation || p.type || p.param_type || "string"}</code>
                        </td>
                        <td>
                          {p.required ? (
                            <span className="badge bg-danger">required</span>
                          ) : (
                            <span className="text-muted">optional</span>
                          )}
                        </td>
                        <td>
                          {p.default_value !== null && p.default_value !== undefined ? (
                            <code>{String(p.default_value)}</code>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                        <td className="text-end">
                          <button
                            type="button"
                            className="btn btn-outline-primary btn-sm py-0 px-1"
                            disabled={explainingKey === p.name}
                            onClick={() =>
                              handleExplainField({
                                field_name: p.name,
                                field_type: p.type_annotation || p.type || p.param_type || "string",
                                location: p.location || "query",
                                required: Boolean(p.required),
                                existing_description: p.description || null,
                              })
                            }
                            aria-label={`Explain parameter ${p.name}`}
                          >
                            {explainingKey === p.name ? "..." : "✨"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Section: Request Body */}
          <div className="mb-4">
            <h6 className="fw-bold mb-2 text-primary">Request Body</h6>
            {!endpoint.request_body ? (
              <p className="text-muted small fst-italic mb-0">
                No request body expected (safe method or no payload).
              </p>
            ) : (
              <div className="border rounded p-3 bg-white">
                <div className="d-flex justify-content-between mb-2 small">
                  <span>
                    <strong>Content-Type:</strong>{" "}
                    <code>{endpoint.request_body.content_type || "application/json"}</code>
                  </span>
                  <span>
                    <strong>Model Ref:</strong>{" "}
                    <code className="text-primary">
                      {endpoint.request_body.schema_ref || "inline object"}
                    </code>
                  </span>
                </div>

                {/* Show schema fields if known */}
                {requestSchemaObj && requestSchemaObj.properties && (
                  <div className="table-responsive mt-2">
                    <table className="table table-sm table-striped mb-0 small">
                      <thead>
                        <tr>
                          <th>Property</th>
                          <th>Type</th>
                          <th>Required</th>
                          <th className="text-end">AI</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(requestSchemaObj.properties).map(([field, schema]) => (
                          <tr key={field}>
                            <td>
                              <code>{field}</code>
                            </td>
                            <td>
                              <code>{schema.type || schema.$ref || "any"}</code>
                            </td>
                            <td>
                              {(requestSchemaObj.required || []).includes(field) ? (
                                <span className="badge bg-danger">yes</span>
                              ) : (
                                <span className="text-muted">no</span>
                              )}
                            </td>
                            <td className="text-end">
                              <button
                                type="button"
                                className="btn btn-outline-primary btn-sm py-0 px-1"
                                disabled={explainingKey === field}
                                onClick={() =>
                                  handleExplainField({
                                    field_name: field,
                                    field_type: schema.type || schema.$ref || "string",
                                    location: "body",
                                    required: (requestSchemaObj.required || []).includes(field),
                                    existing_description: schema.description || null,
                                  })
                                }
                                aria-label={`Explain field ${field}`}
                              >
                                {explainingKey === field ? "..." : "✨"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Section: Responses */}
          <div className="mb-4">
            <h6 className="fw-bold mb-2 text-primary">
              Responses ({responseEntries.length})
            </h6>
            {responseEntries.length === 0 ? (
              <div className="border rounded p-2 small text-muted">
                <code>200 OK</code> (Default success response)
              </div>
            ) : (
              <div className="d-flex flex-column gap-2">
                {responseEntries.map(([code, resp]) => (
                  <div key={code} className="border rounded p-3 bg-white">
                    <div className="d-flex justify-content-between align-items-center mb-1">
                      <span
                        className={`badge ${
                          code.startsWith("2")
                            ? "bg-success"
                            : code.startsWith("4")
                            ? "bg-warning text-dark"
                            : "bg-danger"
                        }`}
                      >
                        {code}
                      </span>
                      {resp.schema_ref && (
                        <span className="small">
                          Schema:{" "}
                          <code className="text-primary">{resp.schema_ref}</code>
                        </span>
                      )}
                    </div>
                    <p className="small text-muted mb-0">
                      {resp.description || "Successful Response"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="p-3 border-top bg-light text-end">
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
      </aside>
    </div>
  );
}

