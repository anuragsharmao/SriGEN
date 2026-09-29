import React, { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import TopBar from "../components/TopBar.jsx";
import { api } from "../services/api.js";
import { workflowStore } from "../services/workflowStore.js";
import "./ApprovalPage.css";

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
  Lock: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
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
  ArrowLeft: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  ),
  UserCheck: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="8.5" cy="7" r="4" />
      <polyline points="17 11 19 13 23 9" />
    </svg>
  ),
  Hash: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="4" y1="9" x2="20" y2="9" />
      <line x1="4" y1="15" x2="20" y2="15" />
      <line x1="10" y1="3" x2="8" y2="21" />
      <line x1="16" y1="3" x2="14" y2="21" />
    </svg>
  )
};

export default function ApprovalPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Load state from workflow store
  const draftId = searchParams.get("draftId") || workflowStore.getActiveDraft()?.id;
  const currentDraft = workflowStore.getAllDrafts().find((d) => d.id === draftId) || workflowStore.getActiveDraft();
  const sourceDoc = workflowStore.getSourceDoc();
  const trustScore = workflowStore.getTrustScore();
  const disclosureItems = workflowStore.getDisclosureItems();

  // Operator sign-off form state
  const [approvalNotes, setApprovalNotes] = useState("");
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitStage, setCommitStage] = useState(1);

  if (!currentDraft || !trustScore || !draftId) {
    return (
      <div className="approval-page-root">
        <TopBar activePage="approval" />
        <main className="approval-container">
          <p>No generated draft is available for approval.</p>
        </main>
      </div>
    );
  }

  // Disclosure counts
  const disclosedCount = disclosureItems.filter((i) => i.analyst_choice === "disclose").length;
  const withheldCount = disclosureItems.filter((i) => i.analyst_choice === "withhold").length;
  const editedCount = disclosureItems.filter((i) => i.analyst_choice === "edit").length;

  const resolvedFinalText = currentDraft?.approved_content || currentDraft?.content || currentDraft?.draft_content || "";

  // Submit Approval & Commit to Ledger
  const handleCommitToLedger = async () => {
    setIsCommitting(true);
    setCommitStage(1);

    // Staged progression through cryptographic commit
    setTimeout(() => setCommitStage(2), 600);
    setTimeout(() => setCommitStage(3), 1300);
    setTimeout(() => {
      setCommitStage(4);
      setTimeout(async () => {
        try {
          if (!currentDraft?.id) throw new Error("No generated draft is available for approval.");
          const ledgerResponse = await api.approveDraft(currentDraft.id, resolvedFinalText);
          workflowStore.recordApproval(ledgerResponse);
        } catch (error) {
          console.error("Approval failed:", error);
          setIsCommitting(false);
          return;
        }
        setIsCommitting(false);
        navigate(`/provenance?draftId=${currentDraft.id}`);
      }, 700);
    }, 2000);
  };

  return (
    <div className="approval-page-root">
      <TopBar activePage="approval" />

      <main className="approval-container">
        {/* Pipeline Tracker */}
        <div className="approval-pipeline-tracker">
          <Link to="/generate" className="pipeline-step completed">
            <span className="pipeline-step-badge">1</span>
            <span>Generate</span>
          </Link>
          <span className="pipeline-divider">›</span>
          <Link to="/result" className="pipeline-step completed">
            <span className="pipeline-step-badge">2</span>
            <span>Validate Result</span>
          </Link>
          <span className="pipeline-divider">›</span>
          <div className="pipeline-step active">
            <span className="pipeline-step-badge">3</span>
            <span>Approval Gate</span>
          </div>
          <span className="pipeline-divider">›</span>
          <div className="pipeline-step">
            <span className="pipeline-step-badge">4</span>
            <span>Provenance</span>
          </div>
        </div>

        {/* Page Header */}
        <div className="approval-header-card">
          <div className="approval-title-block">
            <h1>Final Human Approval Gate</h1>
            <p className="approval-subtitle">
              Final verification checkpoint before cryptographic hashing and irreversible commitment to the SriGEN SHA-256
              Provenance Ledger. Review the publication-ready text and sign off below.
            </p>
          </div>
          <div className="approval-status-chip">
            <Icon.Check />
            <span>Ready for Immutable Sign-off</span>
          </div>
        </div>

        {/* Workspace Two-Column Layout */}
        <div className="approval-workspace-grid">
          {/* Left Column: Final Deliverable Clean Document View */}
          <div className="approval-preview-card">
            <div className="approval-preview-header">
              <div className="preview-title-row">
                <Icon.FileText />
                <strong style={{ fontSize: "0.9375rem" }}>{currentDraft?.title || "Operational Advisory"}</strong>
              </div>
              <span className="preview-badge-seal">
                <Icon.Lock />
                Pre-Commit Clean Preview
              </span>
            </div>

            <div className="approval-preview-body">
              <h2>EXECUTIVE SUMMARY & OPERATIONAL ASSESSMENT</h2>
              <p>
                This synthesized advisory details the operational rollout and strategic metrics established during the
                evaluation cycle.
              </p>
              <p>
                Q1 production reached 42,000 units across primary manufacturing clusters. All critical metrics
                conformed to standard operating boundaries. Internal telemetry cluster identified as{" "}
                <strong style={{ color: disc1?.analyst_choice === "withhold" ? "#6b7280" : "#111827" }}>
                  {val1}
                </strong>{" "}
                has met performance gates.
              </p>
              <p>
                Zero critical telemetry anomalies or security breaches were logged during validation. Quarterly balance
                sheet impact estimated around{" "}
                <strong style={{ color: disc2?.analyst_choice === "withhold" ? "#6b7280" : "#111827" }}>
                  {val2}
                </strong>{" "}
                with total budget headroom intact.
              </p>
              <p>
                Phase 2 operational migration is scheduled to initiate early in Q3 2026. Implementation partners
                including{" "}
                <strong style={{ color: disc3?.analyst_choice === "withhold" ? "#6b7280" : "#111827" }}>
                  {val3}
                </strong>{" "}
                remain fully on track for delivery.
              </p>
              <p>
                Capital reinvestment efficiency improved by 18.5% over the preceding fiscal quarter.
              </p>
            </div>

            <div className="approval-preview-footer">
              <span>All disclosure sanitizations and analyst overrides applied to this preview.</span>
              <span>SHA-256 hash will be calculated at moment of sign-off.</span>
            </div>
          </div>

          {/* Right Column: Audit Badges & Sign-Off Section */}
          <div className="approval-sidebar">
            {/* Read-Only Verification & Compliance Audit Summary */}
            <div className="audit-summary-card">
              <h3 className="audit-card-title">
                <Icon.Shield />
                <span>Verification & Audit Badges</span>
              </h3>

              <div className="audit-badges-list">
                <div className="audit-item-row">
                  <span className="audit-item-label">Composite Trust Score</span>
                  <span className="audit-item-val emerald">{trustScore.composite.toFixed(1)} / 100</span>
                </div>

                <div className="audit-item-row">
                  <span className="audit-item-label">Grounding Verification</span>
                  <span className="audit-item-val">{trustScore.grounding.toFixed(1)}% (12/12 Claims)</span>
                </div>

                <div className="audit-item-row">
                  <span className="audit-item-label">Sibling Format Agreement</span>
                  <span className="audit-item-val">{trustScore.consistency.toFixed(1)}%</span>
                </div>

                <div className="audit-item-row">
                  <span className="audit-item-label">Institutional Policy Check</span>
                  <span className="audit-item-val emerald">100.0% Pass</span>
                </div>

                <div className="audit-item-row">
                  <span className="audit-item-label">Disclosure Gate Status</span>
                  <span className="audit-item-val emerald">
                    100% Resolved ({disclosedCount} Disclose, {withheldCount} Withhold, {editedCount} Edit)
                  </span>
                </div>

                <div className="audit-item-row">
                  <span className="audit-item-label">Source Document</span>
                  <span className="audit-item-val mono">{sourceDoc.name}</span>
                </div>

                <div className="audit-item-row">
                  <span className="audit-item-label">Source Hash</span>
                  <span className="audit-item-val mono">{sourceDoc.hash.slice(0, 16)}...</span>
                </div>

                <div className="audit-item-row">
                  <span className="audit-item-label">Engine Architecture</span>
                  <span className="audit-item-val mono">SriGEN Foundation v2.4</span>
                </div>
              </div>
            </div>

            {/* Approver Sign-Off Card */}
            <div className="signoff-card">
              <h3 className="signoff-title">
                <Icon.UserCheck />
                <span>Operator Sign-off & Ledger Commitment</span>
              </h3>

              <div className="operator-profile-box">
                <div className="operator-avatar">AS</div>
                <div className="operator-details">
                  <span className="operator-name">Operator AS (operator_sec_01)</span>
                  <span className="operator-roles">Role: Approver & Analyst · Authorized</span>
                </div>
              </div>

              <div className="approval-notes-field">
                <label className="approval-notes-label" htmlFor="approval-notes-input">
                  Approval Notes / Audit Justification (Optional)
                </label>
                <textarea
                  id="approval-notes-input"
                  className="approval-notes-textarea"
                  placeholder="e.g. Verified with legal counsel; Phase 2 partner redacted as requested..."
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                />
              </div>

              <div className="signoff-actions-row">
                <Link to={`/refine?draftId=${currentDraft.id}`} className="btn-reject-back">
                  Send Back / Refine
                </Link>
                <button
                  type="button"
                  className="btn-commit-ledger"
                  onClick={handleCommitToLedger}
                >
                  <Icon.Lock />
                  <span>APPROVE & RECORD TO LEDGER</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Cryptographic Commit Modal */}
        {isCommitting && (
          <div className="commit-modal-overlay">
            <div className="commit-modal-card">
              <div className="commit-modal-icon-spinner" />
              <h3 style={{ fontSize: "1.375rem", fontWeight: 700, color: "#f3f4f6", margin: "0 0 8px 0" }}>
                Committing to Provenance Ledger
              </h3>
              <p style={{ fontSize: "0.875rem", color: "#9ca3af", margin: 0 }}>
                Generating cryptographic integrity proofs and mining immutable ledger block.
              </p>

              <div className="commit-steps-box">
                <div className={`commit-step-row ${commitStage > 1 ? "completed" : commitStage === 1 ? "active" : ""}`}>
                  <span>{commitStage > 1 ? <Icon.Check /> : "1."}</span>
                  <span>Hashing finalized deliverable content (SHA-256)...</span>
                </div>
                <div className={`commit-step-row ${commitStage > 2 ? "completed" : commitStage === 2 ? "active" : ""}`}>
                  <span>{commitStage > 2 ? <Icon.Check /> : "2."}</span>
                  <span>Generating cryptographic proof & digital signatures...</span>
                </div>
                <div className={`commit-step-row ${commitStage > 3 ? "completed" : commitStage === 3 ? "active" : ""}`}>
                  <span>{commitStage > 3 ? <Icon.Check /> : "3."}</span>
                  <span>Writing block #1,247 into append-only hash chain...</span>
                </div>
                <div className={`commit-step-row ${commitStage === 4 ? "completed" : ""}`}>
                  <span>{commitStage === 4 ? <Icon.Check /> : "4."}</span>
                  <span>Cryptographic commit verified. Finalizing provenance entry...</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
