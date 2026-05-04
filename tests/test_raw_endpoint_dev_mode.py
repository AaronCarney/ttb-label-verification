"""GET /batches/.../calls — DEV_MODE-gated per ADR D-019."""
from fastapi.testclient import TestClient

from app.main import app


def test_raw_endpoint_404_when_dev_mode_off(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "false")
    client = TestClient(app)
    response = client.get("/batches/B-001/labels/L-001/calls")
    assert response.status_code == 404


def test_raw_endpoint_200_when_dev_mode_on(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    client = TestClient(app)
    response = client.get("/batches/B-001/labels/L-001/calls")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
