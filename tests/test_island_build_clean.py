"""T33: R-5 mitigation — committed island bundle matches frontend sources."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_pnpm_build_produces_clean_diff(pnpm_built_island: Path) -> None:
    """The session-scoped `pnpm_built_island` fixture (defined in T7's
    conftest.py) runs `pnpm install --frozen-lockfile && pnpm build` once
    per session; this test just verifies that `git diff` against the
    committed bundle is empty after that build. Reusing the fixture avoids
    a second `pnpm install + pnpm build` invocation per session.
    """
    result = subprocess.run(
        ["git", "diff", "--exit-code", str(pnpm_built_island)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"app/ui/static/island/ diverges from frontend sources after pnpm build:\n{result.stdout}"
    )
