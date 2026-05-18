"""Unit tests for the Neo4j driver pool (#279).

The live-Neo4j integration tests in `tests/neo4j/` cover the
end-to-end "open a driver, verify connectivity, talk Cypher" path
through the shim `get_driver()`. These tests exercise the **pool**'s
behaviour — keying, concurrent first-use, eviction, draining — with
the real driver factory mocked out so they run without a Neo4j
container.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from infra.neo4j.driver_pool import Neo4jDriverPool


@pytest.fixture
def fake_async_graph_database(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace `neo4j.AsyncGraphDatabase.driver(...)` with a recording
    factory that yields a fake AsyncDriver per call.

    Returns the list of constructor invocations so tests can assert
    how many distinct drivers were built. The fake driver itself
    records `close()` calls and supports `verify_connectivity()`.
    """
    invocations: list[dict[str, Any]] = []

    def factory(uri: str, *, auth: tuple[str, str]) -> Any:
        invocations.append({"uri": uri, "auth": auth})
        fake = MagicMock(name=f"FakeDriver[{uri}]")
        fake.verify_connectivity = AsyncMock(return_value=None)
        fake.close = AsyncMock(return_value=None)
        return fake

    monkeypatch.setattr(
        "infra.neo4j.driver_pool.AsyncGraphDatabase.driver",
        factory,
    )
    # bootstrap_schema runs inside `pool.get` — stub it out so tests
    # don't depend on the schema module.
    monkeypatch.setattr(
        "infra.neo4j.schema.bootstrap_schema",
        AsyncMock(return_value=None),
    )
    return invocations


class TestPoolKeying:
    async def test_same_key_returns_same_driver(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        a = await pool.get("bolt://x:7687", "neo4j", "pwd")
        b = await pool.get("bolt://x:7687", "neo4j", "pwd")
        assert a is b
        # Only one underlying AsyncDriver was constructed.
        assert len(fake_async_graph_database) == 1

    async def test_different_uri_yields_different_drivers(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        a = await pool.get("bolt://prod:7687", "neo4j", "pwd")
        b = await pool.get("bolt://staging:7687", "neo4j", "pwd")
        assert a is not b
        assert len(fake_async_graph_database) == 2
        uris = {inv["uri"] for inv in fake_async_graph_database}
        assert uris == {"bolt://prod:7687", "bolt://staging:7687"}

    async def test_different_user_yields_different_drivers(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        # Same URI, two different users (e.g. read-only vs admin)
        # produce two distinct drivers — auth scope is part of the key.
        pool = Neo4jDriverPool()
        a = await pool.get("bolt://x:7687", "reader", "ro-pwd")
        b = await pool.get("bolt://x:7687", "admin", "ad-pwd")
        assert a is not b
        assert len(fake_async_graph_database) == 2

    async def test_default_database_recorded_on_driver(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        neo = await pool.get("bolt://x:7687", "neo4j", "pwd", database="prod-graph")
        assert neo.database == "prod-graph"

    async def test_keys_snapshot_reflects_pool_state(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        await pool.get("bolt://a:7687", "u1", "p")
        await pool.get("bolt://b:7687", "u2", "p")
        keys = set(pool.keys())
        assert keys == {("bolt://a:7687", "u1"), ("bolt://b:7687", "u2")}


class TestConcurrentFirstUse:
    async def test_parallel_first_calls_share_one_driver(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        """Two coroutines racing to acquire the same fresh key must
        share the resulting driver — the second waits on the first's
        factory call rather than building a second one.
        """
        pool = Neo4jDriverPool()
        results = await asyncio.gather(
            pool.get("bolt://x:7687", "neo4j", "pwd"),
            pool.get("bolt://x:7687", "neo4j", "pwd"),
            pool.get("bolt://x:7687", "neo4j", "pwd"),
        )
        assert results[0] is results[1] is results[2]
        # Exactly one underlying driver was built despite three
        # parallel calls — the entry lock did its job.
        assert len(fake_async_graph_database) == 1

    async def test_distinct_keys_can_init_in_parallel(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        await asyncio.gather(
            pool.get("bolt://a:7687", "u1", "p"),
            pool.get("bolt://b:7687", "u2", "p"),
        )
        assert len(fake_async_graph_database) == 2


class TestEviction:
    async def test_evict_closes_driver_and_drops_key(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        neo = await pool.get("bolt://x:7687", "neo4j", "pwd")
        evicted = await pool.evict("bolt://x:7687", "neo4j")
        assert evicted is True
        neo.driver.close.assert_awaited_once()
        # A subsequent `get` rebuilds — eviction was real.
        again = await pool.get("bolt://x:7687", "neo4j", "pwd")
        assert again is not neo
        assert len(fake_async_graph_database) == 2

    async def test_evict_returns_false_for_unknown_key(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        assert await pool.evict("bolt://nope:7687", "ghost") is False


class TestCloseAll:
    async def test_drains_every_driver_then_clears(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        a = await pool.get("bolt://a:7687", "u1", "p")
        b = await pool.get("bolt://b:7687", "u2", "p")
        await pool.close_all()
        a.driver.close.assert_awaited_once()
        b.driver.close.assert_awaited_once()
        assert pool.keys() == []

    async def test_close_all_is_idempotent(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        await pool.get("bolt://x:7687", "neo4j", "pwd")
        await pool.close_all()
        # Second call must be a no-op (no driver to close, no error).
        await pool.close_all()
        assert pool.keys() == []

    async def test_close_all_continues_when_one_driver_fails(
        self, fake_async_graph_database: list[dict[str, Any]]
    ) -> None:
        pool = Neo4jDriverPool()
        a = await pool.get("bolt://a:7687", "u1", "p")
        b = await pool.get("bolt://b:7687", "u2", "p")
        # Make the first driver's close raise — the second must still
        # be closed (best-effort drain).
        a.driver.close.side_effect = RuntimeError("network gone")
        await pool.close_all()
        b.driver.close.assert_awaited_once()
        assert pool.keys() == []
