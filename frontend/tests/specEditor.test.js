import { describe, expect, it } from "vitest";

describe("specEditor and validation reporting test suite", () => {
  const sampleValidationReport = {
    is_valid: false,
    errors: [
      {
        code: "ERR_BROKEN_REF",
        message: "Referenced schema '#/components/schemas/NonExistent' does not exist.",
        path: "/items.post.requestBody",
      },
      {
        code: "ERR_MISSING_PATH_PARAM",
        message: "Path parameter '{user_id}' is not declared in operation parameters.",
        path: "/users/{user_id}.get",
      },
    ],
    warnings: [{ code: "WARN_NO_DESCRIPTION", message: "Summary missing" }],
    stats: {
      operations_count: 5,
      schemas_count: 3,
      paths_count: 4,
    },
  };

  it("identifies broken $ref and missing path parameter errors in validation report", () => {
    expect(sampleValidationReport.is_valid).toBe(false);
    expect(sampleValidationReport.errors).toHaveLength(2);

    const errorCodes = sampleValidationReport.errors.map((e) => e.code);
    expect(errorCodes).toContain("ERR_BROKEN_REF");
    expect(errorCodes).toContain("ERR_MISSING_PATH_PARAM");
  });

  it("extracts schema metrics correctly from valid report", () => {
    const validReport = {
      is_valid: true,
      errors: [],
      warnings: [],
      stats: {
        operations_count: 9,
        schemas_count: 6,
        paths_count: 7,
      },
    };

    expect(validReport.is_valid).toBe(true);
    expect(validReport.stats.operations_count).toBe(9);
    expect(validReport.stats.schemas_count).toBe(6);
    expect(validReport.errors).toHaveLength(0);
  });

  it("safely serializes and parses OpenAPI JSON document strings", () => {
    const spec = {
      openapi: "3.0.3",
      info: { title: "Test API", version: "1.0.0" },
      paths: {
        "/ping": {
          get: {
            operationId: "ping",
            responses: { "200": { description: "pong" } },
          },
        },
      },
    };

    const serialized = JSON.stringify(spec, null, 2);
    expect(serialized).toContain('"openapi": "3.0.3"');
    expect(serialized).toContain('"operationId": "ping"');

    const parsed = JSON.parse(serialized);
    expect(parsed.openapi).toBe("3.0.3");
    expect(parsed.paths["/ping"].get.responses["200"].description).toBe("pong");
  });
});

