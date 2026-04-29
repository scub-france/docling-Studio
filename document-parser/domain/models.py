"""Domain models — pure data structures with no framework dependencies."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from domain.events import DocumentLifecycleChanged
from domain.lifecycle import assert_transition
from domain.value_objects import (
    ChunkBbox,
    ChunkDocItem,
    ChunkEditAction,
    DocumentLifecycleState,
    DocumentStoreLinkState,
    StoreKind,
)


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


@dataclass
class Store:
    """A logical destination for ingested chunks.

    A `Store` represents a named, configurable target for ingestion (e.g.
    `rh-corpus-v3`, `legal-v1`). It is decoupled from the underlying
    `VectorStore` adapter (which represents the *technology*, like
    OpenSearch). One adapter can serve many stores by namespacing the
    physical index name on `slug`.

    See design doc `docs/design/203-per-store-ingestion-state.md`.
    """

    id: str = field(default_factory=_new_id)
    name: str = ""
    slug: str = ""
    kind: StoreKind = StoreKind.OPENSEARCH
    embedder: str = ""
    config: dict = field(default_factory=dict)
    is_default: bool = False
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class DocumentStoreLink:
    """A live record of a document's presence in a single store.

    The link carries the per-pair state (Ingested / Stale / Failed) plus
    metadata used by the auto-stale detection (#204) and the chunks
    editor (#205). One row per (document, store) pair — enforced by a
    UNIQUE constraint at the persistence layer.
    """

    id: str = field(default_factory=_new_id)
    document_id: str = ""
    store_id: str = ""
    state: DocumentStoreLinkState = DocumentStoreLinkState.INGESTED
    chunkset_hash: str | None = None
    last_push_at: datetime | None = None
    last_run_id: str | None = None
    error_message: str | None = None

    def mark_ingested(
        self,
        *,
        hash_: str,
        at: datetime,
        run_id: str | None = None,
    ) -> None:
        """Record a successful push: chunkset hash + timestamp + run id."""
        self.state = DocumentStoreLinkState.INGESTED
        self.chunkset_hash = hash_
        self.last_push_at = at
        self.last_run_id = run_id
        self.error_message = None

    def mark_stale(self) -> None:
        """Mark the link as stale (source chunkset drifted from pushed)."""
        self.state = DocumentStoreLinkState.STALE
        self.error_message = None

    def mark_failed(self, *, error: str) -> None:
        """Record a failed push attempt."""
        self.state = DocumentStoreLinkState.FAILED
        self.error_message = error


@dataclass
class Chunk:
    """A persisted chunk — first-class entity introduced by #205.

    Replaces the legacy `analysis_jobs.chunks_json` blob. The `id` is
    stable across edits except for split/merge which produce new chunks
    with new ids; the lineage is recorded in `chunk_edits` rows.

    `sequence` controls ordering within a document. Gaps are allowed —
    splits push subsequent chunks' sequences without rewriting them.

    `deleted_at` is non-null when the chunk has been soft-deleted; the
    row stays in the table so the audit trail keeps its before/after
    pointers valid.
    """

    id: str = field(default_factory=_new_id)
    document_id: str = ""
    sequence: int = 0
    text: str = ""
    headings: list[str] = field(default_factory=list)
    source_page: int | None = None
    bboxes: list[ChunkBbox] = field(default_factory=list)
    doc_items: list[ChunkDocItem] = field(default_factory=list)
    token_count: int | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class ChunkEdit:
    """An immutable audit record describing one mutating operation on
    the chunkset of a document. Written atomically with the chunk
    write it describes.

    `before` and `after` are JSON-serializable snapshots of the chunk
    state. They are `None` for the start/end of the chunk's life:
      - `before is None` for INSERT
      - `after  is None` for DELETE
      - For MERGE: a single result row carries `parents = [chunk_ids…]`
      - For SPLIT: two result rows each carry `parents = [source_id]`
        and the source's edit row carries `children = [new_id, new_id]`
    """

    id: str
    document_id: str
    chunk_id: str | None
    action: ChunkEditAction
    actor: str
    at: datetime
    before: dict | None = None
    after: dict | None = None
    parents: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    reason: str | None = None


@dataclass(frozen=True)
class ChunkPush:
    """Snapshot of which chunks were pushed to which store, when.

    Lets the API answer 'show me the chunkset that was in store X at
    push N' without replaying the full audit log.
    """

    id: str
    document_id: str
    store_id: str
    chunkset_hash: str
    chunk_ids: list[str]
    pushed_at: datetime
