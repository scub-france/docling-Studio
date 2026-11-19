"""The PDF inspector and the document file store must be wired where the app
builds its services.

`AnalysisService` accepts no inspector, and then counts 0 pages: batching is
silently off. Tests build it that way; the application must not.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from bootstrap.factories import (
    build_analysis_service,
    build_document_file_store,
    build_document_service,
)
from infra.document_file_store import LocalDocumentFileStore
from infra.pdf_inspector import PdfiumInspector
from infra.settings import settings


def test_analysis_service_is_built_with_the_pdf_inspector():
    # The converter and chunker are not the subject: keep Docling out of it.
    with (
        patch("bootstrap.factories.build_converter", return_value=MagicMock()),
        patch("bootstrap.factories.build_chunker", return_value=MagicMock()),
    ):
        service = build_analysis_service(AsyncMock(), AsyncMock(), None)

    assert isinstance(service._pdf_inspector, PdfiumInspector)


def test_document_service_is_built_with_the_pdf_inspector():
    service = build_document_service(
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        file_store=MagicMock(),
        current_analysis=AsyncMock(),
    )

    assert isinstance(service._pdf_inspector, PdfiumInspector)


def test_the_wiring_test_would_fail_without_an_inspector():
    """Guards the assertion above: a service built by hand has no inspector."""
    from services.analysis_service import AnalysisService

    service = AnalysisService(
        converter=MagicMock(), analysis_repo=AsyncMock(), document_repo=AsyncMock()
    )

    assert service._pdf_inspector is None


def test_the_file_store_is_rooted_at_the_configured_upload_dir():
    store = build_document_file_store()

    assert isinstance(store, LocalDocumentFileStore)
    assert store._upload_dir == settings.upload_dir


def test_document_service_is_built_with_the_given_file_store():
    store = build_document_file_store()

    service = build_document_service(
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        file_store=store,
        current_analysis=AsyncMock(),
    )

    assert service._file_store is store
