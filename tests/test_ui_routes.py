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


# ---------------------------------------------------------------------------
# Single-label upload widget — POST /
# ---------------------------------------------------------------------------

def test_upload_form_present_on_root(client: TestClient) -> None:
    """The grader needs an in-page upload affordance — a multipart POST form
    targeting `/` with a file input named `label`."""
    response = client.get("/")
    assert 'enctype="multipart/form-data"' in response.text
    assert 'name="label"' in response.text
    assert 'method="post"' in response.text or 'method="POST"' in response.text


def test_upload_with_real_image_returns_envelope() -> None:
    """A multipart POST to / with a PNG runs the evaluator and re-renders the
    shell with the live envelope. Uses dependency override to swap the
    real evaluator for a stub so the test never calls OpenAI."""
    from app.api.ui import _get_upload_evaluator
    from tests._fakes.evaluator import FakeEvaluator
    from tests.conftest import _stub_disposition_envelope

    app = create_app()
    env = _stub_disposition_envelope(99, disposition="pass")
    fake = FakeEvaluator([(0.0, env)])
    app.dependency_overrides[_get_upload_evaluator] = lambda: fake
    client = TestClient(app)

    # Tiny valid PNG (1x1 black pixel).
    png_1x1 = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "89000000017352474200aece1ce90000000d4944415478da636060606000000005"
        "0001a5f645400000000049454e44ae426082"
    )
    response = client.post(
        "/",
        files={"label": ("upload.png", png_1x1, "image/png")},
    )
    assert response.status_code == 200, response.text
    assert "EV-0099" in response.text  # evaluation_id from stub envelope
    assert "lbl-0099" in response.text  # label_ref


def test_upload_with_invalid_mime_renders_error() -> None:
    """An obviously-not-an-image upload should re-render the page with an
    inline error banner rather than 500ing or showing a stack trace."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/",
        files={"label": ("not_an_image.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.text.lower() or "png" in response.text.lower()


def test_upload_without_file_returns_422() -> None:
    """FastAPI's File(...) requirement should produce a 422 when missing."""
    app = create_app()
    client = TestClient(app)
    response = client.post("/", files={})
    assert response.status_code == 422
