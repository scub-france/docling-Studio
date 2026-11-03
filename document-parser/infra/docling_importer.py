"""Docling adapter for serialized analysis imports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from docling_core.types.doc import DoclingDocument

from domain.value_objects import ConversionResult
from infra.docling_pages import extract_pages_detail
from infra.settings import settings

if TYPE_CHECKING:
    from docling_core.types.doc import TableCell


class DoclingImportTooLargeError(ValueError):
    """The document's tables would cost more to export than the import allows."""


def _filled_slots(cell: TableCell, num_rows: int, num_cols: int) -> int:
    """Grid positions docling-core writes `cell` into when it builds the grid.

    Same clamping as `TableData.grid`, so this is the exact number of
    iterations of its inner loop for this cell.
    """
    rows = min(cell.end_row_offset_idx, num_rows) - min(cell.start_row_offset_idx, num_rows)
    cols = min(cell.end_col_offset_idx, num_cols) - min(cell.start_col_offset_idx, num_cols)
    return max(rows, 0) * max(cols, 0)


def _check_table_budget(document: DoclingDocument, max_cells: int) -> None:
    """Refuse a document whose table grids would blow up the exports (#audit-08).

    docling-core's `TableData.grid` is a computed field: every export
    (Markdown, HTML, dict) allocates `num_rows x num_cols` cells, then writes
    each table cell into every position it spans. Neither count is bounded
    by the JSON itself: a 691-byte table claiming 400 x 400 cost 18 s and
    347 MB, and 1,000 cells each spanning a 100 x 100 grid (157 KB) are ten
    million writes per export. Validation does not build the grid (measured:
    3 ms for 200 x 200), so the check runs on the validated document, before
    any export.
    """
    if max_cells <= 0:
        return
    declared = 0
    filled = 0
    for table in document.tables:
        data = table.data
        # Clamped: a negative dimension builds an empty grid, and must not
        # cancel another table's count out of the sum.
        declared += max(data.num_rows, 0) * max(data.num_cols, 0)
        filled += sum(_filled_slots(c, data.num_rows, data.num_cols) for c in data.table_cells)
    if declared > max_cells:
        raise DoclingImportTooLargeError(
            f"Docling document too large to import: its tables declare {declared:,} cells, "
            f"over the {max_cells:,} allowed (MAX_IMPORT_TABLE_CELLS)"
        )
    if filled > max_cells:
        raise DoclingImportTooLargeError(
            f"Docling document too large to import: its table cells span {filled:,} grid "
            f"positions, over the {max_cells:,} allowed (MAX_IMPORT_TABLE_CELLS)"
        )


class DoclingDocumentImporter:
    """Turn a serialized Docling document into the analysis domain result.

    `max_table_cells` bounds the table grids of one document, all tables
    together (0 = no limit). It defaults to `MAX_IMPORT_TABLE_CELLS`.
    """

    def __init__(self, max_table_cells: int | None = None) -> None:
        self._max_table_cells = (
            settings.max_import_table_cells if max_table_cells is None else max_table_cells
        )

    def deserialize(self, document: dict) -> ConversionResult:
        try:
            docling_document = DoclingDocument.model_validate(document)
        except Exception as e:
            raise ValueError(f"Invalid Docling document: {e}") from e
        _check_table_budget(docling_document, self._max_table_cells)
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
