"""GET /healthz route. E1 ships the stub; E5 wires the full warm-up sentinel.

L1 §4 AC #3 / AC #7:
- 200 with ``{"status": "ok", "version": <semver>, "mode": {vision, orchestrator}}``.
- A single structured-log JSON line per invocation.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.config import Settings


router = APIRouter(tags=["health"])
_logger = logging.getLogger("app.healthz")


def _get_settings() -> Settings:
    return Settings()


@router.get("/healthz")
async def healthz(settings: Settings = Depends(_get_settings)) -> dict[str, object]:
    body: dict[str, object] = {
        "status": "ok",
        "version": settings.app_version,
        "mode": {
            "vision": settings.vision_mode,
            "orchestrator": settings.orchestrator_backend,
        },
    }
    _logger.info("healthz_invoked", extra={"reason_code": "ENGINE.OK.NONE"})
    return body
