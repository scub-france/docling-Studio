"""TreeWriter — persist a DoclingDocument as a graph in Neo4j.

v0.5.0 strategy: replace-on-write. For a given doc_id, all existing
Document/Element/Page/Chunk nodes are wiped before re-ingestion. The full
serialized `DoclingDocument` JSON is stored as a property on the Document
node so that `TreeReader` can round-trip it verbatim — reconstruction from
graph nodes is deferred to v0.6 (see docs/design/neo4j-integration.md §2).
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from infra.docling_tree import (
    build_collapse_index,
    get_parent_ref,
    is_inline_group,
    iter_items,
    iter_pages,
    iter_provs,
    list_dfs_order,
    map_element_label,
)

if TYPE_CHECKING:
    from neo4j import AsyncTransaction

    from infra.neo4j.driver import Neo4jDriver

logger = logging.getLogger(__name__)


@dataclass
class TreeWriteResult:
    doc_id: str
    elements_written: int
    pages_written: int
    provenances_written: int = 0


def _build_element_props(item: dict[str, Any], doc_id: str) -> dict[str, Any]:
    """Properties stored on the `:Element` node itself.

    Provenance (page + bbox) is NOT here anymore — see `_iter_provs` and the
    `:Provenance` nodes. Keeping it out of the element matches DoclingDocument's
    own model (`prov` is a list of objects, not a scalar).
    """
    props: dict[str, Any] = {
        "doc_id": doc_id,
        "self_ref": item.get("self_ref") or "",
        "docling_label": (item.get("label") or "").lower(),
        "text": item.get("text") or "",
    }
    # Type-specific extras.
    if "level" in item:
        props["level"] = item.get("level")
    if "caption" in item and isinstance(item.get("caption"), str):
        props["caption"] = item.get("caption")
    if item.get("data") and isinstance(item["data"], dict):
        # Tables carry cell layout under data; stringify to keep the schema flat.
        with contextlib.suppress(TypeError, ValueError):
            props["cells_json"] = json.dumps(item["data"])
    return props


@dataclass(frozen=True)
class _DocumentNode:
    """Properties of the `:Document` node, which carries the verbatim JSON."""

    doc_id: str
    title: str
    document_json: str
    tenant_id: str
    source_uri: str | None
    docling_version: str | None
    ingested_at: str


@dataclass(frozen=True)
class _TreeProjection:
    """Rows projected from a DoclingDocument, ready to UNWIND into Neo4j."""

    doc_id: str
    elements: list[dict[str, Any]]
    provenances: list[dict[str, Any]]
    pages: list[dict[str, Any]]
    reading_order: list[str]


def _build_element_row(
    item: dict[str, Any], doc_id: str, inline_meta: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return the `:Element` row for `item` and the provenance rows it owns."""
    ref = item.get("self_ref")
    specific = map_element_label(item.get("label") or "")
    props = _build_element_props(item, doc_id)
    if is_inline_group(item):
        meta = inline_meta.get(ref, {"text": "", "provs": []})
        props["text"] = meta["text"]
        item_provs = meta["provs"]
    else:
        item_provs = iter_provs(item)
    row = {
        "specific_label": specific,
        "parent_ref": get_parent_ref(item),
        **props,
    }
    return row, item_provs


def _build_tree_projection(doc_data: dict[str, Any], doc_id: str) -> _TreeProjection:
    # Issue #197: collapse two noise patterns from Docling into the projection.
    # InlineGroups (paragraph style runs) are merged into a single :Paragraph,
    # and Pictures' internal text labels (flowchart/diagram/chart annotations)
    # are dropped. Both produce refs that land in `skip_refs`.
    skip_refs, inline_meta = build_collapse_index(doc_data)

    elements: list[dict[str, Any]] = []
    # Parallel list: one row per Provenance — each refers back to its owner
    # element via `self_ref`, so we can batch MATCH-and-link after both node
    # sets are created.
    provenances: list[dict[str, Any]] = []
    for _, item in iter_items(doc_data):
        ref = item.get("self_ref")
        if not ref or ref in skip_refs:
            continue
        element, item_provs = _build_element_row(item, doc_id, inline_meta)
        elements.append(element)
        for prov in item_provs:
            provenances.append({"doc_id": doc_id, "self_ref": ref, **prov})

    pages: list[dict[str, Any]] = [{"doc_id": doc_id, **p} for p in iter_pages(doc_data)]

    reading_order = list_dfs_order(doc_data, skip_refs)
    return _TreeProjection(doc_id, elements, provenances, pages, reading_order)


async def _wipe_document_graph(tx: AsyncTransaction, doc_id: str) -> None:
    await tx.run(
        "MATCH (d:Document {id: $doc_id}) "
        "OPTIONAL MATCH (d)-[:HAS_ROOT|HAS_CHUNK*0..]->(n) "
        "DETACH DELETE d, n",
        doc_id=doc_id,
    )
    # Orphan sweep — covers Provenance/Element/Page/Chunk that may linger
    # from an interrupted write or a pre-refactor schema.
    await tx.run("MATCH (pv:Provenance {doc_id: $doc_id}) DETACH DELETE pv", doc_id=doc_id)
    await tx.run("MATCH (e:Element {doc_id: $doc_id}) DETACH DELETE e", doc_id=doc_id)
    await tx.run("MATCH (p:Page {doc_id: $doc_id}) DETACH DELETE p", doc_id=doc_id)


async def _create_document_node(tx: AsyncTransaction, document: _DocumentNode) -> None:
    await tx.run(
        """
        CREATE (d:Document {
          id: $doc_id,
          title: $title,
          source_uri: $source_uri,
          ingested_at: datetime($ingested_at),
          docling_version: $docling_version,
          stages_applied: ['tree'],
          last_tree_write: datetime($ingested_at),
          tenant_id: $tenant_id,
          document_json: $document_json
        })
        """,
        doc_id=document.doc_id,
        title=document.title,
        source_uri=document.source_uri or "",
        ingested_at=document.ingested_at,
        docling_version=document.docling_version or "",
        tenant_id=document.tenant_id,
        document_json=document.document_json,
    )


async def _create_page_nodes(tx: AsyncTransaction, pages: list[dict[str, Any]]) -> None:
    await tx.run(
        "UNWIND $pages AS p "
        "CREATE (:Page {doc_id: p.doc_id, page_no: p.page_no, "
        "width: p.width, height: p.height})",
        pages=pages,
    )


async def _create_element_nodes(tx: AsyncTransaction, elements: list[dict[str, Any]]) -> None:
    # Dynamic :Element:<specific> labels via APOC-free trick: we split by
    # specific label so each CREATE statement is static (no APOC).
    by_specific: dict[str, list[dict[str, Any]]] = {}
    for e in elements:
        by_specific.setdefault(e["specific_label"], []).append(e)
    for specific, batch in by_specific.items():
        await tx.run(
            f"""
            UNWIND $batch AS e
            CREATE (n:Element:{specific} {{
              doc_id: e.doc_id,
              self_ref: e.self_ref,
              docling_label: e.docling_label,
              text: e.text,
              level: e.level,
              caption: e.caption,
              cells_json: e.cells_json
            }})
            """,
            batch=batch,
        )


async def _link_parents(tx: AsyncTransaction, doc_id: str, elements: list[dict[str, Any]]) -> None:
    """PARENT_OF relations (tree structure), with the order tracked inline."""
    parent_rows = [
        {
            "doc_id": doc_id,
            "parent_ref": e["parent_ref"],
            "child_ref": e["self_ref"],
            "order": idx,
        }
        for idx, e in enumerate(elements)
        if e["parent_ref"] and e["parent_ref"] != "#/body"
    ]
    if parent_rows:
        await tx.run(
            """
            UNWIND $rows AS r
            MATCH (p:Element {doc_id: r.doc_id, self_ref: r.parent_ref})
            MATCH (c:Element {doc_id: r.doc_id, self_ref: r.child_ref})
            MERGE (p)-[rel:PARENT_OF]->(c)
            SET rel.order = r.order
            """,
            rows=parent_rows,
        )


async def _link_roots(tx: AsyncTransaction, doc_id: str, elements: list[dict[str, Any]]) -> None:
    """HAS_ROOT for top-level children of the document body."""
    root_rows = [
        {"doc_id": doc_id, "child_ref": e["self_ref"]}
        for e in elements
        if e["parent_ref"] == "#/body"
    ]
    if root_rows:
        await tx.run(
            """
            UNWIND $rows AS r
            MATCH (d:Document {id: r.doc_id})
            MATCH (c:Element {doc_id: r.doc_id, self_ref: r.child_ref})
            MERGE (d)-[:HAS_ROOT]->(c)
            """,
            rows=root_rows,
        )


async def _create_provenance_nodes(tx: AsyncTransaction, provenances: list[dict[str, Any]]) -> None:
    # One per (element, prov-entry) pair. Mirrors Docling's
    # `item.prov = list[ProvenanceItem]` 1:1 so a single item that spans page
    # breaks (or appears twice in the layout) keeps every (page, bbox,
    # charspan) without losing data.
    await tx.run(
        """
        UNWIND $rows AS r
        MATCH (e:Element {doc_id: r.doc_id, self_ref: r.self_ref})
        CREATE (pv:Provenance {
          doc_id: r.doc_id,
          element_ref: r.self_ref,
          prov_order: r.order,
          page_no: r.page_no,
          bbox_l: r.bbox_l,
          bbox_t: r.bbox_t,
          bbox_r: r.bbox_r,
          bbox_b: r.bbox_b,
          coord_origin: r.coord_origin,
          charspan_start: r.charspan_start,
          charspan_end: r.charspan_end
        })
        CREATE (e)-[:HAS_PROV {order: r.order}]->(pv)
        """,
        rows=provenances,
    )


async def _link_provenances_to_pages(
    tx: AsyncTransaction, provenances: list[dict[str, Any]]
) -> None:
    # ON_PAGE attaches the Provenance to its Page — lets downstream
    # queries ("what's on page 3?") stay simple without walking through
    # the Element. A Provenance with no page_no (rare) yields no edge.
    await tx.run(
        """
        UNWIND $rows AS r
        WITH r WHERE r.page_no IS NOT NULL
        MATCH (pv:Provenance {
          doc_id: r.doc_id,
          element_ref: r.self_ref,
          prov_order: r.order
        })
        MATCH (p:Page {doc_id: r.doc_id, page_no: r.page_no})
        MERGE (pv)-[:ON_PAGE]->(p)
        """,
        rows=provenances,
    )


async def _link_reading_order(tx: AsyncTransaction, doc_id: str, reading_order: list[str]) -> None:
    """NEXT chain in DFS pre-order."""
    pairs = [
        {"doc_id": doc_id, "a": reading_order[i], "b": reading_order[i + 1]}
        for i in range(len(reading_order) - 1)
    ]
    await tx.run(
        """
        UNWIND $pairs AS p
        MATCH (a:Element {doc_id: p.doc_id, self_ref: p.a})
        MATCH (b:Element {doc_id: p.doc_id, self_ref: p.b})
        MERGE (a)-[:NEXT]->(b)
        """,
        pairs=pairs,
    )


async def _write_tree(
    tx: AsyncTransaction, document: _DocumentNode, projection: _TreeProjection
) -> None:
    # Replace strategy: wipe the existing graph for this doc_id first.
    await _wipe_document_graph(tx, projection.doc_id)
    await _create_document_node(tx, document)
    if projection.pages:
        await _create_page_nodes(tx, projection.pages)
    await _create_element_nodes(tx, projection.elements)
    await _link_parents(tx, projection.doc_id, projection.elements)
    await _link_roots(tx, projection.doc_id, projection.elements)
    if projection.provenances:
        await _create_provenance_nodes(tx, projection.provenances)
        await _link_provenances_to_pages(tx, projection.provenances)
    if len(projection.reading_order) > 1:
        await _link_reading_order(tx, projection.doc_id, projection.reading_order)


async def write_document(
    neo: Neo4jDriver,
    *,
    doc_id: str,
    filename: str,
    document_json: str,
    tenant_id: str = "default",
    source_uri: str | None = None,
    docling_version: str | None = None,
) -> TreeWriteResult:
    """Persist the full DoclingDocument tree to Neo4j.

    Idempotent: wipes any existing graph for doc_id before writing.
    Fails fast (exception propagates) if Neo4j is unavailable — per design §8.5.
    """
    doc_data = json.loads(document_json)
    document = _DocumentNode(
        doc_id=doc_id,
        title=filename,
        document_json=document_json,
        tenant_id=tenant_id,
        source_uri=source_uri,
        docling_version=docling_version,
        ingested_at=datetime.now(tz=UTC).isoformat(),
    )
    projection = _build_tree_projection(doc_data, doc_id)
    async with (
        neo.driver.session(database=neo.database) as session,
        await session.begin_transaction() as tx,
    ):
        await _write_tree(tx, document, projection)
        await tx.commit()
    logger.info(
        "Neo4j: wrote doc %s (%d elements, %d pages, %d provenances)",
        doc_id,
        len(projection.elements),
        len(projection.pages),
        len(projection.provenances),
    )
    return TreeWriteResult(
        doc_id=doc_id,
        elements_written=len(projection.elements),
        pages_written=len(projection.pages),
        provenances_written=len(projection.provenances),
    )
