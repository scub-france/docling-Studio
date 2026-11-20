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
    DocumentLifecycleState,
    DocumentStoreLinkState,
    StoreKind,
)


class AnalysisStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def get_utc_now() -> datetime:
    """The current time, timezone-aware in UTC: every entity timestamp."""
    return datetime.now(UTC)


def generate_id() -> str:
    """A new entity id, the dashed UUID4 form (36 characters)."""
    return str(uuid.uuid4())


def generate_compact_id() -> str:
    """A new id in the 32-hex-character UUID4 form.

    Kept apart from `generate_id`: document versions and the chunks a
    version restore writes have always used this form.
    """
    return uuid.uuid4().hex


@dataclass
class Document:
    id: str = field(default_factory=generate_id)
    filename: str = ""
    content_type: str | None = None
    file_size: int | None = None
    page_count: int | None = None
    storage_path: str = ""
    created_at: datetime = field(default_factory=get_utc_now)
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
        at = now or get_utc_now()
        self.lifecycle_state = target
        self.lifecycle_state_at = at
        return DocumentLifecycleChanged(
            document_id=self.id,
            previous=previous,
            current=target,
            at=at,
        )


@dataclass(frozen=True)
class DocumentChunkSource:
    """The analysis result a document's live chunks were generated from."""

    document_id: str
    analysis_id: str
    result_hash: str


@dataclass(frozen=True)
class DocumentAnalysisState:
    """A document's analysis state: its active analysis and the source of its chunks.

    Aggregate root of the document-level state (02-2.4.3), read as a whole
    and written in two independent parts. The active analysis is the
    document's current analysis (see `resolve_current_analysis_id`); the
    chunk source is the analysis result the live chunks were generated from.
    Each writer changes only the part it owns, with its own write: completing
    an analysis or deleting the active one writes the selection, a rechunk
    the chunk source, a restore both. So a rechunk never rewrites a selection
    made meanwhile, and a completion never erases the chunk source.
    """

    document_id: str
    active_analysis_id: str | None = None
    chunk_source: DocumentChunkSource | None = None

    def are_chunks_stale(self, analysis_id: str, result_hash: str, *, has_chunks: bool) -> bool:
        """Whether the live chunks may not match the result `result_hash` of `analysis_id`.

        Chunks with no recorded source (made before 0.7.4, #393) have an
        unknown provenance: they count as stale so the user is invited to
        regenerate them. No chunks means nothing can be stale.
        """
        if self.chunk_source is None:
            return has_chunks
        return (
            self.chunk_source.analysis_id != analysis_id
            or self.chunk_source.result_hash != result_hash
        )

    def resolve_selection_after_deleting(
        self, analysis_id: str, latest_remaining_parsed_id: str | None
    ) -> str | None:
        """The active analysis once `analysis_id` is deleted.

        Deleting another analysis keeps the selection. Deleting the active one
        hands it to the latest remaining completed analysis with a Docling
        document (the one the fallback rule would pick), or to none: Ask and
        MCP must not lose their analysis while a usable one remains.
        """
        if self.active_analysis_id != analysis_id:
            return self.active_analysis_id
        return latest_remaining_parsed_id


def resolve_current_analysis_id(
    state: DocumentAnalysisState | None,
    latest_parsed_analysis_id: str | None,
) -> str | None:
    """The document's current analysis: the one its state selects (02-2.3.1).

    Every feature that reads "the document's analysis" without being told
    which one reads this one. `state` is None only for a document with no
    state row at all: one never analysed, whose fallback is None too, or a
    row-less database the 0.7.3 upgrade did not reach. Only then does the
    latest completed analysis with a Docling document stand in. A row whose
    active analysis is NULL is a choice (a restored version without an
    analysis, or the active analysis deleted with no completed analysis with
    a Docling document left to take over): the document has no current one.
    """
    if state is not None:
        return state.active_analysis_id
    return latest_parsed_analysis_id


def resolve_selection_after_restore(
    state: DocumentAnalysisState | None,
    version_analysis_id: str | None,
    fallback_analysis_id: str | None,
) -> str | None:
    """The active analysis once a version is restored.

    A version with an analysis selects it. A version without one clears the
    selection of a document that has a state row; a document with no row
    keeps `fallback_analysis_id` (the latest completed analysis with a
    Docling document), so the row the restore creates does not hide the
    analysis the fallback rule was giving behind a NULL selection.
    """
    if version_analysis_id is not None:
        return version_analysis_id
    if state is not None:
        return None
    return fallback_analysis_id


@dataclass
class AnalysisJob:
    id: str = field(default_factory=generate_id)
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
    created_at: datetime = field(default_factory=get_utc_now)

    # Joined from document (not persisted separately)
    document_filename: str | None = None

    def can_be_current(self) -> bool:
        """Only a completed analysis can be a document's current (active) one."""
        return self.status == AnalysisStatus.COMPLETED

    def can_be_current_of(self, document_id: str) -> bool:
        """Whether this analysis can be the current one of `document_id`."""
        return self.document_id == document_id and self.can_be_current()

    def has_docling_document(self) -> bool:
        """A completed analysis that kept its Docling document: the one the
        editor, the tree, chunking and the fallback current analysis need."""
        return self.can_be_current() and bool(self.document_json)

    def mark_running(self) -> None:
        """Transition to RUNNING and record the start timestamp."""
        if self.status != AnalysisStatus.PENDING:
            raise ValueError(f"Cannot mark as RUNNING from {self.status} (expected PENDING)")
        self.status = AnalysisStatus.RUNNING
        self.started_at = get_utc_now()

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
        self.completed_at = get_utc_now()

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
        self.completed_at = get_utc_now()


@dataclass
class Store:
    """A logical destination for ingested chunks.

    A `Store` represents a named, configurable target for ingestion (e.g.
    `rh-corpus-v3`, `legal-v1`).

    Connection identity (#279): `connection_uri` and `connection_username`
    live on the entity because the store **is** the connection target.
    The password is **not** on this dataclass — it is sealed at rest with
    Fernet and accessed only through explicit repo methods
    (`get_connection_password` / `set_connection_password`). Keeping the
    plaintext off the entity prevents accidental serialization through
    Pydantic / logs / __repr__.

    See design docs `docs/design/203-per-store-ingestion-state.md` and
    `docs/design/279-store-connection-credentials.md`.
    """

    id: str = field(default_factory=generate_id)
    name: str = ""
    slug: str = ""
    kind: StoreKind = StoreKind.OPENSEARCH
    embedder: str = ""
    config: dict = field(default_factory=dict)
    # Connection identity (#279). None means "use env-var fallback at
    # the driver pool" during the transition; once a store carries a
    # URI, the pool keys on that value and ignores the global env.
    connection_uri: str | None = None
    connection_username: str | None = None
    # Whether a password is currently sealed for this store. Lets the
    # API response say "password set" / "password not set" without
    # ever exposing the value. The actual plaintext is fetched via
    # `SqliteStoreRepository.get_connection_password`.
    has_connection_password: bool = False
    is_default: bool = False
    created_at: datetime = field(default_factory=get_utc_now)
    updated_at: datetime = field(default_factory=get_utc_now)


@dataclass
class DocumentStoreLink:
    """A live record of a document's presence in a single store.

    The link carries the per-pair state (Ingested / Stale / Failed) plus
    metadata used by the auto-stale detection (#204) and the chunks
    editor (#205). One row per (document, store) pair — enforced by a
    UNIQUE constraint at the persistence layer.
    """

    id: str = field(default_factory=generate_id)
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

    def mark_failed(self, *, error: str) -> None:
        """Record a failed push attempt."""
        self.state = DocumentStoreLinkState.FAILED
        self.error_message = error


@dataclass
class Chunk:
    """A persisted chunk — first-class entity introduced by #205.

    Replaces the legacy `analysis_jobs.chunks_json` blob. The `id` is
    stable across edits except for split/merge which produce new chunks
    with new ids.

    `sequence` controls ordering within a document. Gaps are allowed —
    splits push subsequent chunks' sequences without rewriting them.

    `deleted_at` is non-null when the chunk has been soft-deleted; the
    row stays in the table until document deletion.
    """

    id: str = field(default_factory=generate_id)
    document_id: str = ""
    sequence: int = 0
    text: str = ""
    headings: list[str] = field(default_factory=list)
    source_page: int | None = None
    bboxes: list[ChunkBbox] = field(default_factory=list)
    doc_items: list[ChunkDocItem] = field(default_factory=list)
    token_count: int | None = None
    created_at: datetime = field(default_factory=get_utc_now)
    updated_at: datetime = field(default_factory=get_utc_now)
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class ChunkPush:
    """Snapshot of which chunks were pushed to which store, when.

    Lets the API identify the chunkset that was pushed to a store.
    """

    id: str
    document_id: str
    store_id: str
    chunkset_hash: str
    chunk_ids: list[str]
    pushed_at: datetime


class DocumentVersionKind(enum.StrEnum):
    """What triggered the version snapshot.

    - ANALYSIS — a `+ New analysis` run completed for this document
    - CHUNKS   — `+ Generate chunks` (rechunk) produced a new chunkset
    """

    ANALYSIS = "analysis"
    CHUNKS = "chunks"


@dataclass
class DocumentVersion:
    """Frozen pair (OCR analysis + chunks state) for a document (#267).

    Created on explicit version-creating triggers (a new analysis run or
    a `+ Generate chunks` invocation). Manual chunk edits do NOT create
    a version — they mutate the live chunkset until the next snapshot.

    `analysis_id` selects the analysis. Its saved edits are always applied. The chunk
    snapshot and its separate source analysis/result hash record the live
    chunkset at version creation. Restore writes both back into live state.
    """

    id: str = field(default_factory=generate_id)
    document_id: str = ""
    kind: DocumentVersionKind = DocumentVersionKind.ANALYSIS
    analysis_id: str | None = None
    chunks_source_analysis_id: str | None = None
    chunks_source_result_hash: str | None = None
    chunks_snapshot: str | None = None  # JSON-serialized list of chunk dicts
    summary: str = ""
    created_at: datetime = field(default_factory=get_utc_now)

    @property
    def chunk_source(self) -> DocumentChunkSource | None:
        """The chunk source this version froze, or None.

        A half-filled pair counts as none: a database upgraded from 0.7.3 has
        no CHECK keeping the two columns together, and restoring must not fail
        on such a row.
        """
        if self.chunks_source_analysis_id is None or self.chunks_source_result_hash is None:
            return None
        return DocumentChunkSource(
            self.document_id, self.chunks_source_analysis_id, self.chunks_source_result_hash
        )
