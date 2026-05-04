# app/api/eval.py
"""GET /eval — DEV_MODE-gated eval dashboard route (E8 T7).

Only registered when settings.dev_mode is truthy. See app/main.py.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from eval.dashboard import render_dashboard

router = APIRouter(tags=["eval"])
# Repo-root-relative; resolves correctly regardless of CWD or container WORKDIR.
# app/api/eval.py → parents[0]=api, [1]=app, [2]=repo root.
_HISTORY_DIR = Path(__file__).resolve().parents[2] / "eval" / "history"


@router.get("/eval", response_class=HTMLResponse)
async def eval_dashboard() -> str:
    return render_dashboard(history_dir=_HISTORY_DIR)
