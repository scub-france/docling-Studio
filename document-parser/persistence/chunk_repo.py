"""Chunk repository — SQLite CRUD for first-class chunks (#205)."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from domain.models import Chunk
from domain.value_objects import ChunkBbox, ChunkDocItem
from persistence.chunk_edit_repo import write_edits
from persistence.database import get_connection
from persistence.timestamps import parse_iso, parse_required_iso

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from domain.models import ChunkEdit


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
        created_at=parse_required_iso(row["created_at"], column="chunks.created_at"),
        updated_at=parse_required_iso(row["updated_at"], column="chunks.updated_at"),
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

    async def replace_chunkset(
        self,
        document_id: str,
        *,
        at: datetime,
        retire_ids: Sequence[str] = (),
        add: Sequence[Chunk] = (),
        edits: Sequence[ChunkEdit] = (),
    ) -> None:
        """Retire `retire_ids`, insert `add` and journal `edits`, all or nothing.

        One connection, one transaction, one statement per kind of row:
        retiring soft-deletes the live chunks of `document_id` among
        `retire_ids` (`deleted_at = updated_at = at`), then `add` and
        `edits` are inserted in order. Any failure rolls the whole
        operation back.
        """
        async with get_connection() as db:
            try:
                if retire_ids:
                    await db.executemany(
                        """UPDATE chunks SET deleted_at = ?, updated_at = ?
                           WHERE id = ? AND document_id = ? AND deleted_at IS NULL""",
                        [(str(at), str(at), chunk_id, document_id) for chunk_id in retire_ids],
                    )
                if add:
                    await db.executemany(_INSERT_SQL, [_chunk_to_params(c) for c in add])
                await write_edits(db, edits)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def shift_sequences(self, document_id: str, *, from_sequence: int, at: datetime) -> int:
        """Move every live chunk of `document_id` at `sequence >= from_sequence`
        one slot up, in a single UPDATE. Returns the number of chunks moved.

        `idx_chunks_doc_seq` is not UNIQUE, so the transient overlap of an
        in-place `sequence + 1` cannot conflict.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """UPDATE chunks SET sequence = sequence + 1, updated_at = ?
                   WHERE document_id = ? AND deleted_at IS NULL AND sequence >= ?""",
                (str(at), document_id, from_sequence),
            )
            await db.commit()
            return cursor.rowcount

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
