"""OpenSearch adapter implementing the VectorStore port.

Uses the opensearch-py client for kNN vector search, full-text search,
and document CRUD against an OpenSearch cluster.
"""

from __future__ import annotations

import logging
from typing import Any

from opensearchpy import AsyncOpenSearch, NotFoundError

from domain.vector_schema import (
    ChunkBboxEntry,
    ChunkOrigin,
    DocItemRef,
    IndexedChunk,
    SearchResult,
)

logger = logging.getLogger(__name__)


def _hit_to_indexed_chunk(hit: dict[str, Any]) -> IndexedChunk:
    """Reconstruct an IndexedChunk from an OpenSearch _source document."""
    src = hit["_source"]
    origin_raw = src.get("origin")
    origin = (
        ChunkOrigin(binary_hash=origin_raw["binary_hash"], filename=origin_raw["filename"])
        if origin_raw
        else None
    )
    return IndexedChunk(
        doc_id=src["doc_id"],
        filename=src["filename"],
        content=src["content"],
        embedding=src.get("embedding", []),
        chunk_index=src["chunk_index"],
        chunk_type=src["chunk_type"],
        page_number=src["page_number"],
        bboxes=[
            ChunkBboxEntry(page=b["page"], x=b["x"], y=b["y"], w=b["w"], h=b["h"])
            for b in src.get("bboxes", [])
        ],
        headings=src.get("headings", []),
        doc_items=[
            DocItemRef(self_ref=d["self_ref"], label=d["label"]) for d in src.get("doc_items", [])
        ],
        origin=origin,
    )


def _hit_to_result(hit: dict[str, Any]) -> SearchResult:
    """Convert an OpenSearch hit to a SearchResult."""
    return SearchResult(
        chunk=_hit_to_indexed_chunk(hit),
        score=hit.get("_score", 0.0),
    )


class OpenSearchStore:
    """Concrete VectorStore adapter backed by OpenSearch.

    Satisfies the ``VectorStore`` Protocol defined in ``domain.ports``.

    Args:
        url: OpenSearch cluster URL (e.g. ``http://localhost:9200``).
        verify_certs: Whether to verify TLS certificates.
        username: Optional HTTP basic-auth username (#279).
        password: Optional HTTP basic-auth password (#279). Required
            when `username` is set; ignored otherwise.
        default_limit: Cap on rows returned by paginated reads.
    """

    def __init__(
        self,
        url: str,
        *,
        verify_certs: bool = False,
        default_limit: int = 1000,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        http_auth = (username, password) if username is not None else None
        self._client = AsyncOpenSearch(
            hosts=[url],
            http_auth=http_auth,
            use_ssl=url.startswith("https"),
            verify_certs=verify_certs,
            ssl_show_warn=False,
        )
        self._default_limit = default_limit

    # -- lifecycle -------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.close()

    async def ping(self) -> bool:
        """Reachability probe — calls OpenSearch `/` (cluster info) once."""
        try:
            info = await self._client.info()
            return bool(info)
        except Exception:
            return False

    # -- VectorStore protocol methods ------------------------------------------

    async def ensure_index(self, index_name: str, mapping: dict) -> None:
        """Create the index if it does not exist. No-op if it already exists."""
        exists = await self._client.indices.exists(index=index_name)
        if not exists:
            await self._client.indices.create(index=index_name, body=mapping)
            logger.info("Created OpenSearch index '%s'", index_name)
        else:
            logger.debug("Index '%s' already exists — skipping creation", index_name)

    async def index_chunks(self, index_name: str, chunks: list[IndexedChunk]) -> int:
        """Bulk-index a list of chunks. Returns the number successfully indexed."""
        if not chunks:
            return 0

        body: list[dict[str, Any]] = []
        for chunk in chunks:
            doc_id = f"{chunk.doc_id}_{chunk.chunk_index}"
            body.append({"index": {"_index": index_name, "_id": doc_id}})
            body.append(chunk.to_dict())

        resp = await self._client.bulk(body=body, refresh="wait_for")

        errors = sum(1 for item in resp["items"] if item["index"].get("error"))
        indexed = len(chunks) - errors
        if errors:
            logger.warning("Bulk index to '%s': %d/%d failed", index_name, errors, len(chunks))
        return indexed

    async def search_similar(
        self,
        index_name: str,
        embedding: list[float],
        *,
        k: int = 10,
        doc_id: str | None = None,
    ) -> list[SearchResult]:
        """kNN search for the k nearest chunks by embedding similarity."""
        knn_query: dict[str, Any] = {
            "knn": {
                "embedding": {
                    "vector": embedding,
                    "k": k,
                },
            },
        }
        if doc_id:
            knn_query["knn"]["embedding"]["filter"] = {
                "term": {"doc_id": doc_id},
            }

        resp = await self._client.search(
            index=index_name,
            body={"size": k, "query": knn_query},
            _source_excludes=["embedding"],
        )
        return [_hit_to_result(hit) for hit in resp["hits"]["hits"]]

    async def get_chunks(
        self,
        index_name: str,
        doc_id: str,
        *,
        limit: int | None = None,
    ) -> list[SearchResult]:
        """Retrieve all indexed chunks for a document, ordered by chunk_index."""
        if limit is None:
            limit = self._default_limit
        resp = await self._client.search(
            index=index_name,
            body={
                "size": limit,
                "query": {"term": {"doc_id": doc_id}},
                "sort": [{"chunk_index": {"order": "asc"}}],
            },
            _source_excludes=["embedding"],
        )
        return [_hit_to_result(hit) for hit in resp["hits"]["hits"]]

    async def delete_document(self, index_name: str, doc_id: str) -> int:
        """Delete all chunks for a document. Returns the number deleted."""
        try:
            resp = await self._client.delete_by_query(
                index=index_name,
                body={"query": {"term": {"doc_id": doc_id}}},
                refresh=True,
            )
            deleted: int = resp.get("deleted", 0)
            return deleted
        except NotFoundError:
            return 0

    # -- full-text search (bonus from spec) ------------------------------------

    async def search_fulltext(
        self,
        index_name: str,
        query_text: str,
        *,
        k: int = 10,
        doc_id: str | None = None,
    ) -> list[SearchResult]:
        """Full-text search on the content field.

        This method is not part of the VectorStore protocol but is specified
        in the issue acceptance criteria.
        """
        must: list[dict[str, Any]] = [{"match": {"content": query_text}}]
        if doc_id:
            must.append({"term": {"doc_id": doc_id}})

        resp = await self._client.search(
            index=index_name,
            body={
                "size": k,
                "query": {"bool": {"must": must}},
            },
            _source_excludes=["embedding"],
        )
        return [_hit_to_result(hit) for hit in resp["hits"]["hits"]]
