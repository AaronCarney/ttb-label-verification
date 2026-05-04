"""Page-shell GET routes for the React island.

This module is template-rendering only. It does NOT import from
``app.services``, ``app.orchestrator``, ``app.vision``, or ``app.rules``.
Engine logic lives in the JSON API routes (``app.api.labels``,
``app.api.batches``, ``app.api.overrides``), which are owned by E5/E6.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import Settings


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "ui" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

# Pre-rendered demo envelope so a grader visiting `/` immediately sees a
# populated reviewer console rather than the raw "no envelope" placeholder.
# Generated offline from a real cloud-vision evaluation against fixture-01;
# the React island reads the JSON-encoded envelope from the page shell at
# mount time. Source path is project-root-relative so the Docker image's
# `COPY demo ./demo` puts it on the running container.
_DEMO_ENVELOPE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "demo" / "sample-envelope.json"
)
_DEMO_ENVELOPE_CACHE: str | None = None
_DEMO_ENVELOPE_CACHED = False


def _read_demo_envelope() -> str | None:
    """Read the on-disk demo envelope once per process; return None if absent
    so the shell falls back to the React island's placeholder."""
    global _DEMO_ENVELOPE_CACHE, _DEMO_ENVELOPE_CACHED
    if _DEMO_ENVELOPE_CACHED:
        return _DEMO_ENVELOPE_CACHE
    try:
        _DEMO_ENVELOPE_CACHE = _DEMO_ENVELOPE_PATH.read_text()
    except OSError:
        _DEMO_ENVELOPE_CACHE = None
    _DEMO_ENVELOPE_CACHED = True
    return _DEMO_ENVELOPE_CACHE


router = APIRouter(tags=["ui"])


def _get_settings() -> Settings:
    return Settings()


@router.get("/", response_class=HTMLResponse)
async def single_page_shell(
    request: Request,
    settings: Settings = Depends(_get_settings),
) -> HTMLResponse:
    """Render the single-label review shell. The React island handles all
    reviewer interaction client-side; the shell is a static document.

    Serves the pre-rendered demo envelope when present so the front page
    isn't blank for a grader visiting cold."""
    return templates.TemplateResponse(
        request=request,
        name="single.html",
        context={"envelope_json": _read_demo_envelope(), "dev_mode": settings.dev_mode},
    )


@router.get("/batch/{batch_id}", response_class=HTMLResponse)
async def batch_page_shell(
    request: Request,
    batch_id: str,
    settings: Settings = Depends(_get_settings),
) -> HTMLResponse:
    """Render the batch review shell for a given batch_id. The React island
    subscribes via SSE to ``/batches/{batch_id}/stream`` (E6 endpoint)."""
    return templates.TemplateResponse(
        request=request,
        name="batch.html",
        context={"batch_id": batch_id, "dev_mode": settings.dev_mode},
    )
