"""Domain ports — abstract interfaces that infrastructure must implement.

These protocols define what the domain NEEDS, not how it's done.
Infrastructure adapters (local Docling, Docling Serve, etc.) implement these.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from domain.app_config import LLMHostProbeResult
    from domain.models import (
        AnalysisJob,
        Chunk,
        ChunkEdit,
        ChunkPush,
        Document,
        DocumentStoreLink,
        DocumentVersion,
        Store,
    )
    from domain.navigation import RasterCrop
    from domain.quote_marks import Glyph
    from domain.value_objects import (
        ChunkingOptions,
        ChunkResult,
        ConversionOptions,
        ConversionResult,
        DocumentLifecycleState,
        GraphPayload,
        PageDetail,
        ReasoningResult,
    )
    from domain.vector_schema import IndexedChunk, SearchResult


class ReasoningParseError(Exception):
    """Raised by a `ReasoningRunner` when the upstream LLM couldn't produce a
    parseable answer after retries — e.g. docling-agent's known IndexError on
    `find_json_dicts(...)[0]` when the model fails rejection-sampling.

    Carries the model identifier so the API layer can surface it to the user
    without leaking adapter internals.
    """

    def __init__(self, model_id: str, reason: str = "no parseable answer") -> None:
        super().__init__(f"{model_id}: {reason}")
        self.model_id = model_id
        self.reason = reason


class DocumentConverter(Protocol):
    """Port for document conversion.

    Any implementation (local Docling lib, remote Docling Serve, mock, etc.)
    must satisfy this contract.
    """

    async def convert(
        self,
        file_path: str,
        options: ConversionOptions,
        *,
        page_range: tuple[int, int] | None = None,
    ) -> ConversionResult: ...

    @property
    def supports_page_batching(self) -> bool:
        """True if the orchestrator may slice a long document into page
        batches (calling `convert` with a `page_range`) and merge the
        results. Local in-process converters set this to True; remote
        converters that handle batching themselves return False so the
        orchestrator passes the full document through in one call."""
        ...

    async def merge_batches(self, results: list[ConversionResult]) -> ConversionResult:
        """Merge the results of page-batched `convert` calls, in page order,
        into the result a single call would have produced. Only called when
        `supports_page_batching` is True."""
        ...


class DoclingDocumentImporter(Protocol):
    """Port for normalizing a serialized Docling document into domain data."""

    def deserialize(self, document: dict[str, Any]) -> ConversionResult: ...


class DocumentChunker(Protocol):
    """Port for document chunking.

    Takes a serialized DoclingDocument (JSON) and returns chunks.
    """

    async def chunk(
        self,
        document_json: str,
        options: ChunkingOptions,
    ) -> list[ChunkResult]: ...


class DocumentRepository(Protocol):
    """Port for document persistence."""

    async def insert(self, doc: Document) -> None: ...

    async def find_all(
        self, *, limit: int = 200, offset: int = 0, filename_like: str | None = None
    ) -> list[Document]: ...

    async def find_by_id(self, doc_id: str) -> Document | None: ...

    async def find_by_ids(self, doc_ids: list[str]) -> dict[str, Document]:
        """The requested documents keyed by id, in one read; missing ids are absent."""
        ...

    async def update_page_count(self, doc_id: str, page_count: int) -> None: ...

    async def update_lifecycle(
        self,
        doc_id: str,
        state: DocumentLifecycleState,
        at: datetime,
    ) -> None: ...

    async def delete(self, doc_id: str) -> bool: ...


class StoreRepository(Protocol):
    """Port for `Store` persistence (introduced by #203).

    The connection password never travels on the `Store` entity: it is
    written through `insert(..., password=)` / `set_connection_password`
    and read back only through `get_connection_password` (#279).
    """

    async def insert(self, store: Store, *, password: str | None = None) -> None: ...

    async def find_all(self) -> list[Store]: ...

    async def find_by_slug(self, slug: str) -> Store | None: ...

    async def find_by_id(self, store_id: str) -> Store | None: ...

    async def find_by_name(self, name: str) -> Store | None: ...

    async def get_default(self) -> Store | None: ...

    async def update(self, store: Store) -> None:
        """Replace the mutable, non-secret fields; never touches the password."""
        ...

    async def clear_default_except(self, store_id: str) -> None:
        """Unset `is_default` on every store but `store_id` (single-default invariant)."""
        ...

    async def delete(self, store_id: str) -> bool: ...

    async def get_connection_password(self, store_id: str) -> str | None:
        """The plaintext password, or None when none is set. Never log it."""
        ...

    async def set_connection_password(self, store_id: str, plaintext: str | None) -> bool:
        """Seal and store `plaintext` (None clears it). False for an unknown store."""
        ...


class DocumentStoreLinkRepository(Protocol):
    """Port for `DocumentStoreLink` persistence (introduced by #203)."""

    async def upsert(self, link: DocumentStoreLink) -> None:
        """Insert or update by (document_id, store_id)."""
        ...

    async def find_for_document(self, document_id: str) -> list[DocumentStoreLink]: ...

    async def find_for_store(self, store_id: str) -> list[DocumentStoreLink]: ...

    async def count_by_store(self) -> dict[str, int]:
        """Linked-document count per store id; stores without links are absent."""
        ...

    async def find_one(self, document_id: str, store_id: str) -> DocumentStoreLink | None: ...

    async def delete(self, document_id: str, store_id: str) -> bool: ...


class ChunkRepository(Protocol):
    """Port for first-class chunk persistence (introduced by #205)."""

    async def insert(self, chunk: Chunk) -> None: ...

    async def insert_many(self, chunks: list[Chunk]) -> None: ...

    async def update(self, chunk: Chunk) -> None: ...

    async def soft_delete(self, chunk_id: str, *, at: datetime) -> bool: ...

    async def replace_chunkset(
        self,
        document_id: str,
        *,
        at: datetime,
        retire_ids: Sequence[str] = (),
        add: Sequence[Chunk] = (),
        edits: Sequence[ChunkEdit] = (),
    ) -> None:
        """Soft-delete the live chunks `retire_ids` (at `at`), insert `add`
        and append `edits` to the audit log as one atomic write: either all
        of it lands or none of it does."""
        ...

    async def shift_sequences(self, document_id: str, *, from_sequence: int, at: datetime) -> int:
        """Move every live chunk at `sequence >= from_sequence` one slot up
        (touching `updated_at`); returns how many moved."""
        ...

    async def find_for_document(
        self,
        document_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[Chunk]: ...

    async def find_by_id(self, chunk_id: str) -> Chunk | None: ...

    async def count_for_document(self, document_id: str) -> int: ...


class ChunkEditRepository(Protocol):
    """Port for the immutable chunk_edits audit log (introduced by #205)."""

    async def insert(self, edit: ChunkEdit) -> None: ...

    async def find_for_document(
        self,
        document_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChunkEdit]: ...

    async def find_for_chunk(self, chunk_id: str) -> list[ChunkEdit]: ...


class ChunkPushRepository(Protocol):
    """Port for chunk_pushes snapshots (introduced by #205)."""

    async def insert(self, push: ChunkPush) -> None: ...

    async def find_by_id(self, push_id: str) -> ChunkPush | None: ...

    async def find_latest(self, document_id: str, store_id: str) -> ChunkPush | None: ...

    async def find_for_document(
        self,
        document_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChunkPush]:
        """Every push of the document, newest first."""
        ...

    async def count_for_document(self, document_id: str) -> int: ...


@dataclass(frozen=True)
class DocumentVersionEntry:
    """One row of a document's version history, as the history list needs it.

    `version.chunks_snapshot` is not loaded (None): the list only shows how
    many chunks each snapshot holds, which the store counts (`chunk_count`)
    rather than handing every snapshot over to be parsed.
    """

    version: DocumentVersion
    chunk_count: int


class DocumentVersionRepository(Protocol):
    """Port for the frozen (analysis, chunks) version history (#267)."""

    async def insert(self, version: DocumentVersion) -> None: ...

    async def find_by_id(self, version_id: str) -> DocumentVersion | None: ...

    async def list_for_document(self, document_id: str) -> list[DocumentVersionEntry]:
        """Every version of the document, newest first, without the snapshot
        bodies. A snapshot that is not a JSON array counts 0 chunks."""
        ...


class AnalysisRepository(Protocol):
    """Port for analysis job persistence."""

    async def insert(self, job: AnalysisJob) -> None: ...

    async def find_all(self, *, limit: int = 200, offset: int = 0) -> list[AnalysisJob]: ...

    async def find_all_summaries(self, *, limit: int = 200, offset: int = 0) -> list[AnalysisJob]:
        """Like `find_all`, without the content: to follow statuses (#354)."""
        ...

    async def find_by_id(self, job_id: str) -> AnalysisJob | None: ...

    async def find_by_document(
        self, document_id: str, *, limit: int = 200, offset: int = 0
    ) -> list[AnalysisJob]:
        """The document's analysis jobs, newest first."""
        ...

    async def find_latest_completed(self, document_id: str) -> AnalysisJob | None: ...

    async def find_latest_completed_by_document(self, document_id: str) -> AnalysisJob | None: ...

    # The parse lookups below read ids and one column, never whole rows: a
    # row carries the docling JSON, the HTML and the markdown.
    async def latest_parsed_ids(self, document_ids: list[str]) -> dict[str, str]: ...

    async def parsed_document_id(self, job_id: str) -> str | None: ...

    async def parse_json(self, job_id: str) -> str | None: ...

    async def update_status(self, job: AnalysisJob) -> None: ...

    async def update_progress(self, job_id: str, current: int, total: int) -> None: ...

    async def update_chunks(self, job_id: str, chunks_json: str) -> bool: ...

    async def delete(self, job_id: str) -> bool: ...

    async def delete_by_document(self, document_id: str) -> int: ...


@runtime_checkable
class EmbeddingService(Protocol):
    """Port for text-to-vector embedding.

    Implementations may call a local model, a remote microservice, etc.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Port for vector storage and retrieval.

    Implementations (OpenSearch, pgvector, Qdrant, etc.) must satisfy this
    contract. The port uses domain types from vector_schema — no infrastructure
    details leak into the domain.
    """

    async def ensure_index(self, index_name: str, mapping: dict) -> None:
        """Create the index if it does not exist. No-op if it already exists."""
        ...

    async def index_chunks(self, index_name: str, chunks: list[IndexedChunk]) -> int:
        """Bulk-index a list of chunks. Returns the number of successfully indexed chunks."""
        ...

    async def search_similar(
        self,
        index_name: str,
        embedding: list[float],
        *,
        k: int = 10,
        doc_id: str | None = None,
    ) -> list[SearchResult]:
        """Find the k nearest chunks by embedding similarity.

        Args:
            index_name: Target index.
            embedding: Query vector.
            k: Number of results to return.
            doc_id: If provided, restrict search to chunks from this document.
        """
        ...

    async def search_fulltext(
        self,
        index_name: str,
        query_text: str,
        *,
        k: int = 10,
        doc_id: str | None = None,
    ) -> list[SearchResult]:
        """Find the k best chunks for `query_text` by full-text match on
        their content, optionally restricted to one document."""
        ...

    async def get_chunks(
        self,
        index_name: str,
        doc_id: str,
        *,
        limit: int = 1000,
    ) -> list[SearchResult]:
        """Retrieve all indexed chunks for a given document, ordered by chunk_index."""
        ...

    async def delete_document(self, index_name: str, doc_id: str) -> int:
        """Delete all chunks for a document from the index. Returns count deleted."""
        ...

    async def ping(self) -> bool:
        """Cheap reachability probe — True if the backing store responds.
        Used by health checks; should not throw."""
        ...


class VectorStorePool(Protocol):
    """Port for the per-connection vector store cache (#279).

    Hands back the `VectorStore` for one `(url, username)` identity,
    building it on first use. Ingestion-only surface, deprecated with it.
    """

    async def get(
        self,
        url: str,
        *,
        username: str | None = None,
        password: str | None = None,
    ) -> VectorStore: ...


class GraphDriverPool(Protocol):
    """Port for the per-connection graph driver cache (#279).

    The driver is opaque to the services: it only travels to the injected
    `GraphWriter` factory. Ingestion-only surface, deprecated with it.
    """

    async def get(
        self,
        uri: str,
        user: str,
        password: str,
        *,
        database: str = "neo4j",
    ) -> Any: ...


class AppSettingsRepository(Protocol):
    """Port for the namespaced runtime-config override store (#317).

    Values are opaque TEXT — the consuming service owns (de)serialization.
    `reasoning` is the first namespace; the table is groundwork for future
    runtime-configurable domains.
    """

    async def get_namespace(self, namespace: str) -> dict[str, str]: ...

    async def set_many(self, namespace: str, values: dict[str, str]) -> None: ...

    async def delete_namespace(self, namespace: str) -> int:
        """Drop every override in `namespace`. Returns the number of rows removed."""
        ...

    async def replace_namespace(self, namespace: str, values: dict[str, str]) -> None:
        """Make `values` the whole override set of `namespace`, in one
        transaction: keys absent from `values` lose their row (#364)."""
        ...


@runtime_checkable
class LLMHostProbe(Protocol):
    """Port for probing an LLM host: reachability + installed models (#317).

    Implementations must never raise — transport/protocol failures map to
    `LLMHostProbeResult(reachable=False, error=...)` so the API layer can
    return a plain 200 carrying the outcome.
    """

    async def probe(self, host: str) -> LLMHostProbeResult: ...


@runtime_checkable
class LLMProvider(Protocol):
    """Where the reasoning runner finds its LLM: the host and the default model.

    The runner consumes a provider, it does not build one. The only backend
    is Ollama (`OllamaProvider`, in `infra/llm/`): docling-agent drives
    Ollama alone, so there is no backend to tell apart and the port carries
    no type tag. A second backend needs docling-agent upstream support
    first (https://github.com/docling-project/docling-agent/issues/26).
    """

    @property
    def host(self) -> str: ...

    @property
    def default_model_id(self) -> str: ...


@runtime_checkable
class DocumentTreeReader(Protocol):
    """Port for walking a `DoclingDocument` JSON tree (#audit-01).

    Exposes the Docling-shape navigation primitives (item iteration,
    inline-group filter, collapse index for nested structures) so callers
    in `services/` can stay format-agnostic and never reach into
    `infra/docling_tree.py` directly. The adapter encapsulates every
    Docling-specific assumption (label taxonomy, parent.$ref/cref shape,
    InlineGroup collapsing, etc.).
    """

    def iter_items(self, doc_data: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield `(source_list_key, item)` for every item in
        texts/tables/pictures/groups."""
        ...

    def is_inline_group(self, item: dict[str, Any]) -> bool:
        """True iff `item` is a Docling InlineGroup (paragraph of mixed
        style runs collapsed into a single Paragraph projection)."""
        ...

    def build_collapse_index(
        self, doc_data: dict[str, Any]
    ) -> tuple[set[str], dict[str, dict[str, Any]]]:
        """Return `(skip_refs, inline_meta)` — refs to omit from any
        projection and per-InlineGroup aggregated metadata (text + provs).
        """
        ...

    def dfs_order(self, doc_data: dict[str, Any], skip_refs: set[str] | None = None) -> list[str]:
        """Return `self_ref`s in reading order (DFS pre-order from body),
        omitting `skip_refs`."""
        ...

    def iter_provs(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten an item's provenance into rows carrying `page_no`,
        `bbox_l/t/r/b`, `coord_origin` and the char span."""
        ...

    def iter_pages(self, doc_data: dict[str, Any]) -> Iterator[dict[str, Any]]:
        """Yield `{page_no, width, height}` for every page of the parse."""
        ...


@runtime_checkable
class PageRasterizer(Protocol):
    """Port for turning a stored document into page images.

    Rasterising is infrastructure — poppler, PIL, a file on disk — while the
    dpi ladder and the byte budget that drive it are policy. The split runs
    here: the adapter renders and crops what it is told to, the service
    decides what to ask for.
    """

    def render_page(self, storage_path: str, *, page: int, dpi: int) -> bytes:
        """Return `page` of the document at `storage_path` as PNG bytes.

        Raises `FileNotFoundError` when nothing is stored at `storage_path`,
        and `ValueError` when the document has no such page; any other
        exception means the file could not be rendered. Callers tell the cases
        apart by these types: a page the document lacks is not a broken file.
        """
        ...

    def crop(
        self,
        png: bytes,
        box: tuple[int, int, int, int],
        *,
        fmt: str = "PNG",
    ) -> RasterCrop:
        """Crop a PNG to `box` (left, top, right, bottom in pixels), clamped
        to the image, and re-encode it as `fmt` (`"PNG"` or `"WEBP"`)."""
        ...


@runtime_checkable
class PageTextReader(Protocol):
    """Port for reading a stored PDF's text layer, character by character.

    Where each character sits is infrastructure — pdfium, a file on disk —
    while finding a quote among them is domain logic (`domain.quote_marks`).
    """

    def glyphs(self, storage_path: str, *, page: int) -> list[Glyph]:
        """Every character of `page`, in the text layer's order, each with its
        box as fractions of the page from the top-left corner. Empty for a
        page it cannot place characters on (a rotated page, a scan)."""
        ...


@runtime_checkable
class GraphReader(Protocol):
    """Port for reading a document's graph projection from the graph store.

    Returns a wire-ready `GraphPayload` — the adapter owns both the query
    and the shape conversion so the service layer never sees driver types.
    Returns `None` when the document is unknown to the graph store.
    """

    async def fetch(self, doc_id: str, *, max_pages: int = 200) -> GraphPayload | None: ...


@runtime_checkable
class GraphWriter(Protocol):
    """Port for writing a document and its chunks into a graph store.

    Two distinct write paths exist by design: `write_document_tree` runs
    after analysis (full DoclingDocument tree), `write_chunks` runs after
    ingestion (chunks linked to the tree). Adapters that don't support
    both paths still must implement them (raise `NotImplementedError`
    rather than silently no-op so the caller can decide whether to fail).

    `ping()` mirrors the `VectorStore` port for the test-connection use
    case — `StoreService.test_connection` calls it through the resolver-
    produced `IngestionTargets.graph_writer` so the service layer never
    needs to touch the underlying driver.
    """

    async def write_document_tree(
        self,
        *,
        doc_id: str,
        filename: str,
        document_json: str,
    ) -> None: ...

    async def write_chunks(
        self,
        *,
        doc_id: str,
        chunks_json: str,
    ) -> None: ...

    async def ping(self) -> bool:
        """Cheap reachability probe — True if the graph store responds.
        Should not throw on connection failure; let the adapter map errors
        into False so the caller can return a clean (ok=False, reason)."""
        ...


@runtime_checkable
class ReasoningRunner(Protocol):
    """Port for live reasoning over a previously-converted document.

    Takes the serialized DoclingDocument JSON + a user query + optional
    per-call model override, returns a `ReasoningResult` (answer + iteration
    trace + convergence flag).

    Adapters MUST translate upstream parsing failures into
    `ReasoningParseError`. Other exceptions propagate as-is — the API layer
    maps them to 5xx.
    """

    @property
    def is_available(self) -> bool:
        """True if the runner can serve requests (deps importable + provider
        wired). Used by the API layer to short-circuit with a 503 instead of
        attempting a doomed call."""
        ...

    async def run(
        self,
        *,
        document_json: str,
        query: str,
        model_id: str | None = None,
    ) -> ReasoningResult:
        """Execute the reasoning loop. `model_id` overrides the provider's
        default for this call only."""
        ...


@runtime_checkable
class PdfInspector(Protocol):
    """Port for reading a stored PDF's geometry: how many pages, how big.

    Opening a PDF is infrastructure — a library, a file on disk, a lock the
    library needs — while what to do with an unreadable one is the caller's
    policy. Both methods raise `FileNotFoundError` when nothing is stored at
    `storage_path`, and another exception when the file is not a readable PDF.
    """

    def page_count(self, storage_path: str) -> int:
        """Number of pages of the PDF at `storage_path`."""
        ...

    def page_sizes(self, storage_path: str) -> list[PageDetail]:
        """Width and height of each page, in points, numbered from 1, without
        any element."""
        ...


@runtime_checkable
class FileStorage(Protocol):
    """Port for the uploaded files: written once, found again, removed.

    A file is named by the storage path its document record keeps. Writing
    it, finding it after the upload directory moved (a record written in the
    Docker image, read from a worktree on the host) and keeping removals
    inside the storage are infrastructure; what a missing or unremovable file
    means is the caller's policy. Every method touches the disk: async
    callers run it in a worker thread.
    """

    def save(self, content: bytes, *, suffix: str) -> str:
        """Store `content` under a fresh name ending in `suffix`; return its
        absolute storage path."""
        ...

    def exists(self, storage_path: str) -> bool:
        """Whether a file is stored at `storage_path`, read as recorded."""
        ...

    def resolve(self, storage_path: str) -> str:
        """Where the file recorded at `storage_path` can be read now: that
        path when a file is there, else a file of the same name in the
        storage, else `storage_path` itself (the read then fails)."""
        ...

    def delete(self, storage_path: str) -> None:
        """Remove the file at `storage_path`, when one is there.

        Never removes anything outside the storage, whatever the path says
        (`..`, a symlink): such a path is refused and logged, not raised.
        Raises `OSError` when the removal itself fails.
        """
        ...
