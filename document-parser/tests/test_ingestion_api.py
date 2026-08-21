"""Tests for the ingestion API endpoints (api.ingestion)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.ingestion import router
from domain.models import AnalysisJob
from services.ingestion_service import IngestionResult
from tests.app_state import wire_state


@pytest.fixture
def mock_ingestion_service() -> AsyncMock:
    svc = AsyncMock()
    svc.ingest.return_value = IngestionResult(
        doc_id="doc-1", chunks_indexed=5, embedding_dimension=384
    )
    svc.delete_document.return_value = 3
    return svc


@pytest.fixture
def mock_analysis_service() -> AsyncMock:
    svc = AsyncMock()
    job = AnalysisJob(document_id="doc-1")
    job.document_filename = "test.pdf"
    job.mark_running()
    job.mark_completed(
        markdown="# Test",
        html="<h1>Test</h1>",
        pages_json="[]",
        document_json='{"doc": true}',
        chunks_json='[{"text": "hello"}]',
    )
    svc.find_by_id.return_value = job
    return svc


@pytest.fixture
def client(mock_ingestion_service: AsyncMock, mock_analysis_service: AsyncMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    wire_state(
        app, ingestion_service=mock_ingestion_service, analysis_service=mock_analysis_service
    )
    return TestClient(app)


class TestIngestAnalysis:
    def test_ingest_success(self, client: TestClient) -> None:
        resp = client.post("/api/ingestion/job-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["docId"] == "doc-1"
        assert data["chunksIndexed"] == 5
        assert data["embeddingDimension"] == 384

    def test_ingest_not_found(self, client: TestClient, mock_analysis_service: AsyncMock) -> None:
        mock_analysis_service.find_by_id.return_value = None
        resp = client.post("/api/ingestion/missing")
        assert resp.status_code == 404

    def test_ingest_not_completed(
        self, client: TestClient, mock_analysis_service: AsyncMock
    ) -> None:
        job = AnalysisJob(document_id="doc-1")
        mock_analysis_service.find_by_id.return_value = job
        resp = client.post("/api/ingestion/job-1")
        assert resp.status_code == 400

    def test_ingest_no_chunks(self, client: TestClient, mock_analysis_service: AsyncMock) -> None:
        job = AnalysisJob(document_id="doc-1")
        job.mark_running()
        job.mark_completed(markdown="x", html="x", pages_json="[]")
        mock_analysis_service.find_by_id.return_value = job
        resp = client.post("/api/ingestion/job-1")
        assert resp.status_code == 400


class TestDeleteIngested:
    def test_delete_success(self, client: TestClient) -> None:
        resp = client.delete("/api/ingestion/doc-1")
        assert resp.status_code == 204


class TestIngestionStatus:
    def test_available(self, client: TestClient) -> None:
        resp = client.get("/api/ingestion/status")
        assert resp.status_code == 200
        assert resp.json()["available"] is True

    def test_not_available(self) -> None:
        app = FastAPI()
        app.include_router(router)
        wire_state(app, ingestion_service=None, analysis_service=AsyncMock())
        tc = TestClient(app)
        resp = tc.get("/api/ingestion/status")
        assert resp.status_code == 200
        assert resp.json()["available"] is False


class TestIngestionDisabled:
    def test_router_not_mounted_returns_404(self) -> None:
        """When ingestion service is None, router should not be mounted → 404."""
        app = FastAPI()
        # Do NOT include ingestion router — simulates main.py conditional mount
        wire_state(app, ingestion_service=None, analysis_service=AsyncMock())
        tc = TestClient(app)
        resp = tc.post("/api/ingestion/job-1")
        assert resp.status_code == 404

    def test_status_still_returns_503_when_router_mounted_but_service_none(self) -> None:
        """If router is mounted but service is None, endpoints return 503."""
        app = FastAPI()
        app.include_router(router)
        wire_state(app, ingestion_service=None, analysis_service=AsyncMock())
        tc = TestClient(app)
        resp = tc.post("/api/ingestion/job-1")
        assert resp.status_code == 503


class TestStatusOpenSearch:
    def test_status_with_opensearch_connected(
        self, client: TestClient, mock_ingestion_service: AsyncMock
    ) -> None:
        mock_ingestion_service.ping.return_value = True
        resp = client.get("/api/ingestion/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["opensearchConnected"] is True

    def test_status_with_opensearch_disconnected(
        self, client: TestClient, mock_ingestion_service: AsyncMock
    ) -> None:
        mock_ingestion_service.ping.return_value = False
        resp = client.get("/api/ingestion/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["opensearchConnected"] is False


class TestSearchEndpoint:
    def test_search_success(self, client: TestClient, mock_ingestion_service: AsyncMock) -> None:
        from domain.vector_schema import IndexedChunk, SearchResult

        chunk = IndexedChunk(
            doc_id="doc-1",
            filename="test.pdf",
            content="hello world",
            embedding=[],
            chunk_index=0,
            chunk_type="text",
            page_number=1,
            headings=["Intro"],
        )
        mock_ingestion_service.search_fulltext.return_value = [
            SearchResult(chunk=chunk, score=0.95)
        ]
        resp = client.get("/api/ingestion/search", params={"q": "hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["query"] == "hello"
        assert data["results"][0]["content"] == "hello world"
        assert data["results"][0]["score"] == 0.95

    def test_search_empty_query(self, client: TestClient) -> None:
        resp = client.get("/api/ingestion/search", params={"q": ""})
        assert resp.status_code == 422

    def test_search_with_doc_filter(
        self, client: TestClient, mock_ingestion_service: AsyncMock
    ) -> None:
        mock_ingestion_service.search_fulltext.return_value = []
        resp = client.get("/api/ingestion/search", params={"q": "test", "doc_id": "doc-1"})
        assert resp.status_code == 200
        mock_ingestion_service.search_fulltext.assert_awaited_once_with(
            "test", k=20, doc_id="doc-1"
        )
