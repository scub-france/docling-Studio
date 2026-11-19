"""Document export application service."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath
from typing import TYPE_CHECKING
from urllib.parse import quote

from domain.analysis_editing import AnalysisEditUnavailableError
from services.errors import ServiceError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from domain.models import AnalysisJob
    from domain.ports import (
        ActiveAnalysisResultReader,
        AnalysisRepository,
        DocumentFileStore,
        DocumentRepository,
    )


class ExportFormat(StrEnum):
    PDF = "pdf"
    MD = "md"
    JSON = "json"


@dataclass(frozen=True)
class ExportResult:
    media_type: str
    filename: str
    content: str | None = None
    file_path: str | None = None


class ExportService:
    """Orchestrates document exports across document + analysis state."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        active_result_service: ActiveAnalysisResultReader,
        *,
        file_store: DocumentFileStore,
    ) -> None:
        self._document_repo = document_repo
        self._analysis_repo = analysis_repo
        self._file_store = file_store
        self._active_result_service = active_result_service

    async def export(
        self,
        doc_id: str,
        format: ExportFormat,
        analysis_id: str | None = None,
    ) -> ExportResult:
        """Export the source PDF, or the Markdown / JSON of an analysis.

        `analysis_id` selects an immutable analysis, as stored; omission
        selects the document's current analysis with its saved edits. The PDF
        is always the source file.
        """
        return await self._export(
            doc_id, format, lambda: self._load_exported_analysis(doc_id, analysis_id)
        )

    async def export_edited(
        self,
        doc_id: str,
        format: ExportFormat,
        analysis_id: str | None,
    ) -> ExportResult:
        """Export like `export`, with Markdown / JSON taken from the saved editor result."""
        return await self._export(
            doc_id, format, lambda: self._load_edited_analysis(doc_id, analysis_id)
        )

    async def _export(
        self,
        doc_id: str,
        format: ExportFormat,
        resolve_analysis: Callable[[], Awaitable[AnalysisJob | None]],
    ) -> ExportResult:
        doc = await self._document_repo.find_by_id(doc_id)
        if not doc:
            raise ExportNotFoundError("Document not found")

        if format is ExportFormat.PDF:
            # Resolved as the preview does: a path stored by another runtime
            # (Docker, read from the host) still finds the uploaded file.
            path = self._file_store.resolve(doc.storage_path)
            if not self._file_store.has_file(path):
                raise ExportNotFoundError("PDF file not found")
            return ExportResult(
                file_path=path,
                media_type="application/pdf",
                filename=doc.filename,
            )

        analysis = await resolve_analysis()
        if format is ExportFormat.MD:
            if not analysis:
                raise ExportNotFoundError("No completed analysis found for this document")
            if not analysis.content_markdown:
                raise ExportNotFoundError("Markdown content not available")
            return ExportResult(
                content=analysis.content_markdown,
                media_type="text/markdown",
                filename=_build_export_filename(doc.filename, doc_id, ExportFormat.MD),
            )

        if not analysis or not analysis.document_json:
            raise ExportNotFoundError("JSON content not available")
        return ExportResult(
            content=analysis.document_json,
            media_type="application/json",
            filename=_build_export_filename(doc.filename, doc_id, ExportFormat.JSON),
        )

    async def _load_exported_analysis(self, doc_id: str, analysis_id: str | None) -> AnalysisJob:
        """The requested analysis as stored, or else the current one with its edits."""
        if analysis_id:
            return await self._load_requested_analysis(doc_id, analysis_id)
        return await self._load_current_edited(doc_id)

    async def _load_requested_analysis(self, doc_id: str, analysis_id: str) -> AnalysisJob:
        """The analysis the caller asked for: it must be a completed one of `doc_id`."""
        analysis = await self._analysis_repo.find_by_id(analysis_id)
        if not analysis or not analysis.can_be_current_of(doc_id):
            raise ExportNotFoundError(f"Analysis not found: {analysis_id}")
        return analysis

    async def _load_current_edited(self, doc_id: str) -> AnalysisJob:
        try:
            return (await self._active_result_service.load_current_edited(doc_id)).job
        except AnalysisEditUnavailableError as exc:
            raise ExportNotFoundError(str(exc)) from exc

    async def _load_edited_analysis(self, doc_id: str, analysis_id: str | None) -> AnalysisJob:
        if not analysis_id:
            raise ExportNotFoundError("Edited analysis export is unavailable")
        await self._load_requested_analysis(doc_id, analysis_id)
        try:
            return (await self._active_result_service.load_editor(doc_id, analysis_id)).job
        except AnalysisEditUnavailableError as exc:
            raise ExportNotFoundError(str(exc)) from exc


class ExportNotFoundError(ServiceError):
    """Requested export payload is not available."""

    http_status = 404


def build_content_disposition(filename: str) -> str:
    """Match FileResponse-style UTF-8 filename handling for attachments."""
    quoted = quote(filename)
    if quoted != filename:
        return f"attachment; filename*=utf-8''{quoted}"
    return f'attachment; filename="{filename}"'


def _build_export_filename(source_filename: str, doc_id: str, format: ExportFormat) -> str:
    stem = PurePath(source_filename).stem if source_filename else doc_id
    return f"{stem}.{format.value}"
