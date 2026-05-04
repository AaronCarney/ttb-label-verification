"""Application Service chokepoint. Source: ARCH §4.2.2, E5 L1 §2.1.

Composes vision (E3), rule engine (E2), orchestrator (E4) into one
end-to-end evaluation behind ``POST /labels``.

Thin — all logic lives in helpers under ``app/services/`` (disposition,
aggregation, patcher, triggers, envelope_builder, audit, metrics_builder,
cache, engine_meta). The Evaluator's job is orchestration + chokepoint
exception routing (P4: every downstream exception → needs_review).
"""
from __future__ import annotations

import logging
import time

from app.config import Settings
from app.orchestrator.base import Orchestrator
from app.rules.engine import RuleEngine
from app.schemas.application import Application
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope
from app.services.cache import SessionCache
from app.vision.base import VisionExtractor
from app.vision.quality import assess as assess_quality

_logger = logging.getLogger("app.services.evaluator")


class Evaluator:
    def __init__(
        self,
        *,
        vision: VisionExtractor,
        rules: RuleEngine,
        orchestrator: Orchestrator,
        settings: Settings,
        cache: SessionCache | None = None,
    ) -> None:
        self._vision = vision
        self._rules = rules
        self._orchestrator = orchestrator
        self._settings = settings
        self._cache = cache

    async def evaluate(self, application: Application, label: Label) -> DispositionEnvelope:
        from app.services.audit import AuditRecorder
        from app.services.engine_meta import EvaluationTimeline
        from app.services.envelope_builder import build_success_envelope
        from app.services.metrics_builder import MetricsBuilder

        t_total = time.monotonic()
        timeline = EvaluationTimeline(evaluation_id=application.evaluation_id)

        # Step 1: vision
        t0 = time.monotonic()
        observations = await self._vision.extract(label)
        timeline.record_vision_done(int((time.monotonic() - t0) * 1000))

        # Step 2: legibility short-circuit (L1 §2.1 step 2; FR-505/603)
        quality = assess_quality(label)
        if quality.disposition == "needs_better_photo":
            timeline.record_failure(
                reason_code=quality.reason_code,
                message=f"image quality insufficient: {quality.reason_code}",
                exception_class="N/A",
            )
            return self._short_circuit(application, label, timeline, quality.reason_code, t_total)

        # Step 3-4: rules
        started_at_ms = int(time.monotonic() * 1000)
        ctx = self._rules.build_validator_context(started_at_ms=started_at_ms)
        expected = tuple(application.expected_values)
        results = await self._rules.evaluate(observations, expected, ctx)

        # Step 5-6: orchestrator (conditional) + FR-303 patching
        from app.services.patcher import patch_validation_results
        from app.services.triggers import should_invoke_orchestrator
        if should_invoke_orchestrator(results):
            t_orch = time.monotonic()
            try:
                refined = await self._orchestrator.refine(application, list(observations), list(results))
                results = patch_validation_results(results, refined)
            except Exception as e:  # noqa: BLE001
                timeline.record_failure(
                    reason_code="ENGINE.MODEL.UNAVAILABLE",
                    message=str(e), exception_class=type(e).__name__,
                )
            finally:
                timeline.record_orchestrator_done(int((time.monotonic() - t_orch) * 1000))

        # Surface failures into per_rule_trace so AuditRecorder picks them up.
        for failure in timeline.failures:
            timeline.record_rule_done(rule_id=failure.reason_code, duration_ms=0,
                                      disposition="needs_review",
                                      evidence_ref=f"engine_failure/{failure.exception_class}")

        # Cycle B placeholder (will be replaced by Cycle D)
        timeline.finish(total_duration_ms=int((time.monotonic() - t_total) * 1000))
        envelope_for_hash = {"evaluation_id": application.evaluation_id, "disposition": "pass", "fields": []}
        audit = AuditRecorder().assemble(timeline=timeline, application=application, label=label,
                                         envelope_for_hash=envelope_for_hash)
        metrics = MetricsBuilder().build(timeline)
        return build_success_envelope(
            application=application, label=label, timeline=timeline,
            disposition="pass", fields=(), audit=audit, metrics=metrics,
        )

    def _short_circuit(self, application, label, timeline, reason_code: str, t_total: float):
        from app.services.audit import AuditRecorder
        from app.services.envelope_builder import build_short_circuit_envelope
        from app.services.metrics_builder import MetricsBuilder

        timeline.finish(total_duration_ms=int((time.monotonic() - t_total) * 1000))
        envelope_for_hash = {"evaluation_id": application.evaluation_id, "disposition": "needs_review",
                             "reason_code": reason_code}
        audit = AuditRecorder().assemble(timeline=timeline, application=application, label=label,
                                         envelope_for_hash=envelope_for_hash)
        metrics = MetricsBuilder().build(timeline)
        return build_short_circuit_envelope(
            application=application, label=label, timeline=timeline,
            reason_code=reason_code, audit=audit, metrics=metrics,
        )
