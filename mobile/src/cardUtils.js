/**
 * Pure utilities for the SpecCraft Expo Go Swipe Reviewer:
 * - LAN IP normalization (phones cannot use localhost:8000)
 * - Decision state persistence helpers
 * - Live /api/ai/summarize-diff fetcher with timeout & offline fallback
 */

export const STORAGE_KEYS = {
  LAN_URL: "speccraft_mobile_lan_url",
  DECISIONS: "speccraft_mobile_decisions",
};

/**
 * Normalize user-entered laptop LAN address (e.g. "192.168.1.42" -> "http://192.168.1.42:8000").
 */
export function normalizeLanBaseUrl(rawInput) {
  const trimmed = String(rawInput || "").trim().replace(/\/+$/, "");
  if (!trimmed) return "";

  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
  try {
    const parsed = new URL(withScheme);
    if (!parsed.port) {
      parsed.port = "8000";
    }
    return parsed.origin;
  } catch {
    return "";
  }
}

/**
 * Record an Approve or Block swipe outcome for a single diff card.
 */
export function recordSwipeDecision(decisionsMap, card, decision, timestamp = new Date().toISOString()) {
  const next = { ...(decisionsMap || {}) };
  if (!card || !card.endpoint) return next;
  next[card.endpoint] = {
    endpoint: card.endpoint,
    severity: card.severity || "non_breaking",
    one_line_impact: card.one_line_impact || "",
    decision: decision === "approved" ? "approved" : "blocked",
    decided_at: timestamp,
  };
  return next;
}

/**
 * Compute aggregate counts from persisted swipe decisions.
 */
export function summarizeDecisions(decisionsMap) {
  const entries = Object.values(decisionsMap || {});
  const approved = entries.filter((d) => d.decision === "approved").length;
  const blocked = entries.filter((d) => d.decision === "blocked").length;
  return {
    total: entries.length,
    approved,
    blocked,
  };
}

/**
 * Fetch diff cards directly from the laptop backend `/api/ai/summarize-diff` over LAN.
 */
export async function fetchDiffCardsFromLan(lanInput, diffPayload, timeoutMs = 8000) {
  const baseUrl = normalizeLanBaseUrl(lanInput);
  if (!baseUrl) {
    return { ok: false, error: "Invalid LAN IP or URL (example: 192.168.1.42:8000)." };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${baseUrl}/api/ai/summarize-diff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(diffPayload),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) {
      return { ok: false, error: `Backend returned HTTP ${res.status}` };
    }
    const data = await res.json();
    return { ok: true, data };
  } catch (err) {
    clearTimeout(timer);
    return {
      ok: false,
      error: err?.name === "AbortError" ? "LAN connection timed out." : err?.message || "Unreachable",
    };
  }
}

