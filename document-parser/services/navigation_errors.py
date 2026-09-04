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


class InvestigationNotFoundError(NavigationServiceError):
    http_status = 404


class InvestigationClosedError(NavigationServiceError):
    """The investigation is no longer accepting writes.

    Also raised when a plan is submitted twice: a plan that grows while it is
    being executed is not a plan, and appending to one silently would make
    the attempt budget meaningless.
    """

    http_status = 409


class StepNotFoundError(NavigationServiceError):
    http_status = 404


class StepSettledError(NavigationServiceError):
    """The step is already answered, or has spent its attempt budget."""

    http_status = 409


class UnbackedAnswerError(NavigationServiceError):
    """The answer cites an anchor no attempt was allowed to keep.

    `verify_citation` applied to the answer as a whole: the server is the
    source of truth for what the document says, and that has to hold at the
    moment the claim is published, not only when it was read.
    """

    http_status = 400


class UnworkedStepError(NavigationServiceError):
    """The plan still has a step nobody worked.

    Closing over a pending step let an investigation publish a claim about
    something it never looked at — the plan said it would, the record shows it
    did not, and the answer asserted it anyway. Working the step or abandoning
    it explicitly are both fine; skipping it silently is what is not.
    """

    http_status = 409
