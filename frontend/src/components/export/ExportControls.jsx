import React, { useState } from "react";

/**
 * ExportControls: 4-card download & copy grid for OpenAPI JSON, OpenAPI YAML,
 * Postman Collection v2.1, and Markdown Validation Report, plus ZIP bundle action.
 */
export default function ExportControls({
  onDownloadJson,
  onCopyJson,
  onDownloadYaml,
  onCopyYaml,
  onDownloadPostman,
  onCopyPostman,
  onDownloadReport,
  onCopyReport,
  onDownloadBundle,
  onPrintHandoff,
  onDownloadHandoffHtml,
  onDownloadSdk,
  onDownloadMockServer,
  brandName = "",
  onBrandNameChange,
  isExporting = false,
}) {
  const [copiedId, setCopiedId] = useState(null);

  async function handleCopy(id, copyFn) {
    if (!copyFn) return;
    const ok = await copyFn();
    if (ok !== false) {
      setCopiedId(id);
      setTimeout(() => {
        setCopiedId((prev) => (prev === id ? null : prev));
      }, 2000);
    }
  }

  const cards = [
    {
      id: "json",
      badge: "OpenAPI 3.0.3",
      badgeClass: "bg-primary-subtle text-primary",
      title: "OpenAPI JSON",
      description: "Formatted, deterministic JSON specification ready for codegen & CI.",
      filename: "openapi_spec.json",
      downloadLabel: "Download JSON",
      onDownload: onDownloadJson,
      onCopy: onCopyJson,
    },
    {
      id: "yaml",
      badge: "OpenAPI 3.0.3",
      badgeClass: "bg-info-subtle text-info-emphasis",
      title: "OpenAPI YAML",
      description: "Clean human-readable YAML specification for Git & SwaggerHub.",
      filename: "openapi_spec.yaml",
      downloadLabel: "Download YAML",
      onDownload: onDownloadYaml,
      onCopy: onCopyYaml,
    },
    {
      id: "postman",
      badge: "Postman v2.1",
      badgeClass: "bg-warning-subtle text-warning-emphasis",
      title: "Postman Collection",
      description: "Importable collection with tag folders, :vars, and sample bodies.",
      filename: "spec.postman_collection.json",
      downloadLabel: "Download Postman",
      onDownload: onDownloadPostman,
      onCopy: onCopyPostman,
    },
    {
      id: "report",
      badge: "Audit Log",
      badgeClass: "bg-success-subtle text-success",
      title: "Validation Report",
      description: "Markdown audit summary of paths, schemas, errors, and warnings.",
      filename: "validation_report.md",
      downloadLabel: "Download Report",
      onDownload: onDownloadReport,
      onCopy: onCopyReport,
    },
  ];

  return (
    <section aria-label="Export format controls">
      <div className="row g-3">
        {cards.map((card) => (
          <div key={card.id} className="col-12 col-md-6 col-lg-3">
            <div className="card h-100 border shadow-sm">
              <div className="card-body d-flex flex-column">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span className={`badge ${card.badgeClass}`}>{card.badge}</span>
                  <code className="small text-muted">{card.filename}</code>
                </div>
                <h3 className="h6 fw-bold mb-1">{card.title}</h3>
                <p className="small text-muted mb-3 flex-grow-1">{card.description}</p>

                <div className="d-grid gap-2">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={card.onDownload}
                    disabled={isExporting}
                    aria-label={card.downloadLabel}
                  >
                    ⬇ {card.downloadLabel}
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => handleCopy(card.id, card.onCopy)}
                    disabled={isExporting}
                    aria-label={`Copy ${card.title} to clipboard`}
                  >
                    {copiedId === card.id ? "✓ Copied!" : `Copy ${card.title}`}
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {(onDownloadBundle || onPrintHandoff || onDownloadHandoffHtml) && (
        <div className="card border shadow-sm mt-3 bg-light">
          <div className="card-body py-3 d-flex justify-content-between align-items-center flex-wrap gap-3">
            {(onPrintHandoff || onDownloadHandoffHtml) && (
              <div className="d-flex align-items-center gap-2 flex-wrap">
                <label htmlFor="handoff-brand-input" className="small fw-semibold text-muted mb-0">
                  Client / Brand Name:
                </label>
                <input
                  id="handoff-brand-input"
                  type="text"
                  className="form-control form-control-sm"
                  style={{ width: "190px" }}
                  placeholder="e.g. Acme Corp"
                  value={brandName}
                  onChange={(e) => onBrandNameChange?.(e.target.value)}
                />
                {onPrintHandoff && (
                  <button
                    type="button"
                    className="btn btn-outline-dark btn-sm"
                    onClick={onPrintHandoff}
                    disabled={isExporting}
                    aria-label="Print or Save Client Handoff PDF"
                  >
                    🖨️ Print / Save Client Handoff PDF
                  </button>
                )}
                {onDownloadHandoffHtml && (
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={onDownloadHandoffHtml}
                    disabled={isExporting}
                    aria-label="Download Standalone Handoff HTML"
                  >
                    ⬇ Download Handoff (.html)
                  </button>
                )}
              </div>
            )}

            {onDownloadSdk && (
              <div className="d-flex align-items-center gap-2">
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm"
                  onClick={() => onDownloadSdk("typescript")}
                  disabled={isExporting}
                >
                  ⬇ TypeScript SDK (.ts)
                </button>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm"
                  onClick={() => onDownloadSdk("python")}
                  disabled={isExporting}
                >
                  ⬇ Python SDK (.py)
                </button>
              </div>
            )}

            {onDownloadMockServer && (
              <button
                type="button"
                className="btn btn-outline-success btn-sm"
                onClick={onDownloadMockServer}
                disabled={isExporting}
              >
                🧪 Mock Server (.py)
              </button>
            )}

            {onDownloadBundle && (
              <button
                type="button"
                className="btn btn-dark btn-sm ms-auto"
                onClick={onDownloadBundle}
                disabled={isExporting}
                aria-label="Download Complete Documentation Bundle ZIP"
              >
                {isExporting ? "Preparing Bundle..." : "📦 Download Full API Documentation Bundle (.zip)"}
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

