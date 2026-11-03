"""Tests for the StoreBackendResolver (#279).

The resolver bridges per-store Store entities and the (uri, user)-keyed
driver pools. Tests use real-ish fakes for the two pools (return
sentinel objects keyed by the args) and a fully real SQLite store repo
so the env-fallback path + the `has_connection_password` plumbing get
exercised end-to-end.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from domain.models import Store
from domain.value_objects import StoreKind
from persistence.database import init_db
from persistence.store_repo import SqliteStoreRepository
from services.store_backend_resolver import (
    IngestionTargets,
    StoreBackendNotConfiguredError,
    StoreBackendResolver,
)


@pytest.fixture(autouse=True)
async def _setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()
    yield


@pytest.fixture(autouse=True)
def _fernet_key(monkeypatch):
    from infra.secrets import generate_key, reset_fernet_box

    reset_fernet_box()
    monkeypatch.setenv("STORE_SECRET_KEY", generate_key())
    yield
    reset_fernet_box()


@pytest.fixture
def store_repo() -> SqliteStoreRepository:
    return SqliteStoreRepository()


@pytest.fixture
def neo4j_pool() -> AsyncMock:
    """Fake Neo4j pool. `get` returns a sentinel keyed by the args so
    tests can assert which (uri, user, password, database) was passed.
    """
    pool = AsyncMock()
    pool.get = AsyncMock(
        side_effect=lambda uri, user, password, *, database="neo4j": {
            "kind": "neo4j",
            "uri": uri,
            "user": user,
            "password": password,
            "database": database,
        }
    )
    return pool


@pytest.fixture
def opensearch_pool() -> AsyncMock:
    pool = AsyncMock()
    pool.get = AsyncMock(
        side_effect=lambda url, *, username=None, password=None, **kw: {
            "kind": "opensearch",
            "url": url,
            "username": username,
            "password": password,
        }
    )
    return pool


def _make_resolver(
    store_repo: SqliteStoreRepository,
    neo4j_pool: Any,
    opensearch_pool: Any,
    **env: str,
) -> StoreBackendResolver:
    # Mark each "wrapped" driver so the assertions can still pattern-match
    # the underlying driver while exercising the GraphWriter port shape.
    def _fake_writer(driver: Any) -> Any:
        return {"_graph_writer_for": driver}

    return StoreBackendResolver(
        store_repo=store_repo,
        neo4j_pool=neo4j_pool,
        opensearch_pool=opensearch_pool,
        graph_writer_factory=_fake_writer,
        env_neo4j_uri=env.get("neo4j_uri", ""),
        env_neo4j_user=env.get("neo4j_user", "neo4j"),
        env_neo4j_password=env.get("neo4j_password", ""),
        env_opensearch_url=env.get("opensearch_url", ""),
    )


class TestNeo4jResolution:
    async def test_uses_store_connection_when_set(self, store_repo, neo4j_pool, opensearch_pool):
        await store_repo.insert(
            Store(
                id="s-neo",
                name="neo",
                slug="neo",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri="bolt://store-uri:7687",
                connection_username="custom-user",
            ),
            password="store-pwd",
        )
        store = await store_repo.find_by_id("s-neo")
        resolver = _make_resolver(
            store_repo,
            neo4j_pool,
            opensearch_pool,
            # Env values are present but must be ignored — store wins.
            neo4j_uri="bolt://env:7687",
            neo4j_user="env-user",
            neo4j_password="env-pwd",
        )

        targets = await resolver.resolve(store)
        assert isinstance(targets, IngestionTargets)
        assert targets.vector_store is None
        assert targets.graph_writer is not None
        neo4j_pool.get.assert_awaited_once()
        call_kwargs = neo4j_pool.get.await_args.kwargs
        call_args = neo4j_pool.get.await_args.args
        assert call_args[0] == "bolt://store-uri:7687"
        assert call_args[1] == "custom-user"
        assert call_args[2] == "store-pwd"
        assert call_kwargs["database"] == "neo4j"

    async def test_falls_back_to_env_when_store_has_no_uri(
        self, store_repo, neo4j_pool, opensearch_pool
    ):
        await store_repo.insert(
            Store(id="s-bare", name="b", slug="b", kind=StoreKind.NEO4J, embedder="b"),
        )
        store = await store_repo.find_by_id("s-bare")
        resolver = _make_resolver(
            store_repo,
            neo4j_pool,
            opensearch_pool,
            neo4j_uri="bolt://env:7687",
            neo4j_user="env-user",
            neo4j_password="env-pwd",
        )

        await resolver.resolve(store)
        args = neo4j_pool.get.await_args.args
        assert args[0] == "bolt://env:7687"
        assert args[1] == "env-user"
        assert args[2] == "env-pwd"

    async def test_raises_when_neither_store_nor_env_has_uri(
        self, store_repo, neo4j_pool, opensearch_pool
    ):
        await store_repo.insert(
            Store(id="s-x", name="x", slug="x", kind=StoreKind.NEO4J, embedder="b"),
        )
        store = await store_repo.find_by_id("s-x")
        resolver = _make_resolver(store_repo, neo4j_pool, opensearch_pool)

        with pytest.raises(StoreBackendNotConfiguredError) as excinfo:
            await resolver.resolve(store)
        msg = str(excinfo.value)
        assert "neo4j" in msg.lower()
        assert "NEO4J_URI" in msg or "connection_uri" in msg
        neo4j_pool.get.assert_not_awaited()

    async def test_picks_database_from_store_config(self, store_repo, neo4j_pool, opensearch_pool):
        await store_repo.insert(
            Store(
                id="s-db",
                name="db",
                slug="db",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri="bolt://x:7687",
                connection_username="neo4j",
                config={"database": "prod-graph"},
            ),
            password="p",
        )
        store = await store_repo.find_by_id("s-db")
        resolver = _make_resolver(store_repo, neo4j_pool, opensearch_pool)

        await resolver.resolve(store)
        assert neo4j_pool.get.await_args.kwargs["database"] == "prod-graph"

    async def test_store_without_password_on_env_uri_uses_env_credentials(
        self, store_repo, neo4j_pool, opensearch_pool
    ):
        """The seeded `default` store, its URI filled in with NEO4J_URI's own
        endpoint: the env credentials still fill in (#audit-08)."""
        await store_repo.insert(
            Store(
                id="s-nop",
                name="nop",
                slug="nop",
                kind=StoreKind.NEO4J,
                embedder="b",
                # Same endpoint as NEO4J_URI, written differently: scheme and
                # host case, the default port spelled out.
                connection_uri="BOLT://Neo4j:7687",
            ),
            # No password kwarg — connection_password_sealed stays NULL.
        )
        store = await store_repo.find_by_id("s-nop")
        assert store.has_connection_password is False
        resolver = _make_resolver(
            store_repo,
            neo4j_pool,
            opensearch_pool,
            neo4j_uri="bolt://neo4j",
            neo4j_user="env-user",
            neo4j_password="env-pwd",
        )

        await resolver.resolve(store)
        args = neo4j_pool.get.await_args.args
        assert args[1] == "env-user"
        assert args[2] == "env-pwd"

    async def test_store_without_password_on_foreign_uri_is_refused(
        self, store_repo, neo4j_pool, opensearch_pool
    ):
        """A store URI is chosen by the API caller: the env password must
        never reach it (#audit-08). No password of its own → credentials
        required, and no connection at all."""
        await store_repo.insert(
            Store(
                id="s-foreign",
                name="foreign",
                slug="foreign",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri="bolt://attacker.example:7687",
                connection_username="neo4j",
            ),
        )
        store = await store_repo.find_by_id("s-foreign")
        resolver = _make_resolver(
            store_repo,
            neo4j_pool,
            opensearch_pool,
            neo4j_uri="bolt://neo4j:7687",
            neo4j_password="env-pwd",
        )

        with pytest.raises(StoreBackendNotConfiguredError) as excinfo:
            await resolver.resolve(store)
        msg = str(excinfo.value)
        assert "credentials required" in msg
        assert "NEO4J_PASSWORD" in msg
        assert "env-pwd" not in msg
        neo4j_pool.get.assert_not_awaited()

    @pytest.mark.parametrize(
        "store_uri",
        [
            "bolt://neo4j:7688",  # another port
            "bolt+s://neo4j:7687",  # another scheme (TLS or not is part of it)
            "neo4j://neo4j:7687",  # another scheme (routing)
            "bolt://127.0.0.1:7687",  # same machine maybe, another name
            "bolt://neo4j.attacker.example:7687",
            "bolt://neo4j:notaport",  # unparseable: never the env endpoint
        ],
    )
    async def test_only_the_env_endpoint_gets_the_env_credentials(
        self, store_repo, neo4j_pool, opensearch_pool, store_uri
    ):
        await store_repo.insert(
            Store(
                id="s-near",
                name="near",
                slug="near",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri=store_uri,
            ),
        )
        store = await store_repo.find_by_id("s-near")
        resolver = _make_resolver(
            store_repo,
            neo4j_pool,
            opensearch_pool,
            neo4j_uri="bolt://neo4j:7687",
            neo4j_password="env-pwd",
        )

        with pytest.raises(StoreBackendNotConfiguredError, match="credentials required"):
            await resolver.resolve(store)
        neo4j_pool.get.assert_not_awaited()

    async def test_store_password_on_foreign_uri_never_borrows_env_user(
        self, store_repo, neo4j_pool, opensearch_pool
    ):
        await store_repo.insert(
            Store(
                id="s-own",
                name="own",
                slug="own",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri="bolt://other:7687",
            ),
            password="store-pwd",
        )
        store = await store_repo.find_by_id("s-own")
        resolver = _make_resolver(
            store_repo,
            neo4j_pool,
            opensearch_pool,
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="env-admin",
            neo4j_password="env-pwd",
        )

        await resolver.resolve(store)
        args = neo4j_pool.get.await_args.args
        assert args[0] == "bolt://other:7687"
        # Neo4j's built-in user, not NEO4J_USER.
        assert args[1] == "neo4j"
        assert args[2] == "store-pwd"


class TestEnvCredentialsNeverLeaveForAForeignUri:
    """The re-audit's probe, at the driver boundary (#audit-08): with the
    real `Neo4jDriverPool`, nothing built for a store on a foreign URI ever
    carries the env password."""

    @pytest.fixture
    def opened(self, monkeypatch) -> list[tuple[str, Any]]:
        """Every driver the real pool opens: `(uri, auth)`."""
        from infra.neo4j import driver_pool

        calls: list[tuple[str, Any]] = []

        class _FakeDriver:
            async def verify_connectivity(self) -> None:
                return None

            async def close(self) -> None:
                return None

        def _driver(uri: str, *, auth: Any) -> _FakeDriver:
            calls.append((uri, auth))
            return _FakeDriver()

        async def _no_schema(_neo: Any) -> None:
            return None

        monkeypatch.setattr(driver_pool.AsyncGraphDatabase, "driver", _driver)
        monkeypatch.setattr("infra.neo4j.schema.bootstrap_schema", _no_schema)
        return calls

    def _resolver(self, store_repo: SqliteStoreRepository) -> StoreBackendResolver:
        from infra.neo4j.driver_pool import Neo4jDriverPool

        return StoreBackendResolver(
            store_repo=store_repo,
            neo4j_pool=Neo4jDriverPool(),
            opensearch_pool=AsyncMock(),
            graph_writer_factory=lambda driver: driver,
            env_neo4j_uri="bolt://neo4j:7687",
            env_neo4j_user="neo4j",
            env_neo4j_password="EnvSecretPw-1234",
        )

    async def test_foreign_uri_without_password_opens_nothing(self, store_repo, opened):
        await store_repo.insert(
            Store(
                id="s-evil",
                name="evil",
                slug="evil",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri="bolt://127.0.0.1:17687",
            ),
        )
        store = await store_repo.find_by_id("s-evil")

        with pytest.raises(StoreBackendNotConfiguredError):
            await self._resolver(store_repo).resolve(store)
        assert opened == []

    async def test_foreign_uri_with_password_sends_only_the_store_credentials(
        self, store_repo, opened
    ):
        await store_repo.insert(
            Store(
                id="s-own",
                name="own",
                slug="own",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri="bolt://127.0.0.1:17687",
            ),
            password="store-pwd",
        )
        store = await store_repo.find_by_id("s-own")

        await self._resolver(store_repo).resolve(store)
        assert opened == [("bolt://127.0.0.1:17687", ("neo4j", "store-pwd"))]
        assert all("EnvSecretPw-1234" not in str(auth) for _, auth in opened)

    async def test_env_uri_still_gets_the_env_credentials(self, store_repo, opened):
        await store_repo.insert(
            Store(id="s-plain", name="plain", slug="plain", kind=StoreKind.NEO4J, embedder="b"),
        )
        store = await store_repo.find_by_id("s-plain")

        await self._resolver(store_repo).resolve(store)
        assert opened == [("bolt://neo4j:7687", ("neo4j", "EnvSecretPw-1234"))]


class TestOpenSearchResolution:
    async def test_uses_store_connection_when_set(self, store_repo, neo4j_pool, opensearch_pool):
        await store_repo.insert(
            Store(
                id="s-os",
                name="os",
                slug="os",
                kind=StoreKind.OPENSEARCH,
                embedder="b",
                connection_uri="http://os-store:9200",
                connection_username="os-user",
            ),
            password="os-pwd",
        )
        store = await store_repo.find_by_id("s-os")
        resolver = _make_resolver(
            store_repo,
            neo4j_pool,
            opensearch_pool,
            opensearch_url="http://os-env:9200",
        )

        targets = await resolver.resolve(store)
        assert targets.vector_store is not None
        assert targets.graph_writer is None
        call_args = opensearch_pool.get.await_args.args
        assert call_args[0] == "http://os-store:9200"
        kwargs = opensearch_pool.get.await_args.kwargs
        assert kwargs["username"] == "os-user"
        assert kwargs["password"] == "os-pwd"

    async def test_anonymous_when_no_username(self, store_repo, neo4j_pool, opensearch_pool):
        await store_repo.insert(
            Store(
                id="s-anon",
                name="anon",
                slug="anon",
                kind=StoreKind.OPENSEARCH,
                embedder="b",
                connection_uri="http://x:9200",
            ),
        )
        store = await store_repo.find_by_id("s-anon")
        resolver = _make_resolver(store_repo, neo4j_pool, opensearch_pool)

        await resolver.resolve(store)
        kwargs = opensearch_pool.get.await_args.kwargs
        assert kwargs["username"] is None
        assert kwargs["password"] is None

    async def test_falls_back_to_env_url(self, store_repo, neo4j_pool, opensearch_pool):
        await store_repo.insert(
            Store(id="s-d", name="d", slug="d", kind=StoreKind.OPENSEARCH, embedder="b"),
        )
        store = await store_repo.find_by_id("s-d")
        resolver = _make_resolver(
            store_repo,
            neo4j_pool,
            opensearch_pool,
            opensearch_url="http://env:9200",
        )

        await resolver.resolve(store)
        assert opensearch_pool.get.await_args.args[0] == "http://env:9200"

    async def test_raises_when_neither_store_nor_env_has_url(
        self, store_repo, neo4j_pool, opensearch_pool
    ):
        await store_repo.insert(
            Store(id="s-x", name="x", slug="x", kind=StoreKind.OPENSEARCH, embedder="b"),
        )
        store = await store_repo.find_by_id("s-x")
        resolver = _make_resolver(store_repo, neo4j_pool, opensearch_pool)

        with pytest.raises(StoreBackendNotConfiguredError) as excinfo:
            await resolver.resolve(store)
        msg = str(excinfo.value)
        assert "opensearch" in msg.lower()


class TestSsrfGuard:
    """Every connection to a store's own URI goes through `resolve`, so the
    guard injected there covers the push as well as the test (#audit-08)."""

    @staticmethod
    def _resolver(store_repo, neo4j_pool, opensearch_pool, blocked: bool, seen: list[str]):
        def _target_is_blocked(uri: str) -> bool:
            seen.append(uri)
            return blocked

        return StoreBackendResolver(
            store_repo=store_repo,
            neo4j_pool=neo4j_pool,
            opensearch_pool=opensearch_pool,
            graph_writer_factory=lambda driver: driver,
            env_neo4j_uri="bolt://neo4j:7687",
            env_opensearch_url="http://opensearch:9200",
            target_is_blocked=_target_is_blocked,
        )

    @pytest.mark.parametrize(
        ("kind", "uri"),
        [
            (StoreKind.OPENSEARCH, "http://169.254.169.254:9200"),
            (StoreKind.NEO4J, "bolt://169.254.169.254:7687"),
        ],
    )
    async def test_blocked_store_uri_is_refused_before_any_connection(
        self, store_repo, neo4j_pool, opensearch_pool, kind, uri
    ):
        from services.store_backend_resolver import StoreTargetBlockedError

        await store_repo.insert(
            Store(
                id="s-meta", name="meta", slug="meta", kind=kind, embedder="b", connection_uri=uri
            ),
            password="p",
        )
        store = await store_repo.find_by_id("s-meta")
        seen: list[str] = []
        resolver = self._resolver(store_repo, neo4j_pool, opensearch_pool, True, seen)

        with pytest.raises(StoreTargetBlockedError) as excinfo:
            await resolver.resolve(store)
        # A StoreBackendNotConfiguredError: callers answer its message as is.
        assert isinstance(excinfo.value, StoreBackendNotConfiguredError)
        assert seen == [uri]
        neo4j_pool.get.assert_not_awaited()
        opensearch_pool.get.assert_not_awaited()

    async def test_allowed_store_uri_resolves(self, store_repo, neo4j_pool, opensearch_pool):
        await store_repo.insert(
            Store(
                id="s-lan",
                name="lan",
                slug="lan",
                kind=StoreKind.OPENSEARCH,
                embedder="b",
                connection_uri="http://10.0.0.5:9200",
            ),
        )
        store = await store_repo.find_by_id("s-lan")
        seen: list[str] = []
        resolver = self._resolver(store_repo, neo4j_pool, opensearch_pool, False, seen)

        await resolver.resolve(store)
        assert seen == ["http://10.0.0.5:9200"]
        assert opensearch_pool.get.await_args.args[0] == "http://10.0.0.5:9200"

    async def test_env_fallback_is_not_screened(self, store_repo, neo4j_pool, opensearch_pool):
        """The env URIs are the operator's: only a store's own URI is checked."""
        await store_repo.insert(
            Store(id="s-env", name="env", slug="env", kind=StoreKind.OPENSEARCH, embedder="b"),
        )
        store = await store_repo.find_by_id("s-env")
        seen: list[str] = []
        resolver = self._resolver(store_repo, neo4j_pool, opensearch_pool, True, seen)

        await resolver.resolve(store)
        assert seen == []
        assert opensearch_pool.get.await_args.args[0] == "http://opensearch:9200"


class TestIsolationBetweenStores:
    async def test_two_neo4j_stores_resolve_to_distinct_keys(
        self, store_repo, neo4j_pool, opensearch_pool
    ):
        """The whole point of #279: two stores pointing at two
        different physical Neo4j instances must reach the right one.
        """
        await store_repo.insert(
            Store(
                id="local",
                name="local",
                slug="local",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri="bolt://local:7687",
                connection_username="neo4j",
            ),
            password="local-pwd",
        )
        await store_repo.insert(
            Store(
                id="prod",
                name="prod",
                slug="prod",
                kind=StoreKind.NEO4J,
                embedder="b",
                connection_uri="bolt://prod:7687",
                connection_username="neo4j",
            ),
            password="prod-pwd",
        )
        local = await store_repo.find_by_id("local")
        prod = await store_repo.find_by_id("prod")
        resolver = _make_resolver(store_repo, neo4j_pool, opensearch_pool)

        local_targets = await resolver.resolve(local)
        prod_targets = await resolver.resolve(prod)
        # `_fake_writer` wraps the driver in {"_graph_writer_for": driver}
        # so the test can still pattern-match the underlying pool output.
        local_driver = local_targets.graph_writer["_graph_writer_for"]
        prod_driver = prod_targets.graph_writer["_graph_writer_for"]
        assert local_driver["uri"] == "bolt://local:7687"
        assert prod_driver["uri"] == "bolt://prod:7687"
        # Passwords reach the pool intact and distinct.
        assert local_driver["password"] == "local-pwd"
        assert prod_driver["password"] == "prod-pwd"
