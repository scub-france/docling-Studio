"""Which analysis is a document's current one: decided here, once (02-2.3.1).

The rule itself is `domain.models.resolve_current_analysis_id`: the active
selection, or for a document with no state row the latest completed analysis
with a Docling document. This module only feeds it. Every reader that picks
an analysis without being told which one asks here: the editor and its
edited result, chunk generation, the tree, exports, Ask and the MCP tools.
What each one reads from that analysis stays its own decision: the original
result (`load_current_original`, here) or the result with saved edits
(`load_current_edited`, on the editor service).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.models import resolve_current_analysis_id

if TYPE_CHECKING:
    from domain.models import AnalysisJob
    from domain.ports import AnalysisRepository, DocumentAnalysisStateRepository


class CurrentAnalysisResolver:
    """Implements the `CurrentAnalysisReader` port over the state and analysis repositories."""

    def __init__(
        self,
        *,
        state_repo: DocumentAnalysisStateRepository,
        analysis_repo: AnalysisRepository,
    ) -> None:
        self._states = state_repo
        self._analyses = analysis_repo

    async def find_current_analysis_ids(self, document_ids: list[str]) -> dict[str, str]:
        """Each document's current analysis id; documents without one are left out.

        Two queries at most whatever the count: the state rows, then the
        latest parse of the documents that have no row.
        """
        if not document_ids:
            return {}
        states = await self._states.find_states(document_ids)
        without_state = [doc_id for doc_id in document_ids if doc_id not in states]
        latest = await self._analyses.find_latest_parsed_ids(without_state) if without_state else {}
        current: dict[str, str] = {}
        for doc_id in document_ids:
            analysis_id = resolve_current_analysis_id(states.get(doc_id), latest.get(doc_id))
            if analysis_id is not None:
                current[doc_id] = analysis_id
        return current

    async def find_current_analysis_id(self, document_id: str) -> str | None:
        return (await self.find_current_analysis_ids([document_id])).get(document_id)

    async def find_current_parse_ids(self, document_ids: list[str]) -> dict[str, str]:
        """Like `find_current_analysis_ids`, keeping only analyses with a parse.

        One more query: a selected analysis may have completed without a
        Docling document, and the MCP tools can only navigate a parse.
        """
        current = await self.find_current_analysis_ids(document_ids)
        if not current:
            return {}
        parsed = await self._analyses.find_parsed_ids(sorted(set(current.values())))
        return {doc_id: aid for doc_id, aid in current.items() if aid in parsed}

    async def load_current_original(self, document_id: str) -> AnalysisJob | None:
        """The current analysis as stored: its original result, saved edits excluded."""
        analysis_id = await self.find_current_analysis_id(document_id)
        if analysis_id is None:
            return None
        job = await self._analyses.find_by_id(analysis_id)
        if job is None or not job.can_be_current_of(document_id):
            return None
        return job
