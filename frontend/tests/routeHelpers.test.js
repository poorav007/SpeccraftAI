import { describe, expect, it } from "vitest";
import {
  computeMethodStats,
  extractAllTags,
  filterEndpoints,
  getMethodBadgeClass,
  updateEndpointMetadata,
} from "../src/utils/routeHelpers.js";

describe("routeHelpers unit test suite", () => {
  const sampleEndpoints = [
    {
      path: "/items",
      method: "get",
      operation_id: "list_items",
      summary: "List all store items",
      description: "Returns paginated list",
      tags: ["items", "public"],
      parameters: [{ name: "skip", location: "query", type: "int" }],
      warnings: [],
    },
    {
      path: "/items",
      method: "post",
      operation_id: "create_item",
      summary: "Create a new item",
      description: "Admin only",
      tags: ["items", "admin"],
      parameters: [],
      warnings: [],
    },
    {
      path: "/items/{item_id}",
      method: "get",
      operation_id: "get_item",
      summary: "Get item by ID",
      tags: ["items"],
      parameters: [{ name: "item_id", location: "path", required: true }],
      warnings: [],
    },
    {
      path: "/items/{item_id}",
      method: "delete",
      operation_id: "delete_item",
      summary: "Delete item",
      tags: ["items"],
      parameters: [{ name: "item_id", location: "path", required: true }],
      warnings: [{ code: "SC-W001", message: "Dynamic path warning" }],
    },
    {
      path: "/orders",
      method: "post",
      operation_id: "place_order",
      summary: "Place a customer order",
      tags: ["orders"],
      parameters: [],
      warnings: [],
    },
  ];

  it("computeMethodStats computes correct counts for standard methods", () => {
    const stats = computeMethodStats(sampleEndpoints);
    expect(stats.ALL).toBe(5);
    expect(stats.GET).toBe(2);
    expect(stats.POST).toBe(2);
    expect(stats.DELETE).toBe(1);
    expect(stats.PUT).toBe(0);
    expect(stats.PATCH).toBe(0);
  });

  it("extractAllTags extracts deduplicated and sorted tags", () => {
    const tags = extractAllTags(sampleEndpoints);
    expect(tags).toEqual(["admin", "items", "orders", "public"]);
  });

  it("filterEndpoints filters by HTTP method", () => {
    const getRoutes = filterEndpoints(sampleEndpoints, { method: "GET" });
    expect(getRoutes).toHaveLength(2);
    expect(getRoutes.every((r) => r.method.toUpperCase() === "GET")).toBe(true);

    const postRoutes = filterEndpoints(sampleEndpoints, { method: "POST" });
    expect(postRoutes).toHaveLength(2);

    const deleteRoutes = filterEndpoints(sampleEndpoints, { method: "DELETE" });
    expect(deleteRoutes).toHaveLength(1);
    expect(deleteRoutes[0].operation_id).toBe("delete_item");
  });

  it("filterEndpoints filters by tag", () => {
    const orderRoutes = filterEndpoints(sampleEndpoints, { tag: "orders" });
    expect(orderRoutes).toHaveLength(1);
    expect(orderRoutes[0].path).toBe("/orders");

    const itemRoutes = filterEndpoints(sampleEndpoints, { tag: "items" });
    expect(itemRoutes).toHaveLength(4);
  });

  it("filterEndpoints filters by search term across path, operationId, and summary", () => {
    // Search path
    const searchById = filterEndpoints(sampleEndpoints, { search: "{item_id}" });
    expect(searchById).toHaveLength(2);

    // Search operation ID
    const searchOpId = filterEndpoints(sampleEndpoints, { search: "place_order" });
    expect(searchOpId).toHaveLength(1);
    expect(searchOpId[0].path).toBe("/orders");

    // Search summary
    const searchSummary = filterEndpoints(sampleEndpoints, { search: "paginated" });
    expect(searchSummary).toHaveLength(1);
    expect(searchSummary[0].operation_id).toBe("list_items");

    // Non-matching search
    const searchNoMatch = filterEndpoints(sampleEndpoints, { search: "nonexistent" });
    expect(searchNoMatch).toHaveLength(0);
  });

  it("filterEndpoints filters for warnings only", () => {
    const warningRoutes = filterEndpoints(sampleEndpoints, { hasWarningsOnly: true });
    expect(warningRoutes).toHaveLength(1);
    expect(warningRoutes[0].operation_id).toBe("delete_item");
    expect(warningRoutes[0].warnings).toHaveLength(1);
  });

  it("updateEndpointMetadata updates documentation while locking AST facts", () => {
    const updated = updateEndpointMetadata(sampleEndpoints, {
      path: "/items",
      method: "get",
      operation_id: "list_catalog_items",
      summary: "Updated summary text",
      description: "Updated description text",
      tags: ["catalog", "public"],
    });

    const target = updated.find((ep) => ep.path === "/items" && ep.method === "get");
    expect(target).toBeDefined();
    expect(target.operation_id).toBe("list_catalog_items");
    expect(target.summary).toBe("Updated summary text");
    expect(target.description).toBe("Updated description text");
    expect(target.tags).toEqual(["catalog", "public"]);
    expect(target.is_customized).toBe(true);

    // AST facts MUST remain untouched
    expect(target.parameters).toEqual(sampleEndpoints[0].parameters);
    expect(target.path).toBe("/items");
    expect(target.method).toBe("get");

    // Other routes untouched
    const untouched = updated.find((ep) => ep.path === "/orders");
    expect(untouched.operation_id).toBe("place_order");
  });

  it("getMethodBadgeClass returns proper badge class mapping", () => {
    expect(getMethodBadgeClass("get")).toBe("badge-method-get");
    expect(getMethodBadgeClass("GET")).toBe("badge-method-get");
    expect(getMethodBadgeClass("POST")).toBe("badge-method-post");
    expect(getMethodBadgeClass("PUT")).toBe("badge-method-put");
    expect(getMethodBadgeClass("DELETE")).toBe("badge-method-delete");
    expect(getMethodBadgeClass("PATCH")).toBe("badge-method-patch");
    expect(getMethodBadgeClass("HEAD")).toBe("badge-method-other");
  });
});

