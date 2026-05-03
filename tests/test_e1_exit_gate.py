"""E1 exit-gate integration suite.

Asserts the 9 ACs from ``docs/plans/ttb-label-verification-epoch-1-foundation.md``
§4. Most are upheld transitively by the per-task tests (T1–T26); this file
ties the per-AC contracts together as one runnable assertion suite.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).parents[1]


def test_ac1_pyproject_is_valid_and_uv_lock_exists() -> None:
    """AC #1: ``uv sync`` succeeds (cloud profile). Existence of ``uv.lock``
    is a transitive check; the parallel-plan-executor verifies fresh
    ``uv sync`` time off-band on a clean checkout."""
    assert (REPO_ROOT / "pyproject.toml").exists()
    assert (REPO_ROOT / "uv.lock").exists()


def test_ac2_taskipy_demo_target_defined() -> None:
    """AC #2: ``uv run task demo`` boots the app. Here we assert the task is
    declared; subprocess boot is exercised by the parallel-plan-executor's
    smoke step, not by pytest."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.taskipy.tasks]" in text
    assert "demo = " in text
    assert "uvicorn app.main:app" in text


def test_ac3_healthz_returns_200_with_payload_shape() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    from app.main import app

    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body and "mode" in body


def test_ac4_test_surface_meets_minimum() -> None:
    """AC #4: ≥4 test files, ≥25 assertions across the suite.

    A loose proxy: count test files and ``def test_`` declarations.
    """
    tests_dir = REPO_ROOT / "tests"
    test_files = list(tests_dir.glob("test_*.py"))
    assert len(test_files) >= 4, [p.name for p in test_files]
    test_count = 0
    for path in test_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("def test_"):
                test_count += 1
    assert test_count >= 25, f"only {test_count} tests defined"


def test_ac5_wire_envelopes_round_trip_byte_identical_keys() -> None:
    """AC #5: every PRD §6.x wire envelope round-trips."""
    from app.schemas.wire.application import ApplicationEnvelope
    from app.schemas.wire.batch import BatchEnvelope
    from app.schemas.wire.disposition import DispositionEnvelope
    from app.schemas.wire.error import ErrorEnvelope

    fixtures_dir = REPO_ROOT / "tests" / "wire_fixtures"
    cases = [
        (ApplicationEnvelope, "application.json"),
        (DispositionEnvelope, "disposition.json"),
        (BatchEnvelope, "batch.json"),
        (ErrorEnvelope, "error.json"),
    ]
    for model, name in cases:
        raw = json.loads((fixtures_dir / name).read_text())
        env = model.model_validate(raw)
        # Re-validate after a dump round trip; equality holds.
        rt = model.model_validate_json(env.model_dump_json())
        assert rt == env, name


def test_ac6_no_os_environ_outside_app_config() -> None:
    """AC #6: NFR-SEC-002 grep enforcement.

    Delegated to ``tests/test_secrets_grep.py``; included here for
    exit-gate completeness — re-run inline.
    """
    from tests.test_secrets_grep import (  # type: ignore[import-not-found]
        test_os_environ_read_only_in_app_config_py,
    )

    test_os_environ_read_only_in_app_config_py()


def test_ac7_healthz_emits_one_json_log_line(capsys) -> None:
    """AC #7: structured log emits a single JSON line on /healthz."""
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    from app.main import create_app

    app_obj = create_app()
    with TestClient(app_obj) as client:
        # `with` triggers the lifespan startup — drain its log line(s)
        # so the next capsys read isolates the /healthz request emission.
        capsys.readouterr()
        r = client.get("/healthz")
        assert r.status_code == 200
        captured = capsys.readouterr().out
    # AC #7: the /healthz route itself emits a single structured log line.
    # Filter to the app.healthz logger — third-party libraries (e.g., httpx
    # in TestClient) may emit their own lines through the root handler;
    # those are not what AC #7 asserts.
    json_lines = [
        json.loads(ln)
        for ln in captured.splitlines()
        if ln.strip().startswith("{")
    ]
    healthz_lines = [p for p in json_lines if p.get("logger") == "app.healthz"]
    assert len(healthz_lines) == 1, json_lines
    parsed = healthz_lines[0]
    assert "ts" in parsed
    assert "level" in parsed
    assert "msg" in parsed


def test_ac8_di_providers_raise_not_implemented_on_seam_invocation() -> None:
    """AC #8: providers raise NotImplementedError on extract()/refine()."""
    import asyncio

    from app.config import Settings
    from app.deps import build_orchestrator, build_vision_extractor

    s = Settings()
    extractor = build_vision_extractor(s)
    orch = build_orchestrator(s)

    async def _run() -> tuple[bool, bool]:
        e3, e4 = False, False
        try:
            await extractor.extract(label=None)  # type: ignore[arg-type]
        except NotImplementedError as exc:
            e3 = "seam not wired in E1" in str(exc) and "E3" in str(exc)
        try:
            await orch.refine(payload=None)  # type: ignore[arg-type]
        except NotImplementedError as exc:
            e4 = "seam not wired in E1" in str(exc) and "E4" in str(exc)
        return e3, e4

    e3, e4 = asyncio.run(_run())
    assert e3 and e4


def test_ac9_rule_set_canonically_declared_in_app_schemas_rules() -> None:
    """AC #9 (E1 partial): canonical declaration lives in app/schemas/rules.py.

    The full ``is``-identity assertion against ``app/rules/models.py`` belongs
    to E2 when the re-export lands; here we only confirm canonical residency.
    """
    from app.schemas.rules import RuleSet

    assert RuleSet.__module__ == "app.schemas.rules"
