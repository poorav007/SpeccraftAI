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
      throw new Error(`Request timed out after ${timeoutMs}ms.`);
    }
    throw err;
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

