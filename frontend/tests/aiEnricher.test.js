import { describe, expect, it } from "vitest";
import {
  buildOfflineDiffSummary,
  buildOfflineEndpointSuggestion,
  buildOfflineFieldExplanation,
  getEndpointKey,
  getProviderBadge,
  isResponseForActiveEndpoint,
} from "../src/utils/aiHelpers.js";

describe("AI Documentation Assistant helpers, race guards, and offline fallbacks", () => {
  it("detects stale endpoint responses when user switches routes mid-flight", () => {
    const orderRoute = { method: "post", path: "/orders" };
    const itemRoute = { method: "get", path: "/items/{item_id}" };

    const requestKey = getEndpointKey(orderRoute);
    expect(requestKey).toBe("post:/orders");
    expect(isResponseForActiveEndpoint(requestKey, orderRoute)).toBe(true);
    expect(isResponseForActiveEndpoint(requestKey, itemRoute)).toBe(false);
    expect(isResponseForActiveEndpoint(requestKey, null)).toBe(false);
  });

  it("maps Gemini, Local, and Offline provider badges cleanly", () => {
    expect(getProviderBadge("gemini").label).toBe("Gemini");
    expect(getProviderBadge("local").label).toBe("Local");
    expect(getProviderBadge("offline").label).toBe("Offline");
    expect(getProviderBadge(undefined).label).toBe("Offline");
  });

  it("builds AST-locked offline endpoint suggestion without altering route facts", () => {
    const proposal = buildOfflineEndpointSuggestion({
      method: "post",
      path: "/orders",
      operation_id: "create_order",
      parameters: [{ name: "dry_run", location: "query" }],
      request_body: { content_type: "application/json" },
    });

    expect(proposal.provider).toBe("offline");
    expect(proposal.ast_facts_locked).toBe(true);
    expect(proposal.summary).toBe("create order");
    expect(proposal.description).toContain("/orders");
    expect(proposal.description).toContain("dry_run");
  });

  it("explains schema fields offline with realistic type-matched examples", () => {
    const emailField = buildOfflineFieldExplanation({
      field_name: "customer_email",
      field_type: "string",
      required: true,
    });
    expect(emailField.provider).toBe("offline");
    expect(emailField.example).toBe("user@example.com");

    const priceField = buildOfflineFieldExplanation({
      field_name: "unit_price",
      field_type: "number",
      required: false,
    });
    expect(priceField.example).toBe(19.99);
  });

  it("caps diff summaries at 50 items, prioritizes breaking changes, and emits mobile cards", () => {
    const changes = Array.from({ length: 55 }, (_, i) => ({
      path: `/items/${i}`,
      method: "get",
      is_breaking: false,
      description: `Optional change ${i}`,
      old_value: null,
      new_value: "v2",
    }));
    changes.push({
      path: "/checkout",
      method: "post",
      is_breaking: true,
      description: "Added required billing_zip parameter",
      old_value: null,
      new_value: { name: "billing_zip", required: true },
    });

    const summary = buildOfflineDiffSummary({ changes });
    expect(summary.truncated).toBe(true);
    expect(summary.risk_level).toBe("medium");
    expect(summary.cards).toHaveLength(50);
    expect(summary.cards[0].endpoint).toBe("POST /checkout");
    expect(summary.cards[0].severity).toBe("breaking");
    expect(summary.cards[0].before).toBe("none");
    expect(summary.cards[0].after).toContain("billing_zip");
  });
});

