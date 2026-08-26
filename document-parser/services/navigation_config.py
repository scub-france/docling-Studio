"""Budgets for the document-agent surface — one place, three consumers.

Every value is a server-side ceiling: a client argument may lower it, never
raise it. Kept in its own module because the parse loader, the navigation
service, the citation service and the image service all read from it, and a
config that lived inside one of them would make the others import a peer for
its constants.
"""

from __future__ import annotations

from dataclasses import dataclass


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

    # --- raster crops for the citation view ------------------------------
    # The byte budget is the real constraint: a crop travels inside a tool
    # result, and hosts stop hydrating an app when the result gets large, so
    # the image is downscaled until it fits rather than sent at full size.
    image_dpi: int = 150
    image_max_bytes: int = 45_000
    image_min_dpi: int = 40
