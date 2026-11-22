/**
 * SpecCraft AI — Preset OpenAPI Specifications for Screen 4 Diff Demos
 */

export const SAMPLE_SHOP_V1 = {
  openapi: "3.0.3",
  info: {
    title: "FastAPI Shop API",
    version: "1.0.0",
    description: "Baseline e-commerce specification version 1.0.0",
  },
  paths: {
    "/health": {
      get: {
        summary: "Service Health Check",
        operationId: "health_check",
        responses: {
          "200": { description: "Service healthy" },
        },
      },
    },
    "/items": {
      get: {
        summary: "List catalog items",
        operationId: "list_items",
        parameters: [
          { name: "skip", in: "query", required: false, schema: { type: "integer" } },
          { name: "limit", in: "query", required: false, schema: { type: "integer" } },
        ],
        responses: {
          "200": { description: "List of items" },
        },
      },
      post: {
        summary: "Create new catalog item",
        operationId: "create_item",
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: {
                type: "object",
                properties: { name: { type: "string" }, price: { type: "number" } },
              },
            },
          },
        },
        responses: {
          "201": { description: "Item created" },
        },
      },
    },
    "/items/{item_id}": {
      get: {
        summary: "Get item by ID",
        operationId: "get_item",
        parameters: [
          { name: "item_id", in: "path", required: true, schema: { type: "integer" } },
        ],
        responses: {
          "200": { description: "Item details" },
        },
      },
      delete: {
        summary: "Delete item",
        operationId: "delete_item",
        parameters: [
          { name: "item_id", in: "path", required: true, schema: { type: "integer" } },
        ],
        responses: {
          "204": { description: "Item deleted successfully" },
        },
      },
    },
  },
};

export const SAMPLE_SHOP_V2 = {
  openapi: "3.0.3",
  info: {
    title: "FastAPI Shop API",
    version: "2.0.0",
    description: "Target e-commerce specification version 2.0.0 with breaking changes",
  },
  paths: {
    "/health": {
      get: {
        summary: "Service Health Check",
        operationId: "health_check",
        responses: {
          "204": { description: "Service healthy (no body)" },
        },
      },
    },
    "/items": {
      get: {
        summary: "List catalog items",
        operationId: "list_items",
        parameters: [
          { name: "skip", in: "query", required: false, schema: { type: "integer" } },
          { name: "limit", in: "query", required: false, schema: { type: "integer" } },
          { name: "sort_by", in: "query", required: false, schema: { type: "string" } }, // NON-BREAKING: added optional param
        ],
        responses: {
          "200": { description: "List of items" },
        },
      },
      post: {
        summary: "Create new catalog item",
        operationId: "create_item",
        parameters: [
          { name: "X-Shop-Tenant", in: "header", required: true, schema: { type: "string" } }, // BREAKING: added required header
        ],
        requestBody: {
          required: true,
          content: {
            "application/json": {
              schema: {
                type: "object",
                properties: { name: { type: "string" }, price: { type: "number" } },
              },
            },
          },
        },
        responses: {
          "201": { description: "Item created" },
        },
      },
    },
    "/items/{item_id}": {
      get: {
        summary: "Get item by ID",
        operationId: "get_item",
        parameters: [
          { name: "item_id", in: "path", required: true, schema: { type: "string" } }, // BREAKING: int -> string alteration
        ],
        responses: {
          "200": { description: "Item details" },
        },
      },
      // BREAKING: delete /items/{item_id} was REMOVED!
    },
    "/items/batch": {
      post: {
        summary: "Batch create items", // NON-BREAKING: new endpoint added
        operationId: "batch_create_items",
        responses: {
          "201": { description: "Batch created" },
        },
      },
    },
  },
};

