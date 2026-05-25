"""Tests for `api.graph` — the `/graph` (Neo4j) and `/reasoning-graph`
(SQLite) endpoints. Neo4j itself is not exercised here; `/graph` is covered
by the integration tests under `tests/neo4j/`. This file focuses on the
SQLite-backed reasoning endpoint and the error paths.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.graph import router
from domain.models import AnalysisJob
from infra.docling_graph import DoclingGraphProjector
from services.graph_service import GraphService

FIXTURE = {
    "pages": {"1": {"page_no": 1, "size": {"width": 595, "height": 842}}},
    "body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]},
    "texts": [
        {
            "self_ref": "#/texts/0",
            "parent": {"$ref": "#/body"},
            "label": "section_header",
            "text": "Hello",
            "level": 1,
            "prov": [{"page_no": 1, "bbox": {"l": 0, "t": 0, "r": 10, "b": 10}}],
        }
    ],
    "tables": [],
    "pictures": [],
    "groups": [],
}


def _job_with_doc_json() -> AnalysisJob:
    job = AnalysisJob(document_id="doc-1")
    job.document_filename = "hello.pdf"
    job.mark_running()
    job.mark_completed(
        markdown="# Hello",
        html="<h1>Hello</h1>",
        pages_json="[]",
        document_json=json.dumps(FIXTURE),
        chunks_json="[]",
    )
    return job


@pytest.fixture
def mock_analysis_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.find_latest_completed_by_document.return_value = _job_with_doc_json()
    return repo


@pytest.fixture
def client(mock_analysis_repo: AsyncMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.analysis_repo = mock_analysis_repo
    # `/reasoning-graph` is decoupled from Neo4j by design — only the
    # projector is required. Pass `graph_reader=None` to prove `/graph`
    # 503-s cleanly while `/reasoning-graph` still serves (#audit-01).
    app.state.graph_service = GraphService(
        analysis_repo=mock_analysis_repo,
        graph_reader=None,
        graph_projector=DoclingGraphProjector(),
    )
    return TestClient(app)


class TestReasoningGraph:
    def test_returns_payload_built_from_sqlite_json(self, client: TestClient) -> None:
        resp = client.get("/api/documents/doc-1/reasoning-graph")
        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_id"] == "doc-1"
        assert data["page_count"] == 1
        assert data["truncated"] is False

        groups = {n["group"] for n in data["nodes"]}
        assert groups == {"document", "page", "element"}

        edge_types = {e["type"] for e in data["edges"]}
        # HAS_ROOT + ON_PAGE expected; NEXT absent (single element so no chain).
        assert edge_types == {"HAS_ROOT", "ON_PAGE"}

    def test_404_when_no_completed_analysis(
        self, client: TestClient, mock_analysis_repo: AsyncMock
    ) -> None:
        mock_analysis_repo.find_latest_completed_by_document.return_value = None
        resp = client.get("/api/documents/doc-1/reasoning-graph")
        assert resp.status_code == 404

    def test_404_when_analysis_has_no_document_json(
        self, client: TestClient, mock_analysis_repo: AsyncMock
    ) -> None:
        job = AnalysisJob(document_id="doc-1")
        job.mark_running()
        job.mark_completed(
            markdown="", html="", pages_json="[]", document_json=None, chunks_json="[]"
        )
        mock_analysis_repo.find_latest_completed_by_document.return_value = job
        resp = client.get("/api/documents/doc-1/reasoning-graph")
        assert resp.status_code == 404

    def test_does_not_need_neo4j(self, client: TestClient) -> None:
        # `app.state.neo4j = None` and the endpoint still serves — proves the
        # reasoning graph is fully decoupled from the Neo4j provider.
        resp = client.get("/api/documents/doc-1/reasoning-graph")
        assert resp.status_code == 200


class TestPrimeEndpointRemoved:
    def test_graph_prime_endpoint_is_gone(self, client: TestClient) -> None:
        # Guardrail — if someone reintroduces /graph/prime we want a failing test.
        resp = client.post("/api/documents/doc-1/graph/prime")
        assert resp.status_code in (404, 405)
