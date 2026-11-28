/**
 * SpecCraft AI Frontend API Client
 *
 * Handles HTTP communication with the Python FastAPI backend (/api/*).
 * Includes timeout handling and graceful offline fallback detection.
 */

export const API_BASE_URL =
  import.meta.env?.VITE_API_BASE_URL || "http://localhost:8000/api";

const DEFAULT_TIMEOUT_MS = 15000;

/**
 * Helper to execute a fetch request with an AbortController timeout.
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  const externalSignal = options.signal;

  function onExternalAbort() {
    controller.abort();
  }
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (err) {
    clearTimeout(id);
    if (err.name === "AbortError") {
      if (externalSignal?.aborted) {
        const abortErr = new Error("Request aborted.");
        abortErr.name = "AbortError";
        throw abortErr;
      }
      throw new Error(`Request timed out after ${timeoutMs}ms.`);
    }
    throw err;
  } finally {
    externalSignal?.removeEventListener("abort", onExternalAbort);
  }
}

/**
 * Checks if the backend FastAPI service is running and healthy.
 *
 * @returns {Promise<{ ok: boolean, data?: object, error?: string }>}
 */
export async function checkBackendHealth() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/health`, { method: "GET" }, 2500);
    if (!res.ok) {
      return { ok: false, error: `Health check failed with status ${res.status}` };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err.message || "Backend server unreachable." };
  }
}

/**
 * Statically parses a raw code string using the backend AST extractor.
 *
 * @param {string} code - Python/FastAPI code string.
 * @param {string} [filename='main.py'] - Virtual filename.
 * @returns {Promise<{ ok: boolean, result?: object, error?: string }>}
 */
export async function parseCodeSnippet(code, filename = "main.py") {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/parse/json`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, filename }),
    });

    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Server returned error (${res.status})` };
    }
    return { ok: true, result: body };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to communicate with backend parser." };
  }
}

/**
 * Safely uploads a .zip project archive or .py file for static AST extraction.
 *
 * @param {File} file - Browser File object.
 * @returns {Promise<{ ok: boolean, result?: object, error?: string }>}
 */
export async function uploadAndParseArchive(file) {
  try {
    const formData = new FormData();
    formData.append("file", file, file.name);

    const res = await fetchWithTimeout(`${API_BASE_URL}/parse`, {
      method: "POST",
      body: formData,
    });

    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Server returned error (${res.status})` };
    }
    return { ok: true, result: body };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to upload project archive to backend." };
  }
}

/**
 * Generates an OpenAPI 3.0.3 specification from extraction results or code.
 *
 * @param {object} payload - { extraction_result?, code?, title?, version?, format? }
 * @returns {Promise<{ ok: boolean, spec?: object|string, format?: string, error?: string }>}
 */
export async function generateOpenApiSpec(payload) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Generation failed (${res.status})` };
    }
    return { ok: true, spec: body.spec, format: body.format };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to generate OpenAPI specification." };
  }
}

/**
 * Validates an OpenAPI 3.0 specification using backend schema integrity validator.
 *
 * @param {object|string} spec - OpenAPI specification dictionary or string.
 * @returns {Promise<{ ok: boolean, report?: object, error?: string }>}
 */
export async function validateOpenApiSpec(spec) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec }),
    });

    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Validation request failed (${res.status})` };
    }
    return { ok: true, report: body };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to connect to validation service." };
  }
}

/**
 * Compares two OpenAPI 3.0 specifications and returns structural differences.
 *
 * @param {object|string} baselineSpec - Baseline specification S1.
 * @param {object|string} targetSpec - Target specification S2.
 * @returns {Promise<{ ok: boolean, report?: object, error?: string }>}
 */
export async function compareOpenApiSpecs(baselineSpec, targetSpec) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/diff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ baseline_spec: baselineSpec, target_spec: targetSpec }),
    });

    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Diff failed (${res.status})` };
    }
    return { ok: true, report: body };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to compare specifications." };
  }
}

/**
 * Converts an OpenAPI 3.0 specification into a Postman Collection v2.1 JSON object.
 *
 * @param {object|string} spec - OpenAPI specification dictionary or string.
 * @returns {Promise<{ ok: boolean, collection?: object, error?: string }>}
 */
export async function exportPostmanCollection(spec) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/export/postman`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec }),
    });

    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Postman export failed (${res.status})` };
    }
    return { ok: true, collection: body };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to export Postman collection." };
  }
}

/**
 * Converts an OpenAPI 3.0 specification into clean YAML via backend ExportManager.
 *
 * @param {object|string} spec - OpenAPI specification dictionary or string.
 * @returns {Promise<{ ok: boolean, yaml?: string, error?: string }>}
 */
export async function exportSpecYaml(spec) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/export/yaml`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec }),
    });

    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `YAML export failed (${res.status})` };
    }
    return { ok: true, yaml: body.content };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to serialize specification to YAML." };
  }
}

/**
 * Downloads a complete ZIP documentation bundle from the backend ExportManager.
 *
 * @param {object|string} spec - OpenAPI specification.
 * @param {object|null} [validationReport=null] - Optional validation report.
 * @returns {Promise<{ ok: boolean, blob?: Blob, error?: string }>}
 */
export async function exportBundleZip(spec, validationReport = null) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/export/bundle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec, validation_report: validationReport }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Bundle export failed (${res.status})` };
    }
    const blob = await res.blob();
    return { ok: true, blob };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to download export bundle." };
  }
}

/**
 * Requests AI endpoint documentation proposal with optional AbortSignal.
 */
export async function enrichEndpointDocs(endpoint, { signal } = {}) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/ai/enrich-endpoint`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        method: endpoint?.method || "get",
        path: endpoint?.path || "/",
        operation_id: endpoint?.operation_id || null,
        summary: endpoint?.summary || null,
        description: endpoint?.description || null,
        tags: endpoint?.tags || [],
        parameters: endpoint?.parameters || [],
        request_body: endpoint?.request_body || null,
      }),
      signal,
    });
    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `AI enrich failed (${res.status})` };
    }
    return { ok: true, proposal: body };
  } catch (err) {
    return { ok: false, aborted: err.name === "AbortError", error: err.message || "AI service unreachable." };
  }
}

/**
 * Requests plain-language explanation for a schema attribute or parameter.
 */
export async function explainSchemaField(fieldPayload, { signal } = {}) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/ai/explain-schema`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fieldPayload),
      signal,
    });
    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `AI explain failed (${res.status})` };
    }
    return { ok: true, explanation: body };
  } catch (err) {
    return { ok: false, aborted: err.name === "AbortError", error: err.message || "AI service unreachable." };
  }
}

/**
 * Summarizes specification diff changes and returns mobile-ready cards array.
 */
export async function summarizeSpecDiff(diffReport, { signal } = {}) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/ai/summarize-diff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        summary: diffReport?.summary || {},
        changes: diffReport?.changes || [],
      }),
      signal,
    });
    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `AI diff summary failed (${res.status})` };
    }
    return { ok: true, report: body };
  } catch (err) {
    return { ok: false, aborted: err.name === "AbortError", error: err.message || "AI service unreachable." };
  }
}

/**
 * Persists a route documentation override in speccraft.overlay.json via backend.
 */
export async function saveOverlayEntry(endpoint, source = "human") {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/overlay/entry`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        method: endpoint?.method || "get",
        path: endpoint?.path || "/",
        operation_id: endpoint?.operation_id || null,
        summary: endpoint?.summary ?? null,
        description: endpoint?.description ?? null,
        tags: endpoint?.tags ?? null,
        source,
      }),
    });
    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Overlay save failed (${res.status})` };
    }
    return { ok: true, data: body };
  } catch (err) {
    return { ok: false, error: err.message || "Overlay service unreachable." };
  }
}

/**
 * Deletes an orphaned overlay entry by canonical key (`METHOD /path`).
 */
export async function deleteOverlayEntry(key) {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE_URL}/overlay/entry?key=${encodeURIComponent(key)}`,
      { method: "DELETE" }
    );
    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Overlay delete failed (${res.status})` };
    }
    return { ok: true, data: body };
  } catch (err) {
    return { ok: false, error: err.message || "Overlay service unreachable." };
  }
}

/**
 * Generates a white-label @media print HTML client handoff report from the backend.
 */
export async function exportHandoffHtml(
  spec,
  { validationReport = null, brandName = "SpecCraft AI" } = {}
) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/export/handoff-html`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        spec,
        validation_report: validationReport,
        brand_name: brandName || "SpecCraft AI",
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.detail || `Handoff export failed (${res.status})` };
    }
    const html = await res.text();
    return { ok: true, html };
  } catch (err) {
    return { ok: false, error: err.message || "Failed to generate handoff HTML." };
  }
}

/**
 * Generates TypeScript or Python client SDK code from an OpenAPI spec.
 */
export async function exportSdkCode(spec, language = "typescript") {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/export/sdk`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec, language }),
    });
    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `SDK generation failed (${res.status})` };
    }
    return { ok: true, files: body.files };
  } catch (err) {
    return { ok: false, error: err.message || "SDK generator unreachable." };
  }
}

/**
 * Generates a standalone runnable FastAPI mock_server.py from an OpenAPI spec.
 */
export async function exportMockServer(spec) {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/export/mock-server`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec }),
    });
    const body = await res.json();
    if (!res.ok) {
      return { ok: false, error: body.detail || `Mock server generation failed (${res.status})` };
    }
    return { ok: true, filename: body.filename, code: body.code };
  } catch (err) {
    return { ok: false, error: err.message || "Mock server generator unreachable." };
  }
}


