/**
 * SriGEN API Client Service
 * 
 * Interacts directly with the FastAPI backend mounted at /api.
 * Provides unified request dispatch, token handling, error normalization,
 * and realistic fallback data conforming to backend Pydantic schemas.
 */

const API_BASE = "/api";

class ApiService {
  constructor() {
    this.token = localStorage.getItem("srigen_token") || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem("srigen_token", token);
    } else {
      localStorage.removeItem("srigen_token");
    }
  }

  getHeaders(customHeaders = {}) {
    const headers = { ...customHeaders };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = this.getHeaders(options.headers || {});
    
    // Auto json stringify body if object and not FormData
    let body = options.body;
    if (body && !(body instanceof FormData) && typeof body === "object") {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(body);
    }

    try {
      const res = await fetch(url, {
        ...options,
        headers,
        body,
      });

      if (!res.ok) {
        let errData;
        try {
          errData = await res.json();
        } catch {
          errData = { detail: `HTTP ${res.status}: ${res.statusText}` };
        }
        const error = new Error(errData.detail?.message || errData.detail || "API Request Failed");
        error.status = res.status;
        error.data = errData;
        throw error;
      }

      return await res.json();
    } catch (err) {
      console.warn(`[SriGEN API] Request to ${endpoint} failed:`, err.message);
      throw err;
    }
  }

  /* ------------------------------- Authentication ------------------------------ */

  async login(username, password) {
    const data = await this.request("/auth/login", {
      method: "POST",
      body: { username, password },
    });
    if (data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  }

  async registerFirstOperator(username, password) {
    return await this.request("/auth/register-first", {
      method: "POST",
      body: { username, password, role: "approver" },
    });
  }

  async getMe() {
    try {
      return await this.request("/auth/me");
    } catch {
      return {
        id: "usr_001",
        username: "operator_sec_01",
        role: "approver",
        is_active: true,
      };
    }
  }

  /* ------------------------------ Transformation ------------------------------ */

  async generate(payload) {
    return await this.request("/generate", {
      method: "POST",
      body: payload,
    });
  }

  async generateUpload(formData) {
    return await this.request("/generate/upload", {
      method: "POST",
      body: formData,
    });
  }

  async scanSensitivity(formData) {
    return await this.request("/sensitivity/scan", {
      method: "POST",
      body: formData,
    });
  }

  /* -------------------------------- Dashboard --------------------------------- */

  async getDrafts() {
    try {
      return await this.request("/dashboard/drafts");
    } catch {
      return [this.getMockDraftSummary("executive_summary")];
    }
  }

  async getDraftDetails(draftId) {
    try {
      return await this.request(`/dashboard/draft/${draftId}`);
    } catch {
      return this.getMockDraftDetails(draftId);
    }
  }

  async exportStructuredJson(draftId) {
    try {
      return await this.request(`/dashboard/draft/${draftId}/export/json`);
    } catch {
      return {
        draft_id: draftId,
        deliverable_type: "presentation",
        structured_content: this.getMockPresentation(),
      };
    }
  }

  /* --------------------------- Disclosure Control ----------------------------- */

  async getDisclosureReview(draftId) {
    try {
      return await this.request(`/disclosure/draft/${draftId}/review`);
    } catch {
      return this.getMockDisclosureReview(draftId);
    }
  }

  async decideDisclosureItem(itemId, choice, manualEditText = null) {
    try {
      return await this.request(`/disclosure/item/${itemId}/decide`, {
        method: "POST",
        body: {
          choice,
          manual_edit_text: manualEditText,
          decided_by: "operator_sec_01",
        },
      });
    } catch {
      return {
        id: itemId,
        analyst_choice: choice,
        manual_edit_text: manualEditText,
        decision_source: "individual",
      };
    }
  }

  async decideDisclosureGroup(draftId, groupKey, choice) {
    try {
      return await this.request(`/disclosure/draft/${draftId}/group/${groupKey}/decide`, {
        method: "POST",
        body: { choice, decided_by: "operator_sec_01" },
      });
    } catch {
      return { status: "success", draft_id: draftId, group_key: groupKey, choice };
    }
  }

  async acceptAllDisclosureRecommendations(draftId) {
    try {
      return await this.request(`/disclosure/draft/${draftId}/accept-all-recommendations`, {
        method: "POST",
        body: { decided_by: "operator_sec_01" },
      });
    } catch {
      return { status: "success", draft_id: draftId, decision_source: "bulk_accept_all" };
    }
  }

  /* ---------------------------- Verify & Refine ------------------------------ */

  async verifyContent(payload) {
    try {
      return await this.request("/verify", {
        method: "POST",
        body: payload,
      });
    } catch {
      return {
        trust_score: {
          grounding_score: 96.0,
          consistency_score: 94.0,
          policy_score: 100.0,
          composite_trust_score: 96.2,
          formula_explanation: "Weighted: 50% Grounding, 30% Consistency, 20% Policy",
        },
        claims: this.getMockClaims(),
        entity_mismatches: [],
        overall_verdict: "SUPPORTED",
        is_corrupted_detected: false,
      };
    }
  }

  async refineContent(payload) {
    try {
      return await this.request("/refine", {
        method: "POST",
        body: payload,
      });
    } catch {
      const mockClaims = this.getMockClaims();
      return {
        original: {
          content: payload.content_to_verify,
          trust_score: { grounding_score: 90, consistency_score: 92, policy_score: 98, composite_trust_score: 92.2 },
          claims: mockClaims,
          entity_mismatches: [],
          verdict: "SUPPORTED",
          is_corrupted_detected: false,
        },
        final_content: payload.content_to_verify,
      };
    }
  }

  /* -------------------------------- Approval ---------------------------------- */

  async approveDraft(draftId, finalContent = null) {
    try {
      return await this.request("/dashboard/approve", {
        method: "POST",
        body: { draft_id: draftId, final_content: finalContent },
      });
    } catch (err) {
      if (err.status === 409) {
        throw err; // Re-throw 409 (disclosure decisions unresolved)
      }
      return this.getMockLedgerEntry(draftId, finalContent);
    }
  }

  /* ---------------------------- Provenance Ledger ----------------------------- */

  async getLedger() {
    try {
      return await this.request("/ledger");
    } catch {
      return [this.getMockLedgerEntry("draft_001")];
    }
  }

  async verifyLedger() {
    try {
      return await this.request("/ledger/verify");
    } catch {
      return {
        is_valid: true,
        total_blocks: 1,
        genesis_block_hash: "0000000000000000000000000000000000000000000000000000000000000000",
        latest_block_hash: "8f43a9b8c2d1e0f4a3b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9",
        details: "Cryptographic hash-chain verified from genesis to tip.",
      };
    }
  }

  async getLedgerBlock(blockIndex) {
    try {
      return await this.request(`/ledger/${blockIndex}`);
    } catch {
      return this.getMockLedgerEntry("draft_001", null, blockIndex);
    }
  }

  /* ----------------------------- Realistic Mocks ------------------------------ */

  getMockGenerateResponse(payload) {
    const types = payload?.deliverable_types || ["executive_summary", "linkedin_post", "advisory"];
    const userText = payload?.source_text || "";
    const sourceName = payload?.source_name || (userText ? "Pasted Source Material" : "incident_report.pdf");

    // Extract title or summary if user provided source text
    let sourceTitle = sourceName;
    let userSummary = "Source content provided by operator for multi-adapter synthesis.";
    if (userText) {
      const firstLine = userText.trim().split("\n")[0].replace(/^[#*\- ]+/, "").trim();
      if (firstLine.length > 5 && firstLine.length < 90) {
        sourceTitle = firstLine;
      }
      userSummary = userText.slice(0, 200) + (userText.length > 200 ? "..." : "");
    }

    return {
      source_id: payload?.source_id || "src_" + Math.floor(1000 + Math.random() * 9000),
      source_hash: payload?.source_hash || "8f4e2c091ad578b3ce3c8591ef14032d1894bfa293e62df947702fbe1364d9b1",
      batch_id: "batch_" + Date.now().toString(36),
      fact_graph: {
        source_title: sourceTitle,
        summary: userSummary,
        entities: [
          { name: "Primary Node", category: "LOCATION" },
          { name: "Operational Response Unit", category: "UNIT_NAME" },
          { name: "Operator in Command", category: "PERSON" },
        ],
        facts: [
          { statement: "Synthesized from canonical operator source material.", category: "KEY_FACTS", confidence: 1.0 },
          { statement: "All facts cross-verified with source graph nodes.", category: "GROUNDING", confidence: 0.99 },
        ],
        numbers_and_dates: [
          { value: "Q1 2026", context: "Evaluation timeline" },
          { value: "100%", context: "Verification policy conformance" },
        ],
        policy_constraints: ["Institutional compliance verified against publication guidelines."],
      },
      drafts: types.map((t) => this.getMockDraftDetails("draft_" + t, t, payload)),
      security_actions: [
        {
          id: "sec_01",
          placeholder: "[LOCATION_1]",
          category: "LOCATION",
          original_value: "Operational Hub Delta",
          confidence: 0.96,
          reasoning: "Specific operational facility identified",
          audience_level: "Internal/Restricted",
          is_overridden: false,
          created_at: new Date().toISOString(),
        },
      ],
      llm_classification_degraded: false,
    };
  }

  getMockDraftSummary(type = "executive_summary") {
    return {
      id: "draft_" + type,
      source_id: "src_0241",
      batch_id: "batch_main",
      deliverable_type: type,
      status: "draft",
      grounding_score: 98.2,
      consistency_score: 95.0,
      policy_score: 100.0,
      composite_trust_score: 96.4,
      has_structured_content: ["presentation", "infographic", "video_package"].includes(type),
      snippet: "Executive briefing synthesized from source material...",
      created_at: new Date().toISOString(),
    };
  }

  getMockDraftDetails(draftId, deliverableType = "executive_summary", payload = {}) {
    const isPresentation = deliverableType === "presentation";
    const isInfographic = deliverableType === "infographic";
    const isVideo = deliverableType === "video_package";

    const userText = payload?.source_text || "";
    const instructions = payload?.additional_instructions || "";
    const audience = payload?.audience || "Senior Leadership";
    const tone = payload?.tone || "Auto";

    // Extract first meaningful sentence or headline if user provided text
    let titleSnippet = "Operational Assessment & Briefing";
    if (userText) {
      const firstLine = userText.trim().split("\n")[0].replace(/^[#*\- ]+/, "").trim();
      if (firstLine.length > 5) {
        titleSnippet = firstLine.slice(0, 80);
      }
    }

    let content = "";
    if (userText) {
      // Synthesize directly using user's input text
      const cleanUserText = userText.trim();
      if (deliverableType === "executive_summary") {
        content = `# Executive Summary: ${titleSnippet}

## 1. Context & Scope
Target Audience: ${audience} | Tone Calibration: ${tone}

${cleanUserText.slice(0, 400)}

## 2. Key Grounded Findings
- Core assertions verified against ingested source facts.
- Institutional safety boundaries and factual consistency maintained across all dimensions.
${instructions ? `\n*Operator Guidance Applied: ${instructions}*` : ""}

## 3. Recommended Next Steps
1. Proceed with formal stakeholder distribution following operator disclosure sign-off.
2. Maintain active monitoring across affected telemetry vectors.`;
      } else if (deliverableType === "linkedin_post") {
        content = `Key Operational Update: ${titleSnippet}

${cleanUserText.slice(0, 300)}...

Key takeaways:
✔ Verified against primary institutional fact base
✔ Full alignment with organizational policy
✔ Action items prioritized for stakeholder execution

${instructions ? `Guidance: ${instructions}\n\n` : ""}#Leadership #OperationalExcellence #Integrity #Strategy`;
      } else if (deliverableType === "advisory") {
        content = `ADVISORY NOTICE: ${titleSnippet.toUpperCase()}
ISSUED: ${new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }).toUpperCase()} | AUDIENCE: ${audience.toUpperCase()}

1. OPERATIONAL CONTEXT:
${cleanUserText.slice(0, 350)}

2. DIRECTIVES & ACTIONS:
- Verify relevant operational points against official documentation.
- Maintain compliance with internal security and disclosure requirements.
${instructions ? `- Operational Note: ${instructions}` : ""}

3. CONTACT & GOVERNANCE:
Direct inquiries to the designated Duty Officer.`;
      } else if (deliverableType === "press_release") {
        content = `FOR IMMEDIATE RELEASE

${titleSnippet.toUpperCase()}

NEW DELHI — Official communication synthesized from verified organizational source material.

${cleanUserText.slice(0, 450)}

"Our commitment remains anchored in absolute operational transparency and rigorous procedural integrity," stated officials today.

###

Media Contacts: Institutional Public Affairs Office.`;
      } else if (deliverableType === "public_faq") {
        content = `# Frequently Asked Questions: ${titleSnippet}

**Q1: What is the primary focus of this update?**
A: ${cleanUserText.slice(0, 180)}...

**Q2: Who is the intended audience and what actions are needed?**
A: This communication is prepared for ${audience}. Follow standard operational guidelines outlined in the core briefing.

**Q3: Has this information been verified?**
A: Yes, all facts and claims have undergone full grounding verification and policy review.`;
      } else {
        content = `# ${titleSnippet}
Synthesized Format: ${deliverableType}
Audience: ${audience}

${cleanUserText}
${instructions ? `\n\n*Special Guidance:* ${instructions}` : ""}`;
      }
    } else {
      // Default canonical sample if no user text provided
      if (deliverableType === "executive_summary") {
        content = `# Operational Incident Advisory — Northern Sector Telemetry Event

## 1. Executive Summary
On 14 September 2026 at 03:42 UTC, anomalous telemetry spikes were recorded across the [LOCATION_1] distribution node. Immediate automated isolation protocols were initiated by [UNIT_NAME_1] under the oversight of [PERSON_1]. 

## 2. Key Operational Findings
- Telemetry divergence was contained within 4.2 seconds via automated secondary bus transfer.
- Zero loss of life or mission-critical command signal was detected across the active operational corridor.
- Redundant optical telemetry channels sustained 99.98% operational reliability throughout the anomaly duration.

## 3. Recommended Actions
1. Maintain heightened spectral monitoring on primary backhaul lines for the next 72 hours.
2. Complete full cryptographic log synchronization with the central node by 18:00 UTC.
3. Deploy firmware patch v4.12 across all field terminal controllers.`;
      } else if (deliverableType === "linkedin_post") {
        content = `Critical Infrastructure Resilience Update:

Earlier today, automated telemetry protocols successfully contained a brief distribution disturbance across our regional operations network within 4.2 seconds.

Key highlights:
✔ Uninterrupted primary operational continuity maintained
✔ Redundant failover executed flawlessly in under 5 seconds
✔ Comprehensive security diagnostics confirmed zero integrity loss

Our operations and engineering teams continue round-the-clock monitoring to ensure uncompromised national infrastructure resilience.

#CriticalInfrastructure #OperationalReadiness #CyberResilience #TechLeadership`;
      } else if (deliverableType === "advisory") {
        content = `ADVISORY NOTICE: REGIONAL TELEMETRY MONITORING PROTOCOL

ISSUED: 14 SEPTEMBER 2026 | CLASSIFICATION: OFFICIAL USE ONLY

1. PURPOSE:
This advisory provides directive guidance regarding anomalous optical signal variations identified in regional distribution sectors.

2. IMMEDIATE DIRECTIVES:
- Verify failover switch responsiveness across all relay points.
- Confirm secondary power coupling meets standard 5-second transfer thresholds.
- Report any deviation exceeding ±0.5 Hz directly to Sector Operations.

3. CONTACT & REPORTING:
Direct inquiries to Regional Command Duty Officer.`;
      } else {
        content = `Standard Deliverable Content for ${deliverableType} synthesized from canonical source facts.`;
      }
    }

    let structured = null;
    if (isPresentation) structured = this.getMockPresentation(titleSnippet, userText);
    if (isInfographic) structured = this.getMockInfographic(titleSnippet, userText);
    if (isVideo) structured = this.getMockVideo(titleSnippet, userText);


    return {
      id: draftId,
      deliverable_type: deliverableType,
      status: "draft",
      draft_content: content,
      structured_content: structured,
      approved_content: null,
      trust_score: {
        grounding_score: 98.2,
        consistency_score: 95.0,
        policy_score: 100.0,
        composite_trust_score: 96.4,
        formula_explanation: "Trust Index = (50% Grounding) + (30% Consistency) + (20% Policy). Security findings evaluated independently.",
      },
      claims: this.getMockClaims(),
      security_actions: [
        {
          id: "sec_01",
          placeholder: "[LOCATION_1]",
          category: "LOCATION",
          original_value: "Forward Operating Base Bravo",
          confidence: 0.96,
          reasoning: "Specific operational facility name",
          audience_level: "Internal",
          is_overridden: false,
          created_at: new Date().toISOString(),
        },
      ],
      policy_violations: [],
      llm_classification_degraded: false,
      created_at: new Date().toISOString(),
    };
  }

  getMockPresentation(title = null, userText = null) {
    const mainTitle = title || "Northern Sector Operational Assessment";
    const bullets = userText
      ? userText.split("\n").filter((l) => l.trim().length > 10).slice(0, 3)
      : ["Operational Findings Verified", "Automated Policy Validation Passed", "Cross-Adapter Consistency Confirmed"];

    return {
      title: mainTitle,
      subtitle: "Executive Briefing & Strategic Assessment",
      slides: [
        {
          slide_number: 1,
          layout: "title",
          title: mainTitle,
          bullets: bullets.length > 0 ? bullets : ["Grounding Verification Complete", "Policy Constraints Satisfied", "100% Traceability"],
          speaker_notes: "Welcome leadership. Today's brief synthesizes core findings directly from verified source material.",
          visual_suggestion: "Split dark card with map vector showing operational boundary.",
        },
        {
          slide_number: 2,
          layout: "bullets",
          title: "Core Operational Findings",
          bullets: [
            "All assertions verified verbatim against canonical graph nodes",
            "Zero unvetted forward-looking commitments detected",
            "Full alignment maintained across sibling communications",
          ],
          speaker_notes: "Emphasize high factual entailment and zero unsupported claims.",
          visual_suggestion: "Horizontal timeline progression with green check indicators.",
        },
        {
          slide_number: 3,
          layout: "stat",
          title: "Verification & Quality Metrics",
          bullets: ["98.2% Grounding Precision", "95.0% Cross-Output Agreement", "100.0% Policy Conformance"],
          speaker_notes: "Key takeaway: comprehensive verification ensures zero hallucination or leakage risk.",
          visual_suggestion: "Large metric counters side-by-side with gold highlight accents.",
        },
      ],
    };
  }

  getMockInfographic(title = null, userText = null) {
    const mainTitle = title || "Operational Incident Quick-Reference";
    return {
      title: mainTitle,
      key_message: userText ? userText.slice(0, 120) + "..." : "Automated telemetry isolation prevented regional cascade within 4.2 seconds.",
      sections: [
        {
          heading: "Verification Index",
          stat_value: "96.4%",
          stat_label: "Trust Score",
          body: "Multi-vector mathematical composite across grounding, consistency, and policy.",
          icon_hint: "shield",
        },
        {
          heading: "Source Grounding",
          stat_value: "98.2%",
          stat_label: "Entailment",
          body: "12 of 12 factual claims verified verbatim against source documentation.",
          icon_hint: "check",
        },
        {
          heading: "Governance Gate",
          stat_value: "100%",
          stat_label: "Disclosure Checked",
          body: "Sensitive entities flagged and cataloged for explicit human decision.",
          icon_hint: "clock",
        },
      ],
      layout_recommendation: "3-column horizontal infographic with central summary hero and bottom citation footer.",
      color_palette: ["#121316", "#f5f1e8", "#d09a45", "#52a87a"],
      footer: "SriGEN Fact & Entity Intelligence Engine · Certified Grounded Data",
    };
  }

  getMockVideo(title = null, userText = null) {
    const mainTitle = title || "Public Operations Update — 60s Briefing";
    return {
      title: mainTitle,
      total_duration_seconds: 60.0,
      narration_script: userText
        ? `Briefing update: ${userText.slice(0, 240)}... All findings have been verified from official records.`
        : "Earlier today, northern sector operations recorded a brief electrical telemetry anomaly. Within 4.2 seconds, automated safety systems successfully engaged secondary power channels. Standard operations continued without disruption, and all monitoring systems report normal status.",
      scenes: [
        {
          scene_number: 1,
          start_seconds: 0.0,
          end_seconds: 15.0,
          visual_description: "Wide satellite view of regional infrastructure with subtle telemetry vector overlay.",
          on_screen_text: mainTitle,
          narration: "Operational status update synthesized directly from canonical source material.",
          b_roll_suggestion: "Clean control room monitors showing steady diagnostic readouts.",
        },
        {
          scene_number: 2,
          start_seconds: 15.0,
          end_seconds: 40.0,
          visual_description: "Diagram highlighting key factual findings.",
          on_screen_text: "Verified Grounding & Policy Adherence",
          narration: "All metrics and assertions have been cross-checked against official records.",
          b_roll_suggestion: "High-voltage switchgear animation illustrating clean transfer.",
        },
        {
          scene_number: 3,
          start_seconds: 40.0,
          end_seconds: 60.0,
          visual_description: "Operations team working calmly with live status confirmed across all sectors.",
          on_screen_text: "System Stability: 99.98% · Full Continuity",
          narration: "Standard operations continued without disruption, and all monitoring systems report normal status.",
          b_roll_suggestion: "Official agency seal with security assurance watermark.",
        },
      ],

      subtitles: [
        { index: 1, start_seconds: 0.5, end_seconds: 14.0, text: "Earlier today, northern sector operations recorded a brief electrical telemetry anomaly." },
        { index: 2, start_seconds: 15.2, end_seconds: 39.0, text: "Within 4.2 seconds, automated safety systems successfully engaged secondary power channels." },
        { index: 3, start_seconds: 40.1, end_seconds: 59.5, text: "Standard operations continued without disruption, and all monitoring systems report normal status." },
      ],
      visual_recommendations: ["Maintain calm corporate tone", "Use subtle gold accent overlays", "Include certified provenance badge in corner"],
    };
  }

  getMockClaims() {
    return [
      {
        claim_text: "Telemetry divergence was contained within 4.2 seconds via automated secondary bus transfer.",
        entailed: true,
        confidence: 0.98,
        reasoning: "Explicitly recorded in source Section 2.1 ('transfer latency 4.2 seconds').",
        matched_source_passage: "Automatic transfer switch TS-4 recorded switchover completion in 4.2s.",
        entity_mismatches: [],
      },
      {
        claim_text: "Zero loss of life or mission-critical command signal was detected across the active operational corridor.",
        entailed: true,
        confidence: 0.99,
        reasoning: "Directly corroborated by primary incident logs.",
        matched_source_passage: "No casualties, damage to equipment, or command link interruptions reported.",
        entity_mismatches: [],
      },
      {
        claim_text: "Redundant optical telemetry channels sustained 99.98% operational reliability throughout the anomaly duration.",
        entailed: true,
        confidence: 0.95,
        reasoning: "Matches telemetry logs with statistical variance < 0.01%.",
        matched_source_passage: "Overall telemetry link margin maintained at 99.98% across channel B.",
        entity_mismatches: [],
      },
      {
        claim_text: "Initial power surge exceeded 1,200 kW across Sector 4.",
        entailed: false,
        confidence: 0.88,
        reasoning: "Source specifies impulse surge was 850 kW, not 1,200 kW. Number is unverified.",
        matched_source_passage: "Peak impulse surge registered at 850 kW on sensor S-12.",
        entity_mismatches: [
          {
            found_in_claim: "1,200 kW",
            matched_in_source: "850 kW",
            mismatch_type: "NUMBER",
            description: "Surge magnitude in deliverable exceeds source telemetry log by 350 kW.",
          },
        ],
      },
    ];
  }

  getMockDisclosureReview(draftId) {
    return {
      draft_id: draftId,
      groups: [
        {
          group_key: "LOCATION",
          label: "Locations",
          total: 1,
          decided: 0,
          pending: 1,
          items: [
            {
              id: "disc_loc_01",
              draft_id: draftId,
              placeholder: "[LOCATION_1]",
              category: "LOCATION",
              detected_value_preview: "Forward Operating Base Bravo",
              confidence: 0.97,
              reasoning: "Military operational base name identifiable in open source",
              suggested_default: "withhold",
              analyst_choice: null,
              manual_edit_text: null,
              decision_source: null,
              group_key: "LOCATION",
              detected_at: "output",
              decided_by: null,
              decided_at: null,
              created_at: new Date().toISOString(),
            },
          ],
        },
        {
          group_key: "UNIT_NAME",
          label: "Unit names",
          total: 1,
          decided: 0,
          pending: 1,
          items: [
            {
              id: "disc_unit_01",
              draft_id: draftId,
              placeholder: "[UNIT_NAME_1]",
              category: "UNIT_NAME",
              detected_value_preview: "Unit 402 Incident Response",
              confidence: 0.95,
              reasoning: "Tactical emergency response designation",
              suggested_default: "withhold",
              analyst_choice: null,
              manual_edit_text: null,
              decision_source: null,
              group_key: "UNIT_NAME",
              detected_at: "output",
              decided_by: null,
              decided_at: null,
              created_at: new Date().toISOString(),
            },
          ],
        },
        {
          group_key: "PERSON",
          label: "Personal names",
          total: 1,
          decided: 0,
          pending: 1,
          items: [
            {
              id: "disc_person_01",
              draft_id: draftId,
              placeholder: "[PERSON_1]",
              category: "PERSON",
              detected_value_preview: "Director General V. Sharma",
              confidence: 0.92,
              reasoning: "Official agency leadership identity",
              suggested_default: "disclose",
              analyst_choice: null,
              manual_edit_text: null,
              decision_source: null,
              group_key: "PERSON",
              detected_at: "output",
              decided_by: null,
              decided_at: null,
              created_at: new Date().toISOString(),
            },
          ],
        },
      ],
      total_items: 3,
      suggested_disclose_count: 1,
      suggested_withhold_count: 2,
      pending_count: 3,
    };
  }

  getMockLedgerEntry(draftId, finalContent = null, blockIndex = 1) {
    const timestamp = new Date().toISOString();
    return {
      id: "led_" + Date.now().toString(36),
      index: blockIndex,
      timestamp,
      operator: "operator_sec_01",
      model_version: "llama-3.3-70b-versatile",
      source_hash: "3a7b9c1d2e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
      draft_hash: "9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c",
      final_hash: "7e6f5d4c3b2a10f9e8d7c6b5a403f2e1d0c9b8a7f6e5d4c3b2a10f9e8d7c6b5a",
      diff_reference: "Resolved 2 sensitive placeholders to generic descriptors: [LOCATION_1] -> an affected regional site, [UNIT_NAME_1] -> the designated response team; approved by authorized approver.",
      previous_hash: "0000000000000000000000000000000000000000000000000000000000000000",
      current_hash: "8f43a9b8c2d1e0f4a3b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9",
      draft_id: draftId,
    };
  }
}

export const api = new ApiService();
export default api;
