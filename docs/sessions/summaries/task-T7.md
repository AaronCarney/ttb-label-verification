# Task T7 — POST /batches + GET /batches/{id}{/stream}

**STATUS: COMPLETE**

## What Was Done

- Created `app/api/batches.py` — 3 routes: `POST /batches` (202), `GET /batches/{batch_id}` (snapshot), `GET /batches/{batch_id}/stream` (SSE)
- Edited `app/main.py` additively: batches router registration + lifespan state init/clear + pre-init state on application object
- Created `tests/test_batch_endpoint_post.py` (4 tests) and `tests/test_batch_endpoint_sse.py` (3 tests)

## Rule 1-3 Fixes Applied

1. **`with TestClient(app) as client:`** — Starlette version requires context-manager form to trigger lifespan; bare `TestClient(app)` didn't run lifespan.
2. **Pre-init `application.state.batches/buses = {}`** — `httpx.AsyncClient` (used in SSE tests) doesn't trigger ASGI lifespan. Pre-init at factory time ensures state exists regardless of how the app is invoked in tests. Lifespan still re-assigns on startup and clears on shutdown for production.

## Test Results

7/7 tests pass. Commit: `82d4e29`.
