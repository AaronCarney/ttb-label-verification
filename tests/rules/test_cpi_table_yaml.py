"""§16.22(a)(4) cpi table is normative — three rows, no interpolation. The
S5-output §a notes block forbids interpolating between rows; the YAML must
declare interpolation: none.
"""
from __future__ import annotations

from pathlib import Path

import yaml

CPI = Path("rules/tables/cpi_16_22_a_4.yaml")


def test_table_parses() -> None:
    data = yaml.safe_load(CPI.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data["interpolation"] == "none"


def test_table_has_three_rows() -> None:
    data = yaml.safe_load(CPI.read_text(encoding="utf-8"))
    assert len(data["entries"]) == 3


def test_table_rows_well_formed() -> None:
    data = yaml.safe_load(CPI.read_text(encoding="utf-8"))
    for row in data["entries"]:
        assert "min_required_type_height_mm" in row
        assert "max_characters_per_inch" in row
        assert isinstance(row["max_characters_per_inch"], int)
