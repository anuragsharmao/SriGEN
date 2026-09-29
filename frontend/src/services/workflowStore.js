/**
 * SriGEN Workflow Store
 * 
 * Manages operator workflow state across the canonical pipeline:
 * GENERATE -> RESULT -> VERIFY & REVIEW <-> REFINE -> APPROVE -> PROVE
 * 
 * Persists session state in memory and localStorage for resilient page refresh.
 */

const STORAGE_KEY = "srigen_workflow_session_v2";

const EMPTY_SOURCE = null;

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
          mode: parsed.mode || "generate",
          source: parsed.source || EMPTY_SOURCE,
          batchId: parsed.batchId || "batch_" + Date.now().toString(36),
          factGraph: parsed.factGraph || null,
          drafts: parsed.drafts || [],
          selectedDraftId: parsed.selectedDraftId || (parsed.drafts?.[0]?.id ?? null),
          disclosureDecisions: parsed.disclosureDecisions || {},
          disclosureItems: parsed.disclosureItems || [],
          trustScore: parsed.trustScore || null,
          approvalStatus: parsed.approvalStatus || "pending",
          latestLedgerEntry: parsed.latestLedgerEntry || null,
          currentUserRole: parsed.currentUserRole || null,
        };
      }
    } catch (e) {
      console.warn("Failed to load workflow state from localStorage:", e);
    }

    return {
      mode: "generate",
      source: EMPTY_SOURCE,
      batchId: null,
      factGraph: null,
      drafts: [],
      selectedDraftId: "draft_advisory_01",
      disclosureDecisions: {},
      disclosureItems: [],
      trustScore: null,
      approvalStatus: "pending",
      latestLedgerEntry: null,
      currentUserRole: null,
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
    return this.state.source;
  }

  setSourceDoc(sourceMeta) {
    this.state.source = {
      ...this.state.source,
      ...sourceMeta,
      hash: sourceMeta.hash || this.state.source?.hash || null,
    };
    this.save();
  }

  // Trust score getters & setters
  getTrustScore() {
    return this.state.trustScore;
  }

  setTrustScore(trustScore) {
    this.state.trustScore = trustScore;
    this.save();
  }

  // Drafts management
  getAllDrafts() {
    return this.state.drafts || [];
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

  // Workflow mode: "generate" | "refine"
  getMode() {
    return this.state.mode || "generate";
  }

  setMode(mode) {
    this.state.mode = mode;
    this.save();
  }

  // Updates from generation run
  setGenerationResult(generateResponse, sourceMeta = null, mode = "generate") {
    this.state.mode = mode;
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
      this.state.trustScore = generateResponse.trust_score;
    }

    if (generateResponse.drafts && Array.isArray(generateResponse.drafts)) {
      this.state.drafts = generateResponse.drafts;
      this.state.selectedDraftId = generateResponse.drafts[0]?.id || null;
    }

    // Reset decisions for new generation
    this.state.disclosureDecisions = {};
    this.state.disclosureItems = generateResponse.disclosure_items || [];
    this.state.approvalStatus = "pending";
    this.state.latestLedgerEntry = null;
    this.save();
  }

  // Updates from refinement run
  setRefineResult(refineResult, sourceMeta = null) {
    this.state.mode = "refine";
    if (sourceMeta) {
      this.state.source = {
        ...this.state.source,
        ...sourceMeta,
      };
    } else if (refineResult.source_id) {
      this.state.source = {
        ...this.state.source,
        id: refineResult.source_id,
        hash: refineResult.source_hash || this.state.source?.hash,
      };
    }

    if (refineResult.batch_id) {
      this.state.batchId = refineResult.batch_id;
    }
    if (refineResult.fact_graph) {
      this.state.factGraph = refineResult.fact_graph;
    }
    if (refineResult.trust_score) {
      this.state.trustScore = refineResult.trust_score;
    }

    if (refineResult.drafts && Array.isArray(refineResult.drafts)) {
      this.state.drafts = refineResult.drafts;
      this.state.selectedDraftId = refineResult.drafts[0]?.id || null;
    }

    this.state.disclosureDecisions = {};
    this.state.disclosureItems = refineResult.disclosure_items || [];
    this.state.approvalStatus = "pending";
    this.state.latestLedgerEntry = null;
    this.save();
  }

  // Disclosure controls management
  getDisclosureItems() {
    const items = this.state.disclosureItems || [];
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
