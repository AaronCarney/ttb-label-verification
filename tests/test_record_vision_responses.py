"""Smoke tests for the recording-rotation companion script.

Covers:
- import-cleanliness (script doesn't crash on import)
- --help exit code
- --live without OPENAI_API_KEY exits 2 with clear stderr message

This test does NOT call the live OpenAI API.
"""
from __future__ import annotations

import os
import subprocess
import sys


def test_script_imports_cleanly():
    """Script must be importable without OPENAI_API_KEY in env."""
    result = subprocess.run(
        [sys.executable, "-c", "import scripts.record_vision_responses"],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "scripts/record_vision_responses.py", "--help"],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert b"--live" in result.stdout


def test_live_without_api_key_exits_2():
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    result = subprocess.run(
        [
            sys.executable,
            "scripts/record_vision_responses.py",
            "--live",
            "--fixture",
            "01-spirits-clean",
        ],
        capture_output=True,
        timeout=10,
        env=env,
    )
    assert result.returncode == 2
    assert b"OPENAI_API_KEY" in result.stderr
