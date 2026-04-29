"""Domain events — frozen records that document state transitions.

Events are produced by domain operations (typically returned from a
mutation method on an aggregate). They are pure data — no event bus is
wired in 0.6.0; services can choose to log, persist, or publish them
later. Keeping them here keeps the domain layer free of any event-bus
infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from domain.value_objects import DocumentLifecycleState


@dataclass(frozen=True)
class DocumentLifecycleChanged:
    """A Document lifecycle transition occurred.

    Attributes:
        document_id: id of the document that transitioned.
        previous: state the document was in before the transition.
        current: state the document is in after the transition.
        at: timestamp of the transition (UTC).
    """

    document_id: str
    previous: DocumentLifecycleState
    current: DocumentLifecycleState
    at: datetime
