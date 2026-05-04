"""Batch worker — pull-based, reactive-streams-style consumer.

Two coroutines collaborate via the per-batch ``BoundedQueue``:

1. ``_producer`` — iterates ``in_flight.items`` in submission order and awaits
   ``queue.put(item)`` for each. Saturates at ``maxsize=k+1`` and blocks until
   the consumer drains. **First-label-individual (FR-401)**: producer starts
   concurrently with the consumer; item 0's put returns immediately and the
   consumer's first get returns it without waiting for the lookahead window.
2. ``_consume`` — ``await queue.get()`` → ``evaluator.evaluate(app, label)`` →
   ``in_flight.record_result(label_id, envelope)`` → broadcast ``label-result``
   SSE event → ``anomaly.observe(headline_reason_code)`` → broadcast
   ``anomaly-advisory`` if one fires. Emits ``stream-end`` after the last item.

Mid-batch override (FR-404) is handled outside this module: the override
endpoint (T8) mutates ``in_flight.results[label_id]`` directly. The worker
never inspects ``overrides`` as a stop condition.

Source: ARCH §4.2.7 / §5.2 / L1 §2.2.
"""
from __future__ import annotations

import asyncio
import logging

from app.api._sse_bus import SSEBus
from app.batch.anomaly import AnomalyDetector
from app.batch.state import InFlightBatch
from app.schemas.application import Application
from app.schemas.batch import BatchItem
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope

_logger = logging.getLogger("app.batch.worker")


def _headline_reason_code(envelope: DispositionEnvelope) -> str | None:
    """Pick one canonical reason-code string for anomaly observation.

    See module docstring + plan §"Reason-code extraction" for the rationale:
    PerRuleTraceEntry carries no `reason_code` field; reason codes live on
    RuleFindingWire inside envelope.fields, with a short-circuit fallback to
    per_rule_trace[0].rule_id (E5 convention for legibility / FR-900
    envelopes that have no per-field findings)."""
    if envelope.disposition == "pass":
        return None
    for field in envelope.fields:
        for finding in field.rule_findings:
            if finding.disposition in ("fail", "needs_review"):
                return finding.reason_code
    if envelope.audit_trail.per_rule_trace:
        return envelope.audit_trail.per_rule_trace[0].rule_id
    return None


class BatchWorker:
    """Pull-based batch consumer."""

    def __init__(
        self,
        *,
        in_flight: InFlightBatch,
        evaluator,
        anomaly: AnomalyDetector,
        bus: SSEBus,
    ) -> None:
        self._in_flight = in_flight
        self._evaluator = evaluator
        self._anomaly = anomaly
        self._bus = bus
        # Stub registries — production wires from `app.state.applications` /
        # the submission registry; tests inject by populating these dicts.
        self._app_lookup: dict[str, Application] = {}
        self._label_lookup: dict[str, Label] = {}

    def _resolve_application(self, item: BatchItem) -> Application:
        """Resolve the Application for a queued BatchItem.

        Cycle A skeleton stub: synthesizes a minimal `Application` from the
        `application_ref`. Cycle C upgrades to read from `app.state.applications`
        when the real submission registry exists. Tests override by populating
        `self._app_lookup` directly."""
        if item.application_ref in self._app_lookup:
            return self._app_lookup[item.application_ref]
        return Application(
            application_id=item.application_ref,
            evaluation_id=item.label_id,
        )

    def _resolve_label(self, item: BatchItem) -> Label:
        """Resolve the Label payload for a queued BatchItem.

        Cycle A skeleton stub: synthesizes a minimal schema-valid `Label` from
        the `label_id`. The real payload (image_bytes etc.) lives in the
        submission registry — Cycle C wires that. Tests override by populating
        `self._label_lookup` directly."""
        if item.label_id in self._label_lookup:
            return self._label_lookup[item.label_id]
        return Label(
            label_id=item.label_id,
            batch_id=self._in_flight.batch_id,
            image_bytes=b"\x89PNG\r\n\x1a\n",
            content_type="image/png",
            face_tag="front",
        )

    async def _producer(self) -> None:
        for item in self._in_flight.items:
            await self._in_flight.queue.put(item)

    async def _consume(self) -> None:
        total = len(self._in_flight.items)
        for queue_position in range(total):
            item: BatchItem = await self._in_flight.queue.get()
            application = self._resolve_application(item)
            label = self._resolve_label(item)
            envelope = await self._evaluator.evaluate(application, label)
            self._in_flight.record_result(item.label_id, envelope)

            # Per-label SSE event with queue_position
            self._bus.broadcast({
                "event": "label-result",
                "data": {
                    "batch_id": self._in_flight.batch_id,
                    "queue_position": queue_position,
                    "envelope": envelope.model_dump(mode="json"),
                },
            })

            # Anomaly observation. Bind once: the helper is pure today, but
            # binding here pins the contract that ``recent_dispositions`` and
            # ``observe`` see the same code, even if the helper later acquires
            # side effects.
            headline_code = _headline_reason_code(envelope)
            self._in_flight.recent_dispositions.append(headline_code)
            advisory = self._anomaly.observe(headline_code)
            if advisory is not None:
                self._bus.broadcast({
                    "event": "anomaly-advisory",
                    "data": {
                        "batch_id": self._in_flight.batch_id,
                        "advisory_id": advisory.advisory_id,
                        "reason_code": advisory.reason_code,
                        "count": advisory.count,
                        "window": advisory.window,
                    },
                })

        self._bus.broadcast({
            "event": "stream-end",
            "data": {
                "batch_id": self._in_flight.batch_id,
                "total_count": total,
            },
        })

    async def run(self) -> None:
        producer_task = asyncio.create_task(self._producer())
        try:
            await self._consume()
        finally:
            # Cancel the producer (which may be parked on a saturated
            # ``queue.put``) and drain any pending exception. Without the
            # cancel, a ``_consume`` error would leave the producer parked
            # forever and ``await producer_task`` would deadlock.
            producer_task.cancel()
            await asyncio.gather(producer_task, return_exceptions=True)
