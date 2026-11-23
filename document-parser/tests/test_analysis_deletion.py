"""Deleting an analysis keeps the document on a current analysis while one remains."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.analyses import router as analyses_router
from api.documents import router as documents_router
from api.state import AppState, get_app_state
from domain.models import AnalysisJob, AnalysisStatus, Document, DocumentAnalysisState
from persistence import database
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.store_repo import SqliteStoreRepository
from services.analysis_service import AnalysisService
from services.current_analysis import CurrentAnalysisResolver
from services.document_service import DocumentConfig, DocumentService
from tests.analysis_state_helpers import set_chunk_source, set_selection

_T0 = datetime(2026, 11, 1, tzinfo=UTC)


async def _seed_analysis(
    analysis_id: str,
    *,
    minutes: int,
    document_id: str = "doc-1",
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    parsed: bool = True,
) -> None:
    analyses = SqliteAnalysisRepository()
    job = AnalysisJob(id=analysis_id, document_id=document_id, status=status)
    await analyses.insert(job)
    job.document_json = '{"v": 1}' if parsed else None
    job.completed_at = (
        _T0 + timedelta(minutes=minutes) if status is AnalysisStatus.COMPLETED else None
    )
    await analyses.update_status(job)


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "deletion.db"))
    await database.init_db()
    documents = SqliteDocumentRepository()
    for document_id in ("doc-1", "doc-2"):
        await documents.insert(Document(id=document_id, filename="a.pdf", storage_path="/tmp/a"))


async def _active(document_id: str = "doc-1") -> str | None:
    state = await SqliteDocumentAnalysisRepository().find_state(document_id)
    return state.active_analysis_id if state else None


@pytest.mark.usefixtures("db")
class TestRepositoryDelete:
    async def test_deleting_the_active_analysis_selects_the_latest_parsed_one(self):
        await _seed_analysis("oldest", minutes=1)
        await _seed_analysis("older", minutes=2)
        # Newer than `older`, but neither can be current with a parse.
        await _seed_analysis("no-parse", minutes=3, parsed=False)
        await _seed_analysis("running", minutes=4, status=AnalysisStatus.RUNNING)
        await _seed_analysis("other-doc", minutes=5, document_id="doc-2")
        await _seed_analysis("active", minutes=6)
        await set_selection("doc-1", "active")

        assert await SqliteAnalysisRepository().delete("active")

        assert await _active() == "older"

    async def test_deleting_the_last_usable_analysis_leaves_no_selection(self):
        await _seed_analysis("no-parse", minutes=1, parsed=False)
        await _seed_analysis("active", minutes=2)
        await set_selection("doc-1", "active")

        await SqliteAnalysisRepository().delete("active")

        state = await SqliteDocumentAnalysisRepository().find_state("doc-1")
        assert state is not None
        assert state.active_analysis_id is None

    async def test_deleting_another_analysis_keeps_the_selection(self):
        await _seed_analysis("older", minutes=1)
        await _seed_analysis("newer", minutes=2)
        await set_selection("doc-1", "older")

        await SqliteAnalysisRepository().delete("newer")

        assert await _active() == "older"

    async def test_a_cleared_selection_stays_cleared(self):
        await _seed_analysis("kept", minutes=1)
        await _seed_analysis("deleted", minutes=2)
        await set_selection("doc-1", "kept")
        await set_selection("doc-1", None)

        await SqliteAnalysisRepository().delete("deleted")

        assert await _active() is None

    async def test_the_chunk_source_is_kept(self):
        await _seed_analysis("older", minutes=1)
        await _seed_analysis("active", minutes=2)
        await set_selection("doc-1", "active")
        await set_chunk_source("doc-1", "active", "a" * 64)

        await SqliteAnalysisRepository().delete("active")

        state = await SqliteDocumentAnalysisRepository().find_state("doc-1")
        assert state.active_analysis_id == "older"
        assert state.chunk_source.analysis_id == "active"

    async def test_deleting_an_unknown_analysis_changes_nothing(self):
        await _seed_analysis("active", minutes=1)
        await set_selection("doc-1", "active")

        assert not await SqliteAnalysisRepository().delete("missing")

        assert await _active() == "active"


def test_the_successor_rule_lives_on_the_aggregate():
    state = DocumentAnalysisState("doc-1", "active")
    assert state.resolve_selection_after_deleting("active", "older") == "older"
    assert state.resolve_selection_after_deleting("active", None) is None
    assert state.resolve_selection_after_deleting("other", "older") == "active"
    assert DocumentAnalysisState("doc-1").resolve_selection_after_deleting("x", "older") is None


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "deletion-api.db"))

    async def seed() -> None:
        await database.init_db()
        await SqliteDocumentRepository().insert(
            Document(id="doc-1", filename="a.pdf", storage_path="/tmp/a")
        )
        await _seed_analysis("older", minutes=1)
        await _seed_analysis("active", minutes=2)
        await set_selection("doc-1", "active")

    asyncio.run(seed())
    documents = SqliteDocumentRepository()
    analyses = SqliteAnalysisRepository()
    current = CurrentAnalysisResolver(
        state_repo=SqliteDocumentAnalysisRepository(), analysis_repo=analyses
    )
    app = FastAPI()
    app.include_router(analyses_router)
    app.include_router(documents_router)
    state = AppState(
        analysis_service=AnalysisService(MagicMock(), analyses, documents),
        document_service=DocumentService(
            documents,
            analyses,
            DocumentConfig(),
            link_repo=SqliteDocumentStoreLinkRepository(),
            store_repo=SqliteStoreRepository(),
            pdf_inspector=MagicMock(),
            file_store=MagicMock(),
        ),
        current_analysis=current,
    )
    app.dependency_overrides[get_app_state] = lambda: state
    with TestClient(app) as test_client:
        yield test_client


def test_deleting_the_active_analysis_through_the_api_hands_over_the_selection(client):
    assert client.get("/api/documents/doc-1").json()["currentAnalysisId"] == "active"

    response = client.delete("/api/analyses/active")

    assert response.status_code == 204
    assert client.get("/api/documents/doc-1").json()["currentAnalysisId"] == "older"
