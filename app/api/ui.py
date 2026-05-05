"""Page-shell GET routes for the React island.

This module is template-rendering only. It does NOT import from
``app.services``, ``app.orchestrator``, ``app.vision``, or ``app.rules``.
Engine logic lives in the JSON API routes (``app.api.labels``,
``app.api.batches``, ``app.api.overrides``), which are owned by E5/E6.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from collections import OrderedDict

_logger = logging.getLogger("app.api.ui")

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
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

# Per-process cache of upload bytes keyed by synthesized evaluation_id. Bounded
# so a long-running Space doesn't grow without limit. The value is (mime, bytes);
# bytes are GC'd when the entry is evicted.
_UPLOAD_IMAGE_CACHE_MAX = 64
_LATEST_UPLOAD_IMAGES: OrderedDict[str, tuple[str, bytes]] = OrderedDict()


def _stash_upload_image(eval_id: str, mime: str, body: bytes) -> None:
    _LATEST_UPLOAD_IMAGES[eval_id] = (mime, body)
    while len(_LATEST_UPLOAD_IMAGES) > _UPLOAD_IMAGE_CACHE_MAX:
        evicted_id, _ = _LATEST_UPLOAD_IMAGES.popitem(last=False)
        _logger.debug(
            "upload_image_evicted",
            extra={"evaluation_id": evicted_id, "cache_max": _UPLOAD_IMAGE_CACHE_MAX},
        )


# Fixture image directory — mirrors the on-disk layout under fixtures/.
_FIXTURE_IMAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "fixtures"
_FIXTURE_DIR_BY_SLUG = {
    "01": "01-spirits-clean",
    "02": "02-bourbon-stones-throw",
    "03": "03-warning-title-case",
    "04": "04-low-res-blurry",
    "06": "06-abv-out-of-tolerance",
    "07": "07-borderline-confidence",
}


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
            "image_url": f"/fixtures/{slug}/label.png",
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
    # Stash under the canonical id the envelope carries so the image route
    # and template URL agree even when the evaluator synthesises its own id.
    _stash_upload_image(envelope.evaluation_id, mime, image_bytes)
    return templates.TemplateResponse(
        request=request,
        name="single.html",
        context={
            "envelope_json": envelope.model_dump_json(),
            "dev_mode": settings.dev_mode,
            "fixture_slug": None,  # suppress prev/next nav for live uploads
            "image_url": f"/labels/{envelope.evaluation_id}/image",
        },
    )


@router.get("/fixtures/{slug}/label.png")
async def fixture_label_image(slug: str) -> Response:
    """Serve the PNG for one of the shipped demo fixtures."""
    from fastapi import HTTPException

    dirname = _FIXTURE_DIR_BY_SLUG.get(slug)
    if dirname is None:
        raise HTTPException(status_code=404, detail=f"unknown fixture {slug!r}")
    path = _FIXTURE_IMAGE_ROOT / dirname / "label.png"
    try:
        body = path.read_bytes()
    except OSError as e:
        # Most likely cause: the Docker image's `COPY fixtures/ ./fixtures/`
        # missed this slug, or the fixture set was renamed without updating
        # _FIXTURE_DIR_BY_SLUG. Log path so ops can diagnose.
        _logger.warning(
            "fixture_image_read_failed",
            extra={"slug": slug, "path": str(path), "error_class": type(e).__name__},
        )
        raise HTTPException(status_code=404, detail=f"fixture image missing: {slug}")
    return Response(content=body, media_type="image/png")


@router.get("/labels/{eval_id}/image")
async def upload_label_image(eval_id: str) -> Response:
    """Serve the PNG/JPEG bytes uploaded for a given evaluation."""
    from fastapi import HTTPException

    entry = _LATEST_UPLOAD_IMAGES.get(eval_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"no image for evaluation {eval_id!r}")
    mime, body = entry
    return Response(content=body, media_type=mime)


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


@router.get("/batches", response_class=HTMLResponse)
async def batches_upload_page(
    request: Request,
    settings: Settings = Depends(_get_settings),
) -> HTMLResponse:
    """Render the bulk-upload form. Submitting it lands at POST /batches/upload
    which spawns a worker and redirects into the existing batch shell."""
    return templates.TemplateResponse(
        request=request,
        name="batches_upload.html",
        context={"dev_mode": settings.dev_mode},
    )


@router.post("/batches/upload")
async def batches_upload_submit(
    request: Request,
    labels: list[UploadFile] = File(...),
    settings: Settings = Depends(_get_settings),
    evaluator=Depends(_get_upload_evaluator),
):
    """Build a real in-flight batch from N uploaded images.

    The existing JSON `POST /batches` endpoint takes only refs and the worker
    stubs out image bytes — that's fine for tests but useless for a grader who
    wants to drop their own files. We pre-populate `BatchWorker._label_lookup`
    here so each item carries the exact bytes the user uploaded.
    """
    from app.api._sse_bus import SSEBus
    from app.batch.anomaly import AnomalyDetector
    from app.batch.state import InFlightBatch
    from app.batch.worker import BatchWorker
    from app.schemas.application import Application
    from app.schemas.batch import BatchItem, ItemState
    from app.schemas.label import Label as LabelModel

    if not labels:
        return templates.TemplateResponse(
            request=request,
            name="batches_upload.html",
            context={
                "dev_mode": settings.dev_mode,
                "upload_error": "Pick at least one PNG or JPEG file.",
            },
            status_code=400,
        )

    # Read every file up front so we can validate MIME before scheduling work.
    raw: list[tuple[str, bytes, str]] = []
    for upload in labels:
        body = await upload.read()
        mime = _detect_image_mime(body)
        if mime is None:
            return templates.TemplateResponse(
                request=request,
                name="batches_upload.html",
                context={
                    "dev_mode": settings.dev_mode,
                    "upload_error": (
                        f"Unsupported file: {upload.filename or 'upload'} — "
                        "every upload must be PNG or JPEG."
                    ),
                },
                status_code=400,
            )
        raw.append((upload.filename or f"label-{len(raw)}", body, mime))

    batch_id = f"B-{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    items: list[BatchItem] = []
    label_lookup: dict[str, LabelModel] = {}
    app_lookup: dict[str, Application] = {}
    for idx, (filename, body, mime) in enumerate(raw):
        label_id = f"{batch_id}-{idx:03d}-{filename}"
        application_ref = f"{batch_id}-app-{idx:03d}"
        items.append(
            BatchItem(
                label_id=label_id,
                application_ref=application_ref,
                state=ItemState.QUEUED,
                result=None,
                enqueued_at=now,
            )
        )
        label_lookup[label_id] = LabelModel(
            label_id=label_id,
            batch_id=batch_id,
            image_bytes=body,
            content_type=mime,
            face_tag="front",
            dimensions=None,
        )
        app_lookup[application_ref] = Application(
            application_id=application_ref,
            evaluation_id=label_id,
            expected_values=(),
        )

    in_flight = InFlightBatch(
        batch_id=batch_id,
        agent_id="ui-bulk-upload",
        items=tuple(items),
        lookahead_k=max(1, settings.lookahead_k),
    )
    bus = SSEBus()
    request.app.state.batches[batch_id] = in_flight
    if not hasattr(request.app.state, "buses"):
        request.app.state.buses = {}
    request.app.state.buses[batch_id] = bus

    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=evaluator,
        anomaly=AnomalyDetector(),
        bus=bus,
    )
    worker._label_lookup = label_lookup
    worker._app_lookup = app_lookup
    asyncio.create_task(worker.run())

    return RedirectResponse(url=f"/batch/{batch_id}", status_code=303)
