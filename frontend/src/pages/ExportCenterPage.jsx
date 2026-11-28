import React, { useEffect, useMemo, useState } from "react";
import ExportControls from "../components/export/ExportControls.jsx";
import { SAMPLE_SHOP_V1 } from "../config/sampleSpecs.js";
import {
  exportBundleZip,
  exportPostmanCollection,
  exportSpecYaml,
  validateOpenApiSpec,
} from "../services/apiClient.js";
import {
  convertObjectToYaml,
  convertOpenApiToPostman,
  copyTextToClipboard,
  downloadBlobFile,
  downloadTextFile,
  formatValidationReportMarkdown,
} from "../utils/fileHelpers.js";

/**
 * Screen 5: Export Center
 * Download OpenAPI 3.0 JSON/YAML, Postman v2.1 collections, validation audit
 * reports, and full ZIP bundles with live format preview tabs.
 */
export default function ExportCenterPage({
  spec = null,
  endpoints = [],
  diagnostics = [],
  onLoadSampleSpec,
  onNavigate,
}) {
  const [activeTab, setActiveTab] = useState("json"); // 'json' | 'yaml' | 'postman' | 'report'
  const [yamlText, setYamlText] = useState("");
  const [postmanObj, setPostmanObj] = useState(null);
  const [validationReport, setValidationReport] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [statusNotice, setStatusNotice] = useState(null);

  const specObject = useMemo(() => {
    if (!spec) return null;
    if (typeof spec === "object") return spec;
    try {
      return JSON.parse(spec);
    } catch {
      return null;
    }
  }, [spec]);

  const jsonText = useMemo(() => {
    if (!spec) return "";
    if (specObject) return JSON.stringify(specObject, null, 2);
    return String(spec);
  }, [spec, specObject]);

  // Hydrate YAML, Postman v2.1, and Validation Report whenever active spec changes
  useEffect(() => {
    if (!spec) {
      setYamlText("");
      setPostmanObj(null);
      setValidationReport(null);
      return;
    }

    let cancelled = false;

    async function hydrateExports() {
      // Immediate offline-ready defaults
      if (specObject) {
        setYamlText(convertObjectToYaml(specObject));
        setPostmanObj(convertOpenApiToPostman(specObject));
      } else {
        setYamlText(String(spec));
      }

      // Upgrade with authoritative backend serializers when API is online
      const [yamlRes, postmanRes, valRes] = await Promise.all([
        exportSpecYaml(spec),
        exportPostmanCollection(spec),
        validateOpenApiSpec(spec),
      ]);

      if (cancelled) return;
      if (yamlRes.ok && yamlRes.yaml) setYamlText(yamlRes.yaml);
      if (postmanRes.ok && postmanRes.collection) setPostmanObj(postmanRes.collection);
      if (valRes.ok && valRes.report) setValidationReport(valRes.report);
    }

    hydrateExports();
    return () => {
      cancelled = true;
    };
  }, [spec, specObject]);

  const postmanText = useMemo(() => {
    if (!postmanObj) return "";
    return JSON.stringify(postmanObj, null, 2);
  }, [postmanObj]);

  const reportMarkdown = useMemo(() => {
    if (!specObject) return "";
    return formatValidationReportMarkdown(specObject, validationReport);
  }, [specObject, validationReport]);

  if (!spec) {
    return (
      <div className="card shadow-sm border-0 text-center py-5 my-4" role="region" aria-label="Export Center Empty State">
        <div className="card-body">
          <span className="badge bg-secondary-subtle text-secondary mb-2">Screen 5: Export Center</span>
          <h2 className="h4 fw-bold">No Active OpenAPI Specification</h2>
          <p className="text-muted small mx-auto mb-4" style={{ maxWidth: "520px" }}>
            Import a codebase in Screen 1 or generate a specification in Screen 3 to export OpenAPI JSON/YAML,
            Postman v2.1 collections, and validation audit reports.
          </p>
          <div className="d-flex justify-content-center gap-2 flex-wrap">
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              onClick={() => onNavigate?.("import")}
            >
              ← Go to Screen 1 (Import Codebase)
            </button>
            {onLoadSampleSpec && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onLoadSampleSpec(SAMPLE_SHOP_V1)}
              >
                ⚡ Load Sample E-Commerce Spec
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  const pathCount = Object.keys(specObject?.paths || {}).length;
  const schemaCount = Object.keys(specObject?.components?.schemas || {}).length;
  const errorCount = validationReport?.errors?.length ?? 0;

  async function handleBundleDownload() {
    setIsExporting(true);
    setStatusNotice(null);
    const res = await exportBundleZip(spec, validationReport);
    setIsExporting(false);

    if (res.ok && res.blob) {
      downloadBlobFile(res.blob, "speccraft-export-bundle.zip");
      setStatusNotice({ type: "success", text: "Downloaded speccraft-export-bundle.zip" });
    } else {
      setStatusNotice({
        type: "warning",
        text: `ZIP bundle requires the Python backend (${res.error}). Individual file downloads work offline.`,
      });
    }
  }

  const previewMap = {
    json: jsonText,
    yaml: yamlText,
    postman: postmanText,
    report: reportMarkdown,
  };

  return (
    <div className="my-3" role="region" aria-labelledby="export-center-heading">
      {/* Header & Summary Banner */}
      <div className="card border-0 shadow-sm mb-3">
        <div className="card-body d-flex flex-wrap justify-content-between align-items-center gap-3">
          <div>
            <span className="badge bg-success-subtle text-success mb-1">Screen 5: Export Center</span>
            <h2 id="export-center-heading" className="h4 fw-bold mb-1">
              {specObject?.info?.title || "SpecCraft Generated API"}{" "}
              <span className="badge bg-light text-dark border fw-normal">
                v{specObject?.info?.version || "1.0.0"}
              </span>
            </h2>
            <p className="text-muted small mb-0">
              Download production OpenAPI 3.0 specs, Postman v2.1 collections, and validation reports.
            </p>
          </div>

          <div className="d-flex gap-2 flex-wrap align-items-center">
            <span className="badge bg-primary-subtle text-primary px-3 py-2">
              {pathCount || endpoints.length} Paths
            </span>
            <span className="badge bg-info-subtle text-info-emphasis px-3 py-2">
              {schemaCount} Schemas
            </span>
            <span
              className={`badge px-3 py-2 ${
                errorCount === 0 ? "bg-success-subtle text-success" : "bg-danger-subtle text-danger"
              }`}
            >
              {errorCount === 0 ? "● Valid OpenAPI 3.0" : `${errorCount} Validation Error(s)`}
            </span>
            {diagnostics.length > 0 && (
              <span className="badge bg-warning-subtle text-warning-emphasis px-3 py-2">
                {diagnostics.length} AST Diagnostic(s)
              </span>
            )}
          </div>
        </div>
      </div>

      {statusNotice && (
        <div className={`alert alert-${statusNotice.type} py-2 small`} role="status" aria-live="polite">
          {statusNotice.text}
        </div>
      )}

      {/* 4 Export Cards + Bundle */}
      <div className="mb-4">
        <ExportControls
          isExporting={isExporting}
          onDownloadJson={() => downloadTextFile(jsonText, "openapi_spec.json", "application/json")}
          onCopyJson={() => copyTextToClipboard(jsonText)}
          onDownloadYaml={() => downloadTextFile(yamlText, "openapi_spec.yaml", "text/yaml")}
          onCopyYaml={() => copyTextToClipboard(yamlText)}
          onDownloadPostman={() =>
            downloadTextFile(postmanText, "spec.postman_collection.json", "application/json")
          }
          onCopyPostman={() => copyTextToClipboard(postmanText)}
          onDownloadReport={() =>
            downloadTextFile(reportMarkdown, "validation_report.md", "text/markdown")
          }
          onCopyReport={() => copyTextToClipboard(reportMarkdown)}
          onDownloadBundle={handleBundleDownload}
        />
      </div>

      {/* Live Preview Tabs */}
      <div className="card border shadow-sm">
        <div className="card-header bg-white d-flex justify-content-between align-items-center flex-wrap gap-2">
          <ul className="nav nav-tabs card-header-tabs" role="tablist">
            {[
              { id: "json", label: "OpenAPI JSON" },
              { id: "yaml", label: "OpenAPI YAML" },
              { id: "postman", label: "Postman v2.1 Preview" },
              { id: "report", label: "Validation Report" },
            ].map((tab) => (
              <li className="nav-item" key={tab.id} role="presentation">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  className={`nav-link ${activeTab === tab.id ? "active fw-semibold" : ""}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              </li>
            ))}
          </ul>

          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={() => onNavigate?.("editor")}
          >
            ← Back to Spec Editor (Screen 3)
          </button>
        </div>

        <div className="card-body p-0" role="tabpanel">
          <pre
            className="mb-0 p-3 bg-dark text-light font-monospace"
            style={{ maxHeight: "420px", overflow: "auto", fontSize: "12px" }}
          >
            {previewMap[activeTab] || "No preview available."}
          </pre>
        </div>
      </div>
    </div>
  );
}

