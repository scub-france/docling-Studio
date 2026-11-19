"""Booting 0.7.4 on a database created by 0.7.3 (#391)."""

from __future__ import annotations

import sqlite3

import pytest

from domain.models import DocumentVersion, DocumentVersionKind
from persistence import database
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository

# The three 0.7.3 tables the upgrade reads or changes, copied from the 0.7.3
# schema. `init_db()` creates every other table, as it would on that install.
_SCHEMA_0_7_3 = """
CREATE TABLE documents (
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
CREATE TABLE analysis_jobs (
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
CREATE TABLE document_versions (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL
                    CHECK (kind IN ('analysis','chunks')),
    analysis_id     TEXT,
    chunks_snapshot TEXT,
    summary         TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);
"""

_ROWS_0_7_3 = """
INSERT INTO documents (id, filename, storage_path) VALUES
    ('doc-json', 'a.pdf', '/tmp/a.pdf'),
    ('doc-batched', 'b.pdf', '/tmp/b.pdf'),
    ('doc-failed', 'c.pdf', '/tmp/c.pdf'),
    ('doc-new', 'd.pdf', '/tmp/d.pdf');
INSERT INTO analysis_jobs (id, document_id, status, document_json, completed_at) VALUES
    ('json-old', 'doc-json', 'COMPLETED', '{}', '2026-10-01T10:00:00'),
    ('json-new', 'doc-json', 'COMPLETED', '{}', '2026-10-02T10:00:00'),
    ('json-failed', 'doc-json', 'FAILED', NULL, '2026-10-03T10:00:00'),
    ('batched-with-json', 'doc-batched', 'COMPLETED', '{}', '2026-10-01T10:00:00'),
    ('batched-without-json', 'doc-batched', 'COMPLETED', NULL, '2026-10-02T10:00:00'),
    ('only-failed', 'doc-failed', 'FAILED', NULL, '2026-10-01T10:00:00');
INSERT INTO document_versions (id, document_id, kind, analysis_id, summary, created_at) VALUES
    ('v-old', 'doc-json', 'analysis', 'json-new', 'Analysis', '2026-10-02T10:00:00');
"""


@pytest.fixture
def db_path(tmp_path, monkeypatch) -> str:
    path = str(tmp_path / "studio-0.7.3.db")
    with sqlite3.connect(path) as db:
        db.executescript(_SCHEMA_0_7_3)
        db.executescript(_ROWS_0_7_3)
    monkeypatch.setattr(database, "DB_PATH", path)
    return path


def _columns(path: str, table: str) -> list[str]:
    with sqlite3.connect(path) as db:
        return [row[1] for row in db.execute(f"PRAGMA table_info({table})")]


def _active(path: str) -> dict[str, str | None]:
    with sqlite3.connect(path) as db:
        return dict(
            db.execute("SELECT document_id, active_analysis_id FROM document_analysis_state")
        )


@pytest.mark.asyncio
async def test_upgrade_adds_the_document_version_columns_and_keeps_old_rows(db_path):
    await database.init_db()

    columns = _columns(db_path, "document_versions")
    assert "chunks_source_analysis_id" in columns
    assert "chunks_source_result_hash" in columns
    versions = SqliteDocumentVersionRepository()
    old = await versions.find_by_id("v-old")
    assert old is not None
    assert old.chunks_source_analysis_id is None
    await versions.insert(
        DocumentVersion(
            id="v-new",
            document_id="doc-json",
            kind=DocumentVersionKind.CHUNKS,
            analysis_id="json-new",
            chunks_source_analysis_id="json-new",
            chunks_source_result_hash="a" * 64,
            chunks_snapshot="[]",
            summary="Chunks generated",
        )
    )
    assert (await versions.find_by_id("v-new")).chunks_source_result_hash == "a" * 64


@pytest.mark.asyncio
async def test_upgrade_selects_the_latest_completed_analysis_with_a_docling_document(db_path):
    await database.init_db()

    assert _active(db_path) == {
        "doc-json": "json-new",
        # The newer batched run kept no Docling document; 0.7.3 chunked the older one.
        "doc-batched": "batched-with-json",
    }
    state = await SqliteDocumentAnalysisRepository().find_state("doc-json")
    assert state is not None
    assert state.active_analysis_id == "json-new"


@pytest.mark.asyncio
async def test_upgrade_falls_back_to_a_completed_analysis_without_docling_document(db_path):
    with sqlite3.connect(db_path) as db:
        db.execute("DELETE FROM analysis_jobs WHERE id = 'batched-with-json'")

    await database.init_db()

    assert _active(db_path)["doc-batched"] == "batched-without-json"


@pytest.mark.asyncio
async def test_upgrade_is_idempotent_and_keeps_user_choices(db_path):
    await database.init_db()
    states = SqliteDocumentAnalysisRepository()
    state = await states.find_state("doc-json")
    state.clear_selection()
    await states.save_state(state)

    await database.init_db()

    assert _active(db_path) == {"doc-json": None, "doc-batched": "batched-with-json"}
    assert _columns(db_path, "document_versions").count("chunks_source_analysis_id") == 1


@pytest.mark.asyncio
async def test_fresh_database_needs_no_upgrade(tmp_path, monkeypatch):
    path = str(tmp_path / "fresh.db")
    monkeypatch.setattr(database, "DB_PATH", path)

    await database.init_db()
    await database.init_db()

    assert _active(path) == {}
