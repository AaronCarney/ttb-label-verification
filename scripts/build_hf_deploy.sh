#!/usr/bin/env bash
# Rebuild the hf-deploy orphan branch from main and push it as hf:main.
#
# Why orphan: HF Space's pre-receive hook rejects pre-Xet binary blobs in any
# part of a push's commit lineage, not just the tip. So the deploy branch
# can't share history with main (which carries the full 1524-label corpus).
# This script throws away history every time and ships a single-commit
# snapshot containing just what the running container needs.
#
# Allowlist (explicitly staged):
#   app/, rules/, assets/, demo/, eval/, fixtures/01-..07-/, fixtures/_corpus/_active.txt,
#   Dockerfile, .dockerignore, .gitignore, pyproject.toml, uv.lock, README.md
#
# Notably excluded:
#   fixtures/_corpus/cola-*/      (binaries — fetched from GitHub raw at runtime)
#   fixtures/_corpus/_search-*    (operational artifacts)
#   fixtures/_corpus/_ids_*       (operational artifacts)
#   fixtures/_corpus/_pull_log    (operational artifacts)
#   scripts/, tests/, docs/, configs/, .env.example, docker-compose.yml
#
# Usage:  ./scripts/build_hf_deploy.sh [--no-push]
#         --no-push   build the local orphan branch but don't force-push it
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

PUSH=1
case "${1:-}" in
    --no-push) PUSH=0 ;;
    "") ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
esac

# Pre-flight: working tree must be clean. The orphan-branch dance fails
# loudly when there's uncommitted work, so block it up front with a clear
# message instead of mid-flight.
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "ERROR: working tree has uncommitted changes. Commit or stash first." >&2
    git status --short
    exit 1
fi

# Remember where to return after the dance.
ORIGINAL_BRANCH="$(git symbolic-ref --short HEAD)"
SOURCE_REF="${SOURCE_REF:-main}"
SOURCE_SHA="$(git rev-parse "$SOURCE_REF")"

echo "→ snapshotting from $SOURCE_REF @ ${SOURCE_SHA:0:7}"

# Stage the working tree at SOURCE_REF so the orphan commit reflects that
# canonical state, regardless of which branch we started on.
git checkout -f "$SOURCE_REF" -- .

# Drop and recreate the orphan branch.
git branch -D hf-deploy 2>/dev/null || true
git checkout --orphan hf-deploy >/dev/null
git rm -rf --quiet --cached . >/dev/null 2>&1 || true

# Allowlisted top-level entries.
APP_PATHS=(
    app rules assets demo eval
    Dockerfile .dockerignore .gitignore
    pyproject.toml uv.lock README.md
)
for p in "${APP_PATHS[@]}"; do
    if [[ -e "$p" ]]; then
        git add "$p"
    else
        echo "  WARN: $p not found in working tree" >&2
    fi
done

# Small-fixture demo dirs (FIX-01..FIX-07). These ship to HF because they're
# tiny PNGs that pre-date the binary policy enforcement.
for d in fixtures/0[1-9]-* fixtures/1[0-9]-*; do
    [[ -d "$d" ]] && git add "$d"
done

# The 150-entry active list. The endpoint reads this to know which labels
# to fetch from GitHub raw at request time.
if [[ -f fixtures/_corpus/_active.txt ]]; then
    git add fixtures/_corpus/_active.txt
else
    echo "ERROR: fixtures/_corpus/_active.txt missing — sample-zip endpoint can't run without it" >&2
    git checkout -f "$ORIGINAL_BRANCH"
    git branch -D hf-deploy
    exit 1
fi

# Hard guard: no cola-*/label.jpg may be staged.
if git ls-files --cached | grep -qE '^fixtures/_corpus/cola-.*\.(jpg|jpeg|png)$'; then
    echo "ERROR: corpus binaries leaked into the staged set — HF will reject:" >&2
    git ls-files --cached | grep -E '^fixtures/_corpus/cola-.*\.(jpg|jpeg|png)$' | head -5 >&2
    git checkout -f "$ORIGINAL_BRANCH"
    git branch -D hf-deploy
    exit 1
fi

STAGED=$(git ls-files --cached | wc -l)
echo "→ $STAGED files staged for orphan commit"

git commit -m "deploy: HF Space snapshot from $SOURCE_REF @ ${SOURCE_SHA:0:7}

Single-commit orphan branch built by scripts/build_hf_deploy.sh.

Ships app + small synthetic fixtures + 150-entry _active.txt only. No
cola-*/label.jpg binaries (HF's pre-receive hook rejects pre-Xet
blobs). The sample-zip endpoint reads _active.txt and fetches binaries
from GitHub raw at request time when not on local disk.

Excluded: 1524 cola-*/ dirs, _search-*.jsonl, _ids_*.txt, _pull_log,
scripts/, tests/, docs/, configs/, .env.example, docker-compose.yml.
" >/dev/null

ORPHAN_SHA="$(git rev-parse HEAD)"
echo "→ orphan commit: ${ORPHAN_SHA:0:7}"

if (( PUSH )); then
    echo "→ force-pushing hf-deploy → hf:main"
    git push hf hf-deploy:main --force
else
    echo "→ --no-push given; orphan branch built but not pushed"
fi

# Return to the original branch. -f because the orphan checkout left the
# working tree mirroring SOURCE_REF, which may differ from $ORIGINAL_BRANCH
# in untracked-but-present-on-disk files.
git checkout -f "$ORIGINAL_BRANCH" >/dev/null
echo "→ back on $ORIGINAL_BRANCH"
