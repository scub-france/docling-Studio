"""ChunkWriter creates Chunk nodes + DERIVED_FROM links.

Builds on the tree_writer fixture — writes the tree first so that DERIVED_FROM
has Elements to link against.
"""

from __future__ import annotations

import json

from infra.neo4j import fetch_graph, write_chunks, write_document
from infra.neo4j.schema import bootstrap_schema
from tests.neo4j.test_tree_writer import FIXTURE

CHUNKS = [
    {
        "text": "Introduction. First paragraph on page 1.",
        "sourcePage": 1,
        "tokenCount": 8,
        "docItems": [
            {"selfRef": "#/texts/0", "label": "section_header"},
            {"selfRef": "#/texts/1", "label": "paragraph"},
        ],
    },
    {
        "text": "Continued on page 2.",
        "sourcePage": 2,
        "tokenCount": 4,
        "docItems": [{"selfRef": "#/texts/2", "label": "paragraph"}],
        "deleted": False,
    },
    # soft-deleted chunk: must be ignored
    {"text": "gone", "deleted": True, "docItems": []},
]


async def test_write_chunks_and_derived_from(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    await write_document(
        neo4j_driver,
        doc_id="doc-fixture",
        filename="fixture.pdf",
        document_json=json.dumps(FIXTURE),
    )

    result = await write_chunks(
        neo4j_driver,
        doc_id="doc-fixture",
        chunks_json=json.dumps(CHUNKS),
    )

    assert result.chunks_written == 2
    assert result.derived_from_edges == 3

    async with neo4j_driver.driver.session(database=neo4j_driver.database) as s:
        count = await (
            await s.run(
                "MATCH (:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk) RETURN count(c) AS n",
                id="doc-fixture",
            )
        ).single()
        assert count["n"] == 2

        # First chunk derives from 2 elements, second from 1.
        for idx, expected in [(0, 2), (1, 1)]:
            cnt = await (
                await s.run(
                    "MATCH (c:Chunk {id: $cid})-[:DERIVED_FROM]->(e:Element) RETURN count(e) AS n",
                    cid=f"doc-fixture::chunk::{idx}",
                )
            ).single()
            assert cnt["n"] == expected

        stages = await (
            await s.run(
                "MATCH (d:Document {id: $id}) RETURN d.stages_applied AS s", id="doc-fixture"
            )
        ).single()
        assert "chunks" in stages["s"]


async def test_fetch_graph_returns_full_payload(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    await write_document(
        neo4j_driver,
        doc_id="doc-fixture",
        filename="fixture.pdf",
        document_json=json.dumps(FIXTURE),
    )
    await write_chunks(
        neo4j_driver,
        doc_id="doc-fixture",
        chunks_json=json.dumps(CHUNKS),
    )

    payload = await fetch_graph(neo4j_driver, "doc-fixture")
    assert payload is not None
    assert payload.truncated is False
    assert payload.page_count == 2

    groups = {n["group"] for n in payload.nodes}
    assert groups == {"document", "element", "page", "chunk"}

    edge_types = {e["type"] for e in payload.edges}
    # Every edge kind this fixture can produce should be present.
    # PARENT_OF is intentionally excluded: all FIXTURE items have
    # `parent = #/body`, so they're roots (→ HAS_ROOT) with no nested hierarchy.
    assert {"HAS_ROOT", "NEXT", "ON_PAGE", "HAS_CHUNK", "DERIVED_FROM"} <= edge_types


async def test_fetch_graph_missing_doc_returns_none(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    assert await fetch_graph(neo4j_driver, "no-such-doc") is None


async def test_write_chunks_merges_document_when_missing(neo4j_driver):
    """Regression for #225 — writing chunks before any tree write must not
    silently no-op. The writer MERGEs the Document node first so the
    subsequent CREATE has a matching root to attach to.

    Before the fix, calling `write_chunks` on a fresh graph (no prior
    `write_document` call) returned `chunks_written = N` but the
    MATCH-then-CREATE no-op'd server-side, leaving zero chunks in the
    graph.
    """
    await bootstrap_schema(neo4j_driver)

    # Intentionally skip write_document — this is the scenario the
    # MERGE fix protects against. Note that without a tree write, the
    # CHUNKS fixture's doc_items reference Elements that don't exist —
    # DERIVED_FROM edges will be skipped (MATCH on Element fails), but
    # the chunks themselves must still land.
    result = await write_chunks(
        neo4j_driver,
        doc_id="doc-bare",
        chunks_json=json.dumps(CHUNKS),
    )

    assert result.chunks_written == 2
    # No Elements exist (no prior tree write) so DERIVED_FROM edges
    # cannot be created — but the chunk nodes themselves are written.
    async with neo4j_driver.driver.session(database=neo4j_driver.database) as s:
        chunks = await (
            await s.run(
                "MATCH (:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk) RETURN count(c) AS n",
                id="doc-bare",
            )
        ).single()
        assert chunks["n"] == 2
        doc = await (
            await s.run("MATCH (d:Document {id: $id}) RETURN d.id AS id", id="doc-bare")
        ).single()
        assert doc["id"] == "doc-bare"


async def test_write_chunks_empty_list_is_noop(neo4j_driver):
    """Writing an empty chunks payload must still succeed (idempotent
    wipe + flag update) without raising the count-mismatch assertion.
    """
    await bootstrap_schema(neo4j_driver)
    result = await write_chunks(
        neo4j_driver,
        doc_id="doc-empty",
        chunks_json=json.dumps([]),
    )
    assert result.chunks_written == 0
    assert result.derived_from_edges == 0


async def test_neo4j_write_error_is_exported_and_documented():
    """The Neo4jWriteError class is the contract for the count-assertion
    safety net. Keep it importable from the package surface so callers
    can catch it explicitly (e.g. the IngestionService log path).
    """
    from infra.neo4j.chunk_writer import Neo4jWriteError

    assert issubclass(Neo4jWriteError, RuntimeError)
    # The error class must explain itself — anyone catching this will
    # want to know it's the server-count assertion, not a generic
    # driver error.
    assert Neo4jWriteError.__doc__ is not None
    assert "count" in Neo4jWriteError.__doc__.lower()
