"""Item 7 — adversarial sensitivity-detection test set.

The regex layer in app/core/config.py::SENSITIVE_PATTERNS is a narrow,
enumerable pre-filter — trivially bypassed by rephrasing. The LLM
classification layer (app/prompts/sensitivity_classification_prompt.txt) is
the real catch-all, and was hardened with obfuscated/rephrased examples as
part of this remediation (see that file).

IMPORTANT CAVEAT: these tests run against the FakeLLMClient, not a live
model, so they verify two things only:
  1. Obfuscated phrasing genuinely does NOT match the regex layer alone
     (proving the regex-only gap is real and this isn't a redundant test).
  2. The merge/dedup pipeline correctly surfaces whatever the classification
     layer returns, so a real LLM's catches aren't silently dropped downstream.
They do NOT prove the live Groq model actually catches every obfuscation
style in the hardened prompt — that requires periodic validation against a
real model call in a separate, live-API integration suite, which is outside
what an offline unit-test suite can check. Treat this file as a regression
guard on the pipeline wiring, not a substitute for that live validation.
"""

import asyncio

from app.db.schemas import SensitiveSpanCandidate
from app.services.sensitivity_firewall import firewall

OBFUSCATED_LOCATION = "the base near the northern ridge, call sign Falcon"
OBFUSCATED_UNIT = "the unit informally known as 'the Wolves', operating out of the eastern command"


def test_obfuscated_phrasing_is_not_caught_by_regex_alone():
    """Proves the gap is real: these phrasings must NOT match any regex pattern."""
    text = f"Response was coordinated from {OBFUSCATED_LOCATION}. {OBFUSCATED_UNIT} led the effort."
    spans, degraded = asyncio.run(firewall._collect_candidate_spans(text))
    regex_only_matches = [s for s in spans if s["source"] == "regex"]
    assert regex_only_matches == [], (
        "Expected zero regex matches for obfuscated phrasing — if this fails, either the "
        "regex patterns were broadened (fine) or the test fixture text accidentally matches "
        "a structural pattern (fix the fixture)."
    )
    assert degraded is False


def test_llm_layer_catches_what_regex_misses(monkeypatch):
    """Simulates a correctly-functioning classification layer catching the
    obfuscated phrasing regex missed, and confirms it flows through to the
    output-side disclosure scan."""
    import app.services.sensitivity_firewall as firewall_module

    async def _simulate_llm_catch(self, text):
        candidates = []
        if OBFUSCATED_LOCATION in text:
            candidates.append(SensitiveSpanCandidate(
                exact_text=OBFUSCATED_LOCATION, category="LOCATION", detection_confidence=0.75,
                sensitivity_tier="sensitive",
                reasoning="Indirect site reference via call sign + geographic description.",
            ))
        if OBFUSCATED_UNIT in text:
            candidates.append(SensitiveSpanCandidate(
                exact_text=OBFUSCATED_UNIT, category="UNIT_NAME", detection_confidence=0.7,
                sensitivity_tier="contextual",
                reasoning="Nickname-based unit reference.",
            ))
        return candidates, False

    monkeypatch.setattr(firewall_module.SensitivityFirewall, "classify_with_llm", _simulate_llm_catch)

    text = f"Response was coordinated from {OBFUSCATED_LOCATION}. {OBFUSCATED_UNIT} led the effort."
    items, degraded = asyncio.run(firewall.scan_for_disclosure_items(text))

    categories_found = {item["category"] for item in items}
    assert "LOCATION" in categories_found
    assert "UNIT_NAME" in categories_found
    assert degraded is False


def test_degraded_flag_set_true_when_classification_call_fails(monkeypatch):
    import app.services.sensitivity_firewall as firewall_module

    async def _fail(self, text):
        return [], True

    monkeypatch.setattr(firewall_module.SensitivityFirewall, "classify_with_llm", _fail)

    text = f"Response was coordinated from {OBFUSCATED_LOCATION}."
    items, degraded = asyncio.run(firewall.scan_for_disclosure_items(text))
    assert degraded is True
    # Regex-only fallback still runs — just misses the obfuscated phrasing.
    assert not any(item["value"] == OBFUSCATED_LOCATION for item in items)
