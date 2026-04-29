"""SQLite database management — async via aiosqlite."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "./data/docling_studio.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    filename        TEXT NOT NULL,
    content_type    TEXT,
    file_size       INTEGER,
    page_count      INTEGER,
    storage_path    TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id                TEXT PRIMARY KEY,
    document_id       TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status            TEXT NOT NULL DEFAULT 'PENDING',
    content_markdown  TEXT,
    content_html      TEXT,
    pages_json        TEXT,
    document_json     TEXT,
    chunks_json       TEXT,
    error_message     TEXT,
    started_at        TEXT,
    completed_at      TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status ON analysis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_created_at ON analysis_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

-- 0.6.0 — Per (document, store) ingestion state (#203).
CREATE TABLE IF NOT EXISTS stores (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL,
    embedder    TEXT NOT NULL,
    config      TEXT NOT NULL DEFAULT '{}',
    is_default  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS document_store_links (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    store_id        TEXT NOT NULL REFERENCES stores(id)    ON DELETE CASCADE,
    state           TEXT NOT NULL,
    chunkset_hash   TEXT,
    last_push_at    TEXT,
    last_run_id     TEXT,
    error_message   TEXT,
    UNIQUE (document_id, store_id)
);

CREATE INDEX IF NOT EXISTS idx_dsl_doc   ON document_store_links(document_id);
CREATE INDEX IF NOT EXISTS idx_dsl_store ON document_store_links(store_id);
CREATE INDEX IF NOT EXISTS idx_dsl_state ON document_store_links(state);
"""


# Column migrations: (table, column_name, ddl). Idempotent — applied only
# when the column is missing from the live schema. Order matters when a
# later migration depends on an earlier one (none today).
_COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    ("analysis_jobs", "document_json", "ALTER TABLE analysis_jobs ADD COLUMN document_json TEXT"),
    ("analysis_jobs", "chunks_json", "ALTER TABLE analysis_jobs ADD COLUMN chunks_json TEXT"),
    (
        "analysis_jobs",
        "progress_current",
        "ALTER TABLE analysis_jobs ADD COLUMN progress_current INTEGER",
    ),
    (
        "analysis_jobs",
        "progress_total",
        "ALTER TABLE analysis_jobs ADD COLUMN progress_total INTEGER",
    ),
    # 0.6.0 — Document lifecycle state machine (#202).
    (
        "documents",
        "lifecycle_state",
        "ALTER TABLE documents ADD COLUMN lifecycle_state TEXT NOT NULL DEFAULT 'Uploaded'",
    ),
    (
        "documents",
        "lifecycle_state_at",
        "ALTER TABLE documents ADD COLUMN lifecycle_state_at TEXT",
    ),
]

# DDL statements run after column migrations — typically CREATE INDEX
# IF NOT EXISTS for indexes on freshly-added columns.
_POST_MIGRATION_DDL: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_documents_lifecycle_state ON documents(lifecycle_state)",
]


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Apply additive column migrations, then any post-migration DDL.

    Existing columns are detected via PRAGMA `table_info`, so re-running
    the migration on an already-up-to-date DB is a no-op.
    """
    columns_by_table: dict[str, set[str]] = {}
    for table, col_name, ddl in _COLUMN_MIGRATIONS:
        if table not in columns_by_table:
            cursor = await db.execute(f"PRAGMA table_info({table})")
            columns_by_table[table] = {row[1] for row in await cursor.fetchall()}
        if col_name not in columns_by_table[table]:
            await db.execute(ddl)
            columns_by_table[table].add(col_name)
            logger.info("Migration: added column %s to %s", col_name, table)
    for ddl in _POST_MIGRATION_DDL:
        await db.execute(ddl)
    await db.commit()


async def init_db() -> None:
    """Create database file and tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await _run_migrations(db)
        await _seed_default_store(db)
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)


async def _seed_default_store(db: aiosqlite.Connection) -> None:
    """Insert the canonical `default` store on first boot.

    Idempotent — uses INSERT OR IGNORE keyed on the unique slug. The
    embedder is read from the DEFAULT_EMBEDDER env var with a sensible
    fallback so existing single-index deployments keep working.
    """
    embedder = os.environ.get("DEFAULT_EMBEDDER", "bge-m3")
    await db.execute(
        """INSERT OR IGNORE INTO stores
           (id, name, slug, kind, embedder, config, is_default, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        ("default", "default", "default", "opensearch", embedder, "{}", 1),
    )


async def get_db() -> aiosqlite.Connection:
    """Open a new database connection with row factory and FK enforcement."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Context manager that opens and auto-closes a database connection."""
    db = await get_db()
    try:
        yield db
    finally:
        await db.close()
