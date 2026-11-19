"""HTTP contract of the document version routes, on a real service and database (#267)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.document_versions import router
from api.state import AppState, get_app_state
from domain.models import (
    AnalysisJob,
    AnalysisStatus,
    Chunk,
    Document,
    DocumentVersion,
    DocumentVersionKind,
)
from persistence import database
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository
from services.version_service import VersionService

BASE = "/api/documents/doc-1"


def _snapshot(*texts: str) -> str:
    return json.dumps(
        [{"sequence": index, "text": text} for index, text in enumerate(texts)],
    )


def _version(version_id: str, *, analysis_id: str | None, day: int, texts: tuple[str, ...]):
    return DocumentVersion(
        id=version_id,
        document_id="doc-1",
        kind=DocumentVersionKind.CHUNKS,
        analysis_id=analysis_id,
        chunks_source_analysis_id=analysis_id,
        chunks_source_result_hash="a" * 64 if analysis_id else None,
        chunks_snapshot=_snapshot(*texts),
        summary=f"Version {version_id}",
        created_at=datetime(2026, 11, day, tzinfo=UTC),
    )


async def _seed() -> VersionService:
    await database.init_db()
    documents = SqliteDocumentRepository()
    analyses = SqliteAnalysisRepository()
    state = SqliteDocumentAnalysisRepository()
    chunks = SqliteChunkRepository()
    versions = SqliteDocumentVersionRepository()
    for doc_id in ("doc-1", "doc-2", "doc-empty"):
        await documents.insert(
            Document(id=doc_id, filename=f"{doc_id}.pdf", storage_path=f"/tmp/{doc_id}.pdf")
        )
    await analyses.insert(
        AnalysisJob(id="analysis-1", document_id="doc-1", status=AnalysisStatus.COMPLETED)
    )
    await analyses.insert(
        AnalysisJob(id="analysis-running", document_id="doc-1", status=AnalysisStatus.RUNNING)
    )
    await chunks.insert_many([Chunk(document_id="doc-1", sequence=0, text="live")])
    await versions.insert(_version("v-old", analysis_id="analysis-1", day=1, texts=("a", "b")))
    await versions.insert(_version("v-new", analysis_id="analysis-1", day=2, texts=("c",)))
    await versions.insert(
        _version("v-running", analysis_id="analysis-running", day=3, texts=("r",))
    )
    await versions.insert(
        DocumentVersion(id="v-other", document_id="doc-2", analysis_id=None, chunks_snapshot="[]")
    )
    return VersionService(
        version_repo=versions,
        chunk_repo=chunks,
        document_repo=documents,
        analysis_repo=analyses,
        analysis_state_repo=state,
    )


async def _live_state(document_id: str) -> tuple[list[str], str | None]:
    live = await SqliteChunkRepository().find_for_document(document_id)
    state = await SqliteDocumentAnalysisRepository().find_state(document_id)
    texts = [chunk.text for chunk in sorted(live, key=lambda chunk: chunk.sequence)]
    return texts, state.active_analysis_id if state else None


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "versions-api.db"))
    service = asyncio.run(_seed())
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_app_state] = lambda: AppState(version_service=service)
    with TestClient(app) as test_client:
        yield test_client


# --- GET /versions ------------------------------------------------------------


def test_list_returns_the_versions_newest_first_in_camel_case(client):
    response = client.get(f"{BASE}/versions")

    assert response.status_code == 200
    body = response.json()
    assert [version["id"] for version in body] == ["v-running", "v-new", "v-old"]
    oldest = body[-1]
    assert oldest["documentId"] == "doc-1"
    assert oldest["kind"] == "chunks"
    assert oldest["analysisId"] == "analysis-1"
    assert oldest["chunksSourceAnalysisId"] == "analysis-1"
    assert oldest["chunksSourceResultHash"] == "a" * 64
    assert oldest["chunksSnapshotSize"] == 2
    assert oldest["summary"] == "Version v-old"
    assert oldest["createdAt"].startswith("2026-11-01")


def test_list_of_a_document_without_versions_is_empty(client):
    response = client.get("/api/documents/doc-empty/versions")

    assert response.status_code == 200
    assert response.json() == []


def test_list_of_an_unknown_document_is_not_found(client):
    response = client.get("/api/documents/missing/versions")

    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]


# --- POST /versions/{id}/restore ---------------------------------------------


def test_restore_replaces_live_chunks_and_selects_the_version_analysis(client):
    response = client.post(f"{BASE}/versions/v-old/restore")

    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["analysisId"], body["chunksSnapshotSize"]) == (
        "v-old",
        "analysis-1",
        2,
    )
    assert asyncio.run(_live_state("doc-1")) == (["a", "b"], "analysis-1")


def test_restore_records_where_the_restored_chunks_came_from(client):
    client.post(f"{BASE}/versions/v-old/restore")

    state = asyncio.run(SqliteDocumentAnalysisRepository().find_state("doc-1"))
    assert state.chunk_source is not None
    assert (state.chunk_source.analysis_id, state.chunk_source.result_hash) == (
        "analysis-1",
        "a" * 64,
    )


def test_restore_on_an_unknown_document_is_not_found(client):
    response = client.post("/api/documents/missing/versions/v-old/restore")

    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]


def test_restore_of_an_unknown_version_is_not_found(client):
    response = client.post(f"{BASE}/versions/nope/restore")

    assert response.status_code == 404
    assert "Version not found" in response.json()["detail"]
    assert asyncio.run(_live_state("doc-1"))[0] == ["live"]


def test_restore_of_another_documents_version_is_not_found(client):
    response = client.post(f"{BASE}/versions/v-other/restore")

    assert response.status_code == 404
    assert "Version not found" in response.json()["detail"]


def test_restore_of_a_version_whose_analysis_is_not_completed_is_a_conflict(client):
    response = client.post(f"{BASE}/versions/v-running/restore")

    assert response.status_code == 409
    assert "no longer available" in response.json()["detail"]
    assert asyncio.run(_live_state("doc-1")) == (["live"], None)


def test_routes_answer_503_when_the_service_is_not_wired():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_app_state] = lambda: AppState()
    with TestClient(app) as test_client:
        assert test_client.get(f"{BASE}/versions").status_code == 503
        assert test_client.post(f"{BASE}/versions/v-old/restore").status_code == 503
