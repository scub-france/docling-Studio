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
from domain.value_objects import DEFAULT_PAGE_WIDTH
from services.navigation_errors import InvalidArgumentError, RefNotFoundError

if TYPE_CHECKING:
    from domain.navigation import BoundingBox, ResolvedElement
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

    async def render_page(self, uri: str, *, max_width: int = 320) -> CitationImage:
        """A thumbnail of the whole page the anchor sits on.

        Same pipeline as the crop, with the box being the page: rendered
        straight at the target width rather than downscaled afterwards, which
        is both faster and sharper. At 320 px a page is ~22 KB of WebP against
        ~108 KB of PNG — the format matters more than the size here, because a
        scaled page is exactly the kind of image PNG encodes badly.
        """
        anchor = DocumentAnchor.parse(uri)
        parse = await self._parses.load(anchor.document_id, anchor.version_id)
        element = resolve(parse.index, anchor.ref)
        if element is None or element.page is None:
            raise RefNotFoundError(f"Ref {anchor.ref!r} has no page in version {parse.version_id}.")
        if not parse.document.storage_path:
            raise InvalidArgumentError(
                f"Document {parse.document.id} has no stored file to render."
            )
        width_pt = (element.bbox.page_width if element.bbox else None) or DEFAULT_PAGE_WIDTH
        dpi = max(24, min(int(max_width / (width_pt / 72.0)), self._config.image_dpi))
        return await asyncio.to_thread(
            self._page_thumbnail,
            parse.document.storage_path,
            element,
            dpi,
            parse.index.page_count or None,
        )

    def _page_thumbnail(
        self,
        storage_path: str,
        element: ResolvedElement,
        dpi: int,
        page_count: int | None,
    ) -> CitationImage:
        def render(at: int):
            page_png = self._raster.render_page(storage_path, page=element.page, dpi=at)
            return self._raster.crop(page_png, (0, 0, 10_000, 10_000), fmt="WEBP")

        crop, at = self._shrink_to_budget(render, dpi=dpi, budget=self._config.image_page_max_bytes)
        # The passage's box in the thumbnail's own pixels, at the dpi the
        # ladder actually settled on — computing it from the dpi that was
        # *asked* for would put the marker somewhere the passage is not.
        highlight = element.bbox.pixel_box(dpi=at, padding=0) if element.bbox else None
        return self._image(
            crop,
            page=element.page,
            dpi=at,
            media_type="image/webp",
            highlight=highlight,
            page_count=page_count,
        )

    def _crop(
        self,
        storage_path: str,
        bbox: BoundingBox,
        *,
        padding: int,
        dpi: int,
    ) -> CitationImage:
        """Render, crop, and shrink until the result fits the byte budget."""

        def render(at: int):
            page_png = self._raster.render_page(storage_path, page=bbox.page, dpi=at)
            return self._raster.crop(page_png, bbox.pixel_box(dpi=at, padding=padding), fmt="WEBP")

        crop, at = self._shrink_to_budget(render, dpi=dpi, budget=self._config.image_max_bytes)
        return self._image(crop, page=bbox.page, dpi=at, media_type="image/webp")

    def _shrink_to_budget(self, render, *, dpi: int, budget: int):
        """Render at `dpi`, halving until the result fits `budget`.

        Blocking on purpose — rasterising a PDF page is CPU work — and called
        through `asyncio.to_thread` so the event loop keeps serving.

        Overshoot deliberately: encoded size falls roughly with the pixel
        count, so halving the dpi quarters the bytes and one or two rounds
        converge instead of a long descent. Returns the dpi it settled on,
        because a caller that projects coordinates onto the raster needs the
        one that was used, not the one that was asked for.
        """
        current = dpi
        while True:
            crop = render(current)
            if len(crop.png) <= budget or current <= self._config.image_min_dpi:
                return crop, current
            current = max(self._config.image_min_dpi, current // 2)

    @staticmethod
    def _image(
        crop,
        *,
        page: int,
        dpi: int,
        media_type: str,
        highlight: tuple[int, int, int, int] | None = None,
        page_count: int | None = None,
    ) -> CitationImage:
        encoded = base64.b64encode(crop.png).decode("ascii")
        return CitationImage(
            png=crop.png,
            data_uri=f"data:{media_type};base64,{encoded}",
            width=crop.width,
            height=crop.height,
            page=page,
            dpi=dpi,
            media_type=media_type,
            highlight=highlight,
            page_count=page_count,
        )
