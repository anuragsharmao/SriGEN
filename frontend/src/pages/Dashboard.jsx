import { useEffect, useState } from "react";
import TopBar from "../components/TopBar.jsx";
import "./Dashboard.css";

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
  Doc: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.5 3.5h8L19 8v12a1 1 0 0 1-1 1h-11.5a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
      <path d="M14 3.5V8h5" />
      <path d="M8.5 12.5h7M8.5 15.5h7M8.5 18h4" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.3 10.8 15 16 9.5" />
    </svg>
  ),
  CheckCircle: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.5 2.5 5-5" />
    </svg>
  ),
  CheckShield: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.5 20 6v6c0 5.2-3.4 9.1-8 10.5C7.4 21.1 4 17.2 4 12V6l8-3.5Z" />
      <path d="M8.5 12.3 11 14.7 15.5 9.5" />
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
  Arrow: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 12h15M13 6l6 6-6 6" />
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
  Person: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="8.5" r="3.2" />
      <path d="M5.5 19c.9-3.3 3.1-5 6.5-5s5.6 1.7 6.5 5" />
    </svg>
  ),
  Calendar: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4" y="5.5" width="16" height="14" rx="1.5" />
      <path d="M4 9.5h16M8 3.5v3M16 3.5v3" />
    </svg>
  ),
  Hash: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 4 7 20M17 4l-2 16M4.5 9h15M3.5 15h15" />
    </svg>
  ),
  Pin: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 21s7-6.3 7-11.5A7 7 0 0 0 5 9.5C5 14.7 12 21 12 21Z" />
      <circle cx="12" cy="9.5" r="2.3" />
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
  EditRefine: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  ),
  SearchCheck: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
      <path d="m9 11 1.5 1.5 3-3" />
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
  Bell: () => (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  ),
};

/* --------------------------------- content --------------------------------- */

const PROCESS_STAGES = [
  {
    id: "understand",
    n: "01",
    title: "UNDERSTAND",
    stageTag: "Source Ingest",
    body: "Extract facts, entities, dates and relationships.",
    icon: "Network",
    tone: "ochre",
    highlights: ["source", "understand"],
  },
  {
    id: "control",
    n: "02",
    title: "CONTROL",
    stageTag: "Firewall Guard",
    body: "Classify sensitivity and protect restricted information.",
    icon: "ShieldLock",
    tone: "terracotta",
    highlights: ["control"],
  },
  {
    id: "generate",
    n: "03",
    title: "GENERATE",
    stageTag: "Grounded Graph",
    body: "Create audience-aware deliverables.",
    icon: "Spark",
    tone: "teal",
    highlights: ["graph", "outputs"],
  },
  {
    id: "refine",
    n: "04",
    title: "REFINE",
    stageTag: "Evidence Checking",
    body: "Check existing content against evidence, then improve and adapt it while preserving intent and voice.",
    icon: "EditRefine",
    tone: "green",
    highlights: ["guard", "control"],
  },
  {
    id: "review",
    n: "05",
    title: "REVIEW",
    stageTag: "Human Sign-off",
    body: "Inspect evidence and approve the result.",
    icon: "Eye",
    tone: "amber",
    highlights: ["guard", "outputs"],
  },
  {
    id: "prove",
    n: "06",
    title: "PROVE",
    stageTag: "Audit Provenance",
    body: "Record provenance after approval.",
    icon: "Link",
    tone: "dark-green",
    highlights: ["provenance"],
  },
];

const CAPABILITIES = [
  {
    icon: "Network",
    title: "GROUNDED GENERATION",
    body: "Outputs are generated from a structured Fact / Entity Graph.",
  },
  {
    icon: "ShieldLock",
    title: "SENSITIVITY FIREWALL",
    body: "Sensitive information is classified and protected before generation.",
  },
  {
    icon: "SearchCheck",
    title: "REFINE + VERIFICATION GUARD",
    body: "Existing content can be checked against source evidence, with unsupported or contradicted claims surfaced for review.",
  },
  {
    icon: "Person",
    title: "HUMAN APPROVAL",
    body: "The operator remains in control before it becomes final.",
  },
  {
    icon: "Link",
    title: "PROVENANCE",
    body: "Approved artifacts receive a traceable provenance record.",
  },
];

/* --------------------------------- component -------------------------------- */

export default function Dashboard() {
  const [hovered, setHovered] = useState(null);

  useEffect(() => {
    document.title = "SriGEN — Transform Intelligence. Prove What Changed.";
  }, []);

  useEffect(() => {
    const els = document.querySelectorAll(".dash .reveal");
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("in-view"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const activeHighlights =
    PROCESS_STAGES.find((s) => s.id === hovered)?.highlights ?? [];

  return (
    <div className="dash">
      {/* GLOBAL NAVIGATION */}
      <TopBar activePage="home" />

      {/* HERO SECTION / DARK INTELLIGENCE SURFACE */}
      <section className="dash-hero" id="home">
        {/* Subtle authentic topographic vector contour backdrop */}
        <div className="hero-topographic-bg" aria-hidden="true">
          <svg viewBox="0 0 1600 700" preserveAspectRatio="xMidYMid slice">
            <path
              d="M-50,120 Q300,90 600,180 T1200,130 T1700,240"
              fill="none"
              stroke="rgba(208, 154, 69, 0.06)"
              strokeWidth="1.2"
            />
            <path
              d="M-50,220 Q250,280 650,230 T1250,300 T1700,280"
              fill="none"
              stroke="rgba(208, 154, 69, 0.045)"
              strokeWidth="1.2"
            />
            <path
              d="M-50,340 Q350,420 750,320 T1350,410 T1700,370"
              fill="none"
              stroke="rgba(208, 154, 69, 0.04)"
              strokeWidth="1.2"
            />
            <path
              d="M-50,480 Q400,430 800,520 T1400,480 T1700,560"
              fill="none"
              stroke="rgba(208, 154, 69, 0.03)"
              strokeWidth="1.2"
            />
            <line x1="200" y1="0" x2="200" y2="700" stroke="rgba(245, 241, 232, 0.02)" strokeDasharray="4 8" />
            <line x1="600" y1="0" x2="600" y2="700" stroke="rgba(245, 241, 232, 0.02)" strokeDasharray="4 8" />
            <line x1="1050" y1="0" x2="1050" y2="700" stroke="rgba(245, 241, 232, 0.02)" strokeDasharray="4 8" />
            <line x1="1450" y1="0" x2="1450" y2="700" stroke="rgba(245, 241, 232, 0.02)" strokeDasharray="4 8" />
          </svg>
        </div>

        <div className="dash-hero-inner">
          {/* LEFT: EDITORIAL VALUE PROPOSITION & ENTRY CARDS */}
          <div className="dash-hero-left">
            <div className="dash-eyebrow reveal r0">
              SECURE GENERATIVE AI PLATFORM
            </div>

            <h1 className="dash-headline reveal r0">
              Transform intelligence.
              <br />
              <span className="dash-headline-accent">Prove what changed.</span>
            </h1>

            <p className="dash-sub reveal r0">
              Turn source material into grounded, audience-aware intelligence products
              — with verification, human review, and provenance built into the process.
            </p>

            {/* DUAL ENTRY WORKFLOW DOORS */}
            <div className="dash-actions reveal r1">
              {/* 1. GENERATE ENTRY PANEL */}
              <a className="door-panel door-generate" href="/generate">
                <div className="door-top">
                  <div className="door-badge door-badge-gen">
                    <Icon.Doc />
                  </div>
                  <div className="door-meta">
                    <span className="door-label">GENERATE</span>
                  </div>
                  <span className="door-arrow">
                    <Icon.Arrow />
                  </span>
                </div>
                <p className="door-desc">
                  Transform source material into controlled intelligence deliverables.
                </p>
              </a>

              {/* 2. REFINE ENTRY PANEL */}
              <a className="door-panel door-refine" href="/refine">
                <div className="door-top">
                  <div className="door-badge door-badge-refine">
                    <Icon.EditRefine />
                  </div>
                  <div className="door-meta">
                    <span className="door-label">REFINE</span>
                  </div>
                  <span className="door-arrow">
                    <Icon.Arrow />
                  </span>
                </div>
                <p className="door-desc">
                  Improve existing content against source evidence while preserving intent and voice.
                </p>
              </a>
            </div>
          </div>

          {/* RIGHT: INTELLIGENCE TRANSMISSION VISUALIZATION */}
          <div className="transmission-wrapper reveal r2">
            <div className="transmission-frame">
              {/* Corner evidence brackets */}
              <span className="tr-corner tr-corner-tl" aria-hidden="true" />
              <span className="tr-corner tr-corner-tr" aria-hidden="true" />
              <span className="tr-corner tr-corner-bl" aria-hidden="true" />
              <span className="tr-corner tr-corner-br" aria-hidden="true" />

              <div className="transmission-header">
                <div className="tr-header-title">
                  <span className="tr-sparkle">✦</span>
                  <h3>INTELLIGENCE TRANSMISSION</h3>
                </div>
                <p className="tr-subtitle">
                  One trusted fact base. Multiple controlled transformations.
                </p>
              </div>

              {/* HORIZONTAL ARCHITECTURE FLOW PIPELINE */}
              <div className="transmission-pipeline">
                {/* 1. SOURCE */}
                <div
                  className={`pipe-stage pipe-source ${
                    activeHighlights.includes("source") ? "is-highlighted" : ""
                  }`}
                >
                  <span className="pipe-col-label">SOURCE</span>
                  <div className="pipe-doc-preview">
                    <div className="doc-sheet">
                      <div className="doc-sheet-header">
                        <span className="doc-micro-dot"></span>
                        <span className="doc-micro-dot"></span>
                        <span className="doc-micro-dot"></span>
                      </div>
                      <div className="doc-sheet-body">
                        <span className="doc-line w-85"></span>
                        <span className="doc-line w-60"></span>
                        <span className="doc-line w-75"></span>
                        <span className="doc-line w-90"></span>
                        <span className="doc-line w-50"></span>
                        <span className="doc-sheet-seal">CONFIDENTIAL</span>
                      </div>
                      {/* Scanning laser beam effect */}
                      <span className="doc-laser-scan" aria-hidden="true"></span>
                    </div>
                  </div>
                  <div className="pipe-caption">
                    <span className="pipe-filename">incident_report.pdf</span>
                    <span className="pipe-formats">PDF / DOCX / TXT / MD</span>
                  </div>
                </div>

                {/* Arrow 1 */}
                <div className="pipe-arrow">
                  <Icon.ArrowRight />
                </div>

                {/* 2. UNDERSTAND */}
                <div
                  className={`pipe-stage pipe-understand ${
                    activeHighlights.includes("understand") ? "is-highlighted" : ""
                  }`}
                >
                  <span className="pipe-col-label">UNDERSTAND</span>
                  <div className="pipe-card card-understand">
                    <ul className="fact-extract-list">
                      <li className="fact-item">
                        <span className="fact-icon"><Icon.Person /></span>
                        <span className="fact-name">ENTITY</span>
                      </li>
                      <li className="fact-item">
                        <span className="fact-icon"><Icon.Calendar /></span>
                        <span className="fact-name">DATE</span>
                      </li>
                      <li className="fact-item">
                        <span className="fact-icon"><Icon.Hash /></span>
                        <span className="fact-name">NUMBER</span>
                      </li>
                      <li className="fact-item">
                        <span className="fact-icon"><Icon.Pin /></span>
                        <span className="fact-name">LOCATION</span>
                      </li>
                    </ul>
                  </div>
                </div>

                {/* Arrow 2 */}
                <div className="pipe-arrow">
                  <Icon.ArrowRight />
                </div>

                {/* 3. CONTROL (SENSITIVITY FIREWALL) */}
                <div
                  className={`pipe-stage pipe-control ${
                    activeHighlights.includes("control") ? "is-highlighted" : ""
                  }`}
                >
                  <span className="pipe-col-label">CONTROL</span>
                  <div className="pipe-card card-firewall">
                    <div className="firewall-badge">
                      <Icon.ShieldLock />
                      <span>SENSITIVITY FIREWALL</span>
                    </div>
                    <ul className="firewall-tokens">
                      <li className="token-item">
                        <span className="token-dot dot-green"></span>
                        <span className="token-text">LOCATION</span>
                      </li>
                      <li className="token-item">
                        <span className="token-dot dot-red"></span>
                        <span className="token-text">UNIT_NAME</span>
                      </li>
                      <li className="token-item">
                        <span className="token-dot dot-amber"></span>
                        <span className="token-text">PERSON</span>
                      </li>
                    </ul>
                  </div>
                </div>

                {/* Arrow 3 */}
                <div className="pipe-arrow">
                  <Icon.ArrowRight />
                </div>

                {/* 4. FACT / ENTITY GRAPH */}
                <div
                  className={`pipe-stage pipe-graph ${
                    activeHighlights.includes("graph") ? "is-highlighted" : ""
                  }`}
                >
                  <span className="pipe-col-label">FACT / ENTITY GRAPH</span>
                  <div className="pipe-card card-graph">
                    <div className="graph-visual">
                      <svg viewBox="0 0 120 100" className="kg-svg" aria-hidden="true">
                        {/* Connecting fine graph edges */}
                        <g className="kg-edges">
                          <line x1="60" y1="20" x2="25" y2="48" />
                          <line x1="60" y1="20" x2="95" y2="45" />
                          <line x1="25" y1="48" x2="60" y2="78" />
                          <line x1="95" y1="45" x2="60" y2="78" />
                          <line x1="25" y1="48" x2="95" y2="45" />
                          <line x1="60" y1="20" x2="60" y2="78" strokeDasharray="2 3" />
                        </g>
                        {/* Orbiting / pulsing nodes */}
                        <circle className="kg-node node-gold" cx="60" cy="20" r="5.5" />
                        <circle className="kg-node node-red" cx="25" cy="48" r="5" />
                        <circle className="kg-node node-teal" cx="95" cy="45" r="5" />
                        <circle className="kg-node node-green" cx="60" cy="78" r="5.5" />
                        <circle className="kg-node node-center" cx="60" cy="49" r="3.5" />
                      </svg>
                    </div>
                    <span className="graph-caption">
                      Structured intelligence knowledge graph
                    </span>
                  </div>
                </div>

                {/* Arrow 4 */}
                <div className="pipe-arrow">
                  <Icon.ArrowRight />
                </div>

                {/* 5. GROUNDING GUARD */}
                <div
                  className={`pipe-stage pipe-guard ${
                    activeHighlights.includes("guard") ? "is-highlighted" : ""
                  }`}
                >
                  <span className="pipe-col-label">GROUNDING GUARD</span>
                  <div className="pipe-card card-guard">
                    <ul className="guard-checks">
                      <li className="guard-item">
                        <span className="guard-icon"><Icon.CheckCircle /></span>
                        <span className="guard-text">GROUNDING</span>
                      </li>
                      <li className="guard-item">
                        <span className="guard-icon"><Icon.CheckCircle /></span>
                        <span className="guard-text">CONSISTENCY</span>
                      </li>
                      <li className="guard-item">
                        <span className="guard-icon"><Icon.CheckCircle /></span>
                        <span className="guard-text">POLICY</span>
                      </li>
                    </ul>
                  </div>
                </div>

                {/* Arrow 5 */}
                <div className="pipe-arrow">
                  <Icon.ArrowRight />
                </div>

                {/* 6. CONTROLLED OUTPUTS */}
                <div
                  className={`pipe-stage pipe-outputs ${
                    activeHighlights.includes("outputs") ? "is-highlighted" : ""
                  }`}
                >
                  <span className="pipe-col-label">CONTROLLED OUTPUTS</span>
                  <div className="output-pills-stack">
                    <div className="out-pill">
                      <Icon.Doc />
                      <span>Executive Summary</span>
                    </div>
                    <div className="out-pill">
                      <Icon.Share />
                      <span>LinkedIn Post</span>
                    </div>
                    <div className="out-pill">
                      <Icon.Bell />
                      <span>Advisory</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* BOTTOM TRANSMISSION PRINCIPLE BANNER */}
              <div
                className={`transmission-footer-rule ${
                  activeHighlights.includes("provenance") ? "is-highlighted-rule" : ""
                }`}
              >
                <span className="rule-badge">
                  ONE TRUSTED FACT BASE &nbsp;✦&nbsp; MULTIPLE CONTROLLED TRANSFORMATIONS
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* THE SRIGEN PROCESS / EDITORIAL WARM PAPER SURFACE */}
      <section className="dash-process-section">
        <div className="process-header">
          <p className="process-eyebrow">THE SRIGEN PROCESS</p>
          <h2 className="process-headline">From source material to trusted intelligence.</h2>
        </div>

        <div className="process-sequence-container">
          <ol className="process-stepper">
            {PROCESS_STAGES.map((stage, i) => {
              const IconComponent = Icon[stage.icon] || Icon.Doc;
              return (
                <li
                  key={stage.id}
                  className={`process-step-item tone-${stage.tone} ${
                    hovered === stage.id ? "step-hovered" : ""
                  }`}
                  style={{ "--rd": `${i * 0.08}s` }}
                  onMouseEnter={() => setHovered(stage.id)}
                  onMouseLeave={() => setHovered(null)}
                >
                  <div className="step-top-row">
                    <div className="step-icon-badge">
                      <IconComponent />
                    </div>
                    {i < PROCESS_STAGES.length - 1 && (
                      <span className="step-flow-arrow" aria-hidden="true">
                        <Icon.ArrowRight />
                      </span>
                    )}
                  </div>
                  <div className="step-meta-row">
                    <span className="step-num">{stage.n}</span>
                    {stage.stageTag && (
                      <span className="step-tag-pill">{stage.stageTag}</span>
                    )}
                  </div>
                  <h3 className="step-title">{stage.title}</h3>
                  <p className="step-description">{stage.body}</p>
                </li>
              );
            })}
          </ol>
        </div>
      </section>

      {/* TWO WORKFLOWS / DEEP DOSSIER PANELS */}
      <section className="dash-workflows-section">
        <div className="workflows-grid">
          {/* LEFT: PRIMARY WORKFLOW - GENERATE */}
          <article className="workflow-card wf-generate reveal r1" id="generate">
            <div className="wf-card-inner">
              <div className="wf-content-side">
                <span className="wf-eyebrow">PRIMARY WORKFLOW</span>
                <h2 className="wf-title">Generate</h2>
                <p className="wf-desc">
                  Transform source material into controlled intelligence deliverables.
                </p>

                {/* Timeline progression */}
                <div className="wf-timeline">
                  <span className="wf-tl-node active">Source</span>
                  <span className="wf-tl-arrow">→</span>
                  <span className="wf-tl-node">Facts</span>
                  <span className="wf-tl-arrow">→</span>
                  <span className="wf-tl-node">Outputs</span>
                  <span className="wf-tl-arrow">→</span>
                  <span className="wf-tl-node">Review</span>
                  <span className="wf-tl-arrow">→</span>
                  <span className="wf-tl-node">Approve</span>
                </div>

                <a className="wf-cta-btn wf-cta-gen" href="#generate">
                  <span>Start Generation</span>
                  <Icon.ArrowRight />
                </a>
              </div>

              {/* RIGHT GRAPHIC: INTELLIGENCE SUMMARY & CLASSIFIED DOSSIER */}
              <div className="wf-graphic-side">
                <div className="wf-dossier-preview">
                  <div className="dossier-sheet">
                    <div className="dossier-topbar">
                      <span className="dossier-title">INTELLIGENCE SUMMARY</span>
                    </div>
                    <div className="dossier-body">
                      <span className="dossier-text-line w-90"></span>
                      <span className="dossier-text-line w-80"></span>
                      <span className="dossier-text-line w-65"></span>
                      <span className="dossier-text-line w-75"></span>
                      <span className="dossier-text-line w-50"></span>
                    </div>
                    {/* Red authentic classified agency stamp */}
                    <div className="classified-stamp">
                      <span>CLASSIFIED</span>
                    </div>
                  </div>

                  {/* Output deliverable floating chips */}
                  <div className="dossier-tags">
                    <div className="dossier-tag">
                      <Icon.Share />
                      <span>LinkedIn Post</span>
                    </div>
                    <div className="dossier-tag">
                      <Icon.Bell />
                      <span>Advisory</span>
                    </div>
                    <div className="dossier-tag">
                      <Icon.Doc />
                      <span>Executive Summary</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </article>

          {/* RIGHT: SECONDARY WORKFLOW - REFINE */}
          <article className="workflow-card wf-refine reveal r2" id="refine">
            <div className="wf-card-inner">
              <div className="wf-content-side">
                <span className="wf-eyebrow wf-eyebrow-refine">SECONDARY WORKFLOW</span>
                <h2 className="wf-title">Refine</h2>
                <p className="wf-desc">
                  Improve existing content against source evidence while preserving intent and voice.
                </p>

                {/* Timeline progression */}
                <div className="wf-timeline">
                  <span className="wf-tl-node active">Content</span>
                  <span className="wf-tl-arrow">→</span>
                  <span className="wf-tl-node">Evidence</span>
                  <span className="wf-tl-arrow">→</span>
                  <span className="wf-tl-node">Check</span>
                  <span className="wf-tl-arrow">→</span>
                  <span className="wf-tl-node">Improve</span>
                  <span className="wf-tl-arrow">→</span>
                  <span className="wf-tl-node">Adapt</span>
                </div>

                <a className="wf-cta-btn wf-cta-refine" href="#refine">
                  <span>Start Refinement</span>
                  <Icon.ArrowRight />
                </a>
              </div>

              {/* RIGHT GRAPHIC: CONTENT ANALYSIS & EVIDENCE CLAIMS */}
              <div className="wf-graphic-side">
                <div className="wf-analysis-preview">
                  <div className="analysis-sheet">
                    <div className="analysis-topbar">
                      <span className="analysis-title">CONTENT ANALYSIS</span>
                    </div>
                    <div className="analysis-body">
                      {/* Highlighted text spans representing claim checking */}
                      <div className="analysis-line">
                        <span className="claim-highlight highlight-supported"></span>
                      </div>
                      <div className="analysis-line">
                        <span className="claim-highlight highlight-contradicted"></span>
                      </div>
                      <div className="analysis-line">
                        <span className="claim-highlight highlight-unsupported"></span>
                      </div>
                      <div className="analysis-line">
                        <span className="claim-highlight highlight-neutral"></span>
                      </div>
                    </div>
                  </div>

                  {/* Status pills matching the reference image */}
                  <div className="analysis-status-pills">
                    <div className="status-pill pill-supported">
                      <span className="pill-dot"></span>
                      <div className="pill-text-group">
                        <span className="pill-title">SUPPORTED</span>
                        <span className="pill-sub">(via evidence)</span>
                      </div>
                    </div>
                    <div className="status-pill pill-contradicted">
                      <span className="pill-dot"></span>
                      <div className="pill-text-group">
                        <span className="pill-title">CONTRADICTED</span>
                        <span className="pill-sub">(needs review)</span>
                      </div>
                    </div>
                    <div className="status-pill pill-unsupported">
                      <span className="pill-dot"></span>
                      <div className="pill-text-group">
                        <span className="pill-title">UNSUPPORTED</span>
                        <span className="pill-sub">(remove / rewrite)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      {/* BUILT FOR INFORMATION THAT MATTERS / 5 EDITORIAL CAPABILITIES */}
      <section className="dash-capabilities-section">
        <div className="capabilities-header">
          <h2 className="capabilities-title">Built for information that matters.</h2>
        </div>

        <div className="capabilities-grid">
          {CAPABILITIES.map((cap, i) => {
            const IconComponent = Icon[cap.icon] || Icon.Shield;
            return (
              <div
                key={cap.title}
                className="capability-col reveal"
                style={{ "--rd": `${i * 0.07}s` }}
              >
                <div className="cap-badge">
                  <IconComponent />
                </div>
                <h3 className="cap-heading">{cap.title}</h3>
                <p className="cap-description">{cap.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* FINAL CALL TO ACTION / DARK INTELLIGENCE BANNER */}
      <section className="dash-cta-banner">
        <div className="cta-topographic-bg" aria-hidden="true">
          <svg viewBox="0 0 1400 320" preserveAspectRatio="xMidYMid slice">
            <path
              d="M-50,60 Q300,30 600,100 T1200,70 T1500,120"
              fill="none"
              stroke="rgba(208, 154, 69, 0.06)"
              strokeWidth="1.2"
            />
            <path
              d="M-50,160 Q350,220 750,140 T1350,200 T1500,180"
              fill="none"
              stroke="rgba(208, 154, 69, 0.04)"
              strokeWidth="1.2"
            />
          </svg>
        </div>

        <div className="cta-content-container reveal">
          <h2 className="cta-headline">Transform intelligence with control.</h2>
          <p className="cta-subtext">
            Start with the source. SriGEN handles the transformation, refinement, review and provenance.
          </p>
          <a className="cta-primary-action" href="#generate">
            <span>Start Generation</span>
            <Icon.ArrowRight />
          </a>
        </div>
      </section>

      {/* EDITORIAL FOOTER */}
      <footer className="dash-footer">
        <div className="footer-inner">
          <span className="footer-left">
            SriGEN &nbsp;/&nbsp; SECURE INTELLIGENCE PLATFORM
          </span>
          <span className="footer-right" id="history">
            SIH 2026 &nbsp;·&nbsp; PS 26154
          </span>
        </div>
      </footer>
    </div>
  );
}
