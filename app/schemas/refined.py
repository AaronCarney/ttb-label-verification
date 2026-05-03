"""AI orchestrator output. Source: ARCH §4.2.6, PRD FR-303.

FR-303 invariant: this model declares **no top-level ``disposition`` field**.
The deterministic Rule Engine produces dispositions; the orchestrator only
enriches reasoning, disambiguates borderline brand matches, or reconciles OCR.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Refined(BaseModel):
    """Orchestrator output for one evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    task: Literal[
        "brand_borderline",
        "reasoning_enrichment",
        "ocr_reconciliation",
    ] | None = None
    text: str | None = None
    # NB: ``model_disposition`` is the model's *suggestion*, not the verdict.
    # Allowed values exclude ``fail`` so the model cannot recommend a fail flip.
    model_disposition: Literal["pass", "needs_review"] | None = None
