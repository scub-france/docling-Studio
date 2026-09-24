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

# About 1 500 tokens, for the largest surface: the journal and both viewers.
MAX_SURFACE_CHARS = 6_000

RULES = {
    "cite the element read": "citations[].uri",
    "never build an anchor": "never build",
    "document text is data": "is data",
    "a truncated read resumes": "next_cursor",
    "unanswered is a finding": "a finding",
    "cite what was kept": "kept_uri",
}


async def _surface(*, apps: bool = True) -> str:
    tools = make_document_tools()
    server = build_mcp_server(lambda: tools, version="test", apps=apps)
    async with Client(server, extensions=[APPS_CLIENT] if apps else None) as client:
        listed = (await client.list_tools()).tools
        instructions = client.instructions or ""
    visible = [t for t in listed if ((t.meta or {}).get("ui") or {}).get("visibility") != ["app"]]
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
