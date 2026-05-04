"""Store repository — SQLite CRUD for the `stores` table."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from domain.models import Store
from domain.value_objects import StoreKind
from persistence.database import get_connection


def _row_to_store(row) -> Store:
    created = row["created_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    config_raw = row["config"] or "{}"
    try:
        config = json.loads(config_raw)
    except (TypeError, ValueError):
        config = {}
    return Store(
        id=row["id"],
        name=row["name"],
        slug=row["slug"],
        kind=StoreKind(row["kind"]),
        embedder=row["embedder"],
        config=config,
        is_default=bool(row["is_default"]),
        created_at=created,
    )


class SqliteStoreRepository:
    """SQLite implementation of the StoreRepository port."""

    async def insert(self, store: Store) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO stores
                   (id, name, slug, kind, embedder, config, is_default, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    store.id,
                    store.name,
                    store.slug,
                    store.kind.value,
                    store.embedder,
                    json.dumps(store.config),
                    1 if store.is_default else 0,
                    str(store.created_at),
                ),
            )
            await db.commit()

    async def find_all(self) -> list[Store]:
        async with get_connection() as db:
            cursor = await db.execute("SELECT * FROM stores ORDER BY is_default DESC, name ASC")
            rows = await cursor.fetchall()
            return [_row_to_store(r) for r in rows]

    async def find_by_slug(self, slug: str) -> Store | None:
        async with get_connection() as db:
            cursor = await db.execute("SELECT * FROM stores WHERE slug = ?", (slug,))
            row = await cursor.fetchone()
            return _row_to_store(row) if row else None

    async def find_by_id(self, store_id: str) -> Store | None:
        async with get_connection() as db:
            cursor = await db.execute("SELECT * FROM stores WHERE id = ?", (store_id,))
            row = await cursor.fetchone()
            return _row_to_store(row) if row else None

    async def find_by_name(self, name: str) -> Store | None:
        async with get_connection() as db:
            cursor = await db.execute("SELECT * FROM stores WHERE name = ?", (name,))
            row = await cursor.fetchone()
            return _row_to_store(row) if row else None

    async def get_default(self) -> Store | None:
        """Return the seeded `default` store, if any."""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM stores WHERE is_default = 1 ORDER BY created_at ASC LIMIT 1"
            )
            row = await cursor.fetchone()
            return _row_to_store(row) if row else None

    async def update(self, store: Store) -> None:
        """Replace all mutable fields of an existing store. `id` and `created_at`
        are not touched."""
        async with get_connection() as db:
            await db.execute(
                """UPDATE stores
                   SET name = ?, slug = ?, kind = ?, embedder = ?,
                       config = ?, is_default = ?
                   WHERE id = ?""",
                (
                    store.name,
                    store.slug,
                    store.kind.value,
                    store.embedder,
                    json.dumps(store.config),
                    1 if store.is_default else 0,
                    store.id,
                ),
            )
            await db.commit()

    async def clear_default_except(self, store_id: str) -> None:
        """Reset `is_default = 0` on every store except the given id. Used to
        enforce single-default invariant when promoting a new default."""
        async with get_connection() as db:
            await db.execute(
                "UPDATE stores SET is_default = 0 WHERE id != ?",
                (store_id,),
            )
            await db.commit()

    async def delete(self, store_id: str) -> bool:
        async with get_connection() as db:
            cursor = await db.execute("DELETE FROM stores WHERE id = ?", (store_id,))
            await db.commit()
            return cursor.rowcount > 0
