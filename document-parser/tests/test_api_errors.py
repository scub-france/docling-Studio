"""One translation of service and editor errors into HTTP (#396)."""

from __future__ import annotations

import pytest

from api.errors import to_http_error
from domain.analysis_editing import (
    AnalysisEditConflictError,
    AnalysisEditError,
    AnalysisEditNotFoundError,
    AnalysisEditUnavailableError,
)
from services.config_overrides import AppConfigReadOnlyError
from services.errors import ServiceError
from services.export_service import ExportNotFoundError
from services.store_service import StoreNotFoundError


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (AnalysisEditNotFoundError("Document not found: d"), 404),
        (AnalysisEditConflictError("stale sequence"), 409),
        (AnalysisEditUnavailableError("no canonical document"), 409),
        (AnalysisEditError("bad command"), 400),
        (StoreNotFoundError("Store not found"), 404),
        (AppConfigReadOnlyError("read-only"), 403),
        (ExportNotFoundError("nothing to export"), 404),
        (ServiceError("busy", http_status=503), 503),
    ],
)
def test_errors_map_to_their_status_and_keep_their_message(error, status):
    http = to_http_error(error)

    assert http.status_code == status
    assert http.detail == str(error)


def test_every_service_family_shares_the_base():
    from services.chunk_service import ChunkServiceError
    from services.graph_service import GraphServiceError
    from services.navigation_errors import NavigationServiceError
    from services.reasoning_service import ReasoningServiceError
    from services.store_service import StoreServiceError
    from services.version_service import VersionServiceError

    for family in (
        ChunkServiceError,
        VersionServiceError,
        GraphServiceError,
        NavigationServiceError,
        ReasoningServiceError,
        StoreServiceError,
        AppConfigReadOnlyError,
        ExportNotFoundError,
    ):
        assert issubclass(family, ServiceError)
