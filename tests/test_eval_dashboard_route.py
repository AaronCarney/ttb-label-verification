# tests/test_eval_dashboard_route.py
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client(dev_mode: bool) -> TestClient:
    # Construct Settings explicitly and pass to the create_app factory — avoids
    # importlib.reload + os.environ mutation, both of which leak into sibling
    # tests via the module-level `app: FastAPI = create_app()` at the bottom of
    # app/main.py.
    return TestClient(create_app(settings=Settings(dev_mode=dev_mode)))


def test_eval_route_404_when_dev_mode_off():
    client = _client(dev_mode=False)
    r = client.get("/eval")
    assert r.status_code == 404


def test_eval_route_200_when_dev_mode_on():
    client = _client(dev_mode=True)
    r = client.get("/eval")
    assert r.status_code == 200
    assert "TTB Label Verification" in r.text
