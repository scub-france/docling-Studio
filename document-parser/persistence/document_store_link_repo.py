"""Document-Store link repository — SQLite CRUD on `document_store_links`."""

from __future__ import annotations

from datetime import UTC, datetime

from domain.models import DocumentStoreLink
from domain.value_objects import DocumentStoreLinkState
from persistence.database import get_connection


def _parse_iso(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _row_to_link(row) -> DocumentStoreLink:
    return DocumentStoreLink(
        id=row["id"],
        document_id=row["document_id"],
        store_id=row["store_id"],
        state=DocumentStoreLinkState(row["state"]),
        chunkset_hash=row["chunkset_hash"],
        last_push_at=_parse_iso(row["last_push_at"]),
        last_run_id=row["last_run_id"],
        error_message=row["error_message"],
    )


class SqliteDocumentStoreLinkRepository:
    """SQLite implementation of the DocumentStoreLinkRepository port."""

    async def upsert(self, link: DocumentStoreLink) -> None:
        """Insert a new link or update the existing (document_id, store_id) row."""
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO document_store_links
                   (id, document_id, store_id, state, chunkset_hash,
                    last_push_at, last_run_id, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(document_id, store_id) DO UPDATE SET
                     state         = excluded.state,
                     chunkset_hash = excluded.chunkset_hash,
                     last_push_at  = excluded.last_push_at,
                     last_run_id   = excluded.last_run_id,
                     error_message = excluded.error_message""",
                (
                    link.id,
                    link.document_id,
                    link.store_id,
                    link.state.value,
                    link.chunkset_hash,
                    str(link.last_push_at) if link.last_push_at else None,
                    link.last_run_id,
                    link.error_message,
                ),
            )
            await db.commit()

    async def find_for_document(self, document_id: str) -> list[DocumentStoreLink]:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM document_store_links WHERE document_id = ?",
                (document_id,),
            )
            rows = await cursor.fetchall()
            return [_row_to_link(r) for r in rows]

    async def find_for_store(self, store_id: str) -> list[DocumentStoreLink]:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM document_store_links WHERE store_id = ?",
                (store_id,),
            )
            rows = await cursor.fetchall()
            return [_row_to_link(r) for r in rows]

    async def find_one(self, document_id: str, store_id: str) -> DocumentStoreLink | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM document_store_links WHERE document_id = ? AND store_id = ?",
                (document_id, store_id),
            )
            row = await cursor.fetchone()
            return _row_to_link(row) if row else None

    async def delete(self, document_id: str, store_id: str) -> bool:
        async with get_connection() as db:
            cursor = await db.execute(
                "DELETE FROM document_store_links WHERE document_id = ? AND store_id = ?",
                (document_id, store_id),
            )
            await db.commit()
            return cursor.rowcount > 0
