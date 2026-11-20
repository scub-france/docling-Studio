"""Tests for FastAPI API endpoints using TestClient."""

import shutil
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from domain.models import AnalysisJob, AnalysisOutput, Document
from infra.document_file_store import LocalDocumentFileStore
from infra.page_raster import PdfPageRasterizer
from infra.pdf_inspector import PdfiumInspector
from infra.preview_cache import PreviewCache
from main import app
from services.preview_service import PreviewService
from tests.app_state import state_override


def _preview_service(documents, tmp_path, *, rasterizer=None, cache=None) -> PreviewService:
    return PreviewService(
        documents=documents,
        files=LocalDocumentFileStore(str(tmp_path / "uploads")),
        rasterizer=rasterizer or PdfPageRasterizer(),
        inspector=PdfiumInspector(),
        cache=cache or PreviewCache(),
    )


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
def mock_document_service(client, tmp_path):
    """Inject a mock DocumentService into app.state for the duration of the test."""
    mock_svc = MagicMock()
    mock_svc.max_file_size = 50 * 1024 * 1024
    mock_svc.max_file_size_mb = 50
    with state_override(
        app,
        document_service=mock_svc,
        preview_service=_preview_service(mock_svc, tmp_path),
        current_analysis=MagicMock(find_current_analysis_id=AsyncMock(return_value=None)),
    ):
        yield mock_svc


@pytest.fixture
def mock_current_analysis(mock_document_service):
    """The current-analysis rule the document route reads, from the same state."""
    return app.state.container.current_analysis


@pytest.fixture
def mock_export_service(client):
    """Inject a mock ExportService into app.state for export endpoint tests."""
    mock_svc = MagicMock()
    mock_svc.export = AsyncMock()
    mock_svc.export_edited = AsyncMock()
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

    def test_health_exposes_analysis_editor_flag(self, client):
        data = client.get("/api/health").json()
        assert data["analysisEditorEnabled"] is True

    def test_health_exposes_disabled_analysis_editor_flag(self, client, monkeypatch):
        import main

        monkeypatch.setattr(main, "settings", replace(main.settings, analysis_editor_enabled=False))
        data = client.get("/api/health").json()
        assert data["analysisEditorEnabled"] is False


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
        mock_document_service.find_with_store_links = AsyncMock(
            return_value=(
                Document(
                    id="d1",
                    filename="test.pdf",
                    content_type="application/pdf",
                    file_size=2048,
                    page_count=3,
                    storage_path="/tmp/test",
                ),
                [],
            )
        )

        resp = client.get("/api/documents/d1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "d1"
        assert data["fileSize"] == 2048
        assert data["pageCount"] == 3
        assert data["storeLinks"] == []
        assert data["currentAnalysisId"] is None

    def test_get_document_names_its_current_analysis(
        self, client, mock_document_service, mock_current_analysis
    ):
        mock_document_service.find_with_store_links = AsyncMock(
            return_value=(Document(id="d1", filename="test.pdf", storage_path="/tmp/test"), [])
        )
        mock_current_analysis.find_current_analysis_id = AsyncMock(return_value="a-older")

        resp = client.get("/api/documents/d1")

        assert resp.json()["currentAnalysisId"] == "a-older"
        mock_current_analysis.find_current_analysis_id.assert_awaited_once_with("d1")

    def test_document_list_leaves_the_current_analysis_out(
        self, client, mock_document_service, mock_current_analysis
    ):
        mock_document_service.find_all = AsyncMock(
            return_value=[Document(id="d1", filename="test.pdf", storage_path="/tmp/test")]
        )

        resp = client.get("/api/documents")

        assert resp.json()[0]["currentAnalysisId"] is None
        mock_current_analysis.find_current_analysis_id.assert_not_awaited()

    def test_get_document_maps_its_store_links(self, client, mock_document_service):
        from datetime import datetime

        from domain.value_objects import DocumentStoreLinkState
        from services.document_service import DocumentStoreLinkView

        pushed = datetime(2026, 11, 1, 12, 0, 0)
        mock_document_service.find_with_store_links = AsyncMock(
            return_value=(
                Document(id="d1", filename="test.pdf", storage_path="/tmp/test"),
                [
                    DocumentStoreLinkView("legal-v1", DocumentStoreLinkState.INGESTED, pushed),
                    DocumentStoreLinkView("rh", DocumentStoreLinkState.STALE, None),
                ],
            )
        )

        resp = client.get("/api/documents/d1")

        assert resp.json()["storeLinks"] == [
            {"store": "legal-v1", "state": "Ingested", "pushedAt": str(pushed)},
            {"store": "rh", "state": "Stale", "pushedAt": None},
        ]

    def test_get_document_not_found(self, client, mock_document_service):
        mock_document_service.find_with_store_links = AsyncMock(return_value=None)

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

    @pytest.mark.skipif(
        shutil.which("pdfinfo") is None,
        reason="poppler's pdfinfo is not installed",
    )
    def test_upload_counts_and_limits_pages_through_the_real_service(self, client, tmp_path):
        """The upload route on a real `DocumentService` and the real inspector."""
        from services.document_service import DocumentConfig, DocumentService
        from tests.test_document_service import pdf_with_pages

        service = DocumentService(
            document_repo=AsyncMock(),
            analysis_repo=AsyncMock(),
            config=DocumentConfig(max_page_count=2),
            link_repo=AsyncMock(),
            store_repo=AsyncMock(),
            pdf_inspector=PdfiumInspector(),
            file_store=LocalDocumentFileStore(str(tmp_path)),
        )
        two = pdf_with_pages((612, 792), (612, 792))
        three = pdf_with_pages((612, 792), (612, 792), (612, 792))

        with state_override(app, document_service=service):
            ok = client.post(
                "/api/documents/upload", files={"file": ("two.pdf", two, "application/pdf")}
            )
            too_many = client.post(
                "/api/documents/upload", files={"file": ("three.pdf", three, "application/pdf")}
            )
            not_pdf = client.post(
                "/api/documents/upload", files={"file": ("x.pdf", b"hello", "application/pdf")}
            )

        assert ok.status_code == 200
        assert ok.json()["pageCount"] == 2
        assert too_many.status_code == 400
        assert too_many.json() == {"detail": "Too many pages (3). Maximum allowed: 2"}
        assert not_pdf.status_code == 400
        assert not_pdf.json() == {"detail": "Invalid file: not a PDF document"}
        assert len(list(tmp_path.iterdir())) == 1

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

    def test_preview_missing_file(self, client, mock_document_service, tmp_path):
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(
                id="d1", filename="gone.pdf", storage_path=str(tmp_path / "gone.pdf")
            )
        )

        resp = client.get("/api/documents/d1/preview?page=1")

        assert resp.status_code == 404
        assert "not found on disk" in resp.json()["detail"]

    def test_preview_document_not_found(self, client, mock_document_service):
        mock_document_service.find_by_id = AsyncMock(return_value=None)

        response = client.get("/api/documents/missing/preview")

        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"

    def test_preview_page_poppler_does_not_render(self, client, mock_document_service, tmp_path):
        pdf = tmp_path / "short.pdf"
        pdf.write_bytes(b"%PDF-short")
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="short.pdf", storage_path=str(pdf))
        )

        with patch("infra.page_raster.convert_from_path", return_value=[]):
            resp = client.get("/api/documents/d1/preview?page=7")

        assert resp.status_code == 404
        # The adapter's message names the file; the response does not.
        assert resp.json()["detail"] == "Page 7 not found"

    def test_preview_reuses_raster_and_invalidates_when_pdf_changes(
        self, client, mock_document_service, tmp_path
    ):
        pdf = tmp_path / "preview.pdf"
        pdf.write_bytes(b"%PDF-first")
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="preview.pdf", storage_path=str(pdf))
        )

        rasterizer = MagicMock()
        rasterizer.render_page.return_value = b"rendered-png"
        render = rasterizer.render_page
        with state_override(
            app,
            preview_service=_preview_service(
                mock_document_service, tmp_path, rasterizer=rasterizer
            ),
        ):
            first = client.get("/api/documents/d1/preview?page=1")
            second = client.get("/api/documents/d1/preview?page=1")
            different_dpi = client.get("/api/documents/d1/preview?page=1&dpi=200")
            webp = client.get("/api/documents/d1/preview?page=1&format=webp")
            pdf.write_bytes(b"%PDF-changed-and-longer")
            changed = client.get("/api/documents/d1/preview?page=1")

        assert all(
            response.status_code == 200
            for response in (first, second, different_dpi, webp, changed)
        )
        assert first.content == second.content == b"rendered-png"
        assert first.headers["cache-control"] == "private, max-age=86400, immutable"
        assert webp.headers["content-type"] == "image/webp"
        assert render.call_count == 4
        # The renderer opens the PDF by path (#398): it never receives its bytes.
        assert render.call_args_list[0].args[0] == str(pdf)
        assert render.call_args_list[2].kwargs["fmt"] == "WEBP"
        assert render.call_args_list[-1].args[0] == str(pdf)

    def test_preview_accepts_a_replacement_cache(self, client, mock_document_service, tmp_path):
        pdf = tmp_path / "preview.pdf"
        pdf.write_bytes(b"%PDF-test")
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="preview.pdf", storage_path=str(pdf))
        )
        cache = MagicMock()
        cache.get.return_value = b"cached-preview"

        rasterizer = MagicMock()
        render = rasterizer.render_page
        with state_override(
            app,
            preview_service=_preview_service(
                mock_document_service, tmp_path, rasterizer=rasterizer, cache=cache
            ),
        ):
            response = client.get("/api/documents/d1/preview?page=1")

        assert response.status_code == 200
        assert response.content == b"cached-preview"
        cache.get.assert_called_once()
        cache.put.assert_not_called()
        render.assert_not_called()

    def test_page_sizes(self, client, mock_document_service, tmp_path):
        from tests.test_document_service import pdf_with_pages

        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(pdf_with_pages((612, 792), (842, 595)))
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="test.pdf", storage_path=str(pdf))
        )

        resp = client.get("/api/documents/d1/pages")

        assert resp.status_code == 200
        assert resp.json() == [
            {"pageNumber": 1, "width": 612.0, "height": 792.0},
            {"pageNumber": 2, "width": 842.0, "height": 595.0},
        ]

    def test_page_sizes_unknown_document(self, client, mock_document_service):
        mock_document_service.find_by_id = AsyncMock(return_value=None)

        resp = client.get("/api/documents/nope/pages")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Document not found"

    def test_page_sizes_missing_file(self, client, mock_document_service, tmp_path):
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(
                id="d1", filename="gone.pdf", storage_path=str(tmp_path / "gone.pdf")
            )
        )

        resp = client.get("/api/documents/d1/pages")

        assert resp.status_code == 404
        assert "not found on disk" in resp.json()["detail"]

    def test_page_sizes_unreadable_pdf(self, client, mock_document_service, tmp_path):
        broken = tmp_path / "broken.pdf"
        broken.write_bytes(b"%PDF-not really")
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="broken.pdf", storage_path=str(broken))
        )

        assert client.get("/api/documents/d1/pages").status_code == 422

    def test_preview_unrenderable_pdf(self, client, mock_document_service, tmp_path):
        pdf = tmp_path / "broken.pdf"
        pdf.write_bytes(b"%PDF-broken")
        mock_document_service.find_by_id = AsyncMock(
            return_value=Document(id="d1", filename="broken.pdf", storage_path=str(pdf))
        )

        with patch("infra.page_raster.convert_from_path", side_effect=RuntimeError("poppler")):
            resp = client.get("/api/documents/d1/preview?page=1")

        assert resp.status_code == 422
        assert resp.json()["detail"] == "Failed to generate preview"

    @pytest.mark.parametrize("route", ["preview", "pages"])
    def test_a_failed_document_lookup_is_a_server_error(self, client, mock_document_service, route):
        """Only reading the PDF answers 422: a database error is a 500."""
        mock_document_service.find_by_id = AsyncMock(side_effect=RuntimeError("database"))

        assert client.get(f"/api/documents/d1/{route}").status_code == 500

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
        mock_export_service.export_edited.assert_not_awaited()

    def test_export_document_supports_editor_result_when_enabled(self, client, mock_export_service):
        from services.export_service import ExportFormat

        mock_export_service.export_edited.return_value.file_path = None
        mock_export_service.export_edited.return_value.content = "# Edited"
        mock_export_service.export_edited.return_value.media_type = "text/markdown"
        mock_export_service.export_edited.return_value.filename = "report.md"

        resp = client.get("/api/documents/d1/export?format=md&analysisId=a1&edited=true")

        assert resp.status_code == 200
        assert resp.text == "# Edited"
        mock_export_service.export_edited.assert_awaited_once_with("d1", ExportFormat.MD, "a1")
        mock_export_service.export.assert_not_awaited()

    def test_editor_export_is_flagged(self, client, mock_export_service):
        with state_override(app, analysis_editor_enabled=False):
            resp = client.get("/api/documents/d1/export?format=md&analysisId=a1&edited=true")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "Analysis editor is disabled"}
        mock_export_service.export.assert_not_awaited()
        mock_export_service.export_edited.assert_not_awaited()

    def test_export_document_unsupported_format_returns_422(self, client, mock_export_service):
        resp = client.get("/api/documents/d1/export?format=docx")
        assert resp.status_code == 422

    def test_editor_export_validates_the_format_before_the_flag(self, client, mock_export_service):
        # The flag is checked in the route body, so FastAPI's 422 on an invalid
        # `format` comes before the "editor disabled" 404 (api/documents.py).
        with state_override(app, analysis_editor_enabled=False):
            resp = client.get("/api/documents/d1/export?format=docx&edited=true")

        assert resp.status_code == 422
        mock_export_service.export_edited.assert_not_awaited()

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

    def test_list_analysis_summaries_of_one_document(self, client, mock_analysis_service):
        # 12 INFO — the library counts a document's analyses from light rows.
        mock_analysis_service.find_all_summaries = AsyncMock(return_value=[])
        mock_analysis_service.find_summaries_by_document = AsyncMock(
            return_value=[AnalysisJob(id="j1", document_id="d1", document_filename="test.pdf")]
        )

        resp = client.get("/api/analyses/summaries?documentId=d1")

        assert resp.status_code == 200
        assert [summary["id"] for summary in resp.json()] == ["j1"]
        assert "contentMarkdown" not in resp.json()[0]
        mock_analysis_service.find_summaries_by_document.assert_awaited_once_with("d1")
        mock_analysis_service.find_all_summaries.assert_not_awaited()

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
        mock_analysis_service.create = AsyncMock(side_effect=ValueError("Document not found: d99"))

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
        job.mark_completed(AnalysisOutput("# Imported", "<p>Imported</p>", "[]", "{}"))
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
        from services.analysis_service import ImportDocumentNotFoundError

        mock_analysis_service.import_docling_document = AsyncMock(
            side_effect=ImportDocumentNotFoundError("Document not found: missing")
        )

        resp = client.post("/api/analyses/import", json={"documentId": "missing", "document": {}})

        assert resp.status_code == 404
        assert resp.json() == {"detail": "Document not found: missing"}

    def test_import_analysis_rejects_an_invalid_docling_document(
        self, client, mock_analysis_service
    ):
        from services.analysis_service import InvalidDoclingDocumentError

        mock_analysis_service.import_docling_document = AsyncMock(
            side_effect=InvalidDoclingDocumentError("Invalid Docling document: bad payload")
        )

        resp = client.post("/api/analyses/import", json={"documentId": "d1", "document": {}})

        assert resp.status_code == 400
        assert resp.json() == {"detail": "Invalid Docling document: bad payload"}

    def test_import_analysis_answers_400_for_any_other_rejection(
        self, client, mock_analysis_service
    ):
        mock_analysis_service.import_docling_document = AsyncMock(
            side_effect=ValueError("Analysis not found: j1")
        )

        resp = client.post("/api/analyses/import", json={"documentId": "d1", "document": {}})

        assert resp.status_code == 400
        assert resp.json() == {"detail": "Analysis not found: j1"}

    def test_delete_analysis(self, client, mock_analysis_service):
        mock_analysis_service.delete = AsyncMock(return_value=True)

        resp = client.delete("/api/analyses/j1")
        assert resp.status_code == 204

    def test_delete_analysis_not_found(self, client, mock_analysis_service):
        mock_analysis_service.delete = AsyncMock(return_value=False)

        resp = client.delete("/api/analyses/missing")
        assert resp.status_code == 404
