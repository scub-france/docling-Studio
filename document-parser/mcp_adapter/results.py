"""A tool result with a compact text copy, not a pretty-printed one (#363).

The SDK's default builds the text block of every result as the same JSON as
`structuredContent`, indented: on a read that is a third of the bytes spent on
whitespace, sent on every call. A host that hands the text to the model pays
for it in tokens. This builds both copies from one dump, with the text
compact — still JSON, so anything that parses the text block (a card on a
host that forwards only the content) reads exactly what it read before.

The page tools keep the default on purpose: their payload is an image, and
the indentation is noise next to it.
"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import TypeAdapter


@cache
def _adapter(kind: type) -> TypeAdapter[Any]:
    return TypeAdapter(kind)


def compact(value: Any) -> CallToolResult:
    """`value` as structured content, and once more as compact JSON text."""
    data = _adapter(type(value)).dump_python(value, mode="json")
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=data)
