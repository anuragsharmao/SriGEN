"""Shared Deliverable Specification formatting.

Both the generation pipeline (app/adapters/base.py) and the Refine pipeline
(app/services/content_refiner.py) describe the same seven dimensions —
Audience, Tone, Language, Length, Content Style, Communication Objective,
Detail Focus — to the LLM. This module is the single place that formats them,
so the two systems can never drift into describing the same enum differently.

Generation always has a fully-resolved spec (Auto has already been resolved by
app/services/resolver.py), so every field is a concrete value there. Refine
allows any subset of fields to be None, meaning "keep this dimension as it
currently is in the content" — never "the model can decide" and never "Auto".
`format_deliverable_spec_block` renders a None field as the literal
"KEEP AS IS" so that intent is explicit in the prompt rather than ambiguous
through omission.
"""

from typing import Any, List, Optional


DIMENSION_ORDER = [
    "audience",
    "tone",
    "language",
    "length",
    "content_style",
    "communication_objective",
    "detail_focus",
]

DIMENSION_LABELS = {
    "audience": "Audience",
    "tone": "Tone",
    "language": "Language",
    "length": "Length",
    "content_style": "Content Style",
    "communication_objective": "Communication Objective",
    "detail_focus": "Detail Focus",
}

KEEP_AS_IS = "KEEP AS IS"

# Establishes, in the prompt itself, that all seven dimensions are peers — no
# dimension (tone included) is the "main" objective. Shared verbatim by both
# generation and refinement prompts.
EQUAL_WEIGHT_NOTICE = (
    "The following are independent deliverable/refinement dimensions. Every dimension that is "
    "explicitly specified is equally important — there is no primary dimension. In particular, "
    "Tone is only one dimension among seven; do not treat it as the main objective or let it "
    "override the others. Apply every explicitly specified dimension together, as one coherent "
    "transformation, not as a priority-ordered sequence (tone first, everything else second). "
    "Any dimension marked '" + KEEP_AS_IS + "' must be left consistent with its current state in "
    "the content — that is not the same as unconstrained or open to change; do not make "
    "unnecessary changes to a dimension that was not explicitly requested."
)


def _fmt_value(value: Any) -> str:
    if value is None:
        return KEEP_AS_IS
    if isinstance(value, (list, tuple)):
        if not value:
            return KEEP_AS_IS
        return ", ".join(_fmt_scalar(v) for v in value)
    return _fmt_scalar(value)


def _fmt_scalar(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def format_deliverable_spec_block(
    audience: Any = None,
    tone: Any = None,
    language: Any = None,
    length: Any = None,
    content_style: Any = None,
    communication_objective: Any = None,
    detail_focus: Optional[List[Any]] = None,
) -> str:
    """Renders the seven-dimension Deliverable Specification as a labeled text
    block. A field left as None renders as KEEP AS IS; this is the ONLY place
    that decides how "keep as is" is spelled out, so generation and refinement
    can never phrase it differently."""
    fields = {
        "audience": audience,
        "tone": tone,
        "language": language,
        "length": length,
        "content_style": content_style,
        "communication_objective": communication_objective,
        "detail_focus": detail_focus,
    }
    lines = [f"{DIMENSION_LABELS[key]}: {_fmt_value(fields[key])}" for key in DIMENSION_ORDER]
    return "\n".join(lines)


def keep_as_is_fields(**fields: Any) -> List[str]:
    """Returns the labels of every dimension whose value is None — useful for
    logging/response metadata about what was left untouched."""
    return [DIMENSION_LABELS[key] for key in DIMENSION_ORDER if fields.get(key) is None]
