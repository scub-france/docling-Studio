"""Domain-level exceptions.

Exceptions defined in this module are raised by domain operations and value
objects when an invariant is violated. They have no infrastructure
dependencies and are safe to import from any layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.value_objects import DocumentLifecycleState


class DomainError(Exception):
    """Base class for domain-level errors. Catch this when wiring API
    layers if you want a single hook for any invariant violation."""


class InvalidLifecycleTransitionError(DomainError):
    """Raised when a Document.transition_to() call asks for a (source,
    target) pair that is not in the allowed transition table.

    Carries `source` and `target` so callers can produce a useful error
    message without re-discovering them.
    """

    def __init__(
        self,
        *,
        source: DocumentLifecycleState,
        target: DocumentLifecycleState,
    ) -> None:
        super().__init__(f"Invalid document lifecycle transition: {source.value} -> {target.value}")
        self.source = source
        self.target = target
