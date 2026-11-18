"""Shared fixtures for Neo4j integration tests.

These tests are skipped unless a live Neo4j is reachable via NEO4J_TEST_URI
(defaulting to bolt://localhost:7687). No CI workflow starts a Neo4j service,
so they are skipped in CI; to run them locally, start one with
`docker compose -f docker-compose.dev.yml up neo4j` (`neo4j:5.15-community`).
"""

from __future__ import annotations

import os

import pytest

# Skip the entire module cleanly when the neo4j driver package is absent
# (e.g. local dev without the dependency installed).
pytest.importorskip("neo4j")

from infra.neo4j import close_driver, get_driver


def _cfg() -> tuple[str, str, str]:
    return (
        os.environ.get("NEO4J_TEST_URI", "bolt://localhost:7687"),
        os.environ.get("NEO4J_TEST_USER", "neo4j"),
        os.environ.get("NEO4J_TEST_PASSWORD", "changeme"),
    )


@pytest.fixture
async def neo4j_driver():
    uri, user, password = _cfg()
    try:
        neo = await get_driver(uri, user, password)
    except Exception as exc:
        pytest.skip(f"Neo4j not reachable at {uri}: {exc}")
    # Wipe DB before each test — integration tests assume an empty graph.
    async with neo.driver.session(database=neo.database) as session:
        await session.run("MATCH (n) DETACH DELETE n")
    yield neo
    await close_driver()
