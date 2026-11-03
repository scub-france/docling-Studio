"""Graph API — returns a cytoscape-shaped view of the document structure.

`/graph` reads from the graph store (Neo4j): a rich graph (elements + chunks
+ pages + merges) requiring the Maintain step (IngestionPipeline) to have run
for the document.

The endpoint is a thin shim over `GraphService` — the router serializes the
domain `GraphPayload` into `GraphResponse`; the service's typed errors (404,
413, 503) reach the app-level handler (`api/errors.py`). No infra imports
(#audit-01).
"""

from __future__ import annotations

import logging
from typing import ClassVar, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from api import deps  # noqa: TC001
from api.schemas import ProvidedKeysModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["graph"])


class GraphProvenance(ProvidedKeysModel):
    """One provenance of an element — a page and a box on it, in order."""

    order: int | None = None
    page_no: int | None = None
    bbox_l: int | float | None = None
    bbox_t: int | float | None = None
    bbox_r: int | float | None = None
    bbox_b: int | float | None = None
    coord_origin: str | None = None
    charspan_start: int | None = None
    charspan_end: int | None = None


class GraphNode(ProvidedKeysModel):
    """One cytoscape node: the fields `infra/neo4j/queries.py` emits, by group.

    Typed instead of `extra="allow"` (#audit-07). A node carries its own
    group's keys only, as the adapter built it; `label` (an element's Neo4j
    label) is on every node, `null` off elements, as it always was.
    """

    always_emitted: ClassVar[frozenset[str]] = frozenset({"label"})

    id: str
    group: Literal["document", "element", "page", "chunk"]
    label: str | None = None
    # document, element, page
    doc_id: str | None = None
    # document
    title: str | None = None
    stages_applied: list[str] | None = None
    # element
    docling_label: str | None = None
    self_ref: str | None = None
    level: int | None = None
    prov_page: int | None = None
    provs: list[GraphProvenance] | None = None
    # element, chunk (both cut to 200 characters)
    text: str | None = None
    # page
    page_no: int | None = None
    width: int | float | None = None
    height: int | float | None = None
    # chunk
    chunk_index: int | None = None
    token_count: int | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    order: int | None = None


class GraphResponse(BaseModel):
    doc_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    node_count: int
    edge_count: int
    truncated: bool
    page_count: int


def _to_response(payload) -> GraphResponse:
    return GraphResponse(
        doc_id=payload.doc_id,
        nodes=[GraphNode(**n) for n in payload.nodes],
        edges=[GraphEdge(**e) for e in payload.edges],
        node_count=payload.node_count,
        edge_count=payload.edge_count,
        truncated=payload.truncated,
        page_count=payload.page_count,
    )


@router.get("/{doc_id}/graph", response_model=GraphResponse)
async def get_document_graph(doc_id: str, service: deps.GraphServiceDep) -> GraphResponse:
    payload = await service.fetch_document_graph(doc_id)
    return _to_response(payload)
