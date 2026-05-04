"""Replay-mode vision adapter — synthesizes a `FieldObservation` list from a
fixture's `ExpectedValue` tuple so the rules engine + disposition logic can be
measured in isolation from live OCR.

Used only by `eval.harness --mode replay`. Documented as a *diagnostic
isolation* tool, not a substitute for the §4 end-to-end macro-F1 gate; see
`docs/plans/ttb-label-verification-epoch-8-demo-eval-deploy.md` §10.1.

Trade-offs explicitly accepted (see ``REPLAY_DISABLED_RULES`` below):
  * Validators that need rich layout/contrast/CPI metadata are disabled in
    replay because synthesizing pixel-derived numbers without a real OCR
    extractor would just be making up data.
  * `spirits.class_type.present` is disabled because the on-disk fixtures
    spell `"BOURBON WHISKEY"` while the rule's allowed_values use British
    `"Whisky"` — a fixture-authorship gap that affects live OCR too.
"""
from __future__ import annotations

from typing import Sequence

from app.schemas.expected import BeverageClass, ExpectedValue
from app.schemas.extracted import (
    Evidence, EvidenceSource, FieldObservation, MatchKind,
)
from app.schemas.label import Label


# Rules disabled in replay mode. Each entry is paired with the reason so the
# disabled set stays auditable from the README/runbook.
REPLAY_DISABLED_RULES: dict[str, str] = {
    "common.warning.verbatim":         "verbatim_hash needs the exact asset string; dict payload won't hash-match.",
    "common.warning.contrasting_bg":   "contrast_ratio_check needs WCAG calc from image pixels.",
    "common.warning.cpi_max":          "cpi_lookup needs precise type metrics from layout extraction.",
    "common.warning.separate_apart":   "layout_isolation_check needs neighbor-distance from layout extraction.",
    "common.warning.type_size_min":    "type_size_check needs point-size measurement from layout extraction.",
    "spirits.same_field_of_vision":    "same_field_of_vision_check needs per-panel field maps from layout.",
    "spirits.class_type.present":      "fixture-authorship gap: fixtures spell 'WHISKEY' but rule allow-list uses 'Whisky'.",
    "spirits.class_type.matches_soi":  "same fixture-authorship gap as spirits.class_type.present.",
}


# Default warning_block payload — passes heading-caps-bold for clean fixtures.
# Override `heading_styles.case` to "title" to encode the FIX-03 violation.
_DEFAULT_WARNING_BLOCK_PAYLOAD: dict[str, object] = {
    "heading_text": "GOVERNMENT WARNING",
    "heading_styles": {"case": "upper", "weight": "bold"},
}


def _make_evidence(field_id: str, text: str, confidence: float) -> Evidence:
    return Evidence(
        field_id=field_id,
        source=EvidenceSource.OCR,
        extracted_text=text or None,
        normalized_text=text or None,
        match_kind=MatchKind.NORMALIZED,
        confidence=confidence,
    )


def _make_obs(
    *,
    field_id: str,
    value: object,
    beverage_class: BeverageClass,
    confidence: float = 0.95,
) -> FieldObservation:
    text = "" if value is None or isinstance(value, dict) else str(value)
    return FieldObservation(
        field_id=field_id,
        beverage_class=beverage_class,
        observed_value=value,
        evidence=(_make_evidence(field_id, text, confidence),),
    )


def _value_for_field(ev: ExpectedValue, overrides: dict[str, object]) -> object:
    """Map a rule-side ExpectedValue to the `observed_value` validators expect."""
    if ev.field_id in overrides:
        ov = overrides[ev.field_id]
        if ev.field_id == "warning_block" and isinstance(ov, dict):
            merged = {**_DEFAULT_WARNING_BLOCK_PAYLOAD, **ov}
            merged["heading_styles"] = {
                **_DEFAULT_WARNING_BLOCK_PAYLOAD["heading_styles"],
                **ov.get("heading_styles", {}),
            }
            return merged
        return ov
    if ev.field_id == "alc_text":
        return ev.value  # already populated as "Alcohol X% by volume"
    if ev.field_id == "abv":
        return ev.abv_labeled_pct  # presence trigger; tolerance reads ExpectedValue
    if ev.field_id == "net_contents":
        vol = ev.container_volume_ml
        return f"{vol} ml" if vol is not None else ev.value
    if ev.field_id == "warning_block":
        return dict(_DEFAULT_WARNING_BLOCK_PAYLOAD)
    if ev.field_id == "warning_heading":
        return "GOVERNMENT WARNING"
    return ev.value


def build_replay_observations(
    expected_values: Sequence[ExpectedValue],
    *,
    beverage_class: BeverageClass = BeverageClass.SPIRITS,
    overrides: dict[str, object] | None = None,
) -> list[FieldObservation]:
    """Synthesize a FieldObservation list from a fixture's RULE-SIDE
    `expected_values` (already remapped from application field_ids).

    `overrides` keys are rule-side field_ids (e.g. "warning_block"); values
    replace the default synthesized payload for that field. Used to encode
    deliberate rule violations (e.g. FIX-03 title-case heading)."""
    overrides = overrides or {}
    obs: list[FieldObservation] = []
    for ev in expected_values:
        value = _value_for_field(ev, overrides)
        obs.append(_make_obs(field_id=ev.field_id, value=value,
                             beverage_class=beverage_class))
    return obs


class ReplayVisionExtractor:
    """`VisionExtractor` Protocol-compatible static-list returner."""

    def __init__(self, observations: Sequence[FieldObservation]) -> None:
        self._obs = list(observations)

    async def extract(self, label: Label) -> list[FieldObservation]:
        return list(self._obs)

    async def ensure_loaded(self) -> None:
        return None
