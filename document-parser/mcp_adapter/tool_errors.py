"""Turning a service rejection into something an agent can act on.

Shared by every tool module in this package rather than kept beside the four
that happened to need it first. Two pieces, both small and both load-bearing:
the error translation, and the anchor parse that has to fail *before* a
service is called so a malformed uri reads as "you built an anchor" instead
of "the document is missing".
"""

from __future__ import annotations

import logging

from mcp.server.mcpserver.exceptions import ToolError

from domain.anchors import AnchorParseError, DocumentAnchor
from services.navigation_errors import NavigationServiceError

logger = logging.getLogger(__name__)


def parse_anchor(uri: str) -> DocumentAnchor:
    try:
        return DocumentAnchor.parse(uri)
    except AnchorParseError as exc:
        raise ToolError(str(exc)) from exc


class ToolErrors:
    """Translate service errors into MCP tool errors.

    An async context manager rather than a decorator so each tool keeps its
    own signature — the SDK derives the input schema from it, so wrapping the
    functions would erase the schema the agent reads.
    """

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            return False
        if isinstance(exc, NavigationServiceError | AnchorParseError):
            # Includes NavigationUnavailableError — "still booting" is a
            # service state, not a crash, and the agent can act on it. And
            # the whole investigation family (#329), whose rejections are
            # part of the protocol rather than failures of it.
            raise ToolError(str(exc)) from exc
        logger.exception("Unhandled error in MCP tool")
        raise ToolError(f"Internal error: {exc}") from exc
