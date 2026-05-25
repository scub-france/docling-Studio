"""Neo4j storage adapter — graph-native document structure.

Provides a thin driver wrapper, idempotent schema bootstrap, and
walkers between DoclingDocument and the graph model.

## Why no OGM (yet)

We use the official `neo4j` Python driver directly with raw Cypher
inside explicit transactions, NOT an Object-Graph Mapper.

The Java/JVM equivalent would be Spring Data Neo4j or Neo4j-OGM. The
Python ecosystem has `neomodel` (closest match — class-based,
declarative, repository pattern) and the older `py2neo`.

Why we stick to the raw driver for 0.6.x:
  - Cypher is the natural query language; OGMs add an extra mapping
    layer on top.
  - Our writers are write-heavy and shape-specific (chunks vs tree vs
    derived-from edges) — the abstractions an OGM offers (single-entity
    repositories, lifecycle hooks) don't map cleanly to what we do.
  - Transaction semantics we need (multi-statement, idempotent MERGE-
    then-CREATE) are already first-class in the driver.

Trade-off acknowledged: raw Cypher MATCH-then-CREATE patterns can
silently no-op when the MATCH returns zero rows (#225 hit this exact
bug). Each writer now asserts the row count returned by Neo4j after
write, raising a `Neo4jWriteError` instead of trusting the Python-side
counts. Anyone re-evaluating the OGM question for 0.7+: see the
discussion in #225 and consider a prototype on a single writer first.
"""

from infra.neo4j.chunk_writer import ChunkWriteResult, write_chunks
from infra.neo4j.driver import Neo4jDriver, close_driver, get_driver
from infra.neo4j.driver_pool import Neo4jDriverPool, get_pool, reset_pool
from infra.neo4j.graph_adapter import Neo4jGraphReader, Neo4jGraphWriter
from infra.neo4j.queries import fetch_graph
from infra.neo4j.schema import bootstrap_schema
from infra.neo4j.tree_reader import (
    delete_document,
    document_exists,
    read_document_json,
)
from infra.neo4j.tree_writer import TreeWriteResult, write_document

__all__ = [
    "ChunkWriteResult",
    "Neo4jDriver",
    "Neo4jDriverPool",
    "Neo4jGraphReader",
    "Neo4jGraphWriter",
    "TreeWriteResult",
    "bootstrap_schema",
    "close_driver",
    "delete_document",
    "document_exists",
    "fetch_graph",
    "get_driver",
    "get_pool",
    "read_document_json",
    "reset_pool",
    "write_chunks",
    "write_document",
]
