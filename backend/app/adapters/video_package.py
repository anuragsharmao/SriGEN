"""Video Package deliverable adapter — content-only (script, storyboard, scene
descriptions, narration, subtitles, visual recommendations), no .mp4 file rendered.

Covers all six PS-listed video artefacts (script, storyboard, scene
descriptions, narration text, subtitles, visual recommendations) in one
structured VideoPackage object.
"""
from typing import List

from app.adapters.base import BaseDeliverableAdapter
from app.db.schemas import DeliverableSpec, FactGraph, LengthType, SubtitleCue, VideoPackage, VideoScene

TARGET_DURATION_SECONDS = {
    LengthType.BRIEF: 30.0,
    LengthType.STANDARD: 60.0,
    LengthType.DETAILED: 120.0,
}

SUBTITLE_MAX_CHARS_PER_LINE = 42
SUBTITLE_MAX_LINES = 2
SUBTITLE_MIN_DURATION = 1.2
SUBTITLE_MAX_DURATION = 6.0


def _wrap_subtitle_text(text: str) -> str:
    """Deterministically wrap subtitle text to the max chars/line and max line
    count constraints. Long overflow is truncated with an ellipsis rather than
    silently dropped, so the constraint is never violated."""
    text = " ".join(text.split())
    if len(text) <= SUBTITLE_MAX_CHARS_PER_LINE:
        return text

    words = text.split(" ")
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= SUBTITLE_MAX_CHARS_PER_LINE:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) == SUBTITLE_MAX_LINES:
            break
    if current and len(lines) < SUBTITLE_MAX_LINES:
        lines.append(current)

    result = "\n".join(lines[:SUBTITLE_MAX_LINES])
    if len(result) < len(text) and not result.endswith("..."):
        # Content was truncated to satisfy the line/char cap.
        last_line = lines[-1] if lines else ""
        if len(last_line) > SUBTITLE_MAX_CHARS_PER_LINE - 3:
            last_line = last_line[: SUBTITLE_MAX_CHARS_PER_LINE - 3]
        lines[-1] = last_line + "..."
        result = "\n".join(lines[:SUBTITLE_MAX_LINES])
    return result


class VideoPackageAdapter(BaseDeliverableAdapter):
    output_model = VideoPackage

    def __init__(self):
        super().__init__(template_filename="video_package.txt")

    async def generate_structured(
        self,
        fact_graph: FactGraph,
        spec: DeliverableSpec,
        source_context: str,
    ) -> VideoPackage:
        package: VideoPackage = await super().generate_structured(fact_graph, spec, source_context)
        return self._normalize(package, spec)

    def _normalize(self, package: VideoPackage, spec: DeliverableSpec) -> VideoPackage:
        """Deterministically enforce the timing invariants the LLM's raw output
        might not satisfy exactly: scenes contiguous with no gaps summing exactly
        to total_duration_seconds, and subtitle cues respecting char/line/duration
        bounds with no overlaps."""
        target_duration = TARGET_DURATION_SECONDS.get(spec.length, 60.0)

        # --- Normalize scenes: proportionally rescale to fill [0, target_duration]
        # contiguously, preserving relative pacing from the model's own estimate. ---
        scenes = sorted(package.scenes, key=lambda s: s.scene_number) if package.scenes else []
        if scenes:
            raw_lengths = [max(0.5, s.end_seconds - s.start_seconds) for s in scenes]
            raw_total = sum(raw_lengths) or 1.0
            cursor = 0.0
            normalized_scenes: List[VideoScene] = []
            for idx, (scene, raw_len) in enumerate(zip(scenes, raw_lengths)):
                scaled_len = (raw_len / raw_total) * target_duration
                start = round(cursor, 2)
                end = round(cursor + scaled_len, 2) if idx < len(scenes) - 1 else round(target_duration, 2)
                normalized_scenes.append(scene.model_copy(update={
                    "scene_number": idx + 1,
                    "start_seconds": start,
                    "end_seconds": end,
                }))
                cursor = end
            package.scenes = normalized_scenes
        package.total_duration_seconds = round(target_duration, 2)

        # --- Normalize subtitle cues: wrap text, clamp per-cue duration, and lay
        # them out back-to-back with no overlaps, capped at total_duration_seconds. ---
        cues = sorted(package.subtitles, key=lambda c: c.index) if package.subtitles else []
        normalized_cues: List[SubtitleCue] = []
        cursor = 0.0
        for i, cue in enumerate(cues, start=1):
            wrapped_text = _wrap_subtitle_text(cue.text)
            raw_duration = max(SUBTITLE_MIN_DURATION, cue.end_seconds - cue.start_seconds)
            duration = min(SUBTITLE_MAX_DURATION, max(SUBTITLE_MIN_DURATION, raw_duration))
            start = round(cursor, 2)
            end = round(min(target_duration, start + duration), 2)
            if end <= start:
                break
            normalized_cues.append(SubtitleCue(index=i, start_seconds=start, end_seconds=end, text=wrapped_text))
            cursor = end
            if cursor >= target_duration:
                break
        package.subtitles = normalized_cues

        return package
