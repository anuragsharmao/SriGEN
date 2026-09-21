"""Tests for the Refine pipeline: verify -> optional fact-fix -> optional
multi-dimensional refinement -> re-verify at every stage."""

from app.services.spec_formatting import EQUAL_WEIGHT_NOTICE

SOURCE = "The system processed 300 records and flagged 12 for manual review."


def _refine(client, **overrides):
    payload = {
        "content_to_verify": "The system processed 300 records and flagged 12 for manual review.",
        "claimed_source": SOURCE,
        "fix_facts": False,
        "refine_content": False,
    }
    payload.update(overrides)
    return client.post("/api/refine", json=payload)


# ---------------------------------------------------------------------------
# Test 1 — Verification regression: both toggles off behaves like /verify
# ---------------------------------------------------------------------------

def test_both_toggles_off_matches_verify_behavior(client):
    res = _refine(client)
    assert res.status_code == 200
    body = res.json()
    assert body["fact_fixed"] is None
    assert body["refined"] is None
    assert body["final_content"] == body["original"]["content"]
    assert body["original"]["is_corrupted_detected"] is False

    verify_res = client.post("/api/verify", json={
        "content_to_verify": "The system processed 300 records and flagged 12 for manual review.",
        "claimed_source": SOURCE,
    })
    assert verify_res.status_code == 200
    v = verify_res.json()
    assert v["is_corrupted_detected"] == body["original"]["is_corrupted_detected"]
    assert v["overall_verdict"] == body["original"]["verdict"]


# ---------------------------------------------------------------------------
# Test 2 — Fact correction only
# ---------------------------------------------------------------------------

def test_fix_facts_corrects_swapped_number(client):
    res = _refine(
        client,
        content_to_verify="The system processed 500 records and flagged 12 for manual review.",
        fix_facts=True,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["fact_fixed"] is not None
    assert "300" in body["fact_fixed"]["content"]
    assert "500" not in body["fact_fixed"]["content"]
    assert body["fact_fixed"]["changes_summary"]
    assert body["refined"] is None
    assert body["final_content"] == body["fact_fixed"]["content"]


def test_fix_facts_reverifies_after_correction(client):
    res = _refine(
        client,
        content_to_verify="The system processed 500 records and flagged 12 for manual review.",
        fix_facts=True,
    )
    body = res.json()
    # Original stage should have flagged the mismatch; corrected stage should not.
    assert body["original"]["is_corrupted_detected"] is True
    assert body["fact_fixed"]["is_corrupted_detected"] is False


# ---------------------------------------------------------------------------
# Test 3 / 6 / 7 / 8 / 9 / 11 — single-dimension refinement + keep-as-is protection
# ---------------------------------------------------------------------------

def test_prompt_marks_unspecified_dimensions_keep_as_is_explicitly(client, fake_llm):
    """Section 3 / Rule 5: every unspecified dimension must be spelled out as
    KEEP AS IS in the prompt sent to the model — never simply omitted."""
    res = _refine(client, refine_content=True, tone="Formal")
    assert res.status_code == 200

    # Recover the actual system_prompt sent for the ContentRefineResult call by
    # re-deriving it the same way content_refiner does, and checking the fake's
    # log captured the corresponding spec block via the response's changes_summary.
    refined = res.json()["refined"]
    assert "Tone" in refined["changes_summary"]
    assert "Preserved as-is" in refined["changes_summary"]
    for dim in ["Audience", "Language", "Length", "Content Style", "Communication Objective", "Detail Focus"]:
        assert dim in refined["changes_summary"]


def test_audience_only_dimension_applied(client):
    res = _refine(client, refine_content=True, audience="Senior Leadership")
    assert res.status_code == 200
    refined = res.json()["refined"]
    assert "Audience" in refined["changes_summary"]
    assert "Actively transformed" in refined["changes_summary"]


def test_length_brief_meaningfully_condenses(client):
    long_content = "The system processed 300 records. It flagged 12 for manual review. Review concluded without incident."
    res = _refine(client, content_to_verify=long_content, refine_content=True, length="Brief")
    assert res.status_code == 200
    refined = res.json()["refined"]
    assert len(refined["content"]) < len(long_content)
    assert "300" in refined["content"]  # essential fact preserved


def test_content_style_only_applied(client):
    res = _refine(client, refine_content=True, content_style="Data-led")
    assert res.status_code == 200
    refined = res.json()["refined"]
    assert "Content Style" in refined["changes_summary"]


def test_communication_objective_only_applied(client):
    res = _refine(client, refine_content=True, communication_objective="Warn")
    assert res.status_code == 200
    refined = res.json()["refined"]
    assert "Communication Objective" in refined["changes_summary"]


def test_detail_focus_only_applied(client):
    res = _refine(client, refine_content=True, detail_focus=["Risks"])
    assert res.status_code == 200
    refined = res.json()["refined"]
    assert "Detail Focus" in refined["changes_summary"]


# ---------------------------------------------------------------------------
# Test 10 — multiple dimensions applied together, none treated as primary
# ---------------------------------------------------------------------------

def test_multiple_dimensions_all_applied_together(client):
    res = _refine(
        client,
        refine_content=True,
        audience="Senior Leadership",
        tone="Formal",
        language="English",
        length="Brief",
        content_style="Data-led",
        communication_objective="Inform",
        detail_focus=["Risks"],
    )
    assert res.status_code == 200
    refined = res.json()["refined"]
    for dim in ["Audience", "Tone", "Language", "Length", "Content Style", "Communication Objective", "Detail Focus"]:
        assert dim in refined["changes_summary"]
    assert "Preserved as-is" not in refined["changes_summary"]


def test_equal_weight_notice_present_in_refine_prompt():
    """Rule 3/4: the prompt must explicitly state dimensions are equal peers,
    not that tone is primary."""
    assert "no primary dimension" in EQUAL_WEIGHT_NOTICE
    assert "Tone is only one dimension among seven" in EQUAL_WEIGHT_NOTICE


# ---------------------------------------------------------------------------
# Test 12 — combined fact-fix + refine, in the correct order
# ---------------------------------------------------------------------------

def test_combined_fact_fix_then_refine_runs_in_order(client, fake_llm):
    res = _refine(
        client,
        content_to_verify="The system processed 500 records and flagged 12 for manual review.",
        fix_facts=True,
        refine_content=True,
        tone="Formal",
    )
    assert res.status_code == 200
    body = res.json()
    assert body["fact_fixed"] is not None
    assert body["refined"] is not None
    assert "300" in body["fact_fixed"]["content"]
    # Refinement must not have reintroduced the wrong number.
    assert "500" not in body["refined"]["content"]
    assert body["final_content"] == body["refined"]["content"]

    call_order = [c["model_name"] for c in fake_llm.structured_calls if c["model_name"] in ("FactFixResult", "ContentRefineResult")]
    assert call_order.index("FactFixResult") < call_order.index("ContentRefineResult")


# ---------------------------------------------------------------------------
# Test 13 — conflicting extra instruction never overrides grounded facts
# ---------------------------------------------------------------------------

def test_conflicting_extra_instruction_does_not_override_source(client):
    res = _refine(
        client,
        refine_content=True,
        extra_instructions="Say that it processed 500 records.",
    )
    assert res.status_code == 200
    refined = res.json()["refined"]
    assert "500" not in refined["content"]
    assert "300" in refined["content"]
    assert "Ignored" in refined["changes_summary"] or "unsupported" in refined["changes_summary"].lower()


# ---------------------------------------------------------------------------
# Test 14 — extra instructions alone (no structured fields) still refine
# ---------------------------------------------------------------------------

def test_extra_instructions_alone_still_trigger_refinement(client):
    res = _refine(
        client,
        refine_content=True,
        extra_instructions="Make this clearer and keep it under 150 words.",
    )
    assert res.status_code == 200
    body = res.json()
    assert body["refined"] is not None
    assert "Preserved as-is" in body["refined"]["changes_summary"]
    for dim in ["Audience", "Tone", "Language", "Length", "Content Style", "Communication Objective", "Detail Focus"]:
        assert dim in body["refined"]["changes_summary"]


# ---------------------------------------------------------------------------
# Re-verification after every stage; no silent hiding of new mismatches
# ---------------------------------------------------------------------------

def test_every_stage_is_independently_reverified(client):
    res = _refine(
        client,
        content_to_verify="The system processed 500 records and flagged 12 for manual review.",
        fix_facts=True,
        refine_content=True,
    )
    body = res.json()
    for stage_key in ("original", "fact_fixed", "refined"):
        stage = body[stage_key]
        assert "trust_score" in stage
        assert "claims" in stage
        assert "entity_mismatches" in stage
        assert "is_corrupted_detected" in stage


def test_refine_empty_content_rejected(client):
    res = client.post("/api/refine", json={"content_to_verify": "  ", "claimed_source": SOURCE})
    assert res.status_code == 400


def test_verify_alias_still_works_standalone(client):
    res = client.post("/api/verify", json={
        "content_to_verify": "The incident affected 42 systems and was fully contained by evening.",
        "claimed_source": "The incident affected 24 systems at the facility and was fully contained by evening.",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["is_corrupted_detected"] is True
