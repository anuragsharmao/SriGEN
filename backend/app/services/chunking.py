"""Deterministic document chunking: the retrieval unit for both Grounding
Guard evidence passages and Refine Mode RAG.

No LLM call — this can never itself fail on a large document. Documents
shorter than `target_chars` return a single chunk, which is the graceful-
degradation path that guarantees zero behavior change for every document
size that already works correctly today (see SriGEN Build Plan, Part A2).
"""

import re
from typing import List, Optional, Tuple, TypedDict


class Chunk(TypedDict):
    chunk_index: int
    page_start: Optional[int]
    page_end: Optional[int]
    section_hint: Optional[str]
    text: str
    char_count: int


def _split_into_paragraphs(text: str) -> List[str]:
    """Paragraph-first split (blank-line separated); falls back to line
    splitting for text with no blank-line structure at all."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if paragraphs:
        return paragraphs
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return lines if lines else ([text.strip()] if text.strip() else [])


def _split_oversized_paragraph(paragraph: str, target_chars: int) -> List[str]:
    """A single paragraph longer than target_chars is split on sentence
    boundaries (never mid-sentence if avoidable) so one giant unbroken
    paragraph can't defeat chunking entirely."""
    if len(paragraph) <= target_chars:
        return [paragraph]

    sentences = re.split(r"(?<=[.!?\u0964])\s+", paragraph)
    pieces: List[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > target_chars and current:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)

    # Fail-safe: a single sentence itself longer than target_chars (no
    # sentence-boundary punctuation at all) is hard-split on chars rather
    # than left unbounded, so no chunk can ever exceed ~2x target_chars.
    final: List[str] = []
    for piece in pieces:
        if len(piece) <= target_chars * 2:
            final.append(piece)
        else:
            for i in range(0, len(piece), target_chars):
                final.append(piece[i:i + target_chars])
    return final


def chunk_document(
    text: str,
    page_map: Optional[List[Tuple[int, int, str]]] = None,
    target_chars: int = 3500,
    overlap_chars: int = 300,
) -> List[Chunk]:
    """
    Splits `text` into ~target_chars chunks on paragraph boundaries where
    possible, with a small trailing overlap so a fact split across a chunk
    boundary is still findable in at least one chunk.

    `page_map`, if available from PDF/DOCX extraction, would be used to stamp
    page_start/page_end. This codebase's current extractors (extract_text_from_pdf,
    extract_text_from_docx) don't track per-page/per-paragraph offsets, so
    page_map is always None in practice today — chunks are persisted with
    page_start/page_end left None. This is the documented fail-safe: the rest
    of the pipeline treats None as "no page citation available", never as an
    error. Wiring a real page_map through the PDF/DOCX extractors is a
    natural follow-up, not required for this fix to be correct.
    """
    text = text or ""
    if not text.strip():
        return []

    if len(text) <= target_chars:
        return [{
            "chunk_index": 0,
            "page_start": page_map[0][0] if page_map else None,
            "page_end": page_map[-1][1] if page_map else None,
            "section_hint": None,
            "text": text.strip(),
            "char_count": len(text.strip()),
        }]

    paragraphs = _split_into_paragraphs(text)
    units: List[str] = []
    for p in paragraphs:
        units.extend(_split_oversized_paragraph(p, target_chars))

    chunks: List[Chunk] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if len(candidate) > target_chars and current:
            chunks.append(current)
            # Trailing overlap: carry the tail of the just-closed chunk
            # forward into the next one so a fact split across the boundary
            # is still findable in at least one chunk.
            overlap = current[-overlap_chars:] if overlap_chars > 0 else ""
            current = f"{overlap}\n\n{unit}".strip() if overlap else unit
        else:
            current = candidate
    if current:
        chunks.append(current)

    result: List[Chunk] = []
    for idx, chunk_text in enumerate(chunks):
        result.append({
            "chunk_index": idx,
            "page_start": None,
            "page_end": None,
            "section_hint": None,
            "text": chunk_text,
            "char_count": len(chunk_text),
        })
    return result
