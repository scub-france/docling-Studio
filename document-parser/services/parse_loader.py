"""Resolving `(document, version)` to a navigable parse — once, and cached.

Every document-agent use case starts the same way: find the document, pick
the analysis the anchor pins (or the latest), and turn its stored JSON into
an index. That sequence was duplicated inside each service and is the single
reason they all needed the same three repositories; it lives here instead.

The cache is what makes an anchor cheap to follow. A parse is immutable for a
given analysis id — that is the whole point of pinning the version — so a
cached index can never be stale, only large. Hence two bounds rather than
one: entries, and the source JSON those entries were built from.
"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.parse_index import build_index
from services.navigation_errors import DocumentNotFoundError, NoParseError

if TYPE_CHECKING:
    from domain.models import AnalysisJob, Document
    from domain.parse_index import DocumentIndex
    from domain.ports import AnalysisRepository, DocumentRepository, DocumentTreeReader
    from services.navigation_config import NavigationConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedParse:
    """A document, the parse being read, and its navigable index."""

    document: Document
    job: AnalysisJob
    index: DocumentIndex

    @property
    def version_id(self) -> str:
        return self.job.id


class ParseLoader:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        tree_reader: DocumentTreeReader,
        config: NavigationConfig,
    ) -> None:
        self._documents = document_repo
        self._analyses = analysis_repo
        self._tree = tree_reader
        self._config = config
        # ref -> (index, source length). Ordered by recency of use.
        self._cache: OrderedDict[str, tuple[DocumentIndex, int]] = OrderedDict()

    @property
    def analyses(self) -> AnalysisRepository:
        """The analysis repository, for callers that need the *latest* parse
        of a document rather than the one an anchor pins."""
        return self._analyses

    @property
    def documents(self) -> DocumentRepository:
        return self._documents

    async def load(self, document_id: str, version_id: str | None = None) -> LoadedParse:
        """Resolve a document and the parse to read it from.

        `version_id` pins a specific analysis; omitting it takes the latest
        completed one. A version that belongs to another document is refused
        rather than silently ignored — an anchor that names the wrong parse is
        a bug in the caller, not a fallback case.
        """
        doc = await self._documents.find_by_id(document_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document not found: {document_id}")

        if version_id:
            job = await self._analyses.find_by_id(version_id)
            if job is None or job.document_id != document_id:
                raise NoParseError(
                    f"Version {version_id} does not belong to document {document_id}.",
                    http_status=404,
                )
        else:
            job = await self._analyses.find_latest_completed_by_document(document_id)

        if job is None or not job.document_json:
            raise NoParseError(
                f"Document {document_id} has no parsed content to navigate yet. "
                "Run an analysis in Docling Studio first."
            )

        return LoadedParse(document=doc, job=job, index=self._index_for(job))

    def _index_for(self, job: AnalysisJob) -> DocumentIndex:
        cached = self._cache.get(job.id)
        if cached is not None:
            self._cache.move_to_end(job.id)
            return cached[0]

        raw = job.document_json or "{}"
        try:
            doc_data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.exception("Invalid document_json for analysis %s", job.id)
            raise NoParseError(
                f"The stored parse for version {job.id} is unreadable.", http_status=500
            ) from exc

        index = build_index(doc_data, self._tree)
        self._cache[job.id] = (index, len(raw))
        self._evict()
        return index

    def _evict(self) -> None:
        """Drop least-recently-used entries until both bounds hold.

        The newest entry is never evicted: a single parse larger than the byte
        bound must still be navigable, and returning an index the caller
        cannot use would trade a memory problem for a broken read.
        """
        while len(self._cache) > 1 and (
            len(self._cache) > self._config.index_cache_size
            or sum(size for _, size in self._cache.values()) > self._config.index_cache_max_chars
        ):
            evicted, _ = self._cache.popitem(last=False)
            logger.debug("Evicted parse index %s", evicted)
