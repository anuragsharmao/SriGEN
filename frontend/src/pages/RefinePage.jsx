import React, { useState, useRef, useEffect } from "react";
import TopBar from "../components/TopBar.jsx";
import "./RefinePage.css";

/* ---------------------------------- icons --------------------------------- */

const Icon = {
  Doc: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.5 3.5h8L19 8v12a1 1 0 0 1-1 1h-11.5a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
      <path d="M14 3.5V8h5" />
      <path d="M8.5 12.5h7M8.5 15.5h7M8.5 18h4" />
    </svg>
  ),
  UploadCloud: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  ),
  EditPen: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  ),
  ArrowRight: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M13 5l7 7-7 7" />
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
  Trash: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  ),
  Refresh: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3" />
    </svg>
  ),
  Close: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  Info: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
  User: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="7" r="4" />
      <path d="M5.5 21a6.5 6.5 0 0 1 13 0" />
    </svg>
  ),
  MessageSquare: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  Globe: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
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
  Target: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  ),
  Compass: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
    </svg>
  ),
  Feather: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z" />
      <line x1="16" y1="8" x2="2" y2="22" />
      <line x1="17.5" y1="15" x2="9" y2="15" />
    </svg>
  ),
  ShieldLock: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.5 20 6v6c0 5.2-3.4 9.1-8 10.5C7.4 21.1 4 17.2 4 12V6l8-3.5Z" />
      <rect x="9.3" y="11" width="5.4" height="4.4" rx="1" />
      <path d="M10.2 11V9.6a1.8 1.8 0 0 1 3.6 0V11" />
    </svg>
  ),
  Spark: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
    </svg>
  ),
};

/* --------------------------------- data --------------------------------- */

// Seven DeliverableSpec dimensions from SriGEN Architecture with dedicated icons and muted accent tones
const REFINEMENT_DIMENSIONS = [
  {
    id: "audience",
    label: "Audience",
    icon: "User",
    accent: "slate",
    defaultOption: "Senior Leadership",
    options: [
      "Senior Leadership",
      "General Public",
      "Government Officials",
      "Technical Team",
      "Internal / Restricted",
      "Auto",
    ],
  },
  {
    id: "tone",
    label: "Tone",
    icon: "MessageSquare",
    accent: "emerald",
    defaultOption: "Formal",
    options: [
      "Formal",
      "Direct",
      "Concise",
      "Analytical",
      "Advisory",
      "Reassuring",
      "Neutral",
      "Urgent",
      "Technical",
    ],
  },
  {
    id: "language",
    label: "Language",
    icon: "Globe",
    accent: "teal",
    defaultOption: "English",
    options: ["English", "Hindi", "Auto"],
  },
  {
    id: "length",
    label: "Length",
    icon: "Sliders",
    accent: "amber",
    defaultOption: "Balanced",
    options: ["Brief", "Balanced", "Detailed"],
  },
  {
    id: "detail_focus",
    label: "Detail Focus",
    icon: "Target",
    accent: "terracotta",
    defaultOption: "Operational Findings",
    options: [
      "Operational Findings",
      "Key Facts",
      "Timeline",
      "Impact",
      "Response Actions",
      "Risks",
      "Recommendations",
    ],
  },
  {
    id: "communication_objective",
    label: "Communication Objective",
    icon: "Compass",
    accent: "indigo",
    defaultOption: "Inform",
    options: [
      "Inform",
      "Reassure",
      "Warn",
      "Persuade",
      "Instruct",
      "Announce",
      "Auto",
    ],
  },
  {
    id: "content_style",
    label: "Content Style",
    icon: "Feather",
    accent: "ochre",
    defaultOption: "Executive Summary",
    options: [
      "Executive Summary",
      "Narrative",
      "Bulleted",
      "Q&A",
      "Data-led",
      "Storytelling",
      "Auto",
    ],
  },
];

// Content Types with Categories and Tone Tags
const CONTENT_TYPES = [
  { id: "executive_summary", label: "Executive Summary", category: "Briefing & Reports · Text", group: "brief" },
  { id: "linkedin_post", label: "LinkedIn Post", category: "Public Communication · Text", group: "public" },
  { id: "advisory", label: "Advisory", category: "Public Communication · Text", group: "public" },
  { id: "briefing_note", label: "Briefing Note", category: "Briefing & Reports · Text", group: "brief" },
  { id: "situation_report", label: "Situation Report", category: "Briefing & Reports · Text", group: "brief" },
  { id: "incident_report", label: "Incident Report", category: "Briefing & Reports · Text", group: "brief" },
  { id: "press_release", label: "Press Release", category: "Public Communication · Text", group: "public" },
  { id: "public_faq", label: "Public FAQ", category: "Public Communication · Text", group: "public" },
  { id: "presentation", label: "Presentation", category: "Structured Content · Presentation", group: "struct" },
  { id: "infographic", label: "Infographic", category: "Structured Content · Infographic", group: "struct" },
  { id: "video_package", label: "Video Package", category: "Structured Content · Video", group: "struct" },
  { id: "custom", label: "Custom Deliverable", category: "General · Custom", group: "custom" },
];

const SUGGESTIONS = [
  { text: "Make it more concise & direct", tone: "amber" },
  { text: "Adopt an executive advisory tone", tone: "emerald" },
  { text: "Highlight key operational findings", tone: "terracotta" },
  { text: "Clarify the incident response timeline", tone: "slate" },
];

/* --------------------------------- component -------------------------------- */

export default function RefinePage() {
  // 1. Source Document State (Empty initially)
  const [sourceFile, setSourceFile] = useState(null);
  const sourceInputRef = useRef(null);

  // 2. Current Content State (Empty initially)
  const [draftFile, setDraftFile] = useState(null);
  const [draftText, setDraftText] = useState("");
  const [draftMode, setDraftMode] = useState("empty"); // "empty" | "upload" | "text"
  const draftInputRef = useRef(null);

  // 3. Content Type (Unselected initially)
  const [contentType, setContentType] = useState("");

  // 4. Fact verification from source doc (only tickable if source is uploaded)
  const [factVerification, setFactVerification] = useState(false);

  // 5. Refinement Dimensions (Unchecked initially)
  const [selectedDimensions, setSelectedDimensions] = useState({
    audience: { checked: false, value: "Senior Leadership" },
    tone: { checked: false, value: "Formal" },
    language: { checked: false, value: "English" },
    length: { checked: false, value: "Balanced" },
    detail_focus: { checked: false, value: "Operational Findings" },
    communication_objective: { checked: false, value: "Inform" },
    content_style: { checked: false, value: "Executive Summary" },
  });

  // 5. Additional Instructions (Empty initially)
  const [instructions, setInstructions] = useState("");

  // 6. Processing / Completion Modal State
  const [modalState, setModalState] = useState(null); // null | "processing" | "completed"
  const [processingStage, setProcessingStage] = useState(1);

  useEffect(() => {
    document.title = "SriGEN — Refine";
  }, []);

  // Handlers for Source Document
  const handleSourceUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSourceFile({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + " KB",
        type: file.type || "Document",
        timestamp: "Just now",
      });
    }
  };

  const handleSourceDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSourceFile({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + " KB",
        type: file.type || "Document",
        timestamp: "Just now",
      });
    }
  };

  // Handlers for Current Content
  const handleDraftFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setDraftFile({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + " KB",
        type: file.type || "Draft Document",
      });
      setDraftMode("upload");
    }
  };

  const handleDraftDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setDraftFile({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + " KB",
        type: file.type || "Draft Document",
      });
      setDraftMode("upload");
    }
  };

  // Dimension Checkbox / Value Toggle
  const handleDimensionToggle = (dimId) => {
    setSelectedDimensions((prev) => ({
      ...prev,
      [dimId]: {
        ...prev[dimId],
        checked: !prev[dimId].checked,
      },
    }));
  };

  const handleDimensionValueChange = (dimId, value) => {
    setSelectedDimensions((prev) => ({
      ...prev,
      [dimId]: {
        ...prev[dimId],
        value,
      },
    }));
  };

  // Quick suggestion click helper
  const handleSuggestionClick = (text) => {
    setInstructions((prev) => (prev ? `${prev} ${text}` : text));
  };

  // Validation: Required fields to enable "Refine Content" button
  const hasSource = Boolean(sourceFile);
  const hasContent = Boolean(draftFile || draftText.trim().length > 0);
  const hasContentType = Boolean(contentType);
  const isReadyToRefine = hasSource && hasContent && hasContentType;

  // Refine Process Trigger
  const handleStartRefine = () => {
    if (!isReadyToRefine) return;
    setModalState("processing");
    setProcessingStage(1);

    setTimeout(() => setProcessingStage(2), 700);
    setTimeout(() => setProcessingStage(3), 1500);
    setTimeout(() => setProcessingStage(4), 2300);
    setTimeout(() => {
      setModalState("completed");
    }, 3100);
  };

  // Selected Content Type Metadata
  const selectedTypeObj = CONTENT_TYPES.find((t) => t.id === contentType);

  return (
    <div className="rf-page">
      {/* GLOBAL MASTER TOP BAR */}
      <TopBar activePage="refine" />

      {/* COMPACT HERO WITH TOPOGRAPHIC DEPTH */}
      <section className="rf-hero">
        <div className="rf-hero-topographic-bg" aria-hidden="true">
          <svg viewBox="0 0 1600 240" preserveAspectRatio="xMidYMid slice">
            <path
              d="M-50,60 Q350,20 750,80 T1350,50 T1700,100"
              fill="none"
              stroke="rgba(208, 154, 69, 0.05)"
              strokeWidth="1.2"
            />
            <path
              d="M-50,140 Q300,180 700,120 T1300,170 T1700,140"
              fill="none"
              stroke="rgba(122, 178, 226, 0.04)"
              strokeWidth="1.2"
            />
          </svg>
        </div>

        <div className="rf-hero-inner">
          <div className="rf-hero-eyebrow-row">
            <span className="rf-eyebrow">REFINE</span>
            <span className="rf-hero-badge">
              <span className="rf-badge-dot"></span>
              EVIDENCE-GROUNDED REFINEMENT
            </span>
          </div>
          <h1 className="rf-headline">Refine your content.</h1>
          <p className="rf-subtext">
            Refine your existing content using source evidence and controlled refinement instructions.
          </p>
        </div>
      </section>

      {/* MAIN TWO-COLUMN WORKSPACE */}
      <main className="rf-workspace">
        <div className="rf-workspace-grid">
          {/* ================= LEFT COLUMN: SOURCE + DRAFT (WARM CREAM) ================= */}
          <div className="rf-col-left">
            {/* CARD 1 — SOURCE DOCUMENT */}
            <section className="rf-card rf-card-source">
              <div className="rf-card-header">
                <div className="rf-card-header-row">
                  <div className="rf-title-group">
                    <span className="rf-card-icon-tag">
                      <Icon.Doc />
                    </span>
                    <h2 className="rf-card-title">SOURCE DOCUMENT</h2>
                  </div>
                  <span className="rf-stamp stamp-terracotta">CANONICAL BASIS</span>
                </div>
                <p className="rf-card-desc">
                  Upload the source material SriGEN should use as the factual and contextual basis for refinement.
                </p>
              </div>

              {/* Hidden File Input */}
              <input
                type="file"
                ref={sourceInputRef}
                style={{ display: "none" }}
                accept=".pdf,.docx,.txt,.md,image/*"
                onChange={handleSourceUpload}
              />

              <div className="rf-card-body">
                {sourceFile ? (
                  /* Uploaded File State with Rich Paper Dossier Preview */
                  <div className="rf-uploaded-dossier">
                    <div className="rf-thumb-paper" aria-hidden="true">
                      <span className="thumb-bar" />
                      <span className="thumb-bar short" />
                      <span className="thumb-seal">SOURCE</span>
                    </div>

                    <div className="rf-file-meta">
                      <div className="rf-meta-head">
                        <span className="rf-filename">{sourceFile.name}</span>
                        <span className="rf-ready-badge">
                          <Icon.Check /> Ready & Indexed
                        </span>
                      </div>
                      <span className="rf-fileinfo">
                        {sourceFile.type} · {sourceFile.size} · Uploaded {sourceFile.timestamp}
                      </span>
                    </div>

                    <div className="rf-file-actions">
                      <button
                        type="button"
                        className="rf-action-link"
                        onClick={() => sourceInputRef.current?.click()}
                        title="Replace file"
                      >
                        <Icon.Refresh />
                        <span>Replace</span>
                      </button>
                      <button
                        type="button"
                        className="rf-action-link rf-action-danger"
                        onClick={() => {
                          setSourceFile(null);
                          setFactVerification(false);
                        }}
                        title="Remove file"
                      >
                        <Icon.Trash />
                        <span>Remove</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  /* Initial Empty Dropzone */
                  <div
                    className="rf-dropzone"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleSourceDrop}
                    onClick={() => sourceInputRef.current?.click()}
                  >
                    <div className="rf-drop-icon">
                      <Icon.UploadCloud />
                    </div>
                    <h4 className="rf-drop-title">Upload source document</h4>
                    <button
                      type="button"
                      className="rf-btn-upload"
                      onClick={(e) => {
                        e.stopPropagation();
                        sourceInputRef.current?.click();
                      }}
                    >
                      <Icon.Doc />
                      <span>Upload File</span>
                    </button>
                    <div className="rf-format-capsules">
                      <span className="fmt-tag tag-pdf">PDF</span>
                      <span className="fmt-tag tag-docx">DOCX</span>
                      <span className="fmt-tag tag-txt">TXT</span>
                      <span className="fmt-tag tag-md">MD</span>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* CARD 2 — CURRENT CONTENT */}
            <section className="rf-card rf-card-draft">
              <div className="rf-card-header">
                <div className="rf-card-header-row">
                  <div className="rf-title-group">
                    <span className="rf-card-icon-tag tag-draft">
                      <Icon.EditPen />
                    </span>
                    <h2 className="rf-card-title">CURRENT CONTENT</h2>
                  </div>
                  {draftMode === "text" ? (
                    <button
                      type="button"
                      className="rf-mode-switch-btn"
                      onClick={() => {
                        setDraftMode("empty");
                        setDraftText("");
                      }}
                    >
                      Switch to File Upload
                    </button>
                  ) : (
                    <span className="rf-stamp stamp-slate">OPERATOR DRAFT</span>
                  )}
                </div>
                <p className="rf-card-desc">
                  Upload or paste the content you want SriGEN to refine.
                </p>
              </div>

              {/* Hidden Draft File Input */}
              <input
                type="file"
                ref={draftInputRef}
                style={{ display: "none" }}
                accept=".pdf,.docx,.txt,.md"
                onChange={handleDraftFileUpload}
              />

              <div className="rf-card-body">
                {draftMode === "upload" && draftFile ? (
                  /* Uploaded Draft State */
                  <div className="rf-uploaded-dossier">
                    <div className="rf-thumb-paper thumb-draft" aria-hidden="true">
                      <span className="thumb-bar" />
                      <span className="thumb-bar short" />
                      <span className="thumb-seal draft-seal">DRAFT</span>
                    </div>

                    <div className="rf-file-meta">
                      <div className="rf-meta-head">
                        <span className="rf-filename">{draftFile.name}</span>
                        <span className="rf-ready-badge badge-teal">
                          <Icon.Check /> Draft Ready
                        </span>
                      </div>
                      <span className="rf-fileinfo">
                        Draft Document · {draftFile.size}
                      </span>
                    </div>

                    <div className="rf-file-actions">
                      <button
                        type="button"
                        className="rf-action-link"
                        onClick={() => draftInputRef.current?.click()}
                      >
                        <Icon.Refresh />
                        <span>Replace</span>
                      </button>
                      <button
                        type="button"
                        className="rf-action-link rf-action-danger"
                        onClick={() => {
                          setDraftFile(null);
                          setDraftMode("empty");
                        }}
                      >
                        <Icon.Trash />
                        <span>Remove</span>
                      </button>
                    </div>
                  </div>
                ) : draftMode === "text" ? (
                  /* Paste / Write Draft Mode */
                  <div className="rf-draft-editor-box">
                    <textarea
                      className="rf-draft-textarea"
                      placeholder="Paste or write your draft here..."
                      value={draftText}
                      onChange={(e) => setDraftText(e.target.value)}
                      rows={5}
                      autoFocus
                    />
                    <div className="rf-draft-editor-footer">
                      <span className="rf-draft-wordcount">
                        {draftText.trim() ? draftText.trim().split(/\s+/).length : 0} words · {draftText.length} characters
                      </span>
                      {draftText && (
                        <button
                          type="button"
                          className="rf-clear-text-btn"
                          onClick={() => setDraftText("")}
                        >
                          Clear Text
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  /* Initial Empty State with Two Options */
                  <div
                    className="rf-dropzone rf-dropzone-split"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDraftDrop}
                  >
                    <div className="rf-drop-icon">
                      <Icon.Doc />
                    </div>
                    <h4 className="rf-drop-title">Upload your draft</h4>
                    <div className="rf-draft-choices">
                      <button
                        type="button"
                        className="rf-btn-upload"
                        onClick={() => draftInputRef.current?.click()}
                      >
                        <Icon.UploadCloud />
                        <span>Upload File</span>
                      </button>
                      <span className="rf-choice-or">or</span>
                      <button
                        type="button"
                        className="rf-btn-text-mode"
                        onClick={() => setDraftMode("text")}
                      >
                        <Icon.EditPen />
                        <span>Paste / Write Draft</span>
                      </button>
                    </div>
                    <div className="rf-format-capsules">
                      <span className="fmt-tag">DOCX</span>
                      <span className="fmt-tag">TXT</span>
                      <span className="fmt-tag">MD</span>
                      <span className="fmt-tag">PDF</span>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>

          {/* ================= RIGHT COLUMN: REFINEMENT CONTROLS (DARK) ================= */}
          <section className="rf-card rf-card-controls">
            <div className="rf-card-header">
              <div className="rf-card-header-row">
                <h2 className="rf-card-title">REFINEMENT CONTROLS</h2>
                <div className="rf-sec-badge">
                  <Icon.ShieldLock />
                  <span className="rf-sec-dot" />
                  <span>FIREWALL: ARMORED</span>
                </div>
              </div>
              <p className="rf-card-desc">Choose what you want to improve.</p>
            </div>

            <div className="rf-controls-scroll-area">
              {/* SECTION: WHAT WOULD YOU LIKE TO IMPROVE? */}
              <div className="rf-control-section">
                <div className="rf-sec-title-row">
                  <span className="rf-section-label">WHAT WOULD YOU LIKE TO IMPROVE?</span>
                  <span className="rf-sec-hint" title="Preserves all unselected aspects">
                    <Icon.Info />
                  </span>
                </div>
                <p className="rf-section-subtext">
                  Select only the dimensions you want to adapt. SriGEN will preserve unselected aspects.
                </p>

                <div className="rf-dimensions-list">
                  {/* FACT VERIFICATION FROM SOURCE DOC (ENABLED ONLY IF SOURCE DOCUMENT IS UPLOADED) */}
                  <div
                    className={`rf-dim-item rf-fact-verify-item ${
                      !hasSource ? "is-disabled" : ""
                    } ${factVerification ? "is-selected" : ""}`}
                  >
                    <label
                      className={`rf-dim-label ${!hasSource ? "label-disabled" : ""}`}
                      title={
                        !hasSource
                          ? "Upload a source document first to enable fact verification"
                          : "Verify deliverable claims against source document facts"
                      }
                    >
                      <input
                        type="checkbox"
                        disabled={!hasSource}
                        checked={factVerification}
                        onChange={(e) => {
                          if (hasSource) setFactVerification(e.target.checked);
                        }}
                      />
                      <span
                        className={`rf-custom-checkbox ${
                          !hasSource ? "checkbox-disabled" : ""
                        }`}
                      >
                        {factVerification && <Icon.Check />}
                      </span>
                      <span className="rf-dim-icon-wrap icon-shield-check">
                        <Icon.ShieldLock />
                      </span>
                      <span className="rf-dim-name">
                        Fact verification from source doc
                      </span>
                      {!hasSource && (
                        <span className="rf-dim-disabled-tag">
                          Source doc required
                        </span>
                      )}
                    </label>

                    {factVerification && hasSource && (
                      <div className="rf-fact-active-badge">
                        <Icon.Check />
                        <span>Evidence Anchored</span>
                      </div>
                    )}
                  </div>

                  {REFINEMENT_DIMENSIONS.map((dim) => {
                    const isChecked = selectedDimensions[dim.id]?.checked || false;
                    const currentValue = selectedDimensions[dim.id]?.value || dim.defaultOption;
                    const DimIcon = Icon[dim.icon] || Icon.Target;

                    return (
                      <div
                        key={dim.id}
                        className={`rf-dim-item dim-accent-${dim.accent} ${
                          isChecked ? "is-selected" : ""
                        }`}
                      >
                        <label className="rf-dim-label">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => handleDimensionToggle(dim.id)}
                          />
                          <span className="rf-custom-checkbox">
                            {isChecked && <Icon.Check />}
                          </span>
                          <span className="rf-dim-icon-wrap">
                            <DimIcon />
                          </span>
                          <span className="rf-dim-name">{dim.label}</span>
                        </label>

                        {/* Value Selector revealed when checked */}
                        {isChecked && (
                          <div className="rf-dim-selector-wrap">
                            <select
                              className="rf-select-compact"
                              value={currentValue}
                              onChange={(e) => handleDimensionValueChange(dim.id, e.target.value)}
                            >
                              {dim.options.map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                            </select>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* SECTION: WHAT TYPE OF CONTENT IS THIS? */}
              <div className="rf-control-section">
                <label htmlFor="rfContentTypeSelect" className="rf-section-label">
                  WHAT TYPE OF CONTENT IS THIS?
                </label>
                <div className="rf-select-group">
                  <select
                    id="rfContentTypeSelect"
                    className={`rf-type-select ${!contentType ? "is-empty" : ""}`}
                    value={contentType}
                    onChange={(e) => setContentType(e.target.value)}
                  >
                    <option value="">Select content type...</option>
                    {CONTENT_TYPES.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label} ({t.category})
                      </option>
                    ))}
                  </select>

                  {selectedTypeObj && (
                    <div className="rf-type-meta-badge">
                      <span className={`badge-cat cat-${selectedTypeObj.group}`}>
                        {selectedTypeObj.category}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* SECTION: ADDITIONAL INSTRUCTIONS WITH SUGGESTION CHIPS */}
              <div className="rf-control-section">
                <div className="rf-sec-title-row">
                  <label htmlFor="rfInstructions" className="rf-section-label">
                    ADDITIONAL INSTRUCTIONS
                  </label>
                  <span className="rf-char-count">{instructions.length}/500</span>
                </div>

                <textarea
                  id="rfInstructions"
                  className="rf-instructions-textarea"
                  placeholder="Tell SriGEN what you want to change..."
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  maxLength={500}
                  rows={3}
                />

                {/* QUICK SUGGESTION CHIPS */}
                <div className="rf-suggestion-chips">
                  {SUGGESTIONS.map((sugg, i) => (
                    <button
                      key={i}
                      type="button"
                      className={`rf-sugg-chip sugg-${sugg.tone}`}
                      onClick={() => handleSuggestionClick(sugg.text)}
                    >
                      <span className="chip-plus">+</span> {sugg.text}
                    </button>
                  ))}
                </div>

                <p className="rf-instructions-hint">
                  Instructions guide presentation, focus, structure, and style while preserving source-grounded facts.
                </p>
              </div>
            </div>

            {/* CARD FOOTER: PRIMARY ACTION */}
            <div className="rf-card-footer">
              <button
                type="button"
                className="rf-btn-refine-primary"
                disabled={!isReadyToRefine}
                onClick={handleStartRefine}
              >
                <span>Refine Content</span>
                <Icon.ArrowRight />
              </button>

              {!isReadyToRefine && (
                <div className="rf-validation-tags">
                  <span className={`val-tag ${hasSource ? "val-ok" : "val-missing"}`}>
                    {hasSource ? "✓ Source ready" : "• Source needed"}
                  </span>
                  <span className={`val-tag ${hasContent ? "val-ok" : "val-missing"}`}>
                    {hasContent ? "✓ Draft ready" : "• Draft needed"}
                  </span>
                  <span className={`val-tag ${hasContentType ? "val-ok" : "val-missing"}`}>
                    {hasContentType ? "✓ Type selected" : "• Type needed"}
                  </span>
                </div>
              )}
            </div>
          </section>
        </div>
      </main>

      {/* ================= PROCESSING MODAL ================= */}
      {modalState === "processing" && (
        <div className="rf-modal-backdrop" role="dialog" aria-modal="true">
          <div className="rf-modal-sheet rf-modal-processing">
            <div className="rf-proc-head">
              <span className="rf-proc-spark">✦</span>
              <h3>REFINING CONTENT</h3>
              <p>Adapting draft with source material under Grounding Guard constraints...</p>
            </div>

            <div className="rf-proc-stepper">
              <div className={`rf-proc-step ${processingStage >= 1 ? "is-active" : ""}`}>
                <div className="rf-proc-dot">{processingStage > 1 ? "✓" : "1"}</div>
                <span>Parsing source evidence & draft structure</span>
              </div>
              <div className={`rf-proc-step ${processingStage >= 2 ? "is-active" : ""}`}>
                <div className="rf-proc-dot">{processingStage > 2 ? "✓" : "2"}</div>
                <span>Applying selected refinement dimensions</span>
              </div>
              <div className={`rf-proc-step ${processingStage >= 3 ? "is-active" : ""}`}>
                <div className="rf-proc-dot">{processingStage > 3 ? "✓" : "3"}</div>
                <span>Enforcing Fact Graph grounding & tone consistency</span>
              </div>
              <div className={`rf-proc-step ${processingStage >= 4 ? "is-active" : ""}`}>
                <div className="rf-proc-dot">{processingStage >= 4 ? "✓" : "4"}</div>
                <span>Finalizing refined deliverable draft</span>
              </div>
            </div>

            <div className="rf-proc-progress">
              <div className="rf-proc-progress-bar"></div>
            </div>
          </div>
        </div>
      )}

      {/* ================= COMPLETED MODAL (TRANSITION TO VERIFY / REVIEW) ================= */}
      {modalState === "completed" && (
        <div className="rf-modal-backdrop" role="dialog" aria-modal="true">
          <div className="rf-modal-sheet rf-modal-completed">
            <div className="rf-comp-head">
              <div className="rf-comp-icon">
                <Icon.CheckCircle />
              </div>
              <div>
                <h3>Content Refined Successfully</h3>
                <p>
                  {selectedTypeObj?.label || "Deliverable"} has been adapted. Proceeding to verification and human review.
                </p>
              </div>
            </div>

            <div className="rf-comp-summary">
              <div className="summary-row">
                <span className="s-label">Source Document:</span>
                <span className="s-value">{sourceFile?.name || "Uploaded file"}</span>
              </div>
              <div className="summary-row">
                <span className="s-label">Deliverable Type:</span>
                <span className="s-value">{selectedTypeObj?.label || "Deliverable"}</span>
              </div>
              <div className="summary-row">
                <span className="s-label">Active Improvements:</span>
                <span className="s-value">
                  {Object.entries(selectedDimensions).filter(([_, v]) => v.checked).length > 0
                    ? Object.entries(selectedDimensions)
                        .filter(([_, v]) => v.checked)
                        .map(([id, v]) => `${REFINEMENT_DIMENSIONS.find((d) => d.id === id)?.label} (${v.value})`)
                        .join(", ")
                    : "Instructions only"}
                </span>
              </div>
            </div>

            <div className="rf-comp-actions">
              <button
                type="button"
                className="rf-btn-secondary"
                onClick={() => setModalState(null)}
              >
                Refine Another
              </button>
              <a
                className="rf-btn-primary-link"
                href="/dashboard#review"
              >
                <span>Proceed to Human Review & Provenance</span>
                <Icon.ArrowRight />
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
