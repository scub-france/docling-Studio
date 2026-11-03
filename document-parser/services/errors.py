"""The one contract between a service rejection and an HTTP status (#audit-05).

Every service error family derives from `ServiceError`, which carries the status
a router answers it with. The API layer maps the whole family in one exception
handler (`api/errors.py`), so the services stay free of FastAPI and the routers
free of a try/except per family. A family keeps its own base so a caller can
still catch it alone: the MCP adapter turns only the navigation family into a
tool error.
"""

from __future__ import annotations


class ServiceError(Exception):
    """A service rejection, with the HTTP status the API layer answers it with.

    A family sets its default status on its base; a subclass narrows it, and
    a single raise can override it with `http_status=`.
    """

    http_status: int = 500

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status
