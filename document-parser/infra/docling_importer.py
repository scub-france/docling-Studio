"""Docling adapter for serialized analysis imports."""

from __future__ import annotations

import json

from docling_core.types.doc import DoclingDocument

from domain.value_objects import ConversionResult
from infra.docling_pages import extract_pages_detail


class DoclingDocumentImporter:
    """Turn a serialized Docling document into the analysis domain result."""

    def deserialize(self, document: dict) -> ConversionResult:
        try:
            docling_document = DoclingDocument.model_validate(document)
            pages, skipped_items = extract_pages_detail(docling_document)
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
