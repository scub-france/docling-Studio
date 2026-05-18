"""Store repository — SQLite CRUD for the `stores` table.

Connection identity (#279):

  - `connection_uri` and `connection_username` are plain TEXT columns
    on `stores`. They show up on the `Store` dataclass and travel
    through every read.
  - `connection_password_sealed` holds Fernet ciphertext. The plaintext
    NEVER appears on the `Store` dataclass — it is fetched only through
    `get_connection_password()` and written only through
    `set_connection_password()` / the `password=` kwarg on `insert()`.

This split keeps the plaintext out of the entity's serialization path
(Pydantic, __repr__, logs). The API layer reads/writes the password
through dedicated endpoints and never echoes it back in responses.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from domain.models import Store
from domain.value_objects import StoreKind
from infra.secrets import get_fernet_box
from persistence.database import get_connection


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _row_to_store(row) -> Store:
    config_raw = row["config"] or "{}"
    try:
        config = json.loads(config_raw)
    except (TypeError, ValueError):
        config = {}
    # `updated_at` is NOT NULL with a server-side default since the
    # 0.6.1 schema reset, so the column is always present.
    return Store(
        id=row["id"],
        name=row["name"],
        slug=row["slug"],
        kind=StoreKind(row["kind"]),
        embedder=row["embedder"],
        config=config,
        connection_uri=row["connection_uri"],
        connection_username=row["connection_username"],
        # Surface the presence of a sealed password without ever
        # touching the Fernet box on a regular list/read.
        has_connection_password=row["connection_password_sealed"] is not None,
        is_default=bool(row["is_default"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


class SqliteStoreRepository:
    """SQLite implementation of the StoreRepository port."""

    async def insert(self, store: Store, *, password: str | None = None) -> None:
        """Persist a new store.

        `password` is a separate kwarg (not a Store field) so that
        plaintext never lives on the entity. When non-None, the value
        is sealed via Fernet before the INSERT — meaning the boot
        precondition (STORE_SECRET_KEY) is enforced lazily at the
        first password-writing call, not at module import.
        """
        sealed = get_fernet_box().seal(password) if password is not None else None
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO stores
                   (id, name, slug, kind, embedder, config,
                    connection_uri, connection_username, connection_password_sealed,
                    is_default, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    store.id,
                    store.name,
                    store.slug,
                    store.kind.value,
                    store.embedder,
                    json.dumps(store.config),
                    store.connection_uri,
                    store.connection_username,
                    sealed,
                    1 if store.is_default else 0,
                    str(store.created_at),
                    str(store.updated_at),
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
        """Replace mutable, non-secret fields of an existing store.

        `id`, `created_at`, and `connection_password_sealed` are never
        touched here. The password has its own write path
        (`set_connection_password`) so PATCH calls that don't include
        a password don't accidentally clear the existing one.
        `updated_at` is touched by the schema-side trigger.
        """
        async with get_connection() as db:
            await db.execute(
                """UPDATE stores
                   SET name = ?, slug = ?, kind = ?, embedder = ?,
                       config = ?, connection_uri = ?, connection_username = ?,
                       is_default = ?
                   WHERE id = ?""",
                (
                    store.name,
                    store.slug,
                    store.kind.value,
                    store.embedder,
                    json.dumps(store.config),
                    store.connection_uri,
                    store.connection_username,
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

    # -- password access (separate path on purpose; see module docstring)

    async def get_connection_password(self, store_id: str) -> str | None:
        """Return the plaintext connection password for `store_id`.

        Returns None when the store has no sealed password. Raises
        `StoreSecretKeyMissingError` / `SealedValueTamperedError` from
        `infra.secrets` if the Fernet box cannot open the row — both
        cases the caller (driver pool) handles by surfacing a clear
        boot/connect error.

        The returned string must NEVER be logged or serialised. Treat
        it as memory-only and pass it directly to the driver factory.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT connection_password_sealed FROM stores WHERE id = ?",
                (store_id,),
            )
            row = await cursor.fetchone()
        if row is None or row["connection_password_sealed"] is None:
            return None
        return get_fernet_box().open(row["connection_password_sealed"])

    async def set_connection_password(self, store_id: str, plaintext: str | None) -> bool:
        """Seal `plaintext` and write it as the store's password.

        `None` clears the column (the store reverts to "no password
        set"). Returns True when a row was affected, False otherwise
        (unknown store_id). The Fernet box is only invoked when the
        plaintext is non-None, so a clear operation works even on a
        backend booted without STORE_SECRET_KEY.
        """
        sealed = get_fernet_box().seal(plaintext) if plaintext is not None else None
        async with get_connection() as db:
            cursor = await db.execute(
                "UPDATE stores SET connection_password_sealed = ? WHERE id = ?",
                (sealed, store_id),
            )
            await db.commit()
            return cursor.rowcount > 0
