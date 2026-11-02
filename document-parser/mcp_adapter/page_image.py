"""A page raster as the two cards receive it — never as a model does.

Shared by the citation card (`get_citation_image`) and the sources card
(`get_source_page`): both fetch pages through an app-only tool, and both draw
the passage box from the same `highlight` contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.navigation import CitationImage


@dataclass(frozen=True)
class CitationImageOut:
    """A raster for the viewer, never for the model.

    `highlight` is the cited passage's box **in this image's own pixels** —
    the renderer knows the dpi it settled on, so the view draws a rectangle
    instead of converting page points. Present on a page thumbnail, absent on
    a crop, which is already the passage.
    """

    data_uri: str
    media_type: str
    width: int
    height: int
    page: int
    bytes: int
    highlight: list[int] | None = None
    page_count: int | None = None


def image_out(image: CitationImage) -> CitationImageOut:
    return CitationImageOut(
        data_uri=image.data_uri,
        media_type=image.media_type,
        width=image.width,
        height=image.height,
        page=image.page,
        bytes=len(image.png),
        highlight=list(image.highlight) if image.highlight else None,
        page_count=image.page_count,
    )
