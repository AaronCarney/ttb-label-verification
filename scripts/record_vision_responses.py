"""Recording-rotation companion (D-020 snapshot rotation).

Iterates the active fixture set and per-field calls, performs one live OpenAI
call each, and writes the response JSON to:
  tests/recordings/openai/<active-snapshot>/<prompt-version>/<fixture-id>/<call-name>.json

Dry-run by default (no live calls). `--live` required to actually call OpenAI.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


CALL_NAMES = (
    "layout",
    "brand_name",
    "class_type",
    "abv",
    "net_contents",
    "gov_warning",
    "heading_typography",
    "name_address",
    "country_origin",
)


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="record_vision_responses",
        description=(
            "Snapshot-rotation companion. "
            "Live calls require --live + OPENAI_API_KEY."
        ),
    )
    p.add_argument(
        "--fixture",
        default="01-spirits-clean",
        help="Fixture id under fixtures/<id>/label.png",
    )
    p.add_argument(
        "--snapshot",
        default=None,
        help="LLM_MODEL_SNAPSHOT; defaults to settings.llm_model_snapshot",
    )
    p.add_argument(
        "--prompt-version",
        default=None,
        help="PROMPT_VERSION; defaults to settings.prompt_version",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Actually call OpenAI. Requires OPENAI_API_KEY.",
    )
    return p


def _main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    if args.live and not os.environ.get("OPENAI_API_KEY"):
        print("error: --live requires OPENAI_API_KEY in env", file=sys.stderr)
        return 2

    if not args.live:
        print(
            f"DRY RUN: would record {len(CALL_NAMES)} calls "
            f"for fixture {args.fixture}"
        )
        return 0

    from app.config import Settings

    settings = Settings()
    snapshot = args.snapshot or settings.llm_model_snapshot
    prompt_version = args.prompt_version or settings.prompt_version

    fixture_path = Path("fixtures") / args.fixture / "label.png"
    if not fixture_path.exists():
        print(f"error: fixture not found: {fixture_path}", file=sys.stderr)
        return 2

    out_dir = (
        Path("tests/recordings/openai") / snapshot / prompt_version / args.fixture
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"would write {len(CALL_NAMES)} recordings to {out_dir} "
        "(live impl deferred)"
    )
    # Real impl iterates CALL_NAMES, makes live OpenAI calls via httpx
    # (mirroring T9/T10), writes each response to out_dir/<call_name>.json.
    # Deferred until first D-020 snapshot rotation — operator-driven flow.
    return 0


if __name__ == "__main__":
    sys.exit(_main())
