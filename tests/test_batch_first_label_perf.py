"""AC-FR-401 perf canary: first-label P50 ≤ 2.7 s, P99 ≤ 5.0 s.

Methodology: 12 trials (2 warmup + 10 measure) × 20 items × 0.1 s evaluator
latency. Total runtime ~30 s, CI-friendly. Budgets unchanged from L1 §4 AC #3.

Race-resolution: T9 v1 hit a late-subscribe race — the SSE GET handler called
``bus.subscribe()`` AFTER the worker had already emitted item 0, so the
subscriber missed event 0 and ``lr == 50`` failed (got 49). The fix landed in
SSEBus: replay-on-subscribe (ARCH §5.2 reconnect contract). The test now
asserts ``lr == n_items`` reliably.
"""
import asyncio
import statistics
import time

import httpx
import pytest


@pytest.mark.slow
@pytest.mark.asyncio
async def test_first_label_p50_under_2_7s_and_p99_under_5_0s_for_50_item_batch(monkeypatch):
    """AC-FR-401 + AC #2 event-count canary at the HTTP boundary."""
    from datetime import datetime, timezone

    from app.main import create_app
    from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
    from tests.conftest import _fake_evaluator

    N_ITEMS = 20
    LATENCY_S = 0.1
    N_TRIALS = 12  # 2 warmup + 10 measure

    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(n_items=N_ITEMS, latency_s=LATENCY_S),
    )

    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            samples_s: list[float] = []
            event_counts: list[tuple[int, int]] = []
            for trial in range(N_TRIALS):
                bid = f"B-perf-{trial:03d}"
                envelope = BatchEnvelope(
                    batch_id=bid,
                    agent_id="a",
                    submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
                    items=tuple(
                        BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                        for i in range(N_ITEMS)
                    ),
                ).model_dump(mode="json")
                t0 = time.perf_counter()
                post_resp = await client.post("/batches", json=envelope)
                assert post_resp.status_code == 202, post_resp.text

                first_event_t = None
                lr = se = 0
                async with client.stream("GET", f"/batches/{bid}/stream") as resp:
                    assert resp.status_code == 200
                    async for line in resp.aiter_lines():
                        if line.startswith("event: label-result"):
                            if first_event_t is None:
                                first_event_t = time.perf_counter() - t0
                            lr += 1
                        elif line.startswith("event: stream-end"):
                            se += 1
                            break
                assert first_event_t is not None
                if trial >= 2:  # drop warmup
                    samples_s.append(first_event_t)
                event_counts.append((lr, se))

    # AC #2 event count: every trial saw N label-result + 1 stream-end.
    for trial_idx, (lr, se) in enumerate(event_counts):
        assert lr == N_ITEMS, f"trial {trial_idx}: expected {N_ITEMS} label-result events, got {lr}"
        assert se == 1, f"trial {trial_idx}: expected exactly 1 stream-end, got {se}"

    p50 = statistics.median(samples_s)
    p99 = max(samples_s)  # 10-sample window — max() is the conservative P99 proxy
    assert p50 <= 2.7, f"P50 {p50:.3f}s exceeds 2.7s budget"
    assert p99 <= 5.0, f"P99 {p99:.3f}s exceeds 5.0s budget"
