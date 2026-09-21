"""Generation Orchestrator: parallel adapter fan-out and end-to-end transformation pipeline."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.adapters import ADAPTER_REGISTRY
from app.db.models import (
    DeliverableDraftModel,
    DisclosureItemModel,
    FactGraphModel,
    GroundingReportModel,
    SecurityActionModel,
    SourceDocumentModel,
)
from app.db.schemas import (
    AudienceType,
    DeliverableSpec,
    DeliverableType,
    DraftOutput,
    GenerateRequest,
    GenerateResponse,
    LanguageType,
    SecurityActionItem,
)
from app.services.content_packages import flatten_package
from app.services.fact_graph import fact_graph_service
from app.services.grounding_guard import grounding_guard
from app.services.ingestion import ingest_document
from app.services.resolver import resolver
from app.services.sensitivity_firewall import firewall
from app.services.trust_score import trust_score_calculator
from app.core.config import settings

logger = logging.getLogger("srigen.orchestrator")


def compute_suggested_default(
    category: str,
    confidence: float,
    audience: AudienceType,
    deliverable_type: DeliverableType,
    publication_status: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Compute contextual suggested disclosure recommendation for analyst review.

    CRITICAL ARCHITECTURAL PRINCIPLE:
    The Sensitivity Firewall's confidence means 'How confident are we that this item is sensitive?'
    It does NOT mean 'How confident are we that this item is safe to disclose?'.
    Therefore, high sensitivity confidence does NOT mean 'Disclose'.

    Contextual recommendation logic:
    - If the source material is officially marked as already published/released -> suggest "disclose".
    - If the intended audience is authorized internal leadership (Internal/Restricted or Senior Leadership)
      for an internal deliverable -> suggest "disclose" with clear audit notation.
    - Otherwise (external / public audiences or unverified release status) -> suggest "withhold"
      as the safest conservative recommendation pending explicit analyst action.
    """
    if publication_status and publication_status.lower() in ["public", "released", "approved"]:
        return "disclose", "Source material is marked as already officially released."

    if audience in [AudienceType.INTERNAL_RESTRICTED, AudienceType.SENIOR_LEADERSHIP]:
        return "disclose", f"Target audience '{audience.value}' is authorized for internal operational context."

    return "withhold", f"Sensitive {category} identified for public/external distribution. Recommended to withhold pending analyst confirmation."


class GenerationOrchestrator:
    """Orchestrates ingestion -> firewall (source-side scan) -> fact graph ->
    parallel adapter fan-out (reading raw source directly) -> output-side
    disclosure scan -> grounding guard -> trust score."""

    async def execute_transformation(
        self,
        db: Session,
        request: GenerateRequest,
        file_bytes: Optional[bytes] = None,
        filename: str = "source_document.txt",
        additional_files: Optional[List[Tuple[bytes, str]]] = None,
    ) -> GenerateResponse:
        batch_id = str(uuid.uuid4())
        logger.info(f"Initiating SriGEN transformation batch {batch_id} for types: {request.deliverable_types}")

        # 1. UNDERSTAND: Ingestion (text, PDF, DOCX, image, audio, video, multi-file)
        doc_data = await ingest_document(
            text=request.source_text,
            file_bytes=file_bytes,
            filename=filename,
            additional_files=additional_files,
        )

        # 2. CONTROL: Sensitivity Firewall — SOURCE-SIDE scan. This produces the
        # source document's transparency log (Security Actions Log) only.
        # Generation below reads the RAW source text directly, never this
        # redacted/placeholder text (see app/adapters/base.py).
        redacted_text, security_actions_items, placeholder_map, source_degraded = await firewall.apply_redaction(
            text=doc_data["raw_text"],
            audience=request.audience,
        )
        source_value_index = {
            (act.category, act.original_value.strip().lower()) for act in security_actions_items
        }

        # Persist Source Document
        source_doc = SourceDocumentModel(
            filename=doc_data["filename"],
            file_type=doc_data["file_type"],
            detected_language=doc_data["detected_language"],
            raw_text=doc_data["raw_text"],
            redacted_text=redacted_text,
            placeholder_map_json=json.dumps(placeholder_map),
            placeholder_native_map_json="{}",
            source_hash=doc_data["source_hash"],
            content_provenance_note=doc_data.get("content_provenance_note"),
            llm_classification_degraded=source_degraded,
        )
        db.add(source_doc)
        db.flush()

        # Persist Security Action transparency logs (source-side findings)
        for act in security_actions_items:
            db_act = SecurityActionModel(
                id=act.id,
                source_id=source_doc.id,
                category=act.category,
                placeholder=act.placeholder,
                original_value=act.original_value,
                confidence=act.confidence,
                reasoning=act.reasoning,
                audience_level=act.audience_level,
                is_overridden=False,
            )
            db.add(db_act)
        db.flush()

        # 3. UNDERSTAND: Canonical Fact Graph (Single Source of Truth)
        fact_graph = await fact_graph_service.extract_fact_graph(doc_data["raw_text"])

        fact_graph_record = FactGraphModel(
            source_id=source_doc.id,
            graph_json=json.dumps(fact_graph.model_dump()),
        )
        db.add(fact_graph_record)
        db.flush()

        # Build placeholder native map cross-referencing fact_graph entities
        # (transparency/audit record only — not used to resolve generation output,
        # since generation reads the raw source directly).
        placeholder_native_map: Dict[str, Dict[str, str]] = {}
        for placeholder, original_value in placeholder_map.items():
            entry = {"en": original_value}
            for entity in fact_graph.entities:
                if entity.name.strip().lower() == original_value.strip().lower():
                    entry.update(entity.native_forms)
                    break
            placeholder_native_map[placeholder] = entry

        source_doc.placeholder_native_map_json = json.dumps(placeholder_native_map)
        db.add(source_doc)
        db.flush()

        # 4. CONTROL: Content Intelligence Resolver. `language: Auto` on the
        # request resolves against the ACTUAL detected source language, not
        # an unconditional English default (see SourceDocumentModel.detected_language
        # / app/services/ingestion.py::detect_source_language).
        detected_language = LanguageType(doc_data["detected_language"])
        deliverable_specs: List[DeliverableSpec] = resolver.resolve_all_specs(
            request, source_language=detected_language
        )

        # 5. GENERATE: Parallel Adapter Fan-out using asyncio.gather.
        # Structured (content-only) deliverables — Presentation, Infographic,
        # Video Package — use generate_structured() and are flattened to text
        # for the shared verification/scoring/ledger machinery; every other
        # adapter uses the original plain-text generate() path, unchanged.
        async def run_adapter(spec: DeliverableSpec) -> Dict[str, Any]:
            adapter = ADAPTER_REGISTRY.get(spec.deliverable_type.value)
            if not adapter:
                logger.warning(f"No custom adapter for {spec.deliverable_type.value}, using fallback.")
                adapter = ADAPTER_REGISTRY["advisory"]

            if getattr(adapter, "output_model", None) is not None:
                structured_package = await adapter.generate_structured(
                    fact_graph=fact_graph,
                    spec=spec,
                    source_context=doc_data["raw_text"],
                )
                flat_text = flatten_package(structured_package)
                return {"spec": spec, "content": flat_text, "structured": structured_package}

            generated_content = await adapter.generate(
                fact_graph=fact_graph,
                spec=spec,
                source_context=doc_data["raw_text"],
            )
            return {"spec": spec, "content": generated_content, "structured": None}

        adapter_tasks = [run_adapter(spec) for spec in deliverable_specs]
        generated_results = await asyncio.gather(*adapter_tasks)

        # 6. VERIFY: Cross-Output Consistency (content already carries real values —
        # generation read the raw source directly, so no placeholder resolution needed)
        resolved_deliverable_texts = [
            {
                "type": res["spec"].deliverable_type.value,
                "language": res["spec"].language.value if hasattr(res["spec"].language, "value") else str(res["spec"].language),
                "content": res["content"],
            }
            for res in generated_results
        ]
        consistency_score, consistency_findings = await grounding_guard.check_cross_output_consistency(
            drafts=resolved_deliverable_texts,
            fact_graph=fact_graph,
        )

        # 7. VERIFY: Claim-level Grounding Guard, Trust Scoring, and Phase 2
        # OUTPUT-SIDE disclosure scan per deliverable.
        draft_outputs: List[DraftOutput] = []

        for item in generated_results:
            spec: DeliverableSpec = item["spec"]
            draft_text: str = item["content"]
            structured_package = item["structured"]

            grounding_score, claim_results = await grounding_guard.verify_content(
                content=draft_text,
                source_text=doc_data["raw_text"],
                fact_graph=fact_graph,
                language=spec.language,
            )

            # Policy Dimension: checks draft_text against
            # fact_graph.policy_constraints (extracted from the source, not
            # invented per-draft, so every sibling deliverable is judged
            # against the same constraint list). Empty constraints -> (0, 0,
            # []) without an LLM call -> policy_score of 100, same as before
            # for the common case where the source states no explicit
            # constraint; a non-empty list now actually gets checked instead
            # of being silently ignored.
            policy_flagged, policy_unresolved, policy_violations = await grounding_guard.evaluate_policy_compliance(
                content=draft_text,
                policy_constraints=fact_graph.policy_constraints,
            )
            trust_breakdown = trust_score_calculator.calculate_score(
                claim_results=claim_results,
                consistency_score_override=consistency_score,
                total_flagged=policy_flagged,
                unresolved_violations=policy_unresolved,
            )

            draft_model = DeliverableDraftModel(
                source_id=source_doc.id,
                batch_id=batch_id,
                deliverable_type=spec.deliverable_type.value,
                spec_json=json.dumps(spec.model_dump()),
                draft_content=draft_text,
                structured_json=json.dumps(structured_package.model_dump()) if structured_package else None,
                approved_content=None,
                status="draft",
                grounding_score=trust_breakdown.grounding_score,
                consistency_score=trust_breakdown.consistency_score,
                policy_score=trust_breakdown.policy_score,
                composite_trust_score=trust_breakdown.composite_trust_score,
            )
            db.add(draft_model)
            db.flush()

            # --- Phase 2.4: OUTPUT-SIDE disclosure scan ---
            # Detection runs on the generated draft text itself (generation can
            # introduce, rephrase, or recombine sensitive info the source-side
            # scan alone can't anticipate). Merge with the source-side findings:
            # detected_at = "both" if the same (category, value) was also found
            # in the source-side scan, else "output". A source-side finding that
            # never made it into this draft produces no item here at all.
            output_spans, output_degraded = await firewall.scan_for_disclosure_items(draft_text)
            if output_degraded and not source_doc.llm_classification_degraded:
                # Surface degradation from EITHER scan point on the source
                # document record — an operator reviewing this source should
                # see "sensitivity detection ran in degraded mode" regardless
                # of whether it degraded on the source-side or output-side pass.
                source_doc.llm_classification_degraded = True
                db.add(source_doc)
            for span_entry in output_spans:
                norm_key = (span_entry["category"], span_entry["value"].strip().lower())
                detected_at = "both" if norm_key in source_value_index else "output"
                conf = span_entry.get("confidence", 1.0)
                sugg_default, sugg_reason = compute_suggested_default(
                    category=span_entry["category"],
                    confidence=conf,
                    audience=spec.audience,
                    deliverable_type=spec.deliverable_type,
                )

                disc_item = DisclosureItemModel(
                    id=str(uuid.uuid4()),
                    draft_id=draft_model.id,
                    placeholder=span_entry["display_placeholder"],
                    category=span_entry["category"],
                    detected_value_preview=span_entry["value"],
                    confidence=conf,
                    reasoning=f"{span_entry.get('reasoning', 'Matched sensitive criteria')}. Recommendation: {sugg_reason}",
                    suggested_default=sugg_default,
                    analyst_choice=None,
                    manual_edit_text=None,
                    decision_source=None,
                    group_key=span_entry["category"],
                    detected_at=detected_at,
                    decided_by=None,
                    decided_at=None,
                )
                db.add(disc_item)

            grounding_report = GroundingReportModel(
                draft_id=draft_model.id,
                source_id=source_doc.id,
                is_verification_mode=False,
                target_content=draft_text,
                claims_json=json.dumps([c.model_dump() for c in claim_results]),
                entity_mismatches_json=json.dumps([]),
                policy_violations_json=json.dumps(policy_violations),
                grounding_score=trust_breakdown.grounding_score,
                consistency_score=trust_breakdown.consistency_score,
                policy_score=trust_breakdown.policy_score,
                composite_trust_score=trust_breakdown.composite_trust_score,
            )
            db.add(grounding_report)

            draft_outputs.append(DraftOutput(
                id=draft_model.id,
                deliverable_type=spec.deliverable_type,
                status="draft",
                draft_content=draft_text,
                structured_content=structured_package.model_dump() if structured_package else None,
                approved_content=None,
                trust_score=trust_breakdown,
                claims=claim_results,
                security_actions=security_actions_items,
                policy_violations=policy_violations,
                llm_classification_degraded=source_doc.llm_classification_degraded,
                created_at=draft_model.created_at,
            ))

        db.commit()

        return GenerateResponse(
            source_id=source_doc.id,
            source_hash=source_doc.source_hash,
            batch_id=batch_id,
            fact_graph=fact_graph,
            drafts=draft_outputs,
            security_actions=security_actions_items,
            content_provenance_note=doc_data.get("content_provenance_note"),
            llm_classification_degraded=source_doc.llm_classification_degraded,
            detected_source_language=doc_data["detected_language"],
            source_context_truncated=len(doc_data["raw_text"]) > settings.MAX_GENERATION_CONTEXT_CHARS,
        )


orchestrator = GenerationOrchestrator()
