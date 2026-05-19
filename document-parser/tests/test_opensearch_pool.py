"""Unit tests for the OpenSearch client pool (#279).

Mirror of `tests/test_neo4j_driver_pool.py` for the OpenSearch
adapter. The pool's behaviour is testable without a live cluster
because `OpenSearchStore.__init__` is the only thing that touches
`AsyncOpenSearch` — we stub that constructor at the module boundary.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from infra.opensearch_pool import OpenSearchClientPool


@pytest.fixture
def fake_async_opensearch(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace `AsyncOpenSearch(...)` with a recording factory.

    Returns the list of constructor invocations; each fake client
    supports `close()` and `info()` for ping-style probes.
    """
    invocations: list[dict[str, Any]] = []

    def factory(**kwargs: Any) -> Any:
        invocations.append(kwargs)
        fake = MagicMock(name=f"FakeOpenSearch[{kwargs.get('hosts')}]")
        fake.close = AsyncMock(return_value=None)
        fake.info = AsyncMock(return_value={"name": "fake"})
        return fake

    monkeypatch.setattr(
        "infra.opensearch_store.AsyncOpenSearch",
        factory,
    )
    return invocations


class TestPoolKeying:
    async def test_same_url_returns_same_client(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        a = await pool.get("http://localhost:9200")
        b = await pool.get("http://localhost:9200")
        assert a is b
        assert len(fake_async_opensearch) == 1

    async def test_different_url_yields_different_clients(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        a = await pool.get("http://prod:9200")
        b = await pool.get("http://staging:9200")
        assert a is not b
        assert len(fake_async_opensearch) == 2

    async def test_username_is_part_of_key(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        # Same URL, two different usernames → two distinct clients.
        a = await pool.get("http://x:9200", username="reader", password="r")
        b = await pool.get("http://x:9200", username="admin", password="a")
        assert a is not b
        assert len(fake_async_opensearch) == 2

    async def test_anonymous_and_authed_are_distinct(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        anon = await pool.get("http://x:9200")
        authed = await pool.get("http://x:9200", username="u", password="p")
        assert anon is not authed

    async def test_password_does_not_affect_key(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        """Passwords are not in the key — rotating a password is an
        explicit evict + re-acquire flow, not a quiet rebuild.
        """
        pool = OpenSearchClientPool()
        first = await pool.get("http://x:9200", username="u", password="old")
        second = await pool.get("http://x:9200", username="u", password="new")
        assert first is second
        assert len(fake_async_opensearch) == 1

    async def test_basic_auth_propagates_to_client_constructor(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        await pool.get("http://x:9200", username="u", password="p")
        assert fake_async_opensearch[0]["http_auth"] == ("u", "p")

    async def test_no_auth_passes_none_to_client(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        await pool.get("http://x:9200")
        assert fake_async_opensearch[0]["http_auth"] is None


class TestConcurrentFirstUse:
    async def test_parallel_first_calls_share_one_client(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        results = await asyncio.gather(
            pool.get("http://x:9200"),
            pool.get("http://x:9200"),
            pool.get("http://x:9200"),
        )
        assert results[0] is results[1] is results[2]
        assert len(fake_async_opensearch) == 1


class TestEviction:
    async def test_evict_closes_and_drops_entry(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        client = await pool.get("http://x:9200")
        evicted = await pool.evict("http://x:9200")
        assert evicted is True
        client._client.close.assert_awaited_once()
        # Re-acquiring rebuilds.
        again = await pool.get("http://x:9200")
        assert again is not client

    async def test_evict_returns_false_for_unknown_key(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        assert await pool.evict("http://nope:9200") is False


class TestCloseAll:
    async def test_drains_every_client(self, fake_async_opensearch: list[dict[str, Any]]) -> None:
        pool = OpenSearchClientPool()
        a = await pool.get("http://a:9200")
        b = await pool.get("http://b:9200")
        await pool.close_all()
        a._client.close.assert_awaited_once()
        b._client.close.assert_awaited_once()
        assert pool.keys() == []

    async def test_close_all_is_idempotent(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        await pool.get("http://x:9200")
        await pool.close_all()
        await pool.close_all()
        assert pool.keys() == []

    async def test_close_all_continues_when_one_client_fails(
        self, fake_async_opensearch: list[dict[str, Any]]
    ) -> None:
        pool = OpenSearchClientPool()
        a = await pool.get("http://a:9200")
        b = await pool.get("http://b:9200")
        a._client.close.side_effect = RuntimeError("network gone")
        await pool.close_all()
        b._client.close.assert_awaited_once()
        assert pool.keys() == []
