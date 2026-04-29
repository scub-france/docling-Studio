"""Domain ports — abstract interfaces that infrastructure must implement.

These protocols define what the domain NEEDS, not how it's done.
Infrastructure adapters (local Docling, Docling Serve, etc.) implement these.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from domain.models import AnalysisJob, Document
    from domain.value_objects import (
        ChunkingOptions,
        ChunkResult,
        ConversionOptions,
        ConversionResult,
        DocumentLifecycleState,
        LLMProviderType,
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

    async def find_all(self, *, limit: int = 200, offset: int = 0) -> list[Document]: ...

    async def find_by_id(self, doc_id: str) -> Document | None: ...

    async def update_page_count(self, doc_id: str, page_count: int) -> None: ...

    async def update_lifecycle(
        self,
        doc_id: str,
        state: DocumentLifecycleState,
        at: datetime,
    ) -> None: ...

    async def delete(self, doc_id: str) -> bool: ...


class AnalysisRepository(Protocol):
    """Port for analysis job persistence."""

    async def insert(self, job: AnalysisJob) -> None: ...

    async def find_all(self, *, limit: int = 200, offset: int = 0) -> list[AnalysisJob]: ...

    async def find_by_id(self, job_id: str) -> AnalysisJob | None: ...

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


@runtime_checkable
class LLMProvider(Protocol):
    """Connection-level abstraction over an LLM backend.

    A provider carries the host/base-URL, the default model identifier, and a
    type tag that adapters can dispatch on. The reasoning runner consumes a
    provider — it doesn't construct one — so the runner stays decoupled from
    Ollama-vs-OpenAI-vs-WatsonX wiring.

    Today only `OllamaProvider` (in `infra/llm/`) is implemented because
    docling-agent v0.1.0 is hardwired to Ollama via mellea's
    `setup_local_session`. Adding a non-Ollama provider requires either
    docling-agent upstream support or a fork (track
    https://github.com/docling-project/docling-agent/issues/26 + provider
    abstraction work upstream).
    """

    @property
    def type(self) -> LLMProviderType: ...

    @property
    def host(self) -> str: ...

    @property
    def default_model_id(self) -> str: ...

    def health_check(self) -> bool:
        """Lightweight reachability probe. Returns True if the provider looks
        usable. Implementations should be cheap (no model load, no inference).
        """
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
