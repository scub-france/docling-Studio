"""Tests for the MCP prompt — the Chunkless RAG loop as a slash command (#363).

A prompt is a contract too: its name is what the user types, its arguments are
what the client asks them for, and its text is what the model then executes.
These pin all three.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from mcp import Client

from mcp_adapter import build_mcp_server
from tests.navigation_fixtures import make_document_tools

ARGS = {"document": "d", "question": "q"}


@asynccontextmanager
async def _client(*, apps: bool = True):
    server = build_mcp_server(lambda: make_document_tools(), version="test", apps=apps)
    async with Client(server) as client:
        yield client


async def _render(args: dict[str, str], *, apps: bool = True) -> str:
    async with _client(apps=apps) as client:
        result = await client.get_prompt("chunkless_rag", args)
    return result.messages[0].content.text


class TestSurface:
    async def test_one_procedure_named_after_what_it_does(self):
        async with _client() as client:
            prompts = {p.name: p for p in (await client.list_prompts()).prompts}
        assert set(prompts) == {"chunkless_rag"}
        assert prompts["chunkless_rag"].title.startswith("Chunkless RAG")

    async def test_arguments_are_described_for_the_person_typing_them(self):
        async with _client() as client:
            prompt = (await client.list_prompts()).prompts[0]
        args = {a.name: a for a in prompt.arguments or []}
        assert set(args) == {"document", "question"}
        assert all(a.required and a.description for a in args.values())

    async def test_it_is_listed_with_or_without_the_cards(self):
        async with _client(apps=False) as client:
            assert [p.name for p in (await client.list_prompts()).prompts] == ["chunkless_rag"]

    async def test_a_missing_argument_is_refused(self):
        with pytest.raises(Exception):  # noqa: B017 — the SDK wraps it as a protocol error
            await _render({"document": "contrat.pdf"})


class TestLoop:
    async def test_carries_the_question_and_the_document(self):
        text = await _render({"document": "contrat.pdf", "question": "Quel est le préavis ?"})
        assert "contrat.pdf" in text
        assert "Quel est le préavis ?" in text

    async def test_walks_the_loop_then_ends_on_the_sources_card(self):
        text = await _render(ARGS)
        steps = ("find_documents", "get_outline", "read_element", "verify_citation", "show_sources")
        positions = [text.index(tool) for tool in steps]
        assert positions == sorted(positions)

    async def test_leaves_show_citation_out_of_the_loop(self):
        """One card ends the answer; show_citation is for a passage on request."""
        assert "show_citation" not in await _render(ARGS)

    async def test_pins_the_two_rules_agents_get_wrong(self):
        text = await _render(ARGS)
        # Citing the section uri instead of the element's, and resuming a
        # truncated read by re-reading it larger.
        assert "citations[].uri" in text
        assert "cursor=next_cursor" in text

    async def test_runs_the_loop_in_bounded_rounds(self):
        """docling-agent's loop: one section per round, a reason, an outcome,
        and the same cap as Studio's own Ask loop."""
        text = await _render(ARGS)
        assert "at most 5 rounds" in text
        assert "pick ONE entry, say in one line why" in text
        assert "say in one line what it gave" in text
        assert "same round, not a new one" in text
        assert "Stop as soon as you can answer" in text

    async def test_tells_the_agent_what_to_hand_show_sources(self):
        text = await _render(ARGS)
        assert "your rounds in order" in text
        assert "`{uri, why, found}`" in text

    async def test_refuses_to_fill_a_gap_from_memory(self):
        text = await _render(ARGS)
        assert "Do not complete the answer from what you already know" in text

    async def test_names_no_card_the_server_did_not_publish(self):
        text = await _render(ARGS, apps=False)
        assert "show_" not in text
        assert "deep_link" in text


class TestLiveRoundCap:
    """#364 — the prompt states the cap of the services a call would use now."""

    async def test_follows_the_cap_of_the_resolved_services(self):
        from services.navigation_config import NavigationConfig

        tools = make_document_tools(config=NavigationConfig(max_rounds=3))
        server = build_mcp_server(lambda: tools, version="test")
        async with Client(server) as client:
            result = await client.get_prompt("chunkless_rag", ARGS)
        text = result.messages[0].content.text
        assert "at most 3 rounds" in text
        assert "If 3 rounds did not find the answer" in text

    async def test_falls_back_to_the_boot_cap_while_the_app_starts(self):
        from services.navigation_errors import NavigationUnavailableError

        def not_yet():
            raise NavigationUnavailableError("starting")

        server = build_mcp_server(not_yet, version="test", max_rounds=7)
        async with Client(server) as client:
            result = await client.get_prompt("chunkless_rag", ARGS)
        assert "at most 7 rounds" in result.messages[0].content.text

    async def test_the_instructions_state_the_boot_cap(self):
        server = build_mcp_server(lambda: make_document_tools(), version="test", max_rounds=4)
        assert "4 rounds at most" in server.instructions
