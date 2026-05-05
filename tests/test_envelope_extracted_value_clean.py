"""The wire envelope's `extracted_value` must show the reviewer-facing
extraction, not internal audit keys. The cloud extractor's observed_value
dict carries:

  - per-field self-reported `confidence` (used by the engine to set
    Evidence.confidence; not user-facing).
  - on `gov_warning` only: heading_bold_llm, heading_bold_measured,
    heading_bold_measured_confident, heading_bold_width_height_ratio
    — internal records of the LLM-vs-measurement comparison.

The wire `extracted_value` must omit those keys.
"""
from __future__ import annotations

from app.schemas.expected import BeverageClass, ExpectedValue
from app.schemas.extracted import (
    Evidence,
    EvidenceSource,
    FieldObservation,
    MatchKind,
)
from app.services.envelope_builder import build_field_findings


def _evidence(field_id: str) -> Evidence:
    return Evidence(
        field_id=field_id,
        source=EvidenceSource.LAYOUT,
        match_kind=MatchKind.NONE,
        confidence=0.95,
    )


def _obs(field_id: str, value: dict) -> FieldObservation:
    return FieldObservation(
        field_id=field_id,
        beverage_class=BeverageClass.SPIRITS,
        observed_value=value,
        evidence=(_evidence(field_id),),
        upstream_meta={},
    )


def test_extracted_value_strips_per_field_confidence():
    findings = build_field_findings(
        results=(),
        observations=[_obs("brand_name", {"brand_name": "ACME", "confidence": 0.95})],
        expected_values=[ExpectedValue(field_id="brand_name")],
    )
    target = next(f for f in findings if f.field_name == "brand_name")
    assert "confidence" not in target.extracted_value
    assert "ACME" in target.extracted_value


def test_extracted_value_strips_heading_audit_keys():
    findings = build_field_findings(
        results=(),
        observations=[
            _obs(
                "gov_warning",
                {
                    "text": "GOVERNMENT WARNING: …",
                    "heading_text": "GOVERNMENT WARNING",
                    "heading_all_caps": True,
                    "heading_bold": True,
                    "type_size_pt": 8.0,
                    "confidence": 0.55,
                    "heading_bold_llm": True,
                    "heading_bold_measured": True,
                    "heading_bold_measured_confident": True,
                    "heading_bold_width_height_ratio": 0.42,
                },
            )
        ],
        expected_values=[ExpectedValue(field_id="gov_warning")],
    )
    target = next(f for f in findings if f.field_name == "warning")
    leaked = (
        "confidence",
        "heading_bold_llm",
        "heading_bold_measured",
        "heading_bold_measured_confident",
        "heading_bold_width_height_ratio",
    )
    for key in leaked:
        assert key not in target.extracted_value, f"leaked audit key: {key}"
    # User-visible content survives.
    assert "GOVERNMENT WARNING" in target.extracted_value


def test_extracted_value_preserves_non_audit_keys_on_warning():
    findings = build_field_findings(
        results=(),
        observations=[
            _obs(
                "gov_warning",
                {
                    "text": "BODY",
                    "heading_text": "GOVERNMENT WARNING",
                    "heading_all_caps": True,
                    "heading_bold": True,
                    "type_size_pt": 8.0,
                    "confidence": 0.9,
                },
            )
        ],
        expected_values=[ExpectedValue(field_id="gov_warning")],
    )
    target = next(f for f in findings if f.field_name == "warning")
    # heading_text + heading_bold drive the verdict — must remain visible.
    assert "GOVERNMENT WARNING" in target.extracted_value
