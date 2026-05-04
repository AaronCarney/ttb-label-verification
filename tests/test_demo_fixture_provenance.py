"""Each single-label fixture must have label, expected.json (parses as
ExpectedValue tuple), and notes.md."""
import json
from pathlib import Path

import pytest

from app.schemas.expected import ExpectedValue
from app.schemas.wire.batch import BatchEnvelope

SINGLE_LABEL_FIXTURES = ["01-spirits-clean", "02-bourbon-stones-throw",
                          "03-warning-title-case", "04-low-res-blurry",
                          "06-abv-out-of-tolerance", "07-borderline-confidence"]

BATCH_FIXTURE_05 = Path("fixtures/05-batch-of-50")
BATCH_FIXTURE_05_LABEL_COUNT = 50


@pytest.mark.parametrize("fid", SINGLE_LABEL_FIXTURES)
def test_fixture_has_required_files(fid):
    base = Path("fixtures") / fid
    assert (base / "notes.md").is_file(), f"{fid} missing notes.md"
    label = list(base.glob("label.*"))
    assert label, f"{fid} missing label.{{png,jpg}}"


@pytest.mark.parametrize("fid", SINGLE_LABEL_FIXTURES)
def test_expected_json_parses_as_expected_value_tuple(fid):
    """Every expected.json must be a list of dicts that parse as ExpectedValue."""
    sidecar = Path("fixtures") / fid / "expected.json"
    assert sidecar.is_file(), f"{fid} missing expected.json"
    raw = json.loads(sidecar.read_text())
    assert isinstance(raw, list), f"{fid}: expected.json must be a JSON array"
    for entry in raw:
        ExpectedValue(**entry)  # raises if shape is wrong


def test_borderline_fixture_07_has_borderline_band_marker():
    """Fixture-07 notes.md must document its FR-704 borderline-band purpose."""
    notes = (Path("fixtures") / "07-borderline-confidence" / "notes.md").read_text()
    assert "FR-704" in notes
    assert "borderline" in notes.lower()


def test_fixture_05_batch_has_required_files():
    """Fixture-05 carries 50 labels + a batch envelope + per-label expected
    blocks + notes.md (provenance). Drives E8 T15 batch-leg AC coverage."""
    assert (BATCH_FIXTURE_05 / "notes.md").is_file(), "fixture-05 missing notes.md"
    assert (BATCH_FIXTURE_05 / "batch_envelope.json").is_file(), (
        "fixture-05 missing batch_envelope.json"
    )
    assert (BATCH_FIXTURE_05 / "expected.json").is_file(), (
        "fixture-05 missing expected.json"
    )
    for i in range(1, BATCH_FIXTURE_05_LABEL_COUNT + 1):
        assert (BATCH_FIXTURE_05 / f"label_{i:03d}.png").is_file(), (
            f"fixture-05 missing label_{i:03d}.png"
        )


def test_fixture_05_batch_envelope_parses():
    """The committed envelope must round-trip through BatchEnvelope and
    reference exactly 50 labels."""
    raw = json.loads((BATCH_FIXTURE_05 / "batch_envelope.json").read_text())
    env = BatchEnvelope(**raw)
    assert len(env.items) == BATCH_FIXTURE_05_LABEL_COUNT, (
        f"fixture-05 envelope has {len(env.items)} items, expected 50"
    )


def test_fixture_05_expected_blocks_match_label_count():
    """expected.json is a list of 50 per-label ExpectedValue tuples."""
    raw = json.loads((BATCH_FIXTURE_05 / "expected.json").read_text())
    assert isinstance(raw, list)
    assert len(raw) == BATCH_FIXTURE_05_LABEL_COUNT, (
        f"fixture-05 expected.json has {len(raw)} entries, expected 50"
    )
    for block in raw:
        assert "label_ref" in block, "each block must carry label_ref"
        assert "expected_disposition" in block, "each block must carry expected_disposition"
        assert "expected_values" in block, "each block must carry expected_values"
        for entry in block["expected_values"]:
            ExpectedValue(**entry)


def test_fixture_05_distribution_forces_anomaly_and_override():
    """Distribution: 30 pass, 10 abv-fail (M-of-N anomaly cluster),
    5 warning-fail, 5 needs_review. >=3 same-reason failures forces
    anomaly advisory; >=1 fail enables override path."""
    raw = json.loads((BATCH_FIXTURE_05 / "expected.json").read_text())
    by_disp: dict[str, int] = {}
    for block in raw:
        by_disp[block["expected_disposition"]] = by_disp.get(block["expected_disposition"], 0) + 1
    assert by_disp.get("pass", 0) == 30
    assert by_disp.get("fail", 0) == 15
    assert by_disp.get("needs_review", 0) == 5
    abv_failures = [b for b in raw if b.get("expected_reason_code") == "FR-400-abv-tolerance"]
    assert len(abv_failures) >= 3, (
        "M-of-N anomaly advisory needs >=3 same-reason failures"
    )
