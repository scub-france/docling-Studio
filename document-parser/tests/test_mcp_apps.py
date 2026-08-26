"""Tests for the MCP Apps extension — the citation viewer.

Three layers: the pure coordinate projection, the service that rasterises a
citation, and the tool contract as an MCP client sees it. The client tests run
twice — once as a host that negotiated `io.modelcontextprotocol/ui` and once as
one that did not — because the whole design rests on those two answers
differing in exactly one field.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from unittest.mock import patch

import pytest

from domain.navigation import BoundingBox

pytest.importorskip(
    "mcp.server.apps",
    reason="MCP SDK not installed — `uv sync --group mcp` to exercise the Apps extension",
)

from contextlib import asynccontextmanager

from mcp import Client
from mcp.client.extension import advertise
from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID

from mcp_adapter import build_mcp_server
from mcp_adapter.apps import CITATION_APP_HTML, CITATION_APP_URI
from services.navigation_service import (
    InvalidArgumentError,
    NavigationConfig,
    RefNotFoundError,
)
from tests.navigation_fixtures import (
    PREAVIS_REF,
    anchor_uri,
    make_document,
    make_navigation_service,
)

APPS_CLIENT = advertise(EXTENSION_ID, {"mimeTypes": [APP_MIME_TYPE]})


def _png(width: int = 1275, height: int = 1650) -> bytes:
    """A blank page raster standing in for poppler's output."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@asynccontextmanager
async def _client(service, *, apps: bool = True, negotiates: bool = False):
    server = build_mcp_server(lambda: service, version="test", apps=apps)
    async with Client(server, extensions=[APPS_CLIENT] if negotiates else None) as client:
        yield client


def _service_with_file(tmp_path: Path, **kwargs):
    """A navigation service whose document points at a real file on disk."""
    pdf = tmp_path / "contrat.pdf"
    pdf.write_bytes(b"%PDF-1.4 not really a pdf")
    document = make_document()
    document.storage_path = str(pdf)
    return make_navigation_service(documents=[document], **kwargs)


class TestPixelProjection:
    def test_topleft_scales_by_dpi(self):
        box = BoundingBox(page=1, left=72, top=100, right=172, bottom=200, page_height=792)
        assert box.pixel_box(dpi=144, padding=0) == (144, 200, 344, 400)

    def test_bottomleft_is_flipped_through_the_page_height(self):
        # y grows upwards: `top` is the larger number, and the crop needs the
        # distance from the top edge instead.
        box = BoundingBox(
            page=1,
            left=72,
            top=700,
            right=172,
            bottom=600,
            coord_origin="BOTTOMLEFT",
            page_height=792,
        )
        assert box.pixel_box(dpi=72, padding=0) == (72, 92, 172, 192)

    def test_padding_never_goes_negative(self):
        box = BoundingBox(page=1, left=2, top=2, right=50, bottom=50)
        left, top, _, _ = box.pixel_box(dpi=72, padding=20)
        assert (left, top) == (0, 0)

    def test_inverted_corners_are_normalised(self):
        # A box whose corners arrive the wrong way round must not produce a
        # negative-height crop — that raises deep inside the imaging library.
        box = BoundingBox(page=1, left=200, top=300, right=100, bottom=100)
        left, top, right, bottom = box.pixel_box(dpi=72, padding=0)
        assert left < right and top < bottom

    def test_bottomleft_without_a_page_height_still_yields_a_valid_box(self):
        box = BoundingBox(
            page=1, left=10, top=300, right=100, bottom=100, coord_origin="BOTTOMLEFT"
        )
        left, top, right, bottom = box.pixel_box(dpi=72, padding=0)
        assert left < right and top < bottom


class TestRenderCitation:
    async def test_returns_a_data_uri_for_the_cited_region(self, tmp_path):
        service = _service_with_file(tmp_path)
        with patch(
            "services.document_service.DocumentService.generate_preview", return_value=_png()
        ):
            image = await service.render_citation(anchor_uri(PREAVIS_REF))
        assert image.data_uri.startswith("data:image/png;base64,")
        assert base64.b64decode(image.data_uri.split(",", 1)[1]) == image.png
        assert image.page == 1
        assert image.width > 0 and image.height > 0

    async def test_shrinks_until_it_fits_the_byte_budget(self, tmp_path):
        service = _service_with_file(
            tmp_path, config=NavigationConfig(image_max_bytes=10, image_dpi=150, image_min_dpi=40)
        )
        with patch(
            "services.document_service.DocumentService.generate_preview", return_value=_png()
        ) as preview:
            image = await service.render_citation(anchor_uri(PREAVIS_REF))
        # Unsatisfiable budget: it descends to the floor and stops there
        # rather than looping, and reports the dpi it settled on.
        assert image.dpi == 40
        assert [call.kwargs["dpi"] for call in preview.call_args_list] == [150, 75, 40]

    async def test_an_element_without_provenance_is_refused_clearly(self, tmp_path):
        service = _service_with_file(tmp_path)
        with pytest.raises(InvalidArgumentError, match="no page coordinates"):
            # The document title in the fixture has provenance; a caption
            # hanging off a picture does too. `#/pages/1` is a virtual ref and
            # carries none.
            await service.render_citation(anchor_uri("#/pages/1"))

    async def test_unknown_ref(self, tmp_path):
        service = _service_with_file(tmp_path)
        with pytest.raises(RefNotFoundError):
            await service.render_citation(anchor_uri("#/texts/999"))

    async def test_a_document_without_a_file_is_refused(self):
        service = make_navigation_service()  # storage_path is empty
        with pytest.raises(InvalidArgumentError, match="no stored file"):
            await service.render_citation(anchor_uri(PREAVIS_REF))


class TestAppsSurface:
    async def test_the_tool_points_at_the_template(self, tmp_path):
        async with _client(_service_with_file(tmp_path)) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
        assert tools["show_citation"].meta["ui"] == {
            "resourceUri": CITATION_APP_URI,
            "visibility": ["model"],
        }
        # The four text tools stay untouched by the extension.
        assert tools["read_element"].meta is None

    async def test_the_template_is_served_as_an_app_resource(self, tmp_path):
        async with _client(_service_with_file(tmp_path)) as client:
            read = await client.read_resource(CITATION_APP_URI)
        assert read.contents[0].mime_type == APP_MIME_TYPE
        assert read.contents[0].text == CITATION_APP_HTML

    async def test_the_server_advertises_the_extension(self, tmp_path):
        async with _client(_service_with_file(tmp_path)) as client:
            assert EXTENSION_ID in (client.server_capabilities.extensions or {})

    async def test_disabled_apps_leave_the_text_surface_alone(self, tmp_path):
        async with _client(_service_with_file(tmp_path), apps=False) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            assert "show_citation" not in tools
            assert not (client.server_capabilities.extensions or {})


class TestGracefulDegradation:
    """SEP-2133: a UI-enabled tool must stay useful without the UI."""

    async def test_a_host_without_apps_gets_the_citation_and_no_image(self, tmp_path):
        async with _client(_service_with_file(tmp_path), negotiates=False) as client:
            with patch(
                "services.document_service.DocumentService.generate_preview", return_value=_png()
            ) as preview:
                result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert view["quote"]
        assert view["page_image"] is None
        # Not merely omitted from the payload — never rendered at all, so the
        # bytes cost nothing on a host that could not have shown them.
        preview.assert_not_called()

    async def test_a_host_with_apps_gets_the_image(self, tmp_path):
        async with _client(_service_with_file(tmp_path), negotiates=True) as client:
            with patch(
                "services.document_service.DocumentService.generate_preview", return_value=_png()
            ):
                result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert view["page_image"].startswith("data:image/png;base64,")
        assert view["image_note"] is None

    async def test_a_failed_render_degrades_to_the_text_citation(self, tmp_path):
        async with _client(_service_with_file(tmp_path), negotiates=True) as client:
            with patch(
                "services.document_service.DocumentService.generate_preview",
                side_effect=OSError("poppler is not installed"),
            ):
                result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert result.is_error is False
        assert view["quote"]
        assert view["page_image"] is None
        assert "poppler" in view["image_note"]

    async def test_a_malformed_anchor_is_still_a_tool_error(self, tmp_path):
        async with _client(_service_with_file(tmp_path)) as client:
            result = await client.call_tool("show_citation", {"uri": "nope"})
        assert result.is_error is True
        assert "dstudio://doc/" in result.content[0].text


class TestTemplate:
    def test_is_a_self_contained_html5_document(self):
        assert CITATION_APP_HTML.lstrip().startswith("<!doctype html>")
        assert "</html>" in CITATION_APP_HTML

    def test_loads_nothing_from_the_network(self):
        # The default MCP Apps CSP is `connect-src 'none'` with `img-src 'self'
        # data:`; anything remote would silently fail to load, so the template
        # must not reference it in the first place.
        for marker in ("http://", "https://", "<link", "<script src"):
            assert marker not in CITATION_APP_HTML, marker

    def test_escapes_document_text_before_it_becomes_markup(self):
        assert "&amp;" in CITATION_APP_HTML and "&lt;" in CITATION_APP_HTML
        # Every interpolation of document-derived text goes through esc().
        for field in ("view.quote", "view.uri", "view.page_image", "view.ref"):
            assert f"esc({field})" in CITATION_APP_HTML, field
