"""Chunk edit / push repositories — immutable audit log + push snapshots (#205)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from domain.models import ChunkEdit, ChunkPush
from domain.value_objects import ChunkEditAction
from persistence.database import get_connection
from persistence.timestamps import parse_required_iso

if TYPE_CHECKING:
    from collections.abc import Sequence

    import aiosqlite


def _row_to_edit(row) -> ChunkEdit:
    return ChunkEdit(
        id=row["id"],
        document_id=row["document_id"],
        chunk_id=row["chunk_id"],
        action=ChunkEditAction(row["action"]),
        actor=row["actor"],
        at=parse_required_iso(row["at"], column="chunk_edits.at"),
        before=json.loads(row["before_json"]) if row["before_json"] else None,
        after=json.loads(row["after_json"]) if row["after_json"] else None,
        parents=json.loads(row["parents_json"]) if row["parents_json"] else [],
        children=json.loads(row["children_json"]) if row["children_json"] else [],
        reason=row["reason"],
    )


_INSERT_EDIT_SQL = """INSERT INTO chunk_edits
    (id, document_id, chunk_id, action, actor, at,
     before_json, after_json, parents_json, children_json, reason)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""


def _edit_to_params(edit: ChunkEdit) -> tuple:
    return (
        edit.id,
        edit.document_id,
        edit.chunk_id,
        edit.action.value,
        edit.actor,
        str(edit.at),
        json.dumps(edit.before) if edit.before is not None else None,
        json.dumps(edit.after) if edit.after is not None else None,
        json.dumps(edit.parents),
        json.dumps(edit.children),
        edit.reason,
    )


async def write_edits(db: aiosqlite.Connection, edits: Sequence[ChunkEdit]) -> None:
    """Append `edits` on `db`, in order, inside the caller's transaction.

    Does not commit: the caller journals in the same transaction as the
    chunk writes the rows describe (`SqliteChunkRepository.replace_chunkset`).
    """
    if edits:
        await db.executemany(_INSERT_EDIT_SQL, [_edit_to_params(e) for e in edits])


def _row_to_push(row) -> ChunkPush:
    return ChunkPush(
        id=row["id"],
        document_id=row["document_id"],
        store_id=row["store_id"],
        chunkset_hash=row["chunkset_hash"],
        chunk_ids=json.loads(row["chunk_ids"]) if row["chunk_ids"] else [],
        pushed_at=parse_required_iso(row["pushed_at"], column="chunk_pushes.pushed_at"),
    )


class SqliteChunkEditRepository:
    """SQLite implementation of the ChunkEditRepository port.

    The audit log is append-only: this repo offers `insert` and reads,
    but no update or delete. Operations that rewrite several chunks
    (add, split, merge, rechunk, restore) journal through
    `SqliteChunkRepository.replace_chunkset`, in the transaction of the
    chunk writes, so an aborted edit leaves no row. `insert` serves the
    single-chunk update and delete, which write the chunk first.
    """

    async def insert(self, edit: ChunkEdit) -> None:
        async with get_connection() as db:
            await write_edits(db, [edit])
            await db.commit()

    async def find_for_document(
        self,
        document_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChunkEdit]:
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM chunk_edits
                   WHERE document_id = ?
                   ORDER BY at DESC
                   LIMIT ? OFFSET ?""",
                (document_id, limit, offset),
            )
            rows = await cursor.fetchall()
            return [_row_to_edit(r) for r in rows]

    async def find_for_chunk(self, chunk_id: str) -> list[ChunkEdit]:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM chunk_edits WHERE chunk_id = ? ORDER BY at ASC",
                (chunk_id,),
            )
            rows = await cursor.fetchall()
            return [_row_to_edit(r) for r in rows]


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
