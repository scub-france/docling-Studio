"""Tests for StoreService — CRUD + validations (#251)."""

from __future__ import annotations

import pytest

from domain.models import Document, DocumentStoreLink
from domain.value_objects import DocumentStoreLinkState, StoreKind
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.store_repo import SqliteStoreRepository
from services.store_service import (
    StoreConflictError,
    StoreNotFoundError,
    StoreService,
    StoreValidationError,
)


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()
    yield


@pytest.fixture
def service():
    return StoreService(SqliteStoreRepository(), SqliteDocumentStoreLinkRepository())


VALID_OS_CONFIG = {"index_name": "rh-corpus-v3"}


class TestCreate:
    async def test_create_ok(self, service):
        store = await service.create_store(
            name="rh-corpus",
            slug="rh-corpus",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        assert store.id
        assert store.slug == "rh-corpus"

    async def test_slug_normalized_to_lowercase(self, service):
        store = await service.create_store(
            name="RH",
            slug="RH-Corpus",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        assert store.slug == "rh-corpus"

    async def test_create_rejects_duplicate_slug(self, service):
        await service.create_store(
            name="rh",
            slug="rh",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        with pytest.raises(StoreConflictError):
            await service.create_store(
                name="rh-2",
                slug="rh",
                kind=StoreKind.OPENSEARCH,
                embedder="bge-m3",
                config=VALID_OS_CONFIG,
            )

    async def test_create_rejects_duplicate_name(self, service):
        await service.create_store(
            name="rh",
            slug="rh-1",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        with pytest.raises(StoreConflictError):
            await service.create_store(
                name="rh",
                slug="rh-2",
                kind=StoreKind.OPENSEARCH,
                embedder="bge-m3",
                config=VALID_OS_CONFIG,
            )

    async def test_create_rejects_bad_slug(self, service):
        with pytest.raises(StoreValidationError):
            await service.create_store(
                name="rh",
                slug="RH Corpus",
                kind=StoreKind.OPENSEARCH,
                embedder="bge-m3",
                config=VALID_OS_CONFIG,
            )

    async def test_create_rejects_missing_index_name(self, service):
        with pytest.raises(StoreValidationError):
            await service.create_store(
                name="rh",
                slug="rh",
                kind=StoreKind.OPENSEARCH,
                embedder="bge-m3",
                config={},
            )

    async def test_create_default_clears_others(self, service):
        # The seeded 'default' store starts as is_default=True.
        new_default = await service.create_store(
            name="new",
            slug="new",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config={"index_name": "new"},
            is_default=True,
        )
        all_stores = await service.list_stores()
        defaults = [s for s in all_stores if s.is_default]
        assert len(defaults) == 1
        assert defaults[0].slug == new_default.slug


class TestRead:
    async def test_get_by_slug_404(self, service):
        with pytest.raises(StoreNotFoundError):
            await service.get_by_slug("missing")

    async def test_list_includes_seeded_default(self, service):
        stores = await service.list_stores()
        slugs = [s.slug for s in stores]
        assert "default" in slugs

    async def test_list_counts_linked_documents(self, service):
        # Seed a doc + a link to the seeded default store.
        doc_repo = SqliteDocumentRepository()
        await doc_repo.insert(Document(id="d-1", filename="t.pdf", storage_path="/tmp/t.pdf"))
        await SqliteDocumentStoreLinkRepository().upsert(
            DocumentStoreLink(
                id="l-1",
                document_id="d-1",
                store_id="default",
                state=DocumentStoreLinkState.INGESTED,
            )
        )
        views = await service.list_stores()
        default_view = next(v for v in views if v.slug == "default")
        assert default_view.document_count == 1


class TestUpdate:
    async def test_partial_update(self, service):
        await service.create_store(
            name="rh",
            slug="rh",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        updated = await service.update_store("rh", embedder="bge-large")
        assert updated.embedder == "bge-large"
        # Other fields untouched.
        assert updated.name == "rh"

    async def test_update_rename_slug(self, service):
        await service.create_store(
            name="rh",
            slug="rh",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        updated = await service.update_store("rh", new_slug="rh-v2")
        assert updated.slug == "rh-v2"
        with pytest.raises(StoreNotFoundError):
            await service.get_by_slug("rh")

    async def test_update_rejects_slug_collision(self, service):
        await service.create_store(
            name="a",
            slug="a",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config={"index_name": "a"},
        )
        await service.create_store(
            name="b",
            slug="b",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config={"index_name": "b"},
        )
        with pytest.raises(StoreConflictError):
            await service.update_store("a", new_slug="b")

    async def test_update_promote_default_demotes_others(self, service):
        await service.create_store(
            name="rh",
            slug="rh",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        await service.update_store("rh", is_default=True)
        defaults = [s for s in await service.list_stores() if s.is_default]
        assert len(defaults) == 1
        assert defaults[0].slug == "rh"

    async def test_update_rejects_invalid_config(self, service):
        await service.create_store(
            name="rh",
            slug="rh",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        with pytest.raises(StoreValidationError):
            await service.update_store("rh", config={})


class TestDelete:
    async def test_delete_ok(self, service):
        await service.create_store(
            name="tmp",
            slug="tmp",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config={"index_name": "tmp"},
        )
        await service.delete_store("tmp")
        with pytest.raises(StoreNotFoundError):
            await service.get_by_slug("tmp")

    async def test_delete_seeded_default_refused(self, service):
        with pytest.raises(StoreConflictError):
            await service.delete_store("default")

    async def test_delete_with_links_refused(self, service):
        store = await service.create_store(
            name="rh",
            slug="rh",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config=VALID_OS_CONFIG,
        )
        doc_repo = SqliteDocumentRepository()
        await doc_repo.insert(Document(id="d-1", filename="t.pdf", storage_path="/tmp/t.pdf"))
        await SqliteDocumentStoreLinkRepository().upsert(
            DocumentStoreLink(
                id="l-1",
                document_id="d-1",
                store_id=store.id,
                state=DocumentStoreLinkState.INGESTED,
            )
        )
        with pytest.raises(StoreConflictError):
            await service.delete_store("rh")
