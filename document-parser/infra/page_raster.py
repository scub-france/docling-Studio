"""PDF page rasterisation — the `PageRasterizer` port's adapter.

Everything poppler and PIL know how to do, and nothing about why. The dpi
ladder, the byte budget and the bounding-box arithmetic that drive this live
in the services and domain layers; here a page is rendered at the dpi it is
asked for and a PNG is cropped to the box it is given.

Reads the file itself so no caller above `infra/` has to touch the
filesystem — the service passes a `storage_path` from the `Document` entity
and gets bytes back.
"""

from __future__ import annotations

import io
from pathlib import Path

from pdf2image import convert_from_bytes

from domain.navigation import RasterCrop


class PdfPageRasterizer:
    """Stateless adapter for the `PageRasterizer` port."""

    def render_page(self, storage_path: str, *, page: int, dpi: int) -> bytes:
        content = Path(storage_path).read_bytes()
        images = convert_from_bytes(content, first_page=page, last_page=page, dpi=dpi)
        if not images:
            raise ValueError(f"Page {page} not found in {storage_path}")
        buffer = io.BytesIO()
        images[0].save(buffer, format="PNG")
        return buffer.getvalue()

    def crop(
        self,
        png: bytes,
        box: tuple[int, int, int, int],
        *,
        fmt: str = "PNG",
    ) -> RasterCrop:
        from PIL import Image

        image = Image.open(io.BytesIO(png))
        left, top, right, bottom = box
        # Clamp to the raster: a box computed from page points can fall off
        # the rendered image by a pixel or two, and a zero-or-negative crop
        # raises deep inside PIL rather than returning something useful.
        clamped = (
            max(0, min(left, image.width - 1)),
            max(0, min(top, image.height - 1)),
            min(max(right, min(left, image.width - 1) + 1), image.width),
            min(max(bottom, min(top, image.height - 1) + 1), image.height),
        )
        cropped = image.crop(clamped)
        buffer = io.BytesIO()
        if fmt.upper() == "WEBP":
            # Half the bytes of PNG on rendered text, and a third of them on a
            # scaled-down page — PNG is lossless per pixel, which is exactly
            # the wrong trade for an image nobody will pixel-peep.
            cropped.convert("RGB").save(buffer, format="WEBP", quality=78, method=6)
        else:
            cropped.save(buffer, format="PNG", optimize=True)
        return RasterCrop(png=buffer.getvalue(), width=cropped.width, height=cropped.height)
