import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import TopBar from "../components/TopBar.jsx";
import workflowStore from "../services/workflowStore.js";
import "./ResultPage.css";

/* ---------------------------------- Icons --------------------------------- */

const Icon = {
  Doc: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.5 3.5h8L19 8v12a1 1 0 0 1-1 1h-11.5a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
      <path d="M14 3.5V8h5" />
      <path d="M8.5 12.5h7M8.5 15.5h7M8.5 18h4" />
    </svg>
  ),
  Spark: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
    </svg>
  ),
  ArrowRight: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  ),
  EditPen: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  ),
  Presentation: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  ),
  Infographic: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  ),
  Video: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polygon points="23 7 16 12 23 17 23 7" />
      <rect x="1" y="5" width="15" height="14" rx="2" />
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
  Clipboard: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <rect x="8" y="2" width="8" height="4" rx="1" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  Layers: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  ),
};

const DELIVERABLE_LABELS = {
  executive_summary: { label: "Executive Summary", icon: Icon.Doc, group: "Briefing & Reports" },
  linkedin_post: { label: "LinkedIn Post", icon: Icon.Share, group: "Public Communication" },
  twitter_thread: { label: "X / Twitter Thread", icon: Icon.Share, group: "Public Communication" },
  press_release: { label: "Press Release", icon: Icon.Doc, group: "Public Communication" },
  public_faq: { label: "Public FAQ", icon: Icon.Clipboard, group: "Public Communication" },
  advisory: { label: "Advisory", icon: Icon.Doc, group: "Public Communication" },
  briefing_note: { label: "Briefing Note", icon: Icon.Clipboard, group: "Briefing & Reports" },
  sitrep: { label: "SITREP", icon: Icon.Doc, group: "Briefing & Reports" },
  incident_report: { label: "Incident Report", icon: Icon.Doc, group: "Briefing & Reports" },
  presentation: { label: "Presentation", icon: Icon.Presentation, group: "Structured Content" },
  infographic: { label: "Infographic", icon: Icon.Infographic, group: "Structured Content" },
  video_package: { label: "Video Package", icon: Icon.Video, group: "Structured Content" },
  custom: { label: "Custom Deliverable", icon: Icon.Doc, group: "Custom" },
};

export default function ResultPage() {
  const navigate = useNavigate();
  const [workflowState, setWorkflowState] = useState(workflowStore.getState());

  useEffect(() => {
    document.title = "SriGEN — Generated Content";
    const unsubscribe = workflowStore.subscribe((newState) => {
      setWorkflowState({ ...newState });
    });
    return unsubscribe;
  }, []);

  const { drafts, selectedDraftId, source } = workflowState;
  const activeDraft = drafts.find((d) => d.id === selectedDraftId) || drafts[0] || null;
  const activeMeta = activeDraft ? DELIVERABLE_LABELS[activeDraft.deliverable_type] || { label: activeDraft.deliverable_type, icon: Icon.Doc, group: "Deliverable" } : null;

  const handleSelectDraft = (id) => {
    workflowStore.setSelectedDraftId(id);
  };

  const handleRefine = () => {
    navigate("/refine");
  };

  const handleProceedToVerify = () => {
    navigate("/verify-review");
  };

  // Calculate stats for selected draft
  const wordCount = activeDraft?.draft_content?.trim()
    ? activeDraft.draft_content.trim().split(/\s+/).length
    : 0;
  const charCount = activeDraft?.draft_content?.length || 0;
  const estimatedReadTime = Math.max(1, Math.ceil(wordCount / 200));

  return (
    <div className="res-page">
      {/* GLOBAL MASTER TOP BAR */}
      <TopBar activePage="result" />

      {/* COMPACT HERO */}
      <section className="res-hero">
        <div className="res-hero-inner">
          <div className="res-hero-eyebrow-row">
            <span className="res-eyebrow">TRANSFORMATION OUTPUT</span>
            <span className="res-hero-badge">
              <span className="res-badge-dot"></span>
              {drafts.length} DELIVERABLES SYNTHESIZED
            </span>
          </div>
          <h1 className="res-headline">Generated Content.</h1>
          <p className="res-subtext">
            Review your generated deliverables synthesized from source evidence before proceeding to verification and review.
          </p>
        </div>
      </section>

      {/* WORKSPACE LAYOUT */}
      <main className="res-workspace">
        <div className="res-layout-grid">
          {/* ================= LEFT COLUMN: DELIVERABLE SELECTOR ================= */}
          <aside className="res-sidebar">
            <div className="res-source-banner">
              <div className="res-source-icon">
                <Icon.Doc />
              </div>
              <div className="res-source-details">
                <span className="res-source-label">CANONICAL BASIS</span>
                <span className="res-source-title" title={source?.name || "Source document"}>
                  {source?.name || "source_material.pdf"}
                </span>
                <span className="res-source-meta">
                  {source?.type || "PDF"} · {source?.size || "2.4 MB"}
                </span>
              </div>
            </div>

            <div className="res-selector-box">
              <div className="res-selector-head">
                <span className="res-selector-title">GENERATED DELIVERABLES</span>
                <span className="res-count-pill">{drafts.length}</span>
              </div>

              <div className="res-deliverable-list" role="tablist">
                {drafts.map((draft) => {
                  const isSelected = draft.id === activeDraft?.id;
                  const meta = DELIVERABLE_LABELS[draft.deliverable_type] || {
                    label: draft.deliverable_type,
                    icon: Icon.Doc,
                    group: "Deliverable",
                  };
                  const DeliverableIcon = meta.icon;
                  const dWordCount = draft.draft_content?.trim()
                    ? draft.draft_content.trim().split(/\s+/).length
                    : 0;

                  return (
                    <button
                      key={draft.id}
                      type="button"
                      role="tab"
                      aria-selected={isSelected}
                      className={`res-nav-item ${isSelected ? "is-selected" : ""}`}
                      onClick={() => handleSelectDraft(draft.id)}
                    >
                      <div className="res-nav-icon">
                        <DeliverableIcon />
                      </div>
                      <div className="res-nav-info">
                        <span className="res-nav-label">{meta.label}</span>
                        <span className="res-nav-group">{meta.group} · {dWordCount} words</span>
                      </div>
                      {isSelected && (
                        <span className="res-nav-active-pill" aria-hidden="true">
                          <Icon.Check />
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </aside>

          {/* ================= MAIN COLUMN: EDITORIAL CREAM DOCUMENT ================= */}
          <section className="res-content-view">
            {activeDraft ? (
              <article className="res-document-paper">
                {/* Document Header */}
                <header className="res-doc-header">
                  <div className="res-doc-header-top">
                    <span className="res-doc-type-stamp">
                      {activeMeta?.group} · {activeMeta?.label.toUpperCase()}
                    </span>
                    <span className="res-doc-status-badge">
                      <span className="status-dot"></span>
                      SYNTHESIZED DRAFT
                    </span>
                  </div>

                  <div className="res-doc-meta-bar">
                    <span className="res-meta-item">
                      <strong>Basis:</strong> {source?.name || "Canonical source"}
                    </span>
                    <span className="res-meta-sep">/</span>
                    <span className="res-meta-item">
                      <strong>Volume:</strong> {wordCount} words ({charCount} chars)
                    </span>
                    <span className="res-meta-sep">/</span>
                    <span className="res-meta-item">
                      <strong>Read time:</strong> ~{estimatedReadTime} min
                    </span>
                  </div>
                </header>

                {/* Document Content Render */}
                <div className="res-doc-body">
                  {activeDraft.structured_content ? (
                    /* Structured Content Presentation (Presentation / Infographic / Video) */
                    <div className="res-structured-package">
                      {activeDraft.deliverable_type === "presentation" && activeDraft.structured_content.slides && (
                        <div className="res-slides-container">
                          <div className="res-pkg-title-banner">
                            <h3>{activeDraft.structured_content.title}</h3>
                            {activeDraft.structured_content.subtitle && (
                              <p>{activeDraft.structured_content.subtitle}</p>
                            )}
                          </div>
                          <div className="res-slides-grid">
                            {activeDraft.structured_content.slides.map((slide) => (
                              <div key={slide.slide_number} className="res-slide-card">
                                <div className="res-slide-head">
                                  <span className="slide-num">SLIDE {slide.slide_number}</span>
                                  <span className="slide-layout">{slide.layout}</span>
                                </div>
                                <h4 className="slide-title">{slide.title}</h4>
                                <ul className="slide-bullets">
                                  {slide.bullets.map((b, idx) => (
                                    <li key={idx}>{b}</li>
                                  ))}
                                </ul>
                                {slide.speaker_notes && (
                                  <div className="slide-notes">
                                    <span className="notes-label">Speaker Notes:</span>
                                    <p>{slide.speaker_notes}</p>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {activeDraft.deliverable_type === "infographic" && activeDraft.structured_content.sections && (
                        <div className="res-infographic-container">
                          <div className="res-pkg-title-banner">
                            <h3>{activeDraft.structured_content.title}</h3>
                            <p className="res-pkg-keymsg">
                              <strong>Key Message:</strong> {activeDraft.structured_content.key_message}
                            </p>
                          </div>
                          <div className="res-info-sections-grid">
                            {activeDraft.structured_content.sections.map((sec, idx) => (
                              <div key={idx} className="res-info-card">
                                {sec.stat_value && (
                                  <div className="res-info-stat">
                                    <span className="stat-val">{sec.stat_value}</span>
                                    {sec.stat_label && <span className="stat-lbl">{sec.stat_label}</span>}
                                  </div>
                                )}
                                <h4 className="res-info-heading">{sec.heading}</h4>
                                <p className="res-info-body">{sec.body}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {activeDraft.deliverable_type === "video_package" && activeDraft.structured_content.scenes && (
                        <div className="res-video-container">
                          <div className="res-pkg-title-banner">
                            <h3>{activeDraft.structured_content.title}</h3>
                            <p>Duration: {activeDraft.structured_content.total_duration_seconds} seconds</p>
                          </div>
                          <div className="res-scenes-list">
                            {activeDraft.structured_content.scenes.map((scene) => (
                              <div key={scene.scene_number} className="res-scene-row">
                                <div className="scene-time-col">
                                  <span className="scene-num">Scene {scene.scene_number}</span>
                                  <span className="scene-time">
                                    {scene.start_seconds}s - {scene.end_seconds}s
                                  </span>
                                </div>
                                <div className="scene-content-col">
                                  <div className="scene-visual">
                                    <strong>Visual:</strong> {scene.visual_description}
                                  </div>
                                  <div className="scene-narration">
                                    <strong>Narration:</strong> "{scene.narration}"
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Plain Text / Editorial Markdown Render */
                    <div className="res-prose-content">
                      {activeDraft.draft_content.split("\n\n").map((para, pIdx) => {
                        const trimmed = para.trim();
                        if (trimmed.startsWith("# ")) {
                          return <h1 key={pIdx} className="res-h1">{trimmed.replace("# ", "")}</h1>;
                        }
                        if (trimmed.startsWith("## ")) {
                          return <h2 key={pIdx} className="res-h2">{trimmed.replace("## ", "")}</h2>;
                        }
                        if (trimmed.startsWith("### ")) {
                          return <h3 key={pIdx} className="res-h3">{trimmed.replace("### ", "")}</h3>;
                        }
                        if (trimmed.startsWith("- ") || trimmed.startsWith("✔ ") || trimmed.startsWith("* ")) {
                          const items = trimmed.split("\n").map((line) => line.replace(/^[-✔*]\s*/, ""));
                          return (
                            <ul key={pIdx} className="res-ul">
                              {items.map((it, itIdx) => (
                                <li key={itIdx}>{it}</li>
                              ))}
                            </ul>
                          );
                        }
                        if (/^\d+\.\s/.test(trimmed)) {
                          const items = trimmed.split("\n").map((line) => line.replace(/^\d+\.\s*/, ""));
                          return (
                            <ol key={pIdx} className="res-ol">
                              {items.map((it, itIdx) => (
                                <li key={itIdx}>{it}</li>
                              ))}
                            </ol>
                          );
                        }
                        return <p key={pIdx} className="res-p">{trimmed}</p>;
                      })}
                    </div>
                  )}
                </div>

                {/* Document Footer Notice */}
                <footer className="res-doc-footer">
                  <div className="res-footer-tag">CANONICAL ARTIFACT · UNVERIFIED DRAFT</div>
                  <p className="res-footer-note">
                    This deliverable has been synthesized from source evidence under operator specifications. Proceed to Verify & Review to inspect grounding claims, sibling consistency, and disclosure controls.
                  </p>
                </footer>
              </article>
            ) : (
              <div className="res-empty-state">
                <Icon.Doc />
                <h3>No Deliverables Generated</h3>
                <p>Generate deliverables from source material to view them here.</p>
                <button
                  type="button"
                  className="res-btn-primary"
                  onClick={() => navigate("/generate")}
                >
                  Go to Generate
                </button>
              </div>
            )}

            {/* STICKY WORKFLOW ACTION BAR */}
            {activeDraft && (
              <div className="res-actions-bar">
                <button
                  type="button"
                  className="res-btn-refine"
                  onClick={handleRefine}
                  title="Modify content, dimensions, or instructions in Refine mode"
                >
                  <Icon.EditPen />
                  <span>Refine Deliverable</span>
                </button>

                <button
                  type="button"
                  className="res-btn-verify"
                  onClick={handleProceedToVerify}
                  title="Proceed to full verification and review"
                >
                  <span>Verify & Review</span>
                  <Icon.ArrowRight />
                </button>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
