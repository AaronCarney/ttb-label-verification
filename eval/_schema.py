"""Manifest line schema + history record schema (E8 T2)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    source: str = Field(..., description="`^synthetic-<slug>` or COLA Registry id")


class ExpectedRule(BaseModel):
    rule_id: str
    result: Literal["pass", "fail", "needs_review"]
    reason_code: str | None = None


class ManifestEntry(BaseModel):
    label_id: str
    application_ref: str  # path or URL
    image_ref: str
    expected_disposition: Literal["pass", "fail", "needs_review"]
    expected_per_rule: list[ExpectedRule]
    provenance: Provenance
    class_balance_tag: Literal["spirits", "wine", "malt"]
    borderline_band: bool = False


class HistoryRecord(BaseModel):
    """Single entry in eval/history/<ISO-8601>.json (one per harness run)."""
    timestamp: str
    subset: Literal["smoke", "full"]
    n_labels: int
    macro_f1: float
    per_rule_precision: dict[str, float]
    per_rule_recall: dict[str, float]
    ece: float
    latency_p50_s: float
    latency_p95_s: float
    latency_p99_s: float
    cost_weighted_score: float  # cost-weighted accuracy (T9 Q9.1); FP penalty 3×, FR 1×
