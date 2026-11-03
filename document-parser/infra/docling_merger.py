"""Native Docling merger for page-batched conversion results."""

from __future__ import annotations

import json

from docling_core.types.doc import DoclingDocument

from domain.value_objects import ConversionResult


class DoclingDocumentMerger:
    """Merge independent batch documents using Docling's reference index."""

    def merge(self, results: list[ConversionResult]) -> ConversionResult:
        if not results:
            return ConversionResult(page_count=0, content_markdown="", content_html="", pages=[])
        if any(not result.document_json for result in results):
            raise ValueError("Every batched result must contain document_json")

        documents = [
            DoclingDocument.model_validate_json(result.document_json)
            for result in results
            if result.document_json
        ]
        merged = DoclingDocument.concatenate(documents)
        merged.validate_tree(merged.body, raise_on_error=True)
        merged.validate_document()
        pages = sorted(
            [page for result in results for page in result.pages],
            key=lambda page: page.page_number,
        )
        return ConversionResult(
            page_count=len(merged.pages) or sum(result.page_count for result in results),
            content_markdown=merged.export_to_markdown(),
            content_html=merged.export_to_html(),
            pages=pages,
            skipped_items=sum(result.skipped_items for result in results),
            document_json=json.dumps(merged.export_to_dict()),
        )
