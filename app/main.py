"""FastAPI application factory. Source: ARCH §14.3.

Boot sequence (E1 subset; E2–E8 extend):
1. Read ``Settings``.
2. Configure logging (JSON-line stdout + redaction filter).
3. Construct the FastAPI app.
4. Register the ``/healthz`` route.

Later epochs add: rule-loader startup, vision/orchestrator wiring, label/batch/
override/eval routes, UI mounts, SSE.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.healthz import router as healthz_router
from app.config import Settings
from app.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings)

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.getLogger("app.main").info(
            "app_startup",
            extra={
                "reason_code": "ENGINE.OK.NONE",
                "rule_set_version": "0.0.0",  # E2 will overwrite at rule-pack load.
                "model_version": settings.llm_model_snapshot,
                "prompt_version": settings.prompt_version,
            },
        )
        app.state.batches = {}  # E6 NFR-DATA-001/002 — process-local in-flight batches
        app.state.buses = {}    # E6 — per-batch SSEBus registry, keyed by batch_id
        yield
        app.state.batches.clear()  # E6 lifespan teardown evicts all in-flight batches
        app.state.buses.clear()    # E6 — drop bus subscribers + queues

    application = FastAPI(
        title="TTB Label Verification (prototype)",
        version=settings.app_version,
        lifespan=_lifespan,
    )
    application.include_router(healthz_router)

    from app.api import labels as labels_module
    application.include_router(labels_module.router)

    from app.api import raw as raw_module
    application.include_router(raw_module.router)

    from app.api import batches as batches_module
    application.include_router(batches_module.router)

    # Pre-init state so routes work even when lifespan hasn't fired (e.g. httpx tests).
    # Lifespan startup will re-assign; shutdown will clear.
    application.state.batches = {}
    application.state.buses = {}

    return application


app: FastAPI = create_app()
