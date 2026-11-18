"""The PDF inspector must be wired where the app builds its services.

`AnalysisService` accepts no inspector, and then counts 0 pages: batching is
silently off. Tests build it that way; the application must not.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from bootstrap.factories import build_analysis_service, build_document_service
from infra.pdf_inspector import PdfiumInspector


def test_analysis_service_is_built_with_the_pdf_inspector():
    # The converter and chunker are not the subject: keep Docling out of it.
    with (
        patch("bootstrap.factories.build_converter", return_value=MagicMock()),
        patch("bootstrap.factories.build_chunker", return_value=MagicMock()),
    ):
        service = build_analysis_service(AsyncMock(), AsyncMock(), None)

    assert isinstance(service._pdf_inspector, PdfiumInspector)


def test_document_service_is_built_with_the_pdf_inspector():
    service = build_document_service(AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())

    assert isinstance(service._pdf_inspector, PdfiumInspector)


def test_the_wiring_test_would_fail_without_an_inspector():
    """Guards the assertion above: a service built by hand has no inspector."""
    from services.analysis_service import AnalysisService

    service = AnalysisService(
        converter=MagicMock(), analysis_repo=AsyncMock(), document_repo=AsyncMock()
    )

    assert service._pdf_inspector is None
