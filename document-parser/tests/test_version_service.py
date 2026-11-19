"""Unit tests for VersionService (#267) — frozen (analysis, chunks) pairs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from domain.models import (
    AnalysisJob,
    AnalysisStatus,
    Chunk,
    Document,
    DocumentAnalysisState,
    DocumentVersionKind,
)
from domain.value_objects import ChunkBbox, ChunkDocItem
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
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
        "analyses": SqliteAnalysisRepository(),
        "analysis_state": SqliteDocumentAnalysisRepository(),
        "chunks": SqliteChunkRepository(),
        "versions": SqliteDocumentVersionRepository(),
    }


@pytest.fixture
def service(repos):
    return VersionService(
        version_repo=repos["versions"],
        chunk_repo=repos["chunks"],
        document_repo=repos["documents"],
        analysis_repo=repos["analyses"],
        analysis_state_repo=repos["analysis_state"],
    )


@pytest.fixture
async def doc(repos):
    d = Document(id="doc-1", filename="a.pdf", storage_path="/tmp/a")
    await repos["documents"].insert(d)
    return d


async def _change_state(repos, document_id: str, change) -> None:
    states = repos["analysis_state"]
    state = await states.find_state(document_id) or DocumentAnalysisState(document_id)
    change(state)
    await states.save_state(state)


class TestRecordOnAnalysis:
    async def test_first_version_has_empty_chunks_snapshot(self, service, doc):
        version = await service.record_on_analysis(doc.id, "a1")
        assert version.kind is DocumentVersionKind.ANALYSIS
        assert version.analysis_id == "a1"
        assert json.loads(version.chunks_snapshot or "[]") == []

    async def test_snapshot_carries_existing_chunks(self, service, repos, doc):
        await _change_state(repos, doc.id, lambda s: s.record_chunk_source("old", "a" * 64))
        await repos["analyses"].insert(
            AnalysisJob(id="a2", document_id=doc.id, status=AnalysisStatus.COMPLETED)
        )
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
        assert version.analysis_id == "a2"
        assert version.chunks_source_analysis_id == "old"
        assert version.chunks_source_result_hash == "a" * 64
        await service.restore(doc.id, version.id)
        state = await repos["analysis_state"].find_state(doc.id)
        assert state.active_analysis_id == "a2"
        assert state.chunk_source.analysis_id == "old"


class TestRecordOnRechunk:
    async def test_records_kind_chunks(self, service, repos, doc):
        await repos["chunks"].insert_many([Chunk(document_id=doc.id, sequence=0, text="new")])
        version = await service.record_on_rechunk(doc.id, "a1", "a" * 64)
        assert version.kind is DocumentVersionKind.CHUNKS
        assert version.analysis_id == "a1"
        assert json.loads(version.chunks_snapshot)[0]["text"] == "new"


class TestRestore:
    async def test_restore_overwrites_live_chunks(self, service, repos, doc):
        await repos["analyses"].insert(
            AnalysisJob(id="a1", document_id=doc.id, status=AnalysisStatus.COMPLETED)
        )
        # V1 — two chunks
        await repos["chunks"].insert_many(
            [
                Chunk(document_id=doc.id, sequence=0, text="v1-a"),
                Chunk(document_id=doc.id, sequence=1, text="v1-b"),
            ]
        )
        v1 = await service.record_on_rechunk(doc.id, "a1", "a" * 64)

        # Move to V2 state — soft-delete V1's chunks, insert a single new
        await repos["chunks"].soft_delete_for_document(doc.id, at=datetime.now(UTC))
        await repos["chunks"].insert_many([Chunk(document_id=doc.id, sequence=0, text="v2-only")])
        await service.record_on_rechunk(doc.id, "a1", "b" * 64)

        # Restore V1 → live should match V1's two chunks
        await service.restore(doc.id, v1.id)
        live = await repos["chunks"].find_for_document(doc.id)
        assert sorted(c.text for c in live) == ["v1-a", "v1-b"]
        state = await repos["analysis_state"].find_state(doc.id)
        assert state.active_analysis_id == "a1"
        assert state.chunk_source.result_hash == "a" * 64

    async def test_restores_analysis_selection_and_chunk_provenance(self, service, repos, doc):
        await repos["analyses"].insert(
            AnalysisJob(id="a1", document_id=doc.id, status=AnalysisStatus.COMPLETED)
        )
        await _change_state(repos, doc.id, lambda s: s.select("a1"))
        version = await service.record_on_rechunk(doc.id, "a1", "c" * 64)
        await service.restore(doc.id, version.id)
        state = await repos["analysis_state"].find_state(doc.id)
        assert state.active_analysis_id == "a1"
        assert state.chunk_source.analysis_id == "a1"
        assert state.chunk_source.result_hash == "c" * 64

    async def test_restore_of_the_older_analysis_makes_it_current(self, service, repos, doc):
        """02-2.3.1: two completed analyses, the user restores the older one."""
        for analysis_id in ("a1", "a2"):
            job = AnalysisJob(id=analysis_id, document_id=doc.id)
            await repos["analyses"].insert(job)
            job.mark_running()
            job.mark_completed(markdown="", html="", pages_json="[]", document_json="{}")
            await repos["analyses"].complete_and_select(job)
        older = await service.record_on_rechunk(doc.id, "a1", "e" * 64)
        assert (await repos["analysis_state"].find_state(doc.id)).active_analysis_id == "a2"

        await service.restore(doc.id, older.id)

        assert (await repos["analysis_state"].find_state(doc.id)).active_analysis_id == "a1"

    async def test_restore_replaces_live_chunks_in_one_transaction(
        self, service, repos, doc, monkeypatch
    ):
        """#398 — one bulk UPDATE, not one soft-delete per live chunk; 02-2.4.3 —
        the chunks and the analysis state are written by one repository call."""
        await repos["analyses"].insert(
            AnalysisJob(id="a1", document_id=doc.id, status=AnalysisStatus.COMPLETED)
        )
        await repos["chunks"].insert_many(
            [Chunk(document_id=doc.id, sequence=i, text=f"live-{i}") for i in range(3)]
        )
        version = await service.record_on_rechunk(doc.id, "a1", "d" * 64)
        chunk_repo = repos["chunks"]
        replace = AsyncMock(wraps=chunk_repo.replace_for_document)
        single = AsyncMock(wraps=chunk_repo.soft_delete)
        monkeypatch.setattr(chunk_repo, "replace_for_document", replace)
        monkeypatch.setattr(chunk_repo, "soft_delete", single)

        await service.restore(doc.id, version.id)

        replace.assert_awaited_once()
        assert replace.await_args.args[0] == doc.id
        single.assert_not_awaited()
        live = await chunk_repo.find_for_document(doc.id)
        assert sorted(c.text for c in live) == ["live-0", "live-1", "live-2"]
        every = await chunk_repo.find_for_document(doc.id, include_deleted=True)
        assert sum(c.deleted_at is not None for c in every) == 3

    async def test_a_failed_state_write_rolls_the_chunks_back(
        self, service, repos, doc, monkeypatch
    ):
        """02-2.4.3: restored chunks never stand recorded against the old analysis."""
        await repos["analyses"].insert(
            AnalysisJob(id="a1", document_id=doc.id, status=AnalysisStatus.COMPLETED)
        )
        await repos["chunks"].insert_many([Chunk(document_id=doc.id, sequence=0, text="before")])
        version = await service.record_on_rechunk(doc.id, "a1", "f" * 64)
        await repos["chunks"].soft_delete_for_document(doc.id, at=datetime.now(UTC))
        await repos["chunks"].insert_many([Chunk(document_id=doc.id, sequence=0, text="after")])

        async def fail(db, state):
            raise RuntimeError("state write failed")

        monkeypatch.setattr("persistence.chunk_repo.write_document_analysis_state", fail)
        with pytest.raises(RuntimeError, match="state write failed"):
            await service.restore(doc.id, version.id)

        live = await repos["chunks"].find_for_document(doc.id)
        assert [c.text for c in live] == ["after"]
        assert await repos["analysis_state"].find_state(doc.id) is None

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
        await service.record_on_rechunk(doc.id, "a1", "a" * 64)
        await service.record_on_analysis(doc.id, "a2")
        versions = await service.list_for_document(doc.id)
        # 3 entries, newest first (analysis a2 wins)
        assert len(versions) == 3
        assert versions[0].kind is DocumentVersionKind.ANALYSIS
        assert versions[0].analysis_id == "a2"

    async def test_unknown_doc_raises(self, service):
        with pytest.raises(VersionServiceError):
            await service.list_for_document("nope")
