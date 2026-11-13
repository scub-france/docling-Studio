"""Tests for the chunk and chunk push repositories (#205)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.models import Chunk, ChunkPush, Document
from domain.value_objects import ChunkBbox
from persistence.chunk_push_repo import SqliteChunkPushRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()
    yield


@pytest.fixture
async def doc():
    repo = SqliteDocumentRepository()
    document = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
    await repo.insert(document)
    return document


@pytest.fixture
def chunk_repo():
    return SqliteChunkRepository()


@pytest.fixture
def push_repo():
    return SqliteChunkPushRepository()


class TestChunkRepo:
    async def test_insert_and_find_for_document(self, doc, chunk_repo):
        c = Chunk(
            id="c-1",
            document_id=doc.id,
            sequence=0,
            text="alpha",
            headings=["A"],
            source_page=1,
            bboxes=[ChunkBbox(page=1, bbox=[0, 0, 10, 10])],
        )
        await chunk_repo.insert(c)

        out = await chunk_repo.find_for_document(doc.id)
        assert len(out) == 1
        assert out[0].id == "c-1"
        assert out[0].text == "alpha"
        assert out[0].headings == ["A"]
        assert out[0].bboxes[0].bbox == [0, 0, 10, 10]

    async def test_insert_many_round_trips(self, doc, chunk_repo):
        chunks = [
            Chunk(id=f"c-{i}", document_id=doc.id, sequence=i, text=f"t{i}") for i in range(5)
        ]
        await chunk_repo.insert_many(chunks)

        out = await chunk_repo.find_for_document(doc.id)
        assert len(out) == 5
        # Returned in sequence order.
        assert [c.id for c in out] == [f"c-{i}" for i in range(5)]

    async def test_soft_delete_excludes_chunk_unless_requested(self, doc, chunk_repo):
        await chunk_repo.insert(Chunk(id="c-1", document_id=doc.id, sequence=0, text="a"))
        await chunk_repo.soft_delete("c-1", at=datetime(2026, 4, 29, 12, tzinfo=UTC))

        active = await chunk_repo.find_for_document(doc.id)
        assert active == []

        all_chunks = await chunk_repo.find_for_document(doc.id, include_deleted=True)
        assert len(all_chunks) == 1
        assert all_chunks[0].deleted_at is not None

    async def test_soft_delete_many_hits_only_the_given_ids(self, doc, chunk_repo):
        await chunk_repo.insert_many(
            [Chunk(id=f"c-{i}", document_id=doc.id, sequence=i, text=f"t{i}") for i in range(3)]
        )
        at = datetime(2026, 4, 29, 12, tzinfo=UTC)

        hit = await chunk_repo.soft_delete_many(["c-0", "c-2", "missing"], at=at)

        assert hit == 2
        assert [c.id for c in await chunk_repo.find_for_document(doc.id)] == ["c-1"]
        deleted = await chunk_repo.find_by_id("c-2")
        assert deleted is not None
        assert deleted.deleted_at == at
        assert deleted.updated_at == at

    async def test_soft_delete_many_with_no_ids_is_a_no_op(self, doc, chunk_repo):
        await chunk_repo.insert(Chunk(id="c-1", document_id=doc.id, sequence=0, text="a"))

        assert await chunk_repo.soft_delete_many([], at=datetime.now(UTC)) == 0
        assert len(await chunk_repo.find_for_document(doc.id)) == 1

    async def test_soft_delete_for_document_hits_live_chunks_of_that_document_only(
        self, doc, chunk_repo
    ):
        other = Document(id="doc-2", filename="o.pdf", storage_path="/tmp/o.pdf")
        await SqliteDocumentRepository().insert(other)
        await chunk_repo.insert_many(
            [
                Chunk(id="c-0", document_id=doc.id, sequence=0, text="a"),
                Chunk(id="c-1", document_id=doc.id, sequence=1, text="b"),
                Chunk(id="c-old", document_id=doc.id, sequence=2, text="c"),
                Chunk(id="o-0", document_id=other.id, sequence=0, text="z"),
            ]
        )
        earlier = datetime(2026, 4, 1, 12, tzinfo=UTC)
        await chunk_repo.soft_delete("c-old", at=earlier)
        at = datetime(2026, 4, 29, 12, tzinfo=UTC)

        hit = await chunk_repo.soft_delete_for_document(doc.id, at=at)

        assert hit == 2
        assert await chunk_repo.find_for_document(doc.id) == []
        live = await chunk_repo.find_by_id("c-0")
        assert live is not None
        assert live.deleted_at == at
        assert live.updated_at == at
        # An already-deleted chunk keeps its original deletion stamp.
        old = await chunk_repo.find_by_id("c-old")
        assert old is not None
        assert old.deleted_at == earlier
        # Another document's chunks are untouched.
        assert [c.id for c in await chunk_repo.find_for_document(other.id)] == ["o-0"]

    async def test_soft_delete_for_document_without_chunks_returns_zero(self, doc, chunk_repo):
        assert await chunk_repo.soft_delete_for_document(doc.id, at=datetime.now(UTC)) == 0

    async def test_shift_sequences_moves_live_chunks_from_the_given_sequence(self, doc, chunk_repo):
        other = Document(id="doc-2", filename="o.pdf", storage_path="/tmp/o.pdf")
        await SqliteDocumentRepository().insert(other)
        await chunk_repo.insert_many(
            [
                Chunk(id="c-0", document_id=doc.id, sequence=0, text="a"),
                Chunk(id="c-1", document_id=doc.id, sequence=1, text="b"),
                Chunk(id="c-2", document_id=doc.id, sequence=2, text="c"),
                Chunk(id="c-gone", document_id=doc.id, sequence=3, text="d"),
                Chunk(id="o-1", document_id=other.id, sequence=1, text="z"),
            ]
        )
        await chunk_repo.soft_delete("c-gone", at=datetime(2026, 4, 1, tzinfo=UTC))
        at = datetime(2026, 4, 29, 12, tzinfo=UTC)

        moved = await chunk_repo.shift_sequences(doc.id, from_sequence=1, at=at)

        assert moved == 2
        out = await chunk_repo.find_for_document(doc.id)
        assert [(c.id, c.sequence) for c in out] == [("c-0", 0), ("c-1", 2), ("c-2", 3)]
        assert [c.updated_at == at for c in out] == [False, True, True]
        gone = await chunk_repo.find_by_id("c-gone")
        assert gone is not None
        assert gone.sequence == 3
        other_chunk = await chunk_repo.find_by_id("o-1")
        assert other_chunk is not None
        assert other_chunk.sequence == 1

    async def test_shift_sequences_by_a_custom_step(self, doc, chunk_repo):
        await chunk_repo.insert(Chunk(id="c-0", document_id=doc.id, sequence=4, text="a"))

        moved = await chunk_repo.shift_sequences(
            doc.id, from_sequence=0, at=datetime.now(UTC), by=3
        )

        assert moved == 1
        out = await chunk_repo.find_by_id("c-0")
        assert out is not None
        assert out.sequence == 7

    async def test_update_persists_text_and_sequence(self, doc, chunk_repo):
        c = Chunk(id="c-1", document_id=doc.id, sequence=0, text="old")
        await chunk_repo.insert(c)

        c.text = "new"
        c.sequence = 5
        c.updated_at = datetime(2026, 4, 29, 12, tzinfo=UTC)
        await chunk_repo.update(c)

        out = await chunk_repo.find_by_id("c-1")
        assert out is not None
        assert out.text == "new"
        assert out.sequence == 5

    async def test_cascade_delete_with_document(self, doc, chunk_repo):
        await chunk_repo.insert(Chunk(id="c-1", document_id=doc.id, sequence=0, text="a"))
        await SqliteDocumentRepository().delete(doc.id)
        out = await chunk_repo.find_for_document(doc.id, include_deleted=True)
        assert out == []


class TestChunkPushRepo:
    async def test_insert_and_find_latest(self, doc, push_repo):
        first = ChunkPush(
            id="p-1",
            document_id=doc.id,
            store_id="default",
            chunkset_hash="hash-old",
            chunk_ids=["c-1", "c-2"],
            pushed_at=datetime(2026, 4, 29, 10, tzinfo=UTC),
        )
        latest = ChunkPush(
            id="p-2",
            document_id=doc.id,
            store_id="default",
            chunkset_hash="hash-new",
            chunk_ids=["c-1", "c-3"],
            pushed_at=datetime(2026, 4, 29, 11, tzinfo=UTC),
        )
        await push_repo.insert(first)
        await push_repo.insert(latest)

        found = await push_repo.find_latest(doc.id, "default")
        assert found is not None
        assert found.id == "p-2"
        assert found.chunkset_hash == "hash-new"
        assert found.chunk_ids == ["c-1", "c-3"]

    async def test_find_latest_returns_none_when_absent(self, doc, push_repo):
        assert await push_repo.find_latest(doc.id, "default") is None
