"""GET /batches/sample.zip — downloadable sample batch from the active corpus.

Deployed-app demo affordance: a grader can pull a sample of real TTB Public
COLA Registry labels (CC0) and upload them through POST /batches/upload to
exercise the real worker pipeline (no simulation).
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def active_ids() -> list[str]:
    path = Path("fixtures/_corpus/_active.txt")
    return [l.strip() for l in path.read_text().splitlines() if l.strip()]


def test_sample_zip_default_returns_zip(client: TestClient) -> None:
    response = client.get("/batches/sample.zip")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "sample.zip" in response.headers["content-disposition"]


def test_sample_zip_default_count_is_ten(client: TestClient) -> None:
    response = client.get("/batches/sample.zip")
    z = zipfile.ZipFile(io.BytesIO(response.content))
    names = [n for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
    assert len(names) == 10


def test_sample_zip_n_param_controls_count(client: TestClient) -> None:
    response = client.get("/batches/sample.zip?n=5")
    z = zipfile.ZipFile(io.BytesIO(response.content))
    names = [n for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
    assert len(names) == 5


def test_sample_zip_n_capped_at_active_size(client: TestClient, active_ids: list[str]) -> None:
    """Asking for more than we have caps cleanly rather than 4xx."""
    response = client.get(f"/batches/sample.zip?n={len(active_ids) + 100}")
    assert response.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(response.content))
    names = [n for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
    assert len(names) == len(active_ids)


def test_sample_zip_n_zero_is_400(client: TestClient) -> None:
    response = client.get("/batches/sample.zip?n=0")
    assert response.status_code == 400


def test_sample_zip_entries_drawn_from_active_set(
    client: TestClient, active_ids: list[str]
) -> None:
    """Every zipped image's name must reference a ttbid in _active.txt — the
    pool labels are excluded from the deployed container per .dockerignore."""
    active_set = set(active_ids)
    response = client.get(f"/batches/sample.zip?n={len(active_ids)}")
    z = zipfile.ZipFile(io.BytesIO(response.content))
    for name in z.namelist():
        if not name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        # Filenames embed the ttbid: cola-{ttbid}-...jpg or similar
        assert any(tid in name for tid in active_set), f"{name!r} references unknown ttbid"


def test_sample_zip_entries_are_valid_images(client: TestClient) -> None:
    response = client.get("/batches/sample.zip?n=3")
    z = zipfile.ZipFile(io.BytesIO(response.content))
    image_names = [n for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png"))]
    assert image_names, "zip must contain images"
    for name in image_names:
        body = z.read(name)
        # JPEG magic
        assert body.startswith(b"\xff\xd8\xff") or body.startswith(b"\x89PNG"), (
            f"{name!r} is not a valid JPEG/PNG (first bytes {body[:4]!r})"
        )


def test_upload_page_links_to_sample_zip(client: TestClient) -> None:
    """The /batches upload form must surface the sample-zip download —
    otherwise a grader without their own labels can't try the bulk flow."""
    response = client.get("/batches")
    assert response.status_code == 200
    assert "/batches/sample.zip" in response.text
