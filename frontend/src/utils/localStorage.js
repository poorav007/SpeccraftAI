import initialState from "../../../data/initial-state.json";

export const STORAGE_KEY = "speccraft";

/** Deep-clone plain JSON-compatible objects without mutating the seed template. */
function cloneState(value) {
  return JSON.parse(JSON.stringify(value));
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function getStorage() {
  try {
    return typeof globalThis !== "undefined" ? globalThis.localStorage : undefined;
  } catch {
    return undefined;
  }
}

export const defaultState = Object.freeze(cloneState(initialState));

/** Return a fresh mutable copy of the initial seed state. */
export function createDefaultState() {
  return cloneState(initialState);
}

/** Merge persisted partial objects safely into the default state shape. */
function normalizeState(parsed) {
  const base = createDefaultState();
  if (!isPlainObject(parsed)) {
    return base;
  }

  return {
    schemaVersion:
      typeof parsed.schemaVersion === "number" ? parsed.schemaVersion : base.schemaVersion,
    project: isPlainObject(parsed.project)
      ? { ...base.project, ...parsed.project }
      : base.project,
    endpoints: Array.isArray(parsed.endpoints) ? parsed.endpoints : base.endpoints,
    specs: isPlainObject(parsed.specs) ? parsed.specs : base.specs,
    reviews: Array.isArray(parsed.reviews) ? parsed.reviews : base.reviews,
  };
}

/** Load persisted SpecCraft state from localStorage, falling back to defaultState. */
export function loadState() {
  const storage = getStorage();
  if (!storage) {
    return createDefaultState();
  }

  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) {
      return createDefaultState();
    }
    const parsed = JSON.parse(raw);
    return normalizeState(parsed);
  } catch {
    return createDefaultState();
  }
}

/** Persist SpecCraft state to localStorage safely, catching quota/serialization errors. */
export function saveState(state) {
  const storage = getStorage();
  if (!storage) {
    return { ok: false, error: "localStorage is not available in this environment." };
  }

  try {
    const normalized = normalizeState(state);
    storage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    return { ok: true };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to persist state to localStorage.";
    return { ok: false, error: message };
  }
}

/** Reset localStorage back to the initial seed state and return the fresh copy. */
export function resetState() {
  const fresh = createDefaultState();
  saveState(fresh);
  return fresh;
}

/** Remove the persisted 'speccraft' key from localStorage. */
export function clearState() {
  const storage = getStorage();
  if (!storage) {
    return { ok: false, error: "localStorage is not available in this environment." };
  }

  try {
    storage.removeItem(STORAGE_KEY);
    return { ok: true };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to clear localStorage.";
    return { ok: false, error: message };
  }
}

