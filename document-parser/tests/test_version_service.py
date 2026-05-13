"""Unit tests for VersionService (#267) — frozen (analysis, chunks) pairs."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from domain.models import Chunk, Document, DocumentVersionKind
from domain.value_objects import ChunkBbox, ChunkDocItem
from persistence.chunk_edit_repo import SqliteChunkEditRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository
from services.version_service import (
    VersionNotFoundError,
    VersionService,
    VersionServiceError,
)


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()
    yield


@pytest.fixture
def repos():
    return {
        "documents": SqliteDocumentRepository(),
        "chunks": SqliteChunkRepository(),
        "chunk_edits": SqliteChunkEditRepository(),
        "versions": SqliteDocumentVersionRepository(),
    }


@pytest.fixture
def service(repos):
    return VersionService(
        version_repo=repos["versions"],
        chunk_repo=repos["chunks"],
        chunk_edit_repo=repos["chunk_edits"],
        document_repo=repos["documents"],
    )


@pytest.fixture
async def doc(repos):
    d = Document(id="doc-1", filename="a.pdf", storage_path="/tmp/a")
    await repos["documents"].insert(d)
    return d


class TestRecordOnAnalysis:
    async def test_first_version_has_empty_chunks_snapshot(self, service, doc):
        version = await service.record_on_analysis(doc.id, "a1")
        assert version.kind is DocumentVersionKind.ANALYSIS
        assert version.analysis_id == "a1"
        assert json.loads(version.chunks_snapshot or "[]") == []

    async def test_snapshot_carries_existing_chunks(self, service, repos, doc):
        await repos["chunks"].insert_many(
            [
                Chunk(
                    document_id=doc.id,
                    sequence=0,
                    text="t1",
                    headings=["h"],
                    source_page=1,
                    bboxes=[ChunkBbox(page=1, bbox=[0, 0, 10, 10])],
                    doc_items=[ChunkDocItem(self_ref="#/texts/0", label="text")],
                    token_count=5,
                ),
                Chunk(document_id=doc.id, sequence=1, text="t2", token_count=4),
            ]
        )
        version = await service.record_on_analysis(doc.id, "a2")
        snapshot = json.loads(version.chunks_snapshot)
        assert [s["text"] for s in snapshot] == ["t1", "t2"]
        assert snapshot[0]["docItems"][0]["selfRef"] == "#/texts/0"


class TestRecordOnRechunk:
    async def test_records_kind_chunks(self, service, repos, doc):
        await repos["chunks"].insert_many([Chunk(document_id=doc.id, sequence=0, text="new")])
        version = await service.record_on_rechunk(doc.id, "a1")
        assert version.kind is DocumentVersionKind.CHUNKS
        assert version.analysis_id == "a1"
        assert json.loads(version.chunks_snapshot)[0]["text"] == "new"


class TestRestore:
    async def test_restore_overwrites_live_chunks(self, service, repos, doc):
        # V1 — two chunks
        await repos["chunks"].insert_many(
            [
                Chunk(document_id=doc.id, sequence=0, text="v1-a"),
                Chunk(document_id=doc.id, sequence=1, text="v1-b"),
            ]
        )
        v1 = await service.record_on_rechunk(doc.id, "a1")

        # Move to V2 state — soft-delete V1's chunks, insert a single new
        now = datetime.now(UTC)
        for c in await repos["chunks"].find_for_document(doc.id):
            await repos["chunks"].soft_delete(c.id, at=now)
        await repos["chunks"].insert_many([Chunk(document_id=doc.id, sequence=0, text="v2-only")])
        await service.record_on_rechunk(doc.id, "a1")

        # Restore V1 → live should match V1's two chunks
        await service.restore(doc.id, v1.id)
        live = await repos["chunks"].find_for_document(doc.id)
        assert sorted(c.text for c in live) == ["v1-a", "v1-b"]

    async def test_restore_unknown_version_raises(self, service, doc):
        with pytest.raises(VersionNotFoundError):
            await service.restore(doc.id, "nope")

    async def test_restore_other_doc_version_raises(self, service, repos, doc):
        other = Document(id="doc-2", filename="b.pdf", storage_path="/tmp/b")
        await repos["documents"].insert(other)
        v = await service.record_on_analysis(other.id, "a1")
        with pytest.raises(VersionNotFoundError):
            await service.restore(doc.id, v.id)


class TestListForDocument:
    async def test_returns_newest_first(self, service, doc):
        await service.record_on_analysis(doc.id, "a1")
        await service.record_on_rechunk(doc.id, "a1")
        await service.record_on_analysis(doc.id, "a2")
        versions = await service.list_for_document(doc.id)
        # 3 entries, newest first (analysis a2 wins)
        assert len(versions) == 3
        assert versions[0].kind is DocumentVersionKind.ANALYSIS
        assert versions[0].analysis_id == "a2"

    async def test_unknown_doc_raises(self, service):
        with pytest.raises(VersionServiceError):
            await service.list_for_document("nope")
