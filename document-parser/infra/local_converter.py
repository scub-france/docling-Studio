"""Local Docling converter — runs Docling as a Python library in-process.

This adapter implements the DocumentConverter port using the Docling library
directly. It wraps the blocking DocumentConverter in asyncio.to_thread for
non-blocking execution.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter as DoclingConverter
from docling.document_converter import PdfFormatOption, WordFormatOption
from docling_core.types.doc import (
    CodeItem,
    DocItem,
    FloatingItem,
    FormulaItem,
    GroupItem,
    ListItem,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)

from domain.value_objects import (
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    ConversionOptions,
    ConversionResult,
    PageDetail,
    PageElement,
)
from infra.bbox import to_topleft_list
from infra.settings import settings

logger = logging.getLogger(__name__)

# Thread lock — DoclingConverter is not thread-safe.
# Uses a timeout to prevent a frozen conversion from blocking all others.
_converter_lock = threading.Lock()

# Default converter (lazy-init on first request)
_default_converter: DoclingConverter | None = None


# ---------------------------------------------------------------------------
# Element type detection
# ---------------------------------------------------------------------------

_ELEMENT_TYPE_MAP: list[tuple[type, str]] = [
    (TableItem, "table"),
    (PictureItem, "picture"),
    (TitleItem, "title"),
    (SectionHeaderItem, "section_header"),
    (ListItem, "list"),
    (FormulaItem, "formula"),
    (CodeItem, "code"),
    (FloatingItem, "floating"),
    (TextItem, "text"),
]


def _get_element_type(item: DocItem) -> str:
    for cls, type_name in _ELEMENT_TYPE_MAP:
        if isinstance(item, cls):
            return type_name
    return "text"


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------


def _build_docling_converter(options: ConversionOptions) -> DoclingConverter:
    table_options = TableStructureOptions(
        do_cell_matching=True,
        mode=TableFormerMode.ACCURATE if options.table_mode == "accurate" else TableFormerMode.FAST,
    )

    pipeline_options = PdfPipelineOptions(
        do_ocr=options.do_ocr,
        do_table_structure=options.do_table_structure,
        table_structure_options=table_options,
        do_code_enrichment=options.do_code_enrichment,
        do_formula_enrichment=options.do_formula_enrichment,
        do_picture_classification=options.do_picture_classification,
        do_picture_description=options.do_picture_description,
        generate_page_images=options.generate_page_images,
        generate_picture_images=options.generate_picture_images,
        images_scale=options.images_scale,
        document_timeout=settings.document_timeout,
    )

    return DoclingConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            InputFormat.DOCX: WordFormatOption(pipeline_options=pipeline_options),
        }
    )


def _ensure_default_converter() -> DoclingConverter:
    global _default_converter
    if _default_converter is None:
        try:
            _default_converter = _build_docling_converter(ConversionOptions())
        except Exception:
            raise
    return _default_converter


def _select_converter(options: ConversionOptions) -> DoclingConverter:
    if options.is_default():
        return _ensure_default_converter()
    return _build_docling_converter(options)


# ---------------------------------------------------------------------------
# Page extraction
# ---------------------------------------------------------------------------


def _extract_pages_detail(doc_result) -> tuple[list[PageDetail], int]:
    pages: dict[int, PageDetail] = {}
    document = doc_result.document
    skipped = 0

    for page_key, page_obj in document.pages.items():
        page_no = int(page_key) if isinstance(page_key, str) else page_key
        pages[page_no] = PageDetail(
            page_number=page_no,
            width=page_obj.size.width,
            height=page_obj.size.height,
        )

    for item, level in document.iterate_items():
        ok = _process_content_item(item, level, pages)
        if not ok:
            skipped += 1

    sorted_pages = sorted(pages.values(), key=lambda p: p.page_number)
    return sorted_pages, skipped


def _process_content_item(
    item: DocItem | GroupItem,
    level: int,
    pages: dict[int, PageDetail],
) -> bool:
    if isinstance(item, GroupItem):
        return True

    if not isinstance(item, DocItem) or not item.prov:
        return False

    for prov in item.prov:
        try:
            page_no = prov.page_no
            if page_no not in pages:
                logger.warning(
                    "Page %d not found in document metadata — using US Letter fallback (%sx%s pt)",
                    page_no,
                    DEFAULT_PAGE_WIDTH,
                    DEFAULT_PAGE_HEIGHT,
                )
                pages[page_no] = PageDetail(
                    page_number=page_no, width=DEFAULT_PAGE_WIDTH, height=DEFAULT_PAGE_HEIGHT
                )

            page_height = pages[page_no].height

            bbox = [0.0, 0.0, 0.0, 0.0]
            if prov.bbox:
                bbox = to_topleft_list(prov.bbox, page_height)

            element_type = _get_element_type(item)

            content = getattr(item, "text", "") or ""
            if isinstance(item, TableItem):
                with contextlib.suppress(AttributeError, ValueError):
                    content = item.export_to_markdown()

            pages[page_no].elements.append(
                PageElement(
                    type=element_type,
                    bbox=bbox,
                    content=content,
                    level=level,
                    self_ref=getattr(item, "self_ref", "") or "",
                )
            )
        except (AttributeError, KeyError, TypeError, ValueError):
            logger.warning(
                "Skipping item %s on page %s",
                type(item).__name__,
                getattr(prov, "page_no", "?"),
                exc_info=True,
            )
            return False

    return True


# ---------------------------------------------------------------------------
# Synchronous conversion (called via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _convert_sync(
    file_path: str,
    options: ConversionOptions,
    *,
    page_range: tuple[int, int] | None = None,
) -> ConversionResult:
    acquired = _converter_lock.acquire(timeout=settings.lock_timeout)
    if not acquired:
        raise TimeoutError(
            f"Could not acquire converter lock within {settings.lock_timeout}s — "
            "a previous conversion may be frozen"
        )
    try:
        conv = _select_converter(options)
        kwargs: dict = {}
        if settings.max_page_count > 0:
            kwargs["max_num_pages"] = settings.max_page_count
        if settings.max_file_size > 0:
            kwargs["max_file_size"] = settings.max_file_size
        if page_range is not None:
            kwargs["page_range"] = page_range
        result = conv.convert(file_path, **kwargs)
    finally:
        _converter_lock.release()

    doc = result.document
    page_count = len(doc.pages)
    pages_detail, skipped = _extract_pages_detail(result)

    if not pages_detail:
        # Fallback for flow-format documents where Docling produced no page
        # model (e.g. native DOCX analysis when LibreOffice pre-conversion
        # failed).  Creates one synthetic page so the viewer can at least
        # show the LibreOffice preview image.
        pages_detail = [
            PageDetail(page_number=1, width=DEFAULT_PAGE_WIDTH, height=DEFAULT_PAGE_HEIGHT)
        ]

    if skipped > 0:
        logger.info("Parsed: %d pages, %d items skipped", len(pages_detail), skipped)

    return ConversionResult(
        page_count=page_count or len(pages_detail) or 1,
        content_markdown=doc.export_to_markdown(),
        content_html=doc.export_to_html(),
        pages=pages_detail,
        skipped_items=skipped,
        document_json=json.dumps(doc.export_to_dict()),
    )


# ---------------------------------------------------------------------------
# DOCX pre-conversion helper
# ---------------------------------------------------------------------------


def _docx_to_pdf_for_analysis(docx_path: str) -> str | None:
    """Convert a DOCX to PDF via LibreOffice and save it alongside the source file.

    The PDF is written to <same_dir>/<same_stem>.pdf so it can be reused by
    both the analysis pipeline (here) and the preview endpoint — LibreOffice
    runs at most once per document.

    Returns the persistent PDF path on success, None on failure.
    """
    companion_pdf = str(Path(docx_path).with_suffix(".pdf"))

    # Reuse if already produced (e.g. a preview request ran first).
    if os.path.exists(companion_pdf):
        return companion_pdf

    tmp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                tmp_dir,
                docx_path,
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
        tmp_pdf = os.path.join(tmp_dir, Path(docx_path).stem + ".pdf")
        if os.path.exists(tmp_pdf):
            shutil.move(tmp_pdf, companion_pdf)
            return companion_pdf
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("LibreOffice DOCX→PDF pre-conversion failed: %s", exc)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return None


# ---------------------------------------------------------------------------
# Public adapter class
# ---------------------------------------------------------------------------


class LocalConverter:
    """Adapter that runs Docling locally as a Python library."""

    # In-process — the orchestrator may slice long docs into page batches
    # and merge results (cf. AnalysisService._run_batched_conversion).
    supports_page_batching: bool = True

    async def convert(
        self,
        file_path: str,
        options: ConversionOptions,
        *,
        page_range: tuple[int, int] | None = None,
    ) -> ConversionResult:
        # For DOCX files, pre-convert to PDF outside the converter lock.
        # LibreOffice can take several seconds; doing it before acquiring
        # _converter_lock avoids blocking other analyses in the meantime.
        # Docling then analyses the PDF and returns a proper page/bbox model.
        analysis_path = file_path

        if Path(file_path).suffix.lower() == ".docx":
            pdf_path = await asyncio.to_thread(_docx_to_pdf_for_analysis, file_path)
            if pdf_path:
                analysis_path = pdf_path
            else:
                logger.warning(
                    "Falling back to native DOCX analysis for %s — "
                    "page count and bboxes will not be available",
                    file_path,
                )

        return await asyncio.to_thread(_convert_sync, analysis_path, options, page_range=page_range)
