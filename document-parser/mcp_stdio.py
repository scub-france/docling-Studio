"""Run the MCP document server over stdio — the local-agent entry point.

Second composition entrypoint of the backend, beside `main.py`. Claude Code
and Claude Desktop launch a stdio server as a subprocess, so this module
builds only what the tools actually need — the two repositories and the
navigation service — instead of the full `AppStateBuilder` sequence. No
Docling import, no Neo4j dial-out, no converter: startup stays instant, which
matters when the client spawns the process on every session.

Register it with::

    claude mcp add docling-studio -- \\
        /abs/path/document-parser/.venv/bin/python /abs/path/document-parser/mcp_stdio.py

The venv interpreter is not optional: a bare `python` resolves against the
ambient interpreter, which does not carry the project's dependencies.

**Nothing may be written to stdout** — stdout is the JSON-RPC channel. Logging
is pinned to stderr below; a stray `print()` anywhere in the call path
corrupts the protocol stream.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from bootstrap.factories import build_navigation_service
from infra.settings import settings
from mcp_adapter import build_mcp_server, deps_present, deps_provenance
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_stdio")


async def _serve() -> None:
    # Creates the SQLite file and applies migrations when absent. Harmless
    # against an existing database — the schema init is idempotent.
    await init_db()

    navigation = build_navigation_service(
        SqliteDocumentRepository(),
        SqliteAnalysisRepository(),
    )
    server = build_mcp_server(lambda: navigation, version=settings.app_version)
    logger.info("Docling Studio MCP (stdio) ready — db=%s", settings.db_path)
    await server.run_stdio_async()


def main() -> int:
    if not deps_present():
        logger.error(
            "The MCP SDK is not importable (%s). Install it with `uv sync --group mcp` "
            "and launch this script with the project venv's interpreter.",
            deps_provenance(),
        )
        return 1
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:  # pragma: no cover — client closed the pipe
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
