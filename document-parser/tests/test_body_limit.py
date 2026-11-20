"""Body ceiling of `POST /api/analyses/import` (08 MIN: unbounded Docling JSON)."""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infra.body_limit import BodySizeLimitMiddleware

IMPORT = "/api/analyses/import"


def _client(max_bytes: int) -> TestClient:
    app = FastAPI()

    @app.post(IMPORT)
    async def import_analysis(body: dict) -> dict:
        return {"keys": sorted(body)}

    @app.post("/api/other")
    async def other(body: dict) -> dict:
        return {"keys": sorted(body)}

    app.add_middleware(
        BodySizeLimitMiddleware, path=IMPORT, max_bytes=max_bytes, detail="Too large"
    )
    return TestClient(app)


def test_a_body_under_the_limit_reaches_the_route():
    with _client(1024) as client:
        response = client.post(IMPORT, json={"documentId": "d1", "document": {}})

    assert response.status_code == 200
    assert response.json() == {"keys": ["document", "documentId"]}


def test_a_declared_length_over_the_limit_answers_413():
    with _client(16) as client:
        response = client.post(IMPORT, json={"document": "x" * 64})

    assert response.status_code == 413
    assert response.json() == {"detail": "Too large"}


def test_a_chunked_body_over_the_limit_answers_413():
    # No Content-Length: the body is counted as it arrives.
    payload = json.dumps({"document": "x" * 64}).encode()
    with _client(16) as client:
        response = client.post(
            IMPORT,
            content=iter([payload[:10], payload[10:]]),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413


@pytest.mark.parametrize("declared", ["²", "12a", "-1", "", "1" * 21])
async def test_a_malformed_declared_length_answers_400(declared):
    # Driven at the ASGI level: HTTP clients will not send these lengths.
    sent: list[dict] = []

    async def app(scope, receive, send):
        raise AssertionError("the app must not run")

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message):
        sent.append(message)

    guard = BodySizeLimitMiddleware(app, path=IMPORT, max_bytes=1024, detail="Too large")
    scope = {
        "type": "http",
        "method": "POST",
        "path": IMPORT,
        "headers": [(b"content-length", declared.encode("latin-1"))],
    }
    await guard(scope, receive, send)

    assert sent[0]["status"] == 400
    assert json.loads(sent[1]["body"]) == {"detail": "Invalid Content-Length header"}


def test_other_routes_are_not_limited():
    with _client(16) as client:
        response = client.post("/api/other", json={"document": "x" * 64})

    assert response.status_code == 200
