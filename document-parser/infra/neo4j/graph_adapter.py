"""Neo4j-backed adapters for the `GraphReader` / `GraphWriter` ports.

Introduced by #audit-01 so `services/` and `api/` stop reaching into
`infra/neo4j/*` at call sites. The free functions (`fetch_graph`,
`write_document`, `write_chunks`) stay public — these classes are thin
shims that bind them to a driver and expose the domain-port surface.

Both adapters take a `Neo4jDriver` in __init__ and dispatch to the
existing query/writer functions. Wire-shape conversion happens inside
those functions; the adapter only adds the port boundary and the driver
reference, no extra logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from infra.neo4j.chunk_writer import write_chunks as _write_chunks
from infra.neo4j.queries import fetch_graph as _fetch_graph
from infra.neo4j.tree_writer import write_document as _write_document

if TYPE_CHECKING:
    from domain.value_objects import GraphPayload
    from infra.neo4j.driver import Neo4jDriver


class Neo4jGraphReader:
    """Adapter implementing `domain.ports.GraphReader`."""

    def __init__(self, driver: Neo4jDriver) -> None:
        self._driver = driver

    async def fetch(self, doc_id: str, *, max_pages: int = 200) -> GraphPayload | None:
        return await _fetch_graph(self._driver, doc_id, max_pages=max_pages)


class Neo4jGraphWriter:
    """Adapter implementing `domain.ports.GraphWriter`.

    Wraps the tree and chunk write paths. Both methods propagate the
    underlying `Neo4jWriteError` so callers can decide whether to fail
    the surrounding pipeline (see `AnalysisService._write_tree_to_graph`
    for the soft-fail behavior gated by `config.neo4j_required`).
    """

    def __init__(self, driver: Neo4jDriver) -> None:
        self._driver = driver

    async def write_document_tree(
        self,
        *,
        doc_id: str,
        filename: str,
        document_json: str,
    ) -> None:
        await _write_document(
            self._driver,
            doc_id=doc_id,
            filename=filename,
            document_json=document_json,
        )

    async def write_chunks(self, *, doc_id: str, chunks_json: str) -> None:
        await _write_chunks(self._driver, doc_id=doc_id, chunks_json=chunks_json)

    async def ping(self) -> bool:
        """Drive a `verify_connectivity` probe through the underlying
        Neo4j driver. Swallows any connection / auth error and returns
        False so the caller (e.g. `StoreService.test_connection`) gets
        a clean boolean."""
        try:
            await self._driver.driver.verify_connectivity()
        except Exception:
            return False
        return True
