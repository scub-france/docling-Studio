"""The investigation viewer — the second MCP App (#329).

Two things are worth pinning here and nowhere else. The card and the text
payload must stay one account of one investigation, so what a host without a
UI reads is asserted against what the viewer is handed. And the template
itself is a security surface: it renders strings a model wrote after reading
a document, so every interpolation has to go through `esc`.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "mcp.server.mcpserver",
    reason="MCP SDK not installed — `uv sync --group mcp` to exercise the adapter",
)

from contextlib import asynccontextmanager

from mcp import Client

from mcp_adapter import build_mcp_server
from mcp_adapter.apps import INVESTIGATION_APP_HTML, INVESTIGATION_APP_URI
from tests.navigation_fixtures import (
    PREAVIS_REF,
    PREAVIS_TEXT,
    anchor_uri,
    make_document,
    make_document_tools,
)

PREAVIS_URI = anchor_uri(PREAVIS_REF)


@asynccontextmanager
async def _client(tools, *, apps: bool = True, investigations: bool = True):
    server = build_mcp_server(
        lambda: tools, version="test", apps=apps, investigations=investigations
    )
    async with Client(server) as client:
        yield client


def _payload(result):
    assert result.is_error is False, result.content[0].text
    return result.structured_content


async def _investigated(client, *, drift_first: bool = True):
    """One investigation: a rejected ref, then a kept one, then closed."""
    opened = _payload(
        await client.call_tool(
            "open_investigation", {"document": "contrat", "question": "Comment résilier ?"}
        )
    )
    planned = _payload(
        await client.call_tool(
            "plan_steps",
            {
                "investigation_id": opened["investigation_id"],
                "steps": [{"question": "Quel est le préavis ?", "why": "tout en dépend"}],
            },
        )
    )
    if drift_first:
        await client.call_tool(
            "record_attempt",
            {
                "investigation_id": opened["investigation_id"],
                "step_id": planned["first_step_id"],
                "thought": "je crois que c'est six mois",
                "uri": PREAVIS_URI,
                "quote": "Le préavis est de six mois.",
            },
        )
    await client.call_tool(
        "record_attempt",
        {
            "investigation_id": opened["investigation_id"],
            "step_id": planned["first_step_id"],
            "thought": "12.2 le dit littéralement",
            "uri": PREAVIS_URI,
            "quote": PREAVIS_TEXT,
        },
    )
    await client.call_tool(
        "close_investigation",
        {
            "investigation_id": opened["investigation_id"],
            "answer": f"Trois mois. {PREAVIS_URI}",
        },
    )
    return opened["investigation_id"]


class TestSurface:
    async def test_the_tool_points_at_the_template(self):
        async with _client(make_document_tools()) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
        assert tools["show_investigation"].meta["ui"] == {
            "resourceUri": INVESTIGATION_APP_URI,
            "visibility": ["model"],
        }
        assert tools["show_investigation"].annotations.read_only_hint

    async def test_the_template_is_served_as_an_app_resource(self):
        async with _client(make_document_tools()) as client:
            read = await client.read_resource(INVESTIGATION_APP_URI)
        assert read.contents[0].text == INVESTIGATION_APP_HTML

    async def test_the_journal_flag_withholds_the_viewer_too(self):
        """A viewer for a record the server does not keep would always error."""
        async with _client(make_document_tools(), investigations=False) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
        assert "show_investigation" not in tools
        assert "get_investigation_page" not in tools
        assert "show_citation" in tools, "the citation view is a separate decision"

    async def test_the_page_fetch_is_the_views_own_and_app_only(self):
        """Bound to this view's resource, not the citation view's: a host is
        free to scope an app's calls to the tools its template declares."""
        async with _client(make_document_tools()) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
        fetch = tools["get_investigation_page"]
        assert fetch.meta["ui"] == {
            "resourceUri": INVESTIGATION_APP_URI,
            "visibility": ["app"],
        }
        assert fetch.annotations.read_only_hint

    async def test_the_page_fetch_answers_with_a_raster(self, tmp_path):
        pdf = tmp_path / "contrat.pdf"
        pdf.write_bytes(b"%PDF-1.4 not really a pdf")
        document = make_document()
        document.storage_path = str(pdf)
        async with _client(make_document_tools(documents=[document])) as client:
            image = _payload(await client.call_tool("get_investigation_page", {"uri": PREAVIS_URI}))
        assert image["data_uri"].startswith("data:image/")
        assert image["width"] > 0 and image["height"] > 0

    async def test_disabling_apps_leaves_the_journal_tools_alone(self):
        async with _client(make_document_tools(), apps=False) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
        assert "show_investigation" not in tools
        assert "get_investigation" in tools

    async def test_closing_steers_at_the_viewer_not_a_card_per_citation(self):
        """The prompt's step 7 is thirty turns behind by close time; the close
        result is what the model reads at the moment it chooses how to display.
        Observed failure: a show_citation per kept anchor instead of the one
        card that shows the record."""
        async with _client(make_document_tools()) as client:
            opened = _payload(
                await client.call_tool(
                    "open_investigation",
                    {"document": "contrat", "question": "Comment résilier ?"},
                )
            )
            planned = _payload(
                await client.call_tool(
                    "plan_steps",
                    {
                        "investigation_id": opened["investigation_id"],
                        "steps": [{"question": "Quel est le préavis ?", "why": "tout en dépend"}],
                    },
                )
            )
            await client.call_tool(
                "record_attempt",
                {
                    "investigation_id": opened["investigation_id"],
                    "step_id": planned["first_step_id"],
                    "thought": "12.2 le dit littéralement",
                    "uri": PREAVIS_URI,
                    "quote": PREAVIS_TEXT,
                },
            )
            closed = _payload(
                await client.call_tool(
                    "close_investigation",
                    {
                        "investigation_id": opened["investigation_id"],
                        "answer": f"Trois mois. {PREAVIS_URI}",
                    },
                )
            )
        assert "show_investigation" in closed["next_step"]
        assert "show_citation" in closed["next_step"], "the wrong move is named, not implied"

    async def test_the_citation_view_yields_to_the_investigation_view(self):
        """show_citation's 'prefer it whenever someone asks to see' is right
        for ad-hoc reading and wrong at the end of an investigation — the
        carve-out exists only while show_investigation does."""
        async with _client(make_document_tools()) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
        assert "show_investigation" in tools["show_citation"].description

        async with _client(make_document_tools(), investigations=False) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
        assert "show_investigation" not in tools["show_citation"].description


class TestCard:
    async def test_it_carries_the_record_the_text_payload_carries(self):
        """One investigation, one account of it — the viewer shows no field a
        text-only host cannot read."""
        tools = make_document_tools()
        async with _client(tools) as client:
            investigation_id = await _investigated(client)
            card = _payload(
                await client.call_tool("show_investigation", {"investigation_id": investigation_id})
            )
            view = _payload(
                await client.call_tool("get_investigation", {"investigation_id": investigation_id})
            )
        assert card["reasoning"] == view["reasoning"]
        assert card["map"] == view["map"]
        assert card["question"] == view["question"]
        assert card["filename"] == view["filename"] == "contrat.pdf"

    async def test_it_states_the_tally_and_the_budget_a_card_draws(self):
        tools = make_document_tools()
        async with _client(tools) as client:
            investigation_id = await _investigated(client)
            card = _payload(
                await client.call_tool("show_investigation", {"investigation_id": investigation_id})
            )
        assert (card["steps_answered"], card["steps_unanswered"]) == (1, 0)
        assert card["attempts_kept"] == 1
        # Without it the card can only draw a count, and "3 attempts" does not
        # say whether the step had any budget left.
        assert card["max_attempts_per_step"] == 3
        assert card["state"] == "closed"
        assert card["answer"].startswith("Trois mois")

    async def test_both_verdicts_reach_the_card(self):
        tools = make_document_tools()
        async with _client(tools) as client:
            investigation_id = await _investigated(client)
            card = _payload(
                await client.call_tool("show_investigation", {"investigation_id": investigation_id})
            )
        attempts = card["reasoning"][0]["attempts"]
        assert [a["outcome"] for a in attempts] == ["quote_drift", "kept"]
        assert attempts[0]["actual_quote"], "the card shows what the page really says"

    async def test_it_reports_the_surface_total_not_just_its_own_cost(self):
        tools = make_document_tools()
        async with _client(tools) as client:
            investigation_id = await _investigated(client)
            card = _payload(
                await client.call_tool("show_investigation", {"investigation_id": investigation_id})
            )
        assert card["total_calls"] > 1
        assert card["total_est_tokens"] > 0

    async def test_an_unknown_investigation_is_a_tool_error(self):
        async with _client(make_document_tools()) as client:
            result = await client.call_tool("show_investigation", {"investigation_id": "nope"})
        assert result.is_error is True
        assert "No investigation" in result.content[0].text


class TestTemplate:
    def test_is_a_self_contained_html5_document(self):
        assert INVESTIGATION_APP_HTML.lstrip().startswith("<!doctype html>")
        assert "</html>" in INVESTIGATION_APP_HTML

    def test_loads_nothing_from_the_network(self):
        for marker in ("http://", "https://", "<link", "<script src"):
            assert marker not in INVESTIGATION_APP_HTML, marker

    def test_every_field_it_renders_is_escaped_first(self):
        """The card renders strings a model wrote after reading a document.
        The server defuses the content delimiter; this is the other half."""
        assert "&amp;" in INVESTIGATION_APP_HTML and "&lt;" in INVESTIGATION_APP_HTML
        for field in (
            "view.question",
            "view.state",
            "attempt.thought",
            "attempt.detail",
            "attempt.actual_quote",
            "node.title",
            "step.question",
            "step.why",
            "image.data_uri",
            "image.page",
            "cached.error",
        ):
            assert f"esc({field})" in INVESTIGATION_APP_HTML, field

    def test_it_says_on_the_card_that_a_thought_is_not_verified(self):
        """A stored trace looks certified and half of it is not. Saying so in
        the docs is not saying so to the person reading the card."""
        assert "never checked" in INVESTIGATION_APP_HTML

    def test_it_tells_a_dropped_step_from_an_exhausted_one(self):
        """Two honest outcomes, two different findings. Showing both as
        `unanswered` would blame the document for the agent's decision."""
        assert "wasAbandoned" in INVESTIGATION_APP_HTML
        assert '"abandoned"' in INVESTIGATION_APP_HTML

    def test_the_only_tool_it_calls_is_its_own_page_fetch(self):
        # The record renders from the tool result alone. The path tab is the
        # one exception, and it goes through the view's own app-only tool —
        # one call site, so nothing else can quietly start fetching.
        assert '"ui/initialize"' in INVESTIGATION_APP_HTML
        assert '"ui/notifications/initialized"' in INVESTIGATION_APP_HTML
        assert 'name: "get_investigation_page"' in INVESTIGATION_APP_HTML
        assert INVESTIGATION_APP_HTML.count('"tools/call"') == 1

    def test_it_offers_the_two_readings_and_the_fold(self):
        # The record and the path are tabs over one record; the tree folds.
        for marker in ('data-tab="record"', 'data-tab="path"', "data-fold", "How it moved"):
            assert marker in INVESTIGATION_APP_HTML, marker

    def test_an_unanswered_step_gets_no_page_thumbnail(self):
        """Only a kept ref earns a page. A thumbnail under an unanswered step
        would claim the investigation found something there."""
        assert "the document did not answer" in INVESTIGATION_APP_HTML
        assert "find((attempt) => isKept(attempt.outcome))" in INVESTIGATION_APP_HTML
        # The guard itself, not just its ingredients: no kept attempt, no uri —
        # and no uri, no data-uri for the hydrator to fetch.
        assert 'const uri = kept ? kept.kept_uri || kept.uri : ""' in INVESTIGATION_APP_HTML
        assert '${uri ? `data-uri="${esc(uri)}"` : ""}' in INVESTIGATION_APP_HTML
