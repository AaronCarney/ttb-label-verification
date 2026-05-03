"""Application-derived reference values. Source: ARCH §6.3."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BeverageClass(str, Enum):
    WINE = "wine"
    SPIRITS = "spirits"
    MALT = "malt"


class ExpectedValue(BaseModel):
    """What the application JSON says should be on the label.

    Constructed by the Application Service from the inbound application envelope
    (PRD §6.1) on each evaluation; held only for the call frame.

    Source: ARCH §6.3.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_id: str
    value: Any | None = None
    aliases: tuple[str, ...] = ()
    abv_labeled_pct: Decimal | None = None
    abv_actual_pct: Decimal | None = None
    container_volume_ml: Decimal | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    source_cola: str | None = None
