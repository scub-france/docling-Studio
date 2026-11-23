"""TreeReader — fetch a DoclingDocument back from Neo4j.

v0.5.0 implementation relies on the verbatim `document_json` property stored
on the Document node by TreeWriter. Reconstruction by walking Element nodes
is deferred to v0.6 (EnrichmentWriter prerequisite), where we may need to
rebuild the DoclingDocument after enrichments have been patched on graph
nodes directly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infra.neo4j.driver import Neo4jDriver

logger = logging.getLogger(__name__)


async def read_document_json(neo: Neo4jDriver, doc_id: str) -> str | None:
    """Return the stored DoclingDocument JSON for `doc_id`, or None if absent."""
    async with neo.driver.session(database=neo.database) as session:
        result = await session.run(
            "MATCH (d:Document {id: $doc_id}) RETURN d.document_json AS json",
            doc_id=doc_id,
        )
        record = await result.single()
    if record is None:
        return None
    return record["json"]


async def has_document(neo: Neo4jDriver, doc_id: str) -> bool:
    async with neo.driver.session(database=neo.database) as session:
        result = await session.run(
            "MATCH (d:Document {id: $doc_id}) RETURN count(d) AS n",
            doc_id=doc_id,
        )
        record = await result.single()
    return bool(record and record["n"] > 0)


async def delete_document(neo: Neo4jDriver, doc_id: str) -> int:
    """Wipe everything related to a doc_id. Returns nodes removed."""
    async with neo.driver.session(database=neo.database) as session:
        result = await session.run(
            """
            MATCH (d:Document {id: $doc_id})
            OPTIONAL MATCH (d)-[:HAS_ROOT|HAS_CHUNK*0..]->(n)
            WITH d, collect(DISTINCT n) AS children
            DETACH DELETE d
            WITH children
            UNWIND children AS c
            DETACH DELETE c
            RETURN size(children) + 1 AS removed
            """,
            doc_id=doc_id,
        )
        record = await result.single()
        # Also clean up orphan elements and pages tagged with this doc_id.
        await session.run("MATCH (e:Element {doc_id: $doc_id}) DETACH DELETE e", doc_id=doc_id)
        await session.run("MATCH (p:Page {doc_id: $doc_id}) DETACH DELETE p", doc_id=doc_id)
    return int(record["removed"]) if record else 0
