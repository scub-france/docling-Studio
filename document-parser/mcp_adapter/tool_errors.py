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
        # Cancellation (and every other BaseException) is not a tool failure:
        # it must reach the task that owns it, or a client hanging up turns
        # into one error report per in-flight call.
        if exc is None or not isinstance(exc, Exception):
            return False
        if isinstance(exc, NavigationServiceError | AnchorParseError):
            # Includes NavigationUnavailableError — "still booting" is a
            # service state, not a crash, and the agent can act on it. And
            # the whole investigation family (#329), whose rejections are
            # part of the protocol rather than failures of it.
            raise ToolError(str(exc)) from exc
        # Anything else is a crash, and its text belongs to the server log:
        # an OSError names the storage path, a driver error the SQL.
        logger.exception("Unhandled error in MCP tool")
        raise ToolError("Internal error — the server log has the details.") from exc
