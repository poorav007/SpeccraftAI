import React, { useEffect, useState } from "react";
import { checkBackendHealth } from "../../services/apiClient.js";

/**
 * Top Navigation Bar with active screen selection, backend connection status,
 * and project reset trigger.
 */
export default function Navbar({
  activeScreen = "import",
  onSelectScreen,
  endpointCount = 0,
  hasSpec = false,
  onReset,
}) {
  const [backendStatus, setBackendStatus] = useState({
    checked: false,
    online: false,
  });

  useEffect(() => {
    let mounted = true;
    checkBackendHealth().then((res) => {
      if (mounted) {
        setBackendStatus({ checked: true, online: res.ok });
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const navItems = [
    {
      id: "import",
      label: "1. Codebase Import",
      badge: null,
    },
    {
      id: "analysis",
      label: "2. AST Analysis",
      badge: endpointCount > 0 ? `${endpointCount} routes` : null,
      badgeClass: "bg-primary",
    },
    {
      id: "editor",
      label: "3. Spec Editor & Preview",
      badge: hasSpec ? "Ready" : null,
      badgeClass: "bg-success",
    },
    {
      id: "diff",
      label: "4. Specification Diff",
      badge: null,
    },
    {
      id: "export",
      label: "5. Export Center",
      badge: null,
    },
  ];

  return (
    <header className="navbar navbar-expand-lg navbar-dark bg-dark mb-4 px-3 rounded shadow-sm">
      <div className="container-fluid px-0">
        <a
          className="navbar-brand d-flex align-items-center gap-2 fw-bold"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            onSelectScreen?.("import");
          }}
        >
          <span>⚡ SpecCraft AI</span>
          <span className="badge bg-primary-subtle text-primary border border-primary-subtle small fw-normal">
            AST Engine
          </span>
        </a>

        {/* Nav Tabs */}
        <nav className="nav nav-pills my-2 my-lg-0 gap-1 flex-wrap">
          {navItems.map((item) => {
            const isActive = activeScreen === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-link py-1 px-3 small ${
                  isActive ? "active bg-primary text-white" : "text-light"
                }`}
                onClick={() => onSelectScreen?.(item.id)}
              >
                {item.label}
                {item.badge && (
                  <span
                    className={`badge ms-2 ${
                      item.badgeClass || "bg-secondary"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right side status & reset */}
        <div className="d-flex align-items-center gap-2 mt-2 mt-lg-0">
          {backendStatus.checked && (
            <span
              className={`badge ${
                backendStatus.online
                  ? "bg-success-subtle text-success border border-success-subtle"
                  : "bg-warning-subtle text-warning border border-warning-subtle"
              } small py-1`}
              title={
                backendStatus.online
                  ? "FastAPI AST Bridge is reachable at localhost:8000"
                  : "Backend offline. Running in client fallback mode."
              }
            >
              {backendStatus.online ? "● API Online" : "○ API Offline"}
            </span>
          )}

          {onReset && (
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary py-1 text-light border-secondary"
              onClick={onReset}
              title="Reset state to default seed data"
            >
              Reset Seed
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

