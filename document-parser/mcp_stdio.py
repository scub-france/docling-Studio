"""Run the MCP document server over stdio — the local-agent entry point.

Second composition entrypoint of the backend, beside `main.py`. Claude Code
and Claude Desktop launch a stdio server as a subprocess, so this module
builds only what the tools actually need — the three repositories and the
document services over them — instead of the full `AppStateBuilder` sequence. No
Docling import, no Neo4j dial-out, no converter: startup stays instant, which
matters when the client spawns the process on every session.

Register it with::

    claude mcp add docling-studio -- \\
        /abs/path/document-parser/.venv/bin/python /abs/path/document-parser/mcp_stdio.py

The venv interpreter is not optional: a bare `python` resolves against the
ambient interpreter, which does not carry the project's dependencies.

The database is Studio's own: `DB_PATH` read as the backend reads it, relative
to this directory rather than to wherever the client spawned the process. A
missing file stops the server with a message instead of serving an empty one.

**Nothing may be written to stdout** — stdout is the JSON-RPC channel. Logging
is pinned to stderr below; a stray `print()` anywhere in the call path
corrupts the protocol stream.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("mcp_stdio")

BACKEND_DIR = Path(__file__).resolve().parent


def db_path() -> Path:
    """`DB_PATH`, resolved against the backend directory when relative."""
    raw = Path(os.environ.get("DB_PATH") or "./data/docling_studio.db")
    return raw if raw.is_absolute() else BACKEND_DIR / raw


async def _serve() -> None:
    # Imported once DB_PATH is pinned: `persistence` and `settings` read it at
    # import time.
    from bootstrap.factories import build_document_tools
    from infra.settings import settings
    from mcp_adapter import build_mcp_server
    from persistence.analysis_repo import SqliteAnalysisRepository
    from persistence.database import init_db
    from persistence.document_repo import SqliteDocumentRepository
    from persistence.investigation_repo import SqliteInvestigationRepository

    # Applies pending migrations; idempotent against an up-to-date database.
    await init_db()

    tools = build_document_tools(
        SqliteDocumentRepository(),
        SqliteAnalysisRepository(),
        SqliteInvestigationRepository(),
    )
    server = build_mcp_server(
        lambda: tools,
        version=settings.app_version,
        apps=settings.mcp_apps_enabled,
        cache_ttl_seconds=settings.mcp_cache_ttl_seconds,
        investigations=settings.mcp_investigation_enabled,
    )
    logger.info("Docling Studio MCP (stdio) ready — db=%s", settings.db_path)
    await server.run_stdio_async()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        stream=sys.stderr,
    )
    db = db_path()
    if not db.is_file():
        logger.error(
            "No Docling Studio database at %s. Start Docling Studio once to create it, "
            "or set DB_PATH to its database file.",
            db,
        )
        return 1
    os.environ["DB_PATH"] = str(db)
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:  # pragma: no cover — client closed the pipe
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
