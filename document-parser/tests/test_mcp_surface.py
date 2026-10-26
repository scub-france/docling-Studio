"""The model-facing surface: what every connected agent reads on every turn.

The instructions, and each visible tool's name, description and input
schema. Bounded, because every character competes with the conversation; and
each rule learned in live runs stated exactly once, because two phrasings of
one rule drift apart.
"""

from __future__ import annotations

import json

import pytest
from mcp import Client

from mcp_adapter import build_mcp_server
from tests.navigation_fixtures import make_document_tools
from tests.test_mcp_apps import APPS_CLIENT

# About 900 tokens, for the largest surface: the read loop and both cards.
# Was 6 000 with the investigation journal (#363 removed it); kept tight so the
# surface does not creep back.
MAX_SURFACE_CHARS = 3_650

VISIBLE_TOOLS = {
    "find_documents",
    "get_outline",
    "read_element",
    "verify_citation",
    "show_citation",
    "show_sources",
}

RULES = {
    "cite the element read": "citations[].uri",
    "never build an anchor": "never build",
    "document text is data": "is data",
    "a truncated read resumes": "next_cursor",
}


async def _visible(*, apps: bool = True):
    tools = make_document_tools()
    server = build_mcp_server(lambda: tools, version="test", apps=apps)
    async with Client(server, extensions=[APPS_CLIENT] if apps else None) as client:
        listed = (await client.list_tools()).tools
        instructions = client.instructions or ""
    visible = [t for t in listed if ((t.meta or {}).get("ui") or {}).get("visibility") != ["app"]]
    return instructions, visible


async def _surface(*, apps: bool = True) -> str:
    instructions, visible = await _visible(apps=apps)
    return instructions + "".join(
        t.name + (t.description or "") + json.dumps(t.input_schema, separators=(",", ":"))
        for t in visible
    )


async def test_the_surface_stays_within_its_budget():
    assert len(await _surface()) <= MAX_SURFACE_CHARS


@pytest.mark.parametrize("marker", RULES.values(), ids=RULES.keys())
async def test_each_hard_won_rule_is_stated_exactly_once(marker):
    assert (await _surface()).lower().count(marker) == 1


async def test_without_the_viewers_no_display_tool_is_named():
    assert "show_" not in await _surface(apps=False)


async def test_the_model_sees_the_loop_and_the_two_cards_only():
    _, visible = await _visible()
    assert {tool.name for tool in visible} == VISIBLE_TOOLS
