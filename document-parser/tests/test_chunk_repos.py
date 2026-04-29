"""Tests for the chunk / chunk_edit / chunk_push repositories (#205)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.models import Chunk, ChunkEdit, ChunkPush, Document
from domain.value_objects import ChunkBbox, ChunkEditAction
from persistence.chunk_edit_repo import (
    SqliteChunkEditRepository,
    SqliteChunkPushRepository,
)
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
def edit_repo():
    return SqliteChunkEditRepository()


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


class TestChunkEditRepo:
    async def test_insert_and_history(self, doc, edit_repo):
        edit = ChunkEdit(
            id="e-1",
            document_id=doc.id,
            chunk_id="c-1",
            action=ChunkEditAction.UPDATE,
            actor="user@example",
            at=datetime(2026, 4, 29, 12, tzinfo=UTC),
            before={"text": "old"},
            after={"text": "new"},
            reason="typo",
        )
        await edit_repo.insert(edit)

        out = await edit_repo.find_for_document(doc.id)
        assert len(out) == 1
        assert out[0].action == ChunkEditAction.UPDATE
        assert out[0].before == {"text": "old"}
        assert out[0].after == {"text": "new"}
        assert out[0].reason == "typo"

    async def test_history_orders_newest_first(self, doc, edit_repo):
        for i in range(3):
            await edit_repo.insert(
                ChunkEdit(
                    id=f"e-{i}",
                    document_id=doc.id,
                    chunk_id=f"c-{i}",
                    action=ChunkEditAction.INSERT,
                    actor="system",
                    at=datetime(2026, 4, 29, 12 + i, tzinfo=UTC),
                )
            )
        out = await edit_repo.find_for_document(doc.id)
        ids = [e.id for e in out]
        assert ids == ["e-2", "e-1", "e-0"]

    async def test_find_for_chunk_filters(self, doc, edit_repo):
        for i in range(3):
            await edit_repo.insert(
                ChunkEdit(
                    id=f"e-{i}",
                    document_id=doc.id,
                    chunk_id="c-target" if i == 1 else f"c-{i}",
                    action=ChunkEditAction.UPDATE,
                    actor="system",
                    at=datetime(2026, 4, 29, 12 + i, tzinfo=UTC),
                )
            )
        out = await edit_repo.find_for_chunk("c-target")
        assert [e.id for e in out] == ["e-1"]

    async def test_lineage_round_trips(self, doc, edit_repo):
        edit = ChunkEdit(
            id="e-merge",
            document_id=doc.id,
            chunk_id="c-merged",
            action=ChunkEditAction.MERGE,
            actor="system",
            at=datetime(2026, 4, 29, 12, tzinfo=UTC),
            parents=["c-1", "c-2"],
            children=["c-merged"],
        )
        await edit_repo.insert(edit)
        out = await edit_repo.find_for_document(doc.id)
        assert out[0].parents == ["c-1", "c-2"]
        assert out[0].children == ["c-merged"]


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
