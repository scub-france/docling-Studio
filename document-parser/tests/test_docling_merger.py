from __future__ import annotations

from docling_core.types.doc import DocItemLabel, DoclingDocument

from domain.value_objects import ConversionResult
from infra.docling_merger import DoclingDocumentMerger


def _batch(name: str, text: str) -> ConversionResult:
    document = DoclingDocument(name=name)
    document.add_text(label=DocItemLabel.TEXT, text=text)
    return ConversionResult(
        page_count=1,
        content_markdown=text,
        content_html=f"<p>{text}</p>",
        pages=[],
        document_json=document.model_dump_json(),
    )


def test_merger_uses_docling_reference_remapping():
    result = DoclingDocumentMerger().merge(
        [_batch("first", "First"), _batch("second", "Second")]
    )
    document = DoclingDocument.model_validate_json(result.document_json)
    items = [item for item, _ in document.iterate_items()]
    assert [item.text for item in items] == ["First", "Second"]
    assert [item.self_ref for item in items] == ["#/texts/0", "#/texts/1"]
    assert document.validate_tree(document.body, raise_on_error=True)
    assert "First" in result.content_markdown
    assert "Second" in result.content_markdown
