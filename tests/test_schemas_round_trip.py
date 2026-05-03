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
