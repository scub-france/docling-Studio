"""One investigation, end to end: MCP client → composition root → SQLite.

The other suites each cut the stack somewhere — the service tests swap the
repository for a fake, the repository tests skip the adapter. This one runs
the wiring `bootstrap.factories` actually produces against a real database,
because that seam is where a feature that passes every unit test still fails
to start.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

pytest.importorskip(
    "mcp.server.mcpserver",
    reason="MCP SDK not installed — `uv sync --group mcp` to exercise the adapter",
)

from mcp import Client

from bootstrap.factories import build_document_tools
from domain.models import Document
from mcp_adapter import build_mcp_server
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.investigation_repo import SqliteInvestigationRepository
from tests.navigation_fixtures import (
    DOC_ID,
    PREAVIS_REF,
    PREAVIS_TEXT,
    anchor_uri,
    make_document,
    make_job,
)

PREAVIS_URI = anchor_uri(PREAVIS_REF)


@pytest.fixture
async def tools(monkeypatch, tmp_path):
    """The real wiring: SQLite journal, in-memory parse."""
    monkeypatch.setattr("persistence.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()
    # The journal's rows hang off `documents` by foreign key, so the row has
    # to exist even though the parse itself is served from the fixture.
    await SqliteDocumentRepository().insert(
        Document(id=DOC_ID, filename="contrat.pdf", storage_path="/tmp/contrat.pdf")
    )

    document_repo = AsyncMock()
    document_repo.find_all = AsyncMock(return_value=[make_document()])
    document_repo.find_by_id = AsyncMock(return_value=make_document())
    analysis_repo = AsyncMock()
    analysis_repo.find_latest_completed_by_document = AsyncMock(return_value=make_job())
    analysis_repo.find_by_id = AsyncMock(return_value=make_job())

    return build_document_tools(document_repo, analysis_repo, SqliteInvestigationRepository())


def _payload(result):
    assert result.is_error is False, result.content[0].text
    return result.structured_content


async def test_a_whole_investigation_survives_the_round_trip(tools):
    server = build_mcp_server(lambda: tools, version="test", apps=False)
    async with Client(server) as client:
        opened = _payload(
            await client.call_tool(
                "open_investigation",
                {"document": "contrat", "question": "Comment résilier le contrat ?"},
            )
        )
        planned = _payload(
            await client.call_tool(
                "plan_steps",
                {
                    "investigation_id": opened["investigation_id"],
                    "steps": [
                        {"question": "Quel est le préavis ?", "why": "la question en dépend"},
                        {"question": "Quelle indemnité ?", "why": "pour être complet"},
                    ],
                },
            )
        )

        # A wrong ref costs an attempt and does not settle the step.
        drifted = _payload(
            await client.call_tool(
                "record_attempt",
                {
                    "investigation_id": opened["investigation_id"],
                    "step_id": planned["first_step_id"],
                    "thought": "je crois que c'est six mois",
                    "uri": PREAVIS_URI,
                    "quote": "Le préavis est de six mois.",
                },
            )
        )
        assert drifted["outcome"] == "quote_drift"
        assert drifted["attempts_left"] == 2

        kept = _payload(
            await client.call_tool(
                "record_attempt",
                {
                    "investigation_id": opened["investigation_id"],
                    "step_id": planned["first_step_id"],
                    "thought": "la section 12.2 le dit littéralement",
                    "uri": PREAVIS_URI,
                    "quote": PREAVIS_TEXT,
                },
            )
        )
        assert kept["outcome"] == "kept"
        assert kept["next_step_id"] == planned["steps"][1]["step_id"]

        # The second step spends its budget and closes as a finding.
        for _ in range(3):
            spent = _payload(
                await client.call_tool(
                    "record_attempt",
                    {
                        "investigation_id": opened["investigation_id"],
                        "step_id": planned["steps"][1]["step_id"],
                        "thought": "rien sur l'indemnité ici",
                        "uri": PREAVIS_URI,
                        "quote": "Une indemnité forfaitaire est due.",
                    },
                )
            )
        assert spent["step_state"] == "unanswered"

        closed = _payload(
            await client.call_tool(
                "close_investigation",
                {
                    "investigation_id": opened["investigation_id"],
                    "answer": (
                        f"Le préavis est de trois mois ({PREAVIS_URI}). "
                        "Le document ne dit rien d'une indemnité."
                    ),
                },
            )
        )
        assert (closed["steps_answered"], closed["steps_unanswered"]) == (1, 1)

    # A second connection — the record outlived the session that made it.
    async with Client(build_mcp_server(lambda: tools, version="test", apps=False)) as client:
        view = _payload(
            await client.call_tool(
                "get_investigation", {"investigation_id": opened["investigation_id"]}
            )
        )

    assert view["state"] == "closed"
    assert [a["outcome"] for a in view["reasoning"][0]["attempts"]] == ["quote_drift", "kept"]
    assert view["reasoning"][0]["attempts"][1]["thought"] == "la section 12.2 le dit littéralement"
    assert [(n["ref"], n["status"]) for n in view["map"]] == [
        ("#/texts/0", "path"),
        ("#/texts/1", "path"),
        ("#/texts/3", "kept"),
    ]
