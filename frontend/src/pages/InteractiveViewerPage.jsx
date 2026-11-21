import React from "react";
import SwaggerPreview from "../components/viewer/SwaggerPreview.jsx";

/**
 * InteractiveViewerPage: Dedicated Swagger UI viewer page.
 */
export default function InteractiveViewerPage({ spec, onGenerateSpec }) {
  return (
    <div className="py-2">
      <div className="mb-3">
        <h2 className="h4 mb-1 fw-bold">Interactive API Documentation Viewer</h2>
        <p className="text-muted small mb-0">
          Explore extracted routes, test operations, and inspect schemas via Swagger UI.
        </p>
      </div>
      <SwaggerPreview spec={spec} onGenerateSpec={onGenerateSpec} height="850px" />
    </div>
  );
}

