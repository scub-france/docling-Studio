"""Async Neo4j driver dataclass.

The `Neo4jDriver` value object lives here so other infra modules
(chunk_writer, tree_writer, schema bootstrap) can import it without
pulling the pool. Driver acquisition itself is the pool's job — see
`infra/neo4j/driver_pool.py`.

Historical note: until 0.6.1, this module owned a process-wide
singleton driver via `get_driver()` / `close_driver()`. That model
hardwired every Neo4j-kind store to one physical cluster (the
`NEO4J_URI` env var). #279 moves driver acquisition to a pool keyed
by `(uri, user)`. The legacy `get_driver` and `close_driver` are
preserved as thin compatibility shims that delegate to the pool —
they are still imported by `tests/neo4j/conftest.py`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Neo4jDriver:
    """Wrapper around an `AsyncDriver` + a default session database.

    Carried by the driver pool; passed around inside services so the
    writers can open sessions without knowing about the pool.
    """

    driver: AsyncDriver
    database: str = "neo4j"


async def get_driver(uri: str, user: str, password: str, database: str = "neo4j") -> Neo4jDriver:
    """Compatibility shim — returns the pool entry for `(uri, user)`.

    Pre-0.6.1 callers (and the live test fixture in
    `tests/neo4j/conftest.py`) still use this. New callers should
    talk to `infra.neo4j.driver_pool.get_pool()` directly.
    """
    from infra.neo4j.driver_pool import get_pool

    return await get_pool().get(uri, user, password, database=database)


async def close_driver() -> None:
    """Compatibility shim — drains the pool.

    Pre-0.6.1 callers expected a single driver. The pool may hold
    several, so this draining variant is the closest semantic match.
    """
    from infra.neo4j.driver_pool import get_pool

    await get_pool().close_all()
