import { describe, expect, it } from "vitest";
import { SAMPLE_SHOP_V1 } from "../src/config/sampleSpecs.js";
import {
  convertObjectToYaml,
  convertOpenApiToPostman,
  formatValidationReportMarkdown,
} from "../src/utils/fileHelpers.js";

describe("Export Center & Postman v2.1 offline helpers", () => {
  it("converts SAMPLE_SHOP_V1 to valid Postman Collection v2.1 schema", () => {
    const collection = convertOpenApiToPostman(SAMPLE_SHOP_V1);

    expect(collection.info.schema).toBe(
      "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    );
    expect(collection.info.name).toBe("FastAPI Shop API");
    expect(collection.variable[0]).toEqual({
      key: "baseUrl",
      value: "http://localhost:8000",
      type: "string",
    });
    expect(collection.item.length).toBeGreaterThan(0);
  });

  it("converts OpenAPI path variables and query params into Postman format", () => {
    const collection = convertOpenApiToPostman(SAMPLE_SHOP_V1);
    const allRequests = collection.item.flatMap((folder) => folder.item);

    const getItem = allRequests.find(
      (r) => r.request.method === "GET" && r.request.url.raw.includes("/items/:item_id")
    );
    expect(getItem).toBeDefined();
    expect(getItem.request.url.path).toEqual(["items", ":item_id"]);
    expect(getItem.request.url.variable[0].key).toBe("item_id");

    const listItems = allRequests.find(
      (r) => r.request.method === "GET" && r.request.url.raw.includes("/items?")
    );
    expect(listItems).toBeDefined();
    const queryKeys = listItems.request.url.query.map((q) => q.key);
    expect(queryKeys).toContain("skip");
    expect(queryKeys).toContain("limit");
  });

  it("generates sample JSON request body and Content-Type header for POST endpoints", () => {
    const collection = convertOpenApiToPostman(SAMPLE_SHOP_V1);
    const allRequests = collection.item.flatMap((folder) => folder.item);
    const createItem = allRequests.find(
      (r) => r.request.method === "POST" && r.request.url.raw.endsWith("/items")
    );

    expect(createItem).toBeDefined();
    expect(createItem.request.header).toContainEqual({
      key: "Content-Type",
      value: "application/json",
    });
    expect(createItem.request.body.mode).toBe("raw");
    const parsedBody = JSON.parse(createItem.request.body.raw);
    expect(parsedBody).toHaveProperty("name");
    expect(parsedBody).toHaveProperty("price");
  });

  it("handles circular $ref schemas safely without infinite recursion", () => {
    const circularSpec = {
      openapi: "3.0.3",
      info: { title: "Tree API", version: "1.0.0" },
      paths: {
        "/tree": {
          post: {
            tags: ["tree"],
            requestBody: {
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/TreeNode" },
                },
              },
            },
            responses: { "200": { description: "OK" } },
          },
        },
      },
      components: {
        schemas: {
          TreeNode: {
            type: "object",
            properties: {
              label: { type: "string" },
              next: { $ref: "#/components/schemas/TreeNode" },
            },
          },
        },
      },
    };

    const collection = convertOpenApiToPostman(circularSpec);
    const req = collection.item[0].item[0].request;
    const body = JSON.parse(req.body.raw);
    expect(body.label).toBe("string");
    expect(body.next).toEqual({});
  });

  it("serializes OpenAPI spec to YAML and builds Markdown validation audit report", () => {
    const yaml = convertObjectToYaml(SAMPLE_SHOP_V1);
    expect(yaml).toContain("openapi: 3.0.3");
    expect(yaml).toContain("FastAPI Shop API");

    const report = formatValidationReportMarkdown(SAMPLE_SHOP_V1, {
      is_valid: true,
      errors: [],
      warnings: [{ code: "WARN_NO_TAG", message: "Optional tag missing" }],
    });
    expect(report).toContain("# SpecCraft AI — Validation Audit Report");
    expect(report).toContain("**Status**: VALID");
    expect(report).toContain("WARN_NO_TAG");
  });
});

