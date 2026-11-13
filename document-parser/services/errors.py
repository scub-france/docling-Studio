"""The one base for service rejections (#396).

Every service error family subclasses `ServiceError`: a message plus the
HTTP status a router maps it to. The API layer translates them in one
place, `api/errors.py`.
"""

from __future__ import annotations


class ServiceError(Exception):
    """A service rejection carrying an HTTP status hint for the API layer."""

    http_status: int = 400

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status
