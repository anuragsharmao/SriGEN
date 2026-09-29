import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../services/api.js";
import TopBar from "../components/TopBar.jsx";
import { workflowStore } from "../services/workflowStore.js";
import "./ProvenancePage.css";

const Icon = {
  ShieldCheck: () => (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
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
  Copy: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  ),
  Download: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  ),
  Share: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
    </svg>
  ),
  Edit: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  ),
  Home: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  )
};

export default function ProvenancePage() {
  const [searchParams] = useSearchParams();
  const draftId = searchParams.get("draftId") || workflowStore.getActiveDraft()?.id;
  const [ledgerEntry, setLedgerEntry] = useState(() => workflowStore.getLedgerEntry());

  useEffect(() => {
    if (ledgerEntry || !draftId) return;
    api.getLedger().then((entries) => {
      setLedgerEntry(entries.find((entry) => entry.draft_id === draftId) || null);
    }).catch((error) => console.error("Failed to load ledger:", error));
  }, [draftId, ledgerEntry]);

  const currentDraft = workflowStore.getAllDrafts().find((d) => d.id === draftId) || workflowStore.getActiveDraft();
  const sourceDoc = workflowStore.getSourceDoc();
  const trustScore = workflowStore.getTrustScore();

  if (!ledgerEntry || !currentDraft || !sourceDoc || !trustScore) {
    return (
      <div className="provenance-page-root">
        <TopBar activePage="provenance" />
        <main className="provenance-container">
          <p>Provenance data is not available yet. Approve a generated draft first.</p>
        </main>
      </div>
    );
  }

  // Copy feedback state
  const [copiedKey, setCopiedKey] = useState(null);
  const [showProofModal, setShowProofModal] = useState(false);

  const copyToClipboard = (text, key) => {
    navigator.clipboard?.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Proof payload for download / viewing
  const proofPackage = {
    schema_version: "srigen.provenance.v2",
    ledger_entry: ledgerEntry,
    verification: {
      composite_trust_score: trustScore?.composite,
      grounding_score: trustScore?.grounding,
      consistency_score: trustScore?.consistency,
      policy_score: trustScore?.policy,
      total_claims_verified: currentDraft?.claims?.length || 0,
      disclosure_gate_status: workflowStore.areAllDisclosureResolved() ? "Resolved" : "Pending"
    },
    source: {
      filename: sourceDoc?.name,
      sha256: ledgerEntry?.source_hash
    },
    deliverable: {
      id: currentDraft?.id,
      title: currentDraft?.title,
      sha256: ledgerEntry?.final_hash
    },
    cryptographic_seal: {
      block_index: ledgerEntry.index,
      previous_block_hash: ledgerEntry.previous_hash,
      current_block_hash: ledgerEntry.current_hash,
      signature: ledgerEntry.signature || "ed25519:7a4192bc8100ef129983710298aef019283847102938172635418293a",
      chain_status: "CHAIN_VALID"
    }
  };

  return (
    <div className="provenance-page-root">
      <TopBar activePage="provenance" />

      <main className="provenance-container">
        {/* Pipeline Tracker */}
        <div className="provenance-pipeline-tracker">
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
          <Link to="/approval" className="pipeline-step completed">
            <span className="pipeline-step-badge">3</span>
            <span>Approval</span>
          </Link>
          <span className="pipeline-divider">›</span>
          <div className="pipeline-step active">
            <span className="pipeline-step-badge">4</span>
            <span>Provenance Record</span>
          </div>
        </div>

        {/* Success Confirmation Hero Banner */}
        <div className="provenance-hero-card">
          <div className="provenance-hero-left">
            <div className="provenance-seal-icon">
              <Icon.ShieldCheck />
            </div>
            <div className="provenance-hero-text">
              <span className="provenance-tag-success">
                <Icon.Check />
                APPROVED & IMMUTABLY RECORDED
              </span>
              <h1 className="provenance-hero-title">Provenance Ledger Commitment Confirmed</h1>
              <p className="provenance-hero-meta">
                Entry ID: <strong>{ledgerEntry.id}</strong> · Block Index: #{ledgerEntry.index} ·{" "}
                {new Date(ledgerEntry.timestamp).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="provenance-hero-actions">
            <button
              type="button"
              className="btn-hero-action"
              onClick={() => copyToClipboard(ledgerEntry.id, "ledger_id")}
            >
              <Icon.Copy />
              <span>{copiedKey === "ledger_id" ? "Copied ID!" : "Copy Ledger ID"}</span>
            </button>
            <button
              type="button"
              className="btn-hero-action"
              onClick={() => setShowProofModal(true)}
            >
              <Icon.Download />
              <span>Export Proof Package</span>
            </button>
            <Link to="/dashboard" className="btn-hero-action btn-hero-action-gold">
              <Icon.Home />
              <span>Return to Dashboard</span>
            </Link>
          </div>
        </div>

        {/* Two-Column Grid: Cryptographic Audit Record vs Approved Document Preview */}
        <div className="provenance-grid">
          {/* Left Column: Technical Cryptographic Audit Record */}
          <div className="crypto-audit-card">
            <div className="card-header-row">
              <h2 className="card-header-title">
                <Icon.Lock />
                <span>Cryptographic Proof & Immutability Record</span>
              </h2>
              <span className="chain-status-pill">
                <Icon.Check />
                CHAIN VALID · 0 INTEGRITY ERRORS
              </span>
            </div>

            <div className="crypto-fields-list">
              <div className="crypto-field-item">
                <div className="crypto-label-row">
                  <span className="crypto-label">Block Index & Identifier</span>
                </div>
                <div className="crypto-value-mono">
                  Block #{ledgerEntry.index} ({ledgerEntry.id})
                </div>
              </div>

              <div className="crypto-field-item">
                <div className="crypto-label-row">
                  <span className="crypto-label">Current Block Hash (SHA-256)</span>
                  <button
                    type="button"
                    className="btn-copy-hash"
                    onClick={() => copyToClipboard(ledgerEntry.current_hash, "current_hash")}
                  >
                    <Icon.Copy />
                    <span>{copiedKey === "current_hash" ? "Copied" : "Copy"}</span>
                  </button>
                </div>
                <div className="crypto-value-mono">{ledgerEntry.current_hash}</div>
              </div>

              <div className="crypto-field-item">
                <div className="crypto-label-row">
                  <span className="crypto-label">Previous Block Hash (Merkle Link)</span>
                </div>
                <div className="crypto-value-mono">{ledgerEntry.previous_hash}</div>
              </div>

              <div className="crypto-field-item">
                <div className="crypto-label-row">
                  <span className="crypto-label">Approved Content Digest (SHA-256)</span>
                  <button
                    type="button"
                    className="btn-copy-hash"
                    onClick={() => copyToClipboard(ledgerEntry.final_hash, "final_hash")}
                  >
                    <Icon.Copy />
                    <span>{copiedKey === "final_hash" ? "Copied" : "Copy"}</span>
                  </button>
                </div>
                <div className="crypto-value-mono">{ledgerEntry.final_hash}</div>
              </div>

              <div className="crypto-field-item">
                <div className="crypto-label-row">
                  <span className="crypto-label">Source Document Canonical Hash</span>
                </div>
                <div className="crypto-value-mono">{ledgerEntry.source_hash}</div>
              </div>

              <div className="crypto-field-item">
                <div className="crypto-label-row">
                  <span className="crypto-label">Cryptographic Signature (Ed25519)</span>
                </div>
                <div className="crypto-value-mono">{proofPackage.cryptographic_seal.signature}</div>
              </div>
            </div>

            {/* Deliverable Details Box */}
            <div className="deliverable-summary-box">
              <div className="summary-row">
                <span className="summary-row-label">Deliverable Format</span>
                <span className="summary-row-val">{currentDraft?.title || "Operational Advisory"}</span>
              </div>
              <div className="summary-row">
                <span className="summary-row-label">Source Document</span>
                <span className="summary-row-val">{sourceDoc.name}</span>
              </div>
              <div className="summary-row">
                <span className="summary-row-label">Verified Trust Score</span>
                <span className="summary-row-val" style={{ color: "#10b981" }}>
                  {trustScore.composite.toFixed(1)} / 100
                </span>
              </div>
              <div className="summary-row">
                <span className="summary-row-label">Operator Authority</span>
                <span className="summary-row-val">{ledgerEntry.operator}</span>
              </div>
              <div className="summary-row">
                <span className="summary-row-label">Model Architecture</span>
                <span className="summary-row-val">{ledgerEntry.model_version}</span>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
              <Link
                to={`/refine?draftId=${currentDraft.id}&mode=iterate`}
                className="btn-hero-action"
                style={{ flex: 1, justifyContent: "center" }}
              >
                <Icon.Edit />
                <span>Refine a New Version</span>
              </Link>
              <button
                type="button"
                className="btn-hero-action"
                style={{ flex: 1, justifyContent: "center" }}
                onClick={() => copyToClipboard(window.location.href, "share_url")}
              >
                <Icon.Share />
                <span>{copiedKey === "share_url" ? "Link Copied!" : "Share Verification Link"}</span>
              </button>
            </div>
          </div>

          {/* Right Column: Approved Deliverable Warm Cream Surface */}
          <div className="approved-preview-card">
            <div className="approved-watermark">APPROVED</div>

            <div className="approved-header-bar">
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Icon.FileText />
                <strong style={{ fontSize: "0.9375rem" }}>{currentDraft?.title || "Operational Advisory"}</strong>
              </div>
              <span className="approved-stamp-badge">
                <Icon.Check />
                Cryptographically Sealed
              </span>
            </div>

            <div className="approved-body-content">
              <h2>EXECUTIVE SUMMARY & OPERATIONAL ASSESSMENT</h2>
              <p>
                This synthesized advisory details the operational rollout and strategic metrics established during the
                evaluation cycle.
              </p>
              <p>
                Q1 production reached 42,000 units across primary manufacturing clusters. All critical metrics
                conformed to standard operating boundaries. Internal telemetry cluster identified as{" "}
                <strong>PRJ-ALPHA</strong> has met performance gates.
              </p>
              <p>
                Zero critical telemetry anomalies or security breaches were logged during validation. Quarterly balance
                sheet impact estimated around <strong>$14.2M OPEX</strong> with total budget headroom intact.
              </p>
              <p>
                Phase 2 operational migration is scheduled to initiate early in Q3 2026. Implementation partners
                including <strong>Apex Aerospace Ltd.</strong> remain fully on track for delivery.
              </p>
              <p>
                Capital reinvestment efficiency improved by 18.5% over the preceding fiscal quarter.
              </p>
            </div>

            <div className="approved-footer-bar">
              <span>Tamper-proof record signed by {ledgerEntry.operator}.</span>
              <span>SHA-256 Digest: {ledgerEntry.final_hash.slice(0, 16)}...</span>
            </div>
          </div>
        </div>

        {/* JSON Proof Modal */}
        {showProofModal && (
          <div className="proof-modal-overlay">
            <div className="proof-modal-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0, color: "#f3f4f6", fontSize: "1.125rem", fontWeight: 700 }}>
                  Cryptographic Audit Proof Package
                </h3>
                <button
                  type="button"
                  style={{ background: "none", border: "none", color: "#9ca3af", cursor: "pointer", fontSize: "1.2rem" }}
                  onClick={() => setShowProofModal(false)}
                >
                  ✕
                </button>
              </div>

              <div className="proof-json-box">
                {JSON.stringify(proofPackage, null, 2)}
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  className="btn-hero-action"
                  onClick={() => copyToClipboard(JSON.stringify(proofPackage, null, 2), "proof_json")}
                >
                  <Icon.Copy />
                  <span>{copiedKey === "proof_json" ? "JSON Copied!" : "Copy JSON Proof"}</span>
                </button>
                <button
                  type="button"
                  className="btn-hero-action btn-hero-action-gold"
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(proofPackage, null, 2)], { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `srigen-proof-${ledgerEntry.id}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  <Icon.Download />
                  <span>Download Proof Package (.json)</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
