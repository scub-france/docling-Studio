"""Vector index schema — data contract for OpenSearch ingestion and inspection.

This module defines the standard metadata schema for the vector index used by
the ingestion pipeline (0.4.0) and the inspection UI (0.5.0).

Field usage by milestone:
    ┌────────────┬────────────────────────┬───────────────────────────────┬──────────────┐
    │ Field      │ 0.4.0 (write)          │ 0.5.0 (read)                  │ Source       │
    ├────────────┼────────────────────────┼───────────────────────────────┼──────────────┤
    │ content    │ Full-text search       │ Chunk panel display           │ Docling std  │
    │ embedding  │ Indexed                │ kNN semantic search           │ Docling std  │
    │ doc_items  │ Indexed                │ Element type filtering        │ Docling std  │
    │ headings   │ Indexed                │ Section hierarchy display     │ Docling std  │
    │ origin     │ Indexed                │ Document provenance           │ Docling std  │
    │ bboxes     │ Written at ingestion   │ Chunk↔bbox highlight          │ Studio       │
    │ page_number│ Written at ingestion   │ Split view navigation         │ Studio       │
    │ chunk_index│ Written at ingestion   │ Chunk ordering in panel       │ Studio       │
    │ chunk_type │ Written at ingestion   │ Metadata panel                │ Studio       │
    │ doc_id     │ Document linking       │ Document list navigation      │ Studio       │
    │ filename   │ "My Documents" list    │ Display                       │ Studio       │
    └────────────┴────────────────────────┴───────────────────────────────┴──────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field

# -- Value objects for a single indexed chunk ----------------------------------

DEFAULT_EMBEDDING_DIMENSION = 384  # Granite Embedding 30M (sentence-transformers)
DEFAULT_INDEX_NAME = "docling-studio-chunks"


@dataclass(frozen=True)
class ChunkBboxEntry:
    """Bounding box for a chunk region on a specific page."""

    page: int
    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class DocItemRef:
    """Reference to a Docling DocItem (element in the document structure)."""

    self_ref: str
    label: str  # text, table, picture, list, etc.


@dataclass(frozen=True)
class ChunkOrigin:
    """Provenance metadata — links a chunk back to its source document binary."""

    binary_hash: str
    filename: str


@dataclass(frozen=True)
class IndexedChunk:
    """A single chunk ready to be indexed in the vector store.

    This is the domain-level representation of a document in the OpenSearch index.
    It combines Docling-standard fields (content, embedding, doc_items, headings,
    origin) with Docling Studio enriched fields (bboxes, page_number, chunk_index,
    chunk_type, doc_id, filename).
    """

    doc_id: str
    filename: str
    content: str
    embedding: list[float]
    chunk_index: int
    chunk_type: str  # text, table, picture, list, etc.
    page_number: int
    bboxes: list[ChunkBboxEntry] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    doc_items: list[DocItemRef] = field(default_factory=list)
    origin: ChunkOrigin | None = None

    def to_dict(self) -> dict:
        """Serialize to a dict matching the OpenSearch index mapping."""
        result: dict = {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "content": self.content,
            "embedding": self.embedding,
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type,
            "page_number": self.page_number,
            "bboxes": [
                {"page": b.page, "x": b.x, "y": b.y, "w": b.w, "h": b.h} for b in self.bboxes
            ],
            "headings": self.headings,
            "doc_items": [{"self_ref": d.self_ref, "label": d.label} for d in self.doc_items],
        }
        if self.origin:
            result["origin"] = {
                "binary_hash": self.origin.binary_hash,
                "filename": self.origin.filename,
            }
        return result


# -- Search result -------------------------------------------------------------


@dataclass(frozen=True)
class SearchResult:
    """A chunk returned from a vector store query."""

    chunk: IndexedChunk
    score: float  # similarity score (higher = more similar)


# -- Index mapping template ----------------------------------------------------


def build_index_mapping(embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION) -> dict:
    """Build the OpenSearch index mapping for the chunk index.

    Args:
        embedding_dimension: Vector dimension for the knn_vector field.
            Defaults to 384 (Granite Embedding 30M / all-MiniLM-L6-v2).
    """
    return {
        "settings": {
            "index": {
                "knn": True,
            },
        },
        "mappings": {
            "properties": _build_chunk_properties(embedding_dimension),
        },
    }


def _build_chunk_properties(embedding_dimension: int) -> dict:
    """The field mappings of one indexed chunk."""
    return {
        "doc_id": {"type": "keyword"},
        "filename": {"type": "keyword"},
        "content": {"type": "text", "analyzer": "standard"},
        "embedding": _build_embedding_field(embedding_dimension),
        "chunk_index": {"type": "integer"},
        "chunk_type": {"type": "keyword"},
        "page_number": {"type": "integer"},
        "bboxes": _build_bboxes_field(),
        "headings": {"type": "text"},
        "doc_items": {
            "type": "nested",
            "properties": {
                "self_ref": {"type": "keyword"},
                "label": {"type": "keyword"},
            },
        },
        "origin": {
            "type": "object",
            "properties": {
                "binary_hash": {"type": "keyword"},
                "filename": {"type": "keyword"},
            },
        },
    }


def _build_embedding_field(embedding_dimension: int) -> dict:
    """The k-NN vector field: HNSW graph on the faiss engine."""
    return {
        "type": "knn_vector",
        "dimension": embedding_dimension,
        "method": {
            "engine": "faiss",
            "name": "hnsw",
        },
    }


def _build_bboxes_field() -> dict:
    """The chunk's bounding boxes, one nested object per page region."""
    return {
        "type": "nested",
        "properties": {
            "page": {"type": "integer"},
            "x": {"type": "float"},
            "y": {"type": "float"},
            "w": {"type": "float"},
            "h": {"type": "float"},
        },
    }
