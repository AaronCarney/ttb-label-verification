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

from app.api.ui import _get_settings
from app.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def dev_client() -> TestClient:
    """Client with DEV_MODE=1 forced via dependency override (D-019)."""
    app = create_app()
    app.dependency_overrides[_get_settings] = lambda: Settings(DEV_MODE="1")
    return TestClient(app)


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
    """The StaticFiles mount serves files under app/ui/static/. After T34 lands
    the built bundle, /static/island/style.css is the canonical mount sentinel
    (Vite's emptyOutDir wipes any placeholder file on each build)."""
    response = client.get("/static/island/style.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_dev_mode_off_by_default(client: TestClient) -> None:
    """RawJSONDrawer guard (single.tsx) reads body[data-dev-mode] — default is '0'."""
    response = client.get("/")
    assert 'data-dev-mode="0"' in response.text


def test_dev_mode_on_when_settings_enabled(dev_client: TestClient) -> None:
    """When DEV_MODE=1, the body attribute lets the React island render the
    RawJSONDrawer (D-019, FR-508). Single + batch shells both honour it."""
    single = dev_client.get("/")
    assert 'data-dev-mode="1"' in single.text
    batch = dev_client.get("/batch/abc-123")
    assert 'data-dev-mode="1"' in batch.text


def test_uswds_skip_link_present(client: TestClient) -> None:
    """NFR-A11Y-002 keyboard-operable end-to-end: the 'Skip to main content'
    link must be the first focusable element on every page."""
    response = client.get("/")
    assert 'class="skip-link"' in response.text
    assert "Skip to main content" in response.text
