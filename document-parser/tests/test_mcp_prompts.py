"""Tests for the MCP prompts — the user-invoked protocols.

A prompt is a contract too: its name is what the user types, its arguments are
what the client asks them for, and its text is what the model then executes.
These pin all three.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "mcp.server.mcpserver",
    reason="MCP SDK not installed — `uv sync --group mcp` to exercise the prompts",
)

from contextlib import asynccontextmanager

from mcp import Client

from mcp_adapter import build_mcp_server
from tests.navigation_fixtures import (
    PREAVIS_REF,
    anchor_uri,
    make_document_tools,
)


@asynccontextmanager
async def _client(*, apps: bool = False):
    server = build_mcp_server(lambda: make_document_tools(), version="test", apps=apps)
    async with Client(server) as client:
        yield client


async def _render(name: str, args: dict[str, str]) -> str:
    async with _client() as client:
        result = await client.get_prompt(name, args)
    return result.messages[0].content.text


class TestSurface:
    async def test_lists_the_two_procedures(self):
        async with _client() as client:
            prompts = {p.name: p for p in (await client.list_prompts()).prompts}
        assert set(prompts) == {"cite_answer", "extract_table"}
        assert prompts["cite_answer"].title == "Answer with verified citations"

    async def test_arguments_are_described_for_the_person_typing_them(self):
        async with _client() as client:
            prompt = next(
                p for p in (await client.list_prompts()).prompts if p.name == "cite_answer"
            )
        args = {a.name: a for a in prompt.arguments or []}
        assert set(args) == {"document", "question", "evidence"}
        assert args["document"].required and args["question"].required
        assert not args["evidence"].required
        assert all(a.description for a in args.values())

    async def test_prompts_do_not_depend_on_the_ui_extension(self):
        # They drive the text tools; enabling a UI is orthogonal.
        async with _client(apps=True) as client:
            assert len((await client.list_prompts()).prompts) == 2

    async def test_a_missing_argument_is_refused(self):
        with pytest.raises(Exception):  # noqa: B017 — the SDK wraps it as a protocol error
            await _render("cite_answer", {"document": "contrat.pdf"})


class TestCiteAnswer:
    async def test_carries_the_question_and_the_document(self):
        text = await _render(
            "cite_answer", {"document": "contrat.pdf", "question": "Quel est le préavis ?"}
        )
        assert "contrat.pdf" in text
        assert "Quel est le préavis ?" in text

    async def test_walks_the_four_tools_in_order(self):
        text = await _render("cite_answer", {"document": "d", "question": "q"})
        positions = [
            text.index(tool)
            for tool in ("find_documents", "get_outline", "read_element", "verify_citation")
        ]
        assert positions == sorted(positions)

    async def test_pins_the_two_rules_agents_get_wrong(self):
        text = await _render("cite_answer", {"document": "d", "question": "q"})
        # Citing the section uri instead of the element's, and resuming a
        # truncated read by re-reading it larger.
        assert "citations[].uri" in text
        assert "cursor=next_cursor" in text

    async def test_refuses_to_fill_a_gap_from_memory(self):
        text = await _render("cite_answer", {"document": "d", "question": "q"})
        assert "Do not complete the answer from what you already know" in text

    async def test_text_evidence_does_not_ask_for_images(self):
        text = await _render("cite_answer", {"document": "d", "question": "q"})
        assert "show_citation" not in text

    async def test_image_evidence_adds_the_visual_step(self):
        text = await _render(
            "cite_answer", {"document": "d", "question": "q", "evidence": "images"}
        )
        assert "show_citation(uri)" in text
        assert text.index("show_citation") > text.index("verify_citation")

    @pytest.mark.parametrize("value", ["text", "TEXT", "", "prose", "  images  "])
    async def test_evidence_is_read_leniently(self, value: str):
        text = await _render("cite_answer", {"document": "d", "question": "q", "evidence": value})
        assert ("show_citation" in text) is (value.strip().lower() == "images")


class TestExtractTable:
    async def test_targets_the_element_not_its_section(self):
        text = await _render("extract_table", {"uri": anchor_uri(PREAVIS_REF)})
        assert 'include="self"' in text
        assert anchor_uri(PREAVIS_REF) in text

    async def test_forbids_tidying_the_table(self):
        text = await _render("extract_table", {"uri": anchor_uri(PREAVIS_REF)})
        for rule in ("re-align", "re-order", "round numbers", "empty"):
            assert rule in text, rule

    async def test_handles_being_pointed_at_something_else(self):
        text = await _render("extract_table", {"uri": anchor_uri(PREAVIS_REF)})
        assert "does not point at a table" in text
