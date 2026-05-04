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

from app.config import Settings
from app.orchestrator.base import Orchestrator
from app.rules.engine import RuleEngine
from app.schemas.application import Application
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope
from app.services.cache import SessionCache
from app.vision.base import VisionExtractor

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
        raise NotImplementedError("Cycle A skeleton")
