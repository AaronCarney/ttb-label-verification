"""Per-batch async event broker.

Each subscriber gets its own ``asyncio.Queue``; ``broadcast`` pushes the same
event dict to every subscriber. The Web layer's SSE response loop iterates the
subscriber queue and yields ``sse_starlette.EventSourceResponse``-friendly
dicts.

Connection-close detection: when the client disconnects (FastAPI raises
``ClientDisconnect`` inside the response generator), the route handler calls
``unsubscribe(q)``. The worker continues so a reconnecting consumer can resume
from ``current_index``. Source: ARCH §5.2 / T6 §Q6.6 contract.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class SSEBus:
    """Per-batch async event bus."""

    def __init__(self) -> None:
        self.subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    def broadcast(self, event: dict) -> None:
        # Iterate over a copy so concurrent unsubscribe does not mutate during.
        for q in list(self.subscribers):
            q.put_nowait(event)

    async def iterate(
        self,
        q: asyncio.Queue,
        *,
        terminator_event: str | None = None,
    ) -> AsyncIterator[dict]:
        """Yield events from a subscriber queue until the terminator event is
        seen (or forever if ``terminator_event`` is None). Auto-unsubscribes on
        terminator."""
        try:
            while True:
                evt = await q.get()
                yield evt
                if terminator_event is not None and evt.get("event") == terminator_event:
                    return
        finally:
            self.unsubscribe(q)
