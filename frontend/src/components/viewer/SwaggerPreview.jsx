import React, { Component } from "react";
import SwaggerUI from "swagger-ui-react";
import "swagger-ui-react/swagger-ui.css";

/**
 * Error boundary for SwaggerUI to prevent full UI crashes if a malformed spec is passed.
 */
class SwaggerErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("SwaggerUI render error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="alert alert-warning p-4 m-3 rounded">
          <h5 className="alert-heading fw-bold">⚠️ Swagger UI Rendering Issue</h5>
          <p className="small mb-2">
            The generated specification could not be rendered in Swagger UI. This typically occurs
            when YAML/JSON contains syntax errors or missing required fields.
          </p>
          <pre className="small bg-light p-2 rounded mb-3">
            {this.state.error?.message || "Unknown error"}
          </pre>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Retry Render
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * Interactive Swagger UI Preview component for OpenAPI 3.0 specifications.
 */
export default function SwaggerPreview({
  spec = null,
  onGenerateSpec,
  height = "750px",
}) {
  if (!spec) {
    return (
      <div className="card text-center p-5 border-dashed my-3">
        <div className="card-body">
          <div className="display-6 mb-3">📖</div>
          <h5 className="card-title fw-bold">No OpenAPI Specification Loaded</h5>
          <p className="card-text text-muted mb-4 small mx-auto" style={{ maxWidth: "460px" }}>
            Generate a specification from extracted endpoints or paste an OpenAPI JSON document to
            preview interactive documentation through Swagger UI.
          </p>
          {onGenerateSpec && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={onGenerateSpec}
            >
              Generate OpenAPI 3.0 Spec Now
            </button>
          )}
        </div>
      </div>
    );
  }

  // Ensure spec is an object for SwaggerUI
  let specObject = spec;
  if (typeof spec === "string") {
    try {
      specObject = JSON.parse(spec);
    } catch {
      // If it's YAML, SwaggerUI supports url or objects; pass through or handle in wrapper
      specObject = null;
    }
  }

  if (!specObject) {
    return (
      <div className="alert alert-info p-4 m-3">
        <h6 className="fw-bold mb-1">YAML Preview Note</h6>
        <p className="small text-muted mb-0">
          Swagger UI renders from JSON objects. Switch the view mode to <strong>JSON</strong> or
          inspect the raw spec in the <strong>Spec Code Editor</strong> tab.
        </p>
      </div>
    );
  }

  return (
    <div
      className="swagger-preview-container border rounded bg-white shadow-sm overflow-auto"
      style={{ minHeight: "500px", maxHeight: height }}
    >
      <SwaggerErrorBoundary>
        <SwaggerUI
          spec={specObject}
          docExpansion="list"
          defaultModelsExpandDepth={1}
          displayRequestDuration={true}
        />
      </SwaggerErrorBoundary>
    </div>
  );
}

