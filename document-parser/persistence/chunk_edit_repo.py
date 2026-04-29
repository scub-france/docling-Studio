"""Chunk edit / push repositories — immutable audit log + push snapshots (#205)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from domain.models import ChunkEdit, ChunkPush
from domain.value_objects import ChunkEditAction
from persistence.database import get_connection


def _parse_iso(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _row_to_edit(row) -> ChunkEdit:
    return ChunkEdit(
        id=row["id"],
        document_id=row["document_id"],
        chunk_id=row["chunk_id"],
        action=ChunkEditAction(row["action"]),
        actor=row["actor"],
        at=_parse_iso(row["at"]) or datetime.now(UTC),
        before=json.loads(row["before_json"]) if row["before_json"] else None,
        after=json.loads(row["after_json"]) if row["after_json"] else None,
        parents=json.loads(row["parents_json"]) if row["parents_json"] else [],
        children=json.loads(row["children_json"]) if row["children_json"] else [],
        reason=row["reason"],
    )


def _row_to_push(row) -> ChunkPush:
    return ChunkPush(
        id=row["id"],
        document_id=row["document_id"],
        store_id=row["store_id"],
        chunkset_hash=row["chunkset_hash"],
        chunk_ids=json.loads(row["chunk_ids"]) if row["chunk_ids"] else [],
        pushed_at=_parse_iso(row["pushed_at"]) or datetime.now(UTC),
    )


class SqliteChunkEditRepository:
    """SQLite implementation of the ChunkEditRepository port.

    The audit log is append-only: this repo offers `insert` and reads,
    but no update or delete. Aborted edits should not produce an audit
    row in the first place — that contract is enforced in the service
    layer (audit + chunk write happen in the same SQL transaction).
    """

    async def insert(self, edit: ChunkEdit) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO chunk_edits
                   (id, document_id, chunk_id, action, actor, at,
                    before_json, after_json, parents_json, children_json, reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
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
                ),
            )
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
