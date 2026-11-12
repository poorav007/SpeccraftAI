import { beforeEach, describe, expect, it, vi } from "vitest";
import { buildOpenApiFromEndpoints, parseRouteCode } from "../src/utils/parser.js";
import { STORAGE_KEY, loadState, saveState } from "../src/utils/localStorage.js";

function createMemoryStorage() {
  const store = new Map();
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  };
}

describe("Screen 1 regex parser stub", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", createMemoryStorage());
  });

  it("extracts Express routes cleanly without requiring whitespace before '('", () => {
    const sample = `
      app.get('/api/users', listUsers);
      app.post("/api/users", createUser);
      router.delete('/api/users/:id', removeUser);
    `;
    const result = parseRouteCode(sample);

    expect(result.error).toBeNull();
    expect(result.parseTimeMs).toBeGreaterThanOrEqual(0);
    expect(result.endpoints).toEqual([
      { method: "GET", path: "/api/users" },
      { method: "POST", path: "/api/users" },
      { method: "DELETE", path: "/api/users/:id" },
    ]);
  });

  it("extracts Flask and FastAPI decorator routes", () => {
    const sample = `
      @app.get("/items")
      def list_items():
          return []

      @app.route('/orders', methods=['GET', 'POST'])
      def orders():
          return {}
    `;
    const result = parseRouteCode(sample);

    expect(result.error).toBeNull();
    expect(result.endpoints).toEqual([
      { method: "GET", path: "/items" },
      { method: "GET", path: "/orders" },
      { method: "POST", path: "/orders" },
    ]);
  });

  it("returns an actionable error for empty or unmatched input", () => {
    const empty = parseRouteCode("   ");
    expect(empty.endpoints).toEqual([]);
    expect(empty.error).toContain("Please paste route code");

    const unmatched = parseRouteCode("const x = 42;");
    expect(unmatched.endpoints).toEqual([]);
    expect(unmatched.error).toContain("No supported route definitions found");
  });

  it("builds a valid minimal OpenAPI 3.0 spec and persists to localStorage via saveState", () => {
    const parsed = parseRouteCode("app.get('/api/users/:id', getUser);");
    const spec = buildOpenApiFromEndpoints(parsed.endpoints);

    expect(spec.openapi).toBe("3.0.3");
    expect(spec.paths["/api/users/{id}"].get.parameters[0]).toEqual({
      name: "id",
      in: "path",
      required: true,
      schema: { type: "string" },
    });

    const current = loadState();
    const saveResult = saveState({
      ...current,
      endpoints: parsed.endpoints,
      specs: { ...current.specs, "parsed-preview": spec },
    });
    expect(saveResult.ok).toBe(true);

    const stored = JSON.parse(globalThis.localStorage.getItem(STORAGE_KEY));
    expect(stored.endpoints).toEqual([{ method: "GET", path: "/api/users/:id" }]);
    expect(stored.specs["parsed-preview"].paths["/api/users/{id}"]).toBeDefined();
  });
});

