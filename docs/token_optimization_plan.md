# SriGEN — LLM Token Optimization Plan

> **Status: implemented.** §2 and §3 below are done — see
> `app/services/text_cleaning.py` and the batching changes in
> `app/services/fact_graph.py`. One change from the original plan: §2's
> boilerplate stripping ended up narrower than first written (see the note
> at the end of §2) after a real test caught it deleting genuinely-repeated
> content, not just headers/footers. Verified on a synthetic 70-chunk
> document: **70 calls → 9 calls (~7.8x fewer LLM calls)**. Full test suite
> (128 tests) passes.

## 0. Verdict on the ChatGPT suggestion first

It's not wrong, but it's an 8-layer pipeline (OCR, structure detection, local NER,
indexing, hashing, sensitivity-candidate layer, etc.) when you only actually have
one problem right now: **fact graph extraction does one LLM call per chunk, and a
long document produces too many chunks.** Building the whole 8-layer thing would
add real engineering surface (new deps, new bugs, more to demo/explain in the SIH
review) for a win you can get from a much smaller change.

Worth taking from it, cheap and immediately useful:
- Strip headers/footers/page-number boilerplate before chunking (§2).
- The general principle "local code should do deterministic work, LLM should do
  judgment work" — you already follow this for merging (`_merge_partials` in
  `fact_graph.py` is pure Python, no LLM) and for regex-layer sensitivity
  detection.

Worth explicitly deferring (skip for the hackathon, revisit only if you have
spare time later):
- Full structure detection (title/section/subsection tree) — page-level
  provenance already works; you don't need an outline.
- A standalone local-NER "candidate extraction" layer — your fact graph LLM
  call already extracts entities/numbers/dates as part of the same structured
  call, so a separate NER pass doesn't save you an LLM call, it just adds a
  new pipeline stage for no token savings.
- A new local index/search layer — Grounding Guard already retrieves by
  `chunk_id`; you don't need a second retrieval system.
- Training a local sensitivity model — agree with the doc, way too early.

So: **one real change (batching), one small change (text cleaning), everything
else stays out for now.**

## 1. Where the tokens actually go today

Traced from the code (`chunking.py`, `fact_graph.py`, `sensitivity_firewall.py`,
`llm_client.py`):

- `chunk_document()` splits at `target_chars=3500` (~600-900 tokens/chunk).
- `extract_fact_graph()` fires **one LLM call per chunk** via
  `asyncio.gather` (parallel, so latency is fine — but cost isn't). A
  500-page source can produce 150-300+ chunks → 150-300+ LLM calls, and
  **each call repeats the full fact-graph system prompt** (`fact_graph_prompt.txt`),
  which is pure overhead paid every single time.
- Sensitivity classification (`classify_with_llm`) currently runs once over
  the *whole* raw text per document (not chunked) — fine for cost, but note
  `_enforce_prompt_budget` silently truncates anything over 40k chars, so a
  very large source is only partially scanned today. Flagging this as a
  correctness gap, not a token-optimization target — lower priority, see §5.

The real cost driver is **call count on the fact-graph stage**, and the
system-prompt repetition that comes with each extra call. That's the thing
to fix.

## 2. Cheap win: clean text before chunking (do this first, ~30 min)

Add one pure-Python pass before `chunk_document()` is called:
- Collapse repeated headers/footers (e.g. "CONFIDENTIAL — INTERNAL USE",
  "Page N") that appear near-identically on every page.
- Collapse excessive blank lines/whitespace.
- Rejoin hard-wrapped lines within a paragraph (line breaks that aren't real
  paragraph breaks).

This shrinks the text going into chunking, which shrinks tokens per call and
can reduce chunk count on documents with heavy boilerplate (scanned/exported
PDFs especially). No LLM involved, no new dependency — a `clean_text(text)`
function ahead of `chunk_document(text)` in the ingestion service.

**Implementation note:** the repeated-header/footer part of this ("strip a
short line that appears 3+ times") was cut during implementation. A test
using a source with a real fact repeated 5 times (`"No casualties
reported."` across several incident summaries) caught the heuristic
deleting it — it can't distinguish "CONFIDENTIAL — INTERNAL USE" stamped on
every page from a genuinely recurring fact, and SriGEN's whole premise is
that no fact gets silently dropped. `clean_text()` now only strips
unambiguous page-number lines (`"Page 17"`, `"Page 17 of 200"`, `"- 17 -"`)
plus collapsing excess blank lines — smaller token saving, but one that
can never eat real content. Only wired into the main ingestion path
(`orchestrator.py`); the ad-hoc Refine/Verify chunking paths were left
alone because they literal-substring-check passages against the uncleaned
source text, and cleaning would break that contiguity.

## 3. The main fix: batch chunks per fact-graph call

Instead of "1 chunk = 1 LLM call", group several chunks into one call up to
a character budget, and let the LLM tag each fact with which chunk it came
from *within the same call* (rather than us making a separate call per chunk
to get that tagging for free).

**Batching function** (pure Python, goes in `fact_graph.py` next to
`_normalize_chunks`):

```python
def _batch_chunks(chunks: List[_ChunkLike], max_chars: int = 28_000) -> List[List[_ChunkLike]]:
    """Group chunks into batches under a char budget, leaving headroom below
    _enforce_prompt_budget's 40k ceiling for the system prompt + output."""
    batches: List[List[_ChunkLike]] = []
    current: List[_ChunkLike] = []
    current_len = 0
    for c in chunks:
        if current and current_len + len(c.text) > max_chars:
            batches.append(current)
            current, current_len = [], 0
        current.append(c)
        current_len += len(c.text)
    if current:
        batches.append(current)
    return batches
```

**Prompt shape for a batch** — mark chunk boundaries explicitly so the model
can still attribute each fact to the right source:

```
--- CHUNK C042 (pages 17-18) ---
<chunk text>
--- END CHUNK C042 ---

--- CHUNK C043 (pages 18-19) ---
<chunk text>
--- END CHUNK C043 ---
```

Add one line to `fact_graph_prompt.txt`: *"The source is split into labeled
chunks. For every fact and entity, set its source chunk id to the CHUNK label
it came from."* (You already have `source_chunk_id` / `source_chunk_ids`
fields on `FactStatement`/`FactEntity` — this just tells the model to fill
them correctly when a call covers more than one chunk, instead of the code
stamping a single id after the fact.)

**Call-count math**: at `max_chars=28_000` and `target_chars=3500`, that's
roughly 8 chunks per call → **an ~8x reduction in fact-graph LLM calls**, and
because the system prompt is only paid once per batch instead of once per
chunk, total input tokens drop too (not just call count). A 300-chunk
document goes from ~300 calls to ~35-40.

**What doesn't change**: `_merge_partials` stays exactly as-is — you're
still merging N partial `FactGraph`s (N = number of batches, not number of
chunks), just fewer of them. `asyncio.gather` still parallelizes across
batches. The single-chunk fast path stays untouched.

**Tuning `max_chars`**: keep it well under `_enforce_prompt_budget`'s 40k so
there's headroom for the system prompt and the model's own output tokens.
28k input + ~2-3k prompt + output should sit safely under budget. You can
increase it further later if Groq's context window and your output size
comfortably allow it — but don't chase this too hard; 8x fewer calls already
solves the "100 LLM calls" problem, and going tighter on the budget risks
truncation edge cases for marginal extra savings.

## 4. Optional next step, only if the above isn't enough: caching

If you find yourself re-running fact-graph extraction on the same source
repeatedly (e.g. regenerating a deliverable during a demo, or re-ingesting
during testing), hash each chunk batch's text (SHA-256 — you already compute
hashes for the provenance ledger, so this reuses an existing pattern) and
cache the resulting partial `FactGraph` keyed on that hash. Unchanged batches
skip the LLM call entirely on a re-run. This is a nice-to-have, not required
for the hackathon deadline — only build it if batching alone doesn't get you
where you need to be.

## 5. Explicitly out of scope for now

- Local NER/candidate-extraction layer — no token savings, adds a pipeline
  stage (see §0).
- Structure/outline detection — not needed for provenance, which already
  works at page level.
- New local index/search layer — Grounding Guard already retrieves by
  `chunk_id`.
- Training a local sensitivity classifier — needs 10k-50k labeled examples
  you don't have yet; revisit only after the LLM-based pipeline has been
  running long enough to generate that labeled data (this matches what the
  ChatGPT doc itself concluded).
- Batching the sensitivity-classification call the same way — worth doing
  later if you hit the 40k-char truncation gap on very large sources, but
  it's a correctness fix more than a cost one, and it's a smaller, separate
  change from fact-graph batching. Don't bundle it into this pass.

## 6. Implementation checklist

1. Add `clean_text()` pre-pass ahead of `chunk_document()` (§2).
2. Add `_batch_chunks()` to `fact_graph.py` (§3).
3. Update `extract_fact_graph()` to batch chunks, build the labeled-chunk
   prompt, and pass batches to `_extract_single` (rename/extend it to accept
   a batch instead of one chunk).
4. Add the one-line instruction to `fact_graph_prompt.txt` about labeled
   chunks and per-fact source attribution.
5. Log call count and total prompt chars per document run (a single counter
   around the `asyncio.gather` call is enough) so you can show a concrete
   before/after number in the SIH demo — "300 calls → 38 calls on a
   500-page source" is a good line to have ready.
6. Test on your largest sample document and confirm `_merge_partials` output
   is unchanged in content (same facts/entities), just built from fewer
   partials.

That's the whole plan — one text-cleaning pass, one batching change to an
already-working service, nothing structurally new added to the pipeline.

## 7. What actually shipped (delta from the plan above)

- `app/services/text_cleaning.py` — new file, `clean_text()`. Narrower than
  originally planned; see the implementation note in §2.
- `app/services/fact_graph.py`:
  - `_batch_chunks(chunks, max_chars)` — module-level, pure Python, exactly
    as sketched in §3.
  - `FactGraphService.BATCH_MAX_CHARS = 28_000` — class attribute (not a
    hardcoded literal) so tests can force small/multi-batch scenarios.
  - `_extract_batch(batch)` — a 1-chunk batch delegates straight to the
    existing `_extract_single` (identical call shape, zero behavior change
    for small documents). A multi-chunk batch builds the `--- CHUNK id ---
    ... --- END CHUNK id ---` labeled prompt and asks the model to tag each
    fact/entity with its source chunk id.
  - **Added beyond the original plan:** the model's chunk-id tags are
    validated, not trusted — any tag that isn't a real chunk id from that
    batch falls back to "all chunk ids in this batch" (and the batch's
    overall page range) rather than shipping a wrong or empty attribution.
    Same defensive posture the Sensitivity Firewall already uses for its
    own LLM claims, so this isn't a new pattern for the codebase.
  - `extract_fact_graph()` now batches chunks before `asyncio.gather`,
    gathers over batches instead of chunks, and merges exactly as before.
    One accepted trade-off, called out in the docstring: a failed call now
    costs a whole batch's chunks instead of one chunk. No retry-with-
    smaller-batch was added for that — deliberately, to keep this change
    small.
  - `fact_graph_prompt.txt` — one line added instructing the model to tag
    `source_chunk_id`/`source_chunk_ids` from the CHUNK labels when present.
- `app/services/orchestrator.py` — one call site updated:
  `chunk_document(clean_text(doc_data["raw_text"]))`. `routes_refine.py`
  and `routes_verify.py` intentionally left unchanged (see §2 note).
- Tests: updated the two existing tests in `test_chunking_and_rag.py` that
  asserted the old "1 call per chunk" behavior, added one test asserting
  batching still adapts correctly when forced into multiple batches, and
  added `tests/test_token_optimization.py` covering `_batch_chunks`,
  `_extract_batch`'s attribution fallback, and `clean_text`. **128/128
  tests pass.**
