import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  checkBackendHealth,
  generateOpenApiSpec,
  parseCodeSnippet,
  uploadAndParseArchive,
  validateOpenApiSpec,
} from "../src/services/apiClient.js";

describe("apiClient service suite", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("checkBackendHealth returns ok=true when backend responds 200", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "healthy", version: "0.1.0" }),
    });

    const res = await checkBackendHealth();
    expect(res.ok).toBe(true);
    expect(res.data.status).toBe("healthy");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.objectContaining({ method: "GET" })
    );
  });

  it("checkBackendHealth returns ok=false when backend is offline", async () => {
    fetch.mockRejectedValueOnce(new Error("Connection refused"));

    const res = await checkBackendHealth();
    expect(res.ok).toBe(false);
    expect(res.error).toContain("Connection refused");
  });

  it("parseCodeSnippet posts code and returns parsed result", async () => {
    const mockResult = {
      endpoints: [{ path: "/users", method: "get", operation_id: "get_users" }],
      files_scanned: 1,
      total_loc: 10,
    };
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResult,
    });

    const res = await parseCodeSnippet("app.get('/users')", "main.py");
    expect(res.ok).toBe(true);
    expect(res.result.endpoints.length).toBe(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/parse/json"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ code: "app.get('/users')", filename: "main.py" }),
      })
    );
  });

  it("uploadAndParseArchive attaches File to FormData and posts to /parse", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        endpoints: [{ path: "/items", method: "post" }],
        files_scanned: 3,
      }),
    });

    const fakeFile = new File(["dummy zip content"], "project.zip", {
      type: "application/zip",
    });

    const res = await uploadAndParseArchive(fakeFile);
    expect(res.ok).toBe(true);
    expect(res.result.endpoints.length).toBe(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/parse"),
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      })
    );
  });

  it("generateOpenApiSpec calls /generate endpoint", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        format: "json",
        spec: { openapi: "3.0.3", info: { title: "Generated" } },
      }),
    });

    const res = await generateOpenApiSpec({ title: "My API", format: "json" });
    expect(res.ok).toBe(true);
    expect(res.spec.openapi).toBe("3.0.3");
  });

  it("validateOpenApiSpec calls /validate endpoint", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        is_valid: true,
        errors: [],
        warnings: [],
      }),
    });

    const res = await validateOpenApiSpec({ openapi: "3.0.3" });
    expect(res.ok).toBe(true);
    expect(res.report.is_valid).toBe(true);
  });
});

