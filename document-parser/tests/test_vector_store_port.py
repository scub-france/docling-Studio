"""Tests for VectorStore port — verify the protocol contract is implementable."""

from __future__ import annotations

import pytest

from domain.ports import VectorStore
from domain.vector_schema import IndexedChunk, SearchResult


class FakeVectorStore:
    """Minimal concrete implementation to verify the protocol is implementable."""

    async def ensure_index(self, index_name: str, mapping: dict) -> None:
        pass

    async def index_chunks(self, index_name: str, chunks: list[IndexedChunk]) -> int:
        return len(chunks)

    async def search_similar(
        self,
        index_name: str,
        embedding: list[float],
        *,
        k: int = 10,
        doc_id: str | None = None,
    ) -> list[SearchResult]:
        return []

    async def get_chunks(
        self,
        index_name: str,
        doc_id: str,
        *,
        limit: int = 1000,
    ) -> list[SearchResult]:
        return []

    async def search_fulltext(
        self,
        index_name: str,
        query_text: str,
        *,
        k: int = 10,
        doc_id: str | None = None,
    ) -> list[SearchResult]:
        return []

    async def delete_document(self, index_name: str, doc_id: str) -> int:
        return 0

    async def ping(self) -> bool:
        return True


class TestVectorStorePort:
    def test_fake_satisfies_protocol(self):
        """A class implementing all methods is accepted as a VectorStore."""
        store: VectorStore = FakeVectorStore()
        assert isinstance(store, VectorStore)

    @pytest.mark.asyncio
    async def test_ensure_index(self):
        store = FakeVectorStore()
        await store.ensure_index("test-index", {"mappings": {}})

    @pytest.mark.asyncio
    async def test_index_chunks(self):
        store = FakeVectorStore()
        chunk = IndexedChunk(
            doc_id="d1",
            filename="test.pdf",
            content="Hello",
            embedding=[0.1] * 384,
            chunk_index=0,
            chunk_type="text",
            page_number=1,
        )
        count = await store.index_chunks("test-index", [chunk])
        assert count == 1

    @pytest.mark.asyncio
    async def test_search_similar(self):
        store = FakeVectorStore()
        results = await store.search_similar("test-index", [0.1] * 384, k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_similar_with_doc_filter(self):
        store = FakeVectorStore()
        results = await store.search_similar("test-index", [0.1] * 384, k=5, doc_id="d1")
        assert results == []

    @pytest.mark.asyncio
    async def test_get_chunks(self):
        store = FakeVectorStore()
        results = await store.get_chunks("test-index", "d1")
        assert results == []

    @pytest.mark.asyncio
    async def test_get_chunks_with_limit(self):
        store = FakeVectorStore()
        results = await store.get_chunks("test-index", "d1", limit=50)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_fulltext(self):
        store = FakeVectorStore()
        results = await store.search_fulltext("test-index", "hello", k=5, doc_id="d1")
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_document(self):
        store = FakeVectorStore()
        count = await store.delete_document("test-index", "d1")
        assert count == 0

    def test_protocol_methods_list(self):
        """Verify the protocol exposes the expected methods."""
        expected = {
            "ensure_index",
            "index_chunks",
            "search_similar",
            "get_chunks",
            "delete_document",
            "search_fulltext",
            "ping",
        }
        protocol_methods = {
            name
            for name in dir(VectorStore)
            if not name.startswith("_") and callable(getattr(VectorStore, name, None))
        }
        assert expected.issubset(protocol_methods)
