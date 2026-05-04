"""Envelope snapshots in demo/cached/<fid>/envelope.json must parse as
DispositionEnvelope; canonicalization is idempotent on unchanged inputs.
"""
import json
import subprocess
from pathlib import Path

import pytest

from app.schemas.wire.disposition import DispositionEnvelope


def test_committed_snapshots_parse_as_disposition_envelope():
    """Any envelope.json committed under demo/cached/ must validate."""
    root = Path("demo/cached")
    if not root.is_dir():
        pytest.skip("demo/cached not yet populated")
    for env_path in root.glob("*/envelope.json"):
        DispositionEnvelope.model_validate_json(env_path.read_text())


def test_canonicalization_idempotent_on_unchanged_snapshot(tmp_path):
    """Re-canonicalizing an existing snapshot produces byte-identical output."""
    target = tmp_path / "demo" / "cached" / "01-spirits-clean"
    target.mkdir(parents=True)
    # Seed a minimal valid envelope JSON for round-trip test.
    seed = {
        "evaluation_id": "EV-test",
        "label_ref": "01-spirits-clean",
        "disposition": "needs_review",
        "disposition_confidence": {"band": "low", "numeric": 0.5},
        "fields": [],
        "audit_trail": {
            "evaluation_id": "EV-test",
            "rule_set_version": "0.1.0",
            "input_hash": "abc",
            "output_hash": "def",
            "started_at": "2026-05-04T00:00:00+00:00",
            "completed_at": "2026-05-04T00:00:01+00:00",
            "per_rule_trace": [],
            "overrides": [],
        },
        "metrics": {
            "total_duration_ms": 1,
            "per_rule_durations_ms": [],
            "vision_duration_ms": 0,
            "orchestrator_duration_ms": 0,
        },
    }
    (target / "envelope.json").write_text(
        json.dumps(seed, indent=2, sort_keys=True) + "\n"
    )
    # Run snapshotter in --canonicalize-only mode against tmp_path.
    cmd = ["python", "scripts/snapshot_demo_envelopes.py",
           "--root", str(tmp_path / "demo" / "cached"),
           "--fixtures", "01-spirits-clean",
           "--canonicalize-only"]
    subprocess.run(cmd, check=True)
    first = (target / "envelope.json").read_bytes()
    subprocess.run(cmd, check=True)
    second = (target / "envelope.json").read_bytes()
    assert first == second
