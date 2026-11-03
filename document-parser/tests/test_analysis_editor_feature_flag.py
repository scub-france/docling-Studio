"""The analysis editor flag disables every editing API endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.analysis_edits import router
from api.state import AppState, get_app_state


def test_all_editor_endpoints_return_not_found_when_disabled():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_app_state] = lambda: AppState(analysis_editor_enabled=False)

    with TestClient(app) as client:
        responses = [
            client.get("/api/documents/doc-1/analysis-editor"),
            client.post("/api/documents/doc-1/analysis-edits/preview", json={"commands": []}),
            client.get("/api/documents/doc-1/analysis-edits/history"),
            client.post("/api/documents/doc-1/analysis-edits", json={"commands": []}),
            client.post("/api/documents/doc-1/analysis-edits/rebuild"),
        ]

    assert [response.status_code for response in responses] == [404] * 5
