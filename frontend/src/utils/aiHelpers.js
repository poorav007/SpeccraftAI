/**
 * SpecCraft AI — Frontend AI Helpers, Provider Badges & Offline Fallbacks
 */

export function getEndpointKey(endpoint) {
  if (!endpoint) return "";
  return `${String(endpoint.method || "").toLowerCase()}:${String(endpoint.path || "")}`;
}

export function isResponseForActiveEndpoint(requestKey, activeEndpoint) {
  if (!requestKey || !activeEndpoint) return false;
  return requestKey === getEndpointKey(activeEndpoint);
}

export function getProviderBadge(provider) {
  const normalized = String(provider || "offline").toLowerCase();
  if (normalized === "gemini") {
    return {
      label: "Gemini",
      badgeClass: "bg-primary-subtle text-primary border border-primary-subtle",
    };
  }
  if (normalized === "local") {
    return {
      label: "Local",
      badgeClass: "bg-info-subtle text-info-emphasis border border-info-subtle",
    };
  }
  return {
    label: "Offline",
    badgeClass: "bg-secondary-subtle text-secondary border border-secondary-subtle",
  };
}

function humanize(name = "") {
  return (
    String(name)
      .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
      .replace(/[_-]+/g, " ")
      .trim() || "resource"
  );
}

/**
 * Deterministic client-side fallback when backend AI bridge is offline.
 */
export function buildOfflineEndpointSuggestion(endpoint) {
  const method = String(endpoint?.method || "get").toUpperCase();
  const path = String(endpoint?.path || "/");
  const segments = path
    .replace(/^\/+|\/+$/g, "")
    .split("/")
    .filter((s) => s && !s.startsWith("{"));
  const resource = humanize(segments[segments.length - 1] || "root");

  const verbMap = {
    GET: path.includes("{") ? "Retrieve" : "List",
    POST: "Create",
    PUT: "Replace",
    PATCH: "Update",
    DELETE: "Delete",
  };
  const verb = verbMap[method] || "Handle";

  const summary = (
    endpoint?.summary?.trim() ||
    (endpoint?.operation_id ? humanize(endpoint.operation_id) : `${verb} ${resource}`)
  ).slice(0, 60);

  const paramNames = (endpoint?.parameters || []).map((p) => p.name).filter(Boolean);
  const paramText = paramNames.length > 0 ? ` Accepts parameters: ${paramNames.join(", ")}.` : "";
  const bodyText = endpoint?.request_body ? " Expects a validated JSON request payload." : "";

  return {
    summary,
    description: endpoint?.description?.trim() || `${verb} \`${path}\` via \`${method}\`.${paramText}${bodyText}`,
    suggested_tags:
      Array.isArray(endpoint?.tags) && endpoint.tags.length > 0
        ? endpoint.tags
        : [segments[0] || "general"],
    provider: "offline",
    ast_facts_locked: true,
  };
}

/**
 * Deterministic client-side field explanation fallback.
 */
export function buildOfflineFieldExplanation(fieldPayload) {
  const name = String(fieldPayload?.field_name || "field");
  const type = String(fieldPayload?.field_type || "string").toLowerCase();
  const location = String(fieldPayload?.location || "body");
  const reqText = fieldPayload?.required ? "Required" : "Optional";

  let example = `sample_${name}`;
  if (type.includes("int")) example = 1;
  else if (type.includes("float") || type.includes("number")) example = 19.99;
  else if (type.includes("bool")) example = true;
  else if (type.includes("array") || type.includes("list")) example = ["example_item"];
  else if (name.toLowerCase().includes("email")) example = "user@example.com";

  return {
    field_name: name,
    explanation:
      fieldPayload?.existing_description?.trim() ||
      `${reqText} ${location} field representing ${humanize(name)} (${type}).`,
    example,
    provider: "offline",
  };
}

function previewText(val) {
  if (val === null || val === undefined || val === "") return "none";
  const text = typeof val === "object" ? JSON.stringify(val) : String(val);
  return text.length <= 140 ? text : `${text.slice(0, 137)}...`;
}

/**
 * Deterministic client-side diff summary + mobile cards fallback.
 */
export function buildOfflineDiffSummary(diffReport) {
  const changes = Array.isArray(diffReport?.changes) ? diffReport.changes : [];
  const prioritized = [...changes].sort(
    (a, b) => (a.is_breaking ? 0 : 1) - (b.is_breaking ? 0 : 1)
  );
  const capped = prioritized.slice(0, 50);
  const truncated = prioritized.length > 50;

  const breakingCount = changes.filter((c) => c.is_breaking).length;
  const nonBreakingCount = Math.max(0, changes.length - breakingCount);
  const risk_level = breakingCount >= 3 ? "high" : breakingCount > 0 ? "medium" : "low";

  const executive_summary =
    breakingCount > 0
      ? `Detected ${changes.length} API changes including ${breakingCount} breaking change(s) and ${nonBreakingCount} non-breaking update(s).`
      : changes.length > 0
      ? `Detected ${changes.length} non-breaking API change(s). Backward compatibility is preserved.`
      : "No specification differences detected.";

  const migration_steps =
    breakingCount > 0
      ? capped
          .filter((c) => c.is_breaking)
          .slice(0, 5)
          .map((c) => `Review ${String(c.method || "").toUpperCase()} ${c.path || "/"}: ${c.description || ""}`)
      : [];

  const cards = capped.map((c) => ({
    endpoint: `${String(c.method || "").toUpperCase()} ${c.path || "/"}`.trim(),
    severity: c.is_breaking ? "breaking" : "non_breaking",
    one_line_impact: String(c.description || "API specification updated"),
    before: previewText(c.old_value ?? c.details?.old ?? c.details?.old_type),
    after: previewText(c.new_value ?? c.details?.new ?? c.details?.new_type),
  }));

  return {
    executive_summary,
    risk_level,
    migration_steps,
    cards,
    truncated,
    provider: "offline",
  };
}

