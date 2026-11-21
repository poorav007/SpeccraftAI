/**
 * Utility functions for filtering, searching, sorting, and editing AST route endpoints.
 */

/**
 * Compute route count distribution by HTTP method.
 * @param {Array} endpoints
 * @returns {Record<string, number>}
 */
export function computeMethodStats(endpoints = []) {
  const stats = {
    ALL: endpoints.length,
    GET: 0,
    POST: 0,
    PUT: 0,
    DELETE: 0,
    PATCH: 0,
    OTHER: 0,
  };

  for (const ep of endpoints) {
    const method = (ep.method || "").toUpperCase();
    if (method in stats && method !== "ALL") {
      stats[method] += 1;
    } else {
      stats.OTHER += 1;
    }
  }

  return stats;
}

/**
 * Extract sorted list of unique tags across all endpoints.
 * @param {Array} endpoints
 * @returns {string[]}
 */
export function extractAllTags(endpoints = []) {
  const tagsSet = new Set();
  for (const ep of endpoints) {
    if (Array.isArray(ep.tags)) {
      for (const t of ep.tags) {
        if (t && typeof t === "string") {
          tagsSet.add(t.trim());
        }
      }
    }
  }
  return Array.from(tagsSet).sort();
}

/**
 * Filter endpoints by search query, HTTP method, tag, and warnings flag.
 * @param {Array} endpoints
 * @param {Object} filters
 * @param {string} [filters.search]
 * @param {string} [filters.method]
 * @param {string} [filters.tag]
 * @param {boolean} [filters.hasWarningsOnly]
 * @returns {Array}
 */
export function filterEndpoints(endpoints = [], filters = {}) {
  const {
    search = "",
    method = "ALL",
    tag = "ALL",
    hasWarningsOnly = false,
  } = filters;

  const normalizedSearch = search.trim().toLowerCase();
  const normalizedMethod = (method || "ALL").toUpperCase();

  return endpoints.filter((ep) => {
    // 1. Method filter
    if (normalizedMethod !== "ALL") {
      const epMethod = (ep.method || "").toUpperCase();
      if (epMethod !== normalizedMethod) {
        return false;
      }
    }

    // 2. Tag filter
    if (tag && tag !== "ALL") {
      const epTags = Array.isArray(ep.tags) ? ep.tags : [];
      if (!epTags.includes(tag)) {
        return false;
      }
    }

    // 3. Warnings filter
    if (hasWarningsOnly) {
      const warningsCount = (ep.warnings || []).length;
      if (warningsCount === 0) {
        return false;
      }
    }

    // 4. Text Search filter (across path, operation_id, summary, description, tags)
    if (normalizedSearch) {
      const pathMatch = (ep.path || "").toLowerCase().includes(normalizedSearch);
      const opIdMatch = (ep.operation_id || "").toLowerCase().includes(normalizedSearch);
      const summaryMatch = (ep.summary || "").toLowerCase().includes(normalizedSearch);
      const descMatch = (ep.description || "").toLowerCase().includes(normalizedSearch);
      const tagMatch = (ep.tags || []).some((t) =>
        t.toLowerCase().includes(normalizedSearch)
      );

      if (!pathMatch && !opIdMatch && !summaryMatch && !descMatch && !tagMatch) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Immutably update documentation metadata on a specific endpoint.
 * Preserves strict AST facts (path, method, parameters, request_body, responses).
 *
 * @param {Array} endpoints
 * @param {Object} updatedMetadata
 * @returns {Array}
 */
export function updateEndpointMetadata(endpoints = [], updatedMetadata = {}) {
  const targetPath = updatedMetadata.path;
  const targetMethod = (updatedMetadata.method || "").toLowerCase();

  return endpoints.map((ep) => {
    const isTarget =
      ep.path === targetPath &&
      (ep.method || "").toLowerCase() === targetMethod;

    if (!isTarget) {
      return ep;
    }

    return {
      ...ep,
      operation_id:
        updatedMetadata.operation_id !== undefined
          ? updatedMetadata.operation_id.trim()
          : ep.operation_id,
      summary:
        updatedMetadata.summary !== undefined
          ? updatedMetadata.summary.trim()
          : ep.summary,
      description:
        updatedMetadata.description !== undefined
          ? updatedMetadata.description.trim()
          : ep.description,
      tags: Array.isArray(updatedMetadata.tags)
        ? updatedMetadata.tags.map((t) => t.trim()).filter(Boolean)
        : ep.tags,
      is_customized: true,
    };
  });
}

/**
 * Return authentic Bootstrap badge styling for standard HTTP methods.
 * @param {string} method
 * @returns {string} CSS class name
 */
export function getMethodBadgeClass(method = "") {
  const m = (method || "").toUpperCase();
  switch (m) {
    case "GET":
      return "badge-method-get";
    case "POST":
      return "badge-method-post";
    case "PUT":
      return "badge-method-put";
    case "DELETE":
      return "badge-method-delete";
    case "PATCH":
      return "badge-method-patch";
    default:
      return "badge-method-other";
  }
}

