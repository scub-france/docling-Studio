"""Chunk repository — SQLite CRUD for first-class chunks (#205)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.exceptions import AnalysisNotSelectableError
from domain.models import Chunk
from domain.value_objects import ChunkBbox, ChunkDocItem
from persistence.database import get_connection
from persistence.document_analysis_repo import (
    adopt_selection,
    write_chunk_source,
    write_selection,
)
from persistence.iso_datetime import parse_iso

if TYPE_CHECKING:
    from domain.models import DocumentChunkSource


def _row_to_chunk(row) -> Chunk:
    headings = json.loads(row["headings"]) if row["headings"] else []
    bboxes_raw = json.loads(row["bboxes"]) if row["bboxes"] else []
    doc_items_raw = json.loads(row["doc_items"]) if row["doc_items"] else []
    return Chunk(
        id=row["id"],
        document_id=row["document_id"],
        sequence=row["sequence"],
        text=row["text"],
        headings=headings,
        source_page=row["source_page"],
        bboxes=[ChunkBbox(page=b["page"], bbox=b["bbox"]) for b in bboxes_raw],
        doc_items=[ChunkDocItem(self_ref=d["self_ref"], label=d["label"]) for d in doc_items_raw],
        token_count=row["token_count"],
        created_at=parse_iso(row["created_at"]) or datetime.now(UTC),
        updated_at=parse_iso(row["updated_at"]) or datetime.now(UTC),
        deleted_at=parse_iso(row["deleted_at"]),
    )


def _chunk_to_params(c: Chunk) -> tuple:
    return (
        c.id,
        c.document_id,
        c.sequence,
        c.text,
        json.dumps(c.headings),
        c.source_page,
        json.dumps([asdict(b) for b in c.bboxes]),
        json.dumps([asdict(d) for d in c.doc_items]),
        c.token_count,
        str(c.created_at),
        str(c.updated_at),
        str(c.deleted_at) if c.deleted_at else None,
    )


_INSERT_SQL = """INSERT INTO chunks
    (id, document_id, sequence, text, headings, source_page,
     bboxes, doc_items, token_count, created_at, updated_at, deleted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

_SOFT_DELETE_FOR_DOCUMENT_SQL = """UPDATE chunks SET deleted_at = ?, updated_at = ?
    WHERE document_id = ? AND deleted_at IS NULL"""


class SqliteChunkRepository:
    """SQLite implementation of the ChunkRepository port."""

    async def insert(self, chunk: Chunk) -> None:
        async with get_connection() as db:
            await db.execute(_INSERT_SQL, _chunk_to_params(chunk))
            await db.commit()

    async def insert_many(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        async with get_connection() as db:
            await db.executemany(_INSERT_SQL, [_chunk_to_params(c) for c in chunks])
            await db.commit()

    async def update(self, chunk: Chunk) -> None:
        async with get_connection() as db:
            await db.execute(
                """UPDATE chunks SET
                       sequence = ?, text = ?, headings = ?, source_page = ?,
                       bboxes = ?, doc_items = ?, token_count = ?,
                       updated_at = ?, deleted_at = ?
                   WHERE id = ?""",
                (
                    chunk.sequence,
                    chunk.text,
                    json.dumps(chunk.headings),
                    chunk.source_page,
                    json.dumps([asdict(b) for b in chunk.bboxes]),
                    json.dumps([asdict(d) for d in chunk.doc_items]),
                    chunk.token_count,
                    str(chunk.updated_at),
                    str(chunk.deleted_at) if chunk.deleted_at else None,
                    chunk.id,
                ),
            )
            await db.commit()

    async def soft_delete(self, chunk_id: str, *, at: datetime) -> bool:
        async with get_connection() as db:
            cursor = await db.execute(
                "UPDATE chunks SET deleted_at = ?, updated_at = ? WHERE id = ?",
                (str(at), str(at), chunk_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def soft_delete_many(self, chunk_ids: list[str], *, at: datetime) -> int:
        """Soft-delete the given chunks in one statement; returns how many were hit."""
        if not chunk_ids:
            return 0
        placeholders = ", ".join("?" for _ in chunk_ids)
        async with get_connection() as db:
            cursor = await db.execute(
                f"UPDATE chunks SET deleted_at = ?, updated_at = ? WHERE id IN ({placeholders})",
                (str(at), str(at), *chunk_ids),
            )
            await db.commit()
            return cursor.rowcount

    async def soft_delete_for_document(self, document_id: str, *, at: datetime) -> int:
        """Soft-delete every live chunk of a document in one statement.

        Chunks already soft-deleted keep their original `deleted_at`.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                _SOFT_DELETE_FOR_DOCUMENT_SQL,
                (str(at), str(at), document_id),
            )
            await db.commit()
            return cursor.rowcount

    async def replace_for_document(
        self,
        document_id: str,
        chunks: list[Chunk],
        *,
        at: datetime,
        chunk_source: DocumentChunkSource | None,
        active_analysis_id: str | None,
        keep_selection: bool = False,
    ) -> int:
        """Replace a document's live chunks and write its analysis state, atomically.

        Soft-deletes every live chunk, inserts `chunks`, writes the selection
        and the chunk source in one transaction (02-2.4.3): the live chunks
        and the record of where they came from never disagree after a
        failure. Returns how many chunks were soft-deleted.
        """
        if chunk_source is not None and chunk_source.document_id != document_id:
            raise ValueError("The chunk source must belong to the document")
        async with get_connection() as db:
            cursor = await db.execute(
                _SOFT_DELETE_FOR_DOCUMENT_SQL,
                (str(at), str(at), document_id),
            )
            deleted = cursor.rowcount
            if chunks:
                await db.executemany(_INSERT_SQL, [_chunk_to_params(c) for c in chunks])
            try:
                if keep_selection:
                    await adopt_selection(db, document_id, active_analysis_id)
                else:
                    await write_selection(db, document_id, active_analysis_id)
            except sqlite3.IntegrityError as exc:
                raise AnalysisNotSelectableError(
                    f"Analysis {active_analysis_id} is no longer available"
                ) from exc
            await write_chunk_source(db, document_id, chunk_source)
            await db.commit()
        return deleted

    async def shift_sequences(
        self,
        document_id: str,
        *,
        from_sequence: int,
        at: datetime,
        by: int = 1,
    ) -> int:
        """Move every live chunk at `sequence >= from_sequence` up by `by`, in one statement.

        `chunks` has no UNIQUE constraint on (document_id, sequence), so the
        rows can be shifted in place without a temporary offset.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """UPDATE chunks SET sequence = sequence + ?, updated_at = ?
                   WHERE document_id = ? AND sequence >= ? AND deleted_at IS NULL""",
                (by, str(at), document_id, from_sequence),
            )
            await db.commit()
            return cursor.rowcount

    async def find_for_document(
        self,
        document_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[Chunk]:
        clause = "" if include_deleted else " AND deleted_at IS NULL"
        async with get_connection() as db:
            cursor = await db.execute(
                f"""SELECT * FROM chunks
                    WHERE document_id = ?{clause}
                    ORDER BY sequence ASC""",
                (document_id,),
            )
            rows = await cursor.fetchall()
            return [_row_to_chunk(r) for r in rows]

    async def find_by_id(self, chunk_id: str) -> Chunk | None:
        async with get_connection() as db:
            cursor = await db.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
            row = await cursor.fetchone()
            return _row_to_chunk(row) if row else None

    async def count_for_document(self, document_id: str) -> int:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) AS n FROM chunks WHERE document_id = ? AND deleted_at IS NULL",
                (document_id,),
            )
            row = await cursor.fetchone()
            return int(row["n"]) if row else 0
