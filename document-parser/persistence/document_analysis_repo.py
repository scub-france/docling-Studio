"""The document's analysis state: active analysis and live chunk provenance.

The only module with SQL on `document_analysis_state` (02-2.4.3). The state is
written in two independent parts, each by the writer that changes it: the
selection (`write_selection`, `adopt_selection`) and the chunk source
(`write_chunk_source`). The repositories that change it in their own
transaction call these functions with their connection and commit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.models import DocumentAnalysisState, DocumentChunkSource
from persistence.database import get_connection

if TYPE_CHECKING:
    import aiosqlite

_SELECT_SQL = """INSERT INTO document_analysis_state
   (document_id, active_analysis_id) VALUES (?, ?)
   ON CONFLICT(document_id) DO UPDATE SET
     active_analysis_id = excluded.active_analysis_id"""

_ADOPT_SQL = """INSERT INTO document_analysis_state
   (document_id, active_analysis_id) VALUES (?, ?)
   ON CONFLICT(document_id) DO NOTHING"""

# An UPDATE, not an upsert: clearing never creates a row (#391 reads a missing
# row and a NULL selection differently).
_CLEAR_SELECTION_SQL = (
    "UPDATE document_analysis_state SET active_analysis_id = NULL WHERE document_id = ?"
)

_RECORD_CHUNK_SOURCE_SQL = """INSERT INTO document_analysis_state
   (document_id, chunks_source_analysis_id, chunks_source_result_hash)
   VALUES (?, ?, ?)
   ON CONFLICT(document_id) DO UPDATE SET
     chunks_source_analysis_id = excluded.chunks_source_analysis_id,
     chunks_source_result_hash = excluded.chunks_source_result_hash"""

_CLEAR_CHUNK_SOURCE_SQL = """UPDATE document_analysis_state
   SET chunks_source_analysis_id = NULL, chunks_source_result_hash = NULL
   WHERE document_id = ?"""


def _row_to_state(row) -> DocumentAnalysisState:
    source = None
    if (
        row["chunks_source_analysis_id"] is not None
        and row["chunks_source_result_hash"] is not None
    ):
        source = DocumentChunkSource(
            row["document_id"],
            row["chunks_source_analysis_id"],
            row["chunks_source_result_hash"],
        )
    return DocumentAnalysisState(row["document_id"], row["active_analysis_id"], source)


async def read_document_analysis_state(
    db: aiosqlite.Connection, document_id: str
) -> DocumentAnalysisState | None:
    """The document's state on the caller's connection, or None without a row."""
    cursor = await db.execute(
        "SELECT * FROM document_analysis_state WHERE document_id = ?", (document_id,)
    )
    row = await cursor.fetchone()
    return _row_to_state(row) if row else None


async def write_selection(
    db: aiosqlite.Connection, document_id: str, analysis_id: str | None
) -> None:
    """Make `analysis_id` the document's active analysis, without committing.

    None clears an existing selection and never creates a row. The chunk
    source is left as it is.

    Raises:
        sqlite3.IntegrityError: the analysis is gone or belongs to another
            document (the state triggers refuse it).
    """
    if analysis_id is None:
        await db.execute(_CLEAR_SELECTION_SQL, (document_id,))
        return
    await db.execute(_SELECT_SQL, (document_id, analysis_id))


async def adopt_selection(
    db: aiosqlite.Connection, document_id: str, analysis_id: str | None
) -> None:
    """Create the document's state row selecting `analysis_id`, if it has none.

    An existing row is left alone, so a selection made meanwhile is kept.
    Writers that create the row for another reason (a chunk source) call this
    first with the document's current analysis: the new row then keeps the
    analysis the fallback rule was giving, instead of hiding it behind a NULL
    selection. None does nothing.
    """
    if analysis_id is None:
        return
    await db.execute(_ADOPT_SQL, (document_id, analysis_id))


async def write_chunk_source(
    db: aiosqlite.Connection, document_id: str, source: DocumentChunkSource | None
) -> None:
    """Record where the live chunks came from, without committing.

    None forgets it (the chunks count as stale) and never creates a row. The
    selection is left as it is.
    """
    if source is None:
        await db.execute(_CLEAR_CHUNK_SOURCE_SQL, (document_id,))
        return
    await db.execute(
        _RECORD_CHUNK_SOURCE_SQL, (document_id, source.analysis_id, source.result_hash)
    )


class SqliteDocumentAnalysisRepository:
    """SQLite implementation of the DocumentAnalysisStateRepository port."""

    async def find_state(self, document_id: str) -> DocumentAnalysisState | None:
        async with get_connection() as db:
            return await read_document_analysis_state(db, document_id)

    async def find_states(self, document_ids: list[str]) -> dict[str, DocumentAnalysisState]:
        if not document_ids:
            return {}
        placeholders = ",".join("?" for _ in document_ids)
        async with get_connection() as db:
            cursor = await db.execute(
                f"SELECT * FROM document_analysis_state WHERE document_id IN ({placeholders})",
                tuple(document_ids),
            )
            return {row["document_id"]: _row_to_state(row) for row in await cursor.fetchall()}
