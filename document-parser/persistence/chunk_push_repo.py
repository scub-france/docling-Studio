"""SQLite repository for immutable chunk push records."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from domain.models import ChunkPush
from persistence.database import get_connection


def _parse_iso(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _row_to_push(row) -> ChunkPush:
    return ChunkPush(
        id=row["id"],
        document_id=row["document_id"],
        store_id=row["store_id"],
        chunkset_hash=row["chunkset_hash"],
        chunk_ids=json.loads(row["chunk_ids"]) if row["chunk_ids"] else [],
        pushed_at=_parse_iso(row["pushed_at"]) or datetime.now(UTC),
    )


class SqliteChunkPushRepository:
    """SQLite implementation of the ChunkPushRepository port."""

    async def insert(self, push: ChunkPush) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO chunk_pushes
                   (id, document_id, store_id, chunkset_hash, chunk_ids, pushed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    push.id,
                    push.document_id,
                    push.store_id,
                    push.chunkset_hash,
                    json.dumps(push.chunk_ids),
                    str(push.pushed_at),
                ),
            )
            await db.commit()

    async def find_by_id(self, push_id: str) -> ChunkPush | None:
        async with get_connection() as db:
            cursor = await db.execute("SELECT * FROM chunk_pushes WHERE id = ?", (push_id,))
            row = await cursor.fetchone()
            return _row_to_push(row) if row else None

    async def find_latest(self, document_id: str, store_id: str) -> ChunkPush | None:
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM chunk_pushes
                   WHERE document_id = ? AND store_id = ?
                   ORDER BY pushed_at DESC
                   LIMIT 1""",
                (document_id, store_id),
            )
            row = await cursor.fetchone()
            return _row_to_push(row) if row else None

    async def find_for_document(
        self,
        document_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChunkPush]:
        """Return every push for `document_id`, newest first.

        Used by `GET /api/documents/{id}/chunks/pushes` (#283) to
        drive the Ingest tab's history list. Hits the
        `idx_chunk_pushes_doc_store_pushed` covering index.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM chunk_pushes
                   WHERE document_id = ?
                   ORDER BY pushed_at DESC
                   LIMIT ? OFFSET ?""",
                (document_id, limit, offset),
            )
            rows = await cursor.fetchall()
            return [_row_to_push(row) for row in rows]

    async def count_for_document(self, document_id: str) -> int:
        """Return the total number of pushes recorded for the document.

        Lets paginated callers expose a "showing N of M" hint without
        a second query against `find_for_document`.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) AS n FROM chunk_pushes WHERE document_id = ?",
                (document_id,),
            )
            row = await cursor.fetchone()
            return row["n"] if row else 0
