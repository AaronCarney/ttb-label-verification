"""Pure envelope assembly — success path + short-circuit path + per-field
FieldFindingWire projection (v0.5 Critical-#1).

No I/O, no clock; takes a pre-built AuditRecord + Metrics so audit/metrics
ownership stays clean.
"""
from __future__ import annotations

from typing import Iterable

from app.schemas.application import Application
from app.schemas.audit import AuditRecord, PerRuleTraceEntry
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.label import Label
from app.schemas.metrics import Metrics
from app.schemas.rejection import ValidationResult
from app.schemas.wire.disposition import (
    AISuggestionWire,
    ConfidenceBand,
    DispositionEnvelope,
    FieldEvidenceWire,
    FieldFindingWire,
    RuleFindingWire,
)
from app.services.aggregation import min_aggregate_confidence
from app.services.confidence import to_band
from app.services.engine_meta import EvaluationTimeline


# Wire-shape vestige (PRD §6.2): orchestrator task names → wire enum.
_TASK_WIRE_NAME = {
    "brand_disambig": "brand_borderline",
    "reasoning_enrich": "reasoning_enrichment",
    "ocr_reconcile": "ocr_reconciliation",
}


# v0.5 Critical-#1 / v0.6 Warning-6: canonical PRD §5.1 field id → wire
# field_name enum. Each canonical id maps to a distinct wire slot — no
# duplicates. PRD §5.1 (FR-001 through FR-008) names exactly seven
# user-visible fields; the wire enum (`FieldFindingWire.field_name`) carries
# exactly seven slots; the mapping is one-to-one.
_FIELD_CANONICAL_TO_WIRE = {
    "brand_name": "brand_name",
    "class_type": "class_type",
    "alcohol_content": "alcohol_content",
    "net_contents": "net_contents",
    "government_warning": "warning",
    "name_and_address": "name_address",
    "country_of_origin": "country_of_origin",
}


def _coerce_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def build_field_findings(
    *,
    results: Iterable[ValidationResult],
    observations: Iterable[FieldObservation],
    expected_values: Iterable[ExpectedValue],
) -> tuple[FieldFindingWire, ...]:
    """Project (ValidationResult, FieldObservation, ExpectedValue) tuples
    into the wire-side `FieldFindingWire` list.

    One entry per canonical PRD §5.1 field for which there is either an
    observation OR an expected value. Canonical fields with no observation
    AND no expected value are omitted (they remain visible to the reviewer
    via the audit `per_rule_trace` synthetic entries that T13 Cycle C builds
    for engine_failure rows). The seven canonical ids are listed in
    `_FIELD_CANONICAL_TO_WIRE`; `country_of_origin` (FR-008) is included
    only when an observation surfaces it.
    """
    obs_by_field: dict[str, FieldObservation] = {o.field_id: o for o in observations}
    exp_by_field: dict[str, ExpectedValue] = {e.field_id: e for e in expected_values}
    # Group ValidationResults by the canonical field they touch (sourced from
    # the first evidence's `field_id`). Validators that emit no evidence
    # cannot be associated with a field — they surface in audit only.
    results_by_field: dict[str, list[ValidationResult]] = {}
    for vr in results:
        if not vr.evidence:
            continue
        fid = vr.evidence[0].field_id
        results_by_field.setdefault(fid, []).append(vr)

    candidate_fields = list(_FIELD_CANONICAL_TO_WIRE.keys())
    out: list[FieldFindingWire] = []
    for fid in candidate_fields:
        obs = obs_by_field.get(fid)
        exp = exp_by_field.get(fid)
        if obs is None and exp is None:
            continue
        if obs is None or not obs.evidence:
            # Per the contract: needs_review trace entry handled in audit;
            # skip the wire entry to keep the wire surface tight.
            continue
        ev = obs.evidence[0]
        evidence_wire = FieldEvidenceWire(
            bbox=ev.bbox if ev.bbox is not None else (0, 0, 0, 0),
            crop_ref=ev.image_uri or "",
            extraction_confidence=ev.confidence,
        )
        rule_findings_for_field = tuple(
            RuleFindingWire(
                rule_id=vr.rule_id,
                cfr_citation=vr.cfr_citation,
                disposition=(
                    "pass" if vr.outcome.value == "pass" else
                    "fail" if vr.outcome.value == "fail" else
                    "needs_review"
                ),
                reason_code=vr.reason_code or "",
                plain_language_explanation=vr.message or "",
            ) for vr in results_by_field.get(fid, [])
        )
        # Min confidence over this field's validators; fall back to
        # the observation's evidence confidence when no rule fired.
        confidences = [vr.aggregated_confidence for vr in results_by_field.get(fid, [])]
        numeric = min(confidences) if confidences else ev.confidence
        out.append(FieldFindingWire(
            field_name=_FIELD_CANONICAL_TO_WIRE[fid],  # type: ignore[arg-type]
            extracted_value=_coerce_str(obs.observed_value),
            expected_value=_coerce_str(exp.value if exp else None),
            evidence=evidence_wire,
            rule_findings=rule_findings_for_field,
            ai_suggestion=AISuggestionWire(present=False),
            field_confidence=ConfidenceBand(band=to_band(numeric), numeric=numeric),
        ))
    return tuple(out)


def build_success_envelope(
    *,
    application: Application,
    label: Label,
    timeline: EvaluationTimeline,
    disposition: str,
    fields: Iterable[FieldFindingWire],
    audit: AuditRecord,
    metrics: Metrics,
) -> DispositionEnvelope:
    fields_t = tuple(fields)
    band, numeric = min_aggregate_confidence(fields_t)
    return DispositionEnvelope(
        evaluation_id=application.evaluation_id,
        label_ref=label.label_id,  # wire-side name <- internal name (Conventions §)
        disposition=disposition,  # type: ignore[arg-type]
        disposition_confidence=ConfidenceBand(band=band, numeric=numeric),
        fields=fields_t,
        audit_trail=audit,
        metrics=metrics,
    )


def build_short_circuit_envelope(
    *,
    application: Application,
    label: Label,
    timeline: EvaluationTimeline,
    reason_code: str,
    audit: AuditRecord,
    metrics: Metrics,
) -> DispositionEnvelope:
    """Assemble a needs_review envelope when an upstream short-circuit fired
    (legibility, whole-eval timeout, total engine failure). Surfaces the
    reason code as a synthetic per_rule_trace entry so reviewers see why."""
    # Augment audit trail with the short-circuit reason if not already present.
    existing_ids = {e.rule_id for e in audit.per_rule_trace}
    if reason_code not in existing_ids:
        synthetic = PerRuleTraceEntry(
            rule_id=reason_code, disposition="needs_review",
            evidence_ref=f"engine_failure/{reason_code}",
        )
        augmented = audit.model_copy(update={"per_rule_trace": audit.per_rule_trace + (synthetic,)})
    else:
        augmented = audit
    return DispositionEnvelope(
        evaluation_id=application.evaluation_id,
        label_ref=label.label_id,  # wire-side name <- internal name (Conventions §)
        disposition="needs_review",
        disposition_confidence=ConfidenceBand(band="low", numeric=0.0),
        fields=(),
        audit_trail=augmented,
        metrics=metrics,
    )
