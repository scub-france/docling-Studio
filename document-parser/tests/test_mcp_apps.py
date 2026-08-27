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
from services.navigation_config import NavigationConfig
from services.navigation_errors import InvalidArgumentError, RefNotFoundError
from tests.navigation_fixtures import (
    PREAVIS_REF,
    FakeRasterizer,
    anchor_uri,
    make_document,
    make_document_tools,
)

APPS_CLIENT = advertise(EXTENSION_ID, {"mimeTypes": [APP_MIME_TYPE]})


def _png(width: int = 1275, height: int = 1650) -> bytes:
    """A blank page raster standing in for poppler's output."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@asynccontextmanager
async def _client(tools, *, apps: bool = True, negotiates: bool = False, inline: bool = False):
    server = build_mcp_server(
        lambda: tools, version="test", apps=apps, inline_citation_image=inline
    )
    async with Client(server, extensions=[APPS_CLIENT] if negotiates else None) as client:
        yield client


def _service_with_file(tmp_path: Path, **kwargs):
    """Document tools whose document points at a real file on disk.

    The path only has to exist for the entity to be valid — the rasterizer is
    a fake, which is what the `PageRasterizer` port was extracted for.
    """
    pdf = tmp_path / "contrat.pdf"
    pdf.write_bytes(b"%PDF-1.4 not really a pdf")
    document = make_document()
    document.storage_path = str(pdf)
    return make_document_tools(documents=[document], **kwargs)


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
        tools = _service_with_file(tmp_path)
        image = await tools.images.render(anchor_uri(PREAVIS_REF))
        assert image.data_uri.startswith("data:image/webp;base64,")
        assert image.media_type == "image/webp"
        assert base64.b64decode(image.data_uri.split(",", 1)[1]) == image.png
        assert image.page == 1
        assert image.width > 0 and image.height > 0

    async def test_shrinks_until_it_fits_the_byte_budget(self, tmp_path):
        raster = FakeRasterizer()
        tools = _service_with_file(
            tmp_path,
            config=NavigationConfig(image_max_bytes=10, image_dpi=150, image_min_dpi=40),
            rasterizer=raster,
        )
        image = await tools.images.render(anchor_uri(PREAVIS_REF))
        # Unsatisfiable budget: it descends to the floor and stops there
        # rather than looping, and reports the dpi it settled on.
        assert image.dpi == 40
        assert [dpi for _, dpi in raster.renders] == [150, 75, 40]

    async def test_an_element_without_provenance_is_refused_clearly(self, tmp_path):
        tools = _service_with_file(tmp_path)
        with pytest.raises(InvalidArgumentError, match="no page coordinates"):
            # The document title in the fixture has provenance; a caption
            # hanging off a picture does too. `#/pages/1` is a virtual ref and
            # carries none.
            await tools.images.render(anchor_uri("#/pages/1"))

    async def test_unknown_ref(self, tmp_path):
        tools = _service_with_file(tmp_path)
        with pytest.raises(RefNotFoundError):
            await tools.images.render(anchor_uri("#/texts/999"))

    async def test_a_document_without_a_file_is_refused(self):
        tools = make_document_tools()  # storage_path is empty
        with pytest.raises(InvalidArgumentError, match="no stored file"):
            await tools.images.render(anchor_uri(PREAVIS_REF))


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
        raster = FakeRasterizer()
        async with _client(
            _service_with_file(tmp_path, rasterizer=raster), negotiates=False
        ) as client:
            result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert view["quote"]
        assert view["page_image"] is None
        # Not merely omitted from the payload — never rendered at all, so the
        # bytes cost nothing on a host that could not have shown them.
        assert raster.renders == []

    async def test_the_payload_carries_the_provenance_the_viewer_shows(self, tmp_path):
        # The anchor already encodes document and parse; unpacking them means
        # the viewer never has to parse a `dstudio://` uri to say where a
        # passage came from — and a text-only host reads the same provenance.
        async with _client(_service_with_file(tmp_path), negotiates=False) as client:
            result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert view["document_id"] == "doc-1"
        assert view["version_id"] == "an-1"
        assert view["label"]
        assert view["quote_hash"].startswith("sha256:")

    async def test_the_quote_is_priced_with_the_estimator_the_rest_of_the_surface_uses(
        self, tmp_path
    ):
        # One estimator across the surface: a card's figure has to be
        # comparable with the `est_tokens` an outline entry advertises,
        # otherwise the two numbers quietly mean different things.
        from domain.navigation import estimate_tokens

        async with _client(_service_with_file(tmp_path), negotiates=False) as client:
            result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert view["est_tokens"] == estimate_tokens(view["quote"])
        # No image was rendered, so there is no weight to report — and the
        # field says so rather than reporting zero.
        assert view["image_bytes"] is None

    async def test_the_page_image_is_weighed_in_bytes_not_tokens(self, tmp_path):
        # How a host prices an image is the host's business; quoting a token
        # figure for it would be inventing one. Only the escape hatch puts an
        # image in this payload at all.
        async with _client(_service_with_file(tmp_path), negotiates=True, inline=True) as client:
            result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert view["image_bytes"] > 0
        # The raster's own size, not the base64 it travels as.
        assert view["image_bytes"] < len(view["page_image"])

    async def test_the_card_reports_the_surface_total_not_just_its_own_cost(self, tmp_path):
        # What a reader wants to know is whether the document work is getting
        # expensive, which one citation's cost cannot answer. The tally counts
        # every tool call on the server, this one included.
        async with _client(_service_with_file(tmp_path), negotiates=False) as client:
            await client.call_tool("find_documents", {})
            await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
            result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert view["total_calls"] == 3
        assert view["total_est_tokens"] > view["est_tokens"]

    async def test_a_failed_render_degrades_to_the_text_citation(self, tmp_path):
        class BrokenRasterizer(FakeRasterizer):
            def render_page(self, storage_path, *, page, dpi):
                raise OSError("poppler is not installed")

        tools = _service_with_file(tmp_path, rasterizer=BrokenRasterizer())
        async with _client(tools, negotiates=True, inline=True) as client:
            result = await client.call_tool("show_citation", {"uri": anchor_uri(PREAVIS_REF)})
        view = result.structured_content
        assert result.is_error is False
        assert view["quote"]
        assert view["page_image"] is None
        assert "poppler" in view["image_note"]

    async def test_a_failed_image_fetch_is_an_error_the_view_can_show(self, tmp_path):
        class BrokenRasterizer(FakeRasterizer):
            def render_page(self, storage_path, *, page, dpi):
                raise OSError("poppler is not installed")

        tools = _service_with_file(tmp_path, rasterizer=BrokenRasterizer())
        async with _client(tools, negotiates=True) as client:
            result = await client.call_tool("get_citation_image", {"uri": anchor_uri(PREAVIS_REF)})
        # The view keeps its text card and shows why the picture is missing.
        assert result.is_error is True

    async def test_a_malformed_anchor_is_still_a_tool_error(self, tmp_path):
        async with _client(_service_with_file(tmp_path)) as client:
            result = await client.call_tool("show_citation", {"uri": "nope"})
        assert result.is_error is True
        assert "dstudio://doc/" in result.content[0].text


def _stylesheet() -> str:
    """Just the <style> block — assertions about CSS should not read the JS."""
    start = CITATION_APP_HTML.index("<style>")
    return CITATION_APP_HTML[start : CITATION_APP_HTML.index("</style>", start)]


class TestTemplate:
    def test_is_a_self_contained_html5_document(self):
        assert CITATION_APP_HTML.lstrip().startswith("<!doctype html>")
        assert "</html>" in CITATION_APP_HTML

    def test_the_view_asks_for_both_rasters_itself(self):
        # Neither the crop nor the page thumbnail travels through the model.
        assert 'name: "get_citation_image"' in CITATION_APP_HTML
        assert 'kind: "page"' in CITATION_APP_HTML
        assert "page_image" in CITATION_APP_HTML  # the escape hatch still renders

    def test_loads_nothing_from_the_network(self):
        # The default MCP Apps CSP is `connect-src 'none'` with `img-src 'self'
        # data:`; anything remote would silently fail to load, so the template
        # must not reference it in the first place.
        for marker in ("http://", "https://", "<link", "<script src"):
            assert marker not in CITATION_APP_HTML, marker

    def test_escapes_document_text_before_it_becomes_markup(self):
        assert "&amp;" in CITATION_APP_HTML and "&lt;" in CITATION_APP_HTML
        # Every interpolation of document-derived text goes through esc().
        for field in ("view.uri", "view.page_image", "view.ref", "view.quote_hash"):
            assert f"esc({field})" in CITATION_APP_HTML, field

    def test_the_quote_is_escaped_before_markdown_becomes_markup(self):
        # The quote is the one field that does *not* reach `esc` at the
        # interpolation site: it is rendered as markdown. The invariant is
        # unchanged, it just moves one call earlier — `renderMarkdown` escapes
        # the whole string before composing a single tag out of it, so every
        # branch below it works on text that can no longer carry markup.
        assert "renderMarkdown(view.quote)" in CITATION_APP_HTML
        assert 'const text = esc(String(raw ?? ""))' in CITATION_APP_HTML

    def test_copying_survives_a_host_that_grants_no_clipboard(self):
        # `navigator.clipboard?.writeText(...).then(...)` throws when the
        # clipboard is absent, so the button did nothing at all — silently.
        # Three layers now: the async API, execCommand, then selecting the
        # text so the reader can copy it themselves.
        assert "execCommand" in CITATION_APP_HTML
        assert "Clipboard blocked" in CITATION_APP_HTML

    def test_open_in_studio_is_offered_only_for_a_link_a_host_can_resolve(self):
        # `deep_link` is a bare path unless MCP_STUDIO_BASE_URL is set, and
        # `ui/open-link` on a bare path does nothing.
        assert "isAbsolute(view.deep_link)" in CITATION_APP_HTML
        assert "MCP_STUDIO_BASE_URL" in CITATION_APP_HTML

    def test_completes_the_handshake_before_calling_a_tool_back(self):
        # The spec's lifecycle is `ui/initialize` -> the host's result ->
        # `ui/notifications/initialized`. Sending only the notification is
        # enough to be *handed* a tool result and not enough to be allowed to
        # call one back — which is exactly how the page thumbnail went missing.
        assert '"ui/initialize"' in CITATION_APP_HTML
        assert "ui/notifications/initialized" in CITATION_APP_HTML
        assert '"2026-01-26"' in CITATION_APP_HTML
        # The image fetch waits for it.
        assert "await handshake()" in CITATION_APP_HTML

    def test_the_notification_is_sent_even_when_the_handshake_is_ignored(self):
        # A host that predates `ui/initialize` still gates the tool result on
        # the notification. Withholding it would trade a missing thumbnail for
        # a blank card.
        assert ".catch(() => false)" in CITATION_APP_HTML

    def test_a_thumbnail_that_cannot_be_fetched_says_so(self):
        # A grey rectangle that never fills in is a bug the reader has to
        # guess at.
        assert "failLocator" in CITATION_APP_HTML
        assert "Aperçu de la page indisponible" in CITATION_APP_HTML

    def test_answers_the_host_s_teardown_request(self):
        assert "ui/resource-teardown" in CITATION_APP_HTML

    def test_follows_the_host_s_theme_and_later_changes_to_it(self):
        # A sandboxed iframe cannot read the host's theme class, so it is
        # asked for — and re-applied when the host says it changed.
        assert "ui/notifications/host-context-changed" in CITATION_APP_HTML
        assert 'setAttribute("data-theme"' in CITATION_APP_HTML

    def test_asks_the_host_to_size_the_frame_to_the_content(self):
        # The host owns the iframe's box, so a citation carrying a page image
        # and a long table only gets the room it needs if the app asks for it.
        assert "ui/notifications/size-changed" in CITATION_APP_HTML
        assert "ResizeObserver" in CITATION_APP_HTML

    def test_no_image_is_sized_against_the_viewport(self):
        # A `vh` size in the stylesheet plus a resize request is a feedback
        # loop: the frame grows, so the image grows, so the frame is asked to
        # grow again. The rail's thumbnail is sized by its column instead.
        #
        # The scripted `100vh` is exempt and deliberate: it is the spec's own
        # prescription for a host that declares a *fixed* height, where the
        # frame's box is the host's and cannot be grown by asking. The report
        # is measured on <main>, never on documentElement, so it stays out of
        # the loop either way.
        import re

        assert not re.search(r"\d+vh\b", _stylesheet())
        assert ".rail" in CITATION_APP_HTML

    def test_the_frame_is_sized_the_way_the_host_asked_for_it(self):
        # `containerDimensions` is how a host says "you get exactly 400px" or
        # "you may grow to 600". Applying neither is how the card ends up laid
        # out at a width the host then cuts off.
        assert "containerDimensions" in CITATION_APP_HTML
        assert "maxWidth" in CITATION_APP_HTML
        # And the card's own breakpoints follow the card, not the window: a
        # viewport media query inside a 400px iframe answers the wrong
        # question.
        assert "container-type: inline-size" in CITATION_APP_HTML
        assert "@container" in CITATION_APP_HTML

    def test_the_rail_says_where_the_page_sits_in_the_document(self):
        # A citation on page 12 of 13 is near the end, and that is worth a
        # glance — the pager and its track carry it.
        assert 'id="pager"' in CITATION_APP_HTML
        assert 'id="track"' in CITATION_APP_HTML
        assert "page_count" in CITATION_APP_HTML

    def test_a_long_passage_is_not_set_as_a_title(self):
        # A heading is the card's title; four hundred characters set at 25px
        # would be shouting.
        assert "TITLE_CHARS" in CITATION_APP_HTML
        assert "as-title" in CITATION_APP_HTML

    def test_renders_a_pipe_table_rather_than_a_wall_of_pipes(self):
        # A table element's text arrives as GFM markup; the viewer builds a
        # real table out of it, wrapped in the same scroll container the
        # Studio markdown viewer uses.
        assert '<div class="md-table">' in CITATION_APP_HTML
        assert "isDelimiter" in CITATION_APP_HTML

    def test_the_element_palette_matches_the_studio_one(self):
        # Same element, same colour on both surfaces — the values are the ones
        # in frontend/src/shared/elementColors.ts.
        for label, color in (
            ("table", "#8B5CF6"),
            ("section_header", "#F97316"),
            ("text", "#3B82F6"),
        ):
            assert f'{label}: "{color}"' in CITATION_APP_HTML, label
        assert "#94A3B8" in CITATION_APP_HTML  # the unknown-type fallback
