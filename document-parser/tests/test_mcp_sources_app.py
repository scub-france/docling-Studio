"""The sources card — `show_sources` and its MCP App (#363).

Three things are worth pinning here and nowhere else. The card and the text a
host without a UI reads must be one account of one answer. The text must be a
tree a model can relay, not a JSON dump. And the template is a security
surface: it renders strings a model wrote after reading a document, so every
interpolation has to go through `esc`.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest
from mcp import Client

from mcp_adapter import build_mcp_server
from mcp_adapter.apps import SOURCES_APP_URI
from mcp_adapter.sources_view import SOURCES_APP_HTML
from services.navigation_config import NavigationConfig
from tests.navigation_fixtures import (
    JOB_ID,
    PREAVIS_REF,
    anchor_uri,
    make_document,
    make_document_tools,
)

PREAVIS_URI = anchor_uri(PREAVIS_REF)
PREAVIS_SECTION_URI = anchor_uri("#/texts/3")


@asynccontextmanager
async def _client(tools, *, apps: bool = True):
    server = build_mcp_server(lambda: tools, version="test", apps=apps)
    async with Client(server) as client:
        yield client


def _payload(result):
    assert result.is_error is False, result.content[0].text
    return result.structured_content


async def _show(client, **overrides):
    arguments = {
        "question": "Quel est le préavis ?",
        "read": [
            {
                "uri": anchor_uri("#/texts/6"),
                "why": "la fin du contrat",
                "found": "rien sur le préavis",
            },
            {"uri": PREAVIS_SECTION_URI, "why": "le préavis y est", "found": "trois mois"},
        ],
        "cited": [PREAVIS_URI],
    }
    arguments.update(overrides)
    return await client.call_tool("show_sources", arguments)


class TestSurface:
    async def test_the_tool_points_at_the_template(self):
        async with _client(make_document_tools()) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
        assert tools["show_sources"].meta["ui"] == {
            "resourceUri": SOURCES_APP_URI,
            "visibility": ["model"],
        }
        assert tools["show_sources"].annotations.read_only_hint

    async def test_the_template_is_served_as_an_app_resource(self):
        async with _client(make_document_tools()) as client:
            read = await client.read_resource(SOURCES_APP_URI)
        assert read.contents[0].text == SOURCES_APP_HTML

    async def test_the_page_fetch_is_the_cards_own_and_app_only(self):
        """Bound to this card's resource, not the citation card's: a host is
        free to scope an app's calls to the tools its template declares."""
        async with _client(make_document_tools()) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
        fetch = tools["get_source_page"]
        assert fetch.meta["ui"] == {"resourceUri": SOURCES_APP_URI, "visibility": ["app"]}
        assert fetch.annotations.read_only_hint

    @pytest.mark.parametrize(("page", "expected"), [(None, 1), (2, 2)])
    async def test_the_page_fetch_answers_with_a_raster(self, tmp_path, page, expected):
        pdf = tmp_path / "contrat.pdf"
        pdf.write_bytes(b"%PDF-1.4 not really a pdf")
        document = make_document()
        document.storage_path = str(pdf)
        arguments = {"uri": PREAVIS_URI} | ({"page": page} if page else {})
        async with _client(make_document_tools(documents=[document])) as client:
            image = _payload(await client.call_tool("get_source_page", arguments))
        assert image["data_uri"].startswith("data:image/")
        assert image["page"] == expected

    async def test_without_apps_neither_card_is_published(self):
        async with _client(make_document_tools(), apps=False) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
        assert tools == {"find_documents", "get_outline", "read_element", "verify_citation"}


class TestCard:
    async def test_it_carries_the_reading_order_the_map_and_the_ratio(self):
        async with _client(make_document_tools()) as client:
            card = _payload(await _show(client))
        assert [hop["why"] for hop in card["hops"]] == ["la fin du contrat", "le préavis y est"]
        assert card["hops"][1]["cited"] == [PREAVIS_URI]
        statuses = {node["ref"]: node["status"] for node in card["map"]}
        assert statuses["#/texts/3"] == "cited"
        assert statuses["#/texts/6"] == "read"
        assert card["summary"].startswith("2 of 5 rounds · read 2 of ")
        assert [hop["found"] for hop in card["hops"]] == ["rien sur le préavis", "trois mois"]
        assert (card["totals"]["rounds"], card["totals"]["max_rounds"]) == (2, 5)
        assert card["totals"]["over_cap"] is False
        assert card["totals"]["tokens_read"] < card["totals"]["tokens_total"]

    async def test_the_text_a_ui_less_host_reads_is_a_tree_not_json(self):
        async with _client(make_document_tools()) as client:
            result = await _show(client)
        text = result.content[0].text
        with pytest.raises(json.JSONDecodeError):
            json.loads(text)
        assert text.startswith("Sources — Quel est le préavis ?")
        assert result.structured_content["summary"] in text
        assert "cited #/texts/4" in text
        assert "1/5. " in text and "2/5. " in text
        assert "found: trois mois" in text
        assert "open in Studio: http://localhost:3000/analyses/" in text

    async def test_a_cited_hop_links_to_the_passage(self):
        async with _client(make_document_tools()) as client:
            card = _payload(await _show(client))
        assert card["hops"][1]["deep_link"].startswith(
            f"http://localhost:3000/analyses/{JOB_ID}?ref=%23%2Ftexts%2F4"
        )

    async def test_rounds_past_the_cap_are_said_not_hidden(self):
        """The server cannot stop a client's loop; it can make a breach visible."""
        config = NavigationConfig(studio_base_url="http://localhost:3000", max_rounds=1)
        async with _client(make_document_tools(config=config)) as client:
            card = _payload(await _show(client))
        assert card["totals"]["over_cap"] is True
        assert card["summary"].startswith("2 rounds, over the 1-round cap · ")

    async def test_unknown_anchors_are_shown_not_dropped(self):
        async with _client(make_document_tools()) as client:
            result = await _show(client, cited=[PREAVIS_URI, "not-an-anchor"])
        assert result.structured_content["unknown"] == ["not-an-anchor"]
        assert "Unknown anchors (not shown): not-an-anchor" in result.content[0].text

    async def test_no_usable_anchor_is_a_tool_error(self):
        async with _client(make_document_tools()) as client:
            result = await _show(client, read=[{"uri": "garbage", "why": ""}], cited=[])
        assert result.is_error is True
        assert "No usable anchor" in result.content[0].text


class TestTemplate:
    def test_is_a_self_contained_html5_document(self):
        assert SOURCES_APP_HTML.lstrip().startswith("<!doctype html>")
        assert "</html>" in SOURCES_APP_HTML

    def test_loads_nothing_from_the_network(self):
        for marker in ("http://", "https://", "<link", "<script src"):
            assert marker not in SOURCES_APP_HTML, marker

    def test_it_only_listens_to_its_host_frame(self):
        # A sibling app could otherwise post a forged record into this view.
        assert "event.source !== window.parent" in SOURCES_APP_HTML

    def test_it_recognises_its_own_payload(self):
        assert "structured?.hops && structured.totals" in SOURCES_APP_HTML

    def test_counts_render_as_numbers_only(self):
        # Interpolated unescaped, so every count goes through `num()`, which
        # coerces before it formats.
        assert "Number.isFinite(number)" in SOURCES_APP_HTML
        assert "num(hop.est_tokens)" in SOURCES_APP_HTML
        assert "num(hop.ordinal)" in SOURCES_APP_HTML and "num(maxRounds)" in SOURCES_APP_HTML

    def test_a_round_shows_against_the_cap_and_a_breach_is_coloured(self):
        assert "roundOf(hop)" in SOURCES_APP_HTML
        assert "view.totals?.over_cap === true" in SOURCES_APP_HTML
        assert ".ratio.over" in SOURCES_APP_HTML

    def test_every_field_it_renders_is_escaped_first(self):
        """The card renders strings a model wrote after reading a document.
        The server defuses the content delimiter; this is the other half."""
        assert "&amp;" in SOURCES_APP_HTML and "&lt;" in SOURCES_APP_HTML
        for field in (
            "view.question",
            "view.summary",
            "node.title",
            "hop.title",
            "hop.why",
            "hop.found",
            "hop.deep_link",
            "refOf(uri)",
            "image.data_uri",
            "image.page",
            "cached.error",
        ):
            assert f"esc({field}" in SOURCES_APP_HTML, field

    def test_it_says_on_the_card_that_a_why_is_the_agents_word(self):
        assert "recorded as" in SOURCES_APP_HTML and "written" in SOURCES_APP_HTML
        assert "resolved from the anchors" in SOURCES_APP_HTML

    def test_a_studio_link_goes_through_the_host_and_only_if_absolute(self):
        assert '"ui/open-link"' in SOURCES_APP_HTML
        assert "isLink(hop.deep_link)" in SOURCES_APP_HTML

    def test_the_only_tool_it_calls_is_its_own_page_fetch(self):
        assert '"ui/initialize"' in SOURCES_APP_HTML
        assert '"ui/notifications/initialized"' in SOURCES_APP_HTML
        assert 'name: "get_source_page"' in SOURCES_APP_HTML
        assert SOURCES_APP_HTML.count('"tools/call"') == 1

    def test_it_offers_the_two_readings_and_the_fold(self):
        for marker in ('data-tab="record"', 'data-tab="path"', "data-fold", "How it moved"):
            assert marker in SOURCES_APP_HTML, marker

    def test_a_thumbnail_enlarges_like_the_citation_cards_page(self):
        """The lens: fullscreen requested (never assumed), the thumbnail
        standing in until the readable render lands, Escape to leave, zoom
        out to the whole page, and leafing through the document."""
        for marker in (
            '"ui/request-display-mode"',
            "LENS_WIDTH = 1400",
            'role", "dialog',
            "provisional",
            '"Escape"',
            "data-shot",
            "data-jump",
            "data-lens-out",
            "data-lens-in",
            "data-lens-fit",
            "data-lens-prev",
            "data-lens-next",
            '"ArrowRight"',
        ):
            assert marker in SOURCES_APP_HTML, marker

    def test_every_section_read_gets_a_page(self):
        """A cited hop shows the quoted passage; a hop read without a quote
        shows the page where its section starts."""
        assert 'const uri = (hop.cited || [])[0] || hop.uri || ""' in SOURCES_APP_HTML
