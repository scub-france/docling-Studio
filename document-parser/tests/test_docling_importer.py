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


# ---------------------------------------------------------------------------
# Grids outside the tables (re-audit 0.7.4, 08 MAJ): a picture's chart data is
# a `TableData` too, and validating a picture's `meta` already builds its grid.
# ---------------------------------------------------------------------------


def _grid(rows: int, cols: int, cells: list[dict] | None = None) -> dict:
    return {"table_cells": cells or [], "num_rows": rows, "num_cols": cols}


def _picture_document(*, meta: dict | None = None, annotations: list | None = None) -> dict:
    """A serialized document holding one picture with the given chart data."""
    payload = DoclingDocument(name="source").export_to_dict()
    picture: dict = {"self_ref": "#/pictures/0", "parent": {"$ref": "#/body"}, "label": "picture"}
    if meta is not None:
        picture["meta"] = meta
    if annotations is not None:
        picture["annotations"] = annotations
    payload["pictures"] = [picture]
    payload["body"]["children"] = [{"$ref": "#/pictures/0"}]
    return payload


def _chart_annotation(grid: dict) -> dict:
    return {"kind": "tabular_chart_data", "title": "chart", "chart_data": grid}


@pytest.mark.parametrize(
    "payload",
    [
        _picture_document(meta={"tabular_chart": {"chart_data": _grid(10**6, 10**6)}}),
        _picture_document(annotations=[_chart_annotation(_grid(10**6, 10**6))]),
    ],
    ids=["meta.tabular_chart", "annotations"],
)
def test_a_huge_chart_grid_is_refused_before_validation(payload):
    """The re-audit's bypass: a 400 x 400 chart (680 bytes) cost 32 s and
    350 MB. Refused before the document is even validated, since validating a
    picture's `meta` builds the grid."""
    started = time.perf_counter()
    with (
        patch("infra.docling_importer.DoclingDocument.model_validate") as validate,
        pytest.raises(DoclingImportTooLargeError, match="1,000,000,000,000 cells"),
    ):
        DoclingDocumentImporter().deserialize(payload)

    assert time.perf_counter() - started < 2
    validate.assert_not_called()


def test_chart_grids_and_tables_share_one_budget():
    payload = _picture_document(meta={"tabular_chart": {"chart_data": _grid(10, 10)}})
    payload["tables"] = _document((10, 10, []))["tables"]
    payload["body"]["children"].append({"$ref": "#/tables/0"})

    with pytest.raises(DoclingImportTooLargeError, match="declare 200 cells"):
        DoclingDocumentImporter(max_table_cells=150).deserialize(payload)


def test_a_chart_annotation_counts_for_each_place_validation_puts_it():
    """docling-core copies the deprecated annotation into `meta`: the same
    grid is then exported twice, and counted twice."""
    payload = _picture_document(annotations=[_chart_annotation(_grid(10, 10))])

    with pytest.raises(DoclingImportTooLargeError, match="declare 200 cells"):
        DoclingDocumentImporter(max_table_cells=150).deserialize(payload)


def test_a_chart_cell_spanning_the_grid_many_times_is_refused():
    full_span = _cell(0, 10, 0, 10)
    payload = _picture_document(
        meta={"tabular_chart": {"chart_data": _grid(10, 10, [full_span] * 3)}}
    )

    with pytest.raises(DoclingImportTooLargeError, match="span 300 grid positions"):
        DoclingDocumentImporter(max_table_cells=200).deserialize(payload)


def test_a_chart_within_the_budget_is_imported():
    cells = [_cell(r, r + 1, c, c + 1, f"v{r}{c}") for r in range(2) for c in range(2)]
    payload = _picture_document(meta={"tabular_chart": {"chart_data": _grid(2, 2, cells)}})

    result = DoclingDocumentImporter(max_table_cells=4).deserialize(payload)

    assert "v11" in result.document_json


@pytest.mark.parametrize("vector", ["table", "chart"])
def test_rows_without_columns_count_one_slot_each(vector):
    """`TableData.grid` allocates a list per row even with no columns:
    1,000,000 x 0 (643 bytes) cost 20 s and 209 MB, and counted 0 cells."""
    if vector == "table":
        payload = _document((10**9, 0, []))
    else:
        payload = _picture_document(meta={"tabular_chart": {"chart_data": _grid(10**9, 0)}})

    with pytest.raises(DoclingImportTooLargeError, match="declare 1,000,000,000 cells"):
        DoclingDocumentImporter().deserialize(payload)


def test_an_object_that_is_not_a_grid_is_not_counted():
    """A custom meta field with a `num_rows` key that docling-core will not
    turn into a grid (it does not validate as one) costs nothing."""
    payload = _picture_document(meta={"acme__stats": {"num_rows": "many", "num_cols": 10**9}})

    result = DoclingDocumentImporter(max_table_cells=10).deserialize(payload)

    assert result.document_json
