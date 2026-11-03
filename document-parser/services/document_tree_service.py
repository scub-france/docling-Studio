"""Document tree service — the outline the Chunks view draws beside the chunks.

Reads the requested (or latest completed) analysis of a document and hands
its parse to the pure projection in `domain/doc_tree.py`. Split out of
`ChunkService`, which edits the chunkset and never needed the parse
(audit 0.7.4, 03 MAJ 3.3.2).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from domain.doc_tree import build_doc_tree
from domain.models import AnalysisStatus
from services.chunk_errors import ChunkNotFoundError, require_document

if TYPE_CHECKING:
    from domain.ports import AnalysisRepository, DocumentRepository, DocumentTreeReader

logger = logging.getLogger(__name__)


class DocumentTreeService:
    """Builds the `[DocTreeNode]` outline of a document from one of its analyses."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        tree_reader: DocumentTreeReader,
    ) -> None:
        self._documents = document_repo
        self._analyses = analysis_repo
        self._tree = tree_reader

    async def get_tree(self, document_id: str, analysis_id: str | None = None) -> list[dict]:
        """Build a doc tree from the requested or latest completed analysis.

        Returns a list of `DocTreeNode`-shaped dicts. Empty list if no
        analysis is available yet — caller decides if that is an error or
        just "not parsed yet". A requested analysis that is not a completed
        analysis of this document is a 404 (`ChunkNotFoundError`).
        """
        await require_document(self._documents, document_id)
        if analysis_id:
            job = await self._analyses.find_by_id(analysis_id)
            if not job or job.document_id != document_id or job.status != AnalysisStatus.COMPLETED:
                raise ChunkNotFoundError(f"Analysis not found: {analysis_id}")
        else:
            job = await self._analyses.find_latest_completed_by_document(document_id)
        if not job or not job.document_json:
            return []
        try:
            doc_data = json.loads(job.document_json)
        except json.JSONDecodeError:
            logger.exception("Invalid document_json for analysis %s", job.id)
            return []
        return build_doc_tree(doc_data, self._tree)
