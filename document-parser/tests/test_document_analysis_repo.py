"""Ownership and lifecycle rules for the document analysis state (02-2.4.3)."""

from __future__ import annotations

import sqlite3

import pytest

from domain.exceptions import AnalysisNotSelectableError
from domain.models import (
    AnalysisJob,
    AnalysisStatus,
    Chunk,
    Document,
    DocumentAnalysisState,
    DocumentChunkSource,
    get_utc_now,
)
from persistence import database
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository
from tests.analysis_state_helpers import set_chunk_source, set_selection


@pytest.mark.asyncio
async def test_selection_requires_analysis_owned_by_document_and_chunk_source_survives_delete(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "selection.db"))
    await database.init_db()
    documents = SqliteDocumentRepository()
    analyses = SqliteAnalysisRepository()
    state = SqliteDocumentAnalysisRepository()
    for document_id in ("doc-a", "doc-b"):
        await documents.insert(Document(id=document_id, storage_path=f"/tmp/{document_id}.pdf"))
    await analyses.insert(
        AnalysisJob(id="analysis-a", document_id="doc-a", status=AnalysisStatus.COMPLETED)
    )

    with pytest.raises(sqlite3.IntegrityError):
        await set_selection("doc-b", "analysis-a")
    await set_selection("doc-a", "analysis-a")
    await set_chunk_source("doc-a", "analysis-a", "a" * 64)
    assert (await state.find_state("doc-a")).active_analysis_id == "analysis-a"
    assert (await state.find_state("doc-a")).chunk_source.result_hash == "a" * 64

    await analyses.delete("analysis-a")
    assert (await state.find_state("doc-a")).active_analysis_id is None
    assert (await state.find_state("doc-a")).chunk_source.result_hash == "a" * 64


@pytest.mark.asyncio
async def test_completion_and_selection_roll_back_together(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "completion.db"))
    await database.init_db()
    documents = SqliteDocumentRepository()
    analyses = SqliteAnalysisRepository()
    for document_id in ("doc-a", "doc-b"):
        await documents.insert(Document(id=document_id, storage_path=f"/tmp/{document_id}.pdf"))
    await analyses.insert(AnalysisJob(id="analysis-a", document_id="doc-a"))

    # A stale or incorrect owner cannot commit a completed job without its selection.
    invalid = AnalysisJob(id="analysis-a", document_id="doc-b", status=AnalysisStatus.COMPLETED)
    with pytest.raises(sqlite3.IntegrityError):
        await analyses.complete_and_select(invalid)
    assert (await analyses.find_by_id("analysis-a")).status == AnalysisStatus.PENDING

    valid = AnalysisJob(id="analysis-a", document_id="doc-a", status=AnalysisStatus.COMPLETED)
    await analyses.complete_and_select(valid)
    assert (await analyses.find_by_id("analysis-a")).status == AnalysisStatus.COMPLETED
    assert (
        await SqliteDocumentAnalysisRepository().find_state("doc-a")
    ).active_analysis_id == "analysis-a"


@pytest.mark.asyncio
async def test_completion_keeps_the_chunk_source(tmp_path, monkeypatch):
    """`complete_and_select` writes the selection only, as before 02-2.4.3."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "completion-source.db"))
    await database.init_db()
    await SqliteDocumentRepository().insert(Document(id="doc-a", storage_path="/tmp/a.pdf"))
    analyses = SqliteAnalysisRepository()
    states = SqliteDocumentAnalysisRepository()
    await analyses.insert(AnalysisJob(id="analysis-a", document_id="doc-a"))
    await set_chunk_source("doc-a", "older", "a" * 64)

    job = AnalysisJob(id="analysis-a", document_id="doc-a", status=AnalysisStatus.COMPLETED)
    await analyses.complete_and_select(job)

    state = await states.find_state("doc-a")
    assert state.active_analysis_id == "analysis-a"
    assert state.chunk_source == DocumentChunkSource("doc-a", "older", "a" * 64)


@pytest.mark.asyncio
async def test_clearing_either_state_keeps_the_other(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "state.db"))
    await database.init_db()
    await SqliteDocumentRepository().insert(Document(id="doc-a", storage_path="/tmp/a.pdf"))
    await SqliteAnalysisRepository().insert(
        AnalysisJob(id="analysis-a", document_id="doc-a", status=AnalysisStatus.COMPLETED)
    )
    state = SqliteDocumentAnalysisRepository()
    source = DocumentChunkSource("doc-a", "analysis-a", "a" * 64)

    await set_chunk_source("doc-a", "analysis-a", "a" * 64)
    await set_selection("doc-a", "analysis-a")
    await set_selection("doc-a", None)
    assert (await state.find_state("doc-a")).active_analysis_id is None
    assert (await state.find_state("doc-a")).chunk_source == source

    await set_selection("doc-a", "analysis-a")
    await set_chunk_source("doc-a", None)
    assert (await state.find_state("doc-a")).active_analysis_id == "analysis-a"
    assert (await state.find_state("doc-a")).chunk_source is None


@pytest.mark.asyncio
async def test_a_rechunk_keeps_a_selection_made_meanwhile(tmp_path, monkeypatch):
    """A rechunk writes the chunk source only: a selection made since it read
    the state stands, and its chunks report stale against it."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "partial.db"))
    await database.init_db()
    await SqliteDocumentRepository().insert(Document(id="doc-a", storage_path="/tmp/a.pdf"))
    analyses = SqliteAnalysisRepository()
    for analysis_id in ("analysis-a", "analysis-b"):
        await analyses.insert(
            AnalysisJob(id=analysis_id, document_id="doc-a", status=AnalysisStatus.COMPLETED)
        )
    states = SqliteDocumentAnalysisRepository()
    await set_selection("doc-a", "analysis-a")

    # The rechunk read analysis-a as current; analysis-b is selected meanwhile.
    await set_selection("doc-a", "analysis-b")
    await SqliteChunkRepository().replace_for_document(
        "doc-a",
        [Chunk(document_id="doc-a", sequence=0, text="t")],
        at=get_utc_now(),
        chunk_source=DocumentChunkSource("doc-a", "analysis-a", "a" * 64),
        active_analysis_id="analysis-a",
        keep_selection=True,
    )

    state = await states.find_state("doc-a")
    assert state.active_analysis_id == "analysis-b"
    assert state.chunk_source == DocumentChunkSource("doc-a", "analysis-a", "a" * 64)


@pytest.mark.asyncio
async def test_a_restore_selecting_a_deleted_analysis_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "gone.db"))
    await database.init_db()
    await SqliteDocumentRepository().insert(Document(id="doc-a", storage_path="/tmp/a.pdf"))
    chunks = SqliteChunkRepository()
    await chunks.insert(Chunk(document_id="doc-a", sequence=0, text="live"))

    with pytest.raises(AnalysisNotSelectableError):
        await chunks.replace_for_document(
            "doc-a",
            [Chunk(document_id="doc-a", sequence=0, text="restored")],
            at=get_utc_now(),
            chunk_source=None,
            active_analysis_id="deleted-analysis",
        )

    assert [c.text for c in await chunks.find_for_document("doc-a")] == ["live"]
    assert await SqliteDocumentAnalysisRepository().find_state("doc-a") is None


@pytest.mark.asyncio
async def test_clearing_never_creates_a_state_row(tmp_path, monkeypatch):
    """A missing row and a NULL selection mean different things (#391)."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "no-row.db"))
    await database.init_db()
    await SqliteDocumentRepository().insert(Document(id="doc-a", storage_path="/tmp/a.pdf"))
    states = SqliteDocumentAnalysisRepository()

    await set_selection("doc-a", None)
    await set_chunk_source("doc-a", None)

    assert await states.find_state("doc-a") is None
    assert await states.find_states(["doc-a", "missing"]) == {}


@pytest.mark.asyncio
async def test_find_states_reads_many_documents_at_once(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "many.db"))
    await database.init_db()
    documents = SqliteDocumentRepository()
    analyses = SqliteAnalysisRepository()
    states = SqliteDocumentAnalysisRepository()
    for document_id in ("doc-a", "doc-b", "doc-c"):
        await documents.insert(Document(id=document_id, storage_path=f"/tmp/{document_id}.pdf"))
    await analyses.insert(
        AnalysisJob(id="analysis-a", document_id="doc-a", status=AnalysisStatus.COMPLETED)
    )
    await set_selection("doc-a", "analysis-a")
    await set_chunk_source("doc-b", "gone", "b" * 64)

    found = await states.find_states(["doc-a", "doc-b", "doc-c"])

    assert set(found) == {"doc-a", "doc-b"}
    assert found["doc-a"].active_analysis_id == "analysis-a"
    assert found["doc-b"].active_analysis_id is None
    assert await states.find_states([]) == {}


def test_chunks_are_stale_against_another_result_or_without_a_source():
    state = DocumentAnalysisState("doc-a")
    assert state.are_chunks_stale("analysis-a", "a" * 64, has_chunks=True)
    assert not state.are_chunks_stale("analysis-a", "a" * 64, has_chunks=False)

    state = DocumentAnalysisState(
        "doc-a", chunk_source=DocumentChunkSource("doc-a", "analysis-a", "a" * 64)
    )
    assert not state.are_chunks_stale("analysis-a", "a" * 64, has_chunks=True)
    assert state.are_chunks_stale("analysis-a", "b" * 64, has_chunks=True)
    assert state.are_chunks_stale("analysis-b", "a" * 64, has_chunks=True)
