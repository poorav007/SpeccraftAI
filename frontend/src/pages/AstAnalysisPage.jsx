import React, { useState } from "react";
import MetadataEditor from "../components/analysis/MetadataEditor.jsx";
import ParameterInspector from "../components/analysis/ParameterInspector.jsx";
import RouteTable from "../components/analysis/RouteTable.jsx";

/**
 * Screen 2: AST Analysis & Route Review Page.
 */
export default function AstAnalysisPage({
  endpoints = [],
  schemas = {},
  metrics = null,
  diagnostics = [],
  onUpdateEndpoint,
  onNavigate,
}) {
  const [inspectingEndpoint, setInspectingEndpoint] = useState(null);
  const [lastInspectingEndpoint, setLastInspectingEndpoint] = useState(null);
  const [editingEndpoint, setEditingEndpoint] = useState(null);
  const [lastEditingEndpoint, setLastEditingEndpoint] = useState(null);
  const [saveToast, setSaveToast] = useState(null);

  function openInspector(ep) {
    setLastInspectingEndpoint(ep);
    setInspectingEndpoint(ep);
  }

  function openEditor(ep) {
    setLastEditingEndpoint(ep);
    setEditingEndpoint(ep);
  }

  function handleSaveMetadata(updatedEndpoint) {
    onUpdateEndpoint?.(updatedEndpoint);
    setEditingEndpoint(null);
    setSaveToast(`Updated metadata for ${updatedEndpoint.path}`);
    setTimeout(() => setSaveToast(null), 3500);
  }

  const totalWarnings = diagnostics.length || 0;
  const schemasCount = Object.keys(schemas || {}).length;

  return (
    <div className="py-2">
      {/* Page Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
        <div>
          <h2 className="h4 mb-1 fw-bold">Screen 2: AST Analysis & Route Review</h2>
          <p className="text-muted small mb-0">
            Inspect extracted endpoints, review parameter typings, and customize documentation metadata.
          </p>
        </div>
        <div className="d-flex align-items-center gap-2">
          {onNavigate && (
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={() => onNavigate("import")}
            >
              ← Back to Importer
            </button>
          )}
          {endpoints.length > 0 && onNavigate && (
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={() => onNavigate("editor")}
            >
              Proceed to Spec Editor (Screen 3) →
            </button>
          )}
        </div>
      </div>

      {/* Save Notification Toast / Banner */}
      {saveToast && (
        <div className="alert alert-success alert-dismissible fade show py-2 px-3 small mb-3" role="alert">
          ✓ {saveToast}
          <button
            type="button"
            className="btn-close py-2"
            aria-label="Close"
            onClick={() => setSaveToast(null)}
          />
        </div>
      )}

      {/* Metrics Row */}
      {endpoints.length > 0 && (
        <div className="row g-3 mb-4">
          <div className="col-6 col-md-3">
            <div className="card shadow-sm border-0 bg-primary-subtle text-primary-emphasis">
              <div className="card-body py-3">
                <span className="small text-uppercase fw-semibold d-block">Routes Extracted</span>
                <span className="h3 fw-bold mb-0">{endpoints.length}</span>
              </div>
            </div>
          </div>
          <div className="col-6 col-md-3">
            <div className="card shadow-sm border-0 bg-success-subtle text-success-emphasis">
              <div className="card-body py-3">
                <span className="small text-uppercase fw-semibold d-block">Pydantic Schemas</span>
                <span className="h3 fw-bold mb-0">{schemasCount}</span>
              </div>
            </div>
          </div>
          <div className="col-6 col-md-3">
            <div className="card shadow-sm border-0 bg-info-subtle text-info-emphasis">
              <div className="card-body py-3">
                <span className="small text-uppercase fw-semibold d-block">Scanned Code</span>
                <span className="h3 fw-bold mb-0">
                  {metrics?.totalLoc ? `${metrics.totalLoc} LOC` : "—"}
                </span>
              </div>
            </div>
          </div>
          <div className="col-6 col-md-3">
            <div
              className={`card shadow-sm border-0 ${
                totalWarnings > 0
                  ? "bg-warning-subtle text-warning-emphasis"
                  : "bg-light text-muted"
              }`}
            >
              <div className="card-body py-3">
                <span className="small text-uppercase fw-semibold d-block">Diagnostics</span>
                <span className="h3 fw-bold mb-0">{totalWarnings}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Route Table */}
      <RouteTable
        endpoints={endpoints}
        onInspectEndpoint={openInspector}
        onEditEndpoint={openEditor}
        onNavigateToImport={() => onNavigate?.("import")}
      />

      {/* Parameter & Schema Inspector Drawer (mounted with inert when closed for exit transition) */}
      <ParameterInspector
        endpoint={inspectingEndpoint || lastInspectingEndpoint}
        isOpen={Boolean(inspectingEndpoint)}
        schemas={schemas}
        onClose={() => setInspectingEndpoint(null)}
        onEdit={(ep) => {
          setInspectingEndpoint(null);
          openEditor(ep);
        }}
      />

      {/* Metadata Editor Drawer (mounted with inert when closed for exit transition) */}
      <MetadataEditor
        endpoint={editingEndpoint || lastEditingEndpoint}
        isOpen={Boolean(editingEndpoint)}
        onSave={handleSaveMetadata}
        onClose={() => setEditingEndpoint(null)}
      />
    </div>
  );
}

