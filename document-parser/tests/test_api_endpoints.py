"""Tests for FastAPI API endpoints using TestClient."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from domain.models import AnalysisJob, Document
from main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_analysis_service(client):
    """Inject a mock AnalysisService into app.state for the duration of the test."""
    mock_svc = MagicMock()
    original = getattr(app.state, "analysis_service", None)
    app.state.analysis_service = mock_svc
    yield mock_svc
    app.state.analysis_service = original


@pytest.fixture
def mock_document_service(client):
    """Inject a mock DocumentService into app.state for the duration of the test."""
    mock_svc = MagicMock()
    mock_svc.max_file_size = 50 * 1024 * 1024
    mock_svc.max_file_size_mb = 50
    original = getattr(app.state, "document_service", None)
    app.state.document_service = mock_svc
    yield mock_svc
    app.state.document_service = original


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert "engine" in data
        assert "database" in data

    def test_health_exposes_max_file_size_mb(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert "maxFileSizeMb" in data
        assert data["maxFileSizeMb"] == 50

    def test_health_exposes_ingestion_available_false(self, client):
        original = getattr(app.state, "ingestion_service", None)
        app.state.ingestion_service = None
        resp = client.get("/api/health")
        app.state.ingestion_service = original
        data = resp.json()
        assert "ingestionAvailable" in data
        assert data["ingestionAvailable"] is False

    def test_health_exposes_ingestion_available_true(self, client):
        original = getattr(app.state, "ingestion_service", None)
        app.state.ingestion_service = MagicMock()
        resp = client.get("/api/health")
        app.state.ingestion_service = original
        data = resp.json()
        assert data["ingestionAvailable"] is True

    def test_health_exposes_doc_mode_flags(self, client):
        """0.6.0 (#210): /api/health surfaces inspect/chunks/ask mode flags."""
        resp = client.get("/api/health")
        data = resp.json()
        assert "inspectModeEnabled" in data
        assert "chunksModeEnabled" in data
        assert "askModeEnabled" in data
        # Defaults preserve current behaviour (all enabled).
        assert data["inspectModeEnabled"] is True
        assert data["chunksModeEnabled"] is True
        assert data["askModeEnabled"] is True


class TestDocumentEndpoints:
    def test_list_documents(self, client, mock_document_service):
        mock_document_service.find_all = AsyncMock(
            return_value=[
                Document(id="d1", filename="a.pdf", storage_path="/tmp/a"),
                Document(id="d2", filename="b.pdf", storage_path="/tmp/b"),
            ]
        )

        resp = client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == "d1"
        assert data[0]["filename"] == "a.pdf"
        # Verify camelCase
        assert "createdAt" in data[0]

    def test_get_document(self, client, mock_document_service):
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(
                id="d1",
                filename="test.pdf",
                content_type="application/pdf",
                file_size=2048,
                page_count=3,
                storage_path="/tmp/test",
            )
        )

        resp = client.get("/api/documents/d1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "d1"
        assert data["fileSize"] == 2048
        assert data["pageCount"] == 3

    def test_get_document_not_found(self, client, mock_document_service):
        mock_document_service.find_by_id = AsyncMock(return_value=None)

        resp = client.get("/api/documents/missing")
        assert resp.status_code == 404

    def test_upload_document(self, client, mock_document_service):
        mock_document_service.upload = AsyncMock(
            return_value=Document(
                id="new-1",
                filename="uploaded.pdf",
                content_type="application/pdf",
                file_size=512,
                storage_path="/tmp/uploaded",
            )
        )

        resp = client.post(
            "/api/documents/upload",
            files={"file": ("uploaded.pdf", b"fake-pdf-content", "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "new-1"
        assert data["filename"] == "uploaded.pdf"

    def test_upload_too_large(self, client, mock_document_service):
        mock_document_service.upload = AsyncMock(
            side_effect=ValueError("File too large (max 5 MB)")
        )

        resp = client.post(
            "/api/documents/upload",
            files={"file": ("big.pdf", b"x", "application/pdf")},
        )
        assert resp.status_code == 400

    def test_preview_page_out_of_range(self, client, mock_document_service):
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(
                id="d1",
                filename="test.pdf",
                page_count=3,
                storage_path="/tmp/test.pdf",
            )
        )

        resp = client.get("/api/documents/d1/preview?page=10")
        assert resp.status_code == 400
        assert "out of range" in resp.json()["detail"]

    def test_delete_document(self, client, mock_document_service):
        mock_document_service.delete = AsyncMock(return_value=True)

        resp = client.delete("/api/documents/d1")
        assert resp.status_code == 204

    def test_delete_document_not_found(self, client, mock_document_service):
        mock_document_service.delete = AsyncMock(return_value=False)

        resp = client.delete("/api/documents/missing")
        assert resp.status_code == 404


class TestAnalysisEndpoints:
    def test_list_analyses(self, client, mock_analysis_service):
        mock_analysis_service.find_all = AsyncMock(
            return_value=[
                AnalysisJob(id="j1", document_id="d1", document_filename="test.pdf"),
            ]
        )

        resp = client.get("/api/analyses")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "j1"
        assert data[0]["documentId"] == "d1"
        assert data[0]["documentFilename"] == "test.pdf"
        assert data[0]["status"] == "PENDING"

    def test_get_analysis(self, client, mock_analysis_service):
        job = AnalysisJob(id="j1", document_id="d1", document_filename="test.pdf")
        job.mark_running()
        mock_analysis_service.find_by_id = AsyncMock(return_value=job)

        resp = client.get("/api/analyses/j1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RUNNING"
        # ISO-8601 datetime string from `mark_running()`
        assert isinstance(data["startedAt"], str)
        assert data["startedAt"]  # not empty

    def test_get_analysis_not_found(self, client, mock_analysis_service):
        mock_analysis_service.find_by_id = AsyncMock(return_value=None)

        resp = client.get("/api/analyses/missing")
        assert resp.status_code == 404

    def test_create_analysis(self, client, mock_analysis_service):
        mock_analysis_service.create = AsyncMock(
            return_value=AnalysisJob(
                id="j1",
                document_id="d1",
                document_filename="test.pdf",
            )
        )

        resp = client.post("/api/analyses", json={"documentId": "d1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "j1"
        assert data["documentId"] == "d1"
        mock_analysis_service.create.assert_called_once_with(
            "d1",
            pipeline_options=None,
            chunking_options=None,
        )

    def test_create_analysis_with_pipeline_options(self, client, mock_analysis_service):
        mock_analysis_service.create = AsyncMock(
            return_value=AnalysisJob(
                id="j2",
                document_id="d1",
                document_filename="test.pdf",
            )
        )

        resp = client.post(
            "/api/analyses",
            json={
                "documentId": "d1",
                "pipelineOptions": {
                    "do_ocr": False,
                    "do_table_structure": True,
                    "table_mode": "fast",
                    "do_code_enrichment": True,
                    "do_formula_enrichment": False,
                    "do_picture_classification": False,
                    "do_picture_description": False,
                    "generate_picture_images": True,
                    "generate_page_images": False,
                    "images_scale": 2.0,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "j2"

        call_kwargs = mock_analysis_service.create.call_args
        opts = call_kwargs.kwargs["pipeline_options"]
        assert opts["do_ocr"] is False
        assert opts["table_mode"] == "fast"
        assert opts["do_code_enrichment"] is True
        assert opts["generate_picture_images"] is True
        assert opts["images_scale"] == 2.0

    def test_create_analysis_with_partial_pipeline_options(self, client, mock_analysis_service):
        """Pipeline options should use defaults for unspecified fields."""
        mock_analysis_service.create = AsyncMock(
            return_value=AnalysisJob(
                id="j3",
                document_id="d1",
                document_filename="test.pdf",
            )
        )

        resp = client.post(
            "/api/analyses", json={"documentId": "d1", "pipelineOptions": {"do_ocr": False}}
        )
        assert resp.status_code == 200

        opts = mock_analysis_service.create.call_args.kwargs["pipeline_options"]
        assert opts["do_ocr"] is False
        # Defaults
        assert opts["do_table_structure"] is True
        assert opts["table_mode"] == "accurate"
        assert opts["do_code_enrichment"] is False

    def test_create_analysis_document_not_found(self, client, mock_analysis_service):
        mock_analysis_service.create = AsyncMock(side_effect=ValueError("Document not found: d99"))

        resp = client.post("/api/analyses", json={"documentId": "d99"})
        assert resp.status_code == 404

    def test_create_analysis_empty_document_id(self, client, mock_analysis_service):
        resp = client.post("/api/analyses", json={"documentId": ""})
        assert resp.status_code == 400

    def test_create_analysis_whitespace_document_id(self, client, mock_analysis_service):
        resp = client.post("/api/analyses", json={"documentId": "   "})
        assert resp.status_code == 400

    def test_delete_analysis(self, client, mock_analysis_service):
        mock_analysis_service.delete = AsyncMock(return_value=True)

        resp = client.delete("/api/analyses/j1")
        assert resp.status_code == 204

    def test_delete_analysis_not_found(self, client, mock_analysis_service):
        mock_analysis_service.delete = AsyncMock(return_value=False)

        resp = client.delete("/api/analyses/missing")
        assert resp.status_code == 404
