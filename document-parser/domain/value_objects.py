"""Domain value objects — pure data structures for document conversion.

These types define the contract between the domain and infrastructure layers.
They have ZERO external dependencies (no docling, no HTTP, no DB).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# US Letter page dimensions (points) — fallback when page size is unknown
DEFAULT_PAGE_WIDTH: float = 612.0
DEFAULT_PAGE_HEIGHT: float = 792.0


class DocumentLifecycleState(StrEnum):
    """Canonical lifecycle of a Document in Docling Studio.

    Distinct from `AnalysisStatus` (which describes a single conversion
    attempt). The lifecycle describes the document as a whole:

      Uploaded   raw file persisted, no parse yet
      Parsed     conversion produced a document tree
      Chunked    chunker produced a draft chunkset (pre-store)
      Ingested   chunkset has been embedded into at least one store
      Stale      a chunkset was edited after a successful push and the
                 corresponding store no longer matches (#204)
      Failed     a pipeline step failed; recoverable by retry

    Allowed transitions live in `domain.lifecycle._TRANSITIONS`.
    """

    UPLOADED = "Uploaded"
    PARSED = "Parsed"
    CHUNKED = "Chunked"
    INGESTED = "Ingested"
    STALE = "Stale"
    FAILED = "Failed"


class StoreKind(StrEnum):
    """Backing technology of a Store. Today only OpenSearch is implemented;
    the enum is here so future backends (Pinecone, Qdrant, pgvector) can be
    added without touching the persistence schema."""

    OPENSEARCH = "opensearch"


class DocumentStoreLinkState(StrEnum):
    """State of a (document, store) ingestion link.

    Distinct from `DocumentLifecycleState` — the document lifecycle is the
    aggregate over all per-store links. A link is `Ingested` when its
    chunkset hash matches the source; `Stale` when the source has drifted
    after the last push; `Failed` when the last push attempt errored.
    """

    INGESTED = "Ingested"
    STALE = "Stale"
    FAILED = "Failed"


@dataclass(frozen=True)
class PageElement:
    type: str
    bbox: list[float]
    content: str
    level: int = 0
    # Docling `self_ref` ("#/texts/12", "#/tables/3", …). Empty for items
    # that don't have one (rare — defensive default). Lets callers correlate
    # a rendered bbox with the corresponding node in the graph without
    # resorting to fuzzy bbox matching.
    self_ref: str = ""


@dataclass(frozen=True)
class PageDetail:
    page_number: int
    width: float
    height: float
    elements: list[PageElement] = field(default_factory=list)


@dataclass(frozen=True)
class ConversionOptions:
    do_ocr: bool = True
    do_table_structure: bool = True
    table_mode: str = "accurate"
    do_code_enrichment: bool = False
    do_formula_enrichment: bool = False
    do_picture_classification: bool = False
    do_picture_description: bool = False
    generate_picture_images: bool = False
    generate_page_images: bool = False
    images_scale: float = 1.0

    def is_default(self) -> bool:
        """Return True if all options match their defaults."""
        return self == ConversionOptions()


@dataclass(frozen=True)
class ConversionResult:
    page_count: int
    content_markdown: str
    content_html: str
    pages: list[PageDetail]
    skipped_items: int = 0
    document_json: str | None = None


@dataclass(frozen=True)
class ChunkingOptions:
    chunker_type: str = "hybrid"  # "hybrid", "hierarchical", "page"
    max_tokens: int = 512
    merge_peers: bool = True
    repeat_table_header: bool = True

    def is_default(self) -> bool:
        """Return True if all options match their defaults."""
        return self == ChunkingOptions()


@dataclass(frozen=True)
class ChunkBbox:
    page: int
    bbox: list[float]  # [left, top, right, bottom] in TOPLEFT origin


@dataclass(frozen=True)
class ChunkDocItem:
    """Source element referenced by a chunk. Enables Neo4j DERIVED_FROM edges."""

    self_ref: str
    label: str


@dataclass(frozen=True)
class ChunkResult:
    text: str
    headings: list[str] = field(default_factory=list)
    source_page: int | None = None
    token_count: int = 0
    bboxes: list[ChunkBbox] = field(default_factory=list)
    doc_items: list[ChunkDocItem] = field(default_factory=list)


# --- Reasoning (live docling-agent runner) -----------------------------------


class LLMProviderType(StrEnum):
    """LLM backends the reasoning runner can talk to.

    Today only OLLAMA is realizable: docling-agent v0.1.0 is hardwired to
    Ollama via mellea's `setup_local_session`. Other variants are kept here
    to make the abstraction visible and prepare future backends — adding one
    requires either docling-agent upstream support (see
    https://github.com/docling-project/docling-agent/issues/26) or a fork.
    """

    OLLAMA = "ollama"


@dataclass(frozen=True)
class ReasoningIteration:
    """One step of the reasoning loop — section the agent visited and what
    it concluded. Mirrors the upstream docling-agent `RAGIteration` shape so
    serialization stays 1:1 with externally-produced traces."""

    iteration: int
    section_ref: str
    reason: str
    section_text_length: int
    can_answer: bool
    response: str


@dataclass(frozen=True)
class ReasoningResult:
    """Full output of a reasoning run: final answer, the path the agent
    walked through the document, and whether the loop converged."""

    answer: str
    iterations: list[ReasoningIteration]
    converged: bool
