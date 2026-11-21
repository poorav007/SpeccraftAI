import React, { useEffect, useState } from "react";
import SwaggerPreview from "../components/viewer/SwaggerPreview.jsx";
import ValidationPanel from "../components/viewer/ValidationPanel.jsx";
import { generateOpenApiSpec, validateOpenApiSpec } from "../services/apiClient.js";

/**
 * Screen 3: Interactive Swagger UI Preview & Live Specification Editor.
 */
export default function SpecificationEditorPage({
  endpoints = [],
  schemas = {},
  initialSpec = null,
  onSaveSpec,
  onNavigate,
}) {
  const [format, setFormat] = useState("json"); // 'json' or 'yaml'
  const [viewMode, setViewMode] = useState("split"); // 'swagger', 'editor', 'split'
  const [rawText, setRawText] = useState("");
  const [specObject, setSpecObject] = useState(null);
  const [validationReport, setValidationReport] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [toast, setToast] = useState(null);

  // Initialize from initialSpec if present
  useEffect(() => {
    if (initialSpec) {
      if (typeof initialSpec === "object") {
        setSpecObject(initialSpec);
        setRawText(JSON.stringify(initialSpec, null, 2));
      } else if (typeof initialSpec === "string") {
        setRawText(initialSpec);
        try {
          const parsed = JSON.parse(initialSpec);
          setSpecObject(parsed);
        } catch {
          // YAML string
          setSpecObject(null);
        }
      }
    } else if (endpoints.length > 0 && !specObject) {
      // Auto-generate if endpoints exist
      triggerGenerate("json");
    }
  }, [initialSpec, endpoints]);

  async function triggerGenerate(targetFormat = format) {
    setIsGenerating(true);
    setToast(null);

    const payload = {
      extraction_result: {
        endpoints,
        schemas,
        files_scanned: 1,
        total_loc: 100,
        parse_duration_ms: 10,
        diagnostics: [],
        warnings: [],
      },
      title: "SpecCraft Generated API",
      version: "1.0.0",
      description: "Automated OpenAPI 3.0 specification generated from source code AST.",
      format: targetFormat,
    };

    const res = await generateOpenApiSpec(payload);
    setIsGenerating(false);

    if (res.ok) {
      const generated = res.spec;
      if (targetFormat === "json") {
        const text = typeof generated === "string" ? generated : JSON.stringify(generated, null, 2);
        setRawText(text);
        const obj = typeof generated === "object" ? generated : JSON.parse(text);
        setSpecObject(obj);
        onSaveSpec?.(obj, "json");
        triggerValidate(obj);
      } else {
        const text = String(generated);
        setRawText(text);
        onSaveSpec?.(text, "yaml");
        triggerValidate(text);
      }
      showToast("OpenAPI 3.0 specification generated successfully.");
    } else {
      showToast(`Generation notice: ${res.error}`, "warning");
    }
  }

  async function triggerValidate(targetSpec = specObject || rawText) {
    if (!targetSpec) return;
    setIsValidating(true);
    const res = await validateOpenApiSpec(targetSpec);
    setIsValidating(false);
    if (res.ok) {
      setValidationReport(res.report);
    }
  }

  function handleFormatChange(newFormat) {
    if (newFormat === format) return;
    setFormat(newFormat);
    triggerGenerate(newFormat);
  }

  function handleTextChange(e) {
    const nextVal = e.target.value;
    setRawText(nextVal);

    if (format === "json") {
      try {
        const parsed = JSON.parse(nextVal);
        setSpecObject(parsed);
        onSaveSpec?.(parsed, "json");
      } catch {
        // Syntax in progress; don't crash
      }
    } else {
      onSaveSpec?.(nextVal, "yaml");
    }
  }

  function showToast(message, type = "success") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  function handleCopy() {
    if (!rawText) return;
    navigator.clipboard.writeText(rawText);
    showToast("Specification copied to clipboard!");
  }

  function handleDownload() {
    if (!rawText) return;
    const blob = new Blob([rawText], {
      type: format === "json" ? "application/json" : "text/yaml",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `openapi_spec.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Downloaded openapi_spec.${format}`);
  }

  return (
    <div className="py-2">
      {/* Top Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-3">
        <div>
          <h2 className="h4 mb-1 fw-bold">Screen 3: Swagger UI Preview & Spec Editor</h2>
          <p className="text-muted small mb-0">
            Interactive OpenAPI 3.0 documentation preview, real-time schema validation, and live YAML/JSON editing.
          </p>
        </div>

        {/* View Mode & Format Controls */}
        <div className="d-flex flex-wrap align-items-center gap-2">
          {/* Format Toggle */}
          <div className="btn-group btn-group-sm" role="group" aria-label="Format toggle">
            <button
              type="button"
              className={`btn ${format === "json" ? "btn-dark fw-bold" : "btn-outline-secondary"}`}
              onClick={() => handleFormatChange("json")}
            >
              JSON
            </button>
            <button
              type="button"
              className={`btn ${format === "yaml" ? "btn-dark fw-bold" : "btn-outline-secondary"}`}
              onClick={() => handleFormatChange("yaml")}
            >
              YAML
            </button>
          </div>

          {/* View Mode Tabs */}
          <div className="btn-group btn-group-sm" role="group" aria-label="View mode">
            <button
              type="button"
              className={`btn ${viewMode === "split" ? "btn-primary" : "btn-outline-secondary"}`}
              onClick={() => setViewMode("split")}
              title="Split View (Editor + Swagger UI)"
            >
              ⚡ Split View
            </button>
            <button
              type="button"
              className={`btn ${viewMode === "swagger" ? "btn-primary" : "btn-outline-secondary"}`}
              onClick={() => setViewMode("swagger")}
              title="Swagger UI Fullscreen"
            >
              📖 Swagger UI
            </button>
            <button
              type="button"
              className={`btn ${viewMode === "editor" ? "btn-primary" : "btn-outline-secondary"}`}
              onClick={() => setViewMode("editor")}
              title="Raw Code Editor Fullscreen"
            >
              💻 Code Editor
            </button>
          </div>

          {/* Actions */}
          <button
            type="button"
            className="btn btn-sm btn-outline-primary"
            onClick={() => triggerGenerate(format)}
            disabled={isGenerating}
          >
            {isGenerating ? "Generating..." : "🔄 Regenerate Spec"}
          </button>

          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={handleCopy}
            disabled={!rawText}
            title="Copy spec to clipboard"
          >
            📋 Copy
          </button>

          <button
            type="button"
            className="btn btn-sm btn-success"
            onClick={handleDownload}
            disabled={!rawText}
            title="Download OpenAPI specification"
          >
            ⬇️ Download {format.toUpperCase()}
          </button>
        </div>
      </div>

      {/* Toast Notification */}
      {toast && (
        <div
          className={`alert ${
            toast.type === "warning" ? "alert-warning" : "alert-success"
          } alert-dismissible fade show py-2 px-3 small mb-3`}
          role="alert"
        >
          {toast.message}
          <button
            type="button"
            className="btn-close py-2"
            aria-label="Close"
            onClick={() => setToast(null)}
          />
        </div>
      )}

      {/* Validation Panel */}
      <ValidationPanel
        report={validationReport}
        isValidating={isValidating}
        onRevalidate={() => triggerValidate()}
      />

      {/* Main Workspace Display */}
      {viewMode === "swagger" && (
        <SwaggerPreview
          spec={specObject}
          onGenerateSpec={() => triggerGenerate("json")}
          height="800px"
        />
      )}

      {viewMode === "editor" && (
        <div className="card shadow-sm border-0">
          <div className="card-header bg-light d-flex justify-content-between align-items-center py-2 px-3 small">
            <span className="fw-semibold">
              OpenAPI 3.0.3 Source ({format.toUpperCase()})
            </span>
            <span className="text-muted">
              {rawText ? `${rawText.split("\n").length} lines` : "Empty"}
            </span>
          </div>
          <div className="card-body p-0">
            <textarea
              className="form-control font-monospace border-0 rounded-0"
              style={{
                minHeight: "650px",
                fontSize: "13px",
                backgroundColor: "#1e1e1e",
                color: "#d4d4d4",
                lineHeight: "1.5",
                resize: "vertical",
              }}
              value={rawText}
              onChange={handleTextChange}
              placeholder="// OpenAPI specification will appear here..."
              spellCheck={false}
            />
          </div>
        </div>
      )}

      {viewMode === "split" && (
        <div className="row g-3">
          {/* Left: Code Editor */}
          <div className="col-12 col-xl-5">
            <div className="card shadow-sm border-0 h-100">
              <div className="card-header bg-light d-flex justify-content-between align-items-center py-2 px-3 small">
                <span className="fw-semibold">
                  Live Spec Editor ({format.toUpperCase()})
                </span>
                <span className="text-muted small">
                  {rawText ? `${rawText.split("\n").length} lines` : "Empty"}
                </span>
              </div>
              <div className="card-body p-0">
                <textarea
                  className="form-control font-monospace border-0 rounded-0"
                  style={{
                    minHeight: "650px",
                    height: "100%",
                    fontSize: "12px",
                    backgroundColor: "#1e1e1e",
                    color: "#d4d4d4",
                    lineHeight: "1.5",
                    resize: "none",
                  }}
                  value={rawText}
                  onChange={handleTextChange}
                  placeholder="// OpenAPI specification will appear here..."
                  spellCheck={false}
                />
              </div>
            </div>
          </div>

          {/* Right: Swagger UI Preview */}
          <div className="col-12 col-xl-7">
            <SwaggerPreview
              spec={specObject}
              onGenerateSpec={() => triggerGenerate("json")}
              height="700px"
            />
          </div>
        </div>
      )}

      {/* Screen Navigation Footer */}
      <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          onClick={() => onNavigate?.("analysis")}
        >
          ← Back to AST Analysis (Screen 2)
        </button>

        <button
          type="button"
          className="btn btn-sm btn-primary"
          onClick={() => onNavigate?.("diff")}
        >
          Proceed to Spec Diff (Screen 4) →
        </button>
      </div>
    </div>
  );
}

