"""Tests for the ingestion service (services.ingestion_service)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from services.ingestion_service import IngestionConfig, IngestionService


def _make_chunks_json(count: int = 3, *, with_deleted: bool = False) -> str:
    chunks = []
    for i in range(count):
        chunk = {
            "text": f"chunk text {i}",
            "headings": [f"Heading {i}"],
            "sourcePage": i + 1,
            "tokenCount": 10,
            "bboxes": [{"page": i + 1, "bbox": [0.0, 0.0, 100.0, 50.0]}],
        }
        if with_deleted and i == count - 1:
            chunk["deleted"] = True
        chunks.append(chunk)
    return json.dumps(chunks)


@pytest.fixture
def mock_embedding() -> AsyncMock:
    svc = AsyncMock()
    svc.embed.return_value = [[0.1, 0.2, 0.3]] * 3
    return svc


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    store = AsyncMock()
    store.ensure_index.return_value = None
    store.delete_document.return_value = 0
    store.index_chunks.return_value = 3
    return store


@pytest.fixture
def service(mock_embedding: AsyncMock, mock_vector_store: AsyncMock) -> IngestionService:
    return IngestionService(
        embedding_service=mock_embedding,
        vector_store=mock_vector_store,
        config=IngestionConfig(index_name="test-idx", embedding_dimension=3),
    )


class TestIngest:
    async def test_full_pipeline(
        self, service: IngestionService, mock_embedding: AsyncMock, mock_vector_store: AsyncMock
    ) -> None:
        result = await service.ingest("doc-1", "test.pdf", _make_chunks_json(3))

        assert result.doc_id == "doc-1"
        assert result.chunks_indexed == 3
        mock_embedding.embed.assert_awaited_once()
        texts = mock_embedding.embed.call_args[0][0]
        assert len(texts) == 3
        mock_vector_store.ensure_index.assert_awaited_once()
        mock_vector_store.delete_document.assert_awaited_once_with("test-idx", "doc-1")
        mock_vector_store.index_chunks.assert_awaited_once()
        indexed = mock_vector_store.index_chunks.call_args[0][1]
        assert len(indexed) == 3
        assert indexed[0].doc_id == "doc-1"
        assert indexed[0].filename == "test.pdf"
        assert indexed[0].embedding == [0.1, 0.2, 0.3]

    async def test_skips_deleted_chunks(
        self, service: IngestionService, mock_embedding: AsyncMock, mock_vector_store: AsyncMock
    ) -> None:
        mock_embedding.embed.return_value = [[0.1, 0.2, 0.3]] * 2
        mock_vector_store.index_chunks.return_value = 2
        result = await service.ingest("doc-1", "test.pdf", _make_chunks_json(3, with_deleted=True))

        assert result.chunks_indexed == 2
        texts = mock_embedding.embed.call_args[0][0]
        assert len(texts) == 2

    async def test_empty_chunks(
        self, service: IngestionService, mock_embedding: AsyncMock, mock_vector_store: AsyncMock
    ) -> None:
        result = await service.ingest("doc-1", "test.pdf", json.dumps([]))
        assert result.chunks_indexed == 0
        mock_embedding.embed.assert_not_awaited()

    async def test_idempotent_deletes_old(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        mock_vector_store.delete_document.return_value = 5
        await service.ingest("doc-1", "test.pdf", _make_chunks_json(3))
        mock_vector_store.delete_document.assert_awaited_once_with("test-idx", "doc-1")

    async def test_bbox_conversion(
        self, service: IngestionService, mock_embedding: AsyncMock, mock_vector_store: AsyncMock
    ) -> None:
        mock_embedding.embed.return_value = [[0.1, 0.2, 0.3]]
        mock_vector_store.index_chunks.return_value = 1
        await service.ingest("doc-1", "test.pdf", _make_chunks_json(1))
        indexed = mock_vector_store.index_chunks.call_args[0][1]
        bbox = indexed[0].bboxes[0]
        assert bbox.x == 0.0
        assert bbox.y == 0.0
        assert bbox.w == 100.0
        assert bbox.h == 50.0

    async def test_with_binary_hash(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        mock_embedding = service._embedding
        mock_embedding.embed.return_value = [[0.1]] * 1
        await service.ingest("doc-1", "test.pdf", _make_chunks_json(1), binary_hash="abc123")
        indexed = mock_vector_store.index_chunks.call_args[0][1]
        assert indexed[0].origin is not None
        assert indexed[0].origin.binary_hash == "abc123"


class TestDeleteDocument:
    async def test_delegates_to_vector_store(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        mock_vector_store.delete_document.return_value = 3
        result = await service.delete_document("doc-1")
        assert result == 3


class TestSearch:
    async def test_embeds_and_searches(
        self, service: IngestionService, mock_embedding: AsyncMock, mock_vector_store: AsyncMock
    ) -> None:
        mock_embedding.embed.return_value = [[0.5, 0.6, 0.7]]
        mock_vector_store.search_similar.return_value = []
        await service.search("test query", k=5)
        mock_embedding.embed.assert_awaited_once_with(["test query"])
        mock_vector_store.search_similar.assert_awaited_once()


class TestSearchFulltext:
    async def test_delegates_to_vector_store(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        mock_vector_store.search_fulltext.return_value = []
        await service.search_fulltext("hello world", k=5)
        mock_vector_store.search_fulltext.assert_awaited_once_with(
            "test-idx", "hello world", k=5, doc_id=None
        )

    async def test_filters_by_doc_id(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        mock_vector_store.search_fulltext.return_value = []
        await service.search_fulltext("hello", doc_id="doc-1")
        mock_vector_store.search_fulltext.assert_awaited_once_with(
            "test-idx", "hello", k=20, doc_id="doc-1"
        )


class TestPing:
    async def test_ping_success(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        mock_vector_store.ping.return_value = True
        result = await service.ping()
        assert result is True

    async def test_ping_failure(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        mock_vector_store.ping.side_effect = ConnectionError("down")
        result = await service.ping()
        assert result is False


class TestEnsureIndex:
    async def test_calls_vector_store(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        await service.ensure_index()
        mock_vector_store.ensure_index.assert_awaited_once()
        call_args = mock_vector_store.ensure_index.call_args
        assert call_args[0][0] == "test-idx"


# ---------------------------------------------------------------------------
# Per-call targets override (#279)
#
# `ingest()` accepts an optional `IngestionTargets` kwarg that
# overrides the service-level (vector_store, neo4j_driver) defaults.
# This is the linchpin of per-store dispatch — the StoreBackendResolver
# resolves a Store to an IngestionTargets, then `chunk_service.push_to_store`
# passes that through. The resolver itself is tested in
# `test_store_backend_resolver.py`; this class pins the IngestionService
# end of the contract.
# ---------------------------------------------------------------------------


class TestIngestTargetsOverride:
    async def test_targets_vector_store_wins_over_service_default(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        """A non-None targets.vector_store is used in place of the
        service-level default. The service-level default must NOT
        receive any call when an override is provided.
        """
        from services.store_backend_resolver import IngestionTargets

        override = AsyncMock()
        override.ensure_index.return_value = None
        override.delete_document.return_value = 0
        override.index_chunks.return_value = 3
        targets = IngestionTargets(vector_store=override, graph_writer=None)

        result = await service.ingest("doc-1", "test.pdf", _make_chunks_json(3), targets=targets)

        # The override carried the writes.
        override.ensure_index.assert_awaited_once()
        override.delete_document.assert_awaited_once_with("test-idx", "doc-1")
        override.index_chunks.assert_awaited_once()
        # The service-level default never saw a single call.
        mock_vector_store.ensure_index.assert_not_awaited()
        mock_vector_store.delete_document.assert_not_awaited()
        mock_vector_store.index_chunks.assert_not_awaited()
        assert result.chunks_indexed == 3

    async def test_targets_graph_writer_wins_over_service_default(
        self,
        service: IngestionService,
        mock_vector_store: AsyncMock,
    ) -> None:
        """A non-None `targets.graph_writer` triggers the graph mirror
        write through the resolved port, not through the service's own
        (None by default in the fixture). #audit-01 — the port replaces
        the raw Neo4j driver that used to be threaded through here.
        """
        from services.store_backend_resolver import IngestionTargets

        graph_writer_mock = AsyncMock()
        targets = IngestionTargets(vector_store=mock_vector_store, graph_writer=graph_writer_mock)

        await service.ingest("doc-1", "test.pdf", _make_chunks_json(3), targets=targets)

        graph_writer_mock.write_chunks.assert_awaited_once()
        kwargs = graph_writer_mock.write_chunks.await_args.kwargs
        assert kwargs["doc_id"] == "doc-1"

    async def test_targets_none_falls_back_to_service_defaults(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        """The explicit `targets=None` path is the pre-#279 contract —
        backwards-compat with single-cluster callers (legacy tests,
        embedding/search endpoints that don't know about stores).
        """
        await service.ingest("doc-1", "test.pdf", _make_chunks_json(3), targets=None)
        mock_vector_store.index_chunks.assert_awaited_once()

    async def test_targets_both_none_inside_envelope_is_a_full_skip(
        self, service: IngestionService, mock_vector_store: AsyncMock
    ) -> None:
        """An IngestionTargets with both fields None reaches the
        Neo4j-only / no-store-configured branch — embedding still runs,
        no vector index call happens. Defensive: shouldn't occur in
        practice (the resolver always returns one non-None), but the
        contract should be predictable if a caller forges this shape.
        """
        from services.store_backend_resolver import IngestionTargets

        targets = IngestionTargets(vector_store=None, graph_writer=None)
        result = await service.ingest("doc-1", "test.pdf", _make_chunks_json(3), targets=targets)

        # Vector store path is entirely skipped despite the
        # service-level default being present (the override wins,
        # even with None).
        mock_vector_store.index_chunks.assert_not_awaited()
        # `chunks_indexed` mirrors the processed count (#199 Neo4j-only
        # contract carries over).
        assert result.chunks_indexed == 3


# ---------------------------------------------------------------------------
# Neo4j-only mode (#199)
#
# When no OpenSearch is configured (vector_store=None), the service
# must still accept ingest/search/delete calls — the user is on a
# Neo4j-only stack and the empty results / no-op behaviour is the
# contract. The previous code raised AttributeError on a None
# `vector_store.<method>` call. These tests pin the contract so it
# can't regress.
# ---------------------------------------------------------------------------


@pytest.fixture
def neo4j_only_service(mock_embedding: AsyncMock) -> IngestionService:
    """Service with `vector_store=None` — mimics a backend started
    with `EMBEDDING_URL` + `NEO4J_URI` but no `OPENSEARCH_URL`.
    """
    return IngestionService(
        embedding_service=mock_embedding,
        vector_store=None,
        config=IngestionConfig(index_name="test-idx", embedding_dimension=3),
    )


class TestNeo4jOnlyMode:
    async def test_ensure_index_is_noop_without_vector_store(
        self, neo4j_only_service: IngestionService
    ) -> None:
        # Must not raise. There's no vector index to ensure.
        await neo4j_only_service.ensure_index()

    async def test_ingest_skips_opensearch_and_reports_processed_count(
        self, neo4j_only_service: IngestionService, mock_embedding: AsyncMock
    ) -> None:
        result = await neo4j_only_service.ingest("doc-1", "test.pdf", _make_chunks_json(3))
        # Embedding still runs (text-search semantics must stay
        # consistent across stores) — only the OpenSearch indexing
        # step is skipped.
        mock_embedding.embed.assert_awaited_once()
        # `chunks_indexed` carries the processed count in Neo4j-only
        # mode (no real OpenSearch indexing happened). This is the
        # contract — renaming to `chunks_processed` is a separate
        # follow-up since it would break the API.
        assert result.chunks_indexed == 3
        assert result.embedding_dimension == 3

    async def test_ingest_empty_chunks_short_circuits(
        self, neo4j_only_service: IngestionService, mock_embedding: AsyncMock
    ) -> None:
        result = await neo4j_only_service.ingest("doc-1", "test.pdf", json.dumps([]))
        assert result.chunks_indexed == 0
        mock_embedding.embed.assert_not_awaited()

    async def test_delete_document_returns_zero(self, neo4j_only_service: IngestionService) -> None:
        # Nothing to delete in a vector store that isn't there — but
        # the call must not raise; otherwise the API endpoint 500s.
        assert await neo4j_only_service.delete_document("doc-1") == 0

    async def test_search_returns_empty_list(
        self, neo4j_only_service: IngestionService, mock_embedding: AsyncMock
    ) -> None:
        results = await neo4j_only_service.search("hello")
        assert results == []
        # The embedding is also skipped — there's no point computing
        # a vector for a search that has nowhere to look.
        mock_embedding.embed.assert_not_awaited()

    async def test_search_fulltext_returns_empty_list(
        self, neo4j_only_service: IngestionService
    ) -> None:
        results = await neo4j_only_service.search_fulltext("hello")
        assert results == []

    async def test_ping_returns_true(self, neo4j_only_service: IngestionService) -> None:
        # The service is reachable even without a vector store — the
        # Neo4j-only ingest path is still operational. Reporting
        # `False` here would make `/api/health.ingestion_available`
        # misleading.
        assert await neo4j_only_service.ping() is True
