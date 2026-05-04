"""Pre-generate per-fixture demo envelopes for the deployed UI.

Runs the live cloud-vision evaluator against each single-label fixture
(FIX-01..04, 06, 07) and writes the resulting `DispositionEnvelope` to
``demo/sample-envelope-NN.json``. The shell route at ``GET /?fixture=NN``
reads these files at request time so a grader can click prev/next without
the Space ever calling OpenAI/etc.

Usage:
    OPENAI_API_KEY=... uv run --python 3.12 python scripts/build_demo_envelopes.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eval.harness import (
    _build_application_from_entry,
    _build_label_from_entry,
    _get_evaluator,
    _load_manifest,
)


SINGLE_LABEL_IDS = {
    "01": "FIX-01-SPIRITS-CLEAN",
    "02": "FIX-02-STONES-THROW",
    "03": "FIX-03-WARNING-TITLE-CASE",
    "04": "FIX-04-LOW-RES-BLURRY",
    "06": "FIX-06-ABV-OUT-OF-TOLERANCE",
    "07": "FIX-07-BORDERLINE-CONFIDENCE",
}


async def _evaluate(entry):
    evaluator = _get_evaluator()
    application = _build_application_from_entry(entry)
    label = _build_label_from_entry(entry)
    return await evaluator.evaluate(application, label)


async def _run(out_dir: Path, by_id: dict) -> None:
    """Single event loop drives every evaluation so the singleton evaluator's
    httpx client stays bound to one loop. Per-fixture asyncio.run() closed
    the loop after the first call and broke subsequent vision requests."""
    for slug, label_id in SINGLE_LABEL_IDS.items():
        entry = by_id.get(label_id)
        if entry is None:
            print(f"  skip {slug}: {label_id} not in manifest", file=sys.stderr)
            continue
        print(f"  evaluating {slug} ({label_id})...", flush=True)
        envelope = await _evaluate(entry)
        path = out_dir / f"sample-envelope-{slug}.json"
        path.write_text(envelope.model_dump_json(indent=2))
        print(f"  -> {path.relative_to(REPO_ROOT)} ({path.stat().st_size} bytes, "
              f"disposition={envelope.disposition})")


def main() -> int:
    manifest = _load_manifest(REPO_ROOT / "eval" / "manifest.jsonl")
    by_id = {e.label_id: e for e in manifest}
    out_dir = REPO_ROOT / "demo"
    out_dir.mkdir(exist_ok=True)
    asyncio.run(_run(out_dir, by_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
