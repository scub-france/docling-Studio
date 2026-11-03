"""The chunkset write paths: audit rows, sequence order, atomicity (#audit-12).

Rechunk, restore, merge, split and add all rewrite several chunks at once.
These tests pin what they leave behind — the `chunk_edits` journal, the
order of the live chunkset — and require that a failure halfway through
leaves the chunkset as it was, not half replaced. Failures are injected
with a SQLite trigger so the tests hold whatever the repository code
looks like.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.models import AnalysisJob, AnalysisStatus, Chunk, Document
from domain.value_objects import ChunkResult
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_edit_repo import SqliteChunkEditRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import get_connection, init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository
from services.chunk_service import ChunkService
from services.version_service import VersionService

DOC = "doc-1"


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    monkeypatch.setattr("persistence.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()
    await SqliteDocumentRepository().insert(
        Document(id=DOC, filename="a.pdf", storage_path="/tmp/a.pdf")
    )


@pytest.fixture
def chunks():
    return SqliteChunkRepository()


@pytest.fixture
def edits():
    return SqliteChunkEditRepository()


@pytest.fixture
def chunker():
    chunker = MagicMock()
    chunker.chunk = AsyncMock(
        return_value=[
            ChunkResult(text="new-a", source_page=1, token_count=3),
            ChunkResult(text="new-b", source_page=1, token_count=3),
            ChunkResult(text="new-c", source_page=2, token_count=3),
        ]
    )
    return chunker


@pytest.fixture
def chunk_service(chunks, edits, chunker):
    return ChunkService(
        chunk_repo=chunks,
        chunk_edit_repo=edits,
        document_repo=SqliteDocumentRepository(),
        analysis_repo=SqliteAnalysisRepository(),
        chunker=chunker,
    )


@pytest.fixture
def version_service(chunks):
    return VersionService(
        version_repo=SqliteDocumentVersionRepository(),
        chunk_repo=chunks,
        document_repo=SqliteDocumentRepository(),
    )


@pytest.fixture
async def analysis():
    """A completed analysis for rechunk to read."""
    repo = SqliteAnalysisRepository()
    job = AnalysisJob(document_id=DOC, status=AnalysisStatus.COMPLETED)
    await repo.insert(job)
    job.document_json = json.dumps({"texts": []})
    job.completed_at = datetime.now(UTC)
    await repo.update_status(job)
    return job


async def _seed(chunks, texts: list[str], *, document_id: str = DOC) -> list[Chunk]:
    seeded = [Chunk(document_id=document_id, sequence=i, text=t) for i, t in enumerate(texts)]
    await chunks.insert_many(seeded)
    return seeded


async def _all_edits(document_id: str = DOC) -> list[dict]:
    """Every journal row in insertion order, raw."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT * FROM chunk_edits WHERE document_id = ? ORDER BY rowid", (document_id,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def _live(chunks, document_id: str = DOC) -> list[tuple[str, int, str]]:
    return [(c.id, c.sequence, c.text) for c in await chunks.find_for_document(document_id)]


async def _fail_on(table: str, when: str) -> None:
    """Make the next INSERT into `table` matching `when` abort."""
    async with get_connection() as db:
        await db.execute(
            f"CREATE TRIGGER fail_write BEFORE INSERT ON {table} WHEN {when} "
            "BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Journal rows and order
# ---------------------------------------------------------------------------


class TestRechunkJournal:
    async def test_one_delete_per_live_chunk_one_insert_per_new_chunk(
        self, chunk_service, chunks, analysis
    ):
        old = await _seed(chunks, ["old-a", "old-b"])
        gone = Chunk(
            document_id=DOC, sequence=9, text="gone", deleted_at=datetime(2026, 1, 1, tzinfo=UTC)
        )
        await chunks.insert(gone)

        new = await chunk_service.rechunk_document(DOC)

        rows = await _all_edits()
        assert [(r["action"], r["chunk_id"]) for r in rows] == [
            ("delete", old[0].id),
            ("delete", old[1].id),
            ("insert", new[0].id),
            ("insert", new[1].id),
            ("insert", new[2].id),
        ]
        assert {r["actor"] for r in rows} == {"system:rechunk"}
        assert len({r["at"] for r in rows}) == 1
        for row, chunk in zip(rows[:2], old, strict=True):
            before = json.loads(row["before_json"])
            assert (before["id"], before["text"], before["sequence"]) == (
                chunk.id,
                chunk.text,
                chunk.sequence,
            )
            assert row["after_json"] is None
        for row, chunk in zip(rows[2:], new, strict=True):
            after = json.loads(row["after_json"])
            assert (after["id"], after["text"], after["sequence"]) == (
                chunk.id,
                chunk.text,
                chunk.sequence,
            )
            assert row["before_json"] is None
        assert all(
            (r["parents_json"], r["children_json"], r["reason"]) == ("[]", "[]", None) for r in rows
        )

        retired = {c.id: c for c in await chunks.find_for_document(DOC, include_deleted=True)}
        assert {retired[c.id].deleted_at for c in old} == {datetime.fromisoformat(rows[0]["at"])}
        assert retired[gone.id].deleted_at == gone.deleted_at

    async def test_new_chunkset_follows_chunker_order(self, chunk_service, chunks, analysis):
        await _seed(chunks, ["old"])
        await chunk_service.rechunk_document(DOC)
        assert [(s, t) for _, s, t in await _live(chunks)] == [
            (0, "new-a"),
            (1, "new-b"),
            (2, "new-c"),
        ]


class TestRestoreJournal:
    async def test_one_delete_per_live_chunk_one_insert_per_restored_chunk(
        self, version_service, chunks
    ):
        snap = await _seed(chunks, ["v1-a", "v1-b"])
        version = await version_service.record_on_rechunk(DOC, None)
        now = datetime.now(UTC)
        for c in snap:
            await chunks.soft_delete(c.id, at=now)
        live = await _seed(chunks, ["v2-a", "v2-b", "v2-c"])

        await version_service.restore(DOC, version.id)

        restored = await chunks.find_for_document(DOC)
        assert [(c.sequence, c.text) for c in restored] == [(0, "v1-a"), (1, "v1-b")]
        assert not {c.id for c in restored} & {c.id for c in snap}, "restored chunks get new ids"

        rows = await _all_edits()
        assert [(r["action"], r["chunk_id"]) for r in rows] == [
            ("delete", live[0].id),
            ("delete", live[1].id),
            ("delete", live[2].id),
            ("insert", restored[0].id),
            ("insert", restored[1].id),
        ]
        assert {r["actor"] for r in rows} == {f"system:restore:{version.id}"}
        assert len({r["at"] for r in rows}) == 1
        assert all(r["before_json"] is None and r["after_json"] is None for r in rows)


class TestMergeJournal:
    async def test_sources_retired_one_merge_row(self, chunk_service, chunks):
        a, b, _c = await _seed(chunks, ["a", "b", "c"])

        merged = await chunk_service.merge_chunks(DOC, [b.id, a.id])

        rows = await _all_edits()
        assert [(r["action"], r["chunk_id"]) for r in rows] == [("merge", merged.id)]
        assert json.loads(rows[0]["parents_json"]) == [a.id, b.id]
        assert json.loads(rows[0]["after_json"])["text"] == "a\nb"
        assert [(s, t) for _, s, t in await _live(chunks)] == [(0, "a\nb"), (2, "c")]
        retired = {x.id: x for x in await chunks.find_for_document(DOC, include_deleted=True)}
        assert retired[a.id].deleted_at is not None
        assert retired[b.id].deleted_at is not None


class TestSequenceShift:
    async def test_add_after_anchor_shifts_only_live_chunks_of_the_document(
        self, chunk_service, chunks
    ):
        a, b, c = await _seed(chunks, ["a", "b", "c"])
        await SqliteDocumentRepository().insert(
            Document(id="doc-2", filename="b.pdf", storage_path="/tmp/b.pdf")
        )
        other = await _seed(chunks, ["other-a", "other-b"], document_id="doc-2")
        await chunks.soft_delete(b.id, at=datetime.now(UTC))
        before = {x.id: x for x in await chunks.find_for_document(DOC, include_deleted=True)}

        added = await chunk_service.add_chunk(DOC, text="new", after_id=a.id)

        assert [(s, t) for _, s, t in await _live(chunks)] == [(0, "a"), (1, "new"), (3, "c")]
        after = {x.id: x for x in await chunks.find_for_document(DOC, include_deleted=True)}
        assert after[b.id].sequence == 1, "a deleted chunk keeps its sequence"
        assert after[b.id].updated_at == before[b.id].updated_at
        assert after[a.id].updated_at == before[a.id].updated_at, "chunks before the slot untouched"
        assert after[c.id].updated_at > before[c.id].updated_at, "a shifted chunk is touched"
        assert [(s, t) for _, s, t in await _live(chunks, "doc-2")] == [
            (0, "other-a"),
            (1, "other-b"),
        ]
        assert [x.id for x in other] == [i for i, _, _ in await _live(chunks, "doc-2")]
        rows = await _all_edits()
        assert [(r["action"], r["chunk_id"]) for r in rows] == [("insert", added.id)]

    async def test_add_at_head_of_long_document_keeps_order(self, chunk_service, chunks):
        seeded = await _seed(chunks, [f"c{i}" for i in range(30)])

        await chunk_service.add_chunk(DOC, text="head", after_id=seeded[0].id)

        live = await _live(chunks)
        assert [t for _, _, t in live] == ["c0", "head", *[f"c{i}" for i in range(1, 30)]]
        assert [s for _, s, _ in live] == list(range(31))

    async def test_split_keeps_order_and_journals_children(self, chunk_service, chunks):
        a, _b = await _seed(chunks, ["abcdef", "next"])

        head, tail = await chunk_service.split_chunk(DOC, a.id, cursor_offset=3)

        assert [(s, t) for _, s, t in await _live(chunks)] == [(0, "abc"), (1, "def"), (2, "next")]
        rows = await _all_edits()
        assert [(r["action"], r["chunk_id"]) for r in rows] == [("split", a.id)]
        assert json.loads(rows[0]["children_json"]) == [head.id, tail.id]
        assert json.loads(rows[0]["before_json"])["text"] == "abcdef"


# ---------------------------------------------------------------------------
# Atomicity — a failure halfway leaves the chunkset as it was
# ---------------------------------------------------------------------------


class TestAtomicity:
    @pytest.mark.parametrize(
        ("table", "when"),
        [
            ("chunks", "NEW.text = 'new-b'"),
            ("chunk_edits", "NEW.action = 'insert'"),
        ],
        ids=["chunk-insert-fails", "journal-insert-fails"],
    )
    async def test_rechunk(self, chunk_service, chunks, analysis, table, when):
        await _seed(chunks, ["old-a", "old-b"])
        live_before = await _live(chunks)
        await _fail_on(table, when)

        with pytest.raises(sqlite3.IntegrityError):
            await chunk_service.rechunk_document(DOC)

        assert await _live(chunks) == live_before
        assert await _all_edits() == []
        assert all(
            c.deleted_at is None for c in await chunks.find_for_document(DOC, include_deleted=True)
        )

    async def test_restore(self, version_service, chunks):
        await _seed(chunks, ["v1-a", "v1-b"])
        version = await version_service.record_on_rechunk(DOC, None)
        live_before = await _live(chunks)
        await _fail_on("chunk_edits", "NEW.action = 'insert'")

        with pytest.raises(sqlite3.IntegrityError):
            await version_service.restore(DOC, version.id)

        assert await _live(chunks) == live_before
        assert await _all_edits() == []

    async def test_merge(self, chunk_service, chunks):
        a, b = await _seed(chunks, ["a", "b"])
        live_before = await _live(chunks)
        await _fail_on("chunk_edits", "NEW.action = 'merge'")

        with pytest.raises(sqlite3.IntegrityError):
            await chunk_service.merge_chunks(DOC, [a.id, b.id])

        assert await _live(chunks) == live_before
        assert await _all_edits() == []

    async def test_split_never_leaves_half_a_split(self, chunk_service, chunks):
        a, _ = await _seed(chunks, ["abcdef", "next"])
        await _fail_on("chunk_edits", "NEW.action = 'split'")

        with pytest.raises(sqlite3.IntegrityError):
            await chunk_service.split_chunk(DOC, a.id, cursor_offset=3)

        # The source survives, no head or tail appears; the shift that made
        # room may stay (sequence gaps are allowed), the order does not move.
        assert [t for _, _, t in await _live(chunks)] == ["abcdef", "next"]
        assert (await _live(chunks))[0][0] == a.id
        assert await _all_edits() == []
