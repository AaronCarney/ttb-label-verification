"""FR-704 / D-017: fixture-07 must produce disposition_confidence.band == "medium"
when OCR returns mid-confidence on the warning field."""
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.deps import build_evaluator
from app.schemas.application import Application
from app.schemas.expected import ExpectedValue
from app.schemas.label import Label


_OCR_REPLAY_GAP = pytest.mark.xfail(
    reason="upstream gap: CloudVisionExtractor has no test-replay seam (E3 owns); "
           "remove when OCR replay lands. The borderline-band assertion is the AC "
           "contract — passes once OCR resolves mid-confidence values.",
    strict=False,
)


@pytest.mark.asyncio
@_OCR_REPLAY_GAP
async def test_fixture_07_borderline_band():
    settings = Settings()
    evaluator = build_evaluator(settings)
    expected_raw = json.loads(
        (Path("fixtures") / "07-borderline-confidence" / "expected.json").read_text()
    )
    application = Application(
        application_id="A-fr704",
        evaluation_id="EV-07-borderline",
        expected_values=tuple(ExpectedValue(**e) for e in expected_raw),
    )
    img = Path("fixtures") / "07-borderline-confidence" / "label.png"
    label = Label(label_id="07-borderline", batch_id="fr704",
                  image_bytes=img.read_bytes(), content_type="image/png",
                  face_tag="front", dimensions=None)
    envelope = await evaluator.evaluate(application=application, label=label)
    # FR-704: medium band — numeric is min over per-field confidences (D-017)
    assert envelope.disposition_confidence.band == "medium", (
        f"expected medium band, got {envelope.disposition_confidence.band} "
        f"(numeric={envelope.disposition_confidence.numeric})"
    )
    assert 0.55 <= envelope.disposition_confidence.numeric <= 0.75
    # FR-704: lowest-confidence field surfaced — verify at least one field is
    # in the medium-or-low band (i.e., the borderline driver).
    has_borderline_field = any(
        f.field_confidence.band in ("medium", "low") for f in envelope.fields
    )
    assert has_borderline_field, (
        "expected at least one field with medium/low confidence (the FR-704 driver)"
    )
