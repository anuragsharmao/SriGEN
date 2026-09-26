"""Conservative pre-chunking text cleanup.

Strips boilerplate that inflates token counts without carrying any content:
page-number-only lines (e.g. "Page 17", "Page 17 of 200", "- 17 -"), plus
collapsing runs of 3+ blank lines. This runs once, locally, before
chunk_document() — no LLM call — and it never touches the stored raw_text
used for redaction/citation/generation elsewhere in the pipeline; only the
copy that feeds chunking (and therefore Fact Graph / Grounding Guard token
counts) is cleaned.

Deliberately narrow: only a line that is UNAMBIGUOUSLY a page number is
dropped. An earlier version of this also stripped short lines that repeated
3+ times, on the theory that a running header/footer repeats every page —
but that heuristic can't tell "CONFIDENTIAL — INTERNAL USE" on every page
apart from a real short fact ("No casualties reported.") that happens to
recur across multiple incidents in the same source, and SriGEN's whole
premise is that no fact gets silently dropped. So repetition-based
stripping was deliberately left out: a smaller, guaranteed-safe token
saving beats a bigger one that can eat real content.
"""

import re

# Matches a line that is ONLY a page number in a few common shapes:
# "Page 17", "Page 17 of 200", "- 17 -", or a bare number on its own line.
_PAGE_NUMBER_RE = re.compile(
    r"^\s*(page\s+\d+(\s+of\s+\d+)?|-\s*\d+\s*-|\d+)\s*$",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Strip page-number-only lines, then collapse runs of 3+ blank lines
    down to one. A no-op on text with no page-number lines, which is most
    of it — this can never remove real sentence content."""
    if not text or not text.strip():
        return ""

    cleaned_lines = [
        line for line in text.split("\n")
        if not _PAGE_NUMBER_RE.match(line.strip())
    ]

    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()
