"""API tests for document edit draft responses."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    original = getattr(app.state, "document_edit_service", None)
    app.state.document_edit_service = svc
    yield svc
    app.state.document_edit_service = original


def _pending_command() -> dict:
    return {
        "id": "cmd-1",
        "analysisId": "a-1",
        "action": "update_page_element",
        "targetRef": "#/texts/12",
        "payload": {"content": "Updated content"},
        "actor": "user",
        "at": "2026-05-30T12:00:00+00:00",
        "status": "pending",
    }


def _tree(label: str = "Draft title") -> list[dict]:
    return [{"ref": "#/texts/12", "type": "title", "label": label, "children": []}]


def _pages() -> list[dict]:
    return [{"page_number": 1, "width": 600, "height": 800, "elements": []}]


class TestDocumentEditSessionRoutes:
    def test_get_session_returns_tree(self, client, mock_service):
        mock_service.get_session = AsyncMock(
            return_value={
                "analysisId": "a-1",
                "pages": _pages(),
                "tree": _tree(),
                "pendingCommands": [_pending_command()],
            }
        )

        resp = client.get("/api/documents/d-1/edits/session")

        assert resp.status_code == 200
        body = resp.json()
        assert body["tree"] == _tree()
        assert body["pendingCommands"][0]["action"] == "update_page_element"

    def test_apply_commands_returns_tree(self, client, mock_service):
        mock_service.apply_commands = AsyncMock(
            return_value={
                "analysisId": "a-1",
                "pages": _pages(),
                "tree": _tree("Updated heading"),
                "pendingCommands": [_pending_command()],
            }
        )

        resp = client.post(
            "/api/documents/d-1/edits/commands",
            json={
                "commands": [
                    {
                        "action": "update_page_element",
                        "targetRef": "#/texts/12",
                        "payload": {"content": "Updated content"},
                    }
                ]
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["tree"] == _tree("Updated heading")
        mock_service.apply_commands.assert_awaited_once()

    def test_commit_returns_tree(self, client, mock_service):
        mock_service.commit = AsyncMock(
            return_value={
                "committed": False,
                "consistent": False,
                "differences": [{"ref": "#/texts/12", "field": "content"}],
                "pages": _pages(),
                "tree": _tree("Backend truth"),
            }
        )

        resp = client.post(
            "/api/documents/d-1/edits/commit",
            json={"frontendPages": _pages()},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["committed"] is False
        assert body["tree"] == _tree("Backend truth")
