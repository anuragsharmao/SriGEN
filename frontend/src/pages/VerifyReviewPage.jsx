import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import TopBar from "../components/TopBar.jsx";
import { api } from "../services/api.js";
import { workflowStore } from "../services/workflowStore.js";
import "./VerifyReviewPage.css";

const Icon = {
  Shield: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  Check: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  AlertTriangle: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  AlertCircle: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  ArrowRight: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  ),
  ArrowLeft: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  ),
  Refresh: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  ),
  Edit: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  ),
  FileText: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  Quote: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z" />
      <path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z" />
    </svg>
  ),
  Lock: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  )
};

export default function VerifyReviewPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Active state synced with workflow store
  const [activeDraftId, setActiveDraftId] = useState(() => {
    return searchParams.get("draftId") || workflowStore.getActiveDraft()?.id || "draft_advisory_01";
  });

  const [draftsList, setDraftsList] = useState(() => workflowStore.getAllDrafts());
  const [sourceDoc, setSourceDoc] = useState(() => workflowStore.getSourceDoc());
  const [trustScore, setTrustScore] = useState(() => workflowStore.getTrustScore());
  const [disclosureItems, setDisclosureItems] = useState(() => workflowStore.getDisclosureItems());

  // UI tabs & selection
  const [activeInspectorTab, setActiveInspectorTab] = useState("grounding"); // 'grounding' | 'consistency' | 'policy'
  const [selectedClaimId, setSelectedClaimId] = useState("claim_1");
  const [editingItemId, setEditingItemId] = useState(null);
  const [editInputText, setEditInputText] = useState("");

  // Verification staged modal
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationStage, setVerificationStage] = useState(1);

  // Sync state whenever store changes
  const refreshStoreState = () => {
    setDraftsList(workflowStore.getAllDrafts());
    setSourceDoc(workflowStore.getSourceDoc());
    setTrustScore(workflowStore.getTrustScore());
    setDisclosureItems(workflowStore.getDisclosureItems());
  };

  const currentDraft = draftsList.find((d) => d.id === activeDraftId) || draftsList[0];

  const handleSelectDraft = (id) => {
    setActiveDraftId(id);
    workflowStore.setActiveDraft(id);
    refreshStoreState();
  };

  // Run verification flow
  const runVerificationPass = () => {
    setIsVerifying(true);
    setVerificationStage(1);
    setTimeout(() => setVerificationStage(2), 500);
    setTimeout(() => setVerificationStage(3), 1100);
    setTimeout(() => setVerificationStage(4), 1700);
    setTimeout(() => {
      setVerificationStage(5);
      setTimeout(() => {
        setIsVerifying(false);
        refreshStoreState();
      }, 600);
    }, 2300);
  };

  // Disclosure decision handlers
  const handleDisclosureDecision = async (itemId, choice, manualText = null) => {
    workflowStore.setDisclosureDecision(itemId, choice, manualText);
    refreshStoreState();
    setEditingItemId(null);
    setEditInputText("");
    try {
      await api.decideDisclosureItem(itemId, choice, manualText);
    } catch {
      // Offline fallback already updated in workflowStore
    }
  };

  const handleBulkAcceptAll = async () => {
    workflowStore.bulkAcceptAllDisclosure();
    refreshStoreState();
    try {
      await api.bulkAcceptDisclosure(currentDraft.id);
    } catch {
      // Handled via local store
    }
  };

  // Check unresolved count
  const unresolvedItems = disclosureItems.filter((item) => !item.analyst_choice);
  const isApprovalReady = unresolvedItems.length === 0;

  // Grounding claims mock list
  const claims = [
    {
      id: "claim_1",
      statement: "Q1 production reached 42,000 units across primary manufacturing clusters.",
      status: "verified",
      confidence: "99.2%",
      sourceExcerpt: "Total cluster yield across Facility Alpha and Facility Gamma reached 42,000 verified operational units in Q1 2026.",
      citation: "Source Document §2.4 (Page 6, Line 12)"
    },
    {
      id: "claim_2",
      statement: "Zero critical telemetry anomalies or security breaches were logged during validation.",
      status: "verified",
      confidence: "98.7%",
      sourceExcerpt: "Audit reports corroborate zero Level-1 safety breaches and zero telemetry security anomalies during the 90-day evaluation interval.",
      citation: "Source Document §5.1 (Page 14, Line 4)"
    },
    {
      id: "claim_3",
      statement: "Phase 2 operational migration is scheduled to initiate early in Q3 2026.",
      status: "extrapolated",
      confidence: "88.4%",
      sourceExcerpt: "Initial Phase 2 deployment target window is estimated for mid-year 2026, contingent upon secondary regulatory review.",
      citation: "Source Document §7.2 (Page 21, Line 33)"
    },
    {
      id: "claim_4",
      statement: "Capital reinvestment efficiency improved by 18.5% over the preceding fiscal quarter.",
      status: "verified",
      confidence: "97.9%",
      sourceExcerpt: "Capital utilization metrics demonstrate an 18.5% quarter-over-quarter efficiency expansion across hardware procurement.",
      citation: "Source Document §3.8 (Page 9, Line 18)"
    }
  ];

  const selectedClaim = claims.find((c) => c.id === selectedClaimId) || claims[0];

  // Cross output consistency items
  const consistencyChecks = [
    {
      fact: "Q1 Output Yield (42,000 units)",
      deliverables: "Advisory, Presentation, FAQ",
      status: "Consistent",
      notes: "Identical numeric value and qualification across all synthesized deliverables."
    },
    {
      fact: "Phase 2 Target Date (Q3 2026)",
      deliverables: "Advisory, Presentation, LinkedIn Post",
      status: "Consistent",
      notes: "Contingency disclaimer preserved identically in formal notes and brief bullet."
    },
    {
      fact: "Facility Redactions / Code Names",
      deliverables: "Advisory, SitRep",
      status: "Pending Disclosure Check",
      notes: "Facility code PRJ-ALPHA masked consistently pending analyst override."
    }
  ];

  return (
    <div className="verify-page-root">
      <TopBar activePage="verify" />

      <main className="verify-container">
        {/* Pipeline Breadcrumb */}
        <div className="verify-pipeline-tracker">
          <Link to="/generate" className="pipeline-step completed">
            <span className="pipeline-step-badge">1</span>
            <span>Generate</span>
          </Link>
          <span className="pipeline-divider">›</span>
          <Link to="/result" className="pipeline-step completed">
            <span className="pipeline-step-badge">2</span>
            <span>Result</span>
          </Link>
          <span className="pipeline-divider">›</span>
          <div className="pipeline-step active">
            <span className="pipeline-step-badge">3</span>
            <span>Verify & Review</span>
          </div>
          <span className="pipeline-divider">›</span>
          <div className={`pipeline-step ${isApprovalReady ? "" : "disabled"}`}>
            <span className="pipeline-step-badge">4</span>
            <span>Approval</span>
          </div>
          <span className="pipeline-divider">›</span>
          <div className="pipeline-step">
            <span className="pipeline-step-badge">5</span>
            <span>Provenance</span>
          </div>
        </div>

        {/* Page Header */}
        <div className="verify-header-card">
          <div className="verify-header-title-block">
            <h1>Verify & Review Workspace</h1>
            <p className="verify-header-subtitle">
              Comprehensive multi-engine audit: Grounding verification against source, cross-deliverable consistency,
              institutional policy checks, and mandatory disclosure governance.
            </p>
          </div>
          <div className="verify-header-meta">
            <div className="source-ref-chip">
              <Icon.FileText />
              <span>{sourceDoc.name}</span>
              <span className="hash-mono">SHA-256: {sourceDoc.hash.slice(0, 10)}...</span>
            </div>
          </div>
        </div>

        {/* Section A: Trust Score Composite Banner */}
        <section className="trust-score-hero-banner" aria-label="Trust Score Breakdown">
          <div className="trust-hero-main-row">
            <div className="trust-hero-score-group">
              <div className="trust-score-dial-large">
                <span className="trust-dial-val">{trustScore.composite.toFixed(1)}</span>
                <span className="trust-dial-scale">/ 100</span>
              </div>
              <div className="trust-hero-status-text">
                <span className="trust-verdict-badge">
                  <Icon.Check />
                  VERIFICATION COMPLETE · HIGH CONFIDENCE
                </span>
                <h2 className="trust-hero-heading">Canonical Multi-Factor Trust Score</h2>
                <p className="trust-hero-sub">
                  Mathematical composite computed directly from factual entailment, sibling format agreement, and constraint verification.
                </p>
              </div>
            </div>
            <button className="btn-secondary-action" type="button" onClick={runVerificationPass}>
              <Icon.Refresh />
              <span>Verify Again</span>
            </button>
          </div>

          {/* Score Pillars Grid */}
          <div className="trust-score-pillars-grid">
            <div className="trust-pillar-card">
              <div className="pillar-top-row">
                <div className="pillar-title-group">
                  <span className="pillar-label">1. Grounding Precision</span>
                  <span className="pillar-weight-tag">50% WEIGHT</span>
                </div>
                <span className="pillar-value">{trustScore.grounding.toFixed(1)}%</span>
              </div>
              <div className="pillar-bar-outer">
                <div className="pillar-bar-fill fill-grounding" style={{ width: `${trustScore.grounding}%` }} />
              </div>
              <p className="pillar-caption">
                12 of 12 factual assertions verified verbatim against canonical source graph nodes.
              </p>
            </div>

            <div className="trust-pillar-card">
              <div className="pillar-top-row">
                <div className="pillar-title-group">
                  <span className="pillar-label">2. Cross-Output Consistency</span>
                  <span className="pillar-weight-tag">30% WEIGHT</span>
                </div>
                <span className="pillar-value">{trustScore.consistency.toFixed(1)}%</span>
              </div>
              <div className="pillar-bar-outer">
                <div className="pillar-bar-fill fill-consistency" style={{ width: `${trustScore.consistency}%` }} />
              </div>
              <p className="pillar-caption">
                Zero contradictions detected across sibling presentation, infographic, and social adapters.
              </p>
            </div>

            <div className="trust-pillar-card">
              <div className="pillar-top-row">
                <div className="pillar-title-group">
                  <span className="pillar-label">3. Policy & Compliance</span>
                  <span className="pillar-weight-tag">20% WEIGHT</span>
                </div>
                <span className="pillar-value">{trustScore.policy.toFixed(1)}%</span>
              </div>
              <div className="pillar-bar-outer">
                <div className="pillar-bar-fill fill-policy" style={{ width: `${trustScore.policy}%` }} />
              </div>
              <p className="pillar-caption">
                Full institutional tone adherence, mandatory disclaimers included, zero prohibited spans.
              </p>
            </div>
          </div>
        </section>

        {/* Deliverable Switcher */}
        {draftsList.length > 1 && (
          <div className="verify-deliverables-nav">
            {draftsList.map((draft) => (
              <button
                key={draft.id}
                type="button"
                className={`verify-nav-tab ${draft.id === activeDraftId ? "active" : ""}`}
                onClick={() => handleSelectDraft(draft.id)}
              >
                <Icon.FileText />
                <span>{draft.title}</span>
                <span className="tab-badge-pass">Verified</span>
              </button>
            ))}
          </div>
        )}

        {/* Main Workspace Two-Column Split (Document vs Inspector) */}
        <div className="verify-workspace-grid">
          {/* Left Column: Warm Cream Editorial Document Surface */}
          <div className="verify-document-card">
            <div className="verify-doc-header">
              <div className="verify-doc-title-row">
                <span className="verify-doc-icon">
                  <Icon.FileText />
                </span>
                <span className="verify-doc-name">{currentDraft?.title || "Operational Advisory"}</span>
              </div>
              <span className="verify-doc-badge">Interactive Audit View</span>
            </div>

            <div className="verify-doc-content-body">
              <p>
                <strong>EXECUTIVE SUMMARY & OPERATIONAL ASSESSMENT</strong>
              </p>
              <p>
                This synthesized advisory details the operational rollout and strategic metrics established during the
                evaluation cycle.
              </p>
              <p>
                <span
                  className={`claim-mark verified ${selectedClaimId === "claim_1" ? "active" : ""}`}
                  onClick={() => {
                    setSelectedClaimId("claim_1");
                    setActiveInspectorTab("grounding");
                  }}
                  title="Click to inspect source grounding evidence"
                >
                  Q1 production reached 42,000 units across primary manufacturing clusters.
                </span>{" "}
                All critical metrics conformed to standard operating boundaries. Internal telemetry cluster identified
                as{" "}
                {disclosureItems.find((i) => i.id === "disc_1")?.analyst_choice === "disclose" ? (
                  <span className="disclosure-span-tag disclosed">[INTERNAL_ID: PRJ-ALPHA]</span>
                ) : disclosureItems.find((i) => i.id === "disc_1")?.analyst_choice === "edit" ? (
                  <span className="disclosure-span-tag edited">
                    [{disclosureItems.find((i) => i.id === "disc_1")?.manual_edit_text || "EDITED"}]
                  </span>
                ) : disclosureItems.find((i) => i.id === "disc_1")?.analyst_choice === "withhold" ? (
                  <span className="disclosure-span-tag withheld">[REDACTED CLUSTER]</span>
                ) : (
                  <span className="disclosure-span-tag pending">[PENDING DISCLOSURE: PRJ-ALPHA]</span>
                )}{" "}
                has met performance gates.
              </p>
              <p>
                <span
                  className={`claim-mark verified ${selectedClaimId === "claim_2" ? "active" : ""}`}
                  onClick={() => {
                    setSelectedClaimId("claim_2");
                    setActiveInspectorTab("grounding");
                  }}
                  title="Click to inspect source grounding evidence"
                >
                  Zero critical telemetry anomalies or security breaches were logged during validation.
                </span>{" "}
                Quarterly balance sheet impact estimated around{" "}
                {disclosureItems.find((i) => i.id === "disc_2")?.analyst_choice === "disclose" ? (
                  <span className="disclosure-span-tag disclosed">[$14.2M OPEX]</span>
                ) : disclosureItems.find((i) => i.id === "disc_2")?.analyst_choice === "edit" ? (
                  <span className="disclosure-span-tag edited">
                    [{disclosureItems.find((i) => i.id === "disc_2")?.manual_edit_text || "EDITED"}]
                  </span>
                ) : disclosureItems.find((i) => i.id === "disc_2")?.analyst_choice === "withhold" ? (
                  <span className="disclosure-span-tag withheld">[FIGURE WITHHELD]</span>
                ) : (
                  <span className="disclosure-span-tag pending">[PENDING DISCLOSURE: $14.2M]</span>
                )}{" "}
                with total budget headroom intact.
              </p>
              <p>
                <span
                  className={`claim-mark warning ${selectedClaimId === "claim_3" ? "active" : ""}`}
                  onClick={() => {
                    setSelectedClaimId("claim_3");
                    setActiveInspectorTab("grounding");
                  }}
                  title="Click to inspect source grounding evidence (extrapolated timeframe)"
                >
                  Phase 2 operational migration is scheduled to initiate early in Q3 2026.
                </span>{" "}
                Implementation partners including{" "}
                {disclosureItems.find((i) => i.id === "disc_3")?.analyst_choice === "disclose" ? (
                  <span className="disclosure-span-tag disclosed">[Apex Aerospace Ltd.]</span>
                ) : disclosureItems.find((i) => i.id === "disc_3")?.analyst_choice === "edit" ? (
                  <span className="disclosure-span-tag edited">
                    [{disclosureItems.find((i) => i.id === "disc_3")?.manual_edit_text || "EDITED"}]
                  </span>
                ) : disclosureItems.find((i) => i.id === "disc_3")?.analyst_choice === "withhold" ? (
                  <span className="disclosure-span-tag withheld">[TIER-1 SUPPLIER]</span>
                ) : (
                  <span className="disclosure-span-tag pending">[PENDING DISCLOSURE: Apex Aerospace]</span>
                )}{" "}
                remain fully on track for delivery.
              </p>
              <p>
                <span
                  className={`claim-mark verified ${selectedClaimId === "claim_4" ? "active" : ""}`}
                  onClick={() => {
                    setSelectedClaimId("claim_4");
                    setActiveInspectorTab("grounding");
                  }}
                  title="Click to inspect source grounding evidence"
                >
                  Capital reinvestment efficiency improved by 18.5% over the preceding fiscal quarter.
                </span>
              </p>
            </div>

            <div className="verify-doc-footer">
              <div className="legend-row">
                <span className="legend-item">
                  <span className="legend-dot dot-green" /> Verified Source Claim
                </span>
                <span className="legend-item">
                  <span className="legend-dot dot-amber" /> Extrapolated / Soft Inference
                </span>
                <span className="legend-item">
                  <span className="legend-dot dot-red" /> Unverified Flag
                </span>
              </div>
              <span>Click any highlighted claim to view source audit link</span>
            </div>
          </div>

          {/* Right Column: Multi-Tab Audit Inspector Panel */}
          <div className="verify-inspector-panel">
            <div className="inspector-tabs-header">
              <button
                type="button"
                className={`inspector-tab-btn ${activeInspectorTab === "grounding" ? "active" : ""}`}
                onClick={() => setActiveInspectorTab("grounding")}
              >
                <span>Grounding & Claims</span>
                <span className="inspector-tab-badge badge-emerald">4/4</span>
              </button>
              <button
                type="button"
                className={`inspector-tab-btn ${activeInspectorTab === "consistency" ? "active" : ""}`}
                onClick={() => setActiveInspectorTab("consistency")}
              >
                <span>Consistency</span>
                <span className="inspector-tab-badge badge-emerald">100%</span>
              </button>
              <button
                type="button"
                className={`inspector-tab-btn ${activeInspectorTab === "policy" ? "active" : ""}`}
                onClick={() => setActiveInspectorTab("policy")}
              >
                <span>Policy & Safety</span>
                <span className="inspector-tab-badge badge-emerald">Pass</span>
              </button>
            </div>

            <div className="inspector-tab-content">
              {/* Tab 1: Grounding & Claims */}
              {activeInspectorTab === "grounding" && (
                <div className="claims-list-wrapper">
                  {claims.map((claim) => (
                    <div
                      key={claim.id}
                      className={`claim-item-card ${selectedClaimId === claim.id ? "selected" : ""}`}
                      onClick={() => setSelectedClaimId(claim.id)}
                    >
                      <div className="claim-item-top">
                        <span
                          className={`claim-status-tag ${
                            claim.status === "verified"
                              ? "tag-verified"
                              : claim.status === "extrapolated"
                              ? "tag-extrapolated"
                              : "tag-unverified"
                          }`}
                        >
                          <Icon.Check />
                          {claim.status === "verified"
                            ? "Verified from Source"
                            : claim.status === "extrapolated"
                            ? "Extrapolated"
                            : "Unverified"}
                        </span>
                        <span className="claim-score-val">Confidence: {claim.confidence}</span>
                      </div>
                      <p className="claim-statement-text">{claim.statement}</p>

                      {selectedClaimId === claim.id && (
                        <div className="claim-evidence-details">
                          <div className="evidence-quote-box">
                            <Icon.Quote /> &ldquo;{claim.sourceExcerpt}&rdquo;
                          </div>
                          <div className="evidence-source-loc">
                            <Icon.FileText />
                            <span>{claim.citation}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 2: Cross-Output Consistency Matrix */}
              {activeInspectorTab === "consistency" && (
                <div>
                  <table className="consistency-matrix-table">
                    <thead>
                      <tr>
                        <th>Asserted Fact / Entity</th>
                        <th>Outputs Checked</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {consistencyChecks.map((check, idx) => (
                        <tr key={idx}>
                          <td>
                            <strong>{check.fact}</strong>
                            <div style={{ color: "#9ca3af", fontSize: "0.75rem", marginTop: 4 }}>
                              {check.notes}
                            </div>
                          </td>
                          <td>{check.deliverables}</td>
                          <td>
                            <span className="status-chip-match">
                              <Icon.Check />
                              {check.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Tab 3: Policy & Compliance */}
              {activeInspectorTab === "policy" && (
                <div className="policy-checklist-group">
                  <div className="policy-card-item">
                    <span className="policy-check-icon"><Icon.Check /></span>
                    <div>
                      <h4 className="policy-item-title">Zero Prohibited Forward-Looking Commitments</h4>
                      <p className="policy-item-desc">
                        Every future date assertion contains qualified contingency clauses matching institutional guidelines.
                      </p>
                    </div>
                  </div>
                  <div className="policy-card-item">
                    <span className="policy-check-icon"><Icon.Check /></span>
                    <div>
                      <h4 className="policy-item-title">Attribution & Source Grounding Verification</h4>
                      <p className="policy-item-desc">
                        100% of numerical findings trace back to verified canonical graph nodes without hallucinatory additions.
                      </p>
                    </div>
                  </div>
                  <div className="policy-card-item">
                    <span className="policy-check-icon"><Icon.Check /></span>
                    <div>
                      <h4 className="policy-item-title">PII & Unsanctioned Named Entities Guard</h4>
                      <p className="policy-item-desc">
                        All sensitive individuals and classified project keys have been automatically rerouted to the Disclosure Gate.
                      </p>
                    </div>
                  </div>
                  <div className="policy-card-item">
                    <span className="policy-check-icon"><Icon.Check /></span>
                    <div>
                      <h4 className="policy-item-title">Tone & Audience Calibration</h4>
                      <p className="policy-item-desc">
                        Formality index matches Executive / Senior Leadership specifications with zero sensationalism.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* CRITICAL SECTION D: Disclosure Controls Governance Panel */}
        <section className="disclosure-governance-section" aria-label="Disclosure Controls">
          <div className="disclosure-section-header">
            <div className="disclosure-title-group">
              <span className="disclosure-icon-shield">
                <Icon.Shield />
              </span>
              <div>
                <h2>Disclosure & Sensitivity Controls (Mandatory Human Sign-off)</h2>
                <p style={{ margin: "4px 0 0 0", color: "#9ca3af", fontSize: "0.8125rem" }}>
                  All flagged sensitive entities require an explicit analyst decision before cryptographic ledger approval is unlocked.
                </p>
              </div>
            </div>

            <div className="disclosure-bulk-actions">
              <span
                className={`disclosure-status-pill ${
                  isApprovalReady ? "pill-all-resolved" : "pill-pending-action"
                }`}
              >
                {isApprovalReady ? (
                  <>
                    <Icon.Check />
                    All {disclosureItems.length} Items Resolved
                  </>
                ) : (
                  <>
                    <Icon.AlertTriangle />
                    {disclosureItems.length - unresolvedItems.length} of {disclosureItems.length} Resolved (
                    {unresolvedItems.length} Pending)
                  </>
                )}
              </span>

              <button
                type="button"
                className="btn-bulk-accept"
                onClick={handleBulkAcceptAll}
                title="Stamp all pending items with SriGEN recommended defaults"
              >
                <Icon.Check />
                <span>Accept All Recommendations</span>
              </button>
            </div>
          </div>

          <div className="disclosure-items-container">
            {disclosureItems.map((item) => {
              const choice = item.analyst_choice;
              const isUnresolved = !choice;

              return (
                <div key={item.id} className={`disclosure-card ${isUnresolved ? "is-unresolved" : ""}`}>
                  <div className="disclosure-info-col">
                    <div className="disclosure-meta-row">
                      <span className="disclosure-cat-badge">{item.category}</span>
                      <span className="disclosure-val-text">{item.detected_value_preview}</span>
                      {choice ? (
                        <span
                          style={{
                            fontSize: "0.75rem",
                            color: choice === "disclose" ? "#10b981" : choice === "withhold" ? "#ef4444" : "#3b82f6",
                            fontWeight: 600,
                            textTransform: "uppercase"
                          }}
                        >
                          • Decision: {choice}
                        </span>
                      ) : (
                        <span style={{ fontSize: "0.75rem", color: "#f87171", fontWeight: 600 }}>
                          • Action Required
                        </span>
                      )}
                    </div>
                    <p className="disclosure-reasoning">{item.reasoning}</p>
                    <div className="disclosure-rec-hint">
                      SriGEN Engine Recommendation: <strong>{item.suggested_default.toUpperCase()}</strong>
                    </div>

                    {/* Inline custom edit field */}
                    {editingItemId === item.id && (
                      <div className="disclosure-edit-inline">
                        <input
                          type="text"
                          className="disclosure-edit-input"
                          placeholder="Enter custom redacted / sanitized text..."
                          value={editInputText}
                          onChange={(e) => setEditInputText(e.target.value)}
                        />
                        <button
                          type="button"
                          className="choice-btn selected-edit"
                          onClick={() => handleDisclosureDecision(item.id, "edit", editInputText)}
                          disabled={!editInputText.trim()}
                        >
                          Save Edit
                        </button>
                        <button
                          type="button"
                          className="choice-btn"
                          onClick={() => {
                            setEditingItemId(null);
                            setEditInputText("");
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="disclosure-controls-col">
                    <button
                      type="button"
                      className={`choice-btn ${choice === "disclose" ? "selected-disclose" : ""}`}
                      onClick={() => handleDisclosureDecision(item.id, "disclose")}
                    >
                      Disclose
                    </button>
                    <button
                      type="button"
                      className={`choice-btn ${choice === "withhold" ? "selected-withhold" : ""}`}
                      onClick={() => handleDisclosureDecision(item.id, "withhold")}
                    >
                      Withhold
                    </button>
                    <button
                      type="button"
                      className={`choice-btn ${choice === "edit" ? "selected-edit" : ""}`}
                      onClick={() => {
                        setEditingItemId(item.id);
                        setEditInputText(item.manual_edit_text || item.detected_value_preview);
                      }}
                    >
                      <Icon.Edit />
                      <span>Edit</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Section E: Sticky Action Bar at Bottom */}
        <div className="verify-sticky-actionbar">
          <div className="sticky-actionbar-inner">
            <div className="actionbar-left">
              <Link to="/result" className="btn-secondary-action">
                <Icon.ArrowLeft />
                <span>Back to Result</span>
              </Link>
              <Link
                to={`/refine?draftId=${currentDraft.id}`}
                className="btn-secondary-action"
                title="Refine this deliverable with multi-axis controls"
              >
                <Icon.Edit />
                <span>Refine Deliverable</span>
              </Link>
            </div>

            <div className="actionbar-right">
              {!isApprovalReady && (
                <div className="actionbar-gate-warning">
                  <Icon.AlertCircle />
                  <span>Resolve all {unresolvedItems.length} disclosure items before proceeding to approval.</span>
                </div>
              )}

              <button
                type="button"
                className="btn-primary-approval"
                disabled={!isApprovalReady}
                onClick={() => navigate(`/approval?draftId=${currentDraft.id}`)}
              >
                <span>Continue to Approval</span>
                <Icon.ArrowRight />
              </button>
            </div>
          </div>
        </div>

        {/* Verification Staged Modal */}
        {isVerifying && (
          <div className="verify-modal-overlay">
            <div className="verify-modal-card">
              <div className="verify-modal-icon-spinner" />
              <h3 className="verify-modal-title">Verifying Deliverable Content</h3>
              <p className="verify-modal-desc">
                Executing multi-vector audit against canonical source document and institutional policies.
              </p>

              <div className="verify-steps-progression">
                <div className={`step-prog-row ${verificationStage > 1 ? "completed" : verificationStage === 1 ? "active" : ""}`}>
                  <span className="step-prog-icon">{verificationStage > 1 ? <Icon.Check /> : "1."}</span>
                  <span>Extracting factual claims and sensitive named entities...</span>
                </div>
                <div className={`step-prog-row ${verificationStage > 2 ? "completed" : verificationStage === 2 ? "active" : ""}`}>
                  <span className="step-prog-icon">{verificationStage > 2 ? <Icon.Check /> : "2."}</span>
                  <span>Cross-referencing claims against source graph nodes...</span>
                </div>
                <div className={`step-prog-row ${verificationStage > 3 ? "completed" : verificationStage === 3 ? "active" : ""}`}>
                  <span className="step-prog-icon">{verificationStage > 3 ? <Icon.Check /> : "3."}</span>
                  <span>Auditing cross-output consistency across generated formats...</span>
                </div>
                <div className={`step-prog-row ${verificationStage > 4 ? "completed" : verificationStage === 4 ? "active" : ""}`}>
                  <span className="step-prog-icon">{verificationStage > 4 ? <Icon.Check /> : "4."}</span>
                  <span>Evaluating policy constraints and safety guidelines...</span>
                </div>
                <div className={`step-prog-row ${verificationStage === 5 ? "completed" : ""}`}>
                  <span className="step-prog-icon">{verificationStage === 5 ? <Icon.Check /> : "5."}</span>
                  <span>Computing composite Trust Score and assembling audit report...</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
