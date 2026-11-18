"""`AnalysisService` counts pages for batching through the `PdfInspector` port."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from services.analysis_service import AnalysisService


def _service(inspector) -> AnalysisService:
    return AnalysisService(
        converter=MagicMock(),
        analysis_repo=MagicMock(),
        document_repo=MagicMock(),
        pdf_inspector=inspector,
    )


async def test_counts_through_the_inspector_off_the_event_loop():
    loop_thread = threading.get_ident()
    seen: list[int] = []
    inspector = MagicMock()

    def page_count(path):
        seen.append(threading.get_ident())
        return 12

    inspector.page_count.side_effect = page_count

    with patch("services.analysis_service._count_pdf_pages") as fallback:
        assert await _service(inspector)._count_pages("/doc.pdf") == 12

    inspector.page_count.assert_called_once_with("/doc.pdf")
    fallback.assert_not_called()
    assert seen and seen[0] != loop_thread


async def test_an_unreadable_pdf_disables_batching():
    inspector = MagicMock()
    inspector.page_count.side_effect = RuntimeError("not a PDF")

    assert await _service(inspector)._count_pages("/doc.pdf") == 0


async def test_without_an_inspector_it_keeps_the_local_count():
    with patch("services.analysis_service._count_pdf_pages", return_value=5) as fallback:
        assert await _service(None)._count_pages("/doc.pdf") == 5

    fallback.assert_called_once_with("/doc.pdf")
