"""Document export application service."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from domain.value_objects import InputFileType

if TYPE_CHECKING:
    from domain.ports import AnalysisRepository, DocumentRepository


class ExportFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
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
    ) -> None:
        self._document_repo = document_repo
        self._analysis_repo = analysis_repo

    async def export(self, doc_id: str, format: ExportFormat) -> ExportResult:
        doc = await self._document_repo.find_by_id(doc_id)
        if not doc:
            raise ExportNotFoundError("Document not found")

        if format is ExportFormat.PDF:
            if InputFileType.from_filename(doc.filename) is not InputFileType.PDF:
                raise ExportNotFoundError("Source file is not a PDF document")
            if not Path(doc.storage_path).is_file():
                raise ExportNotFoundError("PDF file not found")
            return ExportResult(
                file_path=doc.storage_path,
                media_type="application/pdf",
                filename=doc.filename,
            )

        if format is ExportFormat.DOCX:
            if InputFileType.from_filename(doc.filename) is not InputFileType.DOCX:
                raise ExportNotFoundError("Source file is not a DOCX document")
            if not Path(doc.storage_path).is_file():
                raise ExportNotFoundError("DOCX file not found")
            return ExportResult(
                file_path=doc.storage_path,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=doc.filename,
            )

        if format is ExportFormat.MD:
            analysis = await self._analysis_repo.find_latest_completed(doc_id)
            if not analysis:
                raise ExportNotFoundError("No completed analysis found for this document")
            if not analysis.content_markdown:
                raise ExportNotFoundError("Markdown content not available")
            return ExportResult(
                content=analysis.content_markdown,
                media_type="text/markdown",
                filename=_build_export_filename(doc.filename, doc_id, ExportFormat.MD),
            )

        analysis = await self._analysis_repo.find_latest_completed_by_document(doc_id)
        if not analysis:
            raise ExportNotFoundError("JSON content not available")
        if not analysis.document_json:
            raise ExportNotFoundError("JSON content not available")
        return ExportResult(
            content=analysis.document_json,
            media_type="application/json",
            filename=_build_export_filename(doc.filename, doc_id, ExportFormat.JSON),
        )


class ExportNotFoundError(Exception):
    """Requested export payload is not available."""


def build_content_disposition(filename: str) -> str:
    """Match FileResponse-style UTF-8 filename handling for attachments."""
    quoted = quote(filename)
    if quoted != filename:
        return f"attachment; filename*=utf-8''{quoted}"
    return f'attachment; filename="{filename}"'


def _build_export_filename(source_filename: str, doc_id: str, format: ExportFormat) -> str:
    stem = Path(source_filename).stem if source_filename else doc_id
    return f"{stem}.{format.value}"
