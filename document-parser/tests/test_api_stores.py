"""Tests for `/api/stores/*` HTTP endpoints (#251)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from domain.models import Document, DocumentStoreLink
from domain.value_objects import DocumentStoreLinkState
from main import app
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.store_repo import SqliteStoreRepository
from services.store_service import StoreService


@pytest.fixture(autouse=True)
async def setup_db_and_state(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()

    store_repo = SqliteStoreRepository()
    link_repo = SqliteDocumentStoreLinkRepository()
    document_repo = SqliteDocumentRepository()

    original = getattr(app.state, "store_service", None)
    app.state.store_service = StoreService(store_repo, link_repo, document_repo)
    yield
    app.state.store_service = original


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


VALID_OS = {
    "name": "rh",
    "slug": "rh",
    "kind": "opensearch",
    "embedder": "bge-m3",
    "config": {"indexName": "rh"},
}


class TestList:
    def test_list_returns_seeded_default(self, client):
        resp = client.get("/api/stores")
        assert resp.status_code == 200
        slugs = [s["slug"] for s in resp.json()]
        assert "default" in slugs

    def test_list_uses_camel_case(self, client):
        resp = client.get("/api/stores")
        body = resp.json()[0]
        assert "documentCount" in body
        assert "isDefault" in body


class TestCreate:
    def test_create_201(self, client):
        resp = client.post("/api/stores", json=VALID_OS)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["slug"] == "rh"
        assert body["isDefault"] is False

    def test_create_duplicate_slug_409(self, client):
        client.post("/api/stores", json=VALID_OS)
        resp = client.post("/api/stores", json={**VALID_OS, "name": "rh-2"})
        assert resp.status_code == 409

    def test_create_invalid_kind_422(self, client):
        resp = client.post("/api/stores", json={**VALID_OS, "kind": "pinecone"})
        assert resp.status_code == 422

    def test_create_missing_index_422(self, client):
        resp = client.post("/api/stores", json={**VALID_OS, "config": {}})
        assert resp.status_code == 422

    def test_create_bad_slug_422(self, client):
        resp = client.post("/api/stores", json={**VALID_OS, "slug": "RH Corp"})
        assert resp.status_code == 422


class TestRead:
    def test_get_by_slug(self, client):
        client.post("/api/stores", json=VALID_OS)
        resp = client.get("/api/stores/rh")
        assert resp.status_code == 200
        body = resp.json()
        assert body["slug"] == "rh"
        assert body["embedder"] == "bge-m3"

    def test_get_unknown_404(self, client):
        resp = client.get("/api/stores/missing")
        assert resp.status_code == 404


class TestUpdate:
    def test_patch_embedder(self, client):
        client.post("/api/stores", json=VALID_OS)
        resp = client.patch("/api/stores/rh", json={"embedder": "bge-large"})
        assert resp.status_code == 200
        assert resp.json()["embedder"] == "bge-large"

    def test_patch_rename_slug(self, client):
        client.post("/api/stores", json=VALID_OS)
        resp = client.patch("/api/stores/rh", json={"slug": "rh-v2"})
        assert resp.status_code == 200
        assert resp.json()["slug"] == "rh-v2"
        assert client.get("/api/stores/rh").status_code == 404
        assert client.get("/api/stores/rh-v2").status_code == 200

    def test_patch_unknown_404(self, client):
        resp = client.patch("/api/stores/missing", json={"embedder": "x"})
        assert resp.status_code == 404


class TestDelete:
    def test_delete_204(self, client):
        client.post("/api/stores", json=VALID_OS)
        resp = client.delete("/api/stores/rh")
        assert resp.status_code == 204
        assert client.get("/api/stores/rh").status_code == 404

    def test_delete_default_409(self, client):
        resp = client.delete("/api/stores/default")
        assert resp.status_code == 409

    async def test_delete_with_links_409(self, client):
        client.post("/api/stores", json=VALID_OS)
        # Seed a link from outside (service-level access).
        await SqliteDocumentRepository().insert(
            Document(id="d-1", filename="t.pdf", storage_path="/tmp/t.pdf")
        )
        store = await SqliteStoreRepository().find_by_slug("rh")
        assert store is not None
        await SqliteDocumentStoreLinkRepository().upsert(
            DocumentStoreLink(
                id="l-1",
                document_id="d-1",
                store_id=store.id,
                state=DocumentStoreLinkState.INGESTED,
            )
        )
        resp = client.delete("/api/stores/rh")
        assert resp.status_code == 409


class TestStoreDocuments:
    async def test_list_documents_for_store(self, client):
        client.post("/api/stores", json=VALID_OS)
        await SqliteDocumentRepository().insert(
            Document(id="d-1", filename="hr.pdf", storage_path="/tmp/hr.pdf")
        )
        store = await SqliteStoreRepository().find_by_slug("rh")
        assert store is not None
        await SqliteDocumentStoreLinkRepository().upsert(
            DocumentStoreLink(
                id="l-1",
                document_id="d-1",
                store_id=store.id,
                state=DocumentStoreLinkState.INGESTED,
            )
        )
        resp = client.get("/api/stores/rh/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["docId"] == "d-1"
        assert body[0]["filename"] == "hr.pdf"

    async def test_remove_document_204(self, client):
        client.post("/api/stores", json=VALID_OS)
        await SqliteDocumentRepository().insert(
            Document(id="d-1", filename="hr.pdf", storage_path="/tmp/hr.pdf")
        )
        store = await SqliteStoreRepository().find_by_slug("rh")
        assert store is not None
        await SqliteDocumentStoreLinkRepository().upsert(
            DocumentStoreLink(
                id="l-1",
                document_id="d-1",
                store_id=store.id,
                state=DocumentStoreLinkState.INGESTED,
            )
        )
        resp = client.delete("/api/stores/rh/documents/d-1")
        assert resp.status_code == 204
        # Now empty.
        listing = client.get("/api/stores/rh/documents")
        assert listing.json() == []

    def test_remove_unknown_doc_404(self, client):
        client.post("/api/stores", json=VALID_OS)
        resp = client.delete("/api/stores/rh/documents/missing")
        assert resp.status_code == 404
