/**
 * SpecCraft AI — File Export, Clipboard, and Offline Conversion Helpers
 */

const POSTMAN_V2_1_SCHEMA =
  "https://schema.getpostman.com/json/collection/v2.1.0/collection.json";
const HTTP_METHODS_ORDER = ["get", "post", "put", "patch", "delete", "options", "head"];

/**
 * Trigger a browser download for a text string.
 */
export function downloadTextFile(content, filename, mimeType = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type: mimeType });
  downloadBlobFile(blob, filename);
}

/**
 * Trigger a browser download for a Blob.
 */
export function downloadBlobFile(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

/**
 * Copy text to clipboard with fallback for non-HTTPS contexts.
 */
export async function copyTextToClipboard(text) {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  return false;
}

/**
 * Generate a deterministic sample value from an OpenAPI JSON Schema.
 */
function sampleValueFromSchema(schema, schemas = {}, visited = new Set()) {
  if (!schema || typeof schema !== "object") return "string";

  if (schema.$ref) {
    const ref = String(schema.$ref);
    if (visited.has(ref)) return {};
    const nextVisited = new Set(visited);
    nextVisited.add(ref);
    const refName = ref.split("/").pop();
    const target = schemas[refName];
    return target ? sampleValueFromSchema(target, schemas, nextVisited) : {};
  }

  if (schema.example !== undefined) return schema.example;
  if (schema.default !== undefined) return schema.default;
  if (Array.isArray(schema.enum) && schema.enum.length > 0) return schema.enum[0];

  for (const combiner of ["anyOf", "oneOf"]) {
    const variants = schema[combiner];
    if (Array.isArray(variants) && variants.length > 0) {
      const nonNull = variants.find((v) => v && v.type !== "null");
      if (nonNull) return sampleValueFromSchema(nonNull, schemas, visited);
    }
  }

  if (schema.type === "object" || schema.properties) {
    const result = {};
    const props = schema.properties || {};
    for (const [key, propSchema] of Object.entries(props)) {
      result[key] = sampleValueFromSchema(propSchema, schemas, visited);
    }
    return result;
  }

  if (schema.type === "array") {
    const itemSchema = schema.items || { type: "string" };
    return [sampleValueFromSchema(itemSchema, schemas, visited)];
  }
  if (schema.type === "integer") return 1;
  if (schema.type === "number") return 1.0;
  if (schema.type === "boolean") return true;
  if (schema.type === "string") {
    if (schema.format === "email") return "user@example.com";
    if (schema.format === "date-time") return "2026-01-01T00:00:00Z";
    if (schema.format === "uuid") return "00000000-0000-0000-0000-000000000000";
    return "string";
  }
  return "string";
}

/**
 * Pure client-side OpenAPI 3.0 -> Postman Collection v2.1 converter (offline fallback).
 */
export function convertOpenApiToPostman(spec) {
  const specObj = typeof spec === "string" ? JSON.parse(spec) : spec || {};
  const info = specObj.info || {};
  const schemas = specObj.components?.schemas || {};
  const servers = Array.isArray(specObj.servers) ? specObj.servers : [];
  const baseUrl = (servers[0]?.url || "http://localhost:8000").replace(/\/+$/, "");

  const grouped = new Map();
  const paths = specObj.paths || {};

  for (const rawPath of Object.keys(paths).sort()) {
    const pathItem = paths[rawPath];
    if (!pathItem || typeof pathItem !== "object") continue;

    const pathParams = Array.isArray(pathItem.parameters) ? pathItem.parameters : [];

    for (const method of HTTP_METHODS_ORDER) {
      const operation = pathItem[method];
      if (!operation || typeof operation !== "object") continue;

      const opParams = Array.isArray(operation.parameters) ? operation.parameters : [];
      const mergedMap = new Map();
      for (const p of [...pathParams, ...opParams]) {
        if (p && p.name) {
          mergedMap.set(`${p.name}:${p.in || "query"}`, p);
        }
      }
      const parameters = Array.from(mergedMap.values());

      const segments = rawPath.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
      const postmanSegments = [];
      const pathVars = [];

      for (const seg of segments) {
        const match = seg.match(/^\{([^}]+)\}$/);
        if (match) {
          const varName = match[1];
          postmanSegments.push(`:${varName}`);
          const pDef = parameters.find((p) => p.name === varName && p.in === "path") || {};
          const sample = sampleValueFromSchema(pDef.schema || {}, schemas);
          pathVars.push({
            key: varName,
            value: String(sample ?? "1"),
            description: pDef.description || "",
          });
        } else {
          postmanSegments.push(seg);
        }
      }

      const queryParams = parameters
        .filter((p) => p.in === "query")
        .map((p) => {
          const sample = sampleValueFromSchema(p.schema || {}, schemas);
          return {
            key: p.name,
            value: sample === undefined || sample === null ? "" : String(sample),
            description: p.description || "",
            disabled: !p.required,
          };
        });

      const postmanPath = postmanSegments.length > 0 ? `/${postmanSegments.join("/")}` : "";
      let rawUrl = `{{baseUrl}}${postmanPath}`;
      if (queryParams.length > 0) {
        rawUrl += `?${queryParams.map((q) => `${q.key}=${q.value}`).join("&")}`;
      }

      const urlObj = {
        raw: rawUrl,
        host: ["{{baseUrl}}"],
        path: postmanSegments,
      };
      if (pathVars.length > 0) urlObj.variable = pathVars;
      if (queryParams.length > 0) urlObj.query = queryParams;

      const headers = parameters
        .filter((p) => p.in === "header")
        .map((p) => ({
          key: p.name,
          value: String(p.example || ""),
          description: p.description || "",
        }));

      const jsonMedia = operation.requestBody?.content?.["application/json"];
      if (jsonMedia && !headers.some((h) => h.key.toLowerCase() === "content-type")) {
        headers.push({ key: "Content-Type", value: "application/json" });
      }

      const request = {
        method: method.toUpperCase(),
        header: headers,
        url: urlObj,
        description: operation.description || operation.summary || "",
      };

      if (jsonMedia) {
        const examplePayload =
          jsonMedia.example !== undefined
            ? jsonMedia.example
            : sampleValueFromSchema(jsonMedia.schema || {}, schemas);
        request.body = {
          mode: "raw",
          raw: JSON.stringify(examplePayload ?? {}, null, 2),
          options: { raw: { language: "json" } },
        };
      }

      const folderName =
        Array.isArray(operation.tags) && operation.tags.length > 0
          ? String(operation.tags[0])
          : "General";
      if (!grouped.has(folderName)) grouped.set(folderName, []);
      grouped.get(folderName).push({
        name: operation.summary || operation.operationId || `${method.toUpperCase()} ${rawPath}`,
        request,
        response: [],
      });
    }
  }

  return {
    info: {
      name: info.title || "SpecCraft API",
      description: info.description || "",
      version: info.version || "1.0.0",
      schema: POSTMAN_V2_1_SCHEMA,
    },
    item: Array.from(grouped.entries()).map(([name, item]) => ({ name, item })),
    variable: [{ key: "baseUrl", value: baseUrl, type: "string" }],
  };
}

/**
 * Lightweight client-side YAML serializer fallback for OpenAPI objects.
 */
export function convertObjectToYaml(value, indentLevel = 0) {
  const indent = "  ".repeat(indentLevel);

  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean" || typeof value === "number") return String(value);
  if (typeof value === "string") {
    if (
      value === "" ||
      /[:#\-\n\r{}\[\],&*!|>'"%@`]|^\s|\s$/.test(value) ||
      /^(true|false|null|\d+(\.\d+)?)$/i.test(value)
    ) {
      return JSON.stringify(value);
    }
    return value;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    return value
      .map((item) => {
        if (item !== null && typeof item === "object") {
          const nested = convertObjectToYaml(item, indentLevel + 1);
          const trimmed = nested.replace(new RegExp(`^${indent}  `), "");
          return `${indent}- ${trimmed}`;
        }
        return `${indent}- ${convertObjectToYaml(item, indentLevel + 1)}`;
      })
      .join("\n");
  }

  const entries = Object.entries(value);
  if (entries.length === 0) return "{}";
  return entries
    .map(([key, val]) => {
      const safeKey = /^[a-zA-Z0-9_.\-/]+$/.test(key) ? key : JSON.stringify(key);
      if (val !== null && typeof val === "object") {
        if (Array.isArray(val) && val.length === 0) return `${indent}${safeKey}: []`;
        if (!Array.isArray(val) && Object.keys(val).length === 0) return `${indent}${safeKey}: {}`;
        return `${indent}${safeKey}:\n${convertObjectToYaml(val, indentLevel + 1)}`;
      }
      return `${indent}${safeKey}: ${convertObjectToYaml(val, indentLevel + 1)}`;
    })
    .join("\n");
}

/**
 * Format a Markdown validation audit report from an OpenAPI spec and optional report.
 */
export function formatValidationReportMarkdown(spec, validationReport = null) {
  const specObj = typeof spec === "string" ? JSON.parse(spec) : spec || {};
  const info = specObj.info || {};
  const paths = specObj.paths || {};
  const schemas = specObj.components?.schemas || {};
  const operationCount = Object.values(paths).reduce((acc, item) => {
    if (!item || typeof item !== "object") return acc;
    return acc + HTTP_METHODS_ORDER.filter((m) => item[m]).length;
  }, 0);

  const errors = validationReport?.errors || [];
  const warnings = validationReport?.warnings || [];
  const isValid = validationReport ? Boolean(validationReport.is_valid) : errors.length === 0;

  const lines = [
    "# SpecCraft AI — Validation Audit Report",
    "",
    `- **API Title**: ${info.title || "SpecCraft API"}`,
    `- **Version**: ${info.version || "1.0.0"}`,
    `- **OpenAPI Version**: ${specObj.openapi || "3.0.3"}`,
    `- **Status**: ${isValid ? "VALID" : "INVALID"}`,
    `- **Paths**: ${Object.keys(paths).length}`,
    `- **Operations**: ${operationCount}`,
    `- **Schemas**: ${Object.keys(schemas).length}`,
    "",
    `## Errors (${errors.length})`,
    "",
    ...(errors.length > 0
      ? errors.map((e) => `- **[${e.code || "ERROR"}]** \`${e.path || "root"}\`: ${e.message || ""}`)
      : ["- None"]),
    "",
    `## Warnings (${warnings.length})`,
    "",
    ...(warnings.length > 0
      ? warnings.map((w) => `- **[${w.code || "WARN"}]** \`${w.path || "root"}\`: ${w.message || ""}`)
      : ["- None"]),
    "",
  ];

  return lines.join("\n");
}

