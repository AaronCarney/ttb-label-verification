"""T4: page-shell GET routes and the StaticFiles mount.

These routes serve Jinja2 shells only; engine logic lives in E5/E6 routes.
The test guards: (a) /healthz is unaffected by the additive UI registration,
(b) GET / returns the single-mode shell with data-mode="single",
(c) GET /batch/{batch_id} returns the batch shell with data-mode="batch" and
    data-batch-id="{batch_id}",
(d) /static/island/.gitkeep is served (proves the StaticFiles mount works).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_healthz_still_passes(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200


def test_single_page_shell(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="root"' in response.text
    assert 'data-mode="single"' in response.text
    assert "/static/island/single.js" in response.text
    # noscript fallback per L1 §2.6.
    assert "<noscript>" in response.text
    assert "POST /labels" in response.text


def test_batch_page_shell(client: TestClient) -> None:
    response = client.get("/batch/abc-123")
    assert response.status_code == 200
    assert 'data-mode="batch"' in response.text
    assert 'data-batch-id="abc-123"' in response.text
    assert "/static/island/batch.js" in response.text


def test_static_island_mount(client: TestClient) -> None:
    """The StaticFiles mount serves files under app/ui/static/. The .gitkeep
    placeholder proves the mount works before the real bundle lands (T34)."""
    response = client.get("/static/island/.gitkeep")
    assert response.status_code == 200


def test_uswds_skip_link_present(client: TestClient) -> None:
    """NFR-A11Y-002 keyboard-operable end-to-end: the 'Skip to main content'
    link must be the first focusable element on every page."""
    response = client.get("/")
    assert 'class="skip-link"' in response.text
    assert "Skip to main content" in response.text
