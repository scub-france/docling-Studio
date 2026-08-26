"""Typed rejections for the document-agent services.

Shared by the parse loader and the three use-case services, so they live
below all of them rather than inside whichever one happened to need them
first. Each carries the HTTP status a router would map it to — the same
convention `ReasoningService` established — and the MCP adapter turns the
whole family into a tool error.
"""

from __future__ import annotations


class NavigationServiceError(Exception):
    """Base error for document-navigation rejections, with a status hint."""

    http_status: int = 500

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class DocumentNotFoundError(NavigationServiceError):
    http_status = 404


class NoParseError(NavigationServiceError):
    """The document exists but carries no completed analysis to read."""

    http_status = 409


class RefNotFoundError(NavigationServiceError):
    http_status = 404


class InvalidArgumentError(NavigationServiceError):
    http_status = 400


class NavigationUnavailableError(NavigationServiceError):
    """Raised when the services are not wired yet — the app is still booting.

    Lives with the other service errors rather than in the composition root so
    the adapter catches it with the rest of the family instead of
    special-casing a builtin exception type, which would swallow genuine
    internal failures.
    """

    http_status = 503
