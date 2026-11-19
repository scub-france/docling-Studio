"""The document's analysis state: active analysis and live chunk provenance.

The only module that writes `document_analysis_state` (02-2.4.3). Other
repositories that must change it in their own transaction call
`write_document_analysis_state` with their connection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.models import DocumentAnalysisState
from persistence.database import get_connection

if TYPE_CHECKING:
    import aiosqlite

_SELECT_SQL = """INSERT INTO document_analysis_state
   (document_id, active_analysis_id) VALUES (?, ?)
   ON CONFLICT(document_id) DO UPDATE SET
     active_analysis_id = excluded.active_analysis_id"""

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
    return DocumentAnalysisState(
        row["document_id"],
        row["active_analysis_id"],
        row["chunks_source_analysis_id"],
        row["chunks_source_result_hash"],
    )


async def write_document_analysis_state(
    db: aiosqlite.Connection, state: DocumentAnalysisState
) -> None:
    """Write the parts of `state` changed since it was loaded, without committing.

    The caller commits, so the write joins whatever else its transaction
    holds. Only the changed columns are written: a chunk source recorded
    here never overwrites a selection made meanwhile, nor the reverse.
    """
    if state.selection_changed:
        if state.active_analysis_id is None:
            await db.execute(_CLEAR_SELECTION_SQL, (state.document_id,))
        else:
            await db.execute(_SELECT_SQL, (state.document_id, state.active_analysis_id))
    if state.chunk_source_changed:
        if state.chunks_source_analysis_id is None:
            await db.execute(_CLEAR_CHUNK_SOURCE_SQL, (state.document_id,))
        else:
            await db.execute(
                _RECORD_CHUNK_SOURCE_SQL,
                (
                    state.document_id,
                    state.chunks_source_analysis_id,
                    state.chunks_source_result_hash,
                ),
            )


class SqliteDocumentAnalysisRepository:
    """SQLite implementation of the DocumentAnalysisStateRepository port."""

    async def find_state(self, document_id: str) -> DocumentAnalysisState | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM document_analysis_state WHERE document_id = ?",
                (document_id,),
            )
            row = await cursor.fetchone()
            return _row_to_state(row) if row else None

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

    async def save_state(self, state: DocumentAnalysisState) -> None:
        """Write the changed parts of `state` in one transaction."""
        async with get_connection() as db:
            await write_document_analysis_state(db, state)
            await db.commit()
        state.mark_saved()
