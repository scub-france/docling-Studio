"""Docling adapter for serialized analysis imports."""

from __future__ import annotations

import contextlib
import json

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

from domain.value_objects import (
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    ConversionResult,
    PageDetail,
    PageElement,
)
from infra.bbox import to_topleft_list

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


def _element_type(item: DocItem) -> str:
    for item_class, type_name in _ELEMENT_TYPE_MAP:
        if isinstance(item, item_class):
            return type_name
    return "text"


def _extract_pages(document: DoclingDocument) -> tuple[list[PageDetail], int]:
    pages = {
        int(page_number): PageDetail(
            page_number=int(page_number), width=page.size.width, height=page.size.height
        )
        for page_number, page in document.pages.items()
    }
    skipped_items = 0

    for item, level in document.iterate_items():
        if isinstance(item, GroupItem):
            continue
        if not isinstance(item, DocItem) or not item.prov:
            skipped_items += 1
            continue

        for provenance in item.prov:
            try:
                page = pages.setdefault(
                    provenance.page_no,
                    PageDetail(provenance.page_no, DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT),
                )
                bbox = (
                    to_topleft_list(provenance.bbox, page.height) if provenance.bbox else [0.0] * 4
                )
                content = getattr(item, "text", "") or ""
                if isinstance(item, TableItem):
                    with contextlib.suppress(AttributeError, ValueError):
                        content = item.export_to_markdown()
                page.elements.append(
                    PageElement(
                        type=_element_type(item),
                        bbox=bbox,
                        content=content,
                        level=level,
                        self_ref=getattr(item, "self_ref", "") or "",
                    )
                )
            except (AttributeError, KeyError, TypeError, ValueError):
                skipped_items += 1
                break

    return sorted(pages.values(), key=lambda page: page.page_number), skipped_items


class DoclingDocumentImporter:
    """Turn a serialized Docling document into the analysis domain result."""

    def deserialize(self, document: dict) -> ConversionResult:
        try:
            docling_document = DoclingDocument.model_validate(document)
            pages, skipped_items = _extract_pages(docling_document)
            return ConversionResult(
                page_count=len(docling_document.pages),
                content_markdown=docling_document.export_to_markdown(),
                content_html=docling_document.export_to_html(),
                pages=pages,
                skipped_items=skipped_items,
                document_json=json.dumps(docling_document.export_to_dict()),
            )
        except Exception as e:
            raise ValueError(f"Invalid Docling document: {e}") from e
