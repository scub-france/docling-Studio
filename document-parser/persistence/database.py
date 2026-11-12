"""SQLite database management — async via aiosqlite.

The schema is authoritative for new databases.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "./data/docling_studio.db")

# Schema is authoritative. Every enum-shaped TEXT column carries a
# CHECK constraint mirroring the domain enum it stores — see
# `domain/value_objects.py` and `domain/models.py`. Triggers maintain
# `updated_at` on mutable rows (documents, stores) so the column
# reflects the last write without service-layer plumbing.
_SCHEMA = """
-- Documents — aggregate root. Lifecycle state machine (#202) lives
-- inline; CHECK enforces the six canonical states from
-- DocumentLifecycleState. `updated_at` mirrors `lifecycle_state_at` for
-- generic "last touch" queries (renames, retags, future fields).
CREATE TABLE IF NOT EXISTS documents (
    id                  TEXT PRIMARY KEY,
    filename            TEXT NOT NULL,
    content_type        TEXT,
    file_size           INTEGER,
    page_count          INTEGER,
    storage_path        TEXT NOT NULL,
    lifecycle_state     TEXT NOT NULL DEFAULT 'Uploaded'
                        CHECK (lifecycle_state IN
                            ('Uploaded','Parsed','Chunked','Ingested','Stale','Failed')),
    lifecycle_state_at  TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_documents_created_at      ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_lifecycle_state ON documents(lifecycle_state);

CREATE TRIGGER IF NOT EXISTS documents_touch_updated_at
AFTER UPDATE ON documents FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE documents SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Analysis jobs — one row per Docling conversion run. Status CHECK
-- mirrors `domain.models.AnalysisStatus`. The four heavy columns
-- (content_markdown, content_html, pages_json, document_json) are kept
-- on the same row in 0.6.1; splitting them into `analysis_artifacts`
-- is tracked as a follow-up cleanup (see #279 scope comment).
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id                TEXT PRIMARY KEY,
    document_id       TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status            TEXT NOT NULL DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
    content_markdown  TEXT,
    content_html      TEXT,
    pages_json        TEXT,
    document_json     TEXT,
    chunks_json       TEXT,
    progress_current  INTEGER,
    progress_total    INTEGER,
    error_message     TEXT,
    started_at        TEXT,
    completed_at      TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status     ON analysis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_created_at ON analysis_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_doc_status ON analysis_jobs(document_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_jobs_doc_id ON analysis_jobs(document_id, id);

-- One document-level connection for the active analysis and the result that
-- produced the live chunks. The chunk source is soft so deleting an analysis
-- does not erase stale provenance; the active FK clears on analysis deletion.
CREATE TABLE IF NOT EXISTS document_analysis_state (
    document_id TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    active_analysis_id TEXT REFERENCES analysis_jobs(id) ON DELETE SET NULL,
    chunks_source_analysis_id TEXT,
    chunks_source_result_hash TEXT,
    CHECK ((chunks_source_analysis_id IS NULL) = (chunks_source_result_hash IS NULL))
);

CREATE TRIGGER IF NOT EXISTS document_analysis_state_validate_insert
BEFORE INSERT ON document_analysis_state
WHEN NEW.active_analysis_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM analysis_jobs
    WHERE id = NEW.active_analysis_id AND document_id = NEW.document_id
)
BEGIN
    SELECT RAISE(ABORT, 'Active analysis must belong to the document');
END;

CREATE TRIGGER IF NOT EXISTS document_analysis_state_validate_update
BEFORE UPDATE OF active_analysis_id ON document_analysis_state
WHEN NEW.active_analysis_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM analysis_jobs
    WHERE id = NEW.active_analysis_id AND document_id = NEW.document_id
)
BEGIN
    SELECT RAISE(ABORT, 'Active analysis must belong to the document');
END;

-- Stores — logical ingestion destinations (#203). Connection fields
-- (#279) are introduced here in 0.6.1: URI, username, and an
-- encrypted password (sealed via the Fernet box keyed by
-- STORE_SECRET_KEY). `config` keeps the kind-specific application
-- knobs (vector_index_name, database, …). `updated_at` is maintained
-- by trigger.
CREATE TABLE IF NOT EXISTS stores (
    id                          TEXT PRIMARY KEY,
    name                        TEXT NOT NULL UNIQUE,
    slug                        TEXT NOT NULL UNIQUE,
    kind                        TEXT NOT NULL
                                CHECK (kind IN ('opensearch','neo4j')),
    embedder                    TEXT NOT NULL,
    config                      TEXT NOT NULL DEFAULT '{}',
    connection_uri              TEXT,
    connection_username         TEXT,
    connection_password_sealed  TEXT,  -- Fernet ciphertext; NULL = no auth
    is_default                  INTEGER NOT NULL DEFAULT 0
                                CHECK (is_default IN (0,1)),
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TRIGGER IF NOT EXISTS stores_touch_updated_at
AFTER UPDATE ON stores FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE stores SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Per (document, store) live link — drives the Ingest view badges.
-- State CHECK mirrors `domain.value_objects.DocumentStoreLinkState`.
-- `last_run_id` is a soft reference to `chunk_pushes(id)` — kept soft
-- so a push history purge does not cascade into the live link state.
CREATE TABLE IF NOT EXISTS document_store_links (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    store_id        TEXT NOT NULL REFERENCES stores(id)    ON DELETE CASCADE,
    state           TEXT NOT NULL
                    CHECK (state IN ('Ingested','Stale','Failed')),
    chunkset_hash   TEXT,
    last_push_at    TEXT,
    last_run_id     TEXT,
    error_message   TEXT,
    UNIQUE (document_id, store_id)
);
CREATE INDEX IF NOT EXISTS idx_dsl_doc   ON document_store_links(document_id);
CREATE INDEX IF NOT EXISTS idx_dsl_store ON document_store_links(store_id);
CREATE INDEX IF NOT EXISTS idx_dsl_state ON document_store_links(state);

-- Canonical chunkset (#205). Soft-delete via `deleted_at`.
CREATE TABLE IF NOT EXISTS chunks (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    sequence      INTEGER NOT NULL,
    text          TEXT NOT NULL,
    headings      TEXT NOT NULL DEFAULT '[]',
    source_page   INTEGER,
    bboxes        TEXT NOT NULL DEFAULT '[]',
    doc_items     TEXT NOT NULL DEFAULT '[]',
    token_count   INTEGER,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    deleted_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc     ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_seq ON chunks(document_id, sequence);

-- Immutable push audit. Compound index covers the "last push for (doc,
-- store)" lookup that drives the diff endpoint and the link upsert.
CREATE TABLE IF NOT EXISTS chunk_pushes (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    store_id      TEXT NOT NULL REFERENCES stores(id)    ON DELETE CASCADE,
    chunkset_hash TEXT NOT NULL,
    chunk_ids     TEXT NOT NULL,
    pushed_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunk_pushes_doc_store        ON chunk_pushes(document_id, store_id);
CREATE INDEX IF NOT EXISTS idx_chunk_pushes_doc_store_pushed
    ON chunk_pushes(document_id, store_id, pushed_at DESC);

-- Runtime config overrides (#317) — namespaced key/value store. Values
-- are opaque TEXT; the consuming service owns (de)serialization. Env
-- vars are bootstrap defaults, rows here override them at runtime.
-- `reasoning` is the first namespace.
CREATE TABLE IF NOT EXISTS app_settings (
    namespace   TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (namespace, key)
);

-- Document versions (#267) — frozen (analysis, chunks) snapshots
-- created on explicit triggers (new analysis, generate chunks). Kind
-- CHECK mirrors `domain.models.DocumentVersionKind` (lowercase).
-- `analysis_id` is soft: a deleted analysis becomes a "stale" pointer,
-- the frontend renders a badge rather than 404-ing the row.
CREATE TABLE IF NOT EXISTS document_versions (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL
                    CHECK (kind IN ('analysis','chunks')),
    analysis_id     TEXT,
    chunks_source_analysis_id TEXT,
    chunks_source_result_hash TEXT,
    chunks_snapshot TEXT,
    summary         TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    CHECK ((chunks_source_analysis_id IS NULL) = (chunks_source_result_hash IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_document_versions_doc_created
    ON document_versions(document_id, created_at);
CREATE INDEX IF NOT EXISTS idx_document_versions_doc_kind_created
    ON document_versions(document_id, kind, created_at DESC);

-- One edit stream per immutable conversion analysis. Commands are durable
-- user intent; edited_analysis_cache is a replaceable projection.
CREATE TABLE IF NOT EXISTS analysis_edit_streams (
    analysis_id TEXT PRIMARY KEY REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    base_document_hash TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_edit_commands (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_edit_streams(analysis_id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL CHECK(sequence > 0),
    command_version INTEGER NOT NULL CHECK(command_version > 0),
    command_type TEXT NOT NULL CHECK(command_type IN
        ('replaceText','mergeText','setHeadingLevel','moveElement','deleteElement','deleteElements',
         'setCommandActive')),
    payload_json TEXT NOT NULL,
    previous_hash TEXT,
    command_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(analysis_id, sequence),
    UNIQUE(analysis_id, command_hash)
);

CREATE TABLE IF NOT EXISTS edited_analysis_cache (
    analysis_id TEXT PRIMARY KEY REFERENCES analysis_edit_streams(analysis_id) ON DELETE CASCADE,
    applied_through_sequence INTEGER NOT NULL DEFAULT 0,
    document_json TEXT NOT NULL,
    content_markdown TEXT NOT NULL,
    content_html TEXT NOT NULL,
    pages_json TEXT NOT NULL,
    editor_model_json TEXT NOT NULL,
    command_stream_hash TEXT NOT NULL,
    result_hash TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


async def init_db() -> None:
    """Create database file and tables if they don't exist.

    Runs the canonical schema and seeds the default store.
    """
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await _seed_default_store(db)
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)


async def _seed_default_store(db: aiosqlite.Connection) -> None:
    """Insert the canonical `default` store on first boot.

    Idempotent — uses INSERT OR IGNORE keyed on the unique slug. The
    embedder is read from the DEFAULT_EMBEDDER env var with a sensible
    fallback so existing single-index deployments keep working. No
    connection_* values are seeded — the operator either fills them
    via the API/UI or sets env-var fallbacks (covered in #279 wiring).
    """
    embedder = os.environ.get("DEFAULT_EMBEDDER", "bge-m3")
    # Connection columns are intentionally left NULL — the default
    # store seeds happily on any backend (with or without
    # STORE_SECRET_KEY). The operator fills them via the API / UI when
    # they actually want to push to a real endpoint.
    await db.execute(
        """INSERT OR IGNORE INTO stores
           (id, name, slug, kind, embedder, config,
            connection_uri, connection_username, connection_password_sealed,
            is_default, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?,
                   datetime('now'), datetime('now'))""",
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
