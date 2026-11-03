"""Tests for FastAPI API endpoints using TestClient."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from domain.models import AnalysisJob, Document, DocumentStoreLink, Store
from domain.value_objects import DocumentStoreLinkState
from infra.file_storage import LocalFileStorage
from infra.page_raster import PdfPageRasterizer
from infra.pdf_inspector import PdfiumInspector
from main import app
from services.document_service import DocumentConfig, DocumentService
from services.navigation_errors import DocumentNotFoundError
from tests.app_state import state_override


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_analysis_service(client):
    """Inject a mock AnalysisService into app.state for the duration of the test."""
    mock_svc = MagicMock()
    with state_override(app, analysis_service=mock_svc):
        yield mock_svc


@pytest.fixture
def mock_document_service(client):
    """Inject a mock DocumentService into app.state for the duration of the test."""
    mock_svc = MagicMock()
    mock_svc.max_file_size = 50 * 1024 * 1024
    mock_svc.max_file_size_mb = 50
    with state_override(app, document_service=mock_svc):
        yield mock_svc


@pytest.fixture
def document_repos(client, tmp_path):
    """The repositories behind a real DocumentService, with the real PDF
    adapters: the document routes run end to end, on the files a test writes
    under `tmp_path`. No document has store links unless a test adds some."""
    repos = SimpleNamespace(documents=AsyncMock(), links=AsyncMock(), stores=AsyncMock())
    repos.links.find_for_document.return_value = []
    repos.stores.find_all.return_value = []
    service = DocumentService(
        document_repo=repos.documents,
        analysis_repo=AsyncMock(),
        config=DocumentConfig(),
        files=LocalFileStorage(str(tmp_path)),
        rasterizer=PdfPageRasterizer(),
        pdf=PdfiumInspector(),
        store_repo=repos.stores,
        link_repo=repos.links,
    )
    with state_override(app, document_service=service):
        yield repos


@pytest.fixture
def stored_documents(document_repos):
    """The document repository of `document_repos`."""
    return document_repos.documents


@pytest.fixture
def mock_export_service(client):
    """Inject a mock ExportService into app.state for export endpoint tests."""
    mock_svc = MagicMock()
    mock_svc.export = AsyncMock()
    with state_override(app, export_service=mock_svc):
        yield mock_svc


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
        with state_override(app, ingestion_service=None):
            resp = client.get("/api/health")
        data = resp.json()
        assert "ingestionAvailable" in data
        assert data["ingestionAvailable"] is False

    def test_health_exposes_ingestion_available_true(self, client):
        with state_override(app, ingestion_service=MagicMock()):
            resp = client.get("/api/health")
        data = resp.json()
        assert data["ingestionAvailable"] is True

    def test_health_exposes_surface_flags(self, client):
        """0.6.1 (#257): /api/health surfaces studio + rag_pipeline master flags."""
        resp = client.get("/api/health")
        data = resp.json()
        assert "studioModeEnabled" in data
        assert "ragPipelineEnabled" in data
        # Defaults: studio off, rag pipeline on (production target).
        assert data["studioModeEnabled"] is False
        assert data["ragPipelineEnabled"] is True

    def test_health_says_ask_is_hidden_by_default(self, client):
        data = client.get("/api/health").json()
        assert data["askMode"] == "hidden"

    def test_health_says_ask_is_visible_when_asked_for(self, client, monkeypatch):
        import main

        monkeypatch.setattr(main, "settings", replace(main.settings, ask_mode="visible"))
        data = client.get("/api/health").json()
        assert data["askMode"] == "visible"

    def test_health_exposes_doc_mode_flags(self, client):
        """0.6.0 (#210, renamed in #257): /api/health surfaces inspect/linked sub-flags."""
        resp = client.get("/api/health")
        data = resp.json()
        assert "inspectModeEnabled" in data
        assert "linkedModeEnabled" in data
        # Sub-flag defaults preserve current behaviour (all enabled).
        assert data["inspectModeEnabled"] is True
        assert data["linkedModeEnabled"] is True


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

    def test_get_document(self, client, stored_documents):
        stored_documents.find_by_id = AsyncMock(
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
        assert data["storeLinks"] == []

    def test_get_document_with_its_store_links(self, client, document_repos):
        """Each link names its store by slug (#283); a link whose store row is
        gone falls back to the store id."""
        document_repos.documents.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="test.pdf", storage_path="/tmp/test")
        )
        pushed = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
        document_repos.links.find_for_document.return_value = [
            DocumentStoreLink(
                document_id="d1",
                store_id="s-1",
                state=DocumentStoreLinkState.INGESTED,
                last_push_at=pushed,
            ),
            DocumentStoreLink(
                document_id="d1", store_id="s-gone", state=DocumentStoreLinkState.FAILED
            ),
        ]
        document_repos.stores.find_all.return_value = [Store(id="s-1", slug="legal-v1")]

        resp = client.get("/api/documents/d1")

        assert resp.status_code == 200
        assert resp.json()["storeLinks"] == [
            {"store": "legal-v1", "state": "Ingested", "pushedAt": str(pushed)},
            {"store": "s-gone", "state": "Failed", "pushedAt": None},
        ]
        document_repos.links.find_for_document.assert_awaited_once_with("d1")

    def test_get_document_not_found(self, client, stored_documents):
        stored_documents.find_by_id = AsyncMock(return_value=None)

        resp = client.get("/api/documents/missing")
        assert resp.status_code == 404
        assert resp.json() == {"detail": "Document not found"}

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

    def test_upload_rejects_oversized_content_length(self, client, mock_document_service):
        """Endpoint returns 413 from the Content-Length pre-check, before the
        body is read and before the service is touched (#audit-09 MAJ-09a)."""
        mock_document_service.max_file_size = 5  # bytes
        mock_document_service.max_file_size_mb = 0
        mock_document_service.upload = AsyncMock()  # must never be reached

        resp = client.post(
            "/api/documents/upload",
            files={"file": ("big.pdf", b"way-more-than-five-bytes", "application/pdf")},
        )

        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"].lower()
        mock_document_service.upload.assert_not_called()

    def test_preview(self, client, stored_documents, tmp_path):
        from tests.test_document_service import pdf_with_pages

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792), (842, 595)))
        stored_documents.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="test.pdf", page_count=2, storage_path=str(pdf))
        )

        resp = client.get("/api/documents/d1/preview?page=2&dpi=72")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.content.startswith(b"\x89PNG")
        # A page of a stored PDF never changes: the browser keeps it.
        assert resp.headers["cache-control"] == "private, max-age=86400"

    def test_preview_unknown_document(self, client, stored_documents):
        stored_documents.find_by_id = AsyncMock(return_value=None)

        resp = client.get("/api/documents/nope/preview")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "Document not found"}

    def test_preview_page_out_of_range(self, client, stored_documents):
        stored_documents.find_by_id = AsyncMock(
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
        assert resp.json() == {"detail": "Page 10 out of range (document has 3 pages)"}

    def test_preview_page_the_pdf_does_not_have(self, client, stored_documents, tmp_path):
        """Page count unknown (not counted at upload): the PDF answers."""
        from tests.test_document_service import pdf_with_pages

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792)))
        stored_documents.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="test.pdf", storage_path=str(pdf))
        )

        resp = client.get("/api/documents/d1/preview?page=4")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "Page 4 not found"}

    def test_preview_missing_file(self, client, stored_documents, tmp_path):
        stored_documents.find_by_id = AsyncMock(
            return_value=Document(
                id="d1", filename="gone.pdf", storage_path=str(tmp_path / "gone.pdf")
            )
        )

        resp = client.get("/api/documents/d1/preview")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "PDF file not found on disk"}
        assert "cache-control" not in resp.headers

    def test_preview_unreadable_pdf(self, client, stored_documents, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")
        stored_documents.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="broken.pdf", storage_path=str(broken))
        )

        resp = client.get("/api/documents/d1/preview")

        assert resp.status_code == 422
        assert resp.json() == {"detail": "Failed to generate preview"}

    def test_page_sizes(self, client, stored_documents, tmp_path):
        from tests.test_document_service import pdf_with_pages

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792), (842, 595)))
        stored_documents.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="test.pdf", storage_path=str(pdf))
        )

        resp = client.get("/api/documents/d1/pages")

        assert resp.status_code == 200
        assert resp.json() == [
            {"pageNumber": 1, "width": 612.0, "height": 792.0},
            {"pageNumber": 2, "width": 842.0, "height": 595.0},
        ]
        assert resp.headers["cache-control"] == "private, max-age=86400"

    def test_page_sizes_unknown_document(self, client, stored_documents):
        stored_documents.find_by_id = AsyncMock(return_value=None)

        assert client.get("/api/documents/nope/pages").status_code == 404

    def test_page_sizes_missing_file(self, client, stored_documents, tmp_path):
        stored_documents.find_by_id = AsyncMock(
            return_value=Document(
                id="d1", filename="gone.pdf", storage_path=str(tmp_path / "gone.pdf")
            )
        )

        resp = client.get("/api/documents/d1/pages")

        assert resp.status_code == 404
        assert "not found on disk" in resp.json()["detail"]
        assert "cache-control" not in resp.headers

    def test_page_sizes_unreadable_pdf(self, client, stored_documents, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")
        stored_documents.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="broken.pdf", storage_path=str(broken))
        )

        resp = client.get("/api/documents/d1/pages")

        assert resp.status_code == 422
        assert resp.json() == {"detail": "Failed to read PDF file"}

    def test_delete_document(self, client, mock_document_service):
        mock_document_service.delete = AsyncMock(return_value=True)

        resp = client.delete("/api/documents/d1")
        assert resp.status_code == 204

    def test_delete_document_not_found(self, client, mock_document_service):
        mock_document_service.delete = AsyncMock(return_value=False)

        resp = client.delete("/api/documents/missing")
        assert resp.status_code == 404

    def test_export_document_pdf(self, client, mock_export_service, tmp_path):
        pdf_path = tmp_path / "report.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")
        mock_export_service.export.return_value.file_path = str(pdf_path)
        mock_export_service.export.return_value.media_type = "application/pdf"
        mock_export_service.export.return_value.filename = "report.pdf"
        mock_export_service.export.return_value.content = None

        resp = client.get("/api/documents/d1/export?format=pdf")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.headers["content-disposition"] == 'attachment; filename="report.pdf"'

    def test_export_document_markdown(self, client, mock_export_service):
        mock_export_service.export.return_value.file_path = None
        mock_export_service.export.return_value.content = "# Title"
        mock_export_service.export.return_value.media_type = "text/markdown; charset=utf-8"
        mock_export_service.export.return_value.filename = "report.md"

        resp = client.get("/api/documents/d1/export?format=md")

        assert resp.status_code == 200
        assert resp.text == "# Title"
        assert resp.headers["content-type"] == "text/markdown; charset=utf-8"
        assert resp.headers["content-disposition"] == 'attachment; filename="report.md"'

    def test_export_document_json(self, client, mock_export_service):
        mock_export_service.export.return_value.file_path = None
        mock_export_service.export.return_value.content = '{"ok":true}'
        mock_export_service.export.return_value.media_type = "application/json"
        mock_export_service.export.return_value.filename = "report.json"

        resp = client.get("/api/documents/d1/export?format=json")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        assert resp.headers["content-disposition"] == 'attachment; filename="report.json"'

    @pytest.mark.parametrize(
        ("query", "analysis_id"),
        [("format=md", None), ("format=md&analysisId=a1", "a1")],
    )
    def test_export_document_forwards_the_analysis_id(
        self, client, mock_export_service, query, analysis_id
    ):
        from services.export_service import ExportFormat

        mock_export_service.export.return_value.file_path = None
        mock_export_service.export.return_value.content = "# Title"
        mock_export_service.export.return_value.media_type = "text/markdown"
        mock_export_service.export.return_value.filename = "report.md"

        resp = client.get(f"/api/documents/d1/export?{query}")

        assert resp.status_code == 200
        mock_export_service.export.assert_awaited_once_with("d1", ExportFormat.MD, analysis_id)

    def test_export_document_unsupported_format_returns_422(self, client, mock_export_service):
        resp = client.get("/api/documents/d1/export?format=docx")
        assert resp.status_code == 422

    def test_export_document_no_analysis_returns_404(self, client, mock_export_service):
        from services.export_service import ExportNotFoundError

        mock_export_service.export.side_effect = ExportNotFoundError(
            "No completed analysis found for this document"
        )

        resp = client.get("/api/documents/d1/export?format=md")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "No completed analysis found for this document"}

    def test_export_document_json_unavailable_returns_404(self, client, mock_export_service):
        from services.export_service import ExportNotFoundError

        mock_export_service.export.side_effect = ExportNotFoundError("JSON content not available")

        resp = client.get("/api/documents/d1/export?format=json")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "JSON content not available"}


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

    def test_list_analysis_summaries(self, client, mock_analysis_service):
        # #354 — statuses without content, not captured by /{analysis_id}.
        mock_analysis_service.find_all_summaries = AsyncMock(
            return_value=[
                AnalysisJob(
                    id="j1",
                    document_id="d1",
                    document_filename="test.pdf",
                    progress_current=5,
                    progress_total=10,
                ),
            ]
        )

        resp = client.get("/api/analyses/summaries")

        assert resp.status_code == 200
        [summary] = resp.json()
        assert summary["id"] == "j1"
        assert summary["documentFilename"] == "test.pdf"
        assert summary["status"] == "PENDING"
        assert summary["progressCurrent"] == 5
        assert summary["progressTotal"] == 10
        assert "contentMarkdown" not in summary
        assert "pagesJson" not in summary
        mock_analysis_service.find_all_summaries.assert_awaited_once()

    def test_list_analyses_filtered_by_document(self, client, mock_analysis_service):
        mock_analysis_service.find_all = AsyncMock(return_value=[])
        mock_analysis_service.find_by_document = AsyncMock(
            return_value=[
                AnalysisJob(id="j2", document_id="d42", document_filename="paper.pdf"),
            ]
        )

        resp = client.get("/api/analyses?documentId=d42")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["documentId"] == "d42"
        mock_analysis_service.find_by_document.assert_awaited_once_with("d42")
        mock_analysis_service.find_all.assert_not_awaited()

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
        mock_analysis_service.create = AsyncMock(
            side_effect=DocumentNotFoundError("Document not found: d99")
        )

        resp = client.post("/api/analyses", json={"documentId": "d99"})
        assert resp.status_code == 404

    def test_create_analysis_empty_document_id(self, client, mock_analysis_service):
        resp = client.post("/api/analyses", json={"documentId": ""})
        assert resp.status_code == 400

    def test_create_analysis_whitespace_document_id(self, client, mock_analysis_service):
        resp = client.post("/api/analyses", json={"documentId": "   "})
        assert resp.status_code == 400

    def test_import_analysis(self, client, mock_analysis_service):
        job = AnalysisJob(id="j-import", document_id="d1", document_filename="test.pdf")
        job.mark_running()
        job.mark_completed("# Imported", "<p>Imported</p>", "[]", "{}")
        mock_analysis_service.import_docling_document = AsyncMock(return_value=job)
        payload = {"documentId": "d1", "document": {"schema_name": "DoclingDocument"}}

        resp = client.post("/api/analyses/import", json=payload)

        assert resp.status_code == 200
        assert resp.json()["id"] == "j-import"
        assert resp.json()["status"] == "COMPLETED"
        mock_analysis_service.import_docling_document.assert_awaited_once_with(
            "d1", payload["document"]
        )

    def test_import_analysis_requires_document_id(self, client, mock_analysis_service):
        resp = client.post("/api/analyses/import", json={"documentId": " ", "document": {}})

        assert resp.status_code == 400
        assert resp.json() == {"detail": "documentId is required"}

    def test_import_analysis_rejects_missing_document(self, client, mock_analysis_service):
        mock_analysis_service.import_docling_document = AsyncMock(
            side_effect=DocumentNotFoundError("Document not found: missing")
        )

        resp = client.post("/api/analyses/import", json={"documentId": "missing", "document": {}})

        assert resp.status_code == 404

    def test_import_missing_document_body(self, client, mock_analysis_service):
        mock_analysis_service.import_docling_document = AsyncMock(
            side_effect=DocumentNotFoundError("Document not found: missing")
        )

        resp = client.post("/api/analyses/import", json={"documentId": "missing", "document": {}})

        assert resp.json() == {"detail": "Document not found: missing"}

    def test_import_status_does_not_depend_on_the_message(self, client, mock_analysis_service):
        # A ValueError is a document that does not validate, whatever it says:
        # only the typed error is a 404 (#audit-05).
        mock_analysis_service.import_docling_document = AsyncMock(
            side_effect=ValueError("Document not found: worded like one")
        )

        resp = client.post("/api/analyses/import", json={"documentId": "d1", "document": {}})

        assert resp.status_code == 400
        assert resp.json() == {"detail": "Document not found: worded like one"}

    def test_create_missing_document_body(self, client, mock_analysis_service):
        mock_analysis_service.create = AsyncMock(
            side_effect=DocumentNotFoundError("Document not found: d99")
        )

        resp = client.post("/api/analyses", json={"documentId": "d99"})

        assert resp.json() == {"detail": "Document not found: d99"}

    def test_import_answers_400_at_once_to_a_huge_declared_table(
        self, client, mock_analysis_service
    ):
        """#audit-08: a few hundred bytes declaring a 10**6 x 10**6 table."""
        from docling_core.types.doc import DoclingDocument

        from infra.docling_importer import DoclingDocumentImporter

        document = DoclingDocument(name="source").export_to_dict()
        document["tables"] = [
            {
                "self_ref": "#/tables/0",
                "parent": {"$ref": "#/body"},
                "label": "table",
                "data": {"table_cells": [], "num_rows": 10**6, "num_cols": 10**6},
            }
        ]
        document["body"]["children"] = [{"$ref": "#/tables/0"}]
        mock_analysis_service.import_docling_document = AsyncMock(
            side_effect=lambda _doc_id, doc: DoclingDocumentImporter().deserialize(doc)
        )

        resp = client.post("/api/analyses/import", json={"documentId": "d1", "document": document})

        assert resp.status_code == 400
        assert "MAX_IMPORT_TABLE_CELLS" in resp.json()["detail"]

    def test_import_refuses_a_declared_body_over_the_cap_without_reading_it(
        self, client, mock_analysis_service, monkeypatch
    ):
        monkeypatch.setattr("api.analyses._MAX_BODY_BYTES", 1024)

        async def must_not_read(_request):
            raise AssertionError("the body was read despite its Content-Length")

        monkeypatch.setattr("api.analyses._BoundedBodyRequest.body", must_not_read)
        mock_analysis_service.import_docling_document = AsyncMock()

        resp = client.post(
            "/api/analyses/import", json={"documentId": "d1", "document": {"x": "y" * 2048}}
        )

        assert resp.status_code == 413
        assert resp.json()["detail"].startswith("Request body too large")
        mock_analysis_service.import_docling_document.assert_not_awaited()

    def test_import_counts_a_chunked_body_while_reading_it(
        self, client, mock_analysis_service, monkeypatch
    ):
        """No Content-Length to trust: the read itself stops past the cap."""
        monkeypatch.setattr("api.analyses._MAX_BODY_BYTES", 1024)
        mock_analysis_service.import_docling_document = AsyncMock()

        def chunks():
            yield b'{"documentId": "d1", "document": {"x": "'
            for _ in range(64):
                yield b"y" * 512
            yield b'"}}'

        resp = client.post(
            "/api/analyses/import",
            content=chunks(),
            headers={"content-type": "application/json"},
        )

        assert resp.status_code == 413
        mock_analysis_service.import_docling_document.assert_not_awaited()

    def test_a_body_under_the_cap_goes_through(self, client, mock_analysis_service, monkeypatch):
        monkeypatch.setattr("api.analyses._MAX_BODY_BYTES", 4096)
        mock_analysis_service.import_docling_document = AsyncMock(
            side_effect=ValueError("Invalid Docling document: stop here")
        )

        resp = client.post(
            "/api/analyses/import", json={"documentId": "d1", "document": {"x": "y" * 1024}}
        )

        assert resp.status_code == 400
        mock_analysis_service.import_docling_document.assert_awaited_once()

    def test_delete_analysis(self, client, mock_analysis_service):
        mock_analysis_service.delete = AsyncMock(return_value=True)

        resp = client.delete("/api/analyses/j1")
        assert resp.status_code == 204

    def test_delete_analysis_not_found(self, client, mock_analysis_service):
        mock_analysis_service.delete = AsyncMock(return_value=False)

        resp = client.delete("/api/analyses/missing")
        assert resp.status_code == 404
