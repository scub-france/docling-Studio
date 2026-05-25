"""Remote Docling Serve converter — delegates conversion via HTTP.

This adapter implements the DocumentConverter port by calling a remote
Docling Serve instance's REST API (v1).

API contract based on docling-serve source code:
- Options are sent as individual multipart form fields (not a JSON blob)
- Response contains document.md_content, document.html_content, document.json_content
- json_content is a serialized DoclingDocument with texts[], tables[], pictures[]
- Bounding boxes use {l, t, r, b, coord_origin} format
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
from pathlib import Path

import httpx
from docling_core.types.doc.base import BoundingBox, CoordOrigin

from domain.value_objects import (
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    ConversionOptions,
    ConversionResult,
    PageDetail,
    PageElement,
)
from infra.bbox import to_topleft_list

logger = logging.getLogger(__name__)

_API_PREFIX = "/v1"

# Docling Serve label → our element type
_LABEL_MAP = {
    "table": "table",
    "picture": "picture",
    "figure": "picture",
    "title": "title",
    "section_header": "section_header",
    "list_item": "list",
    "formula": "formula",
    "code": "code",
    "caption": "text",
    "footnote": "text",
    "page_header": "text",
    "page_footer": "text",
    "paragraph": "text",
    "text": "text",
    "reference": "text",
}


class ServeConverter:
    """Adapter that delegates document conversion to a remote Docling Serve instance."""

    # Docling Serve handles batching server-side; slicing into page batches
    # client-side would just multiply HTTP roundtrips for no benefit, so
    # the orchestrator passes the full document through in a single call.
    supports_page_batching: bool = False

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 600.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["X-Api-Key"] = self._api_key
        return headers

    async def convert(
        self,
        file_path: str,
        options: ConversionOptions,
        *,
        page_range: tuple[int, int] | None = None,
    ) -> ConversionResult:
        """Convert a document by uploading it to Docling Serve.

        The PDF is read into memory through `asyncio.to_thread` so the
        blocking file read never freezes the FastAPI event loop while a
        large document is in flight to Docling Serve.
        """
        path = Path(file_path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

        form_data = _build_form_data(options, page_range=page_range)
        url = f"{self._base_url}{_API_PREFIX}/convert/file"

        file_bytes = await asyncio.to_thread(path.read_bytes)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url,
                files={"files": (path.name, file_bytes, content_type)},
                data=form_data,
                headers=self._headers(),
            )

        if response.status_code >= 400:
            logger.error(
                "Docling Serve error %d: %s (form_data=%s)",
                response.status_code,
                response.text[:500],
                {k: v for k, v in form_data.items()},
            )
        response.raise_for_status()
        result_data = response.json()

        return _parse_response(result_data)

    async def health_check(self) -> bool:
        """Check if Docling Serve is reachable."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._base_url}/version",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            logger.warning("Docling Serve health check failed at %s", self._base_url, exc_info=True)
            return False


def _build_form_data(
    options: ConversionOptions,
    *,
    page_range: tuple[int, int] | None = None,
) -> dict[str, str | list[str]]:
    """Build form fields matching Docling Serve's multipart form contract.

    Serve uses FastAPI's ``Form()`` parsing — list/tuple fields are sent
    as **repeated form keys** (httpx encodes Python lists this way
    automatically: ``to_formats=md&to_formats=html&to_formats=json``).

    Note: ``generate_page_images`` is a PdfPipelineOptions field, NOT a
    ConvertDocumentsOptions field — sending it causes a 422.
    """
    data: dict[str, str | list[str]] = {
        "to_formats": ["md", "html", "json"],
        "do_ocr": str(options.do_ocr).lower(),
        "do_table_structure": str(options.do_table_structure).lower(),
        "table_mode": options.table_mode,
        "do_code_enrichment": str(options.do_code_enrichment).lower(),
        "do_formula_enrichment": str(options.do_formula_enrichment).lower(),
        "do_picture_classification": str(options.do_picture_classification).lower(),
        "do_picture_description": str(options.do_picture_description).lower(),
        "include_images": str(options.generate_picture_images).lower(),
        "images_scale": str(options.images_scale),
    }
    if page_range is not None:
        # Serve expects page_range as two repeated form fields:
        # page_range=1&page_range=10
        data["page_range"] = [str(page_range[0]), str(page_range[1])]
    return data


def _parse_response(data: dict) -> ConversionResult:
    """Parse Docling Serve v1 ConvertDocumentResponse into our domain ConversionResult."""
    document = data.get("document", {})

    content_md = document.get("md_content") or ""
    content_html = document.get("html_content") or ""

    # json_content contains the full DoclingDocument with pages, elements, bboxes
    json_content = document.get("json_content")
    if isinstance(json_content, str):
        try:
            json_content = json.loads(json_content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse json_content as JSON, ignoring structured data")
            json_content = None

    pages: list[PageDetail] = []
    if json_content:
        pages = _extract_pages_from_docling_document(json_content)

    page_count = len(pages) if pages else 1

    document_json = json.dumps(json_content) if json_content else None

    return ConversionResult(
        page_count=page_count,
        content_markdown=content_md,
        content_html=content_html,
        pages=pages,
        document_json=document_json,
    )


def _extract_pages_from_docling_document(doc: dict) -> list[PageDetail]:
    """Extract pages with elements from a serialized DoclingDocument.

    DoclingDocument structure:
    - pages: {page_no: {size: {width, height}}}
    - texts: [{label, text, prov: [{page_no, bbox: {l,t,r,b,coord_origin}}]}]
    - tables: [{label, prov: [...], data: {...}}]
    - pictures: [{label, prov: [...]}]
    """
    pages_dict: dict[int, PageDetail] = {}

    # Build page dimensions
    for page_key, page_data in doc.get("pages", {}).items():
        page_no = int(page_key)
        size = page_data.get("size", {})
        pages_dict[page_no] = PageDetail(
            page_number=page_no,
            width=size.get("width", DEFAULT_PAGE_WIDTH),
            height=size.get("height", DEFAULT_PAGE_HEIGHT),
        )

    # Process all element arrays
    for item in doc.get("texts", []):
        _add_element(item, pages_dict)

    for item in doc.get("tables", []):
        _add_element(item, pages_dict)

    for item in doc.get("pictures", []):
        _add_element(item, pages_dict)

    return sorted(pages_dict.values(), key=lambda p: p.page_number)


def _add_element(item: dict, pages: dict[int, PageDetail]) -> None:
    """Add an element from a DoclingDocument array to the correct page."""
    label = item.get("label", "text")
    element_type = _LABEL_MAP.get(label, "text")
    content = item.get("text", "") or ""

    for prov in item.get("prov", []):
        page_no = prov.get("page_no", 1)
        if page_no not in pages:
            pages[page_no] = PageDetail(
                page_number=page_no,
                width=DEFAULT_PAGE_WIDTH,
                height=DEFAULT_PAGE_HEIGHT,
            )

        bbox_data = prov.get("bbox", {})
        bbox = _extract_bbox(bbox_data, pages[page_no].height)

        pages[page_no].elements.append(
            PageElement(type=element_type, bbox=bbox, content=content, level=0)
        )


def _extract_bbox(bbox_data: dict, page_height: float) -> list[float]:
    """Extract and normalize bbox to TOPLEFT [l, t, r, b] format.

    Delegates to the canonical to_topleft_list function via a docling-core
    BoundingBox, ensuring consistent coordinate handling across all converters.
    """
    if not isinstance(bbox_data, dict):
        return [0.0, 0.0, 0.0, 0.0]

    origin_str = bbox_data.get("coord_origin", "TOPLEFT")
    origin = CoordOrigin.BOTTOMLEFT if origin_str == "BOTTOMLEFT" else CoordOrigin.TOPLEFT

    bbox = BoundingBox(
        l=bbox_data.get("l", 0.0),
        t=bbox_data.get("t", 0.0),
        r=bbox_data.get("r", 0.0),
        b=bbox_data.get("b", 0.0),
        coord_origin=origin,
    )
    return to_topleft_list(bbox, page_height)
