"""Per-(URI, user) Neo4j driver pool (#279).

Replaces the process-wide singleton that lived in `driver.py`. The
singleton model assumed every Store of `kind=neo4j` targeted the same
physical Neo4j instance — which is the half-baked-abstraction smell
#279 is fixing. The pool keys connections by `(uri, user)`, so two
stores pointing at two different clusters get two different drivers.

Concurrency model:

  - Each `(uri, user)` entry has its own `asyncio.Lock` so two parallel
    pushes to the same fresh store cannot race the driver factory.
  - A coarse pool-lock guards the `(uri, user) → Lock` map itself —
    it is held for a microsecond, only to read-or-create the entry's
    lock. The driver instantiation (TCP handshake +
    `verify_connectivity` + `bootstrap_schema`) happens under the
    entry-specific lock.
  - The pool is process-wide. Subsequent acquisitions for the same key
    short-circuit on the cached entry without touching the lock.

Schema bootstrap timing:

  - The legacy `_init_neo4j()` ran `bootstrap_schema` once at boot.
  - The pool runs it on first instantiation per `(uri, user)` — which
    is functionally equivalent for the single-cluster case and the
    only correct behaviour for multi-cluster.

`Neo4jDriver.database` carries a default database name from the
store's `config["database"]` (falls back to "neo4j"). Sessions can
still override it per call (e.g. `driver.session(database=...)`),
but for the common case the pool sets it once at construction.
"""

from __future__ import annotations

import asyncio
import logging

from neo4j import AsyncGraphDatabase

from infra.neo4j.driver import Neo4jDriver

logger = logging.getLogger(__name__)


class Neo4jDriverPool:
    """Process-wide pool of `Neo4jDriver` instances.

    The class is intentionally small — no driver-lifecycle policy
    (idle eviction, rotating credentials, etc.). For 0.6.1 the pool
    grows monotonically and is drained at shutdown via `close_all()`.
    Eviction lands when stores can be deleted at runtime (post-#279).
    """

    def __init__(self) -> None:
        self._drivers: dict[tuple[str, str], Neo4jDriver] = {}
        self._entry_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()

    async def get(
        self,
        uri: str,
        user: str,
        password: str,
        *,
        database: str = "neo4j",
    ) -> Neo4jDriver:
        """Return (or build) the driver for `(uri, user)`.

        The first caller for a key takes the entry lock, instantiates
        the driver, verifies connectivity, and runs `bootstrap_schema`.
        Subsequent callers short-circuit on the cached entry.

        `database` is the default session database recorded on the
        returned `Neo4jDriver` — callers can still override per-session
        if needed.
        """
        key = (uri, user)
        cached = self._drivers.get(key)
        if cached is not None:
            return cached
        lock = await self._acquire_entry_lock(key)
        async with lock:
            # Double-check inside the lock: another coroutine may have
            # finished the factory while we waited.
            cached = self._drivers.get(key)
            if cached is not None:
                return cached
            driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
            await driver.verify_connectivity()
            neo = Neo4jDriver(driver=driver, database=database)
            # Schema bootstrap is idempotent (every statement is
            # `CREATE CONSTRAINT ... IF NOT EXISTS`); runs once per
            # `(uri, user)` rather than once per process.
            from infra.neo4j.schema import bootstrap_schema

            await bootstrap_schema(neo)
            self._drivers[key] = neo
            logger.info("Neo4j pool: opened driver for %s@%s (db=%s)", user, uri, database)
            return neo

    async def _acquire_entry_lock(self, key: tuple[str, str]) -> asyncio.Lock:
        """Return the per-entry asyncio.Lock, creating it on first use.

        Held briefly under the pool lock — the entry lock itself does
        the long work (the driver factory).
        """
        async with self._pool_lock:
            lock = self._entry_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._entry_locks[key] = lock
            return lock

    async def evict(self, uri: str, user: str) -> bool:
        """Close + drop the driver for `(uri, user)`.

        Used when a Store's connection identity changes (PATCH or DELETE
        on the store). Returns True if a driver was evicted, False when
        the entry did not exist.
        """
        key = (uri, user)
        async with self._pool_lock:
            neo = self._drivers.pop(key, None)
            self._entry_locks.pop(key, None)
        if neo is None:
            return False
        await neo.driver.close()
        logger.info("Neo4j pool: evicted driver for %s@%s", user, uri)
        return True

    async def close_all(self) -> None:
        """Drain the pool — called from the FastAPI lifespan shutdown.

        Closes every driver and clears the maps. Safe to call multiple
        times (no-op after the first).
        """
        async with self._pool_lock:
            drivers = list(self._drivers.values())
            self._drivers.clear()
            self._entry_locks.clear()
        for neo in drivers:
            try:
                await neo.driver.close()
            except Exception:
                logger.exception("Neo4j pool: failed to close a driver during drain")
        if drivers:
            logger.info("Neo4j pool: closed %d driver(s) at shutdown", len(drivers))

    def keys(self) -> list[tuple[str, str]]:
        """Snapshot of currently-open `(uri, user)` keys. Used by tests
        and observability — not for control flow."""
        return list(self._drivers.keys())


# Module-level singleton. Tests build their own instances to avoid
# leaking state across the suite; production code goes through this.
_pool: Neo4jDriverPool | None = None


def get_pool() -> Neo4jDriverPool:
    """Return the process-wide Neo4j driver pool, building it lazily."""
    global _pool
    if _pool is None:
        _pool = Neo4jDriverPool()
    return _pool


async def reset_pool() -> None:
    """Drain the singleton pool — only used by tests.

    Production code should never call this: it discards every open
    driver without giving in-flight sessions a chance to finish.
    """
    global _pool
    if _pool is None:
        return
    await _pool.close_all()
    _pool = None
