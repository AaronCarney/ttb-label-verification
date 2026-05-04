"""POST /batches, GET /batches/{batch_id}/stream, GET /batches/{batch_id}.

Source: ARCH §3.2 / L1 §2.5.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.api._sse_bus import SSEBus
from app.batch.anomaly import AnomalyDetector
from app.batch.state import InFlightBatch
from app.batch.worker import BatchWorker
from app.config import Settings
from app.schemas.batch import BatchItem, ItemState
from app.schemas.wire.batch import BatchEnvelope

router = APIRouter()
_logger = logging.getLogger("app.api.batches")


def _get_settings() -> Settings:
    """Module-private Settings factory. Mirrors E5's app/api/healthz.py and
    app/api/labels.py convention — `app/deps.py` exposes no `get_settings`
    by design. Tests override via FastAPI's dependency_overrides[]."""
    return Settings()


def _build_in_flight_from_envelope(env: BatchEnvelope, *, lookahead_k: int) -> InFlightBatch:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    items = tuple(
        BatchItem(
            label_id=ref.label_ref,
            application_ref=ref.application_ref,
            state=ItemState.QUEUED,
            result=None,
            enqueued_at=now,
        )
        for ref in env.items
    )
    return InFlightBatch(
        batch_id=env.batch_id,
        agent_id=env.agent_id,
        items=items,
        lookahead_k=lookahead_k,
    )


def _resolve_lookahead_k(settings: Settings) -> int:
    """LOOKAHEAD_K env override (AC #10). Default 3."""
    import os
    raw = os.environ.get("LOOKAHEAD_K", "3")
    try:
        k = int(raw)
    except ValueError:
        k = 3
    return max(1, k)


@router.post("/batches", status_code=202)
async def post_batches(
    envelope: BatchEnvelope,
    request: Request,
    settings: Settings = Depends(_get_settings),
) -> dict[str, str]:
    """Spawn a worker and return the batch_id."""
    if envelope.batch_id in request.app.state.batches:
        raise HTTPException(status_code=409, detail=f"batch_id {envelope.batch_id} already in flight")

    lookahead_k = _resolve_lookahead_k(settings)
    in_flight = _build_in_flight_from_envelope(envelope, lookahead_k=lookahead_k)
    bus = SSEBus()
    request.app.state.batches[envelope.batch_id] = in_flight
    request.app.state.buses[envelope.batch_id] = bus

    # Build evaluator via the existing E5 factory; tests monkeypatch this.
    from app.deps import build_evaluator
    evaluator = build_evaluator(settings)

    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=evaluator,
        anomaly=AnomalyDetector(),
        bus=bus,
    )
    asyncio.create_task(worker.run())
    return {"batch_id": envelope.batch_id}


@router.get("/batches/{batch_id}")
async def get_batch_snapshot(batch_id: str, request: Request) -> dict[str, Any]:
    in_flight = request.app.state.batches.get(batch_id)
    if in_flight is None:
        raise HTTPException(status_code=404, detail=f"batch_id {batch_id} not found")
    return in_flight.snapshot().model_dump(mode="json")


@router.get("/batches/{batch_id}/stream")
async def get_batch_stream(batch_id: str, request: Request):
    in_flight = request.app.state.batches.get(batch_id)
    if in_flight is None:
        raise HTTPException(status_code=404, detail=f"batch_id {batch_id} not found")
    bus: SSEBus | None = request.app.state.buses.get(batch_id)
    if bus is None:
        raise HTTPException(status_code=404, detail=f"batch_id {batch_id} stream not registered")
    sub = bus.subscribe()

    async def _event_generator():
        try:
            async for evt in bus.iterate(sub, terminator_event="stream-end"):
                yield {"event": evt["event"], "data": evt["data"]}
        finally:
            bus.unsubscribe(sub)

    return EventSourceResponse(_event_generator())
