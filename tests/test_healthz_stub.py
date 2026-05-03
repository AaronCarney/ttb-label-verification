"""GET /healthz returns 200 with the documented payload shape (E1 stub).

L1 AC #3: the endpoint does NOT invoke any seam yet; full warm-up lands in E5.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app_with_healthz_only() -> FastAPI:
    from app.api.healthz import router

    app = FastAPI()
    app.include_router(router)
    return app


def test_healthz_returns_200_with_documented_shape() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    os.environ.setdefault("VISION_MODE", "cloud")
    os.environ.setdefault("ORCHESTRATOR_BACKEND", "openai")

    client = TestClient(_make_app_with_healthz_only())
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "mode" in body
    assert body["mode"]["vision"] in {"local", "cloud", "auto"}
    assert body["mode"]["orchestrator"] in {"openai", "anthropic"}


def test_healthz_does_not_invoke_seams() -> None:
    """E1 §4 AC #3: ``/healthz`` does not call ``extract()`` or ``refine()``."""
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")

    client = TestClient(_make_app_with_healthz_only())
    response = client.get("/healthz")
    assert response.status_code == 200
    # If the route invoked the placeholder providers' seam methods, we would
    # have surfaced a 500 with a NotImplementedError. The 200 response
    # transitively asserts the seams were not invoked.
