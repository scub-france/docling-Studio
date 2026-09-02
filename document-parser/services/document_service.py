"""Document service — file upload, storage, and preview orchestration."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pdf2image import convert_from_bytes, pdfinfo_from_bytes

from domain.models import Document
from domain.value_objects import InputFileType

if TYPE_CHECKING:
    from domain.ports import AnalysisRepository, DocumentRepository

logger = logging.getLogger(__name__)

_UPLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB chunks for streaming writes


@dataclass
class DocumentConfig:
    """Configuration values needed by DocumentService, extracted from settings."""

    upload_dir: str = "uploads"
    max_file_size_mb: int = 0
    max_page_count: int = 0


class DocumentService:
    """Orchestrates document upload, storage, and preview."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        config: DocumentConfig,
    ):
        self._document_repo = document_repo
        self._analysis_repo = analysis_repo
        self._config = config
        self._upload_dir = config.upload_dir
        self._max_file_size = (
            config.max_file_size_mb * 1024 * 1024 if config.max_file_size_mb > 0 else 0
        )
        self._max_page_count = config.max_page_count

    @property
    def max_file_size(self) -> int:
        return self._max_file_size

    @property
    def max_file_size_mb(self) -> int:
        return self._config.max_file_size_mb

    async def upload(self, filename: str, content_type: str, file_content: bytes) -> Document:
        """Save uploaded file to disk and persist metadata.

        Writes the file in fixed-size chunks to keep peak memory usage low.
        The blocking disk write and the poppler subprocess (`pdfinfo`) are
        offloaded to a worker thread so the FastAPI event loop stays free
        for other requests during large uploads.
        """
        if 0 < self._max_file_size < len(file_content):
            raise ValueError(f"File too large (max {self._config.max_file_size_mb} MB)")

        file_type = InputFileType.from_filename(filename)

        if not file_type:
            raise ValueError("Invalid file type. Accepted formats: PDF, DOCX.")

        safe_name = f"{uuid.uuid4()}.{file_type.value}"
        file_path = os.path.join(self._upload_dir, safe_name)

        # Disk write + poppler subprocess — both blocking. Offload together
        # so we cross the thread boundary once instead of twice.
        page_count = await asyncio.to_thread(
            _persist_and_count, self._upload_dir, file_path, file_content, file_type
        )

        if 0 < self._max_page_count < page_count and page_count is not None:
            await asyncio.to_thread(os.unlink, file_path)
            raise ValueError(
                f"Too many pages ({page_count}). Maximum allowed: {self._max_page_count}"
            )

        doc = Document(
            filename=filename,
            content_type=content_type,
            file_size=len(file_content),
            page_count=page_count,
            storage_path=os.path.abspath(file_path),
        )
        await self._document_repo.insert(doc)
        return doc

    async def find_all(self) -> list[Document]:
        """Return all documents, newest first."""
        return await self._document_repo.find_all()

    async def find_by_id(self, doc_id: str) -> Document | None:
        """Find a document by its ID, or return None."""
        return await self._document_repo.find_by_id(doc_id)

    async def delete(self, doc_id: str) -> bool:
        """Delete document file, associated analyses, and database record."""
        doc = await self._document_repo.find_by_id(doc_id)
        if not doc:
            return False

        # Delete associated analyses first (cascade)
        await self._analysis_repo.delete_by_document(doc_id)

        # Delete file from disk (only if inside upload dir)
        try:
            real_upload_dir = os.path.realpath(self._upload_dir)
            real_path = os.path.realpath(doc.storage_path)
            if real_path.startswith(real_upload_dir + os.sep) and os.path.exists(real_path):
                os.unlink(real_path)
                # Also remove the companion PDF produced for DOCX preview/analysis.
                companion = Path(doc.storage_path).with_suffix(".pdf")
                if companion.exists() and str(companion) != doc.storage_path:
                    companion.unlink(missing_ok=True)
            elif os.path.exists(doc.storage_path):
                logger.warning("Refused to delete file outside upload dir: %s", doc.storage_path)
        except FileNotFoundError:
            logger.info("File already removed: %s", doc.storage_path)
        except PermissionError:
            logger.error("Permission denied deleting file: %s", doc.storage_path)
        except OSError:
            logger.warning("Could not delete file: %s", doc.storage_path, exc_info=True)

        return await self._document_repo.delete(doc_id)

    @staticmethod
    def generate_preview(
        file_content: bytes,
        page: int = 1,
        dpi: int = 150,
        *,
        file_type: InputFileType = InputFileType.PDF,
        storage_path: str | None = None,
    ) -> bytes:
        """Generate a PNG preview of a specific document page.

        For DOCX files, a companion PDF (<same_stem>.pdf) is used if it already
        exists (created by the analysis pipeline). If not, LibreOffice converts
        on the fly and the result is cached as the companion PDF so subsequent
        requests and the analysis step can reuse it without calling LibreOffice again.
        """
        if file_type == InputFileType.DOCX:
            companion = Path(storage_path).with_suffix(".pdf") if storage_path else None
            if companion and companion.exists():
                file_content = companion.read_bytes()
            else:
                file_content = _docx_to_pdf_bytes(file_content)
                if companion:
                    companion.write_bytes(file_content)
        images = convert_from_bytes(file_content, first_page=page, last_page=page, dpi=dpi)
        if not images:
            raise ValueError(f"Page {page} not found")
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        return buf.getvalue()


def _docx_to_pdf_bytes(file_content: bytes) -> bytes:
    """Convert DOCX bytes to PDF bytes via LibreOffice headless.

    Writes the DOCX to a temp directory, runs LibreOffice --headless --convert-to pdf,
    reads the resulting PDF, then cleans up. Raises FileNotFoundError if LibreOffice
    is not installed, ValueError if the conversion fails.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "input.docx")
        pdf_path = os.path.join(tmpdir, "input.pdf")
        with open(docx_path, "wb") as fh:
            fh.write(file_content)
        try:
            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tmpdir,
                    docx_path,
                ],
                capture_output=True,
                timeout=60,
                check=False,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "LibreOffice is not installed or not in PATH — cannot generate DOCX preview"
            ) from exc
        if not os.path.exists(pdf_path):
            raise ValueError(
                "LibreOffice DOCX→PDF conversion failed: " + result.stderr.decode(errors="replace")
            )
        with open(pdf_path, "rb") as fh:
            return fh.read()


def _persist_and_count(
    upload_dir: str, file_path: str, file_content: bytes, file_type: InputFileType
) -> int | None:
    """Write the uploaded bytes to disk and return the page count.

    Synchronous helper meant to be invoked through `asyncio.to_thread` so
    the chunked write loop and the poppler subprocess never block the
    FastAPI event loop.
    """
    os.makedirs(upload_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        for offset in range(0, len(file_content), _UPLOAD_CHUNK_SIZE):
            f.write(file_content[offset : offset + _UPLOAD_CHUNK_SIZE])
    return _count_pages(file_content, file_type)


def _count_pages(file_content: bytes, file_type: InputFileType) -> int | None:
    """Count PDF pages using poppler via pdf2image."""
    if file_type == InputFileType.PDF:
        try:
            info = pdfinfo_from_bytes(file_content)
            return info.get("Pages")
        except (FileNotFoundError, OSError) as exc:
            logger.warning("Could not count pages: %s", exc)
            return None
        except Exception:
            logger.warning("Unexpected error counting pages", exc_info=True)
            return None
    else:
        return None
