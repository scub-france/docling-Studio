"""Tests for ExportService — which analysis a Markdown / JSON export reads."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.analysis_editing import AnalysisEditUnavailableError
from domain.models import AnalysisJob, AnalysisStatus, Document
from infra.document_file_store import LocalDocumentFileStore
from services.export_service import ExportFormat, ExportNotFoundError, ExportService
from tests.current_result_fakes import UneditedResultReader


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
    current_analysis.load_current_original.return_value = _analysis("current")
    return ExportService(
        document_repo=document_repo,
        analysis_repo=analysis_repo,
        active_result_service=UneditedResultReader(current_analysis, analysis_repo),
        # The real store: `has_file` checks the path it is given, whatever its
        # upload directory.
        file_store=file_store or LocalDocumentFileStore("uploads"),
    )


def _current(service: ExportService) -> AsyncMock:
    """The current-analysis mock behind the service's result reader."""
    return service._active_result_service._current


class _FakeFileStore:
    """Files live under their resolved path only, as after a Docker upload read on the host."""

    def __init__(self, resolved: dict[str, str], files: set[str]) -> None:
        self._resolved = resolved
        self._files = files

    def resolve(self, storage_path: str) -> str:
        return self._resolved.get(storage_path, storage_path)

    def has_file(self, storage_path: str) -> bool:
        return storage_path in self._files


class TestExportAnalysisSelection:
    @pytest.mark.asyncio
    async def test_missing_active_selection_is_not_found(self):
        service = _make_service()
        active = AsyncMock()
        active.load_current_edited.side_effect = AnalysisEditUnavailableError(
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
        _current(service).load_current_original.assert_awaited_once_with("d1")
        service._analysis_repo.find_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_current_analysis_is_not_found(self):
        service = _make_service()
        _current(service).load_current_original.return_value = None

        with pytest.raises(ExportNotFoundError, match="no active analysis"):
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
        file_store.resolve.side_effect = lambda path: path
        file_store.has_file.return_value = False
        service = _make_service(file_store=file_store)
        service._document_repo.find_by_id.return_value = Document(
            id="d1", filename="report.pdf", storage_path="/srv/uploads/gone.pdf"
        )

        with pytest.raises(ExportNotFoundError, match=r"^PDF file not found$"):
            await service.export("d1", ExportFormat.PDF)

        file_store.has_file.assert_called_once_with("/srv/uploads/gone.pdf")

    @pytest.mark.asyncio
    async def test_pdf_export_reads_the_path_the_preview_resolves(self):
        """A Docker storage path read on the host: export it, as the preview shows it."""
        store = _FakeFileStore(
            resolved={"/app/uploads/report.pdf": "/host/uploads/report.pdf"},
            files={"/host/uploads/report.pdf"},
        )
        service = _make_service(file_store=store)
        service._document_repo.find_by_id.return_value = Document(
            id="d1", filename="report.pdf", storage_path="/app/uploads/report.pdf"
        )

        result = await service.export("d1", ExportFormat.PDF)

        assert result.file_path == "/host/uploads/report.pdf"
