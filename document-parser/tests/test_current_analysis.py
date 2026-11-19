"""One definition of "the document's current analysis" (02-2.3.1).

`resolve_current_analysis_id` is the rule; `CurrentAnalysisResolver` feeds it
from SQLite. The situations below are the ones the editor, chunking, exports,
Ask and the MCP tools used to answer differently.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.documents import router
from api.state import AppState, get_app_state
from domain.models import (
    AnalysisJob,
    AnalysisStatus,
    Document,
    DocumentAnalysisState,
    resolve_current_analysis_id,
)
from persistence import database
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from services.current_analysis import CurrentAnalysisResolver
from services.document_service import DocumentConfig, DocumentService
from services.export_service import ExportFormat, ExportService

# --- The rule ---------------------------------------------------------------


def test_the_active_selection_is_the_current_analysis():
    state = DocumentAnalysisState("doc-1", "older")
    assert resolve_current_analysis_id(state, "newer") == "older"


def test_a_row_without_selection_has_no_current_analysis():
    assert resolve_current_analysis_id(DocumentAnalysisState("doc-1"), "newer") is None


def test_only_a_document_without_a_state_row_falls_back_to_the_latest_parse():
    assert resolve_current_analysis_id(None, "newer") == "newer"
    assert resolve_current_analysis_id(None, None) is None


# --- The resolver on SQLite -------------------------------------------------


@pytest.fixture
async def repos(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "current.db"))
    await database.init_db()
    documents = SqliteDocumentRepository()
    for doc_id in ("doc-1", "doc-2", "doc-3"):
        await documents.insert(
            Document(id=doc_id, filename=f"{doc_id}.pdf", storage_path=f"/tmp/{doc_id}.pdf")
        )
    analyses = SqliteAnalysisRepository()
    states = SqliteDocumentAnalysisRepository()
    return {
        "documents": documents,
        "analyses": analyses,
        "states": states,
        "current": CurrentAnalysisResolver(state_repo=states, analysis_repo=analyses),
    }


async def _complete(repos, analysis_id: str, doc_id: str = "doc-1", *, parsed: bool = True):
    """Run an analysis to completion the way `AnalysisService` does: it becomes active."""
    job = AnalysisJob(id=analysis_id, document_id=doc_id)
    await repos["analyses"].insert(job)
    job.mark_running()
    job.mark_completed(
        markdown=f"# {analysis_id}",
        html="",
        pages_json="[]",
        document_json=f'{{"v": "{analysis_id}"}}' if parsed else None,
    )
    await repos["analyses"].complete_and_select(job)


async def _restore(repos, analysis_id: str | None, doc_id: str = "doc-1") -> None:
    state = await repos["states"].find_state(doc_id) or DocumentAnalysisState(doc_id)
    if analysis_id is None:
        state.clear_selection()
    else:
        state.select(analysis_id)
    await repos["states"].save_state(state)


async def test_one_analysis(repos):
    await _complete(repos, "a1")
    assert await repos["current"].find_current_analysis_id("doc-1") == "a1"
    assert (await repos["current"].load_current_analysis("doc-1")).content_markdown == "# a1"


async def test_two_analyses_with_the_older_one_restored(repos):
    await _complete(repos, "older")
    await _complete(repos, "newer")
    await _restore(repos, "older")
    assert await repos["current"].find_current_analysis_id("doc-1") == "older"
    assert (await repos["current"].load_current_analysis("doc-1")).id == "older"


async def test_a_newer_analysis_still_running(repos):
    await _complete(repos, "done")
    await repos["analyses"].insert(
        AnalysisJob(id="running", document_id="doc-1", status=AnalysisStatus.RUNNING)
    )
    assert await repos["current"].find_current_analysis_id("doc-1") == "done"


async def test_no_analysis(repos):
    assert await repos["current"].find_current_analysis_id("doc-1") is None
    assert await repos["current"].load_current_analysis("doc-1") is None


async def test_a_cleared_selection_does_not_fall_back(repos):
    await _complete(repos, "a1")
    await _restore(repos, None)
    assert await repos["current"].find_current_analysis_id("doc-1") is None


async def test_a_document_without_a_state_row_reads_its_latest_parse(repos):
    # A row-less database: the jobs exist, nothing selected them.
    for analysis_id in ("old", "new"):
        job = AnalysisJob(id=analysis_id, document_id="doc-1")
        await repos["analyses"].insert(job)
        job.mark_running()
        job.mark_completed(markdown="", html="", pages_json="[]", document_json="{}")
        await repos["analyses"].update_status(job)
    assert await repos["current"].find_current_analysis_id("doc-1") == "new"


async def test_the_parse_lookup_is_batched_and_skips_an_unparsed_selection(repos, monkeypatch):
    await _complete(repos, "a1", "doc-1")
    await _complete(repos, "b1", "doc-2", parsed=False)
    states = repos["states"]
    calls = []
    find_states = states.find_states

    async def count(document_ids):
        calls.append(list(document_ids))
        return await find_states(document_ids)

    monkeypatch.setattr(states, "find_states", count)

    found = await repos["current"].find_current_parse_ids(["doc-1", "doc-2", "doc-3"])

    assert found == {"doc-1": "a1"}
    assert calls == [["doc-1", "doc-2", "doc-3"]]


# --- The readers --------------------------------------------------------------


async def test_export_reads_the_restored_analysis(repos):
    await _complete(repos, "older")
    await _complete(repos, "newer")
    await _restore(repos, "older")
    exports = ExportService(
        document_repo=repos["documents"],
        analysis_repo=repos["analyses"],
        current_analysis=repos["current"],
        file_store=MagicMock(),
    )

    assert (await exports.export("doc-1", ExportFormat.MD)).content == "# older"
    assert (await exports.export("doc-1", ExportFormat.JSON)).content == '{"v": "older"}'
    assert (await exports.export("doc-1", ExportFormat.MD, "newer")).content == "# newer"


def _document_app(repos) -> TestClient:
    service = DocumentService(
        document_repo=repos["documents"],
        analysis_repo=repos["analyses"],
        config=DocumentConfig(),
        link_repo=SqliteDocumentStoreLinkRepository(),
        store_repo=MagicMock(),
        pdf_inspector=MagicMock(),
        file_store=MagicMock(),
        current_analysis=repos["current"],
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_app_state] = lambda: AppState(document_service=service)
    return TestClient(app)


def test_the_document_names_its_current_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "document-api.db"))

    async def seed():
        await database.init_db()
        await SqliteDocumentRepository().insert(
            Document(id="doc-1", filename="doc-1.pdf", storage_path="/tmp/doc-1.pdf")
        )
        analyses = SqliteAnalysisRepository()
        states = SqliteDocumentAnalysisRepository()
        seeded = {
            "documents": SqliteDocumentRepository(),
            "analyses": analyses,
            "states": states,
            "current": CurrentAnalysisResolver(state_repo=states, analysis_repo=analyses),
        }
        await _complete(seeded, "older")
        await _complete(seeded, "newer")
        await _restore(seeded, "older")
        return seeded

    with _document_app(asyncio.run(seed())) as client:
        body = client.get("/api/documents/doc-1").json()
        listing = client.get("/api/documents").json()

    assert body["currentAnalysisId"] == "older"
    assert listing[0]["currentAnalysisId"] is None
