"""Ingestion service: normalizes text, PDF, DOCX, image, audio, and video source
material into unified SourceDocument dicts. Images/audio/video are routed
through Groq's vision/transcription models; the resulting text becomes
`raw_text` — the canonical source Grounding Guard verifies every downstream
claim against — so a `content_provenance_note` is attached whenever it is a
machine-derived transcription rather than the original primary document.
"""

import hashlib
import io
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pypdf import PdfReader

from app.core.config import settings
from app.db.schemas import LanguageType

logger = logging.getLogger("srigen.ingestion")

# Devanagari Unicode block. A deterministic, zero-LLM-cost language signal —
# reused from the same range grounding_guard.py already checks per-claim
# (`is_hindi = ... bool(re.search(r"[\u0900-\u097F]", claim))`), applied once
# here at the whole-document level instead. Threshold guards against a false
# positive from a single quoted Hindi term inside an otherwise-English document.
import re as _re
_DEVANAGARI_RE = _re.compile(r"[\u0900-\u097F]")
DEVANAGARI_DOMINANCE_THRESHOLD = 0.10  # fraction of non-whitespace chars

TEXT_EXTENSIONS = {".txt", ".md"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class UploadTooLargeError(ValueError):
    """Raised when an uploaded file exceeds MAX_UPLOAD_SIZE_MB."""


def compute_sha256(content: str) -> str:
    """Compute deterministic SHA-256 hex digest for given text content."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def detect_source_language(text: str) -> LanguageType:
    """Deterministic English-vs-Hindi detection for the ingested source, used
    to resolve a request's `language: Auto` (see app/services/resolver.py).

    Previously `language: Auto` silently always resolved to English —
    resolver.resolve_all_specs() was never passed a detected source
    language, so this document-level signal simply didn't exist yet. Fixed
    here rather than via a third LLM call: Devanagari-range character
    density is a cheap, reliable signal for English-vs-Hindi specifically
    (the only two languages this platform supports today — see LanguageType),
    and reuses the exact character range grounding_guard.py already checks
    per-claim.

    Not a general-purpose language identifier — if the platform's supported
    language set grows beyond English/Hindi, this needs to become a real
    classifier (or an LLM call) rather than a Unicode-range heuristic.
    """
    non_whitespace = [c for c in text if not c.isspace()]
    if not non_whitespace:
        return LanguageType.ENGLISH
    devanagari_count = sum(1 for c in non_whitespace if _DEVANAGARI_RE.match(c))
    if (devanagari_count / len(non_whitespace)) >= DEVANAGARI_DOMINANCE_THRESHOLD:
        return LanguageType.HINDI
    return LanguageType.ENGLISH


def _check_upload_size(file_bytes: bytes, filename: str) -> None:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise UploadTooLargeError(
            f"'{filename}' is {len(file_bytes) / (1024 * 1024):.1f} MB, which exceeds the "
            f"{settings.MAX_UPLOAD_SIZE_MB} MB upload limit."
        )


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text content from binary PDF bytes."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text.strip())
    return "\n\n".join(pages_text)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract paragraph text and table cell text from a .docx file."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    parts: List[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n\n".join(parts)


async def extract_text_from_image(file_bytes: bytes, extension: str) -> str:
    """Use Groq's vision model to produce a full factual description plus a
    verbatim transcription of any visible text in the image."""
    from app.core.llm_client import llm_client

    mime_type = IMAGE_MIME_TYPES.get(extension, "image/png")
    prompt = (
        "Describe this image factually and completely. Then, separately, provide "
        "a verbatim transcription of every piece of text visible in the image "
        "(signage, labels, documents, captions, etc.), preserving exact wording. "
        "If no text is visible, state that explicitly. Do not speculate beyond "
        "what is visibly present in the image."
    )
    return await llm_client.describe_image(file_bytes, mime_type=mime_type, prompt=prompt)


def _extract_audio_track_via_ffmpeg(video_bytes: bytes, suffix: str) -> bytes:
    """Extract the audio track from a video file using ffmpeg (must be installed
    and on PATH; see README prerequisites)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / f"input{suffix}"
        audio_path = Path(tmpdir) / "audio.mp3"
        video_path.write_bytes(video_bytes)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "mp3", str(audio_path)],
                check=True,
                capture_output=True,
                timeout=300,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "ffmpeg is not installed or not on PATH. Video ingestion requires ffmpeg "
                "to extract the audio track before transcription — see README prerequisites."
            ) from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed to extract audio track: {e.stderr.decode(errors='replace')}") from e
        return audio_path.read_bytes()


async def extract_text_from_audio_or_video(file_bytes: bytes, filename: str, extension: str) -> str:
    """Transcribe audio directly, or extract the audio track from a video via
    ffmpeg first, then transcribe via Groq Whisper."""
    from app.core.llm_client import llm_client

    if extension in VIDEO_EXTENSIONS:
        audio_bytes = _extract_audio_track_via_ffmpeg(file_bytes, extension)
        transcribe_filename = "extracted_audio.mp3"
    else:
        audio_bytes = file_bytes
        transcribe_filename = filename

    return await llm_client.transcribe_audio(audio_bytes, filename=transcribe_filename)


def segment_passages(text: str) -> List[Dict[str, str]]:
    """Segment document text into indexed paragraphs/passages for explainable grounding evidence."""
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [line.strip() for line in text.split("\n") if line.strip()]

    passages = []
    for idx, para in enumerate(raw_paragraphs):
        passages.append({
            "passage_id": f"P-{idx + 1:03d}",
            "text": para
        })
    return passages


async def _extract_single_file(file_bytes: bytes, filename: str) -> Tuple[str, str, Optional[str]]:
    """Returns (extracted_text, file_type, content_provenance_note)."""
    _check_upload_size(file_bytes, filename)
    ext = Path(filename).suffix.lower()

    if ext in PDF_EXTENSIONS:
        return extract_text_from_pdf(file_bytes), "pdf", None
    if ext in DOCX_EXTENSIONS:
        return extract_text_from_docx(file_bytes), "docx", None
    if ext in IMAGE_EXTENSIONS:
        text = await extract_text_from_image(file_bytes, ext)
        note = (
            f"Source '{filename}' is an image. The text above is a machine-generated "
            f"description/transcription produced by a vision model, not the original "
            f"primary document — treat it as a derived artifact when reviewing grounding evidence."
        )
        return text, "image", note
    if ext in AUDIO_EXTENSIONS or ext in VIDEO_EXTENSIONS:
        text = await extract_text_from_audio_or_video(file_bytes, filename, ext)
        kind = "video" if ext in VIDEO_EXTENSIONS else "audio"
        note = (
            f"Source '{filename}' is {kind}. The text above is a machine transcription "
            f"produced by a speech-to-text model, not the original primary document — "
            f"treat it as a derived artifact when reviewing grounding evidence."
        )
        return text, kind, note
    # Default: treat as plain text (.txt, .md, or unrecognized extension)
    return file_bytes.decode("utf-8", errors="replace"), "text", None


async def ingest_document(
    text: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    filename: str = "source_document.txt",
    additional_files: Optional[List[Tuple[bytes, str]]] = None,
) -> Dict[str, Optional[str]]:
    """Ingest, normalize, and hash source material. Supports a single primary
    file/text plus optional additional files (multi-file upload), which are
    concatenated into one coherent source document with clear separators so a
    single Fact Graph is built across all of them."""
    parts: List[str] = []
    file_types: List[str] = []
    provenance_notes: List[str] = []
    combined_filename = filename

    if file_bytes:
        extracted, file_type, note = await _extract_single_file(file_bytes, filename)
        if extracted.strip():
            parts.append(f"--- SOURCE: {filename} ---\n{extracted.strip()}")
        file_types.append(file_type)
        if note:
            provenance_notes.append(note)
    elif text:
        parts.append(text.strip())
        file_types.append("text")

    if additional_files:
        for extra_bytes, extra_filename in additional_files:
            extracted, file_type, note = await _extract_single_file(extra_bytes, extra_filename)
            if extracted.strip():
                parts.append(f"--- SOURCE: {extra_filename} ---\n{extracted.strip()}")
            file_types.append(file_type)
            if note:
                provenance_notes.append(note)

    if not parts:
        if not file_bytes and not text and not additional_files:
            raise ValueError("Either text or file_bytes must be provided for ingestion.")
        raise ValueError("Document content is empty after extraction.")

    raw_content = "\n\n".join(parts)
    if not raw_content.strip():
        raise ValueError("Document content is empty after extraction.")

    source_hash = compute_sha256(raw_content)
    # If every ingested part was plain text, keep file_type "text"/"pdf" as before
    # for single-file uploads; for genuinely multi-file batches, report "multi".
    file_type = file_types[0] if len(file_types) == 1 else "multi"
    detected_language = detect_source_language(raw_content)

    return {
        "filename": combined_filename,
        "file_type": file_type,
        "raw_text": raw_content,
        "source_hash": source_hash,
        "content_provenance_note": " | ".join(provenance_notes) if provenance_notes else None,
        "detected_language": detected_language.value,
    }
