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


def test_default_serves_fixture_01(client: TestClient) -> None:
    """Bare `/` defaults to fixture 01 so a cold-loaded reviewer sees a
    populated envelope rather than the placeholder."""
    response = client.get("/")
    assert response.status_code == 200
    assert "FIX-01-SPIRITS-CLEAN" in response.text


def test_fixture_picker_serves_specific_fixture(client: TestClient) -> None:
    """`?fixture=NN` swaps the embedded envelope so a grader can step
    through the demo set without uploading anything."""
    response = client.get("/?fixture=02")
    assert response.status_code == 200
    assert "FIX-02-STONES-THROW" in response.text


def test_fixture_picker_unknown_falls_back(client: TestClient) -> None:
    """An unknown fixture id renders fixture 01 (the default) rather than 404
    so a hand-edited URL still produces a usable page."""
    response = client.get("/?fixture=99")
    assert response.status_code == 200
    assert "FIX-01-SPIRITS-CLEAN" in response.text


def test_fixture_picker_prev_next_links(client: TestClient) -> None:
    """Server-rendered prev/next links let a grader navigate the demo set
    without JS. Sequence wraps: 07 -> 01 -> 02 -> 03 -> 04 -> 06 -> 07."""
    response = client.get("/?fixture=02")
    assert "?fixture=01" in response.text
    assert "?fixture=03" in response.text


def test_fixture_picker_wraps_around(client: TestClient) -> None:
    """First fixture's prev wraps to last; last fixture's next wraps to first."""
    first = client.get("/?fixture=01")
    assert "?fixture=07" in first.text  # prev wraps
    last = client.get("/?fixture=07")
    assert "?fixture=01" in last.text  # next wraps


def test_fixture_picker_all_fixtures_respond(client: TestClient) -> None:
    """Every shipped demo envelope must be reachable via the picker."""
    for slug, label_id in [
        ("01", "FIX-01-SPIRITS-CLEAN"),
        ("02", "FIX-02-STONES-THROW"),
        ("03", "FIX-03-WARNING-TITLE-CASE"),
        ("04", "FIX-04-LOW-RES-BLURRY"),
        ("06", "FIX-06-ABV-OUT-OF-TOLERANCE"),
        ("07", "FIX-07-BORDERLINE-CONFIDENCE"),
    ]:
        response = client.get(f"/?fixture={slug}")
        assert response.status_code == 200, f"fixture {slug} not 200"
        assert label_id in response.text, f"fixture {slug} missing label_ref"
