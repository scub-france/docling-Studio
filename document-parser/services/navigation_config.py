"""Budgets for the document-agent surface — one place, every consumer.

Every value is a server-side ceiling: a client argument may lower it, never
raise it. Kept in its own module because the parse loader, the navigation
service, the citation service and the image service all read from it, and a
config that lived inside one of them would make the others import a peer for
its constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.mcp_config import McpRuntimeConfig

# The Chunkless RAG loop's round cap: one section read per round, at most this
# many before answering with what was found. The same default as Studio's own
# loop (`REASONING_MAX_ITERATIONS`, docling-agent's `max_iterations`), so the
# two runners of one idea stop at the same point. The prompt states it and the
# sources card counts against it; nothing enforces it server-side — the server
# is stateless and the client model drives the loop. A default only:
# `MCP_MAX_ROUNDS` and the admin panel (#364) override it.
MAX_ROUNDS = 5


@dataclass(frozen=True)
class NavigationConfig:
    studio_base_url: str = ""
    default_read_tokens: int = 1200
    max_read_tokens: int = 4000
    max_outline_nodes: int = 200
    max_documents: int = 50

    # --- parse index cache ---------------------------------------------
    # A parse is immutable for a given analysis id, so a cached index can
    # never go stale; both bounds exist because it is large. `size` caps the
    # entries, `max_chars` caps the source JSON they were built from — the
    # only cheap proxy for retained memory, and an under-estimate of it: a
    # built index retains several times its JSON (measured 4-15x depending on
    # element density). An operator sizing a worker should budget from
    # `max_chars` times that factor, not from `size`.
    index_cache_size: int = 4
    index_cache_max_chars: int = 24_000_000

    # --- page rasters for the viewers ------------------------------------
    # A raster never travels in a tool result — a viewer fetches it through
    # an app-only tool — so it is bounded by what a host will hold in an
    # iframe: wide enough to read when enlarged, small enough that a dense
    # scan cannot hand back megabytes. Halved from `image_dpi` until it fits.
    image_dpi: int = 150
    image_min_dpi: int = 40
    image_page_max_bytes: int = 400_000

    # --- show_sources ----------------------------------------------------
    # The anchors one answer reads and cites: a handful in practice, bounded
    # so a runaway list cannot turn one call into a full-document walk. The
    # question and each `why` are a sentence or two, stored nowhere.
    max_source_anchors: int = 50
    max_source_text_chars: int = 2_000
    max_rounds: int = MAX_ROUNDS

    @classmethod
    def from_runtime(cls, runtime: McpRuntimeConfig) -> NavigationConfig:
        """The budgets for the runtime-configurable knobs (#364); the rest
        keep their defaults."""
        return cls(
            studio_base_url=runtime.studio_base_url,
            max_read_tokens=runtime.max_read_tokens,
            max_rounds=runtime.max_rounds,
        )
