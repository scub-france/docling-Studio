"""Tests for the serialized Docling document import adapter."""

import pytest
from docling_core.types.doc import DoclingDocument

from infra.docling_importer import DoclingDocumentImporter


def test_deserialize_returns_conversion_result():
    result = DoclingDocumentImporter().deserialize(DoclingDocument(name="source").export_to_dict())

    assert result.content_markdown == ""
    assert result.content_html
    assert result.document_json


def test_deserialize_rejects_invalid_document():
    with pytest.raises(ValueError, match="Invalid Docling document"):
        DoclingDocumentImporter().deserialize({})
