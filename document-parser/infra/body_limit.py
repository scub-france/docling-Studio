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
    read; otherwise the body is counted as it arrives (chunked uploads have
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
        declared = Headers(scope=scope).get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > self._max_bytes:
            await self._reject(scope, receive, send)
            return

        messages: deque[Message] = deque()
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            received += len(message.get("body", b""))
            if received > self._max_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            if messages:
                return messages.popleft()
            return await receive()

        await self._app(scope, replay, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse({"detail": self._detail}, status_code=413)
        await response(scope, receive, send)
