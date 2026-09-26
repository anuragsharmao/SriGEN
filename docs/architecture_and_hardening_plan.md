# SriGEN — Model Stack, Sensitivity Architecture & Backend Hardening Plan

> **Status: §1 (per-stage model routing), §2b (Direct/Protected mode), and
> §3 (suggested-default category tiers + sensitivity prompt rule 7) are
> implemented and tested — 140/140 tests pass (was 128 before this round).
> §2a (merging Fact Graph + Sensitivity into one call) was deliberately
> NOT implemented, per the verdict below. Finding #2 (page-level citations)
> and finding #4 (SQLite lock / /docs) remain open, as planned — not urgent.**

Three separate questions came in together — model provider stack, the
Intelligence-Extraction/Protected-Direct-mode proposal, and what to do with
the 4 backend findings from the last review. Splitting them out below, each
with a clear verdict, because they call for different amounts of risk.

---

## 1. Model stack — is Gemini primary / Groq fallback / OpenRouter optional right?

**Verdict: flip it. Groq should be primary, not fallback — Gemini's free
tier is too thin to anchor a pipeline that fires this many calls per run.**
Checked current (Sept 2026) free-tier numbers for all three, since these
change often and it's not worth guessing:

| Provider | Free tier (Sept 2026) | Notes |
|---|---|---|
| **Gemini 3.7/3.6/3.5 Flash** | **~20 requests/day**, 5 RPM | This is the real number for a full Flash model on Google AI Studio's free tier right now. A single "Generate" click that fans out to a few deliverable types, each going through fact-graph batches + sensitivity + adapter draft + disclosure scan, can burn double digits of calls by itself. 20/day means you could exhaust the whole day's quota on **one demo run**. |
| **Gemini 3.1/3.5 Flash-Lite** | 500/day, 15 RPM | Much more usable, but it's the Lite tier — weaker model, and still well under Groq. |
| **Groq — gpt-oss-120b / llama-3.3-70b-versatile** | **1,000 requests/day**, 30 RPM | What you're already using (it's in your `.env` right now). Solid reasoning-capable free tier. |
| **Groq — llama-3.1-8b-instant** | **14,400 requests/day**, 30 RPM | Same account, same key, vastly higher daily ceiling — because it's the small model. |
| **OpenRouter `:free` models** (gpt-oss-120b:free, Llama-3.3-70b:free, etc.) | 20 RPM; **50/day if you've never bought credits, 1,000/day once you've bought ≥$10** | The 50/day number is the one people miss. As a pure fallback that only fires when Groq 429s, 50/day is probably fine. As a real second primary, it isn't, unless you put $10 in once (not a subscription — a one-time top-up).|

So: **Groq stays primary** (already wired, already tested, and its free
tier is 20-700x more generous than Gemini's full Flash tier depending on
which Groq model). Use Gemini as a genuine third-option fallback if you
want model diversity for resilience, but don't lead with it — lead with
Groq's *own* two tiers instead, which is the change that actually matters:

- **gpt-oss-120b or llama-3.3-70b-versatile** for Fact Graph and Sensitivity
  Classification — the two accuracy/safety-critical stages, and (thanks to
  chunk batching already shipped) now a *low* call-volume stage, so the
  1,000/day ceiling isn't actually a binding constraint here.
- **llama-3.1-8b-instant** for the high-volume, lower-stakes calls — adapter
  drafting across many deliverable types/drafts — where the 14,400/day
  ceiling matters because call volume is naturally higher.

This is the same "don't default everything to one model" fix from finding
#1 in the last review, and the free-tier numbers are a second, independent
reason to do it: routing bulk drafting calls to the 8B tier isn't just
about quality, it's what keeps you from burning through the 70B tier's
daily cap on volume that doesn't need it.

**Fallback chain, concretely:** Groq (main) → OpenRouter `:free` (only on
a Groq 429/5xx, not load-balanced against it) → Gemini Flash-Lite as a
last-resort third leg if you want one. Don't put full Gemini Flash in the
chain at all — 20/day will trip mid-demo.

**On "deterministic verification: Python"** — worth knowing this isn't
fully true of the current Grounding Guard today; it already makes its own
LLM calls (`model=None` → default model, twice per verification pass in
`grounding_guard.py`) for semantic entailment checks on top of whatever
deterministic string/overlap checks it does first. If the intent is "make
verification cheaper and more deterministic," that's a real, separate
piece of work — worth its own look, not something to assume is already
true.

---

## 2. The Intelligence-Extraction / Protected-vs-Direct-mode proposal

Two different ideas bundled in that doc — they deserve different verdicts.

### 2a. Merge Fact Graph + Sensitivity Signal extraction into one LLM call

**Verdict: don't do this now.** It's not a bad idea in isolation, but
weighed against what it actually buys you today:

- It saves exactly one LLM call per document (`classify_with_llm`) — and
  after the batching work already shipped, Fact Graph extraction on a big
  document is now ~9 calls instead of ~70. One more call saved off of a
  pipeline that's already been cut ~8x is a small win.
- It costs real regression risk to two subsystems that are currently
  independent, well-tested (128 passing tests), and — this is the part
  that matters most — **independently wrong in different places.** Right
  now, if the Fact-Graph LLM call misreads a passage, sensitivity
  detection over that same passage still runs as its own pass and can
  still catch what the extraction missed. Merge them into one call and a
  single bad extraction now blinds *both* the facts and the sensitivity
  read for that passage at once — a correlated failure in a
  security-adjacent subsystem, in exchange for one saved call.
- It also requires the LLM to self-report `source_chunk_id` accuracy on
  sensitivity signals across a whole document in one shot, which is a
  bigger ask of a single call than what batching already does today, where
  I only asked the model to tag facts by chunk *within* a bounded batch,
  and validate every tag against ground truth rather than trust it.

If document-scale grows a lot later and this one-call-per-document
overhead genuinely starts to matter, revisit it then. Right now it's the
kind of complexity trade the plan already argued against.

### 2b. Protected mode vs Direct mode (firewall on/off, toggleable by the user)

**Verdict: yes, do this — it's small, low-risk, and solves a real
workflow gap that has nothing to do with token cost.** Detection,
Grounding Guard, Trust Score, and the Provenance Ledger all keep running
in Direct mode; only the *enforcement* gate (mandatory per-item
disclose/edit/withhold review before export) gets skipped. Concretely,
this is mostly additive, not a rearchitecture:

- `GenerationMode` enum (`PROTECTED` / `DIRECT`) on the generate request.
- In `DIRECT` mode, `DisclosureItemModel` rows still get created (so the
  Review page can still show "7 sensitivity signals detected, firewall
  off" per the original doc's point — detection ≠ enforcement is a good
  framing), but they get auto-stamped `analyst_choice = "disclose"`,
  `decision_source = "direct_mode_auto"` instead of sitting `None` and
  blocking export.
- The Provenance Ledger records that Direct mode was used for this batch —
  one field, logged same as everything else it already logs.
- UI label matters, per the original doc: call it "Direct Generation —
  Sensitivity Firewall Off" with a visible warning, not a plain toggle
  that reads like a bypass.

This is the one piece of the pasted proposal worth actually building.

---

## 3. The "220 checkboxes" complaint

Worth separating two different problems that are getting blamed on each
other:

**What's already fine:** the backend does NOT require one-by-one review
today. `routes_disclosure.py` already has a group-level batch-decide
endpoint (`/group/{group_key}/decide` — "mark every unreviewed PERSON item
as X in one call") and a whole-draft `accept-all-recommendations` endpoint
that stamps every undecided item with its own `suggested_default` in one
click. So mechanically, an analyst is never forced to click 220 individual
boxes — that's already solved on the backend. If it currently *feels*
that tedious, check whether the frontend actually surfaces the group/
bulk actions prominently, because the API for it already exists.

**What's actually the problem:** `compute_suggested_default()` in
`orchestrator.py` is deliberately conservative — for any external/public
audience, *every single detected item* defaults to `"withhold"`
regardless of confidence or how mundane it is. So bulk-accept, as it
stands, doesn't mean "let the harmless 200 through and only look at the
20 that matter" — it means "withhold all 220 unless someone individually
flips each one to disclose." That's the real source of the "bullshit"
feeling: not too many checkboxes, but too many things defaulting to the
*wrong* bucket, so the bulk action doesn't actually save the reviewer any
judgment.

**What I'd actually build**, cheaper and lower-risk than either 2a or a
UI-only fix:

1. **Direct mode (2b above)** already covers the case where the analyst
   just wants everything through and doesn't want the review gate at all.
2. **Tighten `compute_suggested_default` with a category tier, not just
   audience.** Right now every category (PERSON, LOCATION, UNIT_NAME,
   CLASSIFIED_ASSET, IP_ADDRESS...) gets the same audience-only logic. A
   bare `PERSON` name mentioned neutrally (e.g. quoted in a public
   statement) and a `CLASSIFIED_ASSET` string are not the same risk, and
   shouldn't share one default rule. Add a category-level baseline
   (e.g. PERSON/LOCATION lean toward "disclose unless high LLM
   confidence + operational category", CLASSIFIED_ASSET/IP_ADDRESS always
   lean "withhold") so bulk-accept actually does something useful instead
   of defaulting everything to the safest-possible answer. This is a
   policy-table change in one function, not a pipeline change.
3. **Tighten the sensitivity classification prompt itself** to distinguish
   "this name is operationally sensitive" from "this is just a named
   person mentioned in ordinary, already-public-appropriate context" —
   i.e. make the *detection* narrower, not just the disclosure default.
   Fewer, better-justified candidate spans is a more durable fix than
   defaulting a wide net either way. Cheap to try (prompt-only change),
   easy to evaluate against your existing 128-test suite plus a manual
   check on a real document with a lot of names.

None of this requires touching the fact-graph/sensitivity call boundary
from §2a — it's entirely inside `sensitivity_firewall.py`'s LLM prompt and
`orchestrator.py`'s default-computation function.

---

## 4. Prioritized plan for the 4 backend findings from the last review

| # | Finding | Verdict | Why |
|---|---|---|---|
| 1 | Everything runs on the 8B model by default | **Do now** | Combine with §1 above — this is now also a free-tier-capacity argument, not just a quality one. Small change: pass `model=` explicitly for fact-graph/sensitivity calls. |
| 2 | Page-level citations discarded (`page_map` always `None`) | **Do if there's time before the deadline, not urgent** | Real gap, and cheap to fix since `pages_text` already exists in the extraction loop — but nothing currently *breaks* from its absence, it just means citations are coarser than the pitch implies. Good weekend fix, not a pre-demo blocker. |
| 3 | No OCR for scanned PDFs | **Skip for the hackathon** | Real gap, but adding OCR is a genuinely new dependency and failure surface (Tesseract/cloud OCR, image preprocessing, accuracy tuning) for a class of document you may not even encounter in SIH evaluation. It already fails loud and clear rather than silently, which is the acceptable version of this gap for now. Revisit only if a real scanned-PDF need shows up. |
| 4 | SQLite global lock / `/docs` always on | **Skip for the hackathon** | Both are known, both are fine at demo scale, neither blocks anything. Worth a one-line mention in submission docs if judges ask about production-readiness, not worth engineering time now. |

**Net priority order if you want one ranked list across everything in this
message:**
1. Per-stage model routing (§1 + finding #1) — cheap, immediate, fixes both quality and free-tier capacity risk. **DONE.**
2. Direct/Protected mode (§2b) — small, addresses a real workflow gap. **DONE.**
3. `compute_suggested_default` category tiers + tighter sensitivity prompt (§3) — cheap, fixes the actual "too much gets flagged" problem. **DONE.**
4. Page-level citations (finding #2) — good if time remains. **Not started.**
5. Everything else — explicitly not now.

---

## 5. What actually shipped this round

- **`app/core/config.py`** — new `GROQ_REASONING_MODEL` setting (default
  `llama-3.3-70b-versatile`), documented as used ONLY for Fact Graph +
  Sensitivity Firewall calls. `.env` / `.env.example` updated.
- **`app/services/fact_graph.py`** — both `structured_completion` call
  sites (`_extract_single`'s single-chunk path and `_extract_batch`'s
  multi-chunk path) now pass `model=settings.GROQ_REASONING_MODEL`
  explicitly instead of falling through to the default.
- **`app/services/sensitivity_firewall.py`** — `classify_with_llm`'s one
  LLM call site does the same (covers both the source-side and
  output-side scans, since both funnel through this one method).
- **`app/db/schemas.py`** — new `GenerationMode` enum (`PROTECTED` /
  `DIRECT`), `generation_mode` field added to `GenerateRequest`,
  `DraftOutput`, `GenerateResponse`, and `DisclosureReviewResponse`.
- **`app/db/models.py`** — `generation_mode` column on
  `SourceDocumentModel` (default `"protected"`); recorded once per
  batch, deliberately NOT added to `ProvenanceLedgerModel`/the hash
  chain itself — traceable via `draft -> source_doc.generation_mode`
  instead, so `ledger.py`'s hash computation stays untouched.
- **`app/services/orchestrator.py`** — reads `request.generation_mode`
  onto `source_doc`; in the output-side `DisclosureItemModel` creation
  loop, Direct mode auto-stamps `analyst_choice="disclose"`,
  `decision_source="direct_mode_auto"`, `decided_by="system:direct_mode"`
  instead of leaving them `None` — the ONLY change, so
  `_assert_disclosure_reviewed` and `resolve_with_disclosure_decisions`
  in `routes_dashboard.py`/`sensitivity_firewall.py` needed zero changes.
- **`app/api/routes_dashboard.py`**, **`routes_disclosure.py`** —
  `generation_mode` surfaced in the draft list, draft detail, and
  disclosure-review responses, same pattern as the existing
  `llm_classification_degraded` field.
- **`compute_suggested_default` (`orchestrator.py`)** — now splits
  categories into `_ALWAYS_CONSERVATIVE_CATEGORIES` (`CLASSIFIED_ASSET`,
  `IP_ADDRESS` — always withhold for external audiences regardless of
  confidence) and `_CONTEXTUAL_SENSITIVITY_CATEGORIES` (`PERSON`,
  `LOCATION`, `UNIT_NAME`, `OTHER_SENSITIVE` — below a 0.7 confidence
  threshold, default flips to "disclose" instead of piling onto the
  withhold-everything default that made bulk-accept useless).
- **`app/prompts/sensitivity_classification_prompt.txt`** — added rule 7,
  instructing the classifier to score a routine/non-operational mention
  in the lower part of its existing 0.5–0.8 uncertain-band rather than
  0.9+, so the confidence value the new tiering reads is actually
  meaningful. (This part can't be regression-tested the way the
  deterministic tiering logic can — its real effect is only visible
  against live Groq output, not the fake LLM the test suite uses.)
- **Tests** — 12 new tests across `tests/test_backend.py` (4, exercising
  the real `/api/generate` -> `/api/dashboard/approve` flow end-to-end for
  both modes) and `tests/test_token_optimization.py` (8, covering model
  routing and the suggested-default tiering as unit tests). **140/140
  passing.**
- **Not touched, on purpose:** `app/services/aggregation_check.py` (already
  disconnected, per its own header comment), `ledger.py`'s hash-chain code,
  and the frontend (`frontend/`) — this round stayed backend/API-contract
  only; wiring the Direct-mode toggle and warning banner into the actual UI
  is a natural, separate follow-up.
