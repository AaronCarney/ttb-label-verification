"""Page-shell GET routes for the React island.

This module is template-rendering only. It does NOT import from
``app.services``, ``app.orchestrator``, ``app.vision``, or ``app.rules``.
Engine logic lives in the JSON API routes (``app.api.labels``,
``app.api.batches``, ``app.api.overrides``), which are owned by E5/E6.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "ui" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

router = APIRouter(tags=["ui"])


@router.get("/", response_class=HTMLResponse)
async def single_page_shell(request: Request) -> HTMLResponse:
    """Render the single-label review shell. The React island handles all
    reviewer interaction client-side; the shell is a static document."""
    return templates.TemplateResponse(
        request=request,
        name="single.html",
        context={"envelope_json": None},
    )


@router.get("/batch/{batch_id}", response_class=HTMLResponse)
async def batch_page_shell(request: Request, batch_id: str) -> HTMLResponse:
    """Render the batch review shell for a given batch_id. The React island
    subscribes via SSE to ``/batches/{batch_id}/stream`` (E6 endpoint)."""
    return templates.TemplateResponse(
        request=request,
        name="batch.html",
        context={"batch_id": batch_id},
    )
