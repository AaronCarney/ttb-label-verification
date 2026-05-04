import os
import subprocess
import sys


def test_script_imports_cleanly():
    result = subprocess.run(
        [sys.executable, "-c", "import scripts.record_orchestrator_responses"],
        capture_output=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "scripts/record_orchestrator_responses.py", "--help"],
        capture_output=True, timeout=10,
    )
    assert result.returncode == 0
    assert b"--live" in result.stdout


def test_live_without_api_key_exits_2():
    env = {k: v for k, v in os.environ.items() if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")}
    result = subprocess.run(
        [sys.executable, "scripts/record_orchestrator_responses.py",
         "--live", "--provider", "openai", "--task", "brand_disambig", "--fixture", "01-spirits-clean"],
        capture_output=True, timeout=10, env=env,
    )
    assert result.returncode == 2
    assert b"OPENAI_API_KEY" in result.stderr
