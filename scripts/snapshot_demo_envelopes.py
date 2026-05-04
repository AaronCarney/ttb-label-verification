#!/usr/bin/env python3
"""Demo envelope snapshotter — regression baseline for fixture dispositions.

Modes:
  default (no flags):       For each fixture with both label and expected.json,
                            run `build_evaluator(settings).evaluate(...)` and write
                            the resulting DispositionEnvelope JSON to
                            demo/cached/<fid>/envelope.json (canonicalized,
                            sort_keys=True, indent=2, trailing newline).
  --canonicalize-only:      Read each existing envelope.json, parse against
                            DispositionEnvelope, write back canonicalized.
                            Used in CI to verify byte-identical idempotency.
  --root <path>:            Override demo/cached root (testing only).

Notes:
  - Live evaluator path requires OPENAI_API_KEY (or a mock orchestrator). The
    DEMO_CACHE=1 env-var integration with running app is deferred (see L1
    deviations).
  - Fixtures with empty expected.json (e.g. fixture-04) still produce a valid
    envelope (legibility short-circuit branch). All fixtures are runnable.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.schemas.wire.disposition import DispositionEnvelope

DEFAULT_FIXTURES = (
    "01-spirits-clean", "02-bourbon-stones-throw", "03-warning-title-case",
    "04-low-res-blurry", "06-abv-out-of-tolerance", "07-borderline-confidence",
)


def _canonical(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


async def _live_envelope(fixture_id: str) -> DispositionEnvelope:
    """Run the live evaluator for one fixture and return its envelope."""
    import json as _json

    from app.config import Settings
    from app.deps import build_evaluator
    from app.schemas.application import Application
    from app.schemas.expected import ExpectedValue
    from app.schemas.label import Label

    settings = Settings()
    evaluator = build_evaluator(settings)

    sidecar = Path("fixtures") / fixture_id / "expected.json"
    raw = _json.loads(sidecar.read_text()) if sidecar.is_file() else []
    expected = tuple(ExpectedValue(**e) for e in raw)

    img_png = Path("fixtures") / fixture_id / "label.png"
    img_jpg = Path("fixtures") / fixture_id / "label.jpg"
    if img_png.is_file():
        img, content_type = img_png, "image/png"
    elif img_jpg.is_file():
        img, content_type = img_jpg, "image/jpeg"
    else:
        raise SystemExit(f"[err] {fixture_id}: no label.png or .jpg")

    app = Application(application_id=f"A-{fixture_id}",
                      evaluation_id=f"EV-{fixture_id}",
                      expected_values=expected)
    label = Label(label_id=fixture_id, batch_id="snapshot",
                  image_bytes=img.read_bytes(), content_type=content_type,
                  face_tag="front", dimensions=None)
    return await evaluator.evaluate(application=app, label=label)


def canonicalize_only(root: Path, fixture_id: str) -> None:
    target = root / fixture_id / "envelope.json"
    if not target.is_file():
        print(f"[skip] {fixture_id}: no envelope.json (run without --canonicalize-only first)")
        return
    parsed = DispositionEnvelope.model_validate_json(target.read_text())
    canonical = _canonical(json.loads(parsed.model_dump_json()))
    target.write_text(canonical)
    print(f"[ok] {fixture_id}: canonicalized")


def snapshot_live(root: Path, fixture_id: str) -> None:
    target_dir = root / fixture_id
    target_dir.mkdir(parents=True, exist_ok=True)
    envelope = asyncio.run(_live_envelope(fixture_id))
    target = target_dir / "envelope.json"
    canonical = _canonical(json.loads(envelope.model_dump_json()))
    target.write_text(canonical)
    print(f"[ok] {fixture_id}: snapshot written ({target})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", nargs="+", default=list(DEFAULT_FIXTURES))
    parser.add_argument("--root", type=Path, default=Path("demo/cached"))
    parser.add_argument("--canonicalize-only", action="store_true",
                        help="Skip live evaluator; just re-canonicalize existing JSON")
    args = parser.parse_args()
    for fid in args.fixtures:
        if args.canonicalize_only:
            canonicalize_only(args.root, fid)
        else:
            snapshot_live(args.root, fid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
