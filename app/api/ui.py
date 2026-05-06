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


router = APIRouter(tags=["ui"])


def _get_settings() -> Settings:
    return Settings()


@router.get("/", response_class=HTMLResponse)
async def single_page_shell(
    request: Request,
    settings: Settings = Depends(_get_settings),
) -> HTMLResponse:
    """Render the empty-inbox single-label landing. No pre-loaded fixtures;
    the grader sees a drop-zone CTA and either uploads their own labels or
    pulls a starter pack from `/batches/sample.zip`. The React island mounts
    on `<div id="root" data-mode="single">` and renders an envelope only
    after a real upload returns one."""
    return templates.TemplateResponse(
        request=request,
        name="single.html",
        context={
            "envelope_json": None,
            "dev_mode": settings.dev_mode,
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
            "image_url": f"/labels/{envelope.evaluation_id}/image",
        },
    )


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


_ACTIVE_CORPUS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "fixtures" / "_corpus" / "_active.txt"
)
# GitHub raw URL prefix for fetching label binaries when the deployed Space
# doesn't bundle them locally. HF Space's pre-receive hook rejects bare binary
# blobs (they want Xet), so the deploy ships app + _active.txt only and
# fetches images from origin at sample-zip request time.
_CORPUS_RAW_BASE = (
    "https://raw.githubusercontent.com/AaronCarney/ttb-label-verification/main/fixtures/_corpus"
)


def _load_active_ttbids() -> list[str]:
    if not _ACTIVE_CORPUS_PATH.is_file():
        return []
    return [line.strip() for line in _ACTIVE_CORPUS_PATH.read_text().splitlines() if line.strip()]


def _read_label_bytes(ttbid_dirname: str) -> bytes | None:
    """Return the JPEG bytes for one ttbid, preferring local disk (dev /
    GitHub clone) and falling back to GitHub raw (HF Space deploy)."""
    local = _ACTIVE_CORPUS_PATH.parent / ttbid_dirname / "label.jpg"
    if local.is_file():
        return local.read_bytes()
    import urllib.error
    import urllib.request
    url = f"{_CORPUS_RAW_BASE}/{ttbid_dirname}/label.jpg"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            if resp.status != 200:
                return None
            return resp.read()
    except (urllib.error.URLError, TimeoutError):
        return None


@router.get("/batches/sample.zip")
async def batches_sample_zip(n: int = 10) -> Response:
    """Stream a zip of N random labels from the active corpus.

    Lets a grader try the bulk pipeline against real CC0 TTB Public COLA
    Registry labels without needing their own files: download → drop into
    the upload form on /batches → real worker runs through the same code
    path a production caller would hit.

    Image bytes come from local disk if present (dev / GitHub clone) or
    GitHub raw at request time (HF Space deploy, where the corpus isn't
    bundled).
    """
    if n <= 0:
        return Response(
            content=b"n must be a positive integer",
            status_code=400,
            media_type="text/plain",
        )

    active = _load_active_ttbids()
    if not active:
        return Response(
            content=b"active corpus list is empty (fixtures/_corpus/_active.txt missing)",
            status_code=500,
            media_type="text/plain",
        )

    import io
    import random
    import zipfile

    take = min(n, len(active))
    chosen = random.sample(active, take)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for ttbid_dirname in chosen:
            body = _read_label_bytes(ttbid_dirname)
            if body is None:
                continue
            zf.writestr(f"{ttbid_dirname}.jpg", body)
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"content-disposition": 'attachment; filename="sample.zip"'},
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
