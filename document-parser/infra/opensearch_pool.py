"""Per-(URL, user) OpenSearch client pool (#279).

Mirrors `infra/neo4j/driver_pool.py` for the OpenSearch adapter. The
0.5.x code instantiated a single `OpenSearchStore` for the
`OPENSEARCH_URL` env var — fine for one cluster, broken for the
multi-store mental model #279 establishes. The pool lets two stores
target two different OpenSearch clusters (or the same cluster with
different basic-auth credentials) without sharing state.

Key shape: `(url, username | None)`. Two stores on the same cluster
but different users get distinct pool entries. Two stores on the
same cluster with the same username (or both unauthenticated) share.
`default_limit` is not part of the key — it is a per-call concern.

Concurrency: the pool reuses the same coarse-pool-lock + per-entry-lock
pattern from the Neo4j pool. See `infra/neo4j/driver_pool.py` for the
extended rationale; same constraints apply (idempotent first-use,
double-checked locking inside the entry lock).
"""

from __future__ import annotations

import asyncio
import logging

from infra.opensearch_store import OpenSearchStore

logger = logging.getLogger(__name__)


class OpenSearchClientPool:
    """Process-wide pool of `OpenSearchStore` clients.

    Each entry owns its own `AsyncOpenSearch` connection pool, so
    closing an entry tears down only that cluster's connections.
    """

    def __init__(self) -> None:
        self._clients: dict[tuple[str, str | None], OpenSearchStore] = {}
        self._entry_locks: dict[tuple[str, str | None], asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()

    async def get(
        self,
        url: str,
        *,
        username: str | None = None,
        password: str | None = None,
        verify_certs: bool = False,
        default_limit: int = 1000,
    ) -> OpenSearchStore:
        """Return (or build) the client for `(url, username)`.

        `password` is only consulted on first-build; the cached entry
        ignores subsequent password values for the same key. This is
        intentional — the pool key is the identity, not the credential.
        Rotating a password means evicting the entry first, then
        re-acquiring with the new value.
        """
        key = (url, username)
        cached = self._clients.get(key)
        if cached is not None:
            return cached
        lock = await self._acquire_entry_lock(key)
        async with lock:
            cached = self._clients.get(key)
            if cached is not None:
                return cached
            client = OpenSearchStore(
                url,
                verify_certs=verify_certs,
                default_limit=default_limit,
                username=username,
                password=password,
            )
            self._clients[key] = client
            logger.info(
                "OpenSearch pool: opened client for %s (auth=%s)",
                url,
                "basic" if username else "none",
            )
            return client

    async def _acquire_entry_lock(self, key: tuple[str, str | None]) -> asyncio.Lock:
        async with self._pool_lock:
            lock = self._entry_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._entry_locks[key] = lock
            return lock

    async def evict(self, url: str, username: str | None = None) -> bool:
        """Close + drop the client for `(url, username)`. Returns True
        when an entry was evicted, False when the key was unknown."""
        key = (url, username)
        async with self._pool_lock:
            client = self._clients.pop(key, None)
            self._entry_locks.pop(key, None)
        if client is None:
            return False
        await client.close()
        logger.info(
            "OpenSearch pool: evicted client for %s (auth=%s)",
            url,
            "basic" if username else "none",
        )
        return True

    async def close_all(self) -> None:
        """Drain the pool. Idempotent; best-effort if a close raises."""
        async with self._pool_lock:
            clients = list(self._clients.values())
            self._clients.clear()
            self._entry_locks.clear()
        for client in clients:
            try:
                await client.close()
            except Exception:
                logger.exception("OpenSearch pool: failed to close a client during drain")
        if clients:
            logger.info("OpenSearch pool: closed %d client(s) at shutdown", len(clients))

    def keys(self) -> list[tuple[str, str | None]]:
        """Snapshot of currently-open `(url, user)` keys."""
        return list(self._clients.keys())


_pool: OpenSearchClientPool | None = None


def get_pool() -> OpenSearchClientPool:
    """Process-wide OpenSearch client pool, built lazily."""
    global _pool
    if _pool is None:
        _pool = OpenSearchClientPool()
    return _pool


async def reset_pool() -> None:
    """Drain the singleton — test-only."""
    global _pool
    if _pool is None:
        return
    await _pool.close_all()
    _pool = None
