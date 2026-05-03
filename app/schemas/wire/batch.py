"""PRD §6.3 batch envelope contract."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BatchItemRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label_ref: str
    application_ref: str


class BatchEnvelope(BaseModel):
    """PRD §6.3 batch envelope. ``agent_id`` is structurally present but
    single-agent in MVP per T6 §Q6.7."""

    model_config = ConfigDict(extra="forbid")

    batch_id: str
    agent_id: str
    submitted_at: datetime
    items: tuple[BatchItemRef, ...]
