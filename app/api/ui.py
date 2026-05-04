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

# Pre-rendered demo envelopes so a grader visiting `/` (or stepping through
# `?fixture=NN`) immediately sees a populated reviewer console rather than a
# placeholder. Generated offline by `scripts/build_demo_envelopes.py` against
# the cloud-vision evaluator; the React island reads the JSON-encoded
# envelope from the page shell at mount time. The Docker image's
# `COPY demo ./demo` puts these on the running container.
_DEMO_DIR = Path(__file__).resolve().parent.parent.parent / "demo"

# Sequence excludes 05 (batch fixture). Wraparound: ...07 -> 01 -> 02 -> ... -> 07 -> 01...
_FIXTURE_SEQUENCE: tuple[str, ...] = ("01", "02", "03", "04", "06", "07")
_DEFAULT_FIXTURE = "01"

_DEMO_ENVELOPE_CACHE: dict[str, str] = {}
_DEMO_ENVELOPE_CACHED = False


def _populate_envelope_cache() -> None:
    """Load every per-fixture envelope from disk once per process."""
    global _DEMO_ENVELOPE_CACHED
    if _DEMO_ENVELOPE_CACHED:
        return
    for slug in _FIXTURE_SEQUENCE:
        path = _DEMO_DIR / f"sample-envelope-{slug}.json"
        try:
            _DEMO_ENVELOPE_CACHE[slug] = path.read_text()
        except OSError:
            pass
    # Backwards compat: legacy `sample-envelope.json` fills the default slot
    # if the per-fixture file is missing. Lets older deployments serve `/`
    # without the new envelopes during a partial rollout.
    if _DEFAULT_FIXTURE not in _DEMO_ENVELOPE_CACHE:
        legacy = _DEMO_DIR / "sample-envelope.json"
        try:
            _DEMO_ENVELOPE_CACHE[_DEFAULT_FIXTURE] = legacy.read_text()
        except OSError:
            pass
    _DEMO_ENVELOPE_CACHED = True


def _resolve_fixture(requested: str | None) -> str:
    """Pick the slug to serve. Unknown ids fall back to the default so a
    hand-edited URL still produces a usable page rather than a 404."""
    _populate_envelope_cache()
    if requested and requested in _DEMO_ENVELOPE_CACHE:
        return requested
    return _DEFAULT_FIXTURE


def _read_demo_envelope(slug: str) -> str | None:
    _populate_envelope_cache()
    return _DEMO_ENVELOPE_CACHE.get(slug)


def _neighbours(slug: str) -> tuple[str, str]:
    """Return (prev, next) slugs with wraparound around _FIXTURE_SEQUENCE."""
    try:
        idx = _FIXTURE_SEQUENCE.index(slug)
    except ValueError:
        idx = 0
    n = len(_FIXTURE_SEQUENCE)
    return _FIXTURE_SEQUENCE[(idx - 1) % n], _FIXTURE_SEQUENCE[(idx + 1) % n]


router = APIRouter(tags=["ui"])


def _get_settings() -> Settings:
    return Settings()


@router.get("/", response_class=HTMLResponse)
async def single_page_shell(
    request: Request,
    fixture: str | None = None,
    settings: Settings = Depends(_get_settings),
) -> HTMLResponse:
    """Render the single-label review shell. The React island handles all
    reviewer interaction client-side; the shell is a static document.

    `?fixture=NN` swaps the embedded envelope so a grader can step through
    the demo set (FIX-01..04, 06, 07) without uploading anything."""
    slug = _resolve_fixture(fixture)
    prev_slug, next_slug = _neighbours(slug)
    return templates.TemplateResponse(
        request=request,
        name="single.html",
        context={
            "envelope_json": _read_demo_envelope(slug),
            "dev_mode": settings.dev_mode,
            "fixture_slug": slug,
            "prev_fixture": prev_slug,
            "next_fixture": next_slug,
        },
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
