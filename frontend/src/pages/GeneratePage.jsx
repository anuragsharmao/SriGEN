import { useState, useEffect, useRef } from "react";
import TopBar from "../components/TopBar.jsx";
import "./GeneratePage.css";

/* ---------------------------------- icons --------------------------------- */

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
  Doc: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.5 3.5h8L19 8v12a1 1 0 0 1-1 1h-11.5a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
      <path d="M14 3.5V8h5" />
      <path d="M8.5 12.5h7M8.5 15.5h7M8.5 18h4" />
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
  Spark: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
    </svg>
  ),
  Eye: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  ),
  Link: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9.5 14.5 14.5 9.5" />
      <path d="M11 7.2 12.6 5.6a3.4 3.4 0 0 1 4.8 4.8L15.8 12" />
      <path d="M13 16.8 11.4 18.4a3.4 3.4 0 0 1-4.8-4.8L8.2 12" />
    </svg>
  ),
  ArrowRight: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M13 5l7 7-7 7" />
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
  EditRefine: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
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
  Twitter: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 4l16 16M4 20L20 4" />
    </svg>
  ),
  Newspaper: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2" />
      <path d="M18 14h-8M15 18h-5M10 6h8v4h-8z" />
    </svg>
  ),
  MessageCircle: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  ),
  Bell: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  ),
  FileText: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  Clipboard: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
    </svg>
  ),
  Activity: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  AlertTriangle: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  Layout: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="9" y1="21" x2="9" y2="9" />
    </svg>
  ),
  BarChart: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <line x1="12" y1="20" x2="12" y2="10" />
      <line x1="18" y1="20" x2="18" y2="4" />
      <line x1="6" y1="20" x2="6" y2="16" />
    </svg>
  ),
  Video: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polygon points="23 7 16 12 23 17 23 7" />
      <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
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
  Network: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="5" r="2" />
      <circle cx="5" cy="18" r="2" />
      <circle cx="19" cy="18" r="2" />
      <circle cx="12" cy="12" r="1.8" />
      <path d="M12 7v3.2M10.6 13.2 6.5 16.5M13.4 13.2l4.1 3.3" />
    </svg>
  ),
  Lock: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  ),
  Info: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
  UploadCloud: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  ),
  Close: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
};

/* --------------------------------- data --------------------------------- */

const TRANSFORMATION_STAGES = [
  { id: "understand", label: "UNDERSTAND", icon: "Network" },
  { id: "control", label: "CONTROL", icon: "ShieldLock" },
  { id: "generate", label: "GENERATE", icon: "Spark", active: true },
  { id: "verify", label: "VERIFY", icon: "ShieldCheck" },
  { id: "review", label: "REVIEW", icon: "Eye" },
  { id: "prove", label: "PROVE", icon: "Link" },
];

const DELIVERABLE_GROUPS = [
  {
    category: "PUBLIC COMMUNICATION",
    count: 5,
    items: [
      {
        id: "linkedin_post",
        name: "LinkedIn Post",
        desc: "Short, engaging post for professional network.",
        icon: "Share",
      },
      {
        id: "twitter_thread",
        name: "X / Twitter Thread",
        desc: "Multi-post thread for real-time updates.",
        icon: "Twitter",
      },
      {
        id: "press_release",
        name: "Press Release",
        desc: "Formal announcement for media.",
        icon: "Newspaper",
      },
      {
        id: "public_faq",
        name: "Public FAQ",
        desc: "Q&A for general public.",
        icon: "MessageCircle",
      },
      {
        id: "advisory",
        name: "Advisory",
        desc: "Guidance and recommendations.",
        icon: "Bell",
      },
    ],
  },
  {
    category: "BRIEFING & REPORTS",
    count: 5,
    items: [
      {
        id: "executive_summary",
        name: "Executive Summary",
        desc: "Concise leadership summary.",
        icon: "FileText",
      },
      {
        id: "briefing_note",
        name: "Briefing Note",
        desc: "Detailed briefing for stakeholders.",
        icon: "Clipboard",
      },
      {
        id: "sitrep",
        name: "SITREP",
        desc: "Situation report / operational update.",
        icon: "Activity",
      },
      {
        id: "incident_report",
        name: "Incident Report",
        desc: "Detailed incident analysis.",
        icon: "AlertTriangle",
      },
      {
        id: "presentation",
        name: "Presentation",
        desc: "Slide deck for meetings.",
        icon: "Layout",
      },
    ],
  },
  {
    category: "MORE",
    count: 3,
    items: [
      {
        id: "infographic",
        name: "Infographic",
        desc: "Visual data representation.",
        icon: "BarChart",
      },
      {
        id: "video_package",
        name: "Video Package",
        desc: "Short video with key points.",
        icon: "Video",
      },
      {
        id: "custom",
        name: "Custom Deliverable",
        desc: "Tailored format or structure.",
        icon: "Sliders",
      },
    ],
  },
];

export default function GeneratePage() {
  // Source material state
  const [sourceFile, setSourceFile] = useState({
    name: "incident_report.pdf",
    size: "2.4 MB",
    id: "SRC-0241",
    timestamp: "Added just now",
    type: "PDF",
  });

  // Selected deliverables
  const [selectedOutputs, setSelectedOutputs] = useState([
    "executive_summary",
    "linkedin_post",
    "advisory",
  ]);

  // Form controls
  const [targetAudience, setTargetAudience] = useState("Senior Leadership");
  const [tone, setTone] = useState("Auto");
  const [language, setLanguage] = useState("Auto");
  const [detail, setDetail] = useState("Balanced");
  const [instructions, setInstructions] = useState("");

  // Modals & UI interactive states
  const [activeModal, setActiveModal] = useState(null); // 'preview' | 'details' | 'security' | 'processing' | 'results'
  const [processingStage, setProcessingStage] = useState(0);
  const [generatedDrafts, setGeneratedDrafts] = useState(null);

  const fileInputRef = useRef(null);

  useEffect(() => {
    document.title = "SriGEN — Generate Intelligence";
  }, []);

  const toggleDeliverable = (id) => {
    setSelectedOutputs((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const removeDeliverable = (id) => {
    setSelectedOutputs((prev) => prev.filter((item) => item !== id));
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      const ext = file.name.split(".").pop().toUpperCase();
      setSourceFile({
        name: file.name,
        size: `${sizeMB} MB`,
        id: `SRC-${Math.floor(1000 + Math.random() * 9000)}`,
        timestamp: "Added just now",
        type: ext || "FILE",
      });
    }
  };

  const startGeneration = async () => {
    if (!sourceFile || selectedOutputs.length === 0) return;

    setActiveModal("processing");
    setProcessingStage(1);

    // Staged progression through the canonical architecture
    setTimeout(() => setProcessingStage(2), 900);
    setTimeout(() => setProcessingStage(3), 1900);
    setTimeout(() => setProcessingStage(4), 2900);
    setTimeout(() => {
      setProcessingStage(5);
      setGeneratedDrafts({
        source_id: sourceFile.id,
        trust_score: {
          composite: 96.4,
          grounding: 98.2,
          consistency: 95.0,
          policy: 100.0,
        },
        drafts: selectedOutputs.map((id) => {
          const item = DELIVERABLE_GROUPS.flatMap((g) => g.items).find(
            (i) => i.id === id
          );
          return {
            id,
            title: item ? item.name : id,
            status: "Generated · Verification Passed",
            content: `[Grounded Output: ${item ? item.name : id}]\n\nBased on source material (${sourceFile.name}), this deliverable has been synthesized directly from the canonical Fact & Entity Graph with 100% policy compliance, cross-adapter consistency, and verified grounding citations. All sensitive entities have been cataloged in the Disclosure Control register for operator sign-off.`,
          };
        }),
      });
      setActiveModal("results");
    }, 4000);
  };

  // Helper label lookup
  const getDeliverableName = (id) => {
    for (const group of DELIVERABLE_GROUPS) {
      const item = group.items.find((i) => i.id === id);
      if (item) return item.name;
    }
    return id;
  };

  return (
    <div className="gen-page">
      {/* GLOBAL NAVIGATION */}
      <TopBar activePage="generate" />

      {/* GENERATION HEADER & ARCHITECTURAL TRANSFORMATION PATH */}
      <section className="gen-header">
        <div className="gen-header-bg" aria-hidden="true">
          <svg viewBox="0 0 1600 360" preserveAspectRatio="xMidYMid slice">
            <path
              d="M-50,80 Q300,50 600,120 T1200,90 T1700,160"
              fill="none"
              stroke="rgba(208, 154, 69, 0.05)"
              strokeWidth="1.2"
            />
            <path
              d="M-50,180 Q250,230 650,180 T1250,240 T1700,220"
              fill="none"
              stroke="rgba(208, 154, 69, 0.04)"
              strokeWidth="1.2"
            />
          </svg>
        </div>

        <div className="gen-header-inner">
          <div className="gen-header-left">
            <span className="gen-eyebrow">TRANSFORMATION MODE</span>
            <h1 className="gen-title">Generate intelligence.</h1>
            <p className="gen-sub">
              Transform source material into controlled, audience-aware
              deliverables from a single trusted fact base.
            </p>
          </div>

          {/* Transformation Path Visualization */}
          <div className="gen-path-box">
            <span className="path-corner path-corner-tl" aria-hidden="true" />
            <span className="path-corner path-corner-tr" aria-hidden="true" />
            <span className="path-corner path-corner-bl" aria-hidden="true" />
            <span className="path-corner path-corner-br" aria-hidden="true" />

            <div className="path-header">
              <span className="path-spark">✦</span>
              <span className="path-title">TRANSFORMATION PATH</span>
            </div>

            <div className="path-stepper">
              {TRANSFORMATION_STAGES.map((stg, i) => {
                const IconComponent = Icon[stg.icon] || Icon.Doc;
                return (
                  <div
                    key={stg.id}
                    className={`path-step ${stg.active ? "path-step-active" : ""}`}
                  >
                    <div className="step-badge">
                      <IconComponent />
                    </div>
                    <span className="step-label">{stg.label}</span>
                    {i < TRANSFORMATION_STAGES.length - 1 && (
                      <span className="step-arrow" aria-hidden="true">
                        <Icon.ArrowRight />
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* MAIN THREE-COLUMN WORKSPACE */}
      <main className="gen-workspace">
        <div className="gen-workspace-grid">
          {/* ================= COLUMN 1: 01 SOURCE ================= */}
          <section className="gen-col col-source">
            <div className="col-header">
              <span className="col-tag">01 SOURCE</span>
              <h2 className="col-title">Source material</h2>
              <p className="col-desc">
                Add the document or content SriGEN should understand and
                transform.
              </p>
            </div>

            {/* Hidden File Input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              style={{ display: "none" }}
              accept=".pdf,.docx,.txt,.md,image/*,audio/*,video/*"
            />

            {sourceFile ? (
              /* Paper Document Sheet Preview */
              <div className="source-dossier-card">
                <div className="source-paper-sheet">
                  <div className="sheet-thumb" aria-hidden="true">
                    <div className="sheet-doc-header">
                      <span className="sheet-dot"></span>
                      <span className="sheet-dot"></span>
                    </div>
                    <div className="sheet-lines">
                      <span className="s-line w-80"></span>
                      <span className="s-line w-60"></span>
                      <span className="s-line w-90"></span>
                      <span className="s-line w-50"></span>
                    </div>
                    <div className="sheet-stamp">CONFIDENTIAL</div>
                  </div>

                  <div className="sheet-details">
                    <div className="sheet-icon-file">
                      <Icon.Doc />
                    </div>
                    <div className="sheet-meta">
                      <h4 className="sheet-filename">{sourceFile.name}</h4>
                      <p className="sheet-spec">
                        {sourceFile.type} · {sourceFile.size}
                      </p>
                      <p className="sheet-source-id">
                        Source ID: {sourceFile.id}
                      </p>
                      <p className="sheet-timestamp">{sourceFile.timestamp}</p>
                    </div>
                  </div>
                </div>

                <div className="sheet-actions">
                  <button
                    className="sheet-btn"
                    type="button"
                    onClick={() => setActiveModal("preview")}
                  >
                    <Icon.Eye />
                    <span>Preview</span>
                  </button>
                  <button
                    className="sheet-btn"
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Icon.Refresh />
                    <span>Replace</span>
                  </button>
                  <button
                    className="sheet-btn sheet-btn-danger"
                    type="button"
                    onClick={() => setSourceFile(null)}
                  >
                    <Icon.Trash />
                    <span>Remove</span>
                  </button>
                </div>
              </div>
            ) : (
              /* Dropzone when no file uploaded */
              <div
                className="source-dropzone"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="drop-icon">
                  <Icon.UploadCloud />
                </div>
                <h4>Select or drop source document</h4>
                <p>Supports PDF, DOCX, TXT, MD, Image, Audio & Video</p>
                <button
                  className="drop-cta-btn"
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                >
                  Browse Files
                </button>
              </div>
            )}

            {/* SOURCE READY VERIFICATION PANEL */}
            {sourceFile && (
              <div className="source-ready-panel">
                <div className="ready-top">
                  <span className="ready-icon">
                    <Icon.CheckCircle />
                  </span>
                  <span className="ready-label">SOURCE READY</span>
                </div>
                <div className="ready-checklist">
                  <div className="check-row">
                    <span className="chk">✓</span>
                    <span>Content detected</span>
                  </div>
                  <div className="check-row">
                    <span className="chk">✓</span>
                    <span>Dates detected</span>
                  </div>
                  <div className="check-row">
                    <span className="chk">✓</span>
                    <span>Entities detected</span>
                  </div>
                  <div className="check-row">
                    <span className="chk">✓</span>
                    <span>Numbers detected</span>
                  </div>
                </div>
                <button
                  className="ready-details-link"
                  type="button"
                  onClick={() => setActiveModal("details")}
                >
                  View details →
                </button>
              </div>
            )}

            {/* SENSITIVITY FIREWALL / DISCLOSURE CONTROL */}
            {sourceFile && (
              <div className="disclosure-control-panel">
                <div className="dc-header">
                  <div className="dc-title-group">
                    <span className="dc-icon">
                      <Icon.ShieldLock />
                    </span>
                    <span className="dc-title">SENSITIVITY FIREWALL</span>
                  </div>
                  <span className="dc-badge-ready">
                    <i className="dot-ready"></i>READY
                  </span>
                </div>
                <p className="dc-desc">
                  Sensitive information is automatically classified and
                  protected before generation.
                </p>

                <div className="dc-tags-row">
                  <span className="dc-tag">
                    <span className="tag-label">[LOCATION]</span>
                    <span className="tag-count">2</span>
                  </span>
                  <span className="dc-tag">
                    <span className="tag-label">[UNIT_NAME]</span>
                    <span className="tag-count">1</span>
                  </span>
                  <span className="dc-tag">
                    <span className="tag-label">[PERSON]</span>
                    <span className="tag-count">1</span>
                  </span>
                </div>

                <button
                  className="dc-link"
                  type="button"
                  onClick={() => setActiveModal("security")}
                >
                  View security actions →
                </button>
              </div>
            )}
          </section>

          {/* ================= COLUMN 2: 02 DELIVERABLES ================= */}
          <section className="gen-col col-deliverables">
            <div className="col-header">
              <span className="col-tag">02 DELIVERABLES</span>
              <h2 className="col-title">What should SriGEN create?</h2>
              <p className="col-desc">
                Select one or more deliverables. All selected outputs will be
                generated from the same Fact / Entity Graph.
              </p>
            </div>

            {/* Three Deliverable Categories in Parallel Columns */}
            <div className="deliverable-categories-grid">
              {DELIVERABLE_GROUPS.map((group) => (
                <div key={group.category} className="deliv-category-col">
                  <div className="deliv-cat-header">
                    <span className="cat-title">{group.category}</span>
                    <span className="cat-count">{group.count}</span>
                  </div>

                  <div className="deliv-items-list">
                    {group.items.map((item) => {
                      const isSelected = selectedOutputs.includes(item.id);
                      const ItemIcon = Icon[item.icon] || Icon.Doc;
                      return (
                        <div
                          key={item.id}
                          className={`deliv-row ${isSelected ? "is-selected" : ""}`}
                          onClick={() => toggleDeliverable(item.id)}
                          role="checkbox"
                          aria-checked={isSelected}
                          tabIndex={0}
                        >
                          <div className="deliv-row-left">
                            <span className="deliv-icon">
                              <ItemIcon />
                            </span>
                            <div className="deliv-text">
                              <span className="deliv-name">{item.name}</span>
                              <span className="deliv-desc">{item.desc}</span>
                            </div>
                          </div>

                          <div className="deliv-checkbox">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => {}}
                              tabIndex={-1}
                            />
                            <span className="custom-check">
                              {isSelected && <Icon.Check />}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* SELECTED DELIVERABLES CHIPS STRIP */}
            <div className="selected-strip">
              <div className="strip-left">
                <span className="strip-title">SELECTED DELIVERABLES</span>
                <div className="strip-chips">
                  {selectedOutputs.map((id) => (
                    <span key={id} className="selected-chip">
                      <span>{getDeliverableName(id)}</span>
                      <button
                        type="button"
                        className="chip-remove"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeDeliverable(id);
                        }}
                        aria-label={`Remove ${getDeliverableName(id)}`}
                      >
                        <Icon.Close />
                      </button>
                    </span>
                  ))}
                  {selectedOutputs.length === 0 && (
                    <span className="strip-empty">
                      No deliverables selected
                    </span>
                  )}
                </div>
              </div>

              <div className="strip-right">
                <span className="strip-counter">
                  {selectedOutputs.length} outputs →
                </span>
              </div>
            </div>

            {/* ONE FACT GRAPH · MULTIPLE OUTPUTS EMBEDDED DARK PANEL */}
            <div className="fact-graph-banner">
              <div className="fgb-header">
                <span className="fgb-title">
                  ONE FACT GRAPH · MULTIPLE OUTPUTS
                </span>
              </div>

              <div className="fgb-diagram">
                {/* Source Node */}
                <div className="fgb-source-node">
                  <div className="fgb-doc-icon">
                    <Icon.Doc />
                  </div>
                  <span className="fgb-node-label">SOURCE</span>
                  <span className="fgb-doc-name">
                    {sourceFile ? sourceFile.name : "source_document.pdf"}
                  </span>
                </div>

                <div className="fgb-connector-arrow">
                  <Icon.ArrowRight />
                </div>

                {/* Central Fact/Entity Graph Node */}
                <div className="fgb-graph-center">
                  <div className="fgb-svg-wrap">
                    <svg
                      viewBox="0 0 120 80"
                      className="fgb-kg"
                      aria-hidden="true"
                    >
                      <line
                        x1="60"
                        y1="16"
                        x2="28"
                        y2="42"
                        stroke="rgba(245,241,232,0.2)"
                        strokeWidth="1.2"
                      />
                      <line
                        x1="60"
                        y1="16"
                        x2="92"
                        y2="40"
                        stroke="rgba(245,241,232,0.2)"
                        strokeWidth="1.2"
                      />
                      <line
                        x1="28"
                        y1="42"
                        x2="60"
                        y2="66"
                        stroke="rgba(245,241,232,0.2)"
                        strokeWidth="1.2"
                      />
                      <line
                        x1="92"
                        y1="40"
                        x2="60"
                        y2="66"
                        stroke="rgba(245,241,232,0.2)"
                        strokeWidth="1.2"
                      />
                      <line
                        x1="28"
                        y1="42"
                        x2="92"
                        y2="40"
                        stroke="rgba(245,241,232,0.2)"
                        strokeWidth="1.2"
                      />
                      <circle
                        cx="60"
                        cy="16"
                        r="4.5"
                        fill="var(--ochre-gold)"
                      />
                      <circle cx="28" cy="42" r="4" fill="var(--red)" />
                      <circle
                        cx="92"
                        cy="40"
                        r="4"
                        fill="var(--green-emerald)"
                      />
                      <circle cx="60" cy="66" r="4" fill="var(--green-light)" />
                      <circle cx="60" cy="41" r="3" fill="#ffffff" />
                    </svg>
                  </div>
                  <span className="fgb-kg-label">FACT / ENTITY GRAPH</span>
                </div>

                <div className="fgb-connector-arrow">
                  <Icon.ArrowRight />
                </div>

                {/* Outputs Branch */}
                <div className="fgb-outputs-branch">
                  <div className="fgb-pills-list">
                    {selectedOutputs.slice(0, 3).map((id) => (
                      <div key={id} className="fgb-out-pill">
                        <Icon.Doc />
                        <span>{getDeliverableName(id)}</span>
                      </div>
                    ))}
                    {selectedOutputs.length > 3 && (
                      <div className="fgb-out-pill pill-more">
                        <span>+{selectedOutputs.length - 3} more</span>
                      </div>
                    )}
                  </div>
                  <div className="fgb-shared-caption">
                    <span>Shared Fact Graph</span>
                    <span className="sub">(One source of truth)</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* ================= COLUMN 3: 03 AUDIENCE & CONTROL ================= */}
          <section className="gen-col col-audience">
            <div className="col-header">
              <span className="col-tag">03 AUDIENCE & CONTROL</span>
              <h2 className="col-title">Audience & control</h2>
              <p className="col-desc">
                Define who will receive the output and how it should be
                presented.
              </p>
            </div>

            {/* Form Controls */}
            <div className="audience-form">
              {/* Target Audience */}
              <div className="form-group">
                <label className="form-label">TARGET AUDIENCE</label>
                <div className="select-wrap">
                  <select
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                  >
                    <option value="Senior Leadership">Senior Leadership</option>
                    <option value="General Public">General Public</option>
                    <option value="Government Officials">
                      Government Officials
                    </option>
                    <option value="Technical Team">Technical Team</option>
                    <option value="Internal / Restricted">
                      Internal / Restricted
                    </option>
                    <option value="Auto">Auto</option>
                  </select>
                  <Icon.Chevron />
                </div>
                <span className="form-hint">
                  High-level, strategic context.
                </span>
              </div>

              {/* Tone */}
              <div className="form-group">
                <label className="form-label">TONE</label>
                <div className="select-wrap">
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                  >
                    <option value="Auto">Auto</option>
                    <option value="Formal">Formal</option>
                    <option value="Reassuring">Reassuring</option>
                    <option value="Neutral">Neutral</option>
                    <option value="Urgent">Urgent</option>
                    <option value="Technical">Technical</option>
                  </select>
                  <Icon.Chevron />
                </div>
                <span className="form-hint">
                  Auto adapts to the selected audience.
                </span>
              </div>

              {/* Language */}
              <div className="form-group">
                <label className="form-label">LANGUAGE</label>
                <div className="select-wrap">
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                  >
                    <option value="Auto">Auto</option>
                    <option value="English">English</option>
                    <option value="Hindi">Hindi</option>
                  </select>
                  <Icon.Chevron />
                </div>
                <span className="form-hint">
                  Matches the source document language.
                </span>
              </div>

              {/* Detail */}
              <div className="form-group">
                <label className="form-label">DETAIL</label>
                <div className="select-wrap">
                  <select
                    value={detail}
                    onChange={(e) => setDetail(e.target.value)}
                  >
                    <option value="Balanced">Balanced</option>
                    <option value="Brief">Brief</option>
                    <option value="Detailed">Detailed</option>
                  </select>
                  <Icon.Chevron />
                </div>
                <span className="form-hint">
                  Right level of depth for the audience.
                </span>
              </div>

              {/* Additional Instructions */}
              <div className="form-group">
                <div className="label-with-count">
                  <label className="form-label">
                    ADDITIONAL INSTRUCTIONS (Optional)
                  </label>
                  <span className="char-count">
                    {instructions.length}/500
                  </span>
                </div>
                <textarea
                  className="instructions-area"
                  rows={3}
                  maxLength={500}
                  placeholder="Add presentation guidance for the selected deliverables..."
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                />
                <div className="instructions-notice">
                  <Icon.Info />
                  <span>Instructions control presentation, not source facts.</span>
                </div>
              </div>

              {/* TRANSFORMATION CONFIGURATION SYSTEM MANIFEST */}
              <div className="manifest-card">
                <div className="manifest-header">
                  <span className="manifest-title">
                    TRANSFORMATION CONFIGURATION
                  </span>
                </div>

                <dl className="manifest-list">
                  <div className="manifest-row">
                    <dt>
                      <Icon.Doc /> Source
                    </dt>
                    <dd>{sourceFile ? sourceFile.name : "None"}</dd>
                  </div>
                  <div className="manifest-row">
                    <dt>
                      <Icon.Share /> Deliverables
                    </dt>
                    <dd>
                      {selectedOutputs.length > 0
                        ? selectedOutputs
                            .slice(0, 3)
                            .map((id) => getDeliverableName(id))
                            .join(" + ") +
                          (selectedOutputs.length > 3
                            ? ` +${selectedOutputs.length - 3}`
                            : "")
                        : "None"}
                    </dd>
                  </div>
                  <div className="manifest-row">
                    <dt>
                      <Icon.Eye /> Audience
                    </dt>
                    <dd>{targetAudience}</dd>
                  </div>
                  <div className="manifest-row">
                    <dt>
                      <Icon.Spark /> Tone
                    </dt>
                    <dd>{tone === "Auto" ? "Auto → Formal" : tone}</dd>
                  </div>
                  <div className="manifest-row">
                    <dt>
                      <Icon.MessageCircle /> Language
                    </dt>
                    <dd>{language}</dd>
                  </div>
                  <div className="manifest-row">
                    <dt>
                      <Icon.FileText /> Detail
                    </dt>
                    <dd>{detail}</dd>
                  </div>
                  <div className="manifest-row">
                    <dt>
                      <Icon.ShieldLock /> Security
                    </dt>
                    <dd className="manifest-sec">
                      <span className="dot-green-small"></span>
                      <span>Sensitivity Firewall Active</span>
                    </dd>
                  </div>
                  <div className="manifest-row">
                    <dt>
                      <Icon.Network /> Fact Base
                    </dt>
                    <dd>One shared Fact / Entity Graph</dd>
                  </div>
                </dl>
              </div>
            </div>
          </section>
        </div>
      </main>

      {/* STICKY BOTTOM ACTION BAR */}
      <footer className="gen-action-bar">
        <div className="action-bar-inner">
          <div className="action-left">
            <div className="req-badge">
              <Icon.Doc />
              <span>TRANSFORMATION REQUEST</span>
            </div>

            <div className="telemetry-item">
              <span className="telem-label">SOURCE</span>
              <span className="telem-value">{sourceFile ? 1 : 0}</span>
            </div>

            <span className="telem-arrow">→</span>

            <div className="telemetry-item">
              <span className="telem-label">OUTPUTS</span>
              <span className="telem-value">{selectedOutputs.length}</span>
            </div>

            <div className="telemetry-item">
              <span className="telem-label">AUDIENCE</span>
              <span className="telem-value">{targetAudience}</span>
            </div>

            <div className="telemetry-item">
              <span className="telem-label">LANGUAGE</span>
              <span className="telem-value">{language}</span>
            </div>

            <div className="telemetry-item">
              <span className="telem-label">SECURITY</span>
              <span className="telem-value val-green">Active</span>
            </div>

            <div className="telemetry-item">
              <span className="telem-label">FACT GRAPH</span>
              <span className="telem-value val-green">Ready</span>
            </div>
          </div>

          <div className="action-right">
            <div className="readiness-note">
              <Icon.CheckCircle />
              <span>
                {selectedOutputs.length} deliverables ready · 1 shared Fact Graph
              </span>
            </div>

            <button
              className="generate-cta-btn"
              type="button"
              disabled={!sourceFile || selectedOutputs.length === 0}
              onClick={startGeneration}
            >
              <span>Generate outputs</span>
              <Icon.ArrowRight />
            </button>
          </div>
        </div>
      </footer>

      {/* ================= MODALS & OVERLAYS ================= */}

      {/* 1. DOCUMENT PREVIEW MODAL */}
      {activeModal === "preview" && (
        <div
          className="modal-overlay"
          onClick={() => setActiveModal(null)}
          role="dialog"
          aria-modal="true"
        >
          <div
            className="modal-window modal-dossier"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-top">
              <div className="modal-title-wrap">
                <Icon.Doc />
                <h3>Source Material Preview — {sourceFile?.name}</h3>
              </div>
              <button
                className="modal-close-btn"
                type="button"
                onClick={() => setActiveModal(null)}
              >
                <Icon.Close />
              </button>
            </div>

            <div className="modal-body doc-reader">
              <div className="doc-reader-meta">
                <span>DOCUMENT CLASSIFICATION: RESTRICTED</span>
                <span>ID: {sourceFile?.id}</span>
                <span>INGESTION: COMPLETE</span>
              </div>
              <div className="doc-reader-content">
                <p>
                  <strong>INCIDENT AND OPERATIONS REPORT // REF: CR-2026-09</strong>
                </p>
                <p>
                  <strong>LOCATION:</strong> Northern Cyber Command Facility, New Delhi, Sector 4
                </p>
                <p>
                  <strong>INCIDENT TIMESTAMP:</strong> 19 September 2026, 14:32 IST
                </p>
                <p>
                  <strong>PRIMARY OFFICER:</strong> Dr. V. Sharma, Director of Threat Systems
                </p>
                <p>
                  <strong>INCIDENT SUMMARY:</strong> At 14:32 IST, automated monitoring systems flagged an unauthorized telemetry beacon from internal segment 10.42.18.9. Security protocols isolated the affected relay server within 42 seconds. No exfiltration occurred. Forensic analysis verified all perimeter cryptographic certificates intact. 2.4 GB of event logs were preserved for audit.
                </p>
                <p>
                  <strong>ASSESSMENT:</strong> The situation is under full containment. Zero operational downtime recorded. Follow-up review scheduled for 20 September 2026.
                </p>
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => setActiveModal(null)}
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. SOURCE DETAILS MODAL */}
      {activeModal === "details" && (
        <div
          className="modal-overlay"
          onClick={() => setActiveModal(null)}
          role="dialog"
        >
          <div
            className="modal-window modal-telemetry"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-top">
              <div className="modal-title-wrap">
                <Icon.CheckCircle />
                <h3>Source Ingestion & Fact Graph Metadata</h3>
              </div>
              <button
                className="modal-close-btn"
                type="button"
                onClick={() => setActiveModal(null)}
              >
                <Icon.Close />
              </button>
            </div>

            <div className="modal-body">
              <div className="details-grid">
                <div className="detail-card">
                  <span className="det-label">CANONICAL SOURCE HASH</span>
                  <span className="det-val font-mono">
                    4b6a2f91ec7208d17b89c3...7d1e
                  </span>
                </div>
                <div className="detail-card">
                  <span className="det-label">DETECTED LANGUAGE</span>
                  <span className="det-val">English (99.8% confidence)</span>
                </div>
                <div className="detail-card">
                  <span className="det-label">EXTRACTED ENTITIES</span>
                  <span className="det-val">
                    8 Entities (ORG, PERSON, LOCATION, UNIT)
                  </span>
                </div>
                <div className="detail-card">
                  <span className="det-label">NUMBERS & DATES</span>
                  <span className="det-val">
                    6 temporal and numeric constraints
                  </span>
                </div>
              </div>

              <h4 className="sub-heading">CANONICAL FACT STATEMENTS</h4>
              <ul className="fact-sample-list">
                <li>• Breach attempt occurred at 14:32 IST on 19 Sept 2026.</li>
                <li>• Relay server isolated within 42 seconds of detection.</li>
                <li>• Zero data exfiltration verified by telemetry audit.</li>
                <li>• 2.4 GB forensic event logs safely cataloged.</li>
              </ul>
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => setActiveModal(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. SECURITY ACTIONS MODAL */}
      {activeModal === "security" && (
        <div
          className="modal-overlay"
          onClick={() => setActiveModal(null)}
          role="dialog"
        >
          <div
            className="modal-window modal-security"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-top">
              <div className="modal-title-wrap">
                <Icon.ShieldLock />
                <h3>Sensitivity Firewall — Pre-Generation Protections</h3>
              </div>
              <button
                className="modal-close-btn"
                type="button"
                onClick={() => setActiveModal(null)}
              >
                <Icon.Close />
              </button>
            </div>

            <div className="modal-body">
              <p className="sec-note">
                The Sensitivity Firewall has cataloged 4 sensitive tokens from the source. The raw source remains available to generation, while these findings will require explicit human review (disclose, withhold, or edit) prior to final approval and ledger recording.
              </p>

              <table className="sec-table">
                <thead>
                  <tr>
                    <th>CATEGORY</th>
                    <th>DETECTED TOKEN</th>
                    <th>PLACEHOLDER</th>
                    <th>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><span className="pill-cat cat-loc">LOCATION</span></td>
                    <td>New Delhi, Sector 4</td>
                    <td><code>[LOCATION_1]</code></td>
                    <td><span className="tag-rev">Review Required</span></td>
                  </tr>
                  <tr>
                    <td><span className="pill-cat cat-unit">UNIT_NAME</span></td>
                    <td>Northern Cyber Command</td>
                    <td><code>[UNIT_NAME_1]</code></td>
                    <td><span className="tag-rev">Review Required</span></td>
                  </tr>
                  <tr>
                    <td><span className="pill-cat cat-person">PERSON</span></td>
                    <td>Dr. V. Sharma</td>
                    <td><code>[PERSON_1]</code></td>
                    <td><span className="tag-rev">Review Required</span></td>
                  </tr>
                  <tr>
                    <td><span className="pill-cat cat-loc">LOCATION</span></td>
                    <td>Facility Room 402B</td>
                    <td><code>[LOCATION_2]</code></td>
                    <td><span className="tag-rev">Review Required</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => setActiveModal(null)}
              >
                Acknowledge Protections
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. PROCESSING PIPELINE OVERLAY */}
      {activeModal === "processing" && (
        <div className="modal-overlay modal-overlay-dark" role="dialog">
          <div className="modal-window modal-processing">
            <div className="processing-header">
              <span className="proc-spark">✦</span>
              <h3>Executing Transformation Pipeline</h3>
              <p>One canonical Fact Graph · Multi-Adapter Fan-Out</p>
            </div>

            <div className="processing-stages-track">
              <div className={`proc-step ${processingStage >= 1 ? "is-done" : ""}`}>
                <div className="proc-bullet">{processingStage > 1 ? "✓" : "1"}</div>
                <div className="proc-info">
                  <h4>UNDERSTAND</h4>
                  <p>Extracting facts, dates, entities & relationships...</p>
                </div>
              </div>

              <div className={`proc-step ${processingStage >= 2 ? "is-done" : ""}`}>
                <div className="proc-bullet">{processingStage > 2 ? "✓" : "2"}</div>
                <div className="proc-info">
                  <h4>CONTROL</h4>
                  <p>Running Sensitivity Firewall & Disclosure categorization...</p>
                </div>
              </div>

              <div className={`proc-step ${processingStage >= 3 ? "is-done" : ""}`}>
                <div className="proc-bullet">{processingStage > 3 ? "✓" : "3"}</div>
                <div className="proc-info">
                  <h4>GENERATE</h4>
                  <p>Fanning out to {selectedOutputs.length} adapters simultaneously...</p>
                </div>
              </div>

              <div className={`proc-step ${processingStage >= 4 ? "is-done" : ""}`}>
                <div className="proc-bullet">{processingStage >= 4 ? "✓" : "4"}</div>
                <div className="proc-info">
                  <h4>VERIFY</h4>
                  <p>Grounding Guard checking claim citations & consistency...</p>
                </div>
              </div>
            </div>

            <div className="proc-pulse-bar">
              <div className="proc-pulse-fill"></div>
            </div>
          </div>
        </div>
      )}

      {/* 5. GENERATED RESULTS MODAL */}
      {activeModal === "results" && generatedDrafts && (
        <div className="modal-overlay" role="dialog">
          <div className="modal-window modal-results">
            <div className="modal-top">
              <div className="modal-title-wrap">
                <Icon.Spark />
                <h3>Transformation Complete — {generatedDrafts.drafts.length} Deliverables Generated</h3>
              </div>
              <button
                className="modal-close-btn"
                type="button"
                onClick={() => setActiveModal(null)}
              >
                <Icon.Close />
              </button>
            </div>

            <div className="modal-body">
              {/* Trust Score Telemetry Banner */}
              <div className="trust-score-banner">
                <div className="ts-main">
                  <span className="ts-label">COMPOSITE TRUST INDEX</span>
                  <span className="ts-val">
                    {generatedDrafts.trust_score.composite}%
                  </span>
                </div>
                <div className="ts-subscores">
                  <div className="ts-metric">
                    <span className="metric-name">Grounding</span>
                    <span className="metric-num">
                      {generatedDrafts.trust_score.grounding}%
                    </span>
                  </div>
                  <div className="ts-metric">
                    <span className="metric-name">Consistency</span>
                    <span className="metric-num">
                      {generatedDrafts.trust_score.consistency}%
                    </span>
                  </div>
                  <div className="ts-metric">
                    <span className="metric-name">Policy</span>
                    <span className="metric-num">
                      {generatedDrafts.trust_score.policy}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Draft Tabs & Content Previews */}
              <div className="drafts-results-list">
                {generatedDrafts.drafts.map((draft) => (
                  <div key={draft.id} className="draft-result-card">
                    <div className="draft-card-head">
                      <span className="draft-tag">{draft.title}</span>
                      <span className="draft-status-pill">
                        <Icon.CheckCircle /> {draft.status}
                      </span>
                    </div>
                    <pre className="draft-content-text">{draft.content}</pre>
                  </div>
                ))}
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn-secondary"
                type="button"
                onClick={() => setActiveModal(null)}
              >
                Back to Workspace
              </button>
              <a className="btn-secondary" href="/refine">
                <Icon.EditRefine />
                <span>Refine Deliverable</span>
              </a>
              <a className="btn-primary" href="/dashboard#review">
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
