"""AI orchestrator output. Source: ARCH §6.6, PRD FR-303.

FR-303 invariant: this model declares **no top-level disposition field**.
The deterministic Rule Engine produces dispositions; the orchestrator only
enriches reasoning, disambiguates borderline brand matches, or reconciles OCR.
A misbehaving orchestrator literally cannot return a disposition because no
such field exists on the schema.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class TaskSlice(BaseModel):
    """One per-task contribution to a Refined output. Source: ARCH §6.6."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task: Literal[
        "brand_disambig",
        "reasoning_enrich",
        "ocr_reconcile",
    ]
    rule_id: str | None = None
    payload: dict | None = None
    qualifier: Literal[
        "ENGINE.MODEL.UNAVAILABLE",
        "LLM_OUTPUT_INVALID",
    ] | None = None


class Refined(BaseModel):
    """Orchestrator output for one evaluation. Source: ARCH §6.6, FR-303."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    tasks: tuple[TaskSlice, ...] = ()
