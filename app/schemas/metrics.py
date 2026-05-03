"""Per-evaluation telemetry. Sibling of audit_trail per ADR D-018.

Source: ARCH §6.8 note + §13.5 audit/telemetry split; PRD §6.2 ``metrics`` block.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PerRuleDurationEntry(BaseModel):
    """One per-rule wall-clock duration entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    duration_ms: int


class Metrics(BaseModel):
    """Telemetry block on the disposition envelope (PRD §6.2)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_duration_ms: int
    per_rule_durations_ms: tuple[PerRuleDurationEntry, ...]
    vision_duration_ms: int
    orchestrator_duration_ms: int
