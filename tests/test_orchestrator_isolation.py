"""Inference-dep isolation:
- `openai` may be imported only under app/vision/ (E3) and app/orchestrator/ (E4).
- `anthropic` may be imported only under app/orchestrator/ (E4).
- `vllm`/`xgrammar` must not be imported anywhere (D-021).

Mirrors E3-T19's app/vision/ isolation invariant for the orchestrator direction.
"""
from pathlib import Path
import re


_OPENAI_PATTERNS = (
    re.compile(r"\bimport\s+openai\b"),
    re.compile(r"\bfrom\s+openai\b"),
)
_ANTHROPIC_PATTERNS = (
    re.compile(r"\bimport\s+anthropic\b"),
    re.compile(r"\bfrom\s+anthropic\b"),
)
_FORBIDDEN_PATTERNS = (
    re.compile(r"\bimport\s+vllm\b"),
    re.compile(r"\bfrom\s+vllm\b"),
    re.compile(r"\bimport\s+xgrammar\b"),
    re.compile(r"\bfrom\s+xgrammar\b"),
)


def test_openai_imports_only_under_vision_or_orchestrator():
    violations: list[str] = []
    for py in Path("app").rglob("*.py"):
        path_str = str(py)
        if "app/vision/" in path_str or "app/orchestrator/" in path_str:
            continue
        text = py.read_text()
        for rx in _OPENAI_PATTERNS:
            for m in rx.finditer(text):
                violations.append(f"{py}: {m.group(0)}")
    assert not violations, "openai imports leaked outside app/vision/ + app/orchestrator/:\n" + "\n".join(violations)


def test_anthropic_imports_only_under_orchestrator():
    violations: list[str] = []
    for py in Path("app").rglob("*.py"):
        if "app/orchestrator/" in str(py):
            continue
        text = py.read_text()
        for rx in _ANTHROPIC_PATTERNS:
            for m in rx.finditer(text):
                violations.append(f"{py}: {m.group(0)}")
    assert not violations, "anthropic imports leaked outside app/orchestrator/:\n" + "\n".join(violations)


def test_d021_forbidden_imports_absent():
    violations: list[str] = []
    for py in Path("app").rglob("*.py"):
        text = py.read_text()
        for rx in _FORBIDDEN_PATTERNS:
            for m in rx.finditer(text):
                violations.append(f"{py}: {m.group(0)}")
    assert not violations, "D-021 forbidden imports detected:\n" + "\n".join(violations)


def test_authorization_header_sanitizer_redacts():
    """Sanitizer (in conftest.py) replaces Authorization headers with REDACTED."""
    from tests.conftest import _redact_authorization_headers
    payload = {"headers": {"Authorization": "Bearer sk-secret-12345", "Content-Type": "application/json"}}
    sanitized = _redact_authorization_headers(payload)
    assert sanitized["headers"]["Authorization"] == "REDACTED"
    assert sanitized["headers"]["Content-Type"] == "application/json"  # unchanged
