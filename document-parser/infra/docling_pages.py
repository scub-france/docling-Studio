"""Shared Docling-to-page mapping for conversion and imported analyses."""

from __future__ import annotations

import contextlib
import logging

from docling_core.types.doc import (
    CodeItem,
    DocItem,
    DoclingDocument,
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

from domain.value_objects import DEFAULT_PAGE_HEIGHT, DEFAULT_PAGE_WIDTH, PageDetail, PageElement
from infra.bbox import to_topleft_list

logger = logging.getLogger(__name__)

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
    for item_class, type_name in _ELEMENT_TYPE_MAP:
        if isinstance(item, item_class):
            return type_name
    return "text"


def extract_pages_detail(document: DoclingDocument) -> tuple[list[PageDetail], int]:
    """Return pages and positioned elements from a Docling document."""
    pages: dict[int, PageDetail] = {}
    skipped = 0

    for page_key, page_obj in document.pages.items():
        page_no = int(page_key) if isinstance(page_key, str) else page_key
        pages[page_no] = PageDetail(
            page_number=page_no,
            width=page_obj.size.width,
            height=page_obj.size.height,
        )

    for item, level in document.iterate_items():
        if not _process_content_item(item, level, pages):
            skipped += 1

    return sorted(pages.values(), key=lambda page: page.page_number), skipped


def _process_content_item(
    item: DocItem | GroupItem,
    level: int,
    pages: dict[int, PageDetail],
) -> bool:
    if isinstance(item, GroupItem):
        return True

    if not isinstance(item, DocItem) or not item.prov:
        return False

    for provenance in item.prov:
        try:
            page_no = provenance.page_no
            if page_no not in pages:
                logger.warning(
                    "Page %d not found in document metadata — using US Letter fallback (%sx%s pt)",
                    page_no,
                    DEFAULT_PAGE_WIDTH,
                    DEFAULT_PAGE_HEIGHT,
                )
                pages[page_no] = PageDetail(
                    page_number=page_no,
                    width=DEFAULT_PAGE_WIDTH,
                    height=DEFAULT_PAGE_HEIGHT,
                )

            page_height = pages[page_no].height
            bbox = to_topleft_list(provenance.bbox, page_height) if provenance.bbox else [0.0] * 4
            content = getattr(item, "text", "") or ""
            if isinstance(item, TableItem):
                with contextlib.suppress(AttributeError, ValueError):
                    content = item.export_to_markdown()

            pages[page_no].elements.append(
                PageElement(
                    type=_get_element_type(item),
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
                getattr(provenance, "page_no", "?"),
                exc_info=True,
            )
            return False

    return True
