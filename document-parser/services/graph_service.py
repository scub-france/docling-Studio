"""Graph service — orchestrates the two graph projections exposed by the API.

Routes `/api/documents/{id}/graph` (read from the graph store) and
`/api/documents/{id}/reasoning-graph` (project from the SQLite
`document_json` blob) both need the same `GraphPayload` shape but pull
it from different sources. This service hides that fan-out from the API
layer so `api/graph.py` stops reaching into `infra/` directly (#audit-01).

The wire-shape conversion is owned by the adapters: `Neo4jGraphReader`
already returns a `GraphPayload`; `DoclingGraphProjector.project`
returns one too. The service only carries the orchestration (resolve
the latest analysis for the reasoning-graph case) and the not-found /
truncated bookkeeping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.ports import (
        AnalysisRepository,
        DocumentGraphProjector,
        GraphReader,
    )
    from domain.value_objects import GraphPayload


_DEFAULT_MAX_PAGES = 200


class GraphServiceError(Exception):
    """Base error for graph-service rejections, carrying an HTTP-status hint."""

    http_status: int = 500

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class GraphStoreNotConfiguredError(GraphServiceError):
    """Raised when /graph is called but no `GraphReader` is wired in."""

    http_status = 503


class GraphNotFoundError(GraphServiceError):
    """Raised when no graph projection exists for the requested doc."""

    http_status = 404


class GraphTooLargeError(GraphServiceError):
    """Raised when the graph would exceed the per-doc page cap."""

    http_status = 413

    def __init__(self, page_count: int, max_pages: int) -> None:
        super().__init__(f"Graph too large: document has {page_count} pages (cap {max_pages}).")
        self.page_count = page_count
        self.max_pages = max_pages


@dataclass(frozen=True)
class GraphServiceConfig:
    """Per-instance tunables. `max_pages` is the cap design §8.4 enforces."""

    max_pages: int = _DEFAULT_MAX_PAGES


class GraphService:
    """Orchestrates the two graph projections exposed by the API."""

    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        *,
        graph_reader: GraphReader | None = None,
        graph_projector: DocumentGraphProjector,
        config: GraphServiceConfig | None = None,
    ) -> None:
        self._analyses = analysis_repo
        self._reader = graph_reader
        self._projector = graph_projector
        self._config = config or GraphServiceConfig()

    async def fetch_document_graph(self, doc_id: str) -> GraphPayload:
        """Return the rich Neo4j-backed graph (elements + chunks + pages).

        Raises:
            GraphStoreNotConfiguredError: no `GraphReader` is wired in
                (Neo4j not configured on this deployment).
            GraphNotFoundError: the document is unknown to the graph store
                (Maintain step hasn't run yet).
            GraphTooLargeError: the graph would exceed the page cap.
        """
        if self._reader is None:
            raise GraphStoreNotConfiguredError("Graph store is not configured")
        payload = await self._reader.fetch(doc_id, max_pages=self._config.max_pages)
        if payload is None:
            raise GraphNotFoundError(f"No graph for document {doc_id}")
        if payload.truncated:
            raise GraphTooLargeError(payload.page_count, self._config.max_pages)
        return payload

    async def project_reasoning_graph(self, doc_id: str) -> GraphPayload:
        """Build a graph view from the SQLite `document_json` blob.

        Used by the reasoning-trace viewer — no Neo4j dependency, lighter
        graph (no chunks / DERIVED_FROM edges) but enough structure to
        overlay reasoning iterations onto.

        Raises:
            GraphNotFoundError: no completed analysis carries
                `document_json` for this document.
            GraphTooLargeError: same cap as `fetch_document_graph`.
        """
        latest = await self._analyses.find_latest_completed_by_document(doc_id)
        if latest is None or not latest.document_json:
            raise GraphNotFoundError(f"No completed analysis with document_json for {doc_id}")
        payload = self._projector.project(
            latest.document_json,
            doc_id=doc_id,
            title=latest.document_filename or doc_id,
            max_pages=self._config.max_pages,
        )
        if payload.truncated:
            raise GraphTooLargeError(payload.page_count, self._config.max_pages)
        return payload
