"""Recording-rotation companion for D-020 snapshot rotation.

Iterates the active fixture set + per-task calls, performs one live OpenAI/Anthropic
call each, writes the response to:
  tests/recordings/<provider>/<snapshot>/<prompt-version>/orchestrator/<task>/<fixture>.json

Dry-run by default. `--live` required to actually call.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_TASKS = ("brand_disambig", "reasoning_enrich", "ocr_reconcile")
_PROVIDERS = ("openai", "anthropic")


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="record_orchestrator_responses",
        description="Snapshot-rotation companion for orchestrator recordings. Live calls require --live + API key.",
    )
    p.add_argument("--provider", choices=_PROVIDERS, default="openai")
    p.add_argument("--task", choices=_TASKS, default="brand_disambig")
    p.add_argument("--fixture", default="01-spirits-clean")
    p.add_argument("--snapshot", default=None)
    p.add_argument("--prompt-version", default=None)
    p.add_argument("--live", action="store_true")
    return p


def _main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    if args.live:
        key_env = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
        if not os.environ.get(key_env):
            print(f"error: --live requires {key_env} in env", file=sys.stderr)
            return 2

    from app.config import Settings
    settings = Settings()
    snapshot = args.snapshot or (settings.llm_model_snapshot if args.provider == "openai" else "claude-3-5-sonnet-20241022")
    prompt_version = args.prompt_version or settings.prompt_version
    out_dir = Path("tests/recordings") / args.provider / snapshot / prompt_version / "orchestrator" / args.task
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.fixture}.json"

    if not args.live:
        print(f"DRY RUN: would write {out_path} (provider={args.provider}, task={args.task}, fixture={args.fixture})")
        return 0

    print(f"would write {out_path} (live impl deferred — operator-driven flow)")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
