"""Tests for the serialized Docling document import adapter."""

import time
from unittest.mock import patch

import pytest
from docling_core.types.doc import DoclingDocument

from infra.docling_importer import DoclingDocumentImporter, DoclingImportTooLargeError
from infra.settings import settings


def test_deserialize_returns_conversion_result():
    result = DoclingDocumentImporter().deserialize(DoclingDocument(name="source").export_to_dict())

    assert result.content_markdown == ""
    assert result.content_html
    assert result.document_json


def test_deserialize_rejects_invalid_document():
    with pytest.raises(ValueError, match="Invalid Docling document"):
        DoclingDocumentImporter().deserialize({})


# ---------------------------------------------------------------------------
# Table budget (#audit-08): docling-core builds each table's full grid on
# export, so the declared size, not the JSON size, is what an import costs.
# ---------------------------------------------------------------------------


def _cell(r0: int, r1: int, c0: int, c1: int, text: str = "x") -> dict:
    return {
        "row_span": r1 - r0,
        "col_span": c1 - c0,
        "start_row_offset_idx": r0,
        "end_row_offset_idx": r1,
        "start_col_offset_idx": c0,
        "end_col_offset_idx": c1,
        "text": text,
    }


def _document(*tables: tuple[int, int, list[dict]]) -> dict:
    """A serialized document holding one table per `(rows, cols, cells)`."""
    payload = DoclingDocument(name="source").export_to_dict()
    payload["tables"] = [
        {
            "self_ref": f"#/tables/{i}",
            "parent": {"$ref": "#/body"},
            "label": "table",
            "data": {"table_cells": cells, "num_rows": rows, "num_cols": cols},
        }
        for i, (rows, cols, cells) in enumerate(tables)
    ]
    payload["body"]["children"] = [{"$ref": t["self_ref"]} for t in payload["tables"]]
    return payload


def test_a_huge_declared_table_is_refused_before_any_export():
    """The audit's case, scaled up: 10**12 cells declared in a few hundred bytes."""
    payload = _document((10**6, 10**6, []))

    started = time.perf_counter()
    with (
        patch("infra.docling_importer.extract_pages_detail") as extract,
        pytest.raises(DoclingImportTooLargeError, match="MAX_IMPORT_TABLE_CELLS") as caught,
    ):
        DoclingDocumentImporter().deserialize(payload)

    assert time.perf_counter() - started < 2
    extract.assert_not_called()
    assert "1,000,000,000,000 cells" in str(caught.value)
    assert f"{settings.max_import_table_cells:,}" in str(caught.value)
    # A ValueError, so the API answers 400 like any other invalid import.
    assert isinstance(caught.value, ValueError)


def test_the_budget_counts_every_table_of_the_document():
    payload = _document((10, 10, []), (10, 10, []))

    with pytest.raises(DoclingImportTooLargeError, match="declare 200 cells"):
        DoclingDocumentImporter(max_table_cells=150).deserialize(payload)


def test_a_negative_dimension_cannot_cancel_another_table_out():
    """`-200 x 200` builds an empty grid; it must not offset a real `200 x 200`."""
    payload = _document((-200, 200, []), (200, 200, []))

    with pytest.raises(DoclingImportTooLargeError, match="declare 40,000 cells"):
        DoclingDocumentImporter(max_table_cells=1000).deserialize(payload)


def test_cells_spanning_the_whole_grid_many_times_are_refused():
    """A small grid stays cheap only if its cells do not each cover all of it."""
    full_span = _cell(0, 10, 0, 10)
    payload = _document((10, 10, [full_span] * 3))

    with pytest.raises(DoclingImportTooLargeError, match="span 300 grid positions"):
        DoclingDocumentImporter(max_table_cells=200).deserialize(payload)


def test_a_cell_span_is_clamped_to_the_grid_like_docling_does():
    """A span past the grid's edge costs only the positions inside it."""
    payload = _document((2, 2, [_cell(0, 10**9, 0, 10**9)]))

    result = DoclingDocumentImporter(max_table_cells=4).deserialize(payload)

    assert result.content_html


def test_a_table_exactly_at_the_budget_is_imported():
    cells = [_cell(r, r + 1, c, c + 1, f"r{r}c{c}") for r in range(3) for c in range(2)]
    payload = _document((3, 2, cells))

    result = DoclingDocumentImporter(max_table_cells=6).deserialize(payload)

    assert "r2c1" in result.content_markdown
    assert "r2c1" in result.content_html


def test_a_zero_budget_means_no_limit():
    payload = _document((50, 50, []))

    result = DoclingDocumentImporter(max_table_cells=0).deserialize(payload)

    assert result.document_json
