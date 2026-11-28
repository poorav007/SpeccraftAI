import React from "react";

/**
 * Accessible Screen 1 shimmer skeleton displayed while the Render free-tier
 * backend wakes from cold start (up to ~50s). Intentionally offers no manual
 * skip during warm-up; falls back to Local Mode automatically if the 50s
 * retry budget expires, and unlocks the connected Screen 1 immediately on 200 OK.
 */
export default function BackendWakeSkeleton({ elapsedSeconds = 0, maxWaitSeconds = 50 }) {
  const clampedElapsed = Math.min(Math.max(0, elapsedSeconds), maxWaitSeconds);
  const progressPct = Math.min(100, Math.round((clampedElapsed / maxWaitSeconds) * 100));

  return (
    <div
      className="card shadow-sm border-0"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="card-header bg-body-tertiary d-flex flex-wrap justify-content-between align-items-center gap-2 py-3">
        <div className="d-flex align-items-center gap-2">
          <span
            className="spinner-border spinner-border-sm text-primary"
            aria-hidden="true"
          />
          <div>
            <h2 className="h5 mb-0 fw-bold">Waking up SpecCraft Cloud API...</h2>
            <small className="text-muted">
              Connecting to <code>speccraftai.onrender.com</code> &mdash; free-tier cold starts typically take 25&ndash;45s.
            </small>
          </div>
        </div>
        <span className="badge bg-info-subtle text-info-emphasis border border-info-subtle font-monospace py-1 px-2">
          {clampedElapsed}s / {maxWaitSeconds}s
        </span>
      </div>

      <div className="card-body p-4">
        <div
          className="progress mb-4"
          style={{ height: "6px" }}
          aria-label="Backend startup retry window"
          aria-valuenow={progressPct}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="progress-bar progress-bar-striped progress-bar-animated bg-primary"
            style={{ width: `${Math.max(8, progressPct)}%` }}
          />
        </div>

        {/* Mode selector pills skeleton */}
        <div className="d-flex flex-wrap gap-2 mb-4" aria-hidden="true">
          <div className="skeleton-block skeleton-pill" style={{ width: "175px", height: "36px" }} />
          <div className="skeleton-block skeleton-pill" style={{ width: "210px", height: "36px" }} />
          <div className="skeleton-block skeleton-pill" style={{ width: "155px", height: "36px" }} />
        </div>

        {/* Primary ingestion form skeleton */}
        <div className="mb-3" aria-hidden="true">
          <div className="skeleton-block mb-2" style={{ width: "36%", height: "16px" }} />
          <div className="skeleton-block mb-3" style={{ width: "100%", height: "44px" }} />
          <div className="skeleton-block mb-3" style={{ width: "58%", height: "14px" }} />
          <div className="skeleton-block" style={{ width: "100%", height: "148px" }} />
        </div>

        <div className="d-flex justify-content-between align-items-center mt-4" aria-hidden="true">
          <div className="skeleton-block" style={{ width: "220px", height: "14px" }} />
          <div className="skeleton-block skeleton-pill" style={{ width: "180px", height: "40px" }} />
        </div>
      </div>
    </div>
  );
}

