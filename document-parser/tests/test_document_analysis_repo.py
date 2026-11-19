"""Ownership and lifecycle rules for the document analysis state (02-2.4.3)."""

from __future__ import annotations

import sqlite3

import pytest

from domain.models import (
    AnalysisJob,
    AnalysisStatus,
    Document,
    DocumentAnalysisState,
    DocumentChunkSource,
)
from persistence import database
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository


async def _change(states, document_id: str, change) -> None:
    """Load, change and save a document's state, as the services do."""
    state = await states.find_state(document_id) or DocumentAnalysisState(document_id)
    change(state)
    await states.save_state(state)


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
        await _change(state, "doc-b", lambda s: s.select("analysis-a"))
    await _change(state, "doc-a", lambda s: s.select("analysis-a"))
    await _change(state, "doc-a", lambda s: s.record_chunk_source("analysis-a", "a" * 64))
    assert (await state.find_state("doc-a")).selection.analysis_id == "analysis-a"
    assert (await state.find_state("doc-a")).chunk_source.result_hash == "a" * 64

    await analyses.delete("analysis-a")
    assert (await state.find_state("doc-a")).selection is None
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
    await _change(states, "doc-a", lambda s: s.record_chunk_source("older", "a" * 64))

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

    await _change(state, "doc-a", lambda s: s.record_chunk_source("analysis-a", "a" * 64))
    await _change(state, "doc-a", lambda s: s.select("analysis-a"))
    await _change(state, "doc-a", lambda s: s.clear_selection())
    assert (await state.find_state("doc-a")).selection is None
    assert (await state.find_state("doc-a")).chunk_source == source

    await _change(state, "doc-a", lambda s: s.select("analysis-a"))
    await _change(state, "doc-a", lambda s: s.clear_chunk_source())
    assert (await state.find_state("doc-a")).selection.analysis_id == "analysis-a"
    assert (await state.find_state("doc-a")).chunk_source is None


@pytest.mark.asyncio
async def test_a_save_writes_only_what_changed(tmp_path, monkeypatch):
    """Two writers holding the same loaded state: neither undoes the other."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "partial.db"))
    await database.init_db()
    await SqliteDocumentRepository().insert(Document(id="doc-a", storage_path="/tmp/a.pdf"))
    analyses = SqliteAnalysisRepository()
    for analysis_id in ("analysis-a", "analysis-b"):
        await analyses.insert(
            AnalysisJob(id=analysis_id, document_id="doc-a", status=AnalysisStatus.COMPLETED)
        )
    states = SqliteDocumentAnalysisRepository()
    await _change(states, "doc-a", lambda s: s.select("analysis-a"))

    rechunk_view = await states.find_state("doc-a")
    selection_view = await states.find_state("doc-a")
    selection_view.select("analysis-b")
    await states.save_state(selection_view)
    rechunk_view.record_chunk_source("analysis-a", "a" * 64)
    await states.save_state(rechunk_view)

    state = await states.find_state("doc-a")
    assert state.active_analysis_id == "analysis-b"
    assert state.chunk_source == DocumentChunkSource("doc-a", "analysis-a", "a" * 64)


@pytest.mark.asyncio
async def test_clearing_never_creates_a_state_row(tmp_path, monkeypatch):
    """A missing row and a NULL selection mean different things (#391)."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "no-row.db"))
    await database.init_db()
    await SqliteDocumentRepository().insert(Document(id="doc-a", storage_path="/tmp/a.pdf"))
    states = SqliteDocumentAnalysisRepository()

    await _change(states, "doc-a", lambda s: s.clear_selection())
    await _change(states, "doc-a", lambda s: s.clear_chunk_source())

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
    await _change(states, "doc-a", lambda s: s.select("analysis-a"))
    await _change(states, "doc-b", lambda s: s.record_chunk_source("gone", "b" * 64))

    found = await states.find_states(["doc-a", "doc-b", "doc-c"])

    assert set(found) == {"doc-a", "doc-b"}
    assert found["doc-a"].active_analysis_id == "analysis-a"
    assert found["doc-b"].active_analysis_id is None
    assert await states.find_states([]) == {}


def test_chunks_are_stale_against_another_result_or_without_a_source():
    state = DocumentAnalysisState("doc-a")
    assert state.are_chunks_stale("analysis-a", "a" * 64, has_chunks=True)
    assert not state.are_chunks_stale("analysis-a", "a" * 64, has_chunks=False)

    state.record_chunk_source("analysis-a", "a" * 64)
    assert not state.are_chunks_stale("analysis-a", "a" * 64, has_chunks=True)
    assert state.are_chunks_stale("analysis-a", "b" * 64, has_chunks=True)
    assert state.are_chunks_stale("analysis-b", "a" * 64, has_chunks=True)
