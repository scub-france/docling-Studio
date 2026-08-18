"""SQLite adapter for the `AppSettingsRepository` port (#317).

Namespaced key/value override store behind the runtime-config service.
Values are opaque TEXT — the service owns (de)serialization, this adapter
only moves rows.
"""

from __future__ import annotations

from persistence.database import get_connection


class SqliteAppSettingsRepository:
    """aiosqlite-backed implementation of `AppSettingsRepository`."""

    async def get_namespace(self, namespace: str) -> dict[str, str]:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT key, value FROM app_settings WHERE namespace = ?",
                (namespace,),
            )
            rows = await cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}

    async def set_many(self, namespace: str, values: dict[str, str]) -> None:
        if not values:
            return
        async with get_connection() as db:
            await db.executemany(
                """INSERT INTO app_settings (namespace, key, value, updated_at)
                   VALUES (?, ?, ?, datetime('now'))
                   ON CONFLICT (namespace, key) DO UPDATE SET
                       value = excluded.value,
                       updated_at = excluded.updated_at""",
                [(namespace, key, value) for key, value in values.items()],
            )
            await db.commit()

    async def delete_namespace(self, namespace: str) -> int:
        async with get_connection() as db:
            cursor = await db.execute(
                "DELETE FROM app_settings WHERE namespace = ?",
                (namespace,),
            )
            await db.commit()
            return cursor.rowcount
