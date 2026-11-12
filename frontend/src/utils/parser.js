const METHOD_REGEX =
  /(?:\w+\.)?(get|post|put|patch|delete|options|head)\s*\(\s*['"]([^'"]+)['"]/gi;

const FLASK_ROUTE_REGEX =
  /@\w+\.route\(\s*['"]([^'"]+)['"](?:[^)]*methods\s*=\s*\[([^\]]+)\])?/gi;

const EXPRESS_PARAM_REGEX = /:([A-Za-z_][A-Za-z0-9_]*)/g;
const PATH_PARAM_REGEX = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g;

function nowMs() {
  return typeof globalThis.performance?.now === "function"
    ? globalThis.performance.now()
    : Date.now();
}

/** Convert Express `:id` segments into OpenAPI `{id}` path parameters. */
function toOpenApiPath(rawPath) {
  const withBraces = rawPath.replace(EXPRESS_PARAM_REGEX, "{$1}");
  return withBraces.startsWith("/") ? withBraces : `/${withBraces}`;
}

/** Build a minimal OpenAPI 3.0.3 object from parsed stub endpoints. */
export function buildOpenApiFromEndpoints(endpoints) {
  const paths = {};

  for (const ep of endpoints) {
    const openApiPath = toOpenApiPath(ep.path);
    const lowerMethod = ep.method.toLowerCase();
    if (!paths[openApiPath]) {
      paths[openApiPath] = {};
    }

    const parameters = [];
    let paramMatch;
    PATH_PARAM_REGEX.lastIndex = 0;
    while ((paramMatch = PATH_PARAM_REGEX.exec(openApiPath)) !== null) {
      parameters.push({
        name: paramMatch[1],
        in: "path",
        required: true,
        schema: { type: "string" },
      });
    }

    const operation = {
      summary: `${ep.method} ${openApiPath}`,
      responses: {
        200: { description: "Successful Response" },
      },
    };
    if (parameters.length > 0) {
      operation.parameters = parameters;
    }

    paths[openApiPath][lowerMethod] = operation;
  }

  return {
    openapi: "3.0.3",
    info: {
      title: "SpecCraft Parsed API",
      version: "0.1.0",
    },
    paths,
  };
}

/**
 * Regex parser stub for Express and Python decorator routes.
 * Intended for Screen 1 client-side feedback before full Python AST parsing.
 */
export function parseRouteCode(code) {
  const start = nowMs();
  if (typeof code !== "string" || !code.trim()) {
    return {
      endpoints: [],
      openApiSpec: null,
      parseTimeMs: Number((nowMs() - start).toFixed(2)),
      error: "Please paste route code or upload a .js or .py file.",
    };
  }

  const endpoints = [];
  const seen = new Set();

  const addEndpoint = (method, path) => {
    const upperMethod = method.toUpperCase();
    const key = `${upperMethod} ${path}`;
    if (!seen.has(key)) {
      seen.add(key);
      endpoints.push({ method: upperMethod, path });
    }
  };

  let match;
  METHOD_REGEX.lastIndex = 0;
  while ((match = METHOD_REGEX.exec(code)) !== null) {
    addEndpoint(match[1], match[2]);
  }

  FLASK_ROUTE_REGEX.lastIndex = 0;
  while ((match = FLASK_ROUTE_REGEX.exec(code)) !== null) {
    const routePath = match[1];
    const methodsRaw = match[2];
    const methods = methodsRaw
      ? methodsRaw
          .replace(/['"\s]/g, "")
          .split(",")
          .filter(Boolean)
      : ["GET"];
    for (const method of methods) {
      addEndpoint(method, routePath);
    }
  }

  const parseTimeMs = Number((nowMs() - start).toFixed(2));
  if (endpoints.length === 0) {
    return {
      endpoints: [],
      openApiSpec: null,
      parseTimeMs,
      error: "No supported route definitions found. Try e.g. app.get('/api/users', ...).",
    };
  }

  return {
    endpoints,
    openApiSpec: buildOpenApiFromEndpoints(endpoints),
    parseTimeMs,
    error: null,
  };
}

