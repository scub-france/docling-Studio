"""Tests for the OpenSearch adapter (infra.opensearch_store).

These tests mock the AsyncOpenSearch client to validate adapter logic
without requiring a running OpenSearch instance.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from domain.ports import VectorStore
from domain.vector_schema import (
    ChunkBboxEntry,
    ChunkOrigin,
    DocItemRef,
    IndexedChunk,
    SearchResult,
    build_index_mapping,
)
from infra.opensearch_store import OpenSearchStore, _hit_to_indexed_chunk, _hit_to_result

# -- Fixtures -----------------------------------------------------------------


def _make_chunk(
    doc_id: str = "doc-1",
    chunk_index: int = 0,
    content: str = "hello world",
    embedding: list[float] | None = None,
) -> IndexedChunk:
    return IndexedChunk(
        doc_id=doc_id,
        filename="test.pdf",
        content=content,
        embedding=embedding or [0.1, 0.2, 0.3],
        chunk_index=chunk_index,
        chunk_type="text",
        page_number=1,
        bboxes=[ChunkBboxEntry(page=1, x=0.0, y=0.0, w=100.0, h=50.0)],
        headings=["Chapter 1"],
        doc_items=[DocItemRef(self_ref="#/texts/0", label="text")],
        origin=ChunkOrigin(binary_hash="abc123", filename="test.pdf"),
    )


def _make_hit(
    doc_id: str = "doc-1",
    chunk_index: int = 0,
    score: float = 0.95,
    content: str = "hello world",
) -> dict:
    return {
        "_id": f"{doc_id}_{chunk_index}",
        "_score": score,
        "_source": {
            "doc_id": doc_id,
            "filename": "test.pdf",
            "content": content,
            "chunk_index": chunk_index,
            "chunk_type": "text",
            "page_number": 1,
            "bboxes": [{"page": 1, "x": 0.0, "y": 0.0, "w": 100.0, "h": 50.0}],
            "headings": ["Chapter 1"],
            "doc_items": [{"self_ref": "#/texts/0", "label": "text"}],
            "origin": {"binary_hash": "abc123", "filename": "test.pdf"},
        },
    }


@pytest.fixture
def store() -> OpenSearchStore:
    return OpenSearchStore("http://localhost:9200")


@pytest.fixture
def mock_client(store: OpenSearchStore) -> AsyncMock:
    client = AsyncMock()
    store._client = client
    return client


# -- Protocol satisfaction -----------------------------------------------------


class TestProtocolSatisfaction:
    def test_satisfies_vector_store_protocol(self) -> None:
        """OpenSearchStore structurally satisfies VectorStore Protocol."""
        store = OpenSearchStore("http://localhost:9200")
        assert isinstance(store, VectorStore)


# -- Hit deserialization -------------------------------------------------------


class TestHitDeserialization:
    def test_hit_to_indexed_chunk(self) -> None:
        hit = _make_hit()
        chunk = _hit_to_indexed_chunk(hit)
        assert isinstance(chunk, IndexedChunk)
        assert chunk.doc_id == "doc-1"
        assert chunk.content == "hello world"
        assert chunk.chunk_index == 0
        assert chunk.page_number == 1
        assert len(chunk.bboxes) == 1
        assert chunk.bboxes[0].w == 100.0
        assert len(chunk.doc_items) == 1
        assert chunk.doc_items[0].label == "text"
        assert chunk.origin is not None
        assert chunk.origin.binary_hash == "abc123"

    def test_hit_to_indexed_chunk_no_origin(self) -> None:
        hit = _make_hit()
        hit["_source"]["origin"] = None
        chunk = _hit_to_indexed_chunk(hit)
        assert chunk.origin is None

    def test_hit_to_indexed_chunk_missing_optional_fields(self) -> None:
        hit = _make_hit()
        del hit["_source"]["bboxes"]
        del hit["_source"]["headings"]
        del hit["_source"]["doc_items"]
        del hit["_source"]["origin"]
        chunk = _hit_to_indexed_chunk(hit)
        assert chunk.bboxes == []
        assert chunk.headings == []
        assert chunk.doc_items == []
        assert chunk.origin is None

    def test_hit_to_result(self) -> None:
        hit = _make_hit(score=0.87)
        result = _hit_to_result(hit)
        assert isinstance(result, SearchResult)
        assert result.score == 0.87
        assert result.chunk.doc_id == "doc-1"


# -- ensure_index --------------------------------------------------------------


class TestEnsureIndex:
    async def test_creates_index_when_not_exists(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        mock_client.indices.exists.return_value = False
        mapping = build_index_mapping()
        await store.ensure_index("test-index", mapping)
        mock_client.indices.create.assert_awaited_once_with(index="test-index", body=mapping)

    async def test_noop_when_index_exists(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        mock_client.indices.exists.return_value = True
        await store.ensure_index("test-index", {})
        mock_client.indices.create.assert_not_awaited()


# -- index_chunks --------------------------------------------------------------


class TestIndexChunks:
    async def test_bulk_indexes_chunks(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        chunks = [_make_chunk(chunk_index=0), _make_chunk(chunk_index=1)]
        mock_client.bulk.return_value = {
            "errors": False,
            "items": [
                {"index": {"_id": "doc-1_0", "status": 201}},
                {"index": {"_id": "doc-1_1", "status": 201}},
            ],
        }
        count = await store.index_chunks("test-index", chunks)
        assert count == 2
        mock_client.bulk.assert_awaited_once()

    async def test_returns_zero_for_empty_list(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        count = await store.index_chunks("test-index", [])
        assert count == 0
        mock_client.bulk.assert_not_awaited()

    async def test_counts_partial_failures(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        chunks = [_make_chunk(chunk_index=0), _make_chunk(chunk_index=1)]
        mock_client.bulk.return_value = {
            "errors": True,
            "items": [
                {"index": {"_id": "doc-1_0", "status": 201}},
                {"index": {"_id": "doc-1_1", "error": {"reason": "mapping"}}},
            ],
        }
        count = await store.index_chunks("test-index", chunks)
        assert count == 1

    async def test_bulk_body_structure(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        chunk = _make_chunk(doc_id="d1", chunk_index=3)
        mock_client.bulk.return_value = {
            "errors": False,
            "items": [{"index": {"_id": "d1_3", "status": 201}}],
        }
        await store.index_chunks("idx", [chunk])
        call_body = mock_client.bulk.call_args[1]["body"]
        assert call_body[0] == {"index": {"_index": "idx", "_id": "d1_3"}}
        assert call_body[1]["doc_id"] == "d1"
        assert call_body[1]["chunk_index"] == 3


# -- search_similar ------------------------------------------------------------


class TestSearchSimilar:
    async def test_knn_search(self, store: OpenSearchStore, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = {"hits": {"hits": [_make_hit(score=0.99)]}}
        results = await store.search_similar("idx", [0.1, 0.2, 0.3], k=5)
        assert len(results) == 1
        assert results[0].score == 0.99
        call_body = mock_client.search.call_args[1]["body"]
        assert call_body["query"]["knn"]["embedding"]["vector"] == [0.1, 0.2, 0.3]
        assert call_body["query"]["knn"]["embedding"]["k"] == 5

    async def test_knn_search_with_doc_filter(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = {"hits": {"hits": []}}
        await store.search_similar("idx", [0.1], doc_id="doc-42")
        call_body = mock_client.search.call_args[1]["body"]
        assert call_body["query"]["knn"]["embedding"]["filter"] == {"term": {"doc_id": "doc-42"}}

    async def test_knn_search_no_filter_by_default(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = {"hits": {"hits": []}}
        await store.search_similar("idx", [0.1])
        call_body = mock_client.search.call_args[1]["body"]
        assert "filter" not in call_body["query"]["knn"]["embedding"]


# -- delete_document -----------------------------------------------------------


class TestDeleteDocument:
    async def test_deletes_by_doc_id(self, store: OpenSearchStore, mock_client: AsyncMock) -> None:
        mock_client.delete_by_query.return_value = {"deleted": 5}
        count = await store.delete_document("idx", "doc-1")
        assert count == 5
        call_body = mock_client.delete_by_query.call_args[1]["body"]
        assert call_body["query"] == {"term": {"doc_id": "doc-1"}}

    async def test_returns_zero_on_not_found(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        from opensearchpy import NotFoundError

        mock_client.delete_by_query.side_effect = NotFoundError(404, "index_not_found")
        count = await store.delete_document("idx", "doc-1")
        assert count == 0


# -- search_fulltext -----------------------------------------------------------


class TestSearchFulltext:
    async def test_fulltext_search(self, store: OpenSearchStore, mock_client: AsyncMock) -> None:
        mock_client.search.return_value = {
            "hits": {"hits": [_make_hit(content="matching text", score=1.5)]}
        }
        results = await store.search_fulltext("idx", "matching")
        assert len(results) == 1
        assert results[0].chunk.content == "matching text"
        call_body = mock_client.search.call_args[1]["body"]
        assert {"match": {"content": "matching"}} in call_body["query"]["bool"]["must"]

    async def test_fulltext_search_with_doc_filter(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        mock_client.search.return_value = {"hits": {"hits": []}}
        await store.search_fulltext("idx", "query", doc_id="doc-5")
        call_body = mock_client.search.call_args[1]["body"]
        must_clauses = call_body["query"]["bool"]["must"]
        assert {"term": {"doc_id": "doc-5"}} in must_clauses


# -- close ---------------------------------------------------------------------


class TestClose:
    async def test_close_delegates_to_client(
        self, store: OpenSearchStore, mock_client: AsyncMock
    ) -> None:
        await store.close()
        mock_client.close.assert_awaited_once()
