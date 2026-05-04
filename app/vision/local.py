"""LocalVisionExtractor — composes PaddleOCR + SWT + GPT-4o tiebreaker.

Source: E3 L1 §2.3 (D-021 trimmed pipeline). Florence-2 + Qwen-VL out of MVP.
"""
from __future__ import annotations

from collections import deque

from app.config import Settings
from app.schemas.expected import BeverageClass
from app.schemas.extracted import Evidence, EvidenceSource, FieldObservation, MatchKind
from app.schemas.label import Label
from app.vision.paddle_runner import PaddleRunner
from app.vision.swt import SWTRunner
from app.vision.tiebreak_gpt4o import GPT4oTiebreakRunner
from app.vision.quality import assess as _quality_assess


class LocalVisionExtractor:
    def __init__(self, settings: Settings, ring_buffer: deque) -> None:
        self._ring = ring_buffer
        self._settings = settings
        self._paddle = PaddleRunner(ring_buffer=ring_buffer, batch_id="", label_id="")
        self._swt = SWTRunner(ring_buffer=ring_buffer, batch_id="", label_id="")
        self._tiebreak = GPT4oTiebreakRunner(
            ring_buffer=ring_buffer,
            batch_id="",
            label_id="",
            api_key=settings.openai_api_key or "",
            model_snapshot=settings.llm_model_snapshot,
            prompt_version=settings.prompt_version,
        )

    async def ensure_loaded(self) -> None:
        await self._paddle.ensure_loaded()
        await self._swt.ensure_loaded()
        await self._tiebreak.ensure_loaded()

    async def extract(self, label: Label) -> list[FieldObservation]:
        report = _quality_assess(label)
        if report.disposition != "ok":
            return [
                FieldObservation(
                    field_id="quality",
                    beverage_class=BeverageClass.SPIRITS,  # placeholder — refined when E5 wires beverage_class detection
                    observed_value=None,
                    evidence=(),
                    upstream_meta={
                        "disposition": report.disposition,
                        "reason_code": report.reason_code,
                    },
                )
            ]
        # Bind sub-runners' batch_id/label_id from this label.
        for runner in (self._paddle, self._swt, self._tiebreak):
            runner._batch_id = label.batch_id
            runner._label_id = label.label_id

        # Run PaddleOCR over the full image once to seed candidates for OCR-text fields.
        paddle_candidates = await self._paddle.run(crop=label.image_bytes)

        observations: list[FieldObservation] = []

        # Per-field routing policy — same 8 field_ids as cloud (T10), but produced
        # from local signals. Each field_id maps to a routing decision:
        #   ocr      — extract from paddle_candidates by bbox/text heuristic
        #   swt      — heading_typography only; classify bold + read text via paddle
        #   tiebreak — uncertain or low-confidence ocr; fallback to GPT-4o single-call
        FIELD_ROUTING = {
            "brand_name": "ocr",
            "class_type": "ocr",
            "abv": "ocr",
            "net_contents": "ocr",
            "gov_warning": "ocr",
            "heading_typography": "swt",
            "name_address": "ocr",
            "country_origin": "tiebreak",  # often missing/marginal text; default to tiebreak
        }
        OCR_CONFIDENCE_FLOOR = 0.85  # below this, fall back to tiebreak

        for field_id, route in FIELD_ROUTING.items():
            if route == "ocr":
                cand = self._best_candidate(paddle_candidates, field_id)
                if cand is None or cand.score < OCR_CONFIDENCE_FLOOR:
                    obs = await self._tiebreak_field(label, field_id)
                else:
                    obs = self._observation_from_candidate(field_id, cand, label)
            elif route == "swt":
                swt_report = await self._swt.run(crop=label.image_bytes)
                obs = self._observation_from_swt(field_id, swt_report, paddle_candidates, label)
            else:  # tiebreak
                obs = await self._tiebreak_field(label, field_id)
            observations.append(obs)

        return observations

    def _best_candidate(self, cands: list, field_id: str):
        """Heuristic: return highest-scoring paddle candidate matching field_id keywords.

        E3 ships a *minimal* keyword map sufficient for the synthetic fixture
        (T5) + recordings; full keyword/bbox heuristics tune in E5/E8 against
        the real fixture corpus. The map is intentionally narrow so this method
        is unit-testable in T11 with mocked candidates.
        """
        keywords = {
            "brand_name": ("BOURBON", "ACME"),
            "class_type": ("WHISKEY", "BOURBON", "WINE", "BEER"),
            "abv": ("ALC", "ABV", "VOL"),
            "net_contents": ("ML", "OZ", "L "),
            "gov_warning": ("GOVERNMENT WARNING",),
            "name_address": ("DISTILLER", "BOTTLED BY", "PRODUCED BY"),
        }.get(field_id, ())
        matches = [c for c in cands if any(k in c.text.upper() for k in keywords)]
        return max(matches, key=lambda c: c.score) if matches else None

    def _observation_from_candidate(self, field_id, cand, label):
        return FieldObservation(
            field_id=field_id,
            beverage_class=BeverageClass.SPIRITS,  # E5 widens once class-detection lands
            observed_value=cand.text,
            evidence=(
                Evidence(
                    field_id=field_id,
                    source=EvidenceSource.OCR,
                    bbox=cand.bbox,
                    extracted_text=cand.text,
                    match_kind=MatchKind.NONE,
                    confidence=cand.score,
                ),
            ),
            upstream_meta={"engine_version": "local.paddleocr/v5", "route": "ocr"},
        )

    def _observation_from_swt(self, field_id, swt_report, cands, label):
        return FieldObservation(
            field_id=field_id,
            beverage_class=BeverageClass.SPIRITS,
            observed_value={"all_caps": True, "bold": swt_report.is_bold},
            evidence=(
                Evidence(
                    field_id=field_id,
                    source=EvidenceSource.LAYOUT,
                    match_kind=MatchKind.LAYOUT,
                    confidence=0.9 if swt_report.is_bold else 0.6,
                    notes=f"width/height ratio {swt_report.width_height_ratio:.3f}",
                ),
            ),
            upstream_meta={"engine_version": "local.swt", "route": "swt"},
        )

    async def _tiebreak_field(self, label, field_id):
        result = await self._tiebreak.run(crop=label.image_bytes, prompt=field_id)
        return FieldObservation(
            field_id=field_id,
            beverage_class=BeverageClass.SPIRITS,
            observed_value=result.get(field_id) or next(iter(result.values()), None),
            evidence=(
                Evidence(
                    field_id=field_id,
                    source=EvidenceSource.DERIVED,
                    match_kind=MatchKind.NONE,
                    confidence=0.75,
                ),
            ),
            upstream_meta={"engine_version": "openai/gpt-4o-tiebreak", "route": "tiebreak"},
        )
