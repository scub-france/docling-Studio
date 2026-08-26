"""Rendering the page region a citation points at.

The visual counterpart of verification: instead of asserting that a quote is
in the document, it shows where. A crop, not a page — the crop is the
evidence, and a full page at a readable dpi is an order of magnitude more
bytes than a tool result should carry.

The rasterising itself is infrastructure and reaches this service through the
`PageRasterizer` port. What stays here is policy: which box to ask for, and
how far to climb down the dpi ladder before the result fits the byte budget.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import TYPE_CHECKING

from domain.anchors import DocumentAnchor
from domain.element_reader import resolve
from domain.navigation import CitationImage
from services.navigation_errors import InvalidArgumentError, RefNotFoundError

if TYPE_CHECKING:
    from domain.navigation import BoundingBox
    from domain.ports import PageRasterizer
    from services.navigation_config import NavigationConfig
    from services.parse_loader import ParseLoader

logger = logging.getLogger(__name__)


class CitationImageService:
    def __init__(
        self,
        *,
        parses: ParseLoader,
        rasterizer: PageRasterizer,
        config: NavigationConfig,
    ) -> None:
        self._parses = parses
        self._raster = rasterizer
        self._config = config

    async def render(
        self,
        uri: str,
        *,
        padding: int = 8,
        dpi: int | None = None,
    ) -> CitationImage:
        """Rasterise the page region the anchor at `uri` points at."""
        anchor = DocumentAnchor.parse(uri)
        parse = await self._parses.load(anchor.document_id, anchor.version_id)
        element = resolve(parse.index, anchor.ref)
        if element is None:
            raise RefNotFoundError(
                f"Ref {anchor.ref!r} does not exist in version {parse.version_id}."
            )
        if element.bbox is None or element.page is None:
            raise InvalidArgumentError(
                f"{anchor.ref} carries no page coordinates, so there is nothing to show. "
                "Only elements with provenance can be rendered."
            )
        if not parse.document.storage_path:
            raise InvalidArgumentError(
                f"Document {parse.document.id} has no stored file to render."
            )

        return await asyncio.to_thread(
            self._crop,
            parse.document.storage_path,
            element.bbox,
            padding=padding,
            dpi=min(dpi or self._config.image_dpi, self._config.image_dpi),
        )

    def _crop(
        self,
        storage_path: str,
        bbox: BoundingBox,
        *,
        padding: int,
        dpi: int,
    ) -> CitationImage:
        """Render, crop, and shrink until the result fits the byte budget.

        Blocking on purpose — rasterising a PDF page is CPU work — and called
        through `asyncio.to_thread` so the event loop keeps serving.
        """
        budget = self._config.image_max_bytes
        current = dpi
        while True:
            page_png = self._raster.render_page(storage_path, page=bbox.page, dpi=current)
            crop = self._raster.crop(page_png, bbox.pixel_box(dpi=current, padding=padding))
            if len(crop.png) <= budget or current <= self._config.image_min_dpi:
                encoded = base64.b64encode(crop.png).decode("ascii")
                return CitationImage(
                    png=crop.png,
                    data_uri=f"data:image/png;base64,{encoded}",
                    width=crop.width,
                    height=crop.height,
                    page=bbox.page,
                    dpi=current,
                )
            # Overshoot deliberately: PNG size falls roughly with the pixel
            # count, so halving the dpi quarters the bytes and one or two
            # rounds converge instead of a long descent.
            current = max(self._config.image_min_dpi, current // 2)
