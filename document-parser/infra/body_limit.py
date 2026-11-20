"""Request body ceiling for one route (08 MIN: unbounded Docling JSON import).

FastAPI reads and parses a JSON body before the route runs, so a size check
inside the route comes too late. This middleware counts the body first and
answers 413 like the upload route, with a `{"detail": ...}` body.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimitMiddleware:
    """Answer 413 when the body of a request to `path` is over `max_bytes`.

    A declared `Content-Length` over the limit is refused before anything is
    read, and a malformed one gets a 400; otherwise the body is counted as it arrives (chunked uploads have
    no length) and replayed to the app once it is known to fit. Other paths
    pass through untouched.
    """

    def __init__(self, app: ASGIApp, *, path: str, max_bytes: int, detail: str) -> None:
        self._app = app
        self._path = path
        self._max_bytes = max_bytes
        self._detail = detail

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != self._path:
            await self._app(scope, receive, send)
            return
        refusal = self._check_declared_length(Headers(scope=scope).get("content-length"))
        if refusal is not None:
            await refusal(scope, receive, send)
            return

        messages = await self._buffer_body(receive)
        if messages is None:
            await _refuse(413, self._detail)(scope, receive, send)
            return

        async def replay() -> Message:
            if messages:
                return messages.popleft()
            return await receive()

        await self._app(scope, replay, send)

    def _check_declared_length(self, declared: str | None) -> JSONResponse | None:
        """The answer that refuses a declared `Content-Length`, if it must be refused."""
        if declared is None:
            return None
        # ASCII digits only: `"²".isdigit()` is true but `int("²")` raises.
        # Twenty digits is past any real length and below `int`'s digit limit.
        if not (declared.isascii() and declared.isdigit()) or len(declared) > 20:
            return _refuse(400, "Invalid Content-Length header")
        if int(declared) > self._max_bytes:
            return _refuse(413, self._detail)
        return None

    async def _buffer_body(self, receive: Receive) -> deque[Message] | None:
        """Read the body into memory; None as soon as it goes over the limit."""
        messages: deque[Message] = deque()
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            received += len(message.get("body", b""))
            if received > self._max_bytes:
                return None
            if not message.get("more_body", False):
                break
        return messages


def _refuse(status: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status)
