"""Tests for `api.graph` — the `/graph` (Neo4j-backed) endpoint.

Neo4j itself is not exercised here; the rich integration path is covered under
`tests/neo4j/`. This file stubs the `GraphReader` port to cover the router's
serialization + error mapping (happy path, store-not-configured 503), plus the
guardrail that `/graph/prime` stays removed.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.graph import router
from domain.value_objects import GraphPayload
from services.graph_service import GraphService


class _FakeGraphReader:
    """In-memory `GraphReader` returning a canned payload (or None)."""

    def __init__(self, payload: GraphPayload | None) -> None:
        self._payload = payload

    async def fetch(self, doc_id: str, *, max_pages: int = 200) -> GraphPayload | None:
        return self._payload


def _payload() -> GraphPayload:
    return GraphPayload(
        doc_id="doc-1",
        nodes=[
            {"id": "doc-1", "group": "document", "label": "hello.pdf"},
            {"id": "#/texts/0", "group": "element", "label": "Hello"},
        ],
        edges=[
            {"id": "e1", "source": "doc-1", "target": "#/texts/0", "type": "HAS_ROOT"},
        ],
        node_count=2,
        edge_count=1,
        truncated=False,
        page_count=1,
    )


def _client(*, reader: _FakeGraphReader | None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.graph_service = GraphService(graph_reader=reader)
    return TestClient(app)


class TestDocumentGraph:
    def test_returns_payload_from_reader(self) -> None:
        client = _client(reader=_FakeGraphReader(_payload()))
        resp = client.get("/api/documents/doc-1/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_id"] == "doc-1"
        assert data["node_count"] == 2
        assert data["page_count"] == 1
        assert data["truncated"] is False
        groups = {n["group"] for n in data["nodes"]}
        assert groups == {"document", "element"}
        assert data["edges"][0]["type"] == "HAS_ROOT"

    def test_503_when_graph_store_not_configured(self) -> None:
        # No reader wired (Neo4j absent) → /graph 503s cleanly.
        client = _client(reader=None)
        resp = client.get("/api/documents/doc-1/graph")
        assert resp.status_code == 503

    def test_404_when_document_unknown_to_store(self) -> None:
        client = _client(reader=_FakeGraphReader(None))
        resp = client.get("/api/documents/doc-1/graph")
        assert resp.status_code == 404


class TestPrimeEndpointRemoved:
    def test_graph_prime_endpoint_is_gone(self) -> None:
        # Guardrail — if someone reintroduces /graph/prime we want a failing test.
        client = _client(reader=_FakeGraphReader(_payload()))
        resp = client.post("/api/documents/doc-1/graph/prime")
        assert resp.status_code in (404, 405)
