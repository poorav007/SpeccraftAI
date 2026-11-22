/**
 * SpecCraft AI — Specification Diff Helper Utilities
 *
 * Provides change filtering, aggregate statistics calculation,
 * badge formatting, and client-side fallback spec comparison.
 */

/**
 * Filters a list of diff change records based on filter tab and search query.
 *
 * @param {Array<object>} changes - List of DiffChangeRecord objects.
 * @param {object} options
 * @param {string} [options.filterType="all"] - 'all' | 'breaking' | 'non_breaking' | 'added' | 'removed' | 'modified'
 * @param {string} [options.search=""] - Text search string matched against path, method, description, location.
 * @returns {Array<object>} Filtered list of change records.
 */
export function filterChanges(changes = [], { filterType = "all", search = "" } = {}) {
  if (!Array.isArray(changes)) return [];

  const query = (search || "").trim().toLowerCase();

  return changes.filter((change) => {
    // 1. Filter type check
    if (filterType === "breaking" && !change.is_breaking) return false;
    if (filterType === "non_breaking" && change.is_breaking) return false;
    if (filterType === "added" && change.change_type !== "added") return false;
    if (filterType === "removed" && change.change_type !== "removed") return false;
    if (filterType === "modified" && change.change_type !== "modified") return false;

    // 2. Search query check
    if (query) {
      const path = (change.path || "").toLowerCase();
      const method = (change.method || "").toLowerCase();
      const desc = (change.description || "").toLowerCase();
      const loc = (change.location || "").toLowerCase();
      const category = (change.category || "").toLowerCase();

      const matches =
        path.includes(query) ||
        method.includes(query) ||
        desc.includes(query) ||
        loc.includes(query) ||
        category.includes(query);

      if (!matches) return false;
    }

    return true;
  });
}

/**
 * Computes aggregate diff summary statistics.
 *
 * @param {Array<object>} changes - List of DiffChangeRecord objects.
 * @returns {{ total: number, breaking: number, nonBreaking: number, added: number, removed: number, modified: number }}
 */
export function computeDiffStats(changes = []) {
  if (!Array.isArray(changes)) {
    return { total: 0, breaking: 0, nonBreaking: 0, added: 0, removed: 0, modified: 0 };
  }

  return {
    total: changes.length,
    breaking: changes.filter((c) => c.is_breaking).length,
    nonBreaking: changes.filter((c) => !c.is_breaking).length,
    added: changes.filter((c) => c.change_type === "added").length,
    removed: changes.filter((c) => c.change_type === "removed").length,
    modified: changes.filter((c) => c.change_type === "modified").length,
  };
}

/**
 * Returns badge label, class, and icon for a given change type.
 *
 * @param {string} changeType - 'added' | 'removed' | 'modified'
 * @returns {{ label: string, bgClass: string, icon: string }}
 */
export function getChangeBadge(changeType) {
  switch (changeType) {
    case "added":
      return {
        label: "+ ADDED",
        bgClass: "bg-success text-white",
        icon: "+",
      };
    case "removed":
      return {
        label: "- REMOVED",
        bgClass: "bg-danger text-white",
        icon: "-",
      };
    case "modified":
      return {
        label: "~ MODIFIED",
        bgClass: "bg-warning text-dark",
        icon: "~",
      };
    default:
      return {
        label: changeType?.toUpperCase() || "CHANGE",
        bgClass: "bg-secondary text-white",
        icon: "•",
      };
  }
}

/**
 * Returns dual-channel breaking change badge descriptor.
 * Follows modern-web-guidance accessibility: never relies on color alone.
 *
 * @param {boolean} isBreaking
 * @returns {{ label: string, bgClass: string, ariaLabel: string }}
 */
export function getBreakingBadge(isBreaking) {
  if (isBreaking) {
    return {
      label: "🚨 BREAKING",
      bgClass: "bg-danger text-white border border-danger",
      ariaLabel: "Breaking change: potentially breaks API consumers",
    };
  }
  return {
    label: "✓ NON-BREAKING",
    bgClass: "bg-success-subtle text-success border border-success-subtle",
    ariaLabel: "Non-breaking change: backwards compatible update",
  };
}

/**
 * Returns Bootstrap badge background class for HTTP methods.
 *
 * @param {string} method
 * @returns {string}
 */
export function getMethodBadgeClass(method) {
  const m = (method || "").toUpperCase();
  switch (m) {
    case "GET":
      return "bg-primary text-white";
    case "POST":
      return "bg-success text-white";
    case "PUT":
      return "bg-warning text-dark";
    case "DELETE":
      return "bg-danger text-white";
    case "PATCH":
      return "bg-info text-dark";
    default:
      return "bg-secondary text-white";
  }
}

/**
 * Client-side fallback spec comparison engine.
 * Used when backend FastAPI bridge is temporarily unreachable.
 *
 * @param {object|string} baseline - S1 spec
 * @param {object|string} target - S2 spec
 * @returns {object} DiffReport
 */
export function compareSpecsClientSide(baseline, target) {
  const b = typeof baseline === "string" ? JSON.parse(baseline) : baseline || {};
  const t = typeof target === "string" ? JSON.parse(target) : target || {};

  const bPaths = b.paths || {};
  const tPaths = t.paths || {};

  const changes = [];
  const httpMethods = ["get", "post", "put", "delete", "patch", "options", "head"];

  const allPathKeys = Array.from(new Set([...Object.keys(bPaths), ...Object.keys(tPaths)]));

  for (const path of allPathKeys) {
    const bOps = bPaths[path] || {};
    const tOps = tPaths[path] || {};

    for (const method of httpMethods) {
      const bOp = bOps[method];
      const tOp = tOps[method];

      if (bOp && !tOp) {
        // Removed operation (BREAKING)
        changes.push({
          change_type: "removed",
          category: "operation",
          path,
          method: method.toUpperCase(),
          location: `paths.${path}.${method}`,
          description: `Endpoint ${method.toUpperCase()} ${path} was removed.`,
          is_breaking: true,
          old_value: { summary: bOp.summary || "", operationId: bOp.operationId || "" },
          new_value: null,
        });
      } else if (!bOp && tOp) {
        // Added operation (NON-BREAKING)
        changes.push({
          change_type: "added",
          category: "operation",
          path,
          method: method.toUpperCase(),
          location: `paths.${path}.${method}`,
          description: `Endpoint ${method.toUpperCase()} ${path} was added.`,
          is_breaking: false,
          old_value: null,
          new_value: { summary: tOp.summary || "", operationId: tOp.operationId || "" },
        });
      } else if (bOp && tOp) {
        // Deep compare operation details
        // 1. Parameters
        const bParams = bOp.parameters || [];
        const tParams = tOp.parameters || [];

        const bParamMap = new Map(bParams.map((p) => [`${p.name}:${p.in}`, p]));
        const tParamMap = new Map(tParams.map((p) => [`${p.name}:${p.in}`, p]));

        // Check added params
        for (const [key, tP] of tParamMap.entries()) {
          if (!bParamMap.has(key)) {
            const isReq = Boolean(tP.required);
            changes.push({
              change_type: "added",
              category: "parameter",
              path,
              method: method.toUpperCase(),
              location: `paths.${path}.${method}.parameters[${tP.name}]`,
              description: `Parameter '${tP.name}' in ${tP.in} added (${isReq ? "REQUIRED" : "optional"}).`,
              is_breaking: isReq,
              old_value: null,
              new_value: tP,
            });
          } else {
            const bP = bParamMap.get(key);
            // Check changed to required
            if (!bP.required && tP.required) {
              changes.push({
                change_type: "modified",
                category: "parameter",
                path,
                method: method.toUpperCase(),
                location: `paths.${path}.${method}.parameters[${tP.name}].required`,
                description: `Parameter '${tP.name}' changed from optional to required.`,
                is_breaking: true,
                old_value: false,
                new_value: true,
              });
            }
            // Check type alteration
            const bType = bP.schema?.type;
            const tType = tP.schema?.type;
            if (bType && tType && bType !== tType) {
              changes.push({
                change_type: "modified",
                category: "parameter",
                path,
                method: method.toUpperCase(),
                location: `paths.${path}.${method}.parameters[${tP.name}].schema.type`,
                description: `Parameter '${tP.name}' schema type altered from '${bType}' to '${tType}'.`,
                is_breaking: true,
                old_value: bType,
                new_value: tType,
              });
            }
          }
        }

        // Check removed params
        for (const [key, bP] of bParamMap.entries()) {
          if (!tParamMap.has(key)) {
            changes.push({
              change_type: "removed",
              category: "parameter",
              path,
              method: method.toUpperCase(),
              location: `paths.${path}.${method}.parameters[${bP.name}]`,
              description: `Parameter '${bP.name}' in ${bP.in} removed.`,
              is_breaking: false,
              old_value: bP,
              new_value: null,
            });
          }
        }

        // 2. Responses: check removed success response
        const bResps = bOp.responses || {};
        const tResps = tOp.responses || {};
        for (const code of Object.keys(bResps)) {
          if (!tResps[code] && (code.startsWith("2") || code === "default")) {
            changes.push({
              change_type: "removed",
              category: "response",
              path,
              method: method.toUpperCase(),
              location: `paths.${path}.${method}.responses.${code}`,
              description: `Documented response status '${code}' was removed.`,
              is_breaking: true,
              old_value: bResps[code],
              new_value: null,
            });
          }
        }
      }
    }
  }

  const stats = computeDiffStats(changes);
  return {
    baseline_version: b.info?.version || "1.0.0",
    target_version: t.info?.version || "2.0.0",
    summary: {
      total_changes: stats.total,
      breaking_changes: stats.breaking,
      non_breaking_changes: stats.nonBreaking,
      added_endpoints: changes.filter((c) => c.category === "operation" && c.change_type === "added").length,
      removed_endpoints: changes.filter((c) => c.category === "operation" && c.change_type === "removed").length,
      modified_endpoints: changes.filter((c) => c.category === "operation" && c.change_type === "modified").length,
      parameter_changes: changes.filter((c) => c.category === "parameter").length,
      schema_changes: changes.filter((c) => c.category === "schema" || c.category === "request_body").length,
      response_changes: changes.filter((c) => c.category === "response").length,
    },
    changes,
  };
}

