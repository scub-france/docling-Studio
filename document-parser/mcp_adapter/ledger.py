"""Running tally of what this MCP surface has served.

"What did this citation cost" and "what has this conversation cost" are
different questions, and only the second one tells a reader whether the
document work is getting expensive. A single result's `est_tokens` cannot
answer it: each tool call is independent, and an app card is an isolated
iframe that knows nothing of the call before it. So the tally is kept here,
on the server, where every tool result passes.

**Scope is one server process.** Over stdio that is exactly one client — the
process is spawned per session and dies with it, so the tally is that
session's. Over streamable HTTP the surface is `stateless_http`, meaning
there is no session to key on: every client of that backend adds to the same
total. That is the honest limit of this number, and the viewer says so rather
than implying a per-conversation figure it cannot produce.

What is counted: the JSON each tool returns, priced with the same
`estimate_tokens` as `get_outline` entries, minus the page raster — an image
is not text and pricing it in tokens would be inventing a figure. What is not
counted: the tally fields themselves, which are written after the
measurement. That is a handful of tokens per call, and correcting for it
would mean measuring a payload that does not exist yet.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from threading import Lock
from typing import Any, TypeVar

from domain.navigation import estimate_tokens

T = TypeVar("T")

# Excluded from the measurement wherever it appears: bytes, not text.
_IMAGE_FIELD = "page_image"


@dataclass(frozen=True)
class Usage:
    """What this server has served so far."""

    calls: int
    est_tokens: int


class Ledger:
    """A per-server tally of served payloads.

    One instance per `build_mcp_server` rather than a module-level global:
    two servers in one process (a test suite builds dozens) must not pool
    their totals, and a global would make that impossible to unwind.
    """

    def __init__(self) -> None:
        # uvicorn may serve from more than one thread; the tally is two
        # integers, so a plain lock is both correct and free.
        self._lock = Lock()
        self._calls = 0
        self._tokens = 0

    def record(self, payload: T) -> T:
        """Price `payload`, add it to the tally, and hand it straight back.

        Returns its argument so a tool stays the four-line mapping it was:
        `return ledger.record(outline_result(outline))`.
        """
        cost = estimate_tokens(_serialise(payload))
        with self._lock:
            self._calls += 1
            self._tokens += cost
        return payload

    def snapshot(self) -> Usage:
        with self._lock:
            return Usage(calls=self._calls, est_tokens=self._tokens)


def _serialise(payload: object) -> str:
    """The payload as the client will read it, minus the page raster."""
    if is_dataclass(payload) and not isinstance(payload, type):
        data: Any = asdict(payload)
        data.pop(_IMAGE_FIELD, None)
    else:
        data = payload
    # `default=str` so a stray non-JSON value costs a measurement rather than
    # raising: a tally is never worth failing a tool call over.
    return json.dumps(data, default=str, ensure_ascii=False)
