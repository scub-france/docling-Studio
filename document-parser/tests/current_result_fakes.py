"""A stand-in for the editor's `ActiveAnalysisResultReader`, shared by tests.

Services that read the current analysis with its saved edits take this port.
Tests that do not exercise the editor give them this reader: the current
analysis as stored, as if it had no saved edits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.analysis_editing import AnalysisEditNotFoundError, EditorSnapshot

if TYPE_CHECKING:
    from domain.models import AnalysisJob
    from domain.ports import AnalysisRepository, CurrentAnalysisReader


class UneditedResultReader:
    """Reads the current (or requested) analysis as stored: no saved edits."""

    def __init__(
        self, current_analysis: CurrentAnalysisReader, analysis_repo: AnalysisRepository
    ) -> None:
        self._current = current_analysis
        self._analyses = analysis_repo

    async def load_current_edited(self, document_id: str) -> EditorSnapshot:
        job = await self._current.load_current_original(document_id)
        if job is None:
            raise AnalysisEditNotFoundError("This document has no active analysis")
        return _snapshot(job)

    async def load_editor(self, document_id: str, analysis_id: str | None = None) -> EditorSnapshot:
        if analysis_id is None:
            return await self.load_current_edited(document_id)
        job = await self._analyses.find_by_id(analysis_id)
        if job is None or job.document_id != document_id:
            raise AnalysisEditNotFoundError(f"Analysis not found: {analysis_id}")
        return _snapshot(job)


def _snapshot(job: AnalysisJob) -> EditorSnapshot:
    return EditorSnapshot(
        job=job,
        projection=None,
        applied_through_sequence=0,
        chunks_stale=False,
        base_analysis_id=job.id,
    )
