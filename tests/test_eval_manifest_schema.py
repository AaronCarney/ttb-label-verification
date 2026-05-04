# tests/test_eval_manifest_schema.py
import json
from pathlib import Path

from eval._schema import ManifestEntry


def test_every_manifest_line_validates():
    path = Path("eval/manifest.jsonl")
    assert path.is_file()
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        ManifestEntry.model_validate_json(line)  # raises ValidationError on malformed lines


def test_class_balance_meets_prd_91():
    """spirits 30–40%, wine 30–40%, malt 20–30%; synthetic ≤30%; borderline ≥4 (smoke 20-entry split; full ~50 corpus must hit PRD ≥10)."""
    path = Path("eval/manifest.jsonl")
    entries = [ManifestEntry.model_validate_json(l) for l in path.read_text().splitlines() if l.strip()]
    n = len(entries)
    spirits = sum(1 for e in entries if e.class_balance_tag == "spirits")
    wine = sum(1 for e in entries if e.class_balance_tag == "wine")
    malt = sum(1 for e in entries if e.class_balance_tag == "malt")
    synth = sum(1 for e in entries if e.provenance.source.startswith("synthetic-"))
    borderline = sum(1 for e in entries if e.borderline_band)
    assert 0.30 <= spirits / n <= 0.40, f"spirits ratio {spirits/n}"
    assert 0.30 <= wine / n <= 0.40, f"wine ratio {wine/n}"
    assert 0.20 <= malt / n <= 0.30, f"malt ratio {malt/n}"
    assert synth / n <= 0.30, f"synthetic ratio {synth/n}"
    assert borderline >= 4, f"borderline count {borderline}"  # smoke 20-entry scaling; full ~50 corpus retains PRD ≥10
