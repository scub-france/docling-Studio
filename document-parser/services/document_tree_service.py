"""Document tree service — the outline of a document's analysis result.

Reads the requested or current analysis and projects its Docling document
into a `[DocTreeNode]` outline (`domain.document_tree`).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from domain.analysis_editing import AnalysisEditUnavailableError
from domain.document_tree import build_tree_nodes
from domain.models import AnalysisStatus
from services.chunk_errors import ChunkNotFoundError, require_document

if TYPE_CHECKING:
    from domain.ports import (
        ActiveAnalysisResultReader,
        AnalysisRepository,
        CurrentAnalysisReader,
        DocumentRepository,
        DocumentTreeReader,
    )

logger = logging.getLogger(__name__)


class DocumentTreeService:
    """Builds the document tree from an analysis's `document_json`."""

    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        current_analysis: CurrentAnalysisReader,
        tree_reader: DocumentTreeReader,
        active_result_service: ActiveAnalysisResultReader | None = None,
    ) -> None:
        self._documents = document_repo
        self._analyses = analysis_repo
        self._current = current_analysis
        # `DocumentTreeReader` port (#audit-01) — replaces the local
        # `from infra.docling_tree import ...` smell hiding inside two
        # tree-walking helpers. Required so the tree views stay rendable.
        self._tree = tree_reader
        self._active_result_service = active_result_service

    async def get_tree(self, document_id: str, analysis_id: str | None = None) -> list[dict]:
        """Build a doc tree from the requested or active analysis.

        Returns a list of `DocTreeNode`-shaped dicts (camelCase). Empty
        list if no analysis is available yet — caller decides if that is
        an error or just "not parsed yet".
        """
        await require_document(self._documents, document_id)
        if analysis_id:
            job = await self._analyses.find_by_id(analysis_id)
            if not job or job.document_id != document_id or job.status != AnalysisStatus.COMPLETED:
                raise ChunkNotFoundError(f"Analysis not found: {analysis_id}")
        else:
            if self._active_result_service is not None:
                try:
                    job = (await self._active_result_service.load_active_result(document_id)).job
                except AnalysisEditUnavailableError:
                    return []
            else:
                job = await self._current.load_current_analysis(document_id)
        if not job or not job.document_json:
            return []
        try:
            doc_data = json.loads(job.document_json)
        except json.JSONDecodeError:
            logger.exception("Invalid document_json for analysis %s", job.id)
            return []
        return build_tree_nodes(doc_data, self._tree)
