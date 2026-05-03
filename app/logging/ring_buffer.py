"""``CallRecord`` deque scaffolding. Source: ARCH §6.7 + §6.9.

The actual recording is wired in E3/E4 when seam producers exist; E1 only
ships the constructor so other layers can hold a reference at startup.
"""
from __future__ import annotations

from collections import deque
from typing import Any


DEFAULT_MAXLEN = 200


def new_call_ring_buffer(maxlen: int = DEFAULT_MAXLEN) -> deque[Any]:
    """Return an empty bounded deque for ``CallRecord`` entries (FIFO eviction)."""

    return deque(maxlen=maxlen)
