"""The /api/documents/{id}/versions router (#267): the wire shape of a
document's versions (`frontend/src/shared/types.ts`, `DocumentVersion`),
on a real VersionService and a temporary database."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from domain.models import Chunk, Document, DocumentVersion, DocumentVersionKind
from main import app
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository
from services.version_service import VersionService
from tests.app_state import state_override

WIRE_KEYS = {
    "id",
    "documentId",
    "kind",
    "analysisId",
    "chunksSnapshotSize",
    "summary",
    "createdAt",
}
T0 = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    monkeypatch.setattr("persistence.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()
    await SqliteDocumentRepository().insert(
        Document(id="doc-1", filename="a.pdf", storage_path="/tmp/a.pdf")
    )


@pytest.fixture
def versions():
    return SqliteDocumentVersionRepository()


@pytest.fixture
def client():
    service = VersionService(
        version_repo=SqliteDocumentVersionRepository(),
        chunk_repo=SqliteChunkRepository(),
        document_repo=SqliteDocumentRepository(),
    )
    with state_override(app, version_service=service):
        yield TestClient(app, raise_server_exceptions=False)


def _snapshot(n: int) -> str:
    return json.dumps([{"sequence": i, "text": f"t{i}"} for i in range(n)])


async def _version(repo, vid: str, *, minutes: int, snapshot: str | None, **kw) -> None:
    await repo.insert(
        DocumentVersion(
            id=vid,
            document_id="doc-1",
            chunks_snapshot=snapshot,
            created_at=T0 + timedelta(minutes=minutes),
            **kw,
        )
    )


class TestListVersions:
    async def test_shape_order_and_chunk_counts(self, client, versions):
        await _version(versions, "v-old", minutes=0, snapshot=_snapshot(3), analysis_id="a1")
        await _version(
            versions,
            "v-new",
            minutes=5,
            snapshot=_snapshot(2),
            kind=DocumentVersionKind.CHUNKS,
            summary="Chunks generated",
        )

        resp = client.get("/api/documents/doc-1/versions")

        assert resp.status_code == 200
        body = resp.json()
        assert [set(v) for v in body] == [WIRE_KEYS, WIRE_KEYS]
        assert body == [
            {
                "id": "v-new",
                "documentId": "doc-1",
                "kind": "chunks",
                "analysisId": None,
                "chunksSnapshotSize": 2,
                "summary": "Chunks generated",
                "createdAt": "2026-11-03 09:05:00+00:00",
            },
            {
                "id": "v-old",
                "documentId": "doc-1",
                "kind": "analysis",
                "analysisId": "a1",
                "chunksSnapshotSize": 3,
                "summary": "",
                "createdAt": "2026-11-03 09:00:00+00:00",
            },
        ]

    @pytest.mark.parametrize(
        "snapshot", [None, "", "[]", "not json"], ids=["null", "empty", "no-chunks", "corrupt"]
    )
    async def test_snapshot_without_chunks_counts_zero(self, client, versions, snapshot):
        await _version(versions, "v", minutes=0, snapshot=snapshot)

        resp = client.get("/api/documents/doc-1/versions")

        assert resp.status_code == 200
        assert [v["chunksSnapshotSize"] for v in resp.json()] == [0]

    def test_unknown_document_404(self, client):
        resp = client.get("/api/documents/nope/versions")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "Document not found: nope"}


class TestRestoreVersion:
    async def test_shape_and_chunk_count(self, client, versions):
        await SqliteChunkRepository().insert(Chunk(document_id="doc-1", sequence=0, text="live"))
        await _version(versions, "v1", minutes=0, snapshot=_snapshot(4), analysis_id="a1")

        resp = client.post("/api/documents/doc-1/versions/v1/restore")

        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == WIRE_KEYS
        assert (body["id"], body["analysisId"], body["chunksSnapshotSize"]) == ("v1", "a1", 4)

    def test_unknown_version_404(self, client):
        resp = client.post("/api/documents/doc-1/versions/nope/restore")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "Version not found: nope"}

    def test_unknown_document_404(self, client):
        resp = client.post("/api/documents/nope/versions/v1/restore")

        assert resp.status_code == 404
        assert resp.json() == {"detail": "Document not found: nope"}
