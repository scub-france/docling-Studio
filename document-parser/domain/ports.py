"""Domain ports — abstract interfaces that infrastructure must implement.

These protocols define what the domain NEEDS, not how it's done.
Infrastructure adapters (local Docling, Docling Serve, etc.) implement these.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from domain.analysis_editing import (
        EditCommand,
        EditedAnalysisCache,
        EditorSnapshot,
        EditStream,
        ProjectedAnalysis,
        StoredEditCommand,
    )
    from domain.app_config import LLMHostProbeResult
    from domain.models import (
        AnalysisJob,
        Chunk,
        ChunkPush,
        ChunkReplacement,
        Document,
        DocumentAnalysisState,
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

    async def find_by_ids(self, doc_ids: list[str]) -> dict[str, Document]: ...

    async def update_page_count(self, doc_id: str, page_count: int) -> None: ...

    async def update_lifecycle(
        self,
        doc_id: str,
        state: DocumentLifecycleState,
        at: datetime,
    ) -> None: ...

    async def delete(self, doc_id: str) -> bool: ...


@runtime_checkable
class DocumentFileStore(Protocol):
    """Port for the files uploaded documents are stored in.

    A `storage_path` is the string a `Document` persists. Every method blocks
    on the filesystem: callers decide which calls leave the event loop.
    """

    def save(self, file_name: str, content: bytes) -> str:
        """Write `content` as `file_name` in the upload directory, creating the
        directory if needed, and return the absolute path it was stored at."""
        ...

    def discard(self, storage_path: str) -> None:
        """Remove a file `save` just returned, while the upload that wrote it
        is still running. Raises `OSError` when it cannot."""
        ...

    def delete(self, storage_path: str) -> None:
        """Remove a stored document's file, but only when it lies inside the
        upload directory. Logs every refusal or failure; never raises."""
        ...

    def has_file(self, storage_path: str) -> bool:
        """Whether `storage_path` is an existing regular file."""
        ...

    def resolve(self, storage_path: str) -> str:
        """The path to read a stored document from: `storage_path` when the
        file exists, else the file of the same name in the upload directory
        when that one exists (a Docker path read on the host), else
        `storage_path` unchanged."""
        ...

    def read_fingerprint(self, storage_path: str) -> tuple[int, int]:
        """The file's size in bytes and modification time in nanoseconds.
        Raises `FileNotFoundError` when the file is missing."""
        ...


# Source path, byte size, modification time, page, DPI, and image format.
type PreviewImageKey = tuple[str, int, int, int, int, str]


class PreviewImageCache(Protocol):
    """Store rendered page images under an immutable source/page key."""

    def get(self, key: PreviewImageKey) -> bytes | None: ...

    def put(self, key: PreviewImageKey, image: bytes) -> None: ...


class DocumentAnalysisStateRepository(Protocol):
    """Reads the `DocumentAnalysisState` aggregate (02-2.4.3).

    Its two parts are written by the writers that change them, in their own
    transaction: `AnalysisRepository.complete_and_select` and
    `AnalysisRepository.delete` (selection), `ChunkRepository.replace_and_select`
    (chunk source and selection, on restore) and
    `ChunkRepository.replace_keeping_selection` (chunk source, on rechunk).
    """

    async def find_state(self, document_id: str) -> DocumentAnalysisState | None:
        """The document's state, or None when it has no state row at all."""
        ...

    async def find_states(self, document_ids: list[str]) -> dict[str, DocumentAnalysisState]:
        """The states of the documents that have a row, in one query."""
        ...


class CurrentAnalysisReader(Protocol):
    """Which analysis is a document's current one (02-2.3.1).

    One rule, `domain.models.resolve_current_analysis_id`, for every reader
    that picks an analysis without being told which. Implemented by
    `services.current_analysis.CurrentAnalysisResolver`.
    """

    async def find_current_analysis_id(self, document_id: str) -> str | None: ...

    async def find_current_parse_ids(self, document_ids: list[str]) -> dict[str, str]:
        """Each document's current analysis when it has a parse, in a fixed
        number of queries whatever the count."""
        ...

    async def load_current_original(self, document_id: str) -> AnalysisJob | None:
        """The current analysis as stored: the original result, without edits.

        `ActiveAnalysisResultReader.load_current_edited` reads the same
        analysis with its saved edits."""
        ...


class StoreRepository(Protocol):
    """Port for `Store` persistence (introduced by #203)."""

    async def insert(self, store: Store, *, password: str | None = None) -> None: ...

    async def find_all(self) -> list[Store]: ...

    async def find_by_slug(self, slug: str) -> Store | None: ...

    async def find_by_id(self, store_id: str) -> Store | None: ...

    async def find_by_name(self, name: str) -> Store | None: ...

    async def update(self, store: Store) -> None: ...

    async def clear_default_except(self, store_id: str) -> None: ...

    async def delete(self, store_id: str) -> bool: ...

    # Plaintext secret: never log or serialise it.
    async def get_connection_password(self, store_id: str) -> str | None: ...

    async def set_connection_password(self, store_id: str, plaintext: str | None) -> bool: ...


class DocumentStoreLinkRepository(Protocol):
    """Port for `DocumentStoreLink` persistence (introduced by #203)."""

    async def upsert(self, link: DocumentStoreLink) -> None:
        """Insert or update by (document_id, store_id)."""
        ...

    async def find_for_document(self, document_id: str) -> list[DocumentStoreLink]: ...

    async def find_for_store(self, store_id: str) -> list[DocumentStoreLink]: ...

    async def count_by_store(self) -> dict[str, int]: ...

    async def find_one(self, document_id: str, store_id: str) -> DocumentStoreLink | None: ...

    async def delete(self, document_id: str, store_id: str) -> bool: ...


class ChunkRepository(Protocol):
    """Port for first-class chunk persistence (introduced by #205)."""

    async def insert(self, chunk: Chunk) -> None: ...

    async def insert_many(self, chunks: list[Chunk]) -> None: ...

    async def update(self, chunk: Chunk) -> None: ...

    async def soft_delete(self, chunk_id: str, *, at: datetime) -> bool: ...

    async def soft_delete_many(self, chunk_ids: list[str], *, at: datetime) -> int: ...

    async def replace_and_select(self, replacement: ChunkReplacement) -> int:
        """Soft-delete the live chunks, insert `replacement.chunks` and write the
        document's analysis state, in one transaction. Returns how many chunks
        were soft-deleted. Used by a restore.

        `replacement.chunk_source` is recorded as given (None forgets it).
        `replacement.active_analysis_id` becomes the active analysis (None
        clears an existing selection).

        Raises:
            ValueError: `replacement.chunk_source` belongs to another document.
            AnalysisNotSelectableError: the analysis to select is gone or
                belongs to another document; nothing is written.
        """
        ...

    async def replace_keeping_selection(self, replacement: ChunkReplacement) -> int:
        """Soft-delete the live chunks, insert `replacement.chunks` and record
        `replacement.chunk_source`, in one transaction, keeping the document's
        selection. Returns how many chunks were soft-deleted. Used by a rechunk.

        `replacement.chunk_source` is recorded as given (None forgets it). A
        rechunk never changes an existing selection: an analysis that became
        active while the chunker ran stays active, and the new chunks report
        stale against it. `replacement.active_analysis_id`, the chunked
        analysis, only goes into a state row this write creates, so a document
        without one keeps the analysis the fallback rule gave it.

        Raises:
            ValueError: `replacement.chunk_source` belongs to another document.
            AnalysisNotSelectableError: the analysis to select is gone or
                belongs to another document; nothing is written.
        """
        ...

    async def shift_sequences(
        self,
        document_id: str,
        *,
        from_sequence: int,
        at: datetime,
        by: int = 1,
    ) -> int: ...

    async def find_for_document(
        self,
        document_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[Chunk]: ...

    async def find_by_id(self, chunk_id: str) -> Chunk | None: ...

    async def count_for_document(self, document_id: str) -> int: ...


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
    ) -> list[ChunkPush]: ...

    async def count_for_document(self, document_id: str) -> int: ...


class DocumentVersionRepository(Protocol):
    """Port for frozen (analysis, chunks) document versions (#267)."""

    async def insert(self, version: DocumentVersion) -> None: ...

    async def find_by_id(self, version_id: str) -> DocumentVersion | None: ...

    async def find_for_document(self, document_id: str) -> list[DocumentVersion]: ...


class AnalysisRepository(Protocol):
    """Port for analysis job persistence."""

    async def insert(self, job: AnalysisJob) -> None: ...

    async def find_all(self, *, limit: int = 200, offset: int = 0) -> list[AnalysisJob]: ...

    async def find_all_summaries(self, *, limit: int = 200, offset: int = 0) -> list[AnalysisJob]:
        """Like `find_all`, without the content: to follow statuses (#354)."""
        ...

    async def find_summaries_by_document(self, document_id: str) -> list[AnalysisJob]:
        """Every analysis of one document, without the content and uncapped."""
        ...

    async def find_by_id(self, job_id: str) -> AnalysisJob | None: ...

    async def find_by_document(
        self, document_id: str, *, limit: int = 200, offset: int = 0
    ) -> list[AnalysisJob]: ...

    # The parse lookups below read ids and one column, never whole rows: a
    # row carries the docling JSON, the HTML and the markdown.
    async def find_latest_parsed_ids(self, document_ids: list[str]) -> dict[str, str]:
        """Only the fallback of `resolve_current_analysis_id`: read it through
        `CurrentAnalysisReader`, never to pick a document's analysis."""
        ...

    async def find_parsed_document_id(self, job_id: str) -> str | None: ...

    async def find_parsed_ids(self, job_ids: list[str]) -> set[str]: ...

    async def parse_json(self, job_id: str) -> str | None: ...

    async def update_status(self, job: AnalysisJob) -> None: ...

    async def complete_and_select(self, job: AnalysisJob) -> None:
        """Persist a completed analysis and make it the active one, atomically."""
        ...

    async def update_progress(self, job_id: str, current: int, total: int) -> None: ...

    async def update_chunks(self, job_id: str, chunks_json: str) -> bool: ...

    async def delete(self, job_id: str) -> bool:
        """Delete an analysis; when it was the active one, select the latest
        remaining completed analysis with a Docling document, atomically."""
        ...

    async def delete_by_document(self, document_id: str) -> int: ...


class AnalysisEditRepository(Protocol):
    async def find_stream(self, analysis_id: str) -> EditStream | None: ...

    async def create_stream(self, stream: EditStream) -> None: ...

    async def list_commands(self, analysis_id: str) -> list[StoredEditCommand]: ...

    async def find_cache(self, analysis_id: str) -> EditedAnalysisCache | None: ...

    async def save_commands_and_cache(
        self,
        *,
        stream: EditStream,
        commands: list[EditCommand],
        expected_sequence: int,
        cache: EditedAnalysisCache,
    ) -> list[StoredEditCommand]:
        """Append `commands` and replace the working copy, in one transaction.

        The stream is stamped with `stream.engine_version`, the engine that
        projected this working copy.
        """
        ...


class ActiveAnalysisResultReader(Protocol):
    """Read the analysis result downstream features use, edits included.

    Implemented by the analysis editor service; chunking and export depend on
    this read side only.
    """

    async def load_current_edited(self, document_id: str) -> EditorSnapshot:
        """The document's current analysis with its saved edits.

        `CurrentAnalysisReader.load_current_original` reads the same analysis
        without them."""
        ...

    async def load_editor(
        self, document_id: str, analysis_id: str | None = None
    ) -> EditorSnapshot: ...


class AnalysisDocumentEngine(Protocol):
    """Apply editor commands to a canonical document and project the result (#394).

    The engine owns the document model (Docling): services only exchange the
    serialized base document, commands and `ProjectedAnalysis`. Both methods
    are CPU-bound and synchronous; callers run them in a worker thread.
    """

    def project(
        self,
        document_json: str,
        *,
        base_analysis_id: str,
        commands: list[EditCommand],
    ) -> ProjectedAnalysis:
        """Replay `commands` on the base document and project the edited result."""
        ...

    def project_serialized(
        self,
        document_json: str,
        *,
        base_analysis_id: str,
        editor_model_json: str,
    ) -> ProjectedAnalysis:
        """Project an already edited working copy without replaying commands."""
        ...


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
        """Full-text search on the chunk content, optionally within one document."""
        ...

    async def delete_document(self, index_name: str, doc_id: str) -> int:
        """Delete all chunks for a document from the index. Returns count deleted."""
        ...

    async def ping(self) -> bool:
        """Cheap reachability probe — True if the backing store responds.
        Used by health checks; should not throw."""
        ...


class VectorStorePool(Protocol):
    """Per-connection cache of vector store clients, keyed by `(url, username)` (#279)."""

    async def get(
        self,
        url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        verify_certs: bool = False,
    ) -> VectorStore: ...


class GraphDriverPool(Protocol):
    """Per-connection cache of graph store drivers, keyed by `(uri, user)` (#279).

    The driver stays opaque to services: it is handed straight to an injected
    `GraphWriter` factory.
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
    """Connection to the LLM host the reasoning runner talks to.

    A provider carries the host/base-URL and the default model identifier.
    The reasoning runner consumes a provider — it doesn't construct one.

    Only Ollama exists (`OllamaProvider` in `infra/llm/`): docling-agent is
    hardwired to it through mellea, so there is no backend type to dispatch
    on (04-4.2). A second backend needs docling-agent upstream support first
    (https://github.com/docling-project/docling-agent/issues/26).
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

    def list_dfs_order(
        self, doc_data: dict[str, Any], skip_refs: set[str] | None = None
    ) -> list[str]:
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

    def render_page(self, storage_path: str, *, page: int, dpi: int, fmt: str = "PNG") -> bytes:
        """Return `page` of the document at `storage_path` as `fmt` bytes:
        `"PNG"`, or `"WEBP"` encoded losslessly. Raises `FileNotFoundError`
        when the file is missing, `ValueError` when the page does not exist."""
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
class PdfInspector(Protocol):
    """Port for reading a stored PDF's page geometry, without rendering it."""

    def read_page_sizes(self, storage_path: str) -> list[PageDetail]:
        """Size of each page, in points, without elements. Raises
        `FileNotFoundError` when the file is missing."""
        ...

    def count_pages(self, storage_path: str) -> int:
        """Number of pages. Raises when the file is not a readable PDF."""
        ...

    def count_pages_in_bytes(self, content: bytes) -> int | None:
        """Number of pages of an uploaded PDF still in memory, or None when
        it cannot be read (damaged, locked, no PDF tool). Never raises."""
        ...


@runtime_checkable
class PageTextReader(Protocol):
    """Port for reading a stored PDF's text layer, character by character.

    Where each character sits is infrastructure — pdfium, a file on disk —
    while finding a quote among them is domain logic (`domain.quote_marks`).
    """

    def read_glyphs(self, storage_path: str, *, page: int) -> list[Glyph]:
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
