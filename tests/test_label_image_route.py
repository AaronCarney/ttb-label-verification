"""Reviewer UI must display the label image. Two routes are required:

  GET /fixtures/{slug}/label.png  — returns the PNG bytes for the demo
                                     fixtures shipped under fixtures/.
  GET /labels/{eval_id}/image     — returns the bytes uploaded via
                                     POST /. Bytes are cached in-process
                                     keyed on the synthesized evaluation_id
                                     so a follow-up GET against the rendered
                                     page sees the same image.

Both routes return 404 for unknown ids; both set Content-Type: image/png
or image/jpeg.
"""
from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app


def _png_1x1() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (1, 1), color=(0, 0, 0)).save(buf, "PNG")
    return buf.getvalue()


def test_fixture_image_route_serves_png():
    client = TestClient(create_app())
    response = client.get("/fixtures/01/label.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_fixture_image_route_404_on_unknown_slug():
    client = TestClient(create_app())
    response = client.get("/fixtures/99/label.png")
    assert response.status_code == 404


def test_root_html_includes_image_for_fixture_mode():
    """`GET /?fixture=01` must surface an <img> pointing at the fixture
    image route so the reviewer can see what the engine read."""
    client = TestClient(create_app())
    response = client.get("/?fixture=01")
    assert response.status_code == 200
    assert "<img" in response.text
    assert "/fixtures/01/label.png" in response.text


def test_upload_image_round_trips():
    """An upload's bytes must be retrievable via /labels/{eval_id}/image
    so the rendered template can display them."""
    from app.api.ui import _get_upload_evaluator
    from tests._fakes.evaluator import FakeEvaluator
    from tests.conftest import _stub_disposition_envelope

    app = create_app()
    env = _stub_disposition_envelope(42, disposition="pass")
    fake = FakeEvaluator([(0.0, env)])
    app.dependency_overrides[_get_upload_evaluator] = lambda: fake
    client = TestClient(app)

    png = _png_1x1()
    response = client.post(
        "/", files={"label": ("upload.png", png, "image/png")}
    )
    assert response.status_code == 200
    # The shell must reference the image route by the synthesized eval id.
    assert f"/labels/{env.evaluation_id}/image" in response.text

    # The bytes round-trip — the cache lookup returns the exact upload.
    img = client.get(f"/labels/{env.evaluation_id}/image")
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
    assert img.content == png


def test_upload_image_404_on_unknown_eval_id():
    client = TestClient(create_app())
    response = client.get("/labels/no-such-id/image")
    assert response.status_code == 404
