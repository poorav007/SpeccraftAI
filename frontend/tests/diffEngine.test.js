import { describe, expect, it } from "vitest";
import {
  compareSpecsClientSide,
  computeDiffStats,
  filterChanges,
  getBreakingBadge,
  getChangeBadge,
  getMethodBadgeClass,
} from "../src/utils/diffHelpers.js";

describe("diffHelpers utility suite", () => {
  const sampleChanges = [
    {
      change_type: "removed",
      category: "operation",
      path: "/items/{item_id}",
      method: "DELETE",
      location: "paths./items/{item_id}.delete",
      description: "Endpoint DELETE /items/{item_id} was removed.",
      is_breaking: true,
      old_value: {},
      new_value: null,
    },
    {
      change_type: "added",
      category: "operation",
      path: "/items/batch",
      method: "POST",
      location: "paths./items/batch.post",
      description: "Endpoint POST /items/batch was added.",
      is_breaking: false,
      old_value: null,
      new_value: {},
    },
    {
      change_type: "added",
      category: "parameter",
      path: "/items",
      method: "POST",
      location: "paths./items.post.parameters[X-Shop-Tenant]",
      description: "Parameter 'X-Shop-Tenant' in header added (REQUIRED).",
      is_breaking: true,
      old_value: null,
      new_value: { name: "X-Shop-Tenant", in: "header", required: true },
    },
    {
      change_type: "added",
      category: "parameter",
      path: "/items",
      method: "GET",
      location: "paths./items.get.parameters[sort_by]",
      description: "Parameter 'sort_by' in query added (optional).",
      is_breaking: false,
      old_value: null,
      new_value: { name: "sort_by", in: "query", required: false },
    },
    {
      change_type: "modified",
      category: "parameter",
      path: "/items/{item_id}",
      method: "GET",
      location: "paths./items/{item_id}.get.parameters[item_id].schema.type",
      description: "Parameter 'item_id' schema type altered from 'integer' to 'string'.",
      is_breaking: true,
      old_value: "integer",
      new_value: "string",
    },
  ];

  it("computeDiffStats correctly tallies change metrics", () => {
    const stats = computeDiffStats(sampleChanges);
    expect(stats.total).toBe(5);
    expect(stats.breaking).toBe(3);
    expect(stats.nonBreaking).toBe(2);
    expect(stats.added).toBe(3);
    expect(stats.removed).toBe(1);
    expect(stats.modified).toBe(1);
  });

  it("computeDiffStats returns zeroed metrics for empty or invalid input", () => {
    const stats = computeDiffStats(null);
    expect(stats.total).toBe(0);
    expect(stats.breaking).toBe(0);
  });

  it("filterChanges filters by breaking changes only", () => {
    const filtered = filterChanges(sampleChanges, { filterType: "breaking" });
    expect(filtered.length).toBe(3);
    filtered.forEach((c) => expect(c.is_breaking).toBe(true));
  });

  it("filterChanges filters by non-breaking changes only", () => {
    const filtered = filterChanges(sampleChanges, { filterType: "non_breaking" });
    expect(filtered.length).toBe(2);
    filtered.forEach((c) => expect(c.is_breaking).toBe(false));
  });

  it("filterChanges filters by change_type", () => {
    const added = filterChanges(sampleChanges, { filterType: "added" });
    expect(added.length).toBe(3);

    const removed = filterChanges(sampleChanges, { filterType: "removed" });
    expect(removed.length).toBe(1);
    expect(removed[0].path).toBe("/items/{item_id}");

    const modified = filterChanges(sampleChanges, { filterType: "modified" });
    expect(modified.length).toBe(1);
  });

  it("filterChanges searches by path, method, and description", () => {
    const searchPath = filterChanges(sampleChanges, { search: "batch" });
    expect(searchPath.length).toBe(1);
    expect(searchPath[0].path).toBe("/items/batch");

    const searchMethod = filterChanges(sampleChanges, { search: "delete" });
    expect(searchMethod.length).toBe(1);

    const searchDesc = filterChanges(sampleChanges, { search: "tenant" });
    expect(searchDesc.length).toBe(1);
  });

  it("getBreakingBadge adheres to dual-channel accessibility", () => {
    const breaking = getBreakingBadge(true);
    expect(breaking.label).toContain("BREAKING");
    expect(breaking.label).toContain("🚨");
    expect(breaking.bgClass).toContain("bg-danger");
    expect(breaking.ariaLabel).toBeDefined();

    const nonBreaking = getBreakingBadge(false);
    expect(nonBreaking.label).toContain("NON-BREAKING");
    expect(nonBreaking.label).toContain("✓");
    expect(nonBreaking.ariaLabel).toBeDefined();
  });

  it("getChangeBadge returns correct symbols", () => {
    expect(getChangeBadge("added").label).toBe("+ ADDED");
    expect(getChangeBadge("removed").label).toBe("- REMOVED");
    expect(getChangeBadge("modified").label).toBe("~ MODIFIED");
  });

  it("getMethodBadgeClass returns valid color badges", () => {
    expect(getMethodBadgeClass("get")).toContain("bg-primary");
    expect(getMethodBadgeClass("post")).toContain("bg-success");
    expect(getMethodBadgeClass("delete")).toContain("bg-danger");
  });

  it("compareSpecsClientSide detects breaking and non-breaking changes accurately", () => {
    const s1 = {
      openapi: "3.0.3",
      paths: {
        "/users": {
          get: {
            parameters: [
              { name: "page", in: "query", required: false, schema: { type: "integer" } },
            ],
            responses: { "200": { description: "OK" } },
          },
          delete: {
            responses: { "204": { description: "Deleted" } },
          },
        },
      },
    };

    const s2 = {
      openapi: "3.0.3",
      paths: {
        "/users": {
          get: {
            parameters: [
              { name: "page", in: "query", required: true, schema: { type: "integer" } }, // changed to required (BREAKING)
              { name: "limit", in: "query", required: false, schema: { type: "integer" } }, // added optional (NON-BREAKING)
            ],
            responses: { "204": { description: "OK" } }, // 200 removed (BREAKING)
          },
          // delete was removed (BREAKING)
        },
        "/users/export": {
          post: {
            responses: { "200": { description: "Exported" } }, // added endpoint (NON-BREAKING)
          },
        },
      },
    };

    const report = compareSpecsClientSide(s1, s2);
    expect(report.summary.total_changes).toBeGreaterThanOrEqual(5);
    expect(report.summary.breaking_changes).toBe(3); // delete removed, page made required, 200 response removed
    expect(report.summary.non_breaking_changes).toBe(2); // limit added optional, export added
  });
});

