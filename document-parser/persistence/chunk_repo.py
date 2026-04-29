"""Chunk repository — SQLite CRUD for first-class chunks (#205)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime

from domain.models import Chunk
from domain.value_objects import ChunkBbox, ChunkDocItem
from persistence.database import get_connection


def _parse_iso(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


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
        created_at=_parse_iso(row["created_at"]) or datetime.now(UTC),
        updated_at=_parse_iso(row["updated_at"]) or datetime.now(UTC),
        deleted_at=_parse_iso(row["deleted_at"]),
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
