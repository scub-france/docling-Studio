"""Tests for the Store and DocumentStoreLink repositories (#203)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.models import Document, DocumentStoreLink, Store
from domain.value_objects import DocumentStoreLinkState, StoreKind
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.store_repo import SqliteStoreRepository


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()
    yield


@pytest.fixture
def store_repo():
    return SqliteStoreRepository()


@pytest.fixture
def link_repo():
    return SqliteDocumentStoreLinkRepository()


@pytest.fixture
def document_repo():
    return SqliteDocumentRepository()


class TestStoreRepo:
    async def test_default_store_seeded_on_init(self, store_repo):
        """init_db() must seed exactly one `default` store on a fresh DB."""
        default = await store_repo.get_default()
        assert default is not None
        assert default.slug == "default"
        assert default.is_default is True
        assert default.kind == StoreKind.OPENSEARCH

    async def test_seed_is_idempotent(self, store_repo):
        """Re-running init_db() must not create a second default store."""
        await init_db()
        await init_db()
        all_stores = await store_repo.find_all()
        slugs = [s.slug for s in all_stores]
        assert slugs.count("default") == 1

    async def test_insert_and_find_by_slug(self, store_repo):
        store = Store(
            id="s-rh",
            name="rh-corpus-v3",
            slug="rh-corpus-v3",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config={"index_name": "rh-corpus-v3"},
        )
        await store_repo.insert(store)

        found = await store_repo.find_by_slug("rh-corpus-v3")
        assert found is not None
        assert found.embedder == "bge-m3"
        assert found.config == {"index_name": "rh-corpus-v3"}

    async def test_find_all_orders_default_first(self, store_repo):
        await store_repo.insert(
            Store(
                id="s-rh",
                name="rh",
                slug="rh",
                kind=StoreKind.OPENSEARCH,
                embedder="bge-m3",
            )
        )
        await store_repo.insert(
            Store(
                id="s-legal",
                name="legal",
                slug="legal",
                kind=StoreKind.OPENSEARCH,
                embedder="bge-m3",
            )
        )
        all_stores = await store_repo.find_all()
        assert all_stores[0].slug == "default"  # seeded default comes first


class TestDocumentStoreLinkRepo:
    async def _seed_doc(self, document_repo, doc_id: str = "doc-1") -> Document:
        doc = Document(id=doc_id, filename="t.pdf", storage_path="/tmp/t.pdf")
        await document_repo.insert(doc)
        return doc

    async def test_upsert_creates_then_updates(self, link_repo, document_repo):
        await self._seed_doc(document_repo)
        link = DocumentStoreLink(
            id="l-1",
            document_id="doc-1",
            store_id="default",
            state=DocumentStoreLinkState.INGESTED,
        )
        await link_repo.upsert(link)

        # Update same (doc, store) — no second row.
        link.mark_ingested(
            hash_="abc123",
            at=datetime(2026, 4, 29, 12, tzinfo=UTC),
            run_id="run-1",
        )
        await link_repo.upsert(link)

        all_for_doc = await link_repo.find_for_document("doc-1")
        assert len(all_for_doc) == 1
        assert all_for_doc[0].chunkset_hash == "abc123"
        assert all_for_doc[0].last_run_id == "run-1"

    async def test_unique_constraint_on_doc_store_pair(self, link_repo, document_repo):
        """Two links with the same (doc, store) collapse to one via upsert."""
        await self._seed_doc(document_repo)
        await link_repo.upsert(
            DocumentStoreLink(
                id="l-1",
                document_id="doc-1",
                store_id="default",
                state=DocumentStoreLinkState.INGESTED,
            )
        )
        await link_repo.upsert(
            DocumentStoreLink(
                id="l-2",
                document_id="doc-1",
                store_id="default",
                state=DocumentStoreLinkState.STALE,
            )
        )
        rows = await link_repo.find_for_document("doc-1")
        assert len(rows) == 1
        assert rows[0].state == DocumentStoreLinkState.STALE

    async def test_find_one_returns_none_when_absent(self, link_repo, document_repo):
        await self._seed_doc(document_repo)
        assert await link_repo.find_one("doc-1", "default") is None

    async def test_cascade_delete_when_doc_removed(self, link_repo, document_repo):
        await self._seed_doc(document_repo)
        await link_repo.upsert(
            DocumentStoreLink(
                id="l-1",
                document_id="doc-1",
                store_id="default",
                state=DocumentStoreLinkState.INGESTED,
            )
        )
        await document_repo.delete("doc-1")
        rows = await link_repo.find_for_document("doc-1")
        assert rows == []

    async def test_state_round_trips(self, link_repo, document_repo):
        await self._seed_doc(document_repo)
        for state in DocumentStoreLinkState:
            link = DocumentStoreLink(
                id=f"l-{state.value}",
                document_id="doc-1",
                store_id=f"store-{state.value}",
                state=state,
            )
            # Need a store row for FK; seed minimal stores.
            from persistence.store_repo import SqliteStoreRepository

            await SqliteStoreRepository().insert(
                Store(
                    id=f"store-{state.value}",
                    name=f"s-{state.value}",
                    slug=f"s-{state.value}",
                    kind=StoreKind.OPENSEARCH,
                    embedder="bge-m3",
                )
            )
            await link_repo.upsert(link)
            found = await link_repo.find_one("doc-1", f"store-{state.value}")
            assert found is not None
            assert found.state == state
