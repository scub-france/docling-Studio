"""Ownership and lifecycle rules for the document analysis connection."""

from __future__ import annotations

import sqlite3

import pytest

from domain.models import (
    AnalysisJob,
    AnalysisStatus,
    Document,
    DocumentAnalysisSelection,
    DocumentChunkSource,
)
from persistence import database
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository


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
        await state.select(DocumentAnalysisSelection("doc-b", "analysis-a"))
    await state.select(DocumentAnalysisSelection("doc-a", "analysis-a"))
    await state.set_chunk_source(DocumentChunkSource("doc-a", "analysis-a", "a" * 64))
    assert (await state.get_selection("doc-a")).analysis_id == "analysis-a"
    assert (await state.get_chunk_source("doc-a")).result_hash == "a" * 64

    await analyses.delete("analysis-a")
    assert await state.get_selection("doc-a") is None
    assert (await state.get_chunk_source("doc-a")).result_hash == "a" * 64


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
        await analyses.update_status(invalid, select_analysis=True)
    assert (await analyses.find_by_id("analysis-a")).status == AnalysisStatus.PENDING

    valid = AnalysisJob(id="analysis-a", document_id="doc-a", status=AnalysisStatus.COMPLETED)
    await analyses.update_status(valid, select_analysis=True)
    assert (await analyses.find_by_id("analysis-a")).status == AnalysisStatus.COMPLETED
    assert (
        await SqliteDocumentAnalysisRepository().get_selection("doc-a")
    ).analysis_id == "analysis-a"


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

    await state.set_chunk_source(source)
    await state.select(DocumentAnalysisSelection("doc-a", "analysis-a"))
    await state.clear_selection("doc-a")
    assert await state.get_selection("doc-a") is None
    assert await state.get_chunk_source("doc-a") == source

    await state.select(DocumentAnalysisSelection("doc-a", "analysis-a"))
    await state.clear_chunk_source("doc-a")
    assert (await state.get_selection("doc-a")).analysis_id == "analysis-a"
    assert await state.get_chunk_source("doc-a") is None
