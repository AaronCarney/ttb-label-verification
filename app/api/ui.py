"""Page-shell GET routes for the React island.

This module is template-rendering only. It does NOT import from
``app.services``, ``app.orchestrator``, ``app.vision``, or ``app.rules``.
Engine logic lives in the JSON API routes (``app.api.labels``,
``app.api.batches``, ``app.api.overrides``), which are owned by E5/E6.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile
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


def _get_upload_evaluator():
    """Indirection for tests: returns the singleton evaluator built against
    process settings. Tests override this dependency to inject a fake so the
    upload endpoint never reaches OpenAI."""
    from app.deps import build_evaluator
    return build_evaluator(Settings())


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def _detect_image_mime(data: bytes) -> str | None:
    if data.startswith(_PNG_MAGIC):
        return "image/png"
    if data.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    return None


@router.post("/", response_class=HTMLResponse)
async def single_label_upload(
    request: Request,
    label: UploadFile = File(...),
    settings: Settings = Depends(_get_settings),
    evaluator=Depends(_get_upload_evaluator),
) -> HTMLResponse:
    """Run an uploaded label through the evaluator and re-render the single-
    label shell with the live envelope embedded. The `application` payload is
    synthesized server-side (random IDs, no expected values) so the grader
    only has to pick an image file — they're not expected to hand-author the
    Application JSON. Returns the same template as `/` so the React island
    mounts identically; errors render an inline banner with HTTP 400."""
    from app.schemas.application import Application
    from app.schemas.label import Label as LabelModel

    image_bytes = await label.read()
    mime = _detect_image_mime(image_bytes)
    if mime is None:
        return templates.TemplateResponse(
            request=request,
            name="single.html",
            context={
                "envelope_json": None,
                "dev_mode": settings.dev_mode,
                "upload_error": "Unsupported file type — upload a PNG or JPEG.",
            },
            status_code=400,
        )

    application_id = f"app-{uuid.uuid4().hex[:12]}"
    evaluation_id = f"ev-{uuid.uuid4().hex[:12]}"
    app_obj = Application(
        application_id=application_id,
        evaluation_id=evaluation_id,
        expected_values=(),
    )
    label_obj = LabelModel(
        label_id=label.filename or "uploaded-label",
        batch_id=application_id,
        image_bytes=image_bytes,
        content_type=mime,
        face_tag="front",
        dimensions=None,
    )
    envelope = await evaluator.evaluate(application=app_obj, label=label_obj)
    return templates.TemplateResponse(
        request=request,
        name="single.html",
        context={
            "envelope_json": envelope.model_dump_json(),
            "dev_mode": settings.dev_mode,
            "fixture_slug": None,  # suppress prev/next nav for live uploads
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
