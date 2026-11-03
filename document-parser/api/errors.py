"""Service rejections → HTTP responses, in one place (#audit-05).

Every service error derives from `ServiceError` and carries its status, so
the routers no longer catch them one family at a time: they let them through
and this handler answers with that status and the body FastAPI gives an
`HTTPException`, `{"detail": "<message>"}`.

Registered on the app by `main.py`. A test that builds its own app around a
router registers it too, or the router's rejections surface as 500s.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from services.errors import ServiceError

if TYPE_CHECKING:
    from fastapi import FastAPI, Request


async def _service_error_response(_request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content={"detail": str(exc)})


def register_error_handlers(app: FastAPI) -> None:
    """Answer every `ServiceError` a route lets through with its own status."""
    app.add_exception_handler(ServiceError, _service_error_response)
