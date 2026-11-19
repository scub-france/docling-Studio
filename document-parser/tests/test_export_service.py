"""Tests for ExportService — which analysis a Markdown / JSON export reads."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.analysis_editing import AnalysisEditUnavailableError
from domain.models import AnalysisJob, AnalysisStatus, Document
from infra.document_file_store import LocalDocumentFileStore
from services.export_service import ExportFormat, ExportNotFoundError, ExportService


def _analysis(
    analysis_id: str,
    document_id: str = "d1",
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
) -> AnalysisJob:
    return AnalysisJob(
        id=analysis_id,
        document_id=document_id,
        status=status,
        content_markdown=f"# {analysis_id}",
        document_json=f'{{"id": "{analysis_id}"}}',
    )


def _make_service(requested: AnalysisJob | None = None, file_store=None) -> ExportService:
    """A service over one doc whose current analysis is `current`."""
    document_repo = AsyncMock()
    document_repo.find_by_id.return_value = Document(id="d1", filename="report.pdf")
    analysis_repo = AsyncMock()
    analysis_repo.find_by_id.return_value = requested
    current_analysis = AsyncMock()
    current_analysis.load_current_analysis.return_value = _analysis("current")
    return ExportService(
        document_repo=document_repo,
        analysis_repo=analysis_repo,
        current_analysis=current_analysis,
        # The real store: `has_file` checks the path it is given, whatever its
        # upload directory.
        file_store=file_store or LocalDocumentFileStore("uploads"),
    )


class TestExportAnalysisSelection:
    @pytest.mark.asyncio
    async def test_missing_active_selection_is_not_found(self):
        service = _make_service()
        active = AsyncMock()
        active.load_active_result.side_effect = AnalysisEditUnavailableError(
            "This document has no active analysis"
        )
        service._active_result_service = active

        with pytest.raises(ExportNotFoundError, match="no active analysis"):
            await service.export("d1", ExportFormat.MD)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("format", "expected"),
        [(ExportFormat.MD, "# current"), (ExportFormat.JSON, '{"id": "current"}')],
    )
    async def test_defaults_to_the_current_analysis(self, format, expected):
        service = _make_service()

        result = await service.export("d1", format)

        assert result.content == expected
        service._current.load_current_analysis.assert_awaited_once_with("d1")
        service._analysis_repo.find_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_current_analysis_is_not_found(self):
        service = _make_service()
        service._current.load_current_analysis.return_value = None

        with pytest.raises(ExportNotFoundError, match="No completed analysis"):
            await service.export("d1", ExportFormat.MD)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("format", "expected"),
        [(ExportFormat.MD, "# older"), (ExportFormat.JSON, '{"id": "older"}')],
    )
    async def test_exports_the_requested_analysis(self, format, expected):
        service = _make_service(requested=_analysis("older"))

        result = await service.export("d1", format, "older")

        assert result.content == expected
        service._analysis_repo.find_by_id.assert_awaited_once_with("older")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "requested",
        [
            None,
            _analysis("older", document_id="another-doc"),
            _analysis("older", status=AnalysisStatus.FAILED),
        ],
        ids=["unknown", "other-document", "not-completed"],
    )
    async def test_refuses_an_analysis_it_cannot_export(self, requested):
        service = _make_service(requested=requested)

        with pytest.raises(ExportNotFoundError, match="Analysis not found: older"):
            await service.export("d1", ExportFormat.MD, "older")

    @pytest.mark.asyncio
    async def test_pdf_export_ignores_the_analysis(self, tmp_path):
        pdf = tmp_path / "report.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        service = _make_service()
        service._document_repo.find_by_id.return_value = Document(
            id="d1", filename="report.pdf", storage_path=str(pdf)
        )

        result = await service.export("d1", ExportFormat.PDF, "older")

        assert result.file_path == str(pdf)
        service._analysis_repo.find_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_pdf_export_asks_the_file_store_for_the_stored_file(self):
        file_store = MagicMock()
        file_store.has_file.return_value = False
        service = _make_service(file_store=file_store)
        service._document_repo.find_by_id.return_value = Document(
            id="d1", filename="report.pdf", storage_path="/srv/uploads/gone.pdf"
        )

        with pytest.raises(ExportNotFoundError, match=r"^PDF file not found$"):
            await service.export("d1", ExportFormat.PDF)

        file_store.has_file.assert_called_once_with("/srv/uploads/gone.pdf")
