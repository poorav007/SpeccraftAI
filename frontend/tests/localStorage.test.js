import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  STORAGE_KEY,
  clearState,
  createDefaultState,
  defaultState,
  loadState,
  resetState,
  saveState,
} from "../src/utils/localStorage.js";

function createMemoryStorage() {
  const store = new Map();
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(key, String(value));
    },
    removeItem(key) {
      store.delete(key);
    },
  };
}

describe("localStorage persistence helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", createMemoryStorage());
  });

  it("returns defaultState seed when storage is empty", () => {
    const loaded = loadState();
    expect(loaded).toEqual(defaultState);
    expect(loaded.endpoints).toEqual([]);
    expect(loaded.reviews).toEqual([]);
    expect(loaded.specs["sample-v1"].openapi).toBe("3.0.3");
  });

  it("saves and loads state under the 'speccraft' key", () => {
    const next = createDefaultState();
    next.endpoints.push({ method: "GET", path: "/items", summary: "List items" });
    next.reviews.push({ id: "REV-1", story: "US-01", status: "approved" });

    const res = saveState(next);
    expect(res).toEqual({ ok: true });

    const raw = globalThis.localStorage.getItem(STORAGE_KEY);
    expect(raw).toBeTruthy();

    const loaded = loadState();
    expect(loaded.endpoints).toHaveLength(1);
    expect(loaded.reviews[0].status).toBe("approved");
  });

  it("recovers safely with seed data when stored JSON is corrupt", () => {
    globalThis.localStorage.setItem(STORAGE_KEY, "{not-valid-json");
    expect(loadState()).toEqual(defaultState);

    globalThis.localStorage.setItem(STORAGE_KEY, "[]");
    expect(loadState()).toEqual(defaultState);
  });

  it("handles QuotaExceededError gracefully without throwing", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => null,
      setItem: () => {
        const err = new Error("QuotaExceededError");
        err.name = "QuotaExceededError";
        throw err;
      },
      removeItem: () => {},
    });

    const result = saveState(defaultState);
    expect(result.ok).toBe(false);
    expect(result.error).toContain("QuotaExceededError");
  });

  it("resets and clears state properly", () => {
    const modified = createDefaultState();
    modified.reviews.push({ id: "REV-9", story: "US-02", status: "flagged" });
    saveState(modified);

    const reset = resetState();
    expect(reset.reviews).toEqual([]);
    expect(loadState()).toEqual(defaultState);

    expect(clearState()).toEqual({ ok: true });
    expect(globalThis.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

