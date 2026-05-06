"""Bulk-pull all class-141 bourbon labels from TTB Public COLA Registry.

Reads the ID list from fixtures/_corpus/_ids_class141_remaining.txt, pulls each
label via pull_cola_registry, commits in batches of N so progress is durable
even on long runs. Skips IDs whose cola-{ttbid}/label.jpg already exists.

Logs all per-ID results to fixtures/_corpus/_pull_log.jsonl (append mode).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pull_cola_registry import pull_one  # noqa: E402

REPO_ROOT = Path("/home/context/olorin/projects/takehome-e8backend")
CORPUS_ROOT = REPO_ROOT / "fixtures" / "_corpus"
LOG_PATH = CORPUS_ROOT / "_pull_log.jsonl"


def log_result(result: dict) -> None:
    with LOG_PATH.open("a") as f:
        f.write(json.dumps({**result, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, check=True
    )
    return proc.stdout


def commit_batch(batch_idx: int, count: int, total: int) -> None:
    git("add", "fixtures/_corpus/")
    status = git("status", "--porcelain")
    if not status.strip():
        print(f"[batch {batch_idx}] nothing staged — skip commit", flush=True)
        return
    msg = (
        f"feat(corpus): pull batch {batch_idx} ({count} bourbon labels) "
        f"from TTB Public COLA Registry (CC0)\n\n"
        f"Cumulative progress: {total} of 1524 class-141 BOURBON WHISKY records.\n"
        f"Source: TTB Public COLA Registry (data.gov 015-TTB-54, CC0).\n"
        f"All images real-source per D-025 / no-synthetic memory rule."
    )
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "commit", "-m", msg],
        check=True,
    )
    head = git("log", "--oneline", "-1").strip()
    print(f"[batch {batch_idx}] committed: {head}", flush=True)


def already_pulled(ttbid: str) -> bool:
    return (CORPUS_ROOT / f"cola-{ttbid}" / "label.jpg").exists()


def main(ids_file: Path, batch_size: int, sleep_sec: float) -> None:
    ids = [line.strip() for line in ids_file.read_text().splitlines() if line.strip()]
    print(f"loaded {len(ids)} IDs from {ids_file}", flush=True)

    pending = [t for t in ids if not already_pulled(t)]
    skipped = len(ids) - len(pending)
    print(f"{skipped} already pulled — {len(pending)} to fetch", flush=True)

    batch_idx = 0
    in_batch = 0
    cumulative = skipped

    started = time.time()
    for i, ttbid in enumerate(pending, start=1):
        try:
            r = pull_one(ttbid)
        except Exception as e:
            r = {"ttbid": ttbid, "ok": False, "err": str(e)}
            print(f"  ERROR: {e}", flush=True)
        log_result(r)
        if r.get("ok"):
            in_batch += 1
            cumulative += 1
        if i % 25 == 0:
            elapsed = time.time() - started
            rate = i / max(elapsed, 1)
            eta_sec = (len(pending) - i) / max(rate, 0.01)
            print(
                f"\n--- progress: {i}/{len(pending)} done "
                f"({cumulative}/{len(ids)} cumulative); "
                f"rate={rate:.2f}/s; ETA {eta_sec/60:.1f}min ---\n",
                flush=True,
            )
        if in_batch >= batch_size:
            batch_idx += 1
            commit_batch(batch_idx, in_batch, cumulative)
            in_batch = 0
        time.sleep(sleep_sec)

    # Final partial batch
    if in_batch > 0:
        batch_idx += 1
        commit_batch(batch_idx, in_batch, cumulative)

    print(f"\n=== DONE === {cumulative}/{len(ids)} total pulled across {batch_idx} commits", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ids-file", default=str(CORPUS_ROOT / "_ids_class141_remaining.txt"))
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--sleep-sec", type=float, default=1.5)
    args = p.parse_args()
    main(Path(args.ids_file), args.batch_size, args.sleep_sec)
