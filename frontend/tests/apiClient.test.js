import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  checkBackendHealth,
  compareOpenApiSpecs,
  generateOpenApiSpec,
  normalizeApiBaseUrl,
  parseCodeSnippet,
  parseGithubRepo,
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

  it("compareOpenApiSpecs calls /diff endpoint", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        baseline_version: "1.0.0",
        target_version: "2.0.0",
        summary: { total_changes: 2, breaking_changes: 1, non_breaking_changes: 1 },
        changes: [],
      }),
    });

    const res = await compareOpenApiSpecs({ openapi: "3.0.3" }, { openapi: "3.0.3" });
    expect(res.ok).toBe(true);
    expect(res.report.summary.total_changes).toBe(2);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/diff"),
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("normalizeApiBaseUrl handles hosts with or without /api and scheme", () => {
    expect(normalizeApiBaseUrl("")).toBe("http://localhost:8000/api");
    expect(normalizeApiBaseUrl("https://api.onrender.com")).toBe("https://api.onrender.com/api");
    expect(normalizeApiBaseUrl("https://api.onrender.com/api/")).toBe("https://api.onrender.com/api");
    expect(normalizeApiBaseUrl("my-backend.onrender.com")).toBe("https://my-backend.onrender.com/api");
  });

  it("checkBackendHealth triggers onWaking and succeeds on cold-start retry", async () => {
    const onWaking = vi.fn();
    fetch
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "healthy" }),
      });

    const res = await checkBackendHealth({ retryOnColdStart: true, onWaking });
    expect(onWaking).toHaveBeenCalledTimes(1);
    expect(res.ok).toBe(true);
    expect(res.wakingAttempted).toBe(true);
  });

  it("parseGithubRepo posts repo_url to /parse/github", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ endpoints: [{ method: "get", path: "/health" }], files_scanned: 2 }),
    });

    const res = await parseGithubRepo("https://github.com/owner/repo", "main");
    expect(res.ok).toBe(true);
    expect(res.result.endpoints).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/parse/github"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ repo_url: "https://github.com/owner/repo", ref: "main" }),
      })
    );
  });
});

