# tests/test_eval_harness_cli.py
import subprocess
from pathlib import Path


def test_harness_module_invocable():
    """`python -m eval.harness --help` should print usage."""
    result = subprocess.run(
        ["python", "-m", "eval.harness", "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "--subset" in result.stdout
    assert "smoke" in result.stdout and "full" in result.stdout


def test_harness_writes_history_record(tmp_path, monkeypatch):
    """Smoke run with a fake evaluator writes a timestamped history JSON."""
    from eval.harness import run_subset
    from eval._schema import HistoryRecord

    history_dir = tmp_path / "history"
    history_dir.mkdir()

    # The harness accepts an injected evaluator for testability.
    def fake_evaluator(entry):
        return entry.expected_disposition, entry.expected_per_rule, 0.42, 0.88

    record = run_subset(subset="smoke", manifest_path=Path("eval/manifest.jsonl"),
                       history_dir=history_dir, evaluator=fake_evaluator)
    assert isinstance(record, HistoryRecord)
    assert record.subset == "smoke"
    assert record.macro_f1 == 1.0  # fake returns expected, so perfect
    # Timestamped record sits alongside summary.json (T6 dashboard reads the
    # directory and excludes summary.json by name — see eval/dashboard.py).
    record_files = [p for p in history_dir.glob("*.json") if p.name != "summary.json"]
    assert len(record_files) == 1
    assert (history_dir / "summary.json").is_file()
