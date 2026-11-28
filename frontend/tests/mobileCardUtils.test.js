import { describe, expect, it } from "vitest";
import sampleCards from "../../mobile/src/sampleCards.json";
import {
  normalizeLanBaseUrl,
  parsePrTarget,
  recordSwipeDecision,
  summarizeDecisions,
} from "../../mobile/src/cardUtils.js";

describe("Expo Go mobile swipe reviewer utilities", () => {
  it("normalizes laptop LAN IPs with :8000 while keeping HTTPS cloud URLs intact", () => {
    expect(normalizeLanBaseUrl("192.168.1.42")).toBe("http://192.168.1.42:8000");
    expect(normalizeLanBaseUrl("192.168.1.42:9000/")).toBe("http://192.168.1.42:9000");
    expect(normalizeLanBaseUrl("http://10.0.0.5:8000")).toBe("http://10.0.0.5:8000");
    expect(normalizeLanBaseUrl("https://speccraftai.onrender.com")).toBe(
      "https://speccraftai.onrender.com"
    );
    expect(normalizeLanBaseUrl("https://speccraftai.onrender.com/")).toBe(
      "https://speccraftai.onrender.com"
    );
    expect(normalizeLanBaseUrl("")).toBe("");
  });

  it("persists Approve and Block swipe decisions and summarizes counts", () => {
    const [cardA, cardB] = sampleCards.cards;
    let state = recordSwipeDecision({}, cardA, "blocked", "2026-11-28T00:00:00Z");
    state = recordSwipeDecision(state, cardB, "approved", "2026-11-28T00:01:00Z");

    const summary = summarizeDecisions(state);
    expect(summary).toEqual({ total: 2, approved: 1, blocked: 1 });
    expect(state[cardA.endpoint].decision).toBe("blocked");
    expect(state[cardB.endpoint].decision).toBe("approved");
  });

  it("ships valid offline sampleCards.json matching /api/ai/summarize-diff cards schema", () => {
    expect(sampleCards.cards.length).toBeGreaterThan(0);
    for (const card of sampleCards.cards) {
      expect(card).toHaveProperty("endpoint");
      expect(card).toHaveProperty("severity");
      expect(card).toHaveProperty("one_line_impact");
      expect(card).toHaveProperty("before");
      expect(card).toHaveProperty("after");
    }
  });

  it("parses GitHub PR targets cleanly for mobile PR comment loop", () => {
    expect(parsePrTarget("poorav007/SpeccraftAI#42")).toEqual({
      owner: "poorav007",
      repo: "SpeccraftAI",
      prNumber: 42,
    });
    expect(parsePrTarget("invalid-string")).toBeNull();
  });
});

