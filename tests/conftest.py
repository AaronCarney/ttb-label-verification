"""Shared pytest fixtures for the TTB Label Verification test suite."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from app.schemas.label import Label


@pytest.fixture
def wire_fixtures_dir() -> Path:
    return Path(__file__).parent / "wire_fixtures"


@pytest.fixture
def synthetic_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _redact_authorization_headers(payload: dict) -> dict:
    """Strip Authorization headers from a recording payload before write.
    Per L1 §7 risk: prevents leaked API keys in committed recordings."""
    import copy
    out = copy.deepcopy(payload)
    headers = out.get("headers")
    if isinstance(headers, dict):
        for key in list(headers.keys()):
            if key.lower() == "authorization" or key.lower() == "x-api-key":
                headers[key] = "REDACTED"
    return out


def _stub_label(
    *,
    label_id: str = "lbl-test",
    batch_id: str = "B-test",
    image_bytes: bytes = b"\x89PNG\r\n\x1a\n",
    content_type: str = "image/png",
    face_tag: str = "front",
    dimensions=None,
) -> Label:
    return Label(
        label_id=label_id,
        batch_id=batch_id,
        image_bytes=image_bytes,
        content_type=content_type,
        face_tag=face_tag,
        dimensions=dimensions,
    )


# === E6 batch helpers (T5) — appended; do not edit above this marker ===
from collections.abc import Iterable

import pytest

from app.schemas.wire.disposition import DispositionEnvelope


def _stub_disposition_envelope(idx: int = 0, *, disposition: str = "pass") -> DispositionEnvelope:
    """Minimal `DispositionEnvelope` for batch tests.

    Pre-flight inspection note: if `Metrics` or `AuditRecord` schemas have
    grown additional required fields since this plan was written, add them
    with the simplest schema-conforming defaults (see plan §Conventions
    `_fake_evaluator()`)."""
    from datetime import datetime, timezone

    from app.schemas.audit import AuditRecord
    from app.schemas.metrics import Metrics
    from app.schemas.wire.disposition import ConfidenceBand

    now = datetime.now(timezone.utc)
    return DispositionEnvelope(
        evaluation_id=f"EV-{idx:04d}",
        label_ref=f"lbl-{idx:04d}",
        disposition=disposition,
        disposition_confidence=ConfidenceBand(band="high", numeric=0.95),
        fields=(),
        audit_trail=AuditRecord(
            evaluation_id=f"EV-{idx:04d}",
            rule_set_version="t",
            input_hash="0" * 64,
            output_hash="0" * 64,
            started_at=now,
            completed_at=now,
            per_rule_trace=(),
        ),
        metrics=Metrics(
            total_duration_ms=10,
            per_rule_durations_ms=(),
            vision_duration_ms=5,
            orchestrator_duration_ms=0,
        ),
    )


def _fake_evaluator(
    plan: Iterable[tuple[float, DispositionEnvelope]] | None = None,
    *,
    n_items: int = 1,
    latency_s: float = 0.0,
    envelope_factory=None,
):
    """Build a FakeEvaluator. If `plan` is None, repeats `(latency_s, envelope_factory(i))`
    for `n_items` invocations."""
    from tests._fakes.evaluator import FakeEvaluator

    if plan is not None:
        return FakeEvaluator(plan)
    factory = envelope_factory or _stub_disposition_envelope
    return FakeEvaluator((latency_s, factory(i)) for i in range(n_items))


@pytest.fixture(autouse=True)
def _reset_reason_code_cache():
    """E6 isolation: the override endpoint caches the reason-code registry
    on first request. Reset between tests so a test that monkeypatches the
    YAML or cwd does not silently use the cached set from a prior test."""
    try:
        import app.api.overrides as _overrides_mod
    except ImportError:
        # T8 hasn't landed yet — skip
        yield
        return
    _overrides_mod._ACCEPTED_REASON_CODES_CACHE = None
    yield
    _overrides_mod._ACCEPTED_REASON_CODES_CACHE = None
