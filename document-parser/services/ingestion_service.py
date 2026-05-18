"""Ingestion service — orchestrates Docling → embedding → OpenSearch.

Chains the full ingestion pipeline:
1. Convert document via Docling (reuse existing analysis)
2. Chunk with selected strategy
3. Embed all chunk texts via EmbeddingService
4. Index into OpenSearch via VectorStore

Idempotent: re-ingesting a document deletes old chunks before re-indexing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.vector_schema import (
    ChunkBboxEntry,
    ChunkOrigin,
    IndexedChunk,
    build_index_mapping,
)

if TYPE_CHECKING:
    from domain.ports import EmbeddingService, VectorStore
    from services.store_backend_resolver import IngestionTargets

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for the ingestion pipeline."""

    index_name: str = "docling-studio-chunks"
    embedding_dimension: int = 384


@dataclass
class IngestionResult:
    """Result of an ingestion pipeline run."""

    doc_id: str
    chunks_indexed: int
    embedding_dimension: int


class IngestionService:
    """Orchestrates the embedding + indexing pipeline.

    The vector_store (OpenSearch) is optional (#199) — when None, the
    service runs in "Neo4j only" mode: chunks are still embedded so
    text-search semantics stay consistent, but indexed only in Neo4j
    via the `write_chunks` adapter. Search / full-text endpoints
    return empty results when no vector store is wired.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore | None,
        config: IngestionConfig | None = None,
        neo4j_driver=None,
    ) -> None:
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._config = config or IngestionConfig()
        self._neo4j = neo4j_driver

    async def ensure_index(self) -> None:
        """Ensure the vector index exists with the correct mapping.

        No-op when no vector store is configured (#199).
        """
        if self._vector_store is None:
            return
        mapping = build_index_mapping(self._config.embedding_dimension)
        await self._vector_store.ensure_index(self._config.index_name, mapping)

    async def ingest(
        self,
        doc_id: str,
        filename: str,
        chunks_json: str,
        *,
        binary_hash: str | None = None,
        targets: IngestionTargets | None = None,
    ) -> IngestionResult:
        """Run the embedding + indexing pipeline on pre-chunked data.

        Idempotent — deletes any existing chunks for the document
        before re-indexing.

        Args:
            doc_id: Unique document identifier.
            filename: Original filename.
            chunks_json: JSON-serialized list of chunk dicts.
            binary_hash: Optional hash of the source file for provenance.
            targets: Per-call override for the vector_store /
                neo4j_driver pair (#279). When None, the
                service-level backends are used — preserves the pre-
                #279 single-cluster path. When provided, per-store
                dispatch wins.

        Returns:
            IngestionResult with the number of chunks indexed.
        """
        vector_store, neo4j = self._resolve_call_targets(targets)
        await self._ensure_index_on(vector_store)

        chunks_data: list[dict] = json.loads(chunks_json)
        active_chunks = [c for c in chunks_data if not c.get("deleted")]
        if not active_chunks:
            logger.info("No active chunks for doc %s — skipping ingestion", doc_id)
            return IngestionResult(doc_id=doc_id, chunks_indexed=0, embedding_dimension=0)

        texts = [c["text"] for c in active_chunks]
        logger.info("Embedding %d chunks for doc %s", len(texts), doc_id)
        embeddings = await self._embedding.embed(texts)

        indexed_chunks = self._build_indexed_chunks(
            doc_id=doc_id,
            filename=filename,
            active_chunks=active_chunks,
            embeddings=embeddings,
            binary_hash=binary_hash,
        )

        indexed = await self._write_to_vector_store(vector_store, doc_id, indexed_chunks)
        await self._mirror_to_neo4j(neo4j, doc_id, chunks_json)

        return IngestionResult(
            doc_id=doc_id,
            chunks_indexed=indexed,
            embedding_dimension=len(embeddings[0]) if embeddings else 0,
        )

    # -- per-call helpers (extracted to keep `ingest` under the 30-line budget)

    def _resolve_call_targets(
        self, targets: IngestionTargets | None
    ) -> tuple[VectorStore | None, object | None]:
        """Pick between the call-level override and the service-level
        defaults. Returns `(vector_store, neo4j_driver)`."""
        if targets is None:
            return self._vector_store, self._neo4j
        return targets.vector_store, targets.neo4j_driver

    async def _ensure_index_on(self, vector_store: VectorStore | None) -> None:
        """Idempotent index bootstrap on the resolved vector store."""
        if vector_store is None:
            return
        mapping = build_index_mapping(self._config.embedding_dimension)
        await vector_store.ensure_index(self._config.index_name, mapping)

    def _build_indexed_chunks(
        self,
        *,
        doc_id: str,
        filename: str,
        active_chunks: list[dict],
        embeddings: list[list[float]],
        binary_hash: str | None,
    ) -> list[IndexedChunk]:
        origin = (
            ChunkOrigin(binary_hash=binary_hash or "", filename=filename) if binary_hash else None
        )
        indexed_chunks: list[IndexedChunk] = []
        for i, (chunk_data, embedding) in enumerate(zip(active_chunks, embeddings, strict=True)):
            bboxes = [
                ChunkBboxEntry(
                    page=b["page"],
                    x=b["bbox"][0] if b.get("bbox") else 0,
                    y=b["bbox"][1] if b.get("bbox") else 0,
                    w=(b["bbox"][2] - b["bbox"][0]) if b.get("bbox") and len(b["bbox"]) >= 4 else 0,
                    h=(b["bbox"][3] - b["bbox"][1]) if b.get("bbox") and len(b["bbox"]) >= 4 else 0,
                )
                for b in chunk_data.get("bboxes", [])
            ]
            indexed_chunks.append(
                IndexedChunk(
                    doc_id=doc_id,
                    filename=filename,
                    content=chunk_data["text"],
                    embedding=embedding,
                    chunk_index=i,
                    chunk_type=chunk_data.get("chunkType", "text"),
                    page_number=chunk_data.get("sourcePage", 0) or 0,
                    bboxes=bboxes,
                    headings=chunk_data.get("headings", []),
                    origin=origin,
                )
            )
        return indexed_chunks

    async def _write_to_vector_store(
        self,
        vector_store: VectorStore | None,
        doc_id: str,
        indexed_chunks: list[IndexedChunk],
    ) -> int:
        if vector_store is None:
            logger.info(
                "Vector store not configured — skipping OpenSearch index for doc %s (#199)",
                doc_id,
            )
            return len(indexed_chunks)
        deleted = await vector_store.delete_document(self._config.index_name, doc_id)
        if deleted:
            logger.info("Deleted %d old chunks for doc %s", deleted, doc_id)
        indexed = await vector_store.index_chunks(self._config.index_name, indexed_chunks)
        logger.info("Indexed %d/%d chunks for doc %s", indexed, len(indexed_chunks), doc_id)
        return indexed

    async def _mirror_to_neo4j(self, neo4j_driver, doc_id: str, chunks_json: str) -> None:
        if neo4j_driver is None:
            return
        try:
            from infra.neo4j import write_chunks

            await write_chunks(neo4j_driver, doc_id=doc_id, chunks_json=chunks_json)
        except Exception:
            logger.exception("Neo4j ChunkWriter failed for doc %s", doc_id)

    async def delete_document(self, doc_id: str) -> int:
        """Remove all indexed chunks for a document.

        Returns 0 when no vector store is configured (#199).
        """
        if self._vector_store is None:
            return 0
        return await self._vector_store.delete_document(self._config.index_name, doc_id)

    async def search(
        self,
        query: str,
        *,
        k: int = 10,
        doc_id: str | None = None,
    ) -> list:
        """Semantic search: embed the query then find nearest chunks.

        Returns an empty list when no vector store is configured (#199).
        """
        if self._vector_store is None:
            return []
        embeddings = await self._embedding.embed([query])
        return await self._vector_store.search_similar(
            self._config.index_name,
            embeddings[0],
            k=k,
            doc_id=doc_id,
        )

    async def search_fulltext(
        self,
        query: str,
        *,
        k: int = 20,
        doc_id: str | None = None,
    ) -> list:
        """Full-text keyword search in indexed chunks.

        Returns an empty list when no vector store is configured (#199).
        """
        if self._vector_store is None:
            return []
        return await self._vector_store.search_fulltext(
            self._config.index_name,
            query,
            k=k,
            doc_id=doc_id,
        )

    async def ping(self) -> bool:
        """Check if the underlying vector store is reachable.

        True when no vector store is wired (#199) — the service still
        accepts ingestion calls (Neo4j-only path), so reporting it as
        unreachable would be misleading.
        """
        if self._vector_store is None:
            return True
        try:
            return await self._vector_store.ping()
        except Exception:
            logger.debug("Vector store ping failed", exc_info=True)
            return False
