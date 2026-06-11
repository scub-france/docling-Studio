"""Graph service — serves the document graph projection exposed by the API.

`/api/documents/{id}/graph` reads from the graph store (Neo4j) and needs a
`GraphPayload`. This service hides the source from the API layer so
`api/graph.py` stops reaching into `infra/` directly (#audit-01).

The wire-shape conversion is owned by the adapter: `Neo4jGraphReader` already
returns a `GraphPayload`. The service only carries the not-found / truncated
bookkeeping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.ports import GraphReader
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
    """Serves the Neo4j-backed document graph projection exposed by `/graph`."""

    def __init__(
        self,
        *,
        graph_reader: GraphReader | None = None,
        config: GraphServiceConfig | None = None,
    ) -> None:
        self._reader = graph_reader
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
