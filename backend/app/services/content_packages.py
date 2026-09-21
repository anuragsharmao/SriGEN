"""Flattens structured content packages (Presentation / Infographic / Video Package)
into plain text.

These three deliverables are content-only: the adapters return structured
Pydantic objects (slides, infographic sections, video scenes/subtitles), not a
text blob. Grounding Guard, Trust Score, the Provenance Ledger's hashing/diffing,
and the disclosure dual-scan all consume `draft_content` as plain text — rather
than teach each of those systems about three new structured shapes, we flatten
once here and let all of that machinery work unchanged.
"""
from pydantic import BaseModel

from app.db.schemas import InfographicPackage, PresentationPackage, VideoPackage


def flatten_package(package: BaseModel) -> str:
    """Produce a flattened text rendering of a structured content package."""
    if isinstance(package, PresentationPackage):
        return _flatten_presentation(package)
    if isinstance(package, InfographicPackage):
        return _flatten_infographic(package)
    if isinstance(package, VideoPackage):
        return _flatten_video_package(package)
    raise TypeError(f"flatten_package: unsupported package type {type(package)!r}")


def _flatten_presentation(package: PresentationPackage) -> str:
    parts = [package.title]
    if package.subtitle:
        parts.append(package.subtitle)
    for slide in package.slides:
        parts.append(f"\nSlide {slide.slide_number}: {slide.title}")
        for bullet in slide.bullets:
            parts.append(f"- {bullet}")
        if slide.speaker_notes:
            parts.append(f"Speaker notes: {slide.speaker_notes}")
    return "\n".join(parts)


def _flatten_infographic(package: InfographicPackage) -> str:
    parts = [package.title, package.key_message]
    for section in package.sections:
        header = section.heading
        if section.stat_value:
            header += f" ({section.stat_value}{' ' + section.stat_label if section.stat_label else ''})"
        parts.append(f"\n{header}")
        parts.append(section.body)
    if package.footer:
        parts.append(f"\n{package.footer}")
    return "\n".join(parts)


def _flatten_video_package(package: VideoPackage) -> str:
    parts = [package.title, package.narration_script]
    for scene in package.scenes:
        parts.append(f"\nScene {scene.scene_number} ({scene.start_seconds}s-{scene.end_seconds}s): {scene.visual_description}")
        if scene.on_screen_text:
            parts.append(f"On-screen text: {scene.on_screen_text}")
        parts.append(f"Narration: {scene.narration}")
    if package.visual_recommendations:
        parts.append("\nVisual recommendations: " + "; ".join(package.visual_recommendations))
    return "\n".join(parts)
