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

    async def test_list_counts_are_per_store_batched(self, service):
        # Two stores (plus the seeded 'default') with distinct link counts.
        # Guards the batched count_by_store() attribution: the right count
        # lands on the right store, and an unlinked store reports 0.
        store_a = await service.create_store(
            name="a",
            slug="a",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config={"index_name": "a"},
        )
        store_b = await service.create_store(
            name="b",
            slug="b",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
            config={"index_name": "b"},
        )
        doc_repo = SqliteDocumentRepository()
        link_repo = SqliteDocumentStoreLinkRepository()
        for i in range(3):
            await doc_repo.insert(
                Document(id=f"a-{i}", filename=f"a{i}.pdf", storage_path=f"/tmp/a{i}.pdf")
            )
            await link_repo.upsert(
                DocumentStoreLink(
                    id=f"la-{i}",
                    document_id=f"a-{i}",
                    store_id=store_a.id,
                    state=DocumentStoreLinkState.INGESTED,
                )
            )
        await doc_repo.insert(Document(id="b-0", filename="b0.pdf", storage_path="/tmp/b0.pdf"))
        await link_repo.upsert(
            DocumentStoreLink(
                id="lb-0",
                document_id="b-0",
                store_id=store_b.id,
                state=DocumentStoreLinkState.INGESTED,
            )
        )

        views = await service.list_stores()
        by_slug = {v.slug: v.document_count for v in views}
        assert by_slug["a"] == 3
        assert by_slug["b"] == 1
        # The seeded default has no links → defaults to 0.
        assert by_slug["default"] == 0


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


class TestConnectionPolicy:
    """#audit-08 — `connection_uri` is a target the caller picks, and the
    backend connects to it. The composition root wires the Ollama probe's
    SSRF guard and the Hugging Face read-only switch through
    `set_connection_policy`.
    """

    @pytest.fixture
    def resolver(self):
        from unittest.mock import AsyncMock

        return AsyncMock()

    @pytest.fixture
    def guarded(self, resolver):
        from infra.ssrf_guard import resolved_target_is_blocked

        service = StoreService(
            store_repo=SqliteStoreRepository(),
            link_repo=SqliteDocumentStoreLinkRepository(),
            backend_resolver=resolver,
        )
        service.set_connection_policy(target_is_blocked=resolved_target_is_blocked, read_only=False)
        return service

    async def _create(self, service, uri=None, slug="os"):
        return await service.create_store(
            name=slug,
            slug=slug,
            kind=StoreKind.OPENSEARCH,
            embedder="b",
            config=VALID_OS_CONFIG,
            connection_uri=uri,
        )

    async def test_create_refuses_the_metadata_address(self, guarded):
        with pytest.raises(StoreValidationError, match="resolves to an address") as caught:
            await self._create(guarded, "http://169.254.169.254/")
        assert caught.value.http_status == 422
        assert await SqliteStoreRepository().find_by_slug("os") is None

    async def test_create_refuses_a_neo4j_uri_on_a_link_local_address(self, guarded):
        with pytest.raises(StoreValidationError):
            await guarded.create_store(
                name="neo",
                slug="neo",
                kind=StoreKind.NEO4J,
                embedder="b",
                config={"index_name": "x"},
                connection_uri="bolt://[fe80::1]:7687",
            )

    async def test_create_accepts_loopback_and_lan_addresses(self, guarded):
        await self._create(guarded, "http://127.0.0.1:9200", slug="local")
        await self._create(guarded, "http://10.0.0.5:9200", slug="lan")

    async def test_update_refuses_the_metadata_address_and_keeps_the_old_uri(self, guarded):
        await self._create(guarded, "http://10.0.0.5:9200")

        with pytest.raises(StoreValidationError):
            await guarded.update_store("os", connection_uri="http://169.254.169.254:80")

        stored = await SqliteStoreRepository().find_by_slug("os")
        assert stored.connection_uri == "http://10.0.0.5:9200"

    async def test_update_without_a_uri_does_not_resolve_anything(self, resolver):
        calls: list[str] = []
        service = StoreService(
            SqliteStoreRepository(), SqliteDocumentStoreLinkRepository(), None, resolver
        )
        await self._create(service, "http://10.0.0.5:9200")
        service.set_connection_policy(target_is_blocked=calls.append, read_only=False)

        await service.update_store("os", name="renamed")

        assert calls == []

    async def test_connection_test_refuses_a_blocked_uri_saved_before_the_guard(
        self, guarded, resolver
    ):
        """A row written before the check (or a name re-pointed since) is
        screened again before the probe, and nothing is resolved or sent."""
        unguarded = StoreService(SqliteStoreRepository(), SqliteDocumentStoreLinkRepository())
        await self._create(unguarded, "http://169.254.169.254/")

        ok, err = await guarded.test_connection("os")

        assert ok is False
        assert "resolves to an address" in (err or "")
        resolver.resolve.assert_not_awaited()

    async def test_connection_errors_reach_the_log_not_the_client(self, guarded, resolver, caplog):
        resolver.resolve.side_effect = RuntimeError("SSH-2.0-OpenSSH_9.6 internal banner")
        await self._create(guarded, "http://10.0.0.5:22")

        with caplog.at_level("WARNING", logger="services.store_service"):
            ok, err = await guarded.test_connection("os")

        assert ok is False
        assert "banner" not in (err or "")
        assert "server log" in (err or "")
        assert "internal banner" in caplog.text

    async def test_a_ping_that_raises_gets_the_generic_message(self, guarded, resolver):
        from unittest.mock import AsyncMock

        from services.store_backend_resolver import IngestionTargets

        client = AsyncMock()
        client.ping = AsyncMock(side_effect=OSError("connection refused by 10.0.0.5:9200"))
        resolver.resolve.return_value = IngestionTargets(vector_store=client)
        await self._create(guarded, "http://10.0.0.5:9200")

        ok, err = await guarded.test_connection("os")

        assert ok is False
        assert "10.0.0.5" not in (err or "")


class TestReadOnlyDeployment:
    """On the Hugging Face Space, store configuration is read-only, as the
    reasoning and MCP settings are (`bootstrap/builder.py`)."""

    @pytest.fixture
    def resolver(self):
        from unittest.mock import AsyncMock

        return AsyncMock()

    @pytest.fixture
    def read_only(self, resolver):
        service = StoreService(
            SqliteStoreRepository(), SqliteDocumentStoreLinkRepository(), None, resolver
        )
        service.set_connection_policy(target_is_blocked=lambda _uri: False, read_only=True)
        return service

    async def test_create_update_and_delete_are_refused_with_403(self, read_only):
        from services.store_service import StoreServiceError

        writes = [
            lambda: read_only.create_store(
                name="x", slug="x", kind=StoreKind.OPENSEARCH, embedder="b", config={}
            ),
            lambda: read_only.update_store("default", name="renamed"),
            lambda: read_only.delete_store("default"),
        ]
        for write in writes:
            with pytest.raises(StoreServiceError, match="read-only") as caught:
                await write()
            assert caught.value.http_status == 403
        assert (await read_only.get_by_slug("default")).name != "renamed"

    async def test_removing_a_document_link_is_refused_with_403(self, read_only):
        from services.store_service import StoreServiceError

        store = await read_only.get_by_slug("default")
        await SqliteDocumentRepository().insert(
            Document(id="d-1", filename="t.pdf", storage_path="/tmp/t.pdf")
        )
        links = SqliteDocumentStoreLinkRepository()
        await links.upsert(
            DocumentStoreLink(
                id="l-1",
                document_id="d-1",
                store_id=store.id,
                state=DocumentStoreLinkState.INGESTED,
            )
        )

        with pytest.raises(StoreServiceError, match="read-only") as caught:
            await read_only.remove_document("default", "d-1")
        assert caught.value.http_status == 403
        assert await links.find_one("d-1", store.id) is not None

    async def test_connection_test_is_refused_without_connecting(self, read_only, resolver):
        ok, err = await read_only.test_connection("default")

        assert ok is False
        assert "read-only" in (err or "")
        resolver.resolve.assert_not_awaited()

    async def test_reads_still_work(self, read_only):
        assert [s.slug for s in await read_only.list_stores()] == ["default"]
