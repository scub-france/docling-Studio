"""Docling adapter for serialized analysis imports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from docling_core.types.doc import DoclingDocument, TableData
from pydantic import BaseModel, ValidationError

from domain.value_objects import ConversionResult
from infra.docling_pages import extract_pages_detail
from infra.settings import settings

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from docling_core.types.doc import TableCell


class DoclingImportTooLargeError(ValueError):
    """The document's table grids would cost more to export than the import allows."""


# What the model walk enters: the containers a `TableData` can sit in.
_MODEL_CONTAINERS = (BaseModel, list, tuple, dict)
# A JSON object docling-core may turn into a `TableData`: it has a dimension.
_GRID_KEYS = ("num_rows", "num_cols")


def _filled_slots(cell: TableCell, num_rows: int, num_cols: int) -> int:
    """Grid positions docling-core writes `cell` into when it builds the grid.

    Same clamping as `TableData.grid`, so this is the exact number of
    iterations of its inner loop for this cell.
    """
    rows = min(cell.end_row_offset_idx, num_rows) - min(cell.start_row_offset_idx, num_rows)
    cols = min(cell.end_col_offset_idx, num_cols) - min(cell.start_col_offset_idx, num_cols)
    return max(rows, 0) * max(cols, 0)


def _grid_cost(data: TableData) -> tuple[int, int]:
    """`(declared, filled)`: what building `data.grid` once allocates and writes.

    Declared counts one slot per cell, and one per row without columns:
    `TableData.grid` allocates a list per row whatever the column count, so
    `1,000,000 x 0` (643 bytes) cost 20 s and 209 MB, and counted 0 before.
    A negative dimension builds nothing, and must not cancel another grid's
    count out of the sum.
    """
    declared = max(data.num_rows, 0) * max(data.num_cols, 1)
    filled = sum(_filled_slots(c, data.num_rows, data.num_cols) for c in data.table_cells)
    return declared, filled


def _payload_grids(payload: object) -> Iterator[TableData]:
    """The `TableData` the raw JSON holds, validated alone, before the document.

    The check cannot wait for the validated document: validating a picture's
    `meta` already builds its chart grid, twice (docling-core's
    `_ExtraAllowingModel` dumps itself to check its field names), so a 680-byte
    400 x 400 chart cost 4.6 s and 285 MB before any check could run. A JSON
    object with a dimension is validated as a `TableData` on its own, which
    builds no grid; one that does not validate is not a grid docling-core will
    build, and the walk goes on inside it. One that validates is counted
    wherever it sits, even in a custom field docling-core leaves as plain
    data: the check errs on the side of refusing. (Validating a cell fills in
    its missing `text` in the payload, as the document's validation does
    next anyway.) The walk is iterative: the depth of the JSON does not matter.
    """
    stack: list[object] = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if any(key in node for key in _GRID_KEYS):
                try:
                    grid = TableData.model_validate(node)
                except ValidationError:
                    grid = None
                if grid is not None:
                    yield grid
                    continue
            values = node.values()
        elif isinstance(node, list):
            values = node
        else:
            continue
        stack.extend(v for v in values if isinstance(v, dict | list))


def _document_grids(document: DoclingDocument) -> Iterator[TableData]:
    """Every `TableData` of the validated document, once per place it sits.

    docling-core builds a grid for each of them at every export, not only for
    the tables: a picture's chart data is a `TableData` too
    (`meta.tabular_chart.chart_data`, and the deprecated `annotations` entry
    of kind `tabular_chart_data`, which validation also copies into `meta`, so
    that grid is exported twice and counted twice here). Walking the whole
    model rather than naming those fields keeps the count right when
    docling-core puts a grid somewhere new.

    The walk reads stored values only (`vars`, and the extra fields of the
    models that allow them), never computed fields, so it builds no grid. It
    does not enter a `TableData` itself: its cells hold no grid.
    """
    stack: list[object] = [document]
    while stack:
        node = stack.pop()
        if isinstance(node, TableData):
            yield node
            continue
        if isinstance(node, BaseModel):
            values = list(vars(node).values())
            values.extend((node.__pydantic_extra__ or {}).values())
        elif isinstance(node, dict):
            values = node.values()
        else:  # list or tuple
            values = node
        stack.extend(v for v in values if isinstance(v, _MODEL_CONTAINERS))


def _check_table_budget(grids: Iterable[TableData], max_cells: int) -> None:
    """Refuse a document whose table grids would blow up the exports (#audit-08).

    docling-core's `TableData.grid` is a computed field: every export
    (Markdown, HTML, dict) allocates `num_rows x num_cols` cells, then writes
    each table cell into every position it spans. Neither count is bounded
    by the JSON itself: a 691-byte table claiming 400 x 400 cost 18 s and
    347 MB, and 1,000 cells each spanning a 100 x 100 grid (157 KB) are ten
    million writes per export. The same 400 x 400 declared as a picture's
    chart data (680 bytes) cost 32 s and 350 MB: every grid counts, wherever
    it sits. `max_cells <= 0` lifts the limit.
    """
    if max_cells <= 0:
        return
    declared = 0
    filled = 0
    for data in grids:
        grid_declared, grid_filled = _grid_cost(data)
        declared += grid_declared
        filled += grid_filled
    if declared > max_cells:
        raise DoclingImportTooLargeError(
            f"Docling document too large to import: its tables and charts declare "
            f"{declared:,} cells, over the {max_cells:,} allowed (MAX_IMPORT_TABLE_CELLS)"
        )
    if filled > max_cells:
        raise DoclingImportTooLargeError(
            f"Docling document too large to import: its table and chart cells span "
            f"{filled:,} grid positions, over the {max_cells:,} allowed "
            "(MAX_IMPORT_TABLE_CELLS)"
        )


class DoclingDocumentImporter:
    """Turn a serialized Docling document into the analysis domain result.

    `max_table_cells` bounds the table grids of one document, all tables and
    chart data together (0 = no limit). It defaults to
    `MAX_IMPORT_TABLE_CELLS`.
    """

    def __init__(self, max_table_cells: int | None = None) -> None:
        self._max_table_cells = (
            settings.max_import_table_cells if max_table_cells is None else max_table_cells
        )

    def deserialize(self, document: dict) -> ConversionResult:
        # Twice: on the raw JSON, because validating the document already
        # builds some grids; then on the document, because validation can
        # place one grid in two fields, each exported.
        _check_table_budget(_payload_grids(document), self._max_table_cells)
        try:
            docling_document = DoclingDocument.model_validate(document)
        except Exception as e:
            raise ValueError(f"Invalid Docling document: {e}") from e
        _check_table_budget(_document_grids(docling_document), self._max_table_cells)
        try:
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
