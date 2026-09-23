"""Tests for ExportService — which analysis a Markdown / JSON export reads."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from domain.models import AnalysisJob, AnalysisStatus, Document
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


def _make_service(requested: AnalysisJob | None = None) -> ExportService:
    """A service over one doc whose latest completed analysis is `latest`."""
    document_repo = AsyncMock()
    document_repo.find_by_id.return_value = Document(id="d1", filename="report.pdf")
    analysis_repo = AsyncMock()
    analysis_repo.find_latest_completed.return_value = _analysis("latest")
    analysis_repo.find_latest_completed_by_document.return_value = _analysis("latest")
    analysis_repo.find_by_id.return_value = requested
    return ExportService(document_repo=document_repo, analysis_repo=analysis_repo)


class TestExportAnalysisSelection:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("format", "expected"),
        [(ExportFormat.MD, "# latest"), (ExportFormat.JSON, '{"id": "latest"}')],
    )
    async def test_defaults_to_the_latest_completed_analysis(self, format, expected):
        service = _make_service()

        result = await service.export("d1", format)

        assert result.content == expected
        service._analysis_repo.find_by_id.assert_not_called()

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
