"""NFR-SEC-002 enforcement: ``os.environ`` is read by ``app/config.py`` ONLY.

L1 §4 AC #6: ``grep -rn 'os.environ' app/ | grep -v 'config.py'`` returns no hits.
"""
from __future__ import annotations

import re
from pathlib import Path


_OS_ENVIRON_RE = re.compile(r"\bos\.environ\b")


def test_os_environ_read_only_in_app_config_py() -> None:
    repo = Path(__file__).parents[1]
    app_dir = repo / "app"
    offenders: list[str] = []
    for path in app_dir.rglob("*.py"):
        # Allowed: app/config.py is the single source of truth.
        if path.relative_to(repo) == Path("app") / "config.py":
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _OS_ENVIRON_RE.search(line):
                offenders.append(f"{path.relative_to(repo)}:{lineno}: {stripped}")
    assert not offenders, (
        "NFR-SEC-002 violation: os.environ accessed outside app/config.py:\n"
        + "\n".join(offenders)
    )
