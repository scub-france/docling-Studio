"""HTTP contract of the analysis editor routes, on a real service and database (#399)."""

from __future__ import annotations

import asyncio

import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.analysis_edits import router
from api.state import AppState, get_app_state
from domain.models import AnalysisJob, AnalysisStatus, Document, DocumentAnalysisSelection
from infra.docling_analysis_engine import DoclingAnalysisEngine
from persistence import database
from persistence.analysis_edit_repo import SqliteAnalysisEditRepository
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.document_analysis_repo import SqliteDocumentAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository
from services.analysis_edit_service import AnalysisEditService

BASE = "/api/documents/doc-1"


def _docling_json() -> str:
    document = DoclingDocument(name="fixture")
    document.add_heading(text="Heading", level=1)
    document.add_text(label=DocItemLabel.TEXT, text="First")
    document.add_text(label=DocItemLabel.TEXT, text="Second")
    document.add_text(label=DocItemLabel.TEXT, text="Third")
    return document.model_dump_json()


async def _seed_service() -> AnalysisEditService:
    await database.init_db()
    documents = SqliteDocumentRepository()
    analyses = SqliteAnalysisRepository()
    state = SqliteDocumentAnalysisRepository()
    await documents.insert(
        Document(id="doc-1", filename="fixture.pdf", storage_path="/tmp/fixture.pdf")
    )
    job = AnalysisJob(
        id="analysis-1",
        document_id="doc-1",
        status=AnalysisStatus.COMPLETED,
        content_markdown="First",
        content_html="<p>First</p>",
        pages_json="[]",
        document_json=_docling_json(),
    )
    await analyses.insert(job)
    await analyses.update_status(job)
    await state.select(DocumentAnalysisSelection("doc-1", "analysis-1"))
    return AnalysisEditService(
        analysis_repo=analyses,
        document_repo=documents,
        selection_repo=state,
        chunk_source_repo=state,
        edit_repo=SqliteAnalysisEditRepository(),
        engine=DoclingAnalysisEngine(),
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "editor-api.db"))
    service = asyncio.run(_seed_service())
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_app_state] = lambda: AppState(analysis_edit_service=service)
    with TestClient(app) as test_client:
        yield test_client


def _first_text_id(client: TestClient) -> str:
    return _ids_by_text(client)["First"]


def _ids_by_text(client: TestClient) -> dict[str, str]:
    model = client.get(f"{BASE}/analysis-editor").json()["model"]
    return {element["text"]: element["id"] for element in model["elements"] if element["text"]}


def _texts_in_reading_order(body: dict) -> list[str]:
    by_id = {element["id"]: element for element in body["model"]["elements"]}
    return [by_id[i]["text"] for i in body["readingOrder"] if by_id[i]["text"] is not None]


def _element_with_text(body: dict, text: str) -> dict:
    return next(element for element in body["model"]["elements"] if element["text"] == text)


def _preview(client: TestClient, *commands: dict):
    return client.post(f"{BASE}/analysis-edits/preview", json={"commands": list(commands)})


def _replace(element_id: str, text: str) -> dict:
    return {"type": "replaceText", "elementId": element_id, "text": text}


# --- Happy paths: one per route ---------------------------------------------


def test_load_returns_the_active_analysis_with_its_editor_model(client):
    response = client.get(f"{BASE}/analysis-editor")

    assert response.status_code == 200
    body = response.json()
    assert body["model"]["baseAnalysisId"] == "analysis-1"
    assert body["appliedThroughSequence"] == 0
    assert body["readingOrder"] == [element["id"] for element in body["model"]["elements"]]
    assert "First" in body["result"]["contentMarkdown"]


def test_preview_projects_pending_commands_without_saving(client):
    element_id = _first_text_id(client)

    response = client.post(
        f"{BASE}/analysis-edits/preview",
        json={"commands": [_replace(element_id, "Previewed")]},
    )

    assert response.status_code == 200
    assert response.json()["appliedThroughSequence"] == 1
    assert "Previewed" in response.json()["result"]["contentMarkdown"]
    assert client.get(f"{BASE}/analysis-edits/history").json() == []


def test_save_appends_the_commands_and_returns_the_edited_result(client):
    element_id = _first_text_id(client)

    response = client.post(
        f"{BASE}/analysis-edits",
        json={"commands": [_replace(element_id, "Saved")], "expectedAppliedThroughSequence": 0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["baseAnalysisId"] == "analysis-1"
    assert body["appliedThroughSequence"] == 1
    assert "Saved" in body["result"]["contentMarkdown"]


def test_history_lists_saved_commands_with_their_state(client):
    element_id = _first_text_id(client)
    client.post(
        f"{BASE}/analysis-edits",
        json={"commands": [_replace(element_id, "Saved")], "expectedAppliedThroughSequence": 0},
    )

    response = client.get(f"{BASE}/analysis-edits/history")

    assert response.status_code == 200
    [entry] = response.json()
    assert (entry["sequence"], entry["commandType"], entry["active"]) == (1, "replaceText", True)


def test_set_active_reverts_a_saved_command(client):
    element_id = _first_text_id(client)
    client.post(
        f"{BASE}/analysis-edits",
        json={"commands": [_replace(element_id, "Saved")], "expectedAppliedThroughSequence": 0},
    )

    response = client.patch(
        f"{BASE}/analysis-edits/history/1",
        json={"active": False, "expectedAppliedThroughSequence": 1},
    )

    assert response.status_code == 200
    assert response.json()["appliedThroughSequence"] == 2
    assert "Saved" not in response.json()["result"]["contentMarkdown"]


def test_history_marks_a_reverted_command_and_its_toggle(client):
    element_id = _first_text_id(client)
    client.post(
        f"{BASE}/analysis-edits",
        json={"commands": [_replace(element_id, "Saved")], "expectedAppliedThroughSequence": 0},
    )
    client.patch(
        f"{BASE}/analysis-edits/history/1",
        json={"active": False, "expectedAppliedThroughSequence": 1},
    )

    entries = client.get(f"{BASE}/analysis-edits/history").json()

    assert [(e["sequence"], e["commandType"], e["active"]) for e in entries] == [
        (1, "replaceText", False),
        (2, "setCommandActive", None),
    ]


def test_rebuild_replays_the_saved_stream(client):
    element_id = _first_text_id(client)
    client.post(
        f"{BASE}/analysis-edits",
        json={"commands": [_replace(element_id, "Saved")], "expectedAppliedThroughSequence": 0},
    )

    response = client.post(f"{BASE}/analysis-edits/rebuild")

    assert response.status_code == 200
    assert "Saved" in response.json()["result"]["contentMarkdown"]


# --- Every command type the request schema accepts, through HTTP -------------


def test_set_heading_level_changes_the_heading_level(client):
    ids = _ids_by_text(client)

    response = _preview(
        client, {"type": "setHeadingLevel", "elementId": ids["Heading"], "level": 3}
    )

    assert response.status_code == 200
    assert _element_with_text(response.json(), "Heading")["headingLevel"] == 3
    assert "### Heading" in response.json()["result"]["contentMarkdown"]


def test_merge_text_joins_the_paragraphs_with_the_separator(client):
    ids = _ids_by_text(client)

    response = _preview(
        client,
        {"type": "mergeText", "elementIds": [ids["First"], ids["Second"]], "separator": " + "},
    )

    assert response.status_code == 200
    assert _texts_in_reading_order(response.json()) == ["Heading", "First + Second", "Third"]


def test_delete_element_removes_one_element(client):
    ids = _ids_by_text(client)

    response = _preview(client, {"type": "deleteElement", "elementId": ids["Second"]})

    assert response.status_code == 200
    assert _texts_in_reading_order(response.json()) == ["Heading", "First", "Third"]


def test_delete_elements_removes_every_listed_element(client):
    ids = _ids_by_text(client)

    response = _preview(
        client, {"type": "deleteElements", "elementIds": [ids["First"], ids["Third"]]}
    )

    assert response.status_code == 200
    assert _texts_in_reading_order(response.json()) == ["Heading", "Second"]


def test_move_element_before_another_element(client):
    ids = _ids_by_text(client)

    response = _preview(
        client,
        {"type": "moveElement", "elementId": ids["Third"], "beforeElementId": ids["First"]},
    )

    assert response.status_code == 200
    assert _texts_in_reading_order(response.json()) == ["Heading", "Third", "First", "Second"]


def test_move_element_after_a_target(client):
    ids = _ids_by_text(client)

    response = _preview(
        client,
        {
            "type": "moveElement",
            "elementId": ids["First"],
            "targetElementId": ids["Third"],
            "placement": "after",
        },
    )

    assert response.status_code == 200
    assert _texts_in_reading_order(response.json()) == ["Heading", "Second", "Third", "First"]


def test_move_element_inside_a_heading(client):
    ids = _ids_by_text(client)

    response = _preview(
        client,
        {
            "type": "moveElement",
            "elementId": ids["Third"],
            "targetElementId": ids["Heading"],
            "placement": "inside",
        },
    )

    assert response.status_code == 200
    body = response.json()
    heading = _element_with_text(body, "Heading")
    assert _element_with_text(body, "Third")["parentId"] == heading["id"]
    assert heading["children"] == [_element_with_text(body, "Third")["id"]]


def test_merge_of_a_heading_with_a_paragraph_is_a_bad_request(client):
    ids = _ids_by_text(client)

    response = _preview(client, {"type": "mergeText", "elementIds": [ids["Heading"], ids["First"]]})

    assert response.status_code == 400
    assert "merged" in response.json()["detail"]


# --- Error cases --------------------------------------------------------------


def test_missing_document_is_not_found(client):
    response = client.get("/api/documents/missing/analysis-editor")

    assert response.status_code == 404
    assert "Document not found" in response.json()["detail"]


def test_missing_analysis_is_not_found(client):
    response = client.get(f"{BASE}/analysis-editor", params={"analysisId": "missing"})

    assert response.status_code == 404
    assert "Analysis not found" in response.json()["detail"]


def test_save_against_a_stale_sequence_is_a_conflict(client):
    element_id = _first_text_id(client)

    response = client.post(
        f"{BASE}/analysis-edits",
        json={"commands": [_replace(element_id, "Late")], "expectedAppliedThroughSequence": 5},
    )

    assert response.status_code == 409
    assert client.get(f"{BASE}/analysis-edits/history").json() == []


def test_command_on_an_unknown_element_is_a_bad_request(client):
    response = client.post(
        f"{BASE}/analysis-edits/preview",
        json={"commands": [_replace("analysis-1:#/texts/99", "Nope")]},
    )

    assert response.status_code == 400
    assert "Unknown editor element" in response.json()["detail"]


def test_unknown_command_type_is_rejected_by_validation(client):
    response = client.post(
        f"{BASE}/analysis-edits/preview",
        json={"commands": [{"type": "rewriteEverything", "elementId": "x"}]},
    )

    assert response.status_code == 422
