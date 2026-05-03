"""PRD §6.4 error contract."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ErrorEnvelope(BaseModel):
    """PRD §6.4 boundary error envelope.

    Reason codes follow the T3 §Q3.10 taxonomy
    (``BIN.SUB.SPECIFIC[.QUALIFIER]`` grammar).
    """

    model_config = ConfigDict(extra="forbid")

    error_kind: Literal["rejected_input", "engine_failure", "partial_completion"]
    reason_code: str
    message: str
    details: dict[str, Any]
