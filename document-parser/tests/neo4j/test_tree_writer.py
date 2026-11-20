"""TreeWriter round-trip + structural sanity checks.

Fixture is a hand-crafted DoclingDocument JSON with: one section containing
two paragraphs and a table, spanning two pages. Tests verify that the graph
mirrors the structure (HAS_ROOT, PARENT_OF, ON_PAGE, NEXT) and that
re-writing the same doc is an idempotent replace.
"""

from __future__ import annotations

import json

from infra.neo4j import read_document_json, write_document
from infra.neo4j.schema import bootstrap_schema

FIXTURE = {
    "name": "fixture.pdf",
    "pages": {
        "1": {"page_no": 1, "size": {"width": 595, "height": 842}},
        "2": {"page_no": 2, "size": {"width": 595, "height": 842}},
    },
    "body": {
        "self_ref": "#/body",
        "children": [
            {"$ref": "#/texts/0"},
            {"$ref": "#/texts/1"},
            {"$ref": "#/texts/2"},
            {"$ref": "#/tables/0"},
        ],
    },
    "texts": [
        {
            "self_ref": "#/texts/0",
            "parent": {"$ref": "#/body"},
            "label": "section_header",
            "text": "Introduction",
            "level": 1,
            "prov": [{"page_no": 1, "bbox": {"l": 10, "t": 10, "r": 100, "b": 30}}],
        },
        {
            "self_ref": "#/texts/1",
            "parent": {"$ref": "#/body"},
            "label": "paragraph",
            "text": "First paragraph on page 1.",
            "prov": [{"page_no": 1, "bbox": {"l": 10, "t": 40, "r": 500, "b": 80}}],
        },
        {
            "self_ref": "#/texts/2",
            "parent": {"$ref": "#/body"},
            "label": "paragraph",
            "text": "Continued on page 2.",
            "prov": [{"page_no": 2, "bbox": {"l": 10, "t": 40, "r": 500, "b": 80}}],
        },
    ],
    "tables": [
        {
            "self_ref": "#/tables/0",
            "parent": {"$ref": "#/body"},
            "label": "table",
            "text": "",
            "data": {"num_rows": 2, "num_cols": 2, "grid": [[1, 2], [3, 4]]},
            "prov": [{"page_no": 2, "bbox": {"l": 10, "t": 90, "r": 500, "b": 200}}],
        }
    ],
    "pictures": [],
    "groups": [],
}


async def _count(session, cypher: str, **params) -> int:
    r = await session.run(cypher, **params)
    rec = await r.single()
    return int(rec["n"]) if rec else 0


async def test_write_creates_expected_structure(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    doc_json = json.dumps(FIXTURE)

    result = await write_document(
        neo4j_driver,
        doc_id="doc-fixture",
        filename="fixture.pdf",
        document_json=doc_json,
    )

    assert result.elements_written == 4
    assert result.pages_written == 2
    # Every item in FIXTURE has exactly one prov entry → 4 Provenance nodes.
    assert result.provenances_written == 4

    async with neo4j_driver.driver.session(database=neo4j_driver.database) as s:
        assert (
            await _count(
                s,
                "MATCH (d:Document {id: $id}) RETURN count(d) AS n",
                id="doc-fixture",
            )
            == 1
        )
        assert (
            await _count(
                s,
                "MATCH (:Document {id: $id})-[:HAS_ROOT]->(e:Element) RETURN count(e) AS n",
                id="doc-fixture",
            )
            == 4
        )
        assert (
            await _count(
                s,
                "MATCH (e:Element:SectionHeader {doc_id: $id, self_ref: '#/texts/0'}) "
                "RETURN count(e) AS n",
                id="doc-fixture",
            )
            == 1
        )
        assert (
            await _count(
                s,
                "MATCH (e:Element:Table {doc_id: $id}) RETURN count(e) AS n",
                id="doc-fixture",
            )
            == 1
        )
        # Reading-order chain: 3 NEXT edges for 4 elements.
        assert (
            await _count(
                s,
                "MATCH (a:Element {doc_id: $id})-[:NEXT]->(b:Element {doc_id: $id}) "
                "RETURN count(*) AS n",
                id="doc-fixture",
            )
            == 3
        )
        # Post-v0.6: ON_PAGE attaches Provenance to Page, not Element directly.
        # Traverse through the Provenance node.
        assert (
            await _count(
                s,
                "MATCH (:Element {doc_id: $id})-[:HAS_PROV]->"
                "(:Provenance)-[:ON_PAGE]->(:Page {doc_id: $id}) "
                "RETURN count(*) AS n",
                id="doc-fixture",
            )
            == 4
        )
        # Each element has exactly one Provenance here (single-page fixture).
        assert (
            await _count(
                s,
                "MATCH (e:Element {doc_id: $id})-[:HAS_PROV]->(pv:Provenance) "
                "RETURN count(pv) AS n",
                id="doc-fixture",
            )
            == 4
        )


async def test_rewrite_is_idempotent_replace(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    doc_json = json.dumps(FIXTURE)

    await write_document(
        neo4j_driver,
        doc_id="doc-fixture",
        filename="fixture.pdf",
        document_json=doc_json,
    )
    # Second write with the same id must not duplicate anything.
    await write_document(
        neo4j_driver,
        doc_id="doc-fixture",
        filename="fixture.pdf",
        document_json=doc_json,
    )

    async with neo4j_driver.driver.session(database=neo4j_driver.database) as s:
        assert (
            await _count(s, "MATCH (d:Document {id: $id}) RETURN count(d) AS n", id="doc-fixture")
            == 1
        )
        assert (
            await _count(
                s,
                "MATCH (e:Element {doc_id: $id}) RETURN count(e) AS n",
                id="doc-fixture",
            )
            == 4
        )


async def test_reader_returns_verbatim_json(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    doc_json = json.dumps(FIXTURE, sort_keys=True)
    await write_document(
        neo4j_driver,
        doc_id="doc-fixture",
        filename="fixture.pdf",
        document_json=doc_json,
    )

    read_back = await read_document_json(neo4j_driver, "doc-fixture")
    assert read_back is not None
    assert json.loads(read_back) == json.loads(doc_json)


async def test_reader_missing_doc_returns_none(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    assert await read_document_json(neo4j_driver, "no-such-doc") is None


# Issue #197: Docling emits one InlineGroup per inline-styled paragraph plus N
# child `text` items (one per style run). Naive 1:1 mirroring blew up section
# graphs into per-style-run nodes. The writer now collapses an InlineGroup into
# a single :Paragraph node carrying the concatenated text of its children, and
# skips those children entirely.
INLINE_FIXTURE = {
    "name": "inline.html",
    "pages": {
        "1": {"page_no": 1, "size": {"width": 595, "height": 842}},
    },
    "body": {
        "self_ref": "#/body",
        "children": [
            {"$ref": "#/texts/0"},
            {"$ref": "#/groups/0"},
        ],
    },
    "texts": [
        {
            "self_ref": "#/texts/0",
            "parent": {"$ref": "#/body"},
            "label": "section_header",
            "text": "Heading",
            "level": 1,
            "prov": [{"page_no": 1, "bbox": {"l": 10, "t": 10, "r": 100, "b": 30}}],
        },
        {
            "self_ref": "#/texts/1",
            "parent": {"$ref": "#/groups/0"},
            "label": "text",
            "text": "Hello",
            "prov": [{"page_no": 1, "bbox": {"l": 10, "t": 40, "r": 50, "b": 60}}],
        },
        {
            "self_ref": "#/texts/2",
            "parent": {"$ref": "#/groups/0"},
            "label": "text",
            "text": "world",
            "prov": [{"page_no": 1, "bbox": {"l": 55, "t": 40, "r": 100, "b": 60}}],
        },
        {
            "self_ref": "#/texts/3",
            "parent": {"$ref": "#/groups/0"},
            "label": "text",
            "text": "!",
            "prov": [{"page_no": 1, "bbox": {"l": 105, "t": 40, "r": 110, "b": 60}}],
        },
    ],
    "tables": [],
    "pictures": [],
    "groups": [
        {
            "self_ref": "#/groups/0",
            "parent": {"$ref": "#/body"},
            "label": "inline",
            "children": [
                {"$ref": "#/texts/1"},
                {"$ref": "#/texts/2"},
                {"$ref": "#/texts/3"},
            ],
        },
    ],
}


async def test_inline_group_collapses_into_single_paragraph(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    doc_json = json.dumps(INLINE_FIXTURE)

    result = await write_document(
        neo4j_driver,
        doc_id="doc-inline",
        filename="inline.html",
        document_json=doc_json,
    )

    # Section header + collapsed inline group only — NOT 5 (+3 style runs).
    assert result.elements_written == 2
    # The inline group inherits its 3 children's provs (1 each); the section
    # header has its own prov → 4 Provenance nodes total.
    assert result.provenances_written == 4

    async with neo4j_driver.driver.session(database=neo4j_driver.database) as s:
        r = await s.run(
            "MATCH (e:Element:Paragraph {doc_id: $id, self_ref: '#/groups/0'}) "
            "RETURN e.text AS text",
            id="doc-inline",
        )
        rec = await r.single()
        assert rec is not None, "InlineGroup should write a :Paragraph node"
        assert rec["text"] == "Hello world !"

        for child_ref in ("#/texts/1", "#/texts/2", "#/texts/3"):
            assert (
                await _count(
                    s,
                    "MATCH (e:Element {doc_id: $id, self_ref: $ref}) RETURN count(e) AS n",
                    id="doc-inline",
                    ref=child_ref,
                )
                == 0
            ), f"Style-run {child_ref} should be skipped, not written as a node"

        # Inline group inherits provs from all children (order preserved).
        assert (
            await _count(
                s,
                "MATCH (e:Element:Paragraph {doc_id: $id, self_ref: '#/groups/0'})"
                "-[:HAS_PROV]->(pv:Provenance) RETURN count(pv) AS n",
                id="doc-inline",
            )
            == 3
        )

        # Reading order: section_header → inline-as-paragraph (1 NEXT edge).
        assert (
            await _count(
                s,
                "MATCH (a:Element {doc_id: $id})-[:NEXT]->(b:Element) RETURN count(*) AS n",
                id="doc-inline",
            )
            == 1
        )

        assert (
            await _count(
                s,
                "MATCH (:Document {id: $id})-[:HAS_ROOT]->(:Element) RETURN count(*) AS n",
                id="doc-inline",
            )
            == 2
        )

        # ON_PAGE through Provenance → Page (matches the new schema).
        assert (
            await _count(
                s,
                "MATCH (:Element {doc_id: $id})-[:HAS_PROV]->"
                "(:Provenance)-[:ON_PAGE]->(:Page) RETURN count(*) AS n",
                id="doc-inline",
            )
            == 4
        )


# Same issue (#197): a Picture's `children` are internal text labels (flowchart
# boxes, chart axis labels, diagram callouts) extracted by Docling's layout
# model. Mirroring them 1:1 drowns the figure in dozens of tiny nodes.
PICTURE_FIXTURE = {
    "name": "figure.pdf",
    "pages": {
        "1": {"page_no": 1, "size": {"width": 595, "height": 842}},
    },
    "body": {
        "self_ref": "#/body",
        "children": [
            {"$ref": "#/texts/0"},
            {"$ref": "#/pictures/0"},
        ],
    },
    "texts": [
        {
            "self_ref": "#/texts/0",
            "parent": {"$ref": "#/body"},
            "label": "caption",
            "text": "Figure 1: Pipeline overview.",
            "prov": [{"page_no": 1, "bbox": {"l": 0, "t": 700, "r": 500, "b": 720}}],
        },
        # Internal labels — children of #/pictures/0.
        {
            "self_ref": "#/texts/1",
            "parent": {"$ref": "#/pictures/0"},
            "label": "text",
            "text": "Parse",
            "prov": [{"page_no": 1, "bbox": {"l": 100, "t": 200, "r": 130, "b": 220}}],
        },
        {
            "self_ref": "#/texts/2",
            "parent": {"$ref": "#/pictures/0"},
            "label": "text",
            "text": "Build",
            "prov": [{"page_no": 1, "bbox": {"l": 140, "t": 200, "r": 170, "b": 220}}],
        },
        {
            "self_ref": "#/texts/3",
            "parent": {"$ref": "#/pictures/0"},
            "label": "text",
            "text": "Enrich",
            "prov": [{"page_no": 1, "bbox": {"l": 180, "t": 200, "r": 220, "b": 220}}],
        },
    ],
    "tables": [],
    "pictures": [
        {
            "self_ref": "#/pictures/0",
            "parent": {"$ref": "#/body"},
            "label": "picture",
            "children": [
                {"$ref": "#/texts/1"},
                {"$ref": "#/texts/2"},
                {"$ref": "#/texts/3"},
            ],
            "captions": [{"$ref": "#/texts/0"}],
            "prov": [{"page_no": 1, "bbox": {"l": 90, "t": 100, "r": 510, "b": 600}}],
        }
    ],
    "groups": [],
}


async def test_picture_internal_labels_are_skipped(neo4j_driver):
    await bootstrap_schema(neo4j_driver)
    doc_json = json.dumps(PICTURE_FIXTURE)

    result = await write_document(
        neo4j_driver,
        doc_id="doc-pic",
        filename="figure.pdf",
        document_json=doc_json,
    )

    # Caption + picture only — the 3 internal labels are skipped.
    assert result.elements_written == 2

    async with neo4j_driver.driver.session(database=neo4j_driver.database) as s:
        for child_ref in ("#/texts/1", "#/texts/2", "#/texts/3"):
            assert (
                await _count(
                    s,
                    "MATCH (e:Element {doc_id: $id, self_ref: $ref}) RETURN count(e) AS n",
                    id="doc-pic",
                    ref=child_ref,
                )
                == 0
            ), f"Picture child {child_ref} should be skipped"

        # Picture stays a :Figure node with its own prov.
        assert (
            await _count(
                s,
                "MATCH (e:Element:Figure {doc_id: $id, self_ref: '#/pictures/0'}) "
                "RETURN count(e) AS n",
                id="doc-pic",
            )
            == 1
        )

        # No PARENT_OF from the picture to its dropped children.
        assert (
            await _count(
                s,
                "MATCH (:Element {doc_id: $id, self_ref: '#/pictures/0'})-[:PARENT_OF]->"
                "(:Element) RETURN count(*) AS n",
                id="doc-pic",
            )
            == 0
        )
