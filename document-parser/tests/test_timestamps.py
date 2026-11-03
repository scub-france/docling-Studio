"""Timestamp columns read back as aware UTC datetimes (#audit-05)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from domain.models import AnalysisJob, ChunkEdit, Document
from domain.value_objects import ChunkEditAction
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_edit_repo import SqliteChunkEditRepository
from persistence.database import get_connection, init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.store_repo import SqliteStoreRepository
from persistence.timestamps import parse_iso, parse_required_iso


class TestParseIso:
    @pytest.mark.parametrize("empty", [None, ""])
    def test_empty_is_none(self, empty):
        assert parse_iso(empty) is None

    def test_naive_text_is_read_as_utc(self):
        """`str()` of a naive datetime, as a test or an old row would write it."""
        assert parse_iso("2026-11-03 10:15:30.123456") == datetime(
            2026, 11, 3, 10, 15, 30, 123456, tzinfo=UTC
        )

    def test_sqlite_default_is_read_as_utc(self):
        """`datetime('now')` (schema defaults, `updated_at` triggers)."""
        parsed = parse_iso("2026-11-03 10:15:30")
        assert parsed == datetime(2026, 11, 3, 10, 15, 30, tzinfo=UTC)
        assert parsed.tzinfo is UTC

    def test_written_value_round_trips(self):
        """What every repository writes: `str()` of an aware UTC datetime."""
        written = datetime(2026, 11, 3, 10, 15, 30, 5, tzinfo=UTC)
        parsed = parse_iso(str(written))
        assert parsed == written
        assert parsed.tzinfo is UTC

    def test_other_offset_becomes_utc_same_instant(self):
        parsed = parse_iso("2026-11-03T12:15:30+02:00")
        assert parsed == datetime(2026, 11, 3, 10, 15, 30, tzinfo=UTC)
        assert parsed.utcoffset() == timedelta(0)
        assert str(parsed) == "2026-11-03 10:15:30+00:00"

    def test_zulu_suffix(self):
        assert parse_iso("2026-11-03T10:15:30Z") == datetime(2026, 11, 3, 10, 15, 30, tzinfo=UTC)

    def test_datetime_input_naive_and_aware(self):
        assert parse_iso(datetime(2026, 1, 1)) == datetime(2026, 1, 1, tzinfo=UTC)
        cet = timezone(timedelta(hours=1))
        parsed = parse_iso(datetime(2026, 1, 1, 1, 0, tzinfo=cet))
        assert parsed == datetime(2026, 1, 1, tzinfo=UTC)
        assert parsed.utcoffset() == timedelta(0)

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            parse_iso("not a date")


class TestParseRequiredIso:
    def test_value_is_parsed(self):
        assert parse_required_iso("2026-11-03 10:15:30", column="t.c") == datetime(
            2026, 11, 3, 10, 15, 30, tzinfo=UTC
        )

    @pytest.mark.parametrize("empty", [None, ""])
    def test_empty_raises_naming_the_column(self, empty):
        with pytest.raises(ValueError, match=r"chunk_edits\.at"):
            parse_required_iso(empty, column="chunk_edits.at")


class TestRepositoriesReadUtc:
    @pytest.fixture(autouse=True)
    async def setup_db(self, monkeypatch, tmp_path):
        monkeypatch.setattr("persistence.database.DB_PATH", str(tmp_path / "test.db"))
        await init_db()

    @pytest.fixture
    async def doc(self):
        document = Document(id="doc-1", filename="a.pdf", storage_path="/tmp/a.pdf")
        await SqliteDocumentRepository().insert(document)
        return document

    async def test_analysis_job_naive_row_reads_aware(self, doc):
        """`analysis_repo` was the one copy without UTC coercion."""
        repo = SqliteAnalysisRepository()
        job = AnalysisJob(document_id=doc.id)
        await repo.insert(job)
        async with get_connection() as db:
            await db.execute(
                "UPDATE analysis_jobs SET created_at = ?, started_at = ? WHERE id = ?",
                ("2026-11-03 10:00:00", "2026-11-03 10:00:01", job.id),
            )
            await db.commit()

        found = await repo.find_by_id(job.id)
        assert found.created_at == datetime(2026, 11, 3, 10, 0, 0, tzinfo=UTC)
        assert found.started_at == datetime(2026, 11, 3, 10, 0, 1, tzinfo=UTC)
        assert found.completed_at is None

    async def test_seeded_store_default_timestamps_read_aware(self):
        """The default store's dates come from SQLite's naive `datetime('now')`."""
        store = await SqliteStoreRepository().get_default()
        assert store.created_at.tzinfo is UTC
        assert store.updated_at.tzinfo is UTC

    async def test_empty_audit_date_is_an_error_not_now(self, doc):
        """A NOT NULL date read empty used to come back as "now", rewriting
        the audit trail; it is now reported as the corrupt row it is."""
        repo = SqliteChunkEditRepository()
        await repo.insert(
            ChunkEdit(
                id="e1",
                document_id=doc.id,
                chunk_id="c1",
                action=ChunkEditAction.INSERT,
                actor="user",
                at=datetime.now(UTC),
            )
        )
        async with get_connection() as db:
            await db.execute("UPDATE chunk_edits SET at = ''")
            await db.commit()

        with pytest.raises(ValueError, match=r"chunk_edits\.at"):
            await repo.find_for_document(doc.id)
