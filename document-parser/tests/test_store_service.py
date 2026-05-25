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

    async def test_create_neo4j_ok(self, service):
        store = await service.create_store(
            name="kg",
            slug="kg",
            kind=StoreKind.NEO4J,
            embedder="bge-m3",
            config={"index_name": "chunks-vec", "database": "neo4j"},
        )
        assert store.kind is StoreKind.NEO4J
        assert store.config["index_name"] == "chunks-vec"

    async def test_create_neo4j_rejects_missing_index_name(self, service):
        with pytest.raises(StoreValidationError):
            await service.create_store(
                name="kg",
                slug="kg",
                kind=StoreKind.NEO4J,
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


# ---------------------------------------------------------------------------
# Connection identity (#279)
# ---------------------------------------------------------------------------


class TestTestConnection:
    """Behavioural tests for `StoreService.test_connection`. The
    resolver is mocked at the service boundary — the resolver itself
    has its own dedicated tests in tests/test_store_backend_resolver.py.
    """

    @pytest.fixture(autouse=True)
    def _fernet_key(self, monkeypatch):
        from infra.secrets import generate_key, reset_fernet_box

        reset_fernet_box()
        monkeypatch.setenv("STORE_SECRET_KEY", generate_key())
        yield
        reset_fernet_box()

    @pytest.fixture
    def store_with_resolver(self):
        from unittest.mock import AsyncMock

        store_repo = SqliteStoreRepository()
        link_repo = SqliteDocumentStoreLinkRepository()
        resolver = AsyncMock()
        # Each test overrides resolver.resolve.return_value /
        # side_effect as needed; the targets shape is what matters.
        service = StoreService(
            store_repo=store_repo,
            link_repo=link_repo,
            backend_resolver=resolver,
        )
        return service, resolver

    async def test_returns_ok_true_when_opensearch_ping_succeeds(self, store_with_resolver):
        from unittest.mock import AsyncMock

        from services.store_backend_resolver import IngestionTargets

        service, resolver = store_with_resolver
        fake_client = AsyncMock()
        fake_client.ping = AsyncMock(return_value=True)
        resolver.resolve.return_value = IngestionTargets(vector_store=fake_client)
        await service.create_store(
            name="os",
            slug="os",
            kind=StoreKind.OPENSEARCH,
            embedder="b",
            config=VALID_OS_CONFIG,
            connection_uri="http://x:9200",
        )

        ok, err = await service.test_connection("os")
        assert ok is True
        assert err is None
        fake_client.ping.assert_awaited_once()

    async def test_returns_ok_false_when_ping_returns_false(self, store_with_resolver):
        from unittest.mock import AsyncMock

        from services.store_backend_resolver import IngestionTargets

        service, resolver = store_with_resolver
        fake_client = AsyncMock()
        fake_client.ping = AsyncMock(return_value=False)
        resolver.resolve.return_value = IngestionTargets(vector_store=fake_client)
        await service.create_store(
            name="os",
            slug="os",
            kind=StoreKind.OPENSEARCH,
            embedder="b",
            config=VALID_OS_CONFIG,
            connection_uri="http://x:9200",
        )

        ok, err = await service.test_connection("os")
        assert ok is False
        assert "ping" in (err or "").lower()

    async def test_returns_ok_true_for_neo4j_when_verify_connectivity_succeeds(
        self, store_with_resolver
    ):
        from unittest.mock import AsyncMock, MagicMock

        from services.store_backend_resolver import IngestionTargets

        service, resolver = store_with_resolver
        # `GraphWriter` port stub — `test_connection` now calls
        # `.ping()` instead of reaching into the underlying driver.
        graph_writer = MagicMock()
        graph_writer.ping = AsyncMock(return_value=True)
        resolver.resolve.return_value = IngestionTargets(graph_writer=graph_writer)
        await service.create_store(
            name="neo",
            slug="neo",
            kind=StoreKind.NEO4J,
            embedder="b",
            config={"index_name": "x"},
            connection_uri="bolt://x:7687",
        )

        ok, err = await service.test_connection("neo")
        assert ok is True
        assert err is None
        graph_writer.ping.assert_awaited_once()

    async def test_returns_ok_false_when_resolver_raises(self, store_with_resolver):
        from services.store_backend_resolver import StoreBackendNotConfiguredError

        service, resolver = store_with_resolver
        resolver.resolve.side_effect = StoreBackendNotConfiguredError("no NEO4J_URI configured")
        await service.create_store(
            name="neo",
            slug="neo",
            kind=StoreKind.NEO4J,
            embedder="b",
            config={"index_name": "x"},
        )

        ok, err = await service.test_connection("neo")
        assert ok is False
        assert "NEO4J_URI" in (err or "")

    async def test_returns_ok_false_when_resolver_not_wired(self):
        """A service built without a resolver returns a friendly 'not
        available' message instead of crashing.
        """
        service = StoreService(
            store_repo=SqliteStoreRepository(),
            link_repo=SqliteDocumentStoreLinkRepository(),
        )
        await service.create_store(
            name="os",
            slug="os",
            kind=StoreKind.OPENSEARCH,
            embedder="b",
            config=VALID_OS_CONFIG,
        )
        ok, err = await service.test_connection("os")
        assert ok is False
        assert "resolver" in (err or "").lower()

    async def test_raises_404_when_slug_unknown(self):
        service = StoreService(
            store_repo=SqliteStoreRepository(),
            link_repo=SqliteDocumentStoreLinkRepository(),
        )
        with pytest.raises(StoreNotFoundError):
            await service.test_connection("ghost")


class TestConnectionFieldsRoundTrip:
    """Service-level tests for the create/update + connection fields
    pairing. The repo-level seal/open is already covered in
    tests/test_store_repo.py — here we verify the service plumbing
    forwards the values correctly.
    """

    @pytest.fixture(autouse=True)
    def _fernet_key(self, monkeypatch):
        from infra.secrets import generate_key, reset_fernet_box

        reset_fernet_box()
        monkeypatch.setenv("STORE_SECRET_KEY", generate_key())
        yield
        reset_fernet_box()

    async def test_create_with_uri_username_and_password(self, service):
        store = await service.create_store(
            name="neo",
            slug="neo",
            kind=StoreKind.NEO4J,
            embedder="b",
            config={"index_name": "x"},
            connection_uri="bolt://store:7687",
            connection_username="neo4j",
            connection_password="secret",
        )
        assert store.connection_uri == "bolt://store:7687"
        assert store.connection_username == "neo4j"
        assert store.has_connection_password is True

    async def test_create_rejects_bad_neo4j_scheme(self, service):
        with pytest.raises(StoreValidationError):
            await service.create_store(
                name="neo",
                slug="neo",
                kind=StoreKind.NEO4J,
                embedder="b",
                config={"index_name": "x"},
                connection_uri="http://wrong:7687",
            )

    async def test_create_rejects_bad_opensearch_scheme(self, service):
        with pytest.raises(StoreValidationError):
            await service.create_store(
                name="os",
                slug="os",
                kind=StoreKind.OPENSEARCH,
                embedder="b",
                config=VALID_OS_CONFIG,
                connection_uri="bolt://wrong:9200",
            )

    async def test_update_password_none_keeps_seal(self, service):
        await service.create_store(
            name="neo",
            slug="neo",
            kind=StoreKind.NEO4J,
            embedder="b",
            config={"index_name": "x"},
            connection_password="initial",
        )
        updated = await service.update_store("neo", name="neo-renamed")
        assert updated.has_connection_password is True

    async def test_update_password_empty_string_clears_seal(self, service):
        await service.create_store(
            name="neo",
            slug="neo",
            kind=StoreKind.NEO4J,
            embedder="b",
            config={"index_name": "x"},
            connection_password="initial",
        )
        updated = await service.update_store("neo", connection_password="")
        assert updated.has_connection_password is False

    async def test_update_password_non_empty_replaces_seal(self, service):
        await service.create_store(
            name="neo",
            slug="neo",
            kind=StoreKind.NEO4J,
            embedder="b",
            config={"index_name": "x"},
            connection_password="initial",
        )
        updated = await service.update_store("neo", connection_password="rotated")
        assert updated.has_connection_password is True
        # The plaintext is unsealable from the repo with the right key.
        plaintext = await SqliteStoreRepository().get_connection_password(updated.id)
        assert plaintext == "rotated"
