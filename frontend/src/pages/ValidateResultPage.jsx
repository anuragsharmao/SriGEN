import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import TopBar from "../components/TopBar.jsx";
import { workflowStore } from "../services/workflowStore.js";
import { api } from "../services/api.js";
import "./ValidateResultPage.css";

/* ---------------------------------- Icons --------------------------------- */

const Icon = {
  Doc: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.5 3.5h8L19 8v12a1 1 0 0 1-1 1h-11.5a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
      <path d="M14 3.5V8h5" />
      <path d="M8.5 12.5h7M8.5 15.5h7M8.5 18h4" />
    </svg>
  ),
  Shield: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.5 20 6v6c0 5.2-3.4 9.1-8 10.5C7.4 21.1 4 17.2 4 12V6l8-3.5Z" />
    </svg>
  ),
  ShieldLock: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.5 20 6v6c0 5.2-3.4 9.1-8 10.5C7.4 21.1 4 17.2 4 12V6l8-3.5Z" />
      <rect x="9.3" y="11" width="5.4" height="4.4" rx="1" />
      <path d="M10.2 11V9.6a1.8 1.8 0 0 1 3.6 0V11" />
    </svg>
  ),
  ShieldCheck: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.5 20 6v6c0 5.2-3.4 9.1-8 10.5C7.4 21.1 4 17.2 4 12V6l8-3.5Z" />
      <path d="M8.5 12.3 11 14.7 15.5 9.5" />
    </svg>
  ),
  Network: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="5" r="2" />
      <circle cx="5" cy="18" r="2" />
      <circle cx="19" cy="18" r="2" />
      <circle cx="12" cy="12" r="1.8" />
      <path d="M12 7v3.2M10.6 13.2 6.5 16.5M13.4 13.2l4.1 3.3" />
    </svg>
  ),
  Spark: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
    </svg>
  ),
  Link: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9.5 14.5 14.5 9.5" />
      <path d="M11 7.2 12.6 5.6a3.4 3.4 0 0 1 4.8 4.8L15.8 12" />
      <path d="M13 16.8 11.4 18.4a3.4 3.4 0 0 1-4.8-4.8L8.2 12" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  CheckCircle: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.5 2.5 5-5" />
    </svg>
  ),
  AlertTriangle: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  AlertCircle: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  ArrowRight: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  ),
  Chevron: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 18l6-6-6-6" />
    </svg>
  ),
  ChevronDown: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 9l6 6 6-6" />
    </svg>
  ),
  Search: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  Maximize: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
    </svg>
  ),
  Copy: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  ),
  Sliders: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <line x1="4" y1="21" x2="4" y2="14" />
      <line x1="4" y1="10" x2="4" y2="3" />
      <line x1="12" y1="21" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12" y2="3" />
      <line x1="20" y1="21" x2="20" y2="16" />
      <line x1="20" y1="12" x2="20" y2="3" />
      <line x1="1" y1="14" x2="7" y2="14" />
      <line x1="9" y1="8" x2="15" y2="8" />
      <line x1="17" y1="16" x2="23" y2="16" />
    </svg>
  ),
  Close: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  Share: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <path d="m8.59 13.51 6.83 3.98M15.41 6.51l-6.82 3.98" />
    </svg>
  ),
};

/* ----------------------------- Initial Data ----------------------------- */

const INITIAL_DELIVERABLES = [
  {
    id: "deliv_01",
    index: "01",
    type: "executive_summary",
    title: "EXECUTIVE SUMMARY",
    status: "VERIFIED",
    trustScore: 91,
    icon: Icon.Doc,
  },
  {
    id: "deliv_02",
    index: "02",
    type: "linkedin_post",
    title: "LINKEDIN POST",
    status: "ATTENTION",
    trustScore: 88,
    icon: Icon.Share,
  },
  {
    id: "deliv_03",
    index: "03",
    type: "advisory",
    title: "ADVISORY",
    status: "VERIFIED",
    trustScore: 96,
    icon: Icon.Doc,
  },
];

const CLAIMS_DATA = {
  E01: {
    id: "E01",
    tag: "E01",
    status: "VERIFIED",
    quote: "The incident affected 24 systems across the affected region, with initial indications of coordinated activity targeting critical infrastructure.",
    evidence: "Telemetry log audit confirmed 24 server endpoints in the regional cluster were impacted during the initial surge on 14 Sep 2026.",
    matchType: "Entity + Number",
    grounding: "Grounding confirmed",
  },
  E03: {
    id: "E03",
    tag: "E03",
    status: "ATTENTION",
    quote: "Initial access was likely gained via a compromised credential.",
    evidence: "The investigation identified the use of stolen credentials to gain initial access to the target environment.",
    matchType: "Literal + Entity + Number",
    grounding: "Grounding confirmed",
  },
  E06: {
    id: "E06",
    tag: "E06",
    status: "VERIFIED",
    quote: "No evidence of data exfiltration at this time.",
    evidence: "DLP monitoring and perimeter egress inspection logs revealed no abnormal outbound data transfers during the incident window.",
    matchType: "Literal + Semantic",
    grounding: "Grounding confirmed",
  },
};

const INITIAL_DISCLOSURES = [
  {
    id: "disc_1",
    text: "Potential PII detected in source (e.g., email addresses).",
    action: "Disclose",
    resolved: true,
  },
  {
    id: "disc_2",
    text: "Sensitive infrastructure details in advisory draft.",
    action: "Edit",
    resolved: true,
    customText: "Redacted operational endpoints per CISO directive",
  },
  {
    id: "disc_3",
    text: "Tool names may reveal capabilities.",
    action: "Withhold",
    resolved: false,
  },
];

export default function ValidateResultPage() {
  const navigate = useNavigate();

  // Workflow state from store
  const [storeState, setStoreState] = useState(() => workflowStore.getState());
  const [selectedDelivId, setSelectedDelivId] = useState("deliv_01");
  const [selectedClaimId, setSelectedClaimId] = useState("E03");
  const [zoomLevel, setZoomLevel] = useState("100%");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [saveToast, setSaveToast] = useState(false);

  // Disclosure items
  const [disclosureList, setDisclosureList] = useState(INITIAL_DISCLOSURES);
  const [editingDisclosureId, setEditingDisclosureId] = useState(null);
  const [editingText, setEditingText] = useState("");

  // Dimensions
  const [groundingScore] = useState(94);
  const [consistencyScore] = useState(100);
  const [policyScore] = useState(79);
  const compositeTrustScore = 91;

  // Active deliverable
  const activeDeliverable =
    INITIAL_DELIVERABLES.find((d) => d.id === selectedDelivId) || INITIAL_DELIVERABLES[0];
  const activeClaim = CLAIMS_DATA[selectedClaimId] || CLAIMS_DATA.E03;

  useEffect(() => {
    document.title = "SriGEN — Validate Result";
    const unsubscribe = workflowStore.subscribe((newState) => {
      setStoreState({ ...newState });
    });
    return unsubscribe;
  }, []);

  const handleSelectClaim = (claimTag) => {
    if (CLAIMS_DATA[claimTag]) {
      setSelectedClaimId(claimTag);
    }
  };

  const handleDisclosureActionChange = (id, newAction) => {
    setDisclosureList((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              action: newAction,
              resolved: true,
            }
          : item
      )
    );
    if (newAction === "Edit") {
      const target = disclosureList.find((i) => i.id === id);
      setEditingDisclosureId(id);
      setEditingText(target?.customText || "");
    } else {
      if (editingDisclosureId === id) {
        setEditingDisclosureId(null);
      }
    }
  };

  const handleSaveEditDisclosure = (id) => {
    setDisclosureList((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              customText: editingText,
              resolved: true,
            }
          : item
      )
    );
    setEditingDisclosureId(null);
  };

  const handleSaveChanges = () => {
    setSaveToast(true);
    setTimeout(() => setSaveToast(false), 2600);
  };

  const handleRefine = () => {
    navigate("/refine");
  };

  const handleApproveAndProve = async () => {
    // Record approval in workflowStore
    try {
      const activeDraft = workflowStore.getActiveDraft();
      const draftId = activeDraft?.id || "draft_executive_summary_01";
      const resolvedContent = activeDraft?.content || "SriGEN Executive Summary approved.";
      try {
        const res = await api.approveDraft(draftId, resolvedContent);
        workflowStore.recordApproval(res);
      } catch {
        workflowStore.recordApproval({
          draft_id: draftId,
          final_content: resolvedContent,
          notes: "Approved via Validate Result workspace.",
        });
      }
    } catch (e) {
      console.warn("Failed recording approval:", e);
    }
    navigate("/provenance");
  };

  const unresolvedCount = disclosureList.filter((d) => !d.resolved).length;

  return (
    <div className="val-workspace-root">
      {/* 1. MASTER TOP NAVIGATION (Preserving canonical top bar, Generate active) */}
      <TopBar activePage="generate" />

      {/* 2. SUB-HEADER WITH TOPOGRAPHIC TEXTURE & WORKFLOW PATH */}
      <header className="val-subhead">
        {/* Subtle authentic topographic vector contour backdrop */}
        <div className="val-topo-bg" aria-hidden="true">
          <svg viewBox="0 0 1600 240" preserveAspectRatio="xMidYMid slice">
            <path
              d="M-50,60 Q350,20 750,80 T1350,50 T1700,100"
              fill="none"
              stroke="rgba(208, 154, 69, 0.07)"
              strokeWidth="1.2"
            />
            <path
              d="M-50,140 Q300,180 700,120 T1300,170 T1700,140"
              fill="none"
              stroke="rgba(208, 154, 69, 0.045)"
              strokeWidth="1.2"
            />
            <line
              x1="280"
              y1="0"
              x2="280"
              y2="240"
              stroke="rgba(245, 241, 232, 0.02)"
              strokeDasharray="4 8"
            />
            <line
              x1="880"
              y1="0"
              x2="880"
              y2="240"
              stroke="rgba(245, 241, 232, 0.02)"
              strokeDasharray="4 8"
            />
          </svg>
        </div>

        <div className="val-subhead-inner">
          {/* Left Title Block */}
          <div className="val-title-block">
            <div className="val-eyebrow">VALIDATE / GENERATED RESULTS</div>
            <h1 className="val-heading">Validate Result</h1>
            <p className="val-supporting">
              Inspect evidence, resolve disclosure findings, and confirm the generated result before approval.
            </p>
          </div>

          {/* Right Workflow Path: 01 UNDERSTAND -> 02 CONTROL -> 03 GENERATE -> 04 VALIDATE -> 05 PROVE */}
          <div className="val-workflow-track" aria-label="Transformation Workflow Progression">
            <div className="val-wf-step val-wf-past">
              <div className="val-wf-circle">
                <Icon.Doc />
              </div>
              <div className="val-wf-label">
                <span className="wf-num">01</span>
                <span className="wf-name">UNDERSTAND</span>
              </div>
            </div>

            <div className="val-wf-connector">
              <span className="wf-arrow">→</span>
            </div>

            <div className="val-wf-step val-wf-past">
              <div className="val-wf-circle">
                <Icon.ShieldLock />
              </div>
              <div className="val-wf-label">
                <span className="wf-num">02</span>
                <span className="wf-name">CONTROL</span>
              </div>
            </div>

            <div className="val-wf-connector">
              <span className="wf-arrow">→</span>
            </div>

            <div className="val-wf-step val-wf-past">
              <div className="val-wf-circle">
                <Icon.Spark />
              </div>
              <div className="val-wf-label">
                <span className="wf-num">03</span>
                <span className="wf-name">GENERATE</span>
              </div>
            </div>

            <div className="val-wf-connector val-wf-connector-active">
              <span className="wf-arrow">→</span>
            </div>

            <div className="val-wf-step val-wf-active">
              <div className="val-wf-circle val-wf-circle-gold">
                <Icon.ShieldCheck />
              </div>
              <div className="val-wf-label val-wf-label-gold">
                <span className="wf-num">04</span>
                <span className="wf-name">VALIDATE</span>
              </div>
            </div>

            <div className="val-wf-connector">
              <span className="wf-arrow">→</span>
            </div>

            <div className="val-wf-step val-wf-future">
              <div className="val-wf-circle">
                <Icon.Link />
              </div>
              <div className="val-wf-label">
                <span className="wf-num">05</span>
                <span className="wf-name">PROVE</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 3. MAIN THREE-COLUMN WORKSPACE */}
      <main className="val-main-layout">
        {/* ================= COLUMN 1: DELIVERABLES ================= */}
        <aside className="val-col-deliverables" aria-label="Deliverables List">
          <div className="val-sidebar-header">
            <h2 className="val-sidebar-title">Deliverables</h2>
            <span className="val-sidebar-count">3 total</span>
          </div>

          <div className="val-deliv-list">
            {INITIAL_DELIVERABLES.map((deliv) => {
              const isSelected = deliv.id === selectedDelivId;
              const DelivIcon = deliv.icon;
              return (
                <div
                  key={deliv.id}
                  className={`val-deliv-card ${isSelected ? "is-selected" : ""}`}
                  onClick={() => setSelectedDelivId(deliv.id)}
                  role="button"
                  tabIndex={0}
                  aria-pressed={isSelected}
                >
                  <div className="val-deliv-icon-box">
                    <DelivIcon />
                  </div>

                  <div className="val-deliv-content">
                    <div className="val-deliv-num">{deliv.index}</div>
                    <div className="val-deliv-name">{deliv.title}</div>
                    <div className="val-deliv-meta-row">
                      <span className={`val-deliv-pill pill-${deliv.status.toLowerCase()}`}>
                        {deliv.status === "VERIFIED" ? (
                          <>
                            <Icon.Check /> VERIFIED
                          </>
                        ) : (
                          <>
                            <span className="amber-dot">●</span> ATTENTION
                          </>
                        )}
                      </span>

                      <div className="val-deliv-trust">
                        <span className="trust-circle-badge">{deliv.trustScore}</span>
                        <span className="trust-label">Trust score</span>
                      </div>
                    </div>
                  </div>

                  <div className="val-deliv-chevron">
                    <Icon.Chevron />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Bottom Sidebar Pinned Box: Cross-output consistency */}
          <div className="val-deliv-bottom-box">
            <div className="val-deliv-bottom-inner">
              <span className="val-chain-icon">
                <Icon.Link />
              </span>
              <div className="val-consistency-info">
                <span className="val-cons-title">Cross-output consistency</span>
                <span className="val-cons-status">
                  <Icon.Check /> Consistent
                </span>
              </div>
              <span className="val-bottom-chevron">
                <Icon.Chevron />
              </span>
            </div>
          </div>
        </aside>

        {/* ================= COLUMN 2: CENTER GENERATED RESULT (CREAM PAPER) ================= */}
        <section className="val-col-document" aria-label="Generated Result Document">
          {/* Document Top Bar Controls */}
          <div className="val-doc-topbar">
            <div className="val-doc-topbar-left">
              <span className="val-doc-top-icon">
                <Icon.Doc />
              </span>
              <span className="val-doc-top-title">Executive Summary</span>
              <span className="val-doc-pill draft-pill">DRAFT</span>
              <span className="val-doc-version">v1.0</span>
            </div>

            <div className="val-doc-topbar-right">
              {searchOpen && (
                <input
                  type="text"
                  className="val-doc-search-input"
                  placeholder="Find in document..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  autoFocus
                />
              )}
              <div className="val-zoom-select-wrap">
                <select
                  className="val-zoom-select"
                  value={zoomLevel}
                  onChange={(e) => setZoomLevel(e.target.value)}
                  aria-label="Document zoom level"
                >
                  <option value="90%">90%</option>
                  <option value="100%">100%</option>
                  <option value="110%">110%</option>
                  <option value="125%">125%</option>
                </select>
                <Icon.ChevronDown />
              </div>

              <button
                type="button"
                className="val-doc-ctrl-btn"
                title="Search Document"
                onClick={() => setSearchOpen(!searchOpen)}
              >
                <Icon.Search />
              </button>
              <button
                type="button"
                className="val-doc-ctrl-btn"
                title="Fullscreen View"
                onClick={() => {}}
              >
                <Icon.Maximize />
              </button>
              <button
                type="button"
                className="val-doc-ctrl-btn"
                title="Copy Content"
                onClick={() => {
                  navigator.clipboard?.writeText(
                    "Executive Summary\nIncident Response - Operational Overview\nCLASSIFIED SRI GEN INTELLIGENCE PRODUCT"
                  );
                }}
              >
                <Icon.Copy />
              </button>
              <button
                type="button"
                className="val-doc-ctrl-btn"
                title="Transformation Options"
                onClick={() => {}}
              >
                <Icon.Sliders />
              </button>
            </div>
          </div>

          {/* Authentic Warm Cream Paper Document Viewport */}
          <div className="val-doc-scroll-area">
            <article
              className="val-cream-sheet"
              style={{
                transform: `scale(${parseFloat(zoomLevel) / 100})`,
                transformOrigin: "top center",
              }}
            >
              {/* Paper Header */}
              <div className="val-sheet-header">
                <div className="val-stamp-classified">CLASSIFIED</div>
                <div className="val-sheet-meta-top">
                  <span className="sheet-prod-tag">SRIGEN / INTELLIGENCE PRODUCT</span>
                  <span className="sheet-page-tag">Page 1 of 4</span>
                </div>
              </div>

              {/* Title & Subtitle */}
              <div className="val-sheet-title-group">
                <h1 className="val-sheet-title">Executive Summary</h1>
                <p className="val-sheet-subtitle">Incident Response – Operational Overview</p>
              </div>

              {/* Thin Rules & Document Metadata Table */}
              <div className="val-sheet-meta-bar">
                <div className="val-sm-cell">
                  <span className="val-sm-lbl">SOURCE</span>
                  <span className="val-sm-val">
                    {storeState.source?.name || "incident_report.pdf"}
                  </span>
                </div>
                <div className="val-sm-cell">
                  <span className="val-sm-lbl">DATE:</span>
                  <span className="val-sm-val">15 Sep 2026</span>
                </div>
                <div className="val-sm-cell">
                  <span className="val-sm-lbl">REF:</span>
                  <span className="val-sm-val">
                    {storeState.source?.id || "SRI-2026-041"}
                  </span>
                </div>
              </div>

              {/* Body Content with Inline Claim Highlights */}
              <div className="val-sheet-body">
                {/* 1. Situation */}
                <section className="val-sheet-section">
                  <h2 className="val-section-heading">1. Situation</h2>
                  <p className="val-sheet-para">
                    The incident affected{" "}
                    <mark className="val-paper-mark-green">24 systems</mark>{" "}
                    <span
                      className={`val-claim-pill chip-verified ${
                        selectedClaimId === "E01" ? "chip-active" : ""
                      }`}
                      onClick={() => handleSelectClaim("E01")}
                      role="button"
                      tabIndex={0}
                    >
                      E01 <span className="chip-status">VERIFIED</span>
                    </span>{" "}
                    across the affected region, with initial indications of coordinated activity
                    targeting critical infrastructure. The event was detected on 14 Sep 2026 at
                    approximately 03:42 (UTC) and remains under investigation.
                  </p>
                  <p className="val-sheet-para">
                    Preliminary analysis suggests the activity is consistent with a known threat
                    actor's tactics, techniques and procedures (TTPs) observed in recent campaigns.
                  </p>
                </section>

                {/* 2. Key Findings */}
                <section className="val-sheet-section">
                  <h2 className="val-section-heading">2. Key Findings</h2>
                  <ul className="val-sheet-list">
                    <li>
                      <mark className="val-paper-mark-green">24 systems</mark> were affected across
                      the region.{" "}
                      <span
                        className={`val-claim-pill chip-verified ${
                          selectedClaimId === "E01" ? "chip-active" : ""
                        }`}
                        onClick={() => handleSelectClaim("E01")}
                        role="button"
                        tabIndex={0}
                      >
                        E01 <span className="chip-status">VERIFIED</span>
                      </span>
                    </li>
                    <li className="val-li-highlighted">
                      Initial access was likely gained via a compromised credential.{" "}
                      <span
                        className={`val-claim-pill chip-attention ${
                          selectedClaimId === "E03" ? "chip-active" : ""
                        }`}
                        onClick={() => handleSelectClaim("E03")}
                        role="button"
                        tabIndex={0}
                      >
                        E03 <span className="chip-status">ATTENTION</span>
                      </span>
                    </li>
                    <li>
                      No evidence of data exfiltration at this time.{" "}
                      <span
                        className={`val-claim-pill chip-verified ${
                          selectedClaimId === "E06" ? "chip-active" : ""
                        }`}
                        onClick={() => handleSelectClaim("E06")}
                        role="button"
                        tabIndex={0}
                      >
                        E06 <span className="chip-status">VERIFIED</span>
                      </span>
                    </li>
                  </ul>
                </section>

                {/* 3. Recommended Action */}
                <section className="val-sheet-section">
                  <h2 className="val-section-heading">3. Recommended Action</h2>
                  <ol className="val-sheet-numbered">
                    <li>Increase monitoring on affected systems.</li>
                    <li>Validate credential hygiene and access controls.</li>
                    <li>Continue investigation to determine full scope and attribution.</li>
                  </ol>
                </section>
              </div>

              {/* Watermark Angled Stamp */}
              <div className="val-watermark-draft" aria-hidden="true">
                DRAFT
              </div>

              {/* Fine Document Footer */}
              <div className="val-sheet-footer">
                <span>SRIGEN</span>
                <span className="footer-slash">/</span>
                <span>INTELLIGENCE PRODUCT</span>
                <span className="footer-slash">/</span>
                <span>EXECUTIVE SUMMARY</span>
              </div>
            </article>
          </div>
        </section>

        {/* ================= COLUMN 3: VALIDATION & SECURITY INSPECTOR ================= */}
        <aside className="val-col-inspector" aria-label="Validation & Security Inspector">
          <div className="val-inspector-stack">
            {/* 1. VALIDATION PANEL */}
            <div className="val-card val-card-validation">
              <div className="val-card-header">
                <div className="val-card-title-group">
                  <Icon.ShieldCheck />
                  <h3 className="val-card-title">Validation</h3>
                </div>
                <button type="button" className="val-card-close" aria-label="Close">
                  <Icon.Close />
                </button>
              </div>

              <div className="val-card-body">
                {/* Flagged Claim Header */}
                <div className="val-claim-header-row">
                  <div className="val-claim-tag-group">
                    <span className="val-claim-sublabel">FLAGGED CLAIM</span>
                    <span
                      className={`val-claim-code ${
                        activeClaim.status === "ATTENTION" ? "code-amber" : "code-green"
                      }`}
                    >
                      {activeClaim.tag}
                    </span>
                  </div>
                  <span className="val-grounding-pill">
                    <Icon.CheckCircle /> Grounding confirmed
                  </span>
                </div>

                <div className="val-claim-quote-box">
                  <p className="val-claim-quote-text">“{activeClaim.quote}”</p>
                </div>

                {/* Source Evidence */}
                <div className="val-evidence-header-row">
                  <span className="val-ev-label">Source evidence</span>
                  <span className="val-ev-match">Match type: {activeClaim.matchType}</span>
                </div>

                <div className="val-evidence-box">
                  <p className="val-evidence-text">“{activeClaim.evidence}”</p>
                  <div className="val-evidence-status">
                    <Icon.CheckCircle />
                    <span>Grounding confirmed</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 2. DISCLOSURE CONTROL PANEL */}
            <div className="val-card val-card-disclosure">
              <div className="val-card-header">
                <div className="val-card-title-group">
                  <Icon.ShieldLock />
                  <h3 className="val-card-title">Disclosure Control</h3>
                </div>
                <div className="val-card-header-right">
                  <span className="val-badge-pill pill-amber">
                    {disclosureList.filter((d) => !d.resolved).length > 0 ? "2 findings" : "0 unresolved"}
                  </span>
                  <button type="button" className="val-card-close" aria-label="Close">
                    <Icon.Close />
                  </button>
                </div>
              </div>

              <div className="val-card-body">
                <div className="val-disclosure-list">
                  {disclosureList.map((item, idx) => (
                    <div key={item.id} className="val-disc-item">
                      <div className="val-disc-left">
                        <span className="val-disc-num">{idx + 1}.</span>
                        <div className="val-disc-text-wrap">
                          <span
                            className={`val-disc-text ${
                              !item.resolved ? "text-unresolved" : ""
                            }`}
                          >
                            {!item.resolved && <strong className="unres-tag">Unresolved: </strong>}
                            {item.text}
                          </span>
                          {item.action === "Edit" && item.customText && (
                            <span className="val-disc-edit-preview">
                              Edited: “{item.customText}”
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="val-disc-actions">
                        <select
                          className={`val-disc-select select-${item.action.toLowerCase()}`}
                          value={item.action}
                          onChange={(e) =>
                            handleDisclosureActionChange(item.id, e.target.value)
                          }
                          aria-label={`Action for disclosure finding ${idx + 1}`}
                        >
                          <option value="Disclose">Disclose ⌵</option>
                          <option value="Edit">Edit ⌵</option>
                          <option value="Withhold">Withhold ◊</option>
                        </select>
                      </div>

                      {editingDisclosureId === item.id && (
                        <div className="val-disc-inline-edit">
                          <input
                            type="text"
                            value={editingText}
                            onChange={(e) => setEditingText(e.target.value)}
                            placeholder="Enter sanitized redaction text..."
                            className="val-disc-input"
                          />
                          <button
                            type="button"
                            className="val-btn-tiny-save"
                            onClick={() => handleSaveEditDisclosure(item.id)}
                          >
                            Save
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 3. TRUST SCORE PANEL */}
            <div className="val-card val-card-trust">
              <div className="val-card-header">
                <div className="val-card-title-group">
                  <Icon.ShieldCheck />
                  <h3 className="val-card-title">Trust Score</h3>
                </div>
                <span className="val-trust-subnote">
                  Security & disclosure findings are separate from trust score.
                </span>
              </div>

              <div className="val-card-body">
                {/* Score Number Row */}
                <div className="val-trust-score-row">
                  <div className="val-ts-digits">
                    <span className="val-ts-big">{compositeTrustScore}</span>
                    <span className="val-ts-denom">/ 100</span>
                  </div>
                  <span className="val-review-badge">REVIEW REQUIRED</span>
                </div>

                {/* Dimension Progress Bars */}
                <div className="val-trust-bars">
                  <div className="val-bar-row">
                    <span className="val-bar-name">Grounding</span>
                    <div className="val-bar-track">
                      <div
                        className="val-bar-fill fill-green"
                        style={{ width: `${groundingScore}%` }}
                      ></div>
                    </div>
                    <span className="val-bar-val">{groundingScore}</span>
                  </div>

                  <div className="val-bar-row">
                    <span className="val-bar-name">Consistency</span>
                    <div className="val-bar-track">
                      <div
                        className="val-bar-fill fill-green"
                        style={{ width: `${consistencyScore}%` }}
                      ></div>
                    </div>
                    <span className="val-bar-val">{consistencyScore}</span>
                  </div>

                  <div className="val-bar-row">
                    <span className="val-bar-name">Policy</span>
                    <div className="val-bar-track">
                      <div
                        className="val-bar-fill fill-amber"
                        style={{ width: `${policyScore}%` }}
                      ></div>
                    </div>
                    <span className="val-bar-val">{policyScore}</span>
                  </div>
                </div>

                {/* Sub Consistency indicator */}
                <div className="val-trust-consistency-strip">
                  <Icon.Link />
                  <span className="val-tc-label">Cross-output consistency</span>
                  <span className="val-tc-status">
                    <Icon.Check /> Consistent
                  </span>
                </div>
              </div>
            </div>

            {/* 4. SECURITY ACTIONS PANEL */}
            <div className="val-card val-card-security">
              <div className="val-card-header">
                <div className="val-card-title-group">
                  <Icon.ShieldCheck />
                  <h3 className="val-card-title">Security Actions</h3>
                  <span className="val-sec-count-badge">2</span>
                </div>
                <button type="button" className="val-card-close" aria-label="Close">
                  <Icon.Close />
                </button>
              </div>

              <div className="val-card-body">
                <ol className="val-sec-actions-list">
                  <li>Review and confirm disclosure decisions</li>
                  <li>Check for potential policy violations</li>
                </ol>
                <div className="val-sec-footer-link">
                  <a href="#view-log" onClick={(e) => e.preventDefault()}>
                    View log →
                  </a>
                </div>
              </div>
            </div>

            {/* 5. TRANSFORMATION CONFIGURATION PANEL */}
            <div className="val-card val-card-config">
              <div className="val-card-header">
                <div className="val-card-title-group">
                  <Icon.Sliders />
                  <h3 className="val-card-title">Transformation Configuration</h3>
                </div>
                <button type="button" className="val-card-close" aria-label="Close">
                  <Icon.Close />
                </button>
              </div>

              <div className="val-card-body">
                <div className="val-config-grid">
                  <div className="val-cfg-item">
                    <span className="cfg-key">Source</span>
                    <span className="cfg-val">
                      {storeState.source?.name || "incident_report.pdf"}
                    </span>
                  </div>
                  <div className="val-cfg-item">
                    <span className="cfg-key">Language</span>
                    <span className="cfg-val">Auto</span>
                  </div>

                  <div className="val-cfg-item">
                    <span className="cfg-key">Deliverables</span>
                    <span className="cfg-val">Executive Summary + LinkedIn Post + Advisory</span>
                  </div>
                  <div className="val-cfg-item">
                    <span className="cfg-key">Detail</span>
                    <span className="cfg-val">Balanced</span>
                  </div>

                  <div className="val-cfg-item">
                    <span className="cfg-key">Audience</span>
                    <span className="cfg-val">Senior Leadership</span>
                  </div>
                  <div className="val-cfg-item">
                    <span className="cfg-key">Security</span>
                    <span className="cfg-val cfg-highlight-green">Disclosure Control Active</span>
                  </div>

                  <div className="val-cfg-item">
                    <span className="cfg-key">Tone</span>
                    <span className="cfg-val">Auto → Formal</span>
                  </div>
                  <div className="val-cfg-item">
                    <span className="cfg-key">Fact Base</span>
                    <span className="cfg-val">One shared Fact / Entity Graph</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </main>

      {/* 4. PERSISTENT BOTTOM VALIDATION STATUS BAR */}
      <footer className="val-bottom-bar" role="contentinfo">
        <div className="val-bottom-bar-inner">
          {/* Left Requirement Alert */}
          <div className="val-bottom-left">
            <div className="val-alert-icon-circle">!</div>
            <div className="val-bottom-req-text">
              <span className="req-title">VALIDATION REQUIRED</span>
              <span className="req-sub">
                All flagged claims and disclosure findings must be resolved before approval.
              </span>
            </div>
          </div>

          {/* Middle Telemetry Statistics */}
          <div className="val-bottom-metrics">
            <div className="val-metric-col">
              <span className="metric-val">3</span>
              <span className="metric-lbl">deliverables</span>
            </div>
            <div className="metric-divider"></div>

            <div className="val-metric-col">
              <span className="metric-val">17</span>
              <span className="metric-lbl">claims checked</span>
            </div>
            <div className="metric-divider"></div>

            <div className="val-metric-col">
              <span className="metric-val metric-green">16</span>
              <span className="metric-lbl">verified</span>
            </div>
            <div className="metric-divider"></div>

            <div className="val-metric-col">
              <span className="metric-val metric-amber">1</span>
              <span className="metric-lbl">requires attention</span>
            </div>
            <div className="metric-divider"></div>

            <div className="val-metric-col">
              <span className="metric-val">2</span>
              <span className="metric-lbl">disclosure actions</span>
            </div>
            <div className="metric-divider"></div>

            <div className="val-metric-col">
              <span className="metric-val">91/100</span>
              <span className="metric-lbl">Trust</span>
            </div>
            <div className="metric-divider"></div>

            <div className="val-metric-col val-metric-cons">
              <span className="metric-lbl-compact">Cross-output consistency</span>
              <span className="metric-val-compact">
                <Icon.Check /> Consistent
              </span>
            </div>
          </div>

          {/* Right Action Buttons */}
          <div className="val-bottom-actions">
            <button
              type="button"
              className="val-btn-secondary"
              onClick={handleSaveChanges}
            >
              Save changes
            </button>

            <button
              type="button"
              className="val-btn-secondary"
              onClick={handleRefine}
            >
              Refine output
            </button>

            <div className="val-approve-cta-group">
              <button
                type="button"
                className="val-btn-approve-primary"
                onClick={handleApproveAndProve}
              >
                <span>Approve & prove</span>
                <span className="val-btn-arrow">→</span>
              </button>
              <span className="val-cta-subtext">(Triggers provenance proof)</span>
            </div>
          </div>
        </div>

        {/* Save confirmation toast */}
        {saveToast && (
          <div className="val-save-toast">
            <Icon.CheckCircle />
            <span>Validation changes saved to session.</span>
          </div>
        )}
      </footer>
    </div>
  );
}
