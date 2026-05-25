"""Graph API — returns a cytoscape-shaped view of the document structure.

Two endpoints:
- `/graph` — read from the graph store (Neo4j). Rich graph (elements +
  chunks + pages + merges). Requires the Maintain step
  (IngestionPipeline) to have run for the document.
- `/reasoning-graph` — built on-the-fly from the SQLite `document_json`
  blob. No graph-store dependency. Lighter graph (no chunks) but enough
  to render the reasoning-trace overlay on top of `GraphView`.

Both endpoints are thin shims over `GraphService` — the router only
translates between domain errors and HTTP status codes, and serializes
the domain `GraphPayload` into the camelCase-friendly `GraphResponse`.
No infra imports (#audit-01).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services.graph_service import GraphService, GraphServiceError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["graph"])


class GraphNode(BaseModel):
    id: str
    group: str
    label: str | None = None

    model_config = {"extra": "allow"}


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


def _service(request: Request) -> GraphService:
    """Resolve `GraphService` from the app state, 500-ing if unwired."""
    svc = getattr(request.app.state, "graph_service", None)
    if svc is None:
        raise HTTPException(status_code=500, detail="GraphService not wired")
    return svc


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
async def get_document_graph(doc_id: str, request: Request) -> GraphResponse:
    try:
        payload = await _service(request).fetch_document_graph(doc_id)
    except GraphServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return _to_response(payload)


@router.get("/{doc_id}/reasoning-graph", response_model=GraphResponse)
async def get_reasoning_graph(doc_id: str, request: Request) -> GraphResponse:
    """Graph projection built from SQLite `document_json` — no Neo4j needed.

    Serves the reasoning-trace viewer, which only needs the element/page/edge
    structure to overlay iterations onto.
    """
    try:
        payload = await _service(request).project_reasoning_graph(doc_id)
    except GraphServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return _to_response(payload)
