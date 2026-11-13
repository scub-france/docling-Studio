"""Translate service and editor errors into HTTP responses, in one place (#396)."""

from __future__ import annotations

from fastapi import HTTPException

from domain.analysis_editing import (
    AnalysisEditConflictError,
    AnalysisEditError,
    AnalysisEditNotFoundError,
    AnalysisEditUnavailableError,
)
from services.errors import ServiceError

# Editor errors live in the domain, which knows nothing about HTTP: their
# status is decided here. Most specific class first.
_EDIT_ERROR_STATUS: tuple[tuple[type[AnalysisEditError], int], ...] = (
    (AnalysisEditNotFoundError, 404),
    (AnalysisEditConflictError, 409),
    (AnalysisEditUnavailableError, 409),
    (AnalysisEditError, 400),
)


def http_error(error: ServiceError | AnalysisEditError) -> HTTPException:
    """The HTTPException a router raises for a service or editor error."""
    if isinstance(error, ServiceError):
        status = error.http_status
    else:
        status = next(code for kind, code in _EDIT_ERROR_STATUS if isinstance(error, kind))
    return HTTPException(status_code=status, detail=str(error))
