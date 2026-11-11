"""Active analysis selection and live chunk provenance for a document."""

from __future__ import annotations

from domain.models import DocumentAnalysisSelection, DocumentChunkSource
from persistence.database import get_connection


class SqliteDocumentAnalysisRepository:
    async def get_selection(self, document_id: str) -> DocumentAnalysisSelection | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM document_analysis_state WHERE document_id = ?",
                (document_id,),
            )
            row = await cursor.fetchone()
            return (
                DocumentAnalysisSelection(row["document_id"], row["active_analysis_id"])
                if row and row["active_analysis_id"] is not None
                else None
            )

    async def select(self, selection: DocumentAnalysisSelection) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO document_analysis_state
                   (document_id, active_analysis_id) VALUES (?, ?)
                   ON CONFLICT(document_id) DO UPDATE SET
                     active_analysis_id = excluded.active_analysis_id""",
                (
                    selection.document_id,
                    selection.analysis_id,
                ),
            )
            await db.commit()

    async def clear_selection(self, document_id: str) -> None:
        async with get_connection() as db:
            await db.execute(
                "UPDATE document_analysis_state SET active_analysis_id = NULL WHERE document_id = ?",
                (document_id,),
            )
            await db.commit()

    async def get_chunk_source(self, document_id: str) -> DocumentChunkSource | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM document_analysis_state WHERE document_id = ?",
                (document_id,),
            )
            row = await cursor.fetchone()
            return (
                DocumentChunkSource(
                    row["document_id"],
                    row["chunks_source_analysis_id"],
                    row["chunks_source_result_hash"],
                )
                if row and row["chunks_source_analysis_id"] is not None
                else None
            )

    async def set_chunk_source(self, source: DocumentChunkSource) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO document_analysis_state
                   (document_id, chunks_source_analysis_id, chunks_source_result_hash)
                   VALUES (?, ?, ?)
                   ON CONFLICT(document_id) DO UPDATE SET
                     chunks_source_analysis_id = excluded.chunks_source_analysis_id,
                     chunks_source_result_hash = excluded.chunks_source_result_hash""",
                (source.document_id, source.analysis_id, source.result_hash),
            )
            await db.commit()

    async def clear_chunk_source(self, document_id: str) -> None:
        async with get_connection() as db:
            await db.execute(
                """UPDATE document_analysis_state
                   SET chunks_source_analysis_id = NULL, chunks_source_result_hash = NULL
                   WHERE document_id = ?""",
                (document_id,),
            )
            await db.commit()
