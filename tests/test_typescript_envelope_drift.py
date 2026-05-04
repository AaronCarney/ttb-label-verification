"""T5: hand-mirrored TS envelope types track Pydantic schema field names.

This is a fast structural canary, not a full type-isomorphism check. If a
field is renamed in app/schemas/wire/*.py, this test surfaces the drift; the
fix is a one-line edit in frontend/src/types/envelopes.ts.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS_PATH = ROOT / "frontend" / "src" / "types" / "envelopes.ts"
PYDANTIC_FILES = [
    ROOT / "app" / "schemas" / "wire" / "disposition.py",
    ROOT / "app" / "schemas" / "wire" / "batch.py",
    ROOT / "app" / "schemas" / "audit.py",
    ROOT / "app" / "schemas" / "metrics.py",
]

# Fields whose names the TS file is required to contain. These are field
# IDENTIFIERS as written in Pydantic source (e.g. ``label_ref:``); the regex
# captures lines like ``    label_ref: str`` or ``    label_ref: Literal[...]``.
_FIELD_RE = re.compile(r"^\s{4}([a-z_][a-z0-9_]*):\s", re.MULTILINE)


def _pydantic_fields() -> set[str]:
    out: set[str] = set()
    for p in PYDANTIC_FILES:
        source = p.read_text()
        out |= set(_FIELD_RE.findall(source))
    return out


def test_typescript_envelopes_file_exists() -> None:
    assert TS_PATH.exists(), f"missing {TS_PATH}"


def test_typescript_envelopes_mirror_pydantic_fields() -> None:
    ts = TS_PATH.read_text()
    missing: list[str] = []
    for field in sorted(_pydantic_fields()):
        # Skip fields with names that conflict with TS reserved-word patterns
        # or are intentionally renamed (none today, but keep the hook).
        if field in {}:
            continue
        # The field name must appear at least once in the TS file (as a
        # property declaration or a comment hook).
        if field not in ts:
            missing.append(field)
    assert not missing, f"TypeScript envelope types missing fields: {missing}"
