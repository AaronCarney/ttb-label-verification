"""Internal & wire schemas round-trip a representative payload byte-identically."""
from __future__ import annotations

import json

import pytest


def test_extracted_field_observation_round_trip() -> None:
    from app.schemas.expected import BeverageClass
    from app.schemas.extracted import (
        BBox,
        Evidence,
        EvidenceSource,
        FieldObservation,
        MatchKind,
    )

    obs = FieldObservation(
        field_id="brand",
        beverage_class=BeverageClass.SPIRITS,
        observed_value="Stone's Throw",
        evidence=(
            Evidence(
                field_id="brand",
                source=EvidenceSource.OCR,
                page_id=None,
                panel="front",
                image_uri=None,
                bbox=(120, 240, 800, 120),
                extracted_text="Stone's Throw",
                normalized_text="stones throw",
                matched_against_value="Stone's Throw",
                match_kind=MatchKind.NORMALIZED,
                match_score=None,
                confidence=0.96,
                notes=None,
            ),
        ),
        timestamp_ms=1714579200000,
        upstream_meta={"engine": "paddleocr-3.0", "snapshot": "v1"},
    )
    obs2 = FieldObservation.model_validate_json(obs.model_dump_json())
    assert obs2 == obs


def test_extracted_models_are_frozen() -> None:
    from app.schemas.extracted import BBox, Evidence, EvidenceSource, MatchKind

    ev = Evidence(
        field_id="brand",
        source=EvidenceSource.OCR,
        page_id=None,
        panel=None,
        image_uri=None,
        bbox=(0, 0, 1, 1),
        extracted_text=None,
        normalized_text=None,
        matched_against_value=None,
        match_kind=MatchKind.NONE,
        match_score=None,
        confidence=0.5,
        notes=None,
    )
    with pytest.raises(Exception):  # ValidationError or FrozenInstanceError-like
        ev.confidence = 0.9  # type: ignore[misc]


def test_extracted_models_forbid_extra_fields() -> None:
    from pydantic import ValidationError

    from app.schemas.extracted import Evidence, EvidenceSource, MatchKind

    with pytest.raises(ValidationError):
        Evidence(
            field_id="brand",
            source=EvidenceSource.OCR,
            page_id=None,
            panel=None,
            image_uri=None,
            bbox=None,
            extracted_text=None,
            normalized_text=None,
            matched_against_value=None,
            match_kind=MatchKind.NONE,
            match_score=None,
            confidence=0.5,
            notes=None,
            unexpected_extra="bad",  # type: ignore[call-arg]
        )


def test_reason_code_grammar() -> None:
    from app.schemas.rejection import ReasonCode

    assert ReasonCode.validate_grammar("BRAND.NAME.MATCH") == "BRAND.NAME.MATCH"
    assert (
        ReasonCode.validate_grammar("ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND")
        == "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND"
    )
    assert (
        ReasonCode.validate_grammar("ENGINE.MODEL.UNAVAILABLE.LLM_OUTPUT_INVALID")
        == "ENGINE.MODEL.UNAVAILABLE.LLM_OUTPUT_INVALID"
    )
    import pytest

    for bad in ["lower.case.code", "TOO.SHORT", "FIVE.PARTS.IS.TOO.MANY.NOPE", ""]:
        with pytest.raises(ValueError):
            ReasonCode.validate_grammar(bad)


def test_validation_result_round_trip() -> None:
    from app.schemas.expected import BeverageClass
    from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult

    vr = ValidationResult(
        rule_id="common.brand.exact_or_normalized",
        cfr_citation="27 CFR §4.33(a)",
        beverage_class=BeverageClass.SPIRITS,
        outcome=Outcome.PASS,
        severity=Severity.INFO,
        reason_code="BRAND.NAME.MATCH",
        aggregated_confidence=0.94,
        evidence=(),
        expected=None,
        observed=None,
        message="Brand name matches.",
        engine_meta=EngineMeta(
            engine_version="0.1.0",
            rule_pack_version="0.1.0",
            rule_pack="common",
            started_at_ms=1714579200000,
            elapsed_ms=8,
        ),
    )
    vr2 = ValidationResult.model_validate_json(vr.model_dump_json())
    assert vr2 == vr


def test_refined_round_trip() -> None:
    from app.schemas.refined import Refined

    r = Refined(
        evaluation_id="00000000-0000-4000-8000-000000000001",
        task="brand_borderline",
        text="Stone's Throw vs Stones Throw — punctuation only.",
        model_disposition="pass",
    )
    r2 = Refined.model_validate_json(r.model_dump_json())
    assert r2 == r


def test_refined_has_no_disposition_field_fr303() -> None:
    """FR-303 invariant: the orchestrator output schema must NOT carry a top-level
    ``disposition`` field — AI never decides pass/fail.
    ``model_disposition`` is permitted (it is the model's *suggestion*, not the
    deterministic verdict). The forbidden field is the bare ``disposition``.
    """
    from app.schemas.refined import Refined

    fields = Refined.model_fields
    assert "disposition" not in fields, (
        "FR-303 violation: Refined.disposition would let the AI decide pass/fail."
    )


def test_audit_record_round_trip() -> None:
    from datetime import datetime, timezone

    from app.schemas.audit import AuditRecord, OverrideEntry, PerRuleTraceEntry

    rec = AuditRecord(
        evaluation_id="00000000-0000-4000-8000-000000000001",
        rule_set_version="0.1.0",
        model_version="gpt-4o-2024-08-06",
        prompt_version="v1",
        input_hash="0" * 64,
        output_hash="1" * 64,
        started_at=datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 4, 1, 12, 0, 1, 230000, tzinfo=timezone.utc),
        per_rule_trace=(
            PerRuleTraceEntry(
                rule_id="common.brand.exact_or_normalized",
                disposition="pass",
                evidence_ref="crop-001",
            ),
        ),
        overrides=(),
    )
    rec2 = AuditRecord.model_validate_json(rec.model_dump_json())
    assert rec2 == rec


def test_per_rule_trace_entry_has_no_duration_ms_d018() -> None:
    """ADR D-018: per-rule durations live in metrics, not in audit."""
    from app.schemas.audit import PerRuleTraceEntry

    fields = PerRuleTraceEntry.model_fields
    assert "duration_ms" not in fields, (
        "D-018 violation: per-rule duration belongs in app.schemas.metrics, "
        "not in audit_trail.per_rule_trace[]."
    )
    assert set(fields.keys()) == {"rule_id", "disposition", "evidence_ref"}


def test_metrics_round_trip() -> None:
    from app.schemas.metrics import Metrics, PerRuleDurationEntry

    m = Metrics(
        total_duration_ms=1230,
        per_rule_durations_ms=(
            PerRuleDurationEntry(rule_id="common.brand.exact_or_normalized", duration_ms=8),
        ),
        vision_duration_ms=720,
        orchestrator_duration_ms=480,
    )
    m2 = Metrics.model_validate_json(m.model_dump_json())
    assert m2 == m


def test_rule_set_round_trip() -> None:
    from app.schemas.expected import BeverageClass
    from app.schemas.rejection import Severity
    from app.schemas.rules import (
        AssetRef,
        DecisionTable,
        MatchPolicy,
        ReasonCodeEntry,
        RuleDefinition,
        RuleSet,
    )

    rule = RuleDefinition(
        rule_id="spirits.alcohol.tolerance_band",
        cfr_citation="27 CFR §5.65(c)",
        applies_to_classes=(BeverageClass.SPIRITS,),
        reason_code="ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND",
        severity=Severity.REJECT,
        match_policy=MatchPolicy.TOLERANCE,
        validator="abv_band",
        evidence_required=("abv",),
        confidence_floor=0.5,
        parameters={"tolerance_pp": 0.3, "arithmetic": "decimal"},
        tolerance=None,
        decision_table=None,
        decision_table_ref=None,
        asset=None,
        effective_date="2022-02-09",
        supersedes=(),
        rule_pack_version="0.1.0",
        rule_pack="spirits",
        test_fixtures=("F-SPIRITS-ALC-36-PASS-01",),
        disabled=False,
        notes=None,
    )

    rs = RuleSet(
        version="0.1.0",
        effective_date="2026-04-01",
        rules=(rule,),
        reason_codes={
            "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND": ReasonCodeEntry(
                description="ABV outside the regulatory tolerance band.",
                cfr_anchors=("27 CFR §5.65(c)",),
                severity=Severity.REJECT,
            ),
        },
        assets={
            "warning_16_21": AssetRef(
                path="assets/warnings/govt_warning_16_21.txt",
                sha256="0" * 64,
            ),
        },
        decision_tables={
            "cpi_16_22_a_4": DecisionTable(
                interpolation="none",
                entries=({"min_ml": 50, "max_ml": 100, "cpi": 0.4},),
            ),
        },
    )
    rs2 = RuleSet.model_validate_json(rs.model_dump_json())
    assert rs2 == rs


def test_match_policy_enum_values() -> None:
    from app.schemas.rules import MatchPolicy

    assert MatchPolicy("tolerance") is MatchPolicy.TOLERANCE
    assert MatchPolicy("verbatim_hash") is MatchPolicy.VERBATIM_HASH
    assert MatchPolicy("fuzzy") is MatchPolicy.FUZZY
