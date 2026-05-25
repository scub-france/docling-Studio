"""Integration tests for the /api/documents/{id}/chunks router (#256)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from domain.models import Chunk
from main import app
from services.chunk_service import (
    ChunkConflictError,
    ChunkNotFoundError,
    ChunkValidationError,
    DocumentNotFoundError,
)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_service(client):
    svc = MagicMock()
    original = getattr(app.state, "chunk_service", None)
    app.state.chunk_service = svc
    yield svc
    app.state.chunk_service = original


def _chunk(*, id="c-1", doc_id="d-1", sequence=0, text="hi") -> Chunk:
    return Chunk(id=id, document_id=doc_id, sequence=sequence, text=text)


class TestListChunks:
    def test_200(self, client, mock_service):
        mock_service.list_chunks = AsyncMock(return_value=[_chunk(id="c1"), _chunk(id="c2")])
        resp = client.get("/api/documents/d-1/chunks")
        assert resp.status_code == 200
        data = resp.json()
        assert [c["id"] for c in data] == ["c1", "c2"]
        # camelCase serialization
        assert "docId" in data[0]
        assert "sourcePage" in data[0]

    def test_404_when_doc_missing(self, client, mock_service):
        mock_service.list_chunks = AsyncMock(side_effect=DocumentNotFoundError("nope"))
        resp = client.get("/api/documents/no-such/chunks")
        assert resp.status_code == 404


class TestAddChunk:
    def test_201(self, client, mock_service):
        mock_service.add_chunk = AsyncMock(return_value=_chunk(id="new"))
        resp = client.post("/api/documents/d-1/chunks", json={"text": "hello"})
        assert resp.status_code == 201
        assert resp.json()["id"] == "new"
        mock_service.add_chunk.assert_awaited_once_with("d-1", text="hello", after_id=None)

    def test_400_on_empty_body(self, client, mock_service):
        resp = client.post("/api/documents/d-1/chunks", json={"text": ""})
        assert resp.status_code == 400

    def test_passes_after_id(self, client, mock_service):
        mock_service.add_chunk = AsyncMock(return_value=_chunk(id="new"))
        client.post(
            "/api/documents/d-1/chunks",
            json={"text": "x", "afterId": "c-prev"},
        )
        mock_service.add_chunk.assert_awaited_once_with("d-1", text="x", after_id="c-prev")


class TestUpdateChunk:
    def test_200(self, client, mock_service):
        mock_service.update_chunk = AsyncMock(return_value=_chunk(text="new"))
        resp = client.patch(
            "/api/documents/d-1/chunks/c-1",
            json={"text": "new"},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == "new"

    def test_400_when_no_field_set(self, client, mock_service):
        resp = client.patch("/api/documents/d-1/chunks/c-1", json={})
        assert resp.status_code == 400

    def test_404_when_chunk_missing(self, client, mock_service):
        mock_service.update_chunk = AsyncMock(side_effect=ChunkNotFoundError("nope"))
        resp = client.patch("/api/documents/d-1/chunks/c-1", json={"text": "x"})
        assert resp.status_code == 404

    def test_title_maps_to_first_heading(self, client, mock_service):
        mock_service.update_chunk = AsyncMock(return_value=_chunk())
        client.patch("/api/documents/d-1/chunks/c-1", json={"title": "Section A"})
        mock_service.update_chunk.assert_awaited_once_with(
            "d-1", "c-1", text=None, headings=["Section A"]
        )


class TestDeleteChunk:
    def test_204(self, client, mock_service):
        mock_service.delete_chunk = AsyncMock(return_value=None)
        resp = client.delete("/api/documents/d-1/chunks/c-1")
        assert resp.status_code == 204

    def test_404(self, client, mock_service):
        mock_service.delete_chunk = AsyncMock(side_effect=ChunkNotFoundError("nope"))
        resp = client.delete("/api/documents/d-1/chunks/c-1")
        assert resp.status_code == 404


class TestSplit:
    def test_200(self, client, mock_service):
        mock_service.split_chunk = AsyncMock(
            return_value=[_chunk(id="head"), _chunk(id="tail", sequence=1)]
        )
        resp = client.post(
            "/api/documents/d-1/chunks/c-1/split",
            json={"cursorOffset": 3},
        )
        assert resp.status_code == 200
        assert [c["id"] for c in resp.json()] == ["head", "tail"]

    def test_400_on_invalid_offset(self, client, mock_service):
        mock_service.split_chunk = AsyncMock(side_effect=ChunkValidationError("oor"))
        resp = client.post(
            "/api/documents/d-1/chunks/c-1/split",
            json={"cursorOffset": 999},
        )
        assert resp.status_code == 400


class TestMerge:
    def test_200(self, client, mock_service):
        mock_service.merge_chunks = AsyncMock(return_value=_chunk(id="merged"))
        resp = client.post(
            "/api/documents/d-1/chunks/merge",
            json={"ids": ["a", "b"]},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == "merged"

    def test_409_on_non_contiguous(self, client, mock_service):
        mock_service.merge_chunks = AsyncMock(side_effect=ChunkConflictError("nope"))
        resp = client.post(
            "/api/documents/d-1/chunks/merge",
            json={"ids": ["a", "z"]},
        )
        assert resp.status_code == 409


class TestRechunk:
    def test_200_no_options(self, client, mock_service):
        mock_service.rechunk_document = AsyncMock(return_value=[_chunk(id="r1")])
        resp = client.post("/api/documents/d-1/rechunk", json={})
        assert resp.status_code == 200
        mock_service.rechunk_document.assert_awaited_once_with("d-1", None)

    def test_200_with_options(self, client, mock_service):
        mock_service.rechunk_document = AsyncMock(return_value=[])
        resp = client.post(
            "/api/documents/d-1/rechunk",
            json={"chunkingOptions": {"chunkerType": "hybrid", "maxTokens": 256}},
        )
        assert resp.status_code == 200
        call_args = mock_service.rechunk_document.await_args
        assert call_args.args[0] == "d-1"
        passed_opts = call_args.args[1]
        # snake_case dump from Pydantic ChunkingOptionsRequest
        assert passed_opts["chunker_type"] == "hybrid"
        assert passed_opts["max_tokens"] == 256


class TestTree:
    def test_200_empty(self, client, mock_service):
        mock_service.get_tree = AsyncMock(return_value=[])
        resp = client.get("/api/documents/d-1/tree")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_200_groups(self, client, mock_service):
        mock_service.get_tree = AsyncMock(
            return_value=[
                {"ref": "#group/title", "type": "group", "label": "Titles", "children": []}
            ]
        )
        resp = client.get("/api/documents/d-1/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["label"] == "Titles"


class TestDiff:
    def test_200(self, client, mock_service):
        mock_service.diff_against_store = AsyncMock(
            return_value=[
                {"chunkId": "c1", "status": "added", "textDiff": None},
            ]
        )
        resp = client.get("/api/documents/d-1/diff?store=mystore")
        assert resp.status_code == 200
        assert resp.json()[0]["chunkId"] == "c1"

    def test_400_when_store_missing(self, client, mock_service):
        resp = client.get("/api/documents/d-1/diff")
        # FastAPI auto-422 on missing required query
        assert resp.status_code in (400, 422)


class TestPush:
    def test_200(self, client, mock_service):
        mock_service.push_to_store = AsyncMock(
            return_value={"pushId": "p1", "summary": {"embeds": 3, "tokens": 30}}
        )
        resp = client.post(
            "/api/documents/d-1/chunks/push",
            json={"store": "mystore"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["pushId"] == "p1"
        assert body["summary"]["embeds"] == 3


class TestListPushes:
    """`GET /api/documents/{id}/chunks/pushes` — push history feed (#283)."""

    def test_200_returns_paginated_envelope(self, client, mock_service):
        mock_service.list_pushes = AsyncMock(
            return_value={
                "items": [
                    {
                        "id": "push-1",
                        "documentId": "d-1",
                        "storeId": "s-rh",
                        "storeSlug": "rh-corpus",
                        "storeName": "RH Corpus",
                        "storeKind": "opensearch",
                        "chunksetHash": "abc123",
                        "chunkCount": 11,
                        "pushedAt": "2026-05-19T14:32:00+00:00",
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            }
        )
        resp = client.get("/api/documents/d-1/chunks/pushes")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["limit"] == 50
        assert body["offset"] == 0
        assert len(body["items"]) == 1
        entry = body["items"][0]
        assert entry["storeSlug"] == "rh-corpus"
        assert entry["storeKind"] == "opensearch"
        assert entry["chunkCount"] == 11
        # Service got the default limit/offset.
        mock_service.list_pushes.assert_awaited_once_with("d-1", limit=50, offset=0)

    def test_forwards_limit_and_offset_query_params(self, client, mock_service):
        mock_service.list_pushes = AsyncMock(
            return_value={"items": [], "total": 0, "limit": 10, "offset": 20}
        )
        resp = client.get("/api/documents/d-1/chunks/pushes?limit=10&offset=20")
        assert resp.status_code == 200
        mock_service.list_pushes.assert_awaited_once_with("d-1", limit=10, offset=20)

    def test_404_when_document_unknown(self, client, mock_service):
        mock_service.list_pushes = AsyncMock(side_effect=DocumentNotFoundError("not found"))
        resp = client.get("/api/documents/ghost/chunks/pushes")
        assert resp.status_code == 404

    def test_422_when_limit_out_of_range(self, client, mock_service):
        mock_service.list_pushes = AsyncMock(return_value={"items": [], "total": 0})
        resp = client.get("/api/documents/d-1/chunks/pushes?limit=500")
        # 500 > 200 (the cap).
        assert resp.status_code == 422
        mock_service.list_pushes.assert_not_awaited()

    def test_422_when_offset_negative(self, client, mock_service):
        mock_service.list_pushes = AsyncMock(return_value={"items": [], "total": 0})
        resp = client.get("/api/documents/d-1/chunks/pushes?offset=-1")
        assert resp.status_code == 422
        mock_service.list_pushes.assert_not_awaited()
