"""Build a Cytoscape-shaped graph payload straight from a serialized
`DoclingDocument` (i.e. the `document_json` blob stored in SQLite).

Mirrors `infra.neo4j.queries.fetch_graph` so the frontend can reuse the same
`GraphView` component — the only intentional difference is the absence of
Chunk nodes / HAS_CHUNK / DERIVED_FROM edges, since chunks are a product of
the Maintain step and don't exist in `document_json` alone.

Used by the reasoning-trace viewer, which needs the structural graph to
overlay iterations onto but does NOT need (and should not require) Neo4j.
"""

from __future__ import annotations

import json
from itertools import pairwise
from typing import Any

from infra.docling_tree import (
    build_collapse_index,
    dfs_order,
    element_label,
    is_inline_group,
    iter_items,
    iter_pages,
    iter_provs,
    parent_ref,
)
from infra.neo4j.queries import GraphPayload


def _element_node(
    doc_id: str,
    item: dict[str, Any],
    provs: list[dict[str, Any]],
    *,
    text_override: str | None = None,
) -> dict[str, Any]:
    first_page = provs[0].get("page_no") if provs else None
    raw_text = text_override if text_override is not None else (item.get("text") or "")
    return {
        "id": f"elem::{item.get('self_ref')}",
        "group": "element",
        "label": element_label(item.get("label") or ""),
        "docling_label": (item.get("label") or "").lower(),
        "self_ref": item.get("self_ref"),
        "text": raw_text[:200],
        "prov_page": first_page,
        "provs": provs,
        "level": item.get("level"),
        "doc_id": doc_id,
    }


def _page_node(doc_id: str, page: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"page::{page.get('page_no')}",
        "group": "page",
        "page_no": page.get("page_no"),
        "width": page.get("width"),
        "height": page.get("height"),
        "doc_id": doc_id,
    }


def _edge(source: str, target: str, edge_type: str, *, order: int | None = None) -> dict[str, Any]:
    return {
        "id": f"{edge_type}::{source}::{target}",
        "source": source,
        "target": target,
        "type": edge_type,
        "order": order,
    }


def build_graph_payload(
    document_json: str,
    *,
    doc_id: str,
    title: str | None = None,
    max_pages: int = 200,
) -> GraphPayload:
    """Build a `GraphPayload` equivalent to `fetch_graph(neo4j, doc_id)` from
    the raw `DoclingDocument` JSON.

    Returns `truncated=True` with empty node/edge lists beyond `max_pages`, so
    the caller can mirror the Neo4j endpoint's 413 behavior.
    """
    doc_data = json.loads(document_json)

    pages_raw = list(iter_pages(doc_data))
    page_count = len(pages_raw)
    if page_count > max_pages:
        return GraphPayload(
            doc_id=doc_id,
            nodes=[],
            edges=[],
            node_count=0,
            edge_count=0,
            truncated=True,
            page_count=page_count,
        )

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    doc_node_id = f"doc::{doc_id}"
    nodes.append(
        {
            "id": doc_node_id,
            "group": "document",
            "doc_id": doc_id,
            "title": title,
            # `stages_applied` is a Neo4j-only artifact; keep the key present
            # for shape parity but leave it empty since SQLite doesn't track it.
            "stages_applied": [],
        }
    )

    # Page nodes.
    for p in pages_raw:
        nodes.append(_page_node(doc_id, p))

    # Issue #197: collapse Docling noise — InlineGroup style runs and the
    # internal text labels Docling extracts from pictures/charts.
    skip_refs, inline_meta = build_collapse_index(doc_data)

    # Element nodes + collect parent/body metadata for edges below. The
    # `element_idx` mirrors TreeWriter's `enumerate(elements)` so PARENT_OF
    # carries the same `order` the Neo4j projection does.
    by_ref: dict[str, dict[str, Any]] = {}
    element_idx = 0
    for _, item in iter_items(doc_data):
        ref = item.get("self_ref")
        if not ref or ref in skip_refs:
            continue
        by_ref[ref] = item
        if is_inline_group(item):
            meta = inline_meta.get(ref, {"text": "", "provs": []})
            provs = meta["provs"]
            text_override: str | None = meta["text"]
        else:
            provs = iter_provs(item)
            text_override = None
        nodes.append(_element_node(doc_id, item, provs, text_override=text_override))

        pref = parent_ref(item)
        if pref == "#/body":
            edges.append(_edge(doc_node_id, f"elem::{ref}", "HAS_ROOT"))
        elif pref:
            edges.append(_edge(f"elem::{pref}", f"elem::{ref}", "PARENT_OF", order=element_idx))

        # ON_PAGE, dedup'd per (element, page) — matches the Neo4j query's
        # DISTINCT projection through Provenance.
        seen_pages: set[int] = set()
        for prov in provs:
            page_no = prov.get("page_no")
            if page_no is None or page_no in seen_pages:
                continue
            seen_pages.add(page_no)
            edges.append(_edge(f"elem::{ref}", f"page::{page_no}", "ON_PAGE"))

        element_idx += 1

    # NEXT chain (DFS pre-order from body), inline-group children skipped.
    for a, b in pairwise(dfs_order(doc_data, skip_refs)):
        if a in by_ref and b in by_ref:
            edges.append(_edge(f"elem::{a}", f"elem::{b}", "NEXT"))

    return GraphPayload(
        doc_id=doc_id,
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
        truncated=False,
        page_count=page_count,
    )


# ---------------------------------------------------------------------------
# Adapter class — implements `domain.ports.DocumentGraphProjector`
# (#audit-01). Thin shim around `build_graph_payload` so the GraphService
# can depend on the port without reaching into infra.
# ---------------------------------------------------------------------------


class DoclingGraphProjector:
    """Stateless adapter for the `DocumentGraphProjector` port."""

    def project(
        self,
        document_json: str,
        *,
        doc_id: str,
        title: str | None = None,
        max_pages: int = 200,
    ) -> GraphPayload:
        return build_graph_payload(
            document_json,
            doc_id=doc_id,
            title=title,
            max_pages=max_pages,
        )
