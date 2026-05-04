# eval/dashboard.py
"""Render /eval HTML against eval/history/. Server-side Jinja2."""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(("html",)),
)


def render_dashboard(history_dir: Path) -> str:
    summary_path = history_dir / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.is_file() else {"runs": []}

    latest = None
    history_files = sorted(p for p in history_dir.glob("*.json") if p.name != "summary.json")
    if history_files:
        latest = json.loads(history_files[-1].read_text())

    template = _env.get_template("dashboard.html")
    return template.render(summary=summary, latest=latest)
