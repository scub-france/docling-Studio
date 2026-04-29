"""Domain models — pure data structures with no framework dependencies."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from domain.events import DocumentLifecycleChanged
from domain.lifecycle import assert_transition
from domain.value_objects import DocumentLifecycleState


class AnalysisStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Document:
    id: str = field(default_factory=_new_id)
    filename: str = ""
    content_type: str | None = None
    file_size: int | None = None
    page_count: int | None = None
    storage_path: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    lifecycle_state: DocumentLifecycleState = DocumentLifecycleState.UPLOADED
    lifecycle_state_at: datetime | None = None

    def transition_to(
        self,
        target: DocumentLifecycleState,
        *,
        now: datetime | None = None,
    ) -> DocumentLifecycleChanged:
        """Move the document to `target`, validating the transition.

        Returns the corresponding `DocumentLifecycleChanged` event so the
        caller (typically a service) can log / persist / publish it. The
        event is pure data — no event bus is wired in 0.6.0.

        Raises:
            InvalidLifecycleTransitionError: if (current → target) is not in
                the allowed transition table.
        """
        previous = self.lifecycle_state
        assert_transition(previous, target)
        at = now or _utcnow()
        self.lifecycle_state = target
        self.lifecycle_state_at = at
        return DocumentLifecycleChanged(
            document_id=self.id,
            previous=previous,
            current=target,
            at=at,
        )


@dataclass
class AnalysisJob:
    id: str = field(default_factory=_new_id)
    document_id: str = ""
    status: AnalysisStatus = AnalysisStatus.PENDING
    content_markdown: str | None = None
    content_html: str | None = None
    pages_json: str | None = None
    document_json: str | None = None
    chunks_json: str | None = None
    error_message: str | None = None
    progress_current: int | None = None
    progress_total: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)

    # Joined from document (not persisted separately)
    document_filename: str | None = None

    def mark_running(self) -> None:
        """Transition to RUNNING and record the start timestamp."""
        if self.status != AnalysisStatus.PENDING:
            raise ValueError(f"Cannot mark as RUNNING from {self.status} (expected PENDING)")
        self.status = AnalysisStatus.RUNNING
        self.started_at = _utcnow()

    def mark_completed(
        self,
        markdown: str,
        html: str,
        pages_json: str,
        document_json: str | None = None,
        chunks_json: str | None = None,
    ) -> None:
        """Transition to COMPLETED with conversion results."""
        if self.status != AnalysisStatus.RUNNING:
            raise ValueError(f"Cannot mark as COMPLETED from {self.status} (expected RUNNING)")
        self.status = AnalysisStatus.COMPLETED
        self.content_markdown = markdown
        self.content_html = html
        self.pages_json = pages_json
        self.document_json = document_json
        self.chunks_json = chunks_json
        self.completed_at = _utcnow()

    def update_progress(self, current: int, total: int) -> None:
        """Update batch progress counters."""
        if self.status != AnalysisStatus.RUNNING:
            raise ValueError(f"Cannot update progress from {self.status} (expected RUNNING)")
        self.progress_current = current
        self.progress_total = total

    def mark_failed(self, error: str) -> None:
        """Transition to FAILED with an error message."""
        if self.status not in (AnalysisStatus.PENDING, AnalysisStatus.RUNNING):
            raise ValueError(
                f"Cannot mark as FAILED from {self.status} (expected PENDING or RUNNING)"
            )
        self.status = AnalysisStatus.FAILED
        self.error_message = error
        self.completed_at = _utcnow()
