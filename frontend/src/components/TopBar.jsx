import React from "react";
import { Link, useLocation } from "react-router-dom";
import "./TopBar.css";

const Icon = {
  BrandShield: () => (
    <svg viewBox="0 0 48 58" aria-hidden="true">
      <path
        d="M24 2 44 9v18c0 13.2-8.4 23.3-20 28C12.4 50.3 4 40.2 4 27V9L24 2Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
      />
      <path
        d="M24 11v27M15 19h18M17 31h14"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  ),
  Help: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.3 9.3a2.7 2.7 0 1 1 3.9 2.4c-.9.5-1.2 1-1.2 2" />
      <circle cx="12" cy="16.6" r=".4" fill="currentColor" />
    </svg>
  ),
  Chevron: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 9l6 6 6-6" />
    </svg>
  ),
};

export default function TopBar({ activePage }) {
  const location = useLocation();

  // Determine current active page from prop or pathname
  const currentActive =
    activePage === "generate" ||
    activePage === "result" ||
    activePage === "validate" ||
    activePage === "verify-review" ||
    ["/generate", "/result", "/validate", "/verify-review"].includes(location.pathname)
      ? "generate"
      : activePage === "home" || location.pathname === "/dashboard"
      ? "home"
      : activePage === "history" || location.hash === "#history"
      ? "history"
      : activePage || "";

  return (
    <header className="dash-nav srigen-master-topbar">
      <div className="dash-nav-inner">
        {/* Canonical SriGEN Brand Identity */}
        <Link to="/dashboard" className="dash-brand" aria-label="SriGEN Home">
          <span className="dash-brand-mark">
            <Icon.BrandShield />
          </span>
          <span className="dash-brand-text">SriGEN</span>
        </Link>

        {/* Canonical Navigation Links: Home, Generate, History */}
        <nav className="dash-links" aria-label="Primary Navigation">
          <Link
            to="/dashboard"
            className={`dash-link ${currentActive === "home" ? "dash-link-active" : ""}`}
          >
            Home
          </Link>
          <Link
            to="/generate"
            className={`dash-link ${currentActive === "generate" ? "dash-link-active" : ""}`}
          >
            Generate
          </Link>
          <a
            href="/dashboard#history"
            className={`dash-link ${currentActive === "history" ? "dash-link-active" : ""}`}
          >
            History
          </a>
        </nav>

        {/* Right Status & Controls */}
        <div className="dash-nav-right">
          <span className="dash-secure">
            <i className="dash-dot" aria-hidden="true"></i>SECURE
          </span>
          <button className="dash-ghost-btn" type="button" aria-label="Help & Documentation">
            <Icon.Help />
            <span>Help</span>
          </button>
          <div className="dash-operator" role="button" tabIndex={0} aria-label="Operator Profile">
            <span className="dash-avatar">AS</span>
            <span className="dash-op-name">Operator</span>
            <Icon.Chevron />
          </div>
        </div>
      </div>
    </header>
  );
}
