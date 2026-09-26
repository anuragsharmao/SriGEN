/**
 * SriGEN Workflow Store
 * 
 * Manages operator workflow state across the canonical pipeline:
 * GENERATE -> RESULT -> VERIFY & REVIEW <-> REFINE -> APPROVE -> PROVE
 * 
 * Persists session state in memory and localStorage for resilient page refresh.
 */

const STORAGE_KEY = "srigen_workflow_session_v1";

const DEFAULT_SOURCE = {
  id: "SRC-0241",
  name: "incident_telemetry_report.pdf",
  size: "2.4 MB",
  type: "PDF",
  hash: "8f4e2c091ad578b3ce3c8591ef14032d1894bfa293e62df947702fbe1364d9b1",
  text: "",
};

const DEFAULT_TRUST_SCORE = {
  composite: 96.4,
  grounding: 98.2,
  consistency: 95.0,
  policy: 100.0,
  formula_explanation: "Trust Index = (50% Grounding) + (30% Consistency) + (20% Policy).",
};

const DEFAULT_DISCLOSURE_ITEMS = [
  {
    id: "disc_1",
    draft_id: "draft_advisory_01",
    placeholder: "[INTERNAL_ID: PRJ-ALPHA]",
    category: "INTERNAL_IDENTIFIER",
    detected_value_preview: "PRJ-ALPHA",
    confidence: 0.98,
    reasoning: "Internal operational codename detected; unreleased publicly.",
    suggested_default: "disclose",
    analyst_choice: null,
    manual_edit_text: null,
    group_key: "group_internal_id",
  },
  {
    id: "disc_2",
    draft_id: "draft_advisory_01",
    placeholder: "[REVENUE_METRIC: $14.2M]",
    category: "FINANCIAL_FIGURE",
    detected_value_preview: "$14.2M OPEX",
    confidence: 0.95,
    reasoning: "Exact OPEX expenditure figure subject to institutional embargo.",
    suggested_default: "withhold",
    analyst_choice: null,
    manual_edit_text: null,
    group_key: "group_financial",
  },
  {
    id: "disc_3",
    draft_id: "draft_advisory_01",
    placeholder: "[VENDOR_NAME: Apex Aerospace Ltd.]",
    category: "VENDOR_PARTNER",
    detected_value_preview: "Apex Aerospace Ltd.",
    confidence: 0.99,
    reasoning: "Commercial partner name mentioned; NDA status pending verification.",
    suggested_default: "disclose",
    analyst_choice: null,
    manual_edit_text: null,
    group_key: "group_vendor",
  },
];

class WorkflowStore {
  constructor() {
    this.listeners = new Set();
    this.state = this.loadInitialState();
  }

  loadInitialState() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          source: parsed.source || DEFAULT_SOURCE,
          batchId: parsed.batchId || "batch_" + Date.now().toString(36),
          factGraph: parsed.factGraph || null,
          drafts: parsed.drafts || [],
          selectedDraftId: parsed.selectedDraftId || (parsed.drafts?.[0]?.id ?? "draft_advisory_01"),
          disclosureDecisions: parsed.disclosureDecisions || {},
          disclosureItems: parsed.disclosureItems || DEFAULT_DISCLOSURE_ITEMS,
          trustScore: parsed.trustScore || DEFAULT_TRUST_SCORE,
          approvalStatus: parsed.approvalStatus || "pending",
          latestLedgerEntry: parsed.latestLedgerEntry || null,
          currentUserRole: parsed.currentUserRole || "approver",
        };
      }
    } catch (e) {
      console.warn("Failed to load workflow state from localStorage:", e);
    }

    return {
      source: DEFAULT_SOURCE,
      batchId: "batch_" + Date.now().toString(36),
      factGraph: null,
      drafts: [
        {
          id: "draft_advisory_01",
          title: "Operational Advisory",
          deliverable_type: "advisory",
          status: "Generated · Verification Passed",
          content: `EXECUTIVE SUMMARY & OPERATIONAL ASSESSMENT\n\nThis synthesized advisory details the operational rollout and strategic metrics established during the evaluation cycle.\n\nQ1 production reached 42,000 units across primary manufacturing clusters. All critical metrics conformed to standard operating boundaries. Internal telemetry cluster identified as PRJ-ALPHA has met performance gates.\n\nZero critical telemetry anomalies or security breaches were logged during validation. Quarterly balance sheet impact estimated around $14.2M OPEX with total budget headroom intact.\n\nPhase 2 operational migration is scheduled to initiate early in Q3 2026. Implementation partners including Apex Aerospace Ltd. remain fully on track for delivery.\n\nCapital reinvestment efficiency improved by 18.5% over the preceding fiscal quarter.`,
          format_tags: ["Advisory", "English", "Leadership"],
          reading_time: "2 min read",
          word_count: 142,
        },
      ],
      selectedDraftId: "draft_advisory_01",
      disclosureDecisions: {},
      disclosureItems: DEFAULT_DISCLOSURE_ITEMS,
      trustScore: DEFAULT_TRUST_SCORE,
      approvalStatus: "pending",
      latestLedgerEntry: null,
      currentUserRole: "approver",
    };
  }

  save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch (e) {
      console.warn("Failed to persist workflow state:", e);
    }
    this.notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify() {
    for (const listener of this.listeners) {
      try {
        listener(this.state);
      } catch (e) {
        console.error("Workflow listener error:", e);
      }
    }
  }

  getState() {
    return this.state;
  }

  // Source document getters & setters
  getSourceDoc() {
    return this.state.source || DEFAULT_SOURCE;
  }

  setSourceDoc(sourceMeta) {
    this.state.source = {
      ...this.state.source,
      ...sourceMeta,
      hash: sourceMeta.hash || this.state.source?.hash || "8f4e2c091ad578b3ce3c8591ef14032d1894bfa293e62df947702fbe1364d9b1",
    };
    this.save();
  }

  // Trust score getters & setters
  getTrustScore() {
    return this.state.trustScore || DEFAULT_TRUST_SCORE;
  }

  setTrustScore(trustScore) {
    this.state.trustScore = trustScore;
    this.save();
  }

  // Drafts management
  getAllDrafts() {
    if (this.state.drafts && this.state.drafts.length > 0) {
      return this.state.drafts;
    }
    return [
      {
        id: "draft_advisory_01",
        title: "Operational Advisory",
        deliverable_type: "advisory",
        status: "Generated · Verification Passed",
        content: `EXECUTIVE SUMMARY & OPERATIONAL ASSESSMENT\n\nThis synthesized advisory details the operational rollout and strategic metrics established during the evaluation cycle.\n\nQ1 production reached 42,000 units across primary manufacturing clusters. All critical metrics conformed to standard operating boundaries. Internal telemetry cluster identified as PRJ-ALPHA has met performance gates.\n\nZero critical telemetry anomalies or security breaches were logged during validation. Quarterly balance sheet impact estimated around $14.2M OPEX with total budget headroom intact.\n\nPhase 2 operational migration is scheduled to initiate early in Q3 2026. Implementation partners including Apex Aerospace Ltd. remain fully on track for delivery.\n\nCapital reinvestment efficiency improved by 18.5% over the preceding fiscal quarter.`,
        format_tags: ["Advisory", "English", "Leadership"],
        reading_time: "2 min read",
        word_count: 142,
      },
    ];
  }

  getActiveDraft() {
    const drafts = this.getAllDrafts();
    return drafts.find((d) => d.id === this.state.selectedDraftId) || drafts[0] || null;
  }

  setActiveDraft(draftId) {
    this.state.selectedDraftId = draftId;
    this.save();
  }

  setSelectedDraftId(draftId) {
    this.setActiveDraft(draftId);
  }

  updateDraftContent(draftId, updatedContent) {
    const draft = this.state.drafts.find((d) => d.id === draftId);
    if (draft) {
      draft.content = updatedContent;
      draft.draft_content = updatedContent;
      this.save();
    }
  }

  // Updates from generation run
  setGenerationResult(generateResponse, sourceMeta = null) {
    if (sourceMeta) {
      this.state.source = {
        ...this.state.source,
        ...sourceMeta,
      };
    } else if (generateResponse.source_id) {
      this.state.source = {
        ...this.state.source,
        id: generateResponse.source_id,
        hash: generateResponse.source_hash || this.state.source.hash,
      };
    }

    if (generateResponse.batch_id) {
      this.state.batchId = generateResponse.batch_id;
    }
    if (generateResponse.fact_graph) {
      this.state.factGraph = generateResponse.fact_graph;
    }
    if (generateResponse.trust_score) {
      this.state.trustScore = {
        ...DEFAULT_TRUST_SCORE,
        ...generateResponse.trust_score,
      };
    }

    if (generateResponse.drafts && Array.isArray(generateResponse.drafts)) {
      this.state.drafts = generateResponse.drafts;
      this.state.selectedDraftId = generateResponse.drafts[0]?.id || "draft_01";
    }

    // Reset decisions for new generation
    this.state.disclosureDecisions = {};
    this.state.disclosureItems = DEFAULT_DISCLOSURE_ITEMS.map((item) => ({
      ...item,
      analyst_choice: null,
      manual_edit_text: null,
    }));
    this.state.approvalStatus = "pending";
    this.state.latestLedgerEntry = null;
    this.save();
  }

  // Disclosure controls management
  getDisclosureItems() {
    const items = this.state.disclosureItems || DEFAULT_DISCLOSURE_ITEMS;
    return items.map((item) => {
      const decision = this.state.disclosureDecisions[item.id];
      if (decision) {
        return {
          ...item,
          analyst_choice: decision.choice,
          manual_edit_text: decision.manualEditText,
        };
      }
      return item;
    });
  }

  setDisclosureDecision(itemId, choice, manualEditText = null) {
    this.state.disclosureDecisions[itemId] = {
      choice,
      manualEditText,
      decidedAt: new Date().toISOString(),
    };
    // Also sync to items array
    if (this.state.disclosureItems) {
      const idx = this.state.disclosureItems.findIndex((i) => i.id === itemId);
      if (idx !== -1) {
        this.state.disclosureItems[idx].analyst_choice = choice;
        this.state.disclosureItems[idx].manual_edit_text = manualEditText;
      }
    }
    this.save();
  }

  bulkAcceptAllDisclosure() {
    const items = this.getDisclosureItems();
    for (const item of items) {
      this.state.disclosureDecisions[item.id] = {
        choice: item.suggested_default,
        manualEditText: null,
        decidedAt: new Date().toISOString(),
      };
      if (this.state.disclosureItems) {
        const idx = this.state.disclosureItems.findIndex((i) => i.id === item.id);
        if (idx !== -1) {
          this.state.disclosureItems[idx].analyst_choice = item.suggested_default;
          this.state.disclosureItems[idx].manual_edit_text = null;
        }
      }
    }
    this.save();
  }

  areAllDisclosureResolved() {
    const items = this.getDisclosureItems();
    return items.every((i) => i.analyst_choice !== null && i.analyst_choice !== undefined);
  }

  // Approval & Ledger management
  recordApproval(ledgerEntry) {
    this.state.approvalStatus = "approved";
    this.state.latestLedgerEntry = ledgerEntry;
    const active = this.getActiveDraft();
    if (active) {
      active.status = "approved";
      active.approved_content = ledgerEntry.final_hash ? active.content : active.content;
    }
    this.save();
  }

  setApproved(ledgerEntry) {
    this.recordApproval(ledgerEntry);
  }

  getLedgerEntry() {
    return this.state.latestLedgerEntry;
  }

  getApprovedContent() {
    const active = this.getActiveDraft();
    return active?.approved_content || active?.content || "";
  }

  setCurrentUserRole(role) {
    this.state.currentUserRole = role;
    this.save();
  }

  reset() {
    localStorage.removeItem(STORAGE_KEY);
    this.state = this.loadInitialState();
    this.notify();
  }
}

export const workflowStore = new WorkflowStore();
export default workflowStore;
