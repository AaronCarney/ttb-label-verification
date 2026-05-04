"""Each single-label fixture must have label, expected.json (parses as
ExpectedValue tuple), and notes.md."""
import json
from pathlib import Path

import pytest

from app.schemas.expected import ExpectedValue

SINGLE_LABEL_FIXTURES = ["01-spirits-clean", "02-bourbon-stones-throw",
                          "03-warning-title-case", "04-low-res-blurry",
                          "06-abv-out-of-tolerance", "07-borderline-confidence"]


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
