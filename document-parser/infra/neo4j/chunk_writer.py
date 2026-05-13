"""ChunkWriter — push chunk nodes and DERIVED_FROM edges to Neo4j.

Embeddings stay in OpenSearch. Each :Chunk node carries a chunk_index so the
OpenSearch entry can be retrieved via (doc_id, chunk_index). The
`embedding_ref` property is reserved for a future vector-store id (not used
in v0.5 — OpenSearch indexes by doc_id+chunk_index already).

When chunks carry `doc_items` provenance (list of `self_ref` strings), we
create `(:Chunk)-[:DERIVED_FROM]->(:Element)` links so that queries can go
from a chunk back to its source elements. Chunks without doc_items get no
back-links but are still persisted.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from infra.neo4j.driver import Neo4jDriver

logger = logging.getLogger(__name__)


@dataclass
class ChunkWriteResult:
    doc_id: str
    chunks_written: int
    derived_from_edges: int


def _chunk_id(doc_id: str, index: int) -> str:
    return f"{doc_id}::chunk::{index}"


async def write_chunks(
    neo: Neo4jDriver,
    *,
    doc_id: str,
    chunks_json: str,
) -> ChunkWriteResult:
    """Persist chunks for `doc_id`. Wipes prior chunks first (idempotent)."""
    chunks: list[dict[str, Any]] = json.loads(chunks_json)
    active = [c for c in chunks if not c.get("deleted")]

    chunk_rows: list[dict[str, Any]] = []
    derived_rows: list[dict[str, Any]] = []
    for idx, c in enumerate(active):
        cid = _chunk_id(doc_id, idx)
        chunk_rows.append(
            {
                "id": cid,
                "doc_id": doc_id,
                "text": c.get("text") or "",
                "chunk_index": idx,
                "token_count": c.get("tokenCount") or 0,
                "embedding_ref": "",
            }
        )
        for item in c.get("docItems") or []:
            ref = item.get("selfRef") if isinstance(item, dict) else None
            if ref:
                derived_rows.append({"chunk_id": cid, "doc_id": doc_id, "self_ref": ref})

    async with (
        neo.driver.session(database=neo.database) as session,
        await session.begin_transaction() as tx,
    ):
        # MERGE the Document node first — chunk-ingest must not silently
        # fail when the workspace wasn't analyzed via the tree writer
        # yet (or the graph was wiped manually). MERGE is idempotent;
        # `write_document` later fills in the metadata.
        await tx.run("MERGE (d:Document {id: $doc_id})", doc_id=doc_id)

        # Replace existing chunks.
        await tx.run(
            """
                MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(c:Chunk)
                DETACH DELETE c
                """,
            doc_id=doc_id,
        )
        await tx.run("MATCH (c:Chunk {doc_id: $doc_id}) DETACH DELETE c", doc_id=doc_id)

        if chunk_rows:
            await tx.run(
                """
                    MATCH (d:Document {id: $doc_id})
                    UNWIND $rows AS r
                    CREATE (c:Chunk {
                      id: r.id,
                      doc_id: r.doc_id,
                      text: r.text,
                      chunk_index: r.chunk_index,
                      token_count: r.token_count,
                      embedding_ref: r.embedding_ref
                    })
                    MERGE (d)-[:HAS_CHUNK]->(c)
                    """,
                doc_id=doc_id,
                rows=chunk_rows,
            )

        if derived_rows:
            await tx.run(
                """
                    UNWIND $rows AS r
                    MATCH (c:Chunk {id: r.chunk_id})
                    MATCH (e:Element {doc_id: r.doc_id, self_ref: r.self_ref})
                    MERGE (c)-[:DERIVED_FROM]->(e)
                    """,
                rows=derived_rows,
            )

        # Flag the Document with the new stage.
        await tx.run(
            """
                MATCH (d:Document {id: $doc_id})
                SET d.stages_applied = [s IN coalesce(d.stages_applied, []) WHERE s <> 'chunks']
                                       + ['chunks'],
                    d.last_chunk_write = datetime()
                """,
            doc_id=doc_id,
        )

        await tx.commit()

    logger.info(
        "Neo4j: wrote %d chunks (%d DERIVED_FROM) for doc %s",
        len(chunk_rows),
        len(derived_rows),
        doc_id,
    )
    return ChunkWriteResult(
        doc_id=doc_id,
        chunks_written=len(chunk_rows),
        derived_from_edges=len(derived_rows),
    )
