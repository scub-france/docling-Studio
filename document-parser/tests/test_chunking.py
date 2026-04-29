"""Tests for chunking feature — domain, schemas, service, and API endpoints."""

from __future__ import annotations

import json
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.schemas import ChunkBboxResponse, ChunkingOptionsRequest, ChunkResponse, RechunkRequest
from domain.models import AnalysisJob, AnalysisStatus, Document
from domain.value_objects import ChunkBbox, ChunkingOptions, ChunkResult
from main import app

# ---------------------------------------------------------------------------
# Domain: value objects
# ---------------------------------------------------------------------------


class TestChunkingOptions:
    def test_defaults(self):
        opts = ChunkingOptions()
        assert opts.chunker_type == "hybrid"
        assert opts.max_tokens == 512
        assert opts.merge_peers is True
        assert opts.repeat_table_header is True

    def test_custom_values(self):
        opts = ChunkingOptions(chunker_type="hierarchical", max_tokens=256, merge_peers=False)
        assert opts.chunker_type == "hierarchical"
        assert opts.max_tokens == 256
        assert opts.merge_peers is False

    def test_is_default(self):
        assert ChunkingOptions().is_default()
        assert not ChunkingOptions(max_tokens=256).is_default()


class TestChunkResult:
    def test_defaults(self):
        chunk = ChunkResult(text="hello")
        assert chunk.text == "hello"
        assert chunk.headings == []
        assert chunk.source_page is None
        assert chunk.token_count == 0

    def test_full_values(self):
        chunk = ChunkResult(
            text="content",
            headings=["Title", "Section"],
            source_page=3,
            token_count=42,
        )
        assert chunk.headings == ["Title", "Section"]
        assert chunk.source_page == 3
        assert chunk.token_count == 42

    def test_serializable(self):
        chunk = ChunkResult(text="x", headings=["h1"], source_page=1, token_count=10)
        data = asdict(chunk)
        assert data == {
            "text": "x",
            "headings": ["h1"],
            "source_page": 1,
            "token_count": 10,
            "bboxes": [],
            "doc_items": [],
        }


class TestChunkBbox:
    def test_construction(self):
        bbox = ChunkBbox(page=1, bbox=[10.0, 20.0, 100.0, 80.0])
        assert bbox.page == 1
        assert bbox.bbox == [10.0, 20.0, 100.0, 80.0]

    def test_serializable(self):
        bbox = ChunkBbox(page=2, bbox=[0.0, 0.0, 50.0, 50.0])
        data = asdict(bbox)
        assert data == {"page": 2, "bbox": [0.0, 0.0, 50.0, 50.0]}

    def test_chunk_result_with_bboxes(self):
        chunk = ChunkResult(
            text="content",
            bboxes=[
                ChunkBbox(page=1, bbox=[10, 20, 100, 80]),
                ChunkBbox(page=2, bbox=[50, 50, 150, 250]),
            ],
        )
        assert len(chunk.bboxes) == 2
        assert chunk.bboxes[0].page == 1


class TestChunkBboxResponse:
    def test_serializes(self):
        resp = ChunkBboxResponse(page=1, bbox=[10.0, 20.0, 100.0, 80.0])
        data = resp.model_dump(by_alias=True)
        assert data == {"page": 1, "bbox": [10.0, 20.0, 100.0, 80.0]}

    def test_chunk_response_with_bboxes(self):
        resp = ChunkResponse(
            text="hello",
            bboxes=[ChunkBboxResponse(page=1, bbox=[10, 20, 100, 80])],
        )
        data = resp.model_dump(by_alias=True)
        assert len(data["bboxes"]) == 1
        assert data["bboxes"][0]["page"] == 1


# ---------------------------------------------------------------------------
# Domain: AnalysisJob with chunking fields
# ---------------------------------------------------------------------------


class TestAnalysisJobChunking:
    def test_default_chunking_fields(self):
        job = AnalysisJob()
        assert job.document_json is None
        assert job.chunks_json is None

    def test_mark_completed_with_chunks(self):
        job = AnalysisJob()
        job.mark_running()
        job.mark_completed(
            markdown="# Title",
            html="<h1>Title</h1>",
            pages_json="[]",
            document_json='{"name": "doc"}',
            chunks_json='[{"text": "chunk1"}]',
        )
        assert job.status == AnalysisStatus.COMPLETED
        assert job.document_json == '{"name": "doc"}'
        assert job.chunks_json == '[{"text": "chunk1"}]'

    def test_mark_completed_without_chunks(self):
        job = AnalysisJob()
        job.mark_running()
        job.mark_completed(markdown="md", html="html", pages_json="[]")
        assert job.document_json is None
        assert job.chunks_json is None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TestChunkingOptionsRequest:
    def test_defaults(self):
        opts = ChunkingOptionsRequest()
        assert opts.chunker_type == "hybrid"
        assert opts.max_tokens == 512
        assert opts.merge_peers is True
        assert opts.repeat_table_header is True

    def test_custom_values(self):
        opts = ChunkingOptionsRequest(chunker_type="hierarchical", max_tokens=1024)
        assert opts.chunker_type == "hierarchical"
        assert opts.max_tokens == 1024

    def test_invalid_chunker_type(self):
        with pytest.raises(ValueError, match="chunker_type"):
            ChunkingOptionsRequest(chunker_type="invalid")

    def test_max_tokens_too_low(self):
        with pytest.raises(ValueError, match="max_tokens"):
            ChunkingOptionsRequest(max_tokens=10)

    def test_max_tokens_too_high(self):
        with pytest.raises(ValueError, match="max_tokens"):
            ChunkingOptionsRequest(max_tokens=10000)

    def test_boundary_max_tokens(self):
        opts_low = ChunkingOptionsRequest(max_tokens=64)
        assert opts_low.max_tokens == 64
        opts_high = ChunkingOptionsRequest(max_tokens=8192)
        assert opts_high.max_tokens == 8192


class TestChunkResponse:
    def test_serializes_to_camel_case(self):
        resp = ChunkResponse(text="hello", headings=["H1"], source_page=1, token_count=5)
        data = resp.model_dump(by_alias=True)
        assert "sourcePage" in data
        assert "tokenCount" in data
        assert data["text"] == "hello"


class TestRechunkRequest:
    def test_parses(self):
        req = RechunkRequest(chunkingOptions=ChunkingOptionsRequest(max_tokens=256))
        assert req.chunkingOptions.max_tokens == 256


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_analysis_service(client):
    mock_svc = MagicMock()
    original = getattr(app.state, "analysis_service", None)
    app.state.analysis_service = mock_svc
    yield mock_svc
    app.state.analysis_service = original


class TestCreateAnalysisWithChunking:
    def test_create_with_chunking_options(self, client, mock_analysis_service):
        mock_analysis_service.create = AsyncMock(
            return_value=AnalysisJob(
                id="j1",
                document_id="d1",
                document_filename="test.pdf",
            )
        )

        resp = client.post(
            "/api/analyses",
            json={
                "documentId": "d1",
                "chunkingOptions": {
                    "chunker_type": "hybrid",
                    "max_tokens": 256,
                    "merge_peers": False,
                },
            },
        )
        assert resp.status_code == 200

        call_kwargs = mock_analysis_service.create.call_args
        chunking = call_kwargs.kwargs["chunking_options"]
        assert chunking["chunker_type"] == "hybrid"
        assert chunking["max_tokens"] == 256
        assert chunking["merge_peers"] is False

    def test_create_without_chunking_options(self, client, mock_analysis_service):
        mock_analysis_service.create = AsyncMock(
            return_value=AnalysisJob(
                id="j1",
                document_id="d1",
                document_filename="test.pdf",
            )
        )

        resp = client.post("/api/analyses", json={"documentId": "d1"})
        assert resp.status_code == 200

        call_kwargs = mock_analysis_service.create.call_args
        assert call_kwargs.kwargs["chunking_options"] is None

    def test_response_includes_chunking_fields(self, client, mock_analysis_service):
        job = AnalysisJob(id="j1", document_id="d1", document_filename="test.pdf")
        job.mark_running()
        job.mark_completed(
            markdown="# Title",
            html="<h1>Title</h1>",
            pages_json="[]",
            document_json='{"name": "doc"}',
            chunks_json=json.dumps([asdict(ChunkResult(text="chunk1", token_count=5))]),
        )
        mock_analysis_service.find_by_id = AsyncMock(return_value=job)

        resp = client.get("/api/analyses/j1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasDocumentJson"] is True
        assert data["chunksJson"] is not None
        chunks = json.loads(data["chunksJson"])
        assert len(chunks) == 1
        assert chunks[0]["text"] == "chunk1"


class TestUpdateChunkTextEndpoint:
    def test_update_chunk_text_success(self, client, mock_analysis_service):
        updated_chunks = [
            {
                "text": "updated text",
                "headings": ["H1"],
                "sourcePage": 1,
                "tokenCount": 10,
                "bboxes": [],
                "modified": True,
            },
            {
                "text": "chunk2",
                "headings": [],
                "sourcePage": 2,
                "tokenCount": 20,
                "bboxes": [],
                "modified": False,
            },
        ]
        mock_analysis_service.update_chunk_text = AsyncMock(return_value=updated_chunks)

        resp = client.patch(
            "/api/analyses/j1/chunks/0",
            json={"text": "updated text"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["text"] == "updated text"
        assert data[0]["modified"] is True
        assert data[1]["modified"] is False

    def test_update_chunk_text_invalid_index(self, client, mock_analysis_service):
        mock_analysis_service.update_chunk_text = AsyncMock(
            side_effect=ValueError("Chunk index out of range: 99"),
        )
        resp = client.patch(
            "/api/analyses/j1/chunks/99",
            json={"text": "new"},
        )
        assert resp.status_code == 400

    def test_update_chunk_text_not_completed(self, client, mock_analysis_service):
        mock_analysis_service.update_chunk_text = AsyncMock(
            side_effect=ValueError("Analysis is not completed: j1"),
        )
        resp = client.patch(
            "/api/analyses/j1/chunks/0",
            json={"text": "new"},
        )
        assert resp.status_code == 400

    def test_update_chunk_text_not_found(self, client, mock_analysis_service):
        mock_analysis_service.update_chunk_text = AsyncMock(
            side_effect=ValueError("Analysis not found: j1"),
        )
        resp = client.patch(
            "/api/analyses/j1/chunks/0",
            json={"text": "new"},
        )
        assert resp.status_code == 400


class TestDeleteChunkEndpoint:
    def test_delete_chunk_success(self, client, mock_analysis_service):
        updated_chunks = [
            {
                "text": "chunk1",
                "headings": [],
                "sourcePage": 1,
                "tokenCount": 10,
                "bboxes": [],
                "deleted": True,
            },
            {
                "text": "chunk2",
                "headings": [],
                "sourcePage": 2,
                "tokenCount": 20,
                "bboxes": [],
                "deleted": False,
            },
        ]
        mock_analysis_service.delete_chunk = AsyncMock(return_value=updated_chunks)

        resp = client.delete("/api/analyses/j1/chunks/0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["deleted"] is True
        assert data[1]["deleted"] is False

    def test_delete_chunk_invalid_index(self, client, mock_analysis_service):
        mock_analysis_service.delete_chunk = AsyncMock(
            side_effect=ValueError("Chunk index out of range: 99"),
        )
        resp = client.delete("/api/analyses/j1/chunks/99")
        assert resp.status_code == 400

    def test_delete_chunk_not_completed(self, client, mock_analysis_service):
        mock_analysis_service.delete_chunk = AsyncMock(
            side_effect=ValueError("Analysis is not completed: j1"),
        )
        resp = client.delete("/api/analyses/j1/chunks/0")
        assert resp.status_code == 400


class TestRechunkEndpoint:
    def test_rechunk_success(self, client, mock_analysis_service):
        mock_analysis_service.rechunk = AsyncMock(
            return_value=[
                ChunkResult(text="chunk1", headings=["H1"], source_page=1, token_count=10),
                ChunkResult(text="chunk2", headings=["H1", "H2"], source_page=2, token_count=20),
            ]
        )

        resp = client.post(
            "/api/analyses/j1/rechunk",
            json={
                "chunkingOptions": {"chunker_type": "hybrid", "max_tokens": 128},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["text"] == "chunk1"
        assert data[0]["sourcePage"] == 1
        assert data[0]["tokenCount"] == 10
        assert data[1]["headings"] == ["H1", "H2"]

    def test_rechunk_not_completed(self, client, mock_analysis_service):
        mock_analysis_service.rechunk = AsyncMock(
            side_effect=ValueError("Analysis is not completed: j1"),
        )

        resp = client.post(
            "/api/analyses/j1/rechunk",
            json={
                "chunkingOptions": {"chunker_type": "hybrid"},
            },
        )
        assert resp.status_code == 400

    def test_rechunk_no_document_json(self, client, mock_analysis_service):
        mock_analysis_service.rechunk = AsyncMock(
            side_effect=ValueError("No document data available for re-chunking: j1"),
        )

        resp = client.post(
            "/api/analyses/j1/rechunk",
            json={
                "chunkingOptions": {"chunker_type": "hierarchical"},
            },
        )
        assert resp.status_code == 400

    def test_rechunk_returns_bboxes(self, client, mock_analysis_service):
        mock_analysis_service.rechunk = AsyncMock(
            return_value=[
                ChunkResult(
                    text="chunk1",
                    source_page=1,
                    token_count=10,
                    bboxes=[ChunkBbox(page=1, bbox=[10, 20, 100, 80])],
                ),
            ]
        )

        resp = client.post(
            "/api/analyses/j1/rechunk",
            json={"chunkingOptions": {"chunker_type": "hybrid"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data[0]["bboxes"]) == 1
        assert data[0]["bboxes"][0]["page"] == 1
        assert data[0]["bboxes"][0]["bbox"] == [10, 20, 100, 80]

    def test_rechunk_invalid_chunker_type(self, client, mock_analysis_service):
        resp = client.post(
            "/api/analyses/j1/rechunk",
            json={
                "chunkingOptions": {"chunker_type": "invalid"},
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Remote chunking path — hybrid local chunking from Serve's document_json
# ---------------------------------------------------------------------------


class TestRemoteChunkingPath:
    """Verify that chunking works on document_json produced by Serve (remote mode)."""

    @pytest.mark.asyncio
    async def test_rechunk_with_serve_document_json(self):
        """AnalysisService.rechunk() works with a LocalChunker even in remote mode."""
        from infra.local_chunker import LocalChunker
        from services.analysis_service import AnalysisService

        chunker = LocalChunker()
        analysis_repo = AsyncMock()
        document_repo = AsyncMock()
        converter = AsyncMock()  # ServeConverter mock — not used for rechunking

        service = AnalysisService(
            converter=converter,
            analysis_repo=analysis_repo,
            document_repo=document_repo,
            chunker=chunker,
        )

        # Simulate a completed job with document_json from Serve
        job = AnalysisJob(id="j-remote", document_id="d1")
        job.mark_running()
        job.mark_completed(
            markdown="# Title\nParagraph text here.",
            html="<h1>Title</h1><p>Paragraph text here.</p>",
            pages_json="[]",
            document_json=json.dumps(
                {
                    "schema_name": "DoclingDocument",
                    "version": "1.0.0",
                    "name": "test",
                    "origin": {
                        "mimetype": "application/pdf",
                        "filename": "test.pdf",
                        "binary_hash": 0,
                    },
                    "furniture": {
                        "self_ref": "#/furniture",
                        "children": [],
                        "content_layer": "furniture",
                    },
                    "body": {"self_ref": "#/body", "children": [], "content_layer": "body"},
                    "groups": [],
                    "texts": [],
                    "pictures": [],
                    "tables": [],
                    "key_value_items": [],
                    "form_items": [],
                    "pages": {},
                }
            ),
        )
        analysis_repo.find_by_id = AsyncMock(return_value=job)
        analysis_repo.update_chunks = AsyncMock(return_value=True)
        # rechunk() now drives a Document lifecycle transition (#202), so
        # the document_repo must return a real Document and accept the
        # update_lifecycle write.
        document_repo.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="test.pdf", storage_path="/tmp/test.pdf")
        )
        document_repo.update_lifecycle = AsyncMock()

        chunks = await service.rechunk(
            "j-remote",
            {"chunker_type": "hybrid", "max_tokens": 512},
        )

        assert isinstance(chunks, list)
        analysis_repo.update_chunks.assert_called_once()
