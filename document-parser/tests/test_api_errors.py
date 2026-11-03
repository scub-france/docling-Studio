"""One handler answers every service rejection (#audit-05).

The routers no longer translate the service errors family by family: a
`ServiceError` reaches the app-level handler, which answers with the status
the error carries and the body an `HTTPException` would have had.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.errors import register_error_handlers
from services import chunk_errors, navigation_errors
from services.chunk_errors import ChunkConflictError, ChunkServiceError
from services.config_overrides import AppConfigError, AppConfigReadOnlyError
from services.document_service import DocumentFileError, PageNotFoundError, PageOutOfRangeError
from services.errors import ServiceError
from services.export_service import ExportNotFoundError
from services.graph_service import GraphServiceError, GraphTooLargeError
from services.navigation_errors import DocumentNotFoundError, NavigationServiceError
from services.reasoning_service import ReasoningServiceError
from services.store_service import StoreServiceError
from services.version_service import VersionServiceError


def _client_raising(exc: Exception) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise exc

    return TestClient(app, raise_server_exceptions=False)


# Each family's base, with the status it answered with before the handler.
FAMILIES = [
    (StoreServiceError, 400),
    (GraphServiceError, 500),
    (ChunkServiceError, 400),
    (VersionServiceError, 400),
    (ReasoningServiceError, 500),
    (NavigationServiceError, 500),
    (AppConfigError, 500),
]


class TestServiceErrorHandler:
    @pytest.mark.parametrize(("family", "status"), FAMILIES)
    def test_every_family_answers_with_its_own_status(self, family, status):
        assert issubclass(family, ServiceError)
        resp = _client_raising(family("nope")).get("/boom")
        assert resp.status_code == status
        assert resp.json() == {"detail": "nope"}

    @pytest.mark.parametrize(
        ("exc", "status"),
        [
            (ChunkConflictError("merge requires contiguous chunks"), 409),
            (AppConfigReadOnlyError("read-only"), 403),
            (DocumentNotFoundError("Document not found: d1"), 404),
            (GraphTooLargeError(300, 200), 413),
        ],
    )
    def test_a_subclass_status_wins(self, exc, status):
        resp = _client_raising(exc).get("/boom")
        assert resp.status_code == status
        assert resp.json() == {"detail": str(exc)}

    @pytest.mark.parametrize(
        ("exc", "status"),
        [
            (PageOutOfRangeError(10, 3), 400),
            (PageNotFoundError(4), 404),
            (DocumentFileError("Failed to generate preview"), 422),
            (ExportNotFoundError("JSON content not available"), 404),
        ],
    )
    def test_the_document_and_export_errors_join_the_contract(self, exc, status):
        """Once mapped one by one in `api/documents.py`; now the handler's."""
        assert isinstance(exc, ServiceError)
        resp = _client_raising(exc).get("/boom")
        assert resp.status_code == status
        assert resp.json() == {"detail": str(exc)}

    def test_a_raise_can_override_the_status(self):
        resp = _client_raising(ChunkServiceError("Chunker not configured", http_status=503)).get(
            "/boom"
        )
        assert resp.status_code == 503
        assert resp.json() == {"detail": "Chunker not configured"}

    def test_the_response_is_the_one_an_http_exception_gave(self):
        """Same status, body and content type as the `raise HTTPException(...)`
        the routers used to write by hand."""
        before = _client_raising(HTTPException(status_code=404, detail="Chunk not found: c1"))
        after = _client_raising(chunk_errors.ChunkNotFoundError("Chunk not found: c1"))
        old, new = before.get("/boom"), after.get("/boom")
        assert (new.status_code, new.json()) == (old.status_code, old.json())
        assert new.headers["content-type"] == old.headers["content-type"]

    def test_anything_else_is_still_a_500(self):
        resp = _client_raising(ValueError("Document not found: d1")).get("/boom")
        assert resp.status_code == 500


class TestOneDocumentNotFound:
    def test_the_chunk_service_raises_the_shared_class(self):
        assert chunk_errors.DocumentNotFoundError is navigation_errors.DocumentNotFoundError

    def test_the_version_and_export_services_raise_it_too(self):
        from services import export_service, version_service

        assert version_service.DocumentNotFoundError is DocumentNotFoundError
        assert export_service.DocumentNotFoundError is DocumentNotFoundError

    def test_it_stays_in_the_navigation_family_the_mcp_adapter_reports(self):
        assert issubclass(DocumentNotFoundError, NavigationServiceError)
        assert DocumentNotFoundError.http_status == 404
