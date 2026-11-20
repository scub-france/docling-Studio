"""Application service for the durable analysis editor."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.analysis_editing import (
    AnalysisEditConflictError,
    AnalysisEditError,
    AnalysisEditNotFoundError,
    AnalysisEditUnavailableError,
    CommandActivation,
    EditCommand,
    EditedAnalysisCache,
    EditHistoryEntry,
    EditorSnapshot,
    EditStream,
    ProjectedAnalysis,
    check_expected_sequence,
    get_last_sequence,
    hash_command_stream,
    hash_result,
    resolve_active_edit_commands,
)
from domain.models import AnalysisJob, AnalysisStatus

if TYPE_CHECKING:
    from domain.ports import (
        AnalysisDocumentEngine,
        AnalysisEditRepository,
        AnalysisRepository,
        ChunkRepository,
        CurrentAnalysisReader,
        DocumentAnalysisStateRepository,
        DocumentRepository,
        GraphWriter,
    )


ENGINE_VERSION = "analysis-editor-1"
logger = logging.getLogger(__name__)


class AnalysisEditService:
    """Coordinates replay, projection, and transactional materialization."""

    def __init__(
        self,
        *,
        analysis_repo: AnalysisRepository,
        document_repo: DocumentRepository,
        analysis_state_repo: DocumentAnalysisStateRepository,
        current_analysis: CurrentAnalysisReader,
        edit_repo: AnalysisEditRepository,
        engine: AnalysisDocumentEngine,
        graph_writer: GraphWriter | None = None,
        chunk_repo: ChunkRepository | None = None,
    ) -> None:
        self._analyses = analysis_repo
        self._documents = document_repo
        self._states = analysis_state_repo
        self._current = current_analysis
        self._edits = edit_repo
        self._engine = engine
        self._graph_writer = graph_writer
        self._chunks = chunk_repo
        self._unedited_projection: tuple[str, str, ProjectedAnalysis] | None = None

    async def load_editor(self, document_id: str, analysis_id: str | None = None) -> EditorSnapshot:
        document = await self._require_document(document_id)
        base = await self._load_base_analysis(document, analysis_id)
        stream = await self._edits.find_stream(base.id)
        stored = await self._edits.list_commands(base.id) if stream else []
        sequence = get_last_sequence(stored)
        if not stored:
            base_hash = hash_result(base.document_json)
            cached = self._unedited_projection
            if cached is not None and cached[0] == base.id and cached[1] == base_hash:
                return await self._build_snapshot(document, base, cached[2], sequence)
        cache = await self._edits.find_cache(base.id) if stream else None
        projection = None
        if (
            stream is not None
            and cache is not None
            # A working copy projected by another engine version is not
            # trusted: the stream is replayed by this one.
            and stream.engine_version == ENGINE_VERSION
            and cache.analysis_id == base.id
            and cache.applied_through_sequence == sequence
            and cache.command_stream_hash == hash_command_stream(stored, [])
        ):
            projection = await self._project_cache(base, cache)
        if projection is None:
            projection = await self._replay(base, stored)
        if not stored:
            self._unedited_projection = (base.id, base_hash, projection)
        return await self._build_snapshot(document, base, projection, sequence)

    async def load_current_edited(self, document_id: str) -> EditorSnapshot:
        """The current analysis with its saved edits, as document features read it.

        `CurrentAnalysisReader.load_current_original` reads the same analysis
        without its edits."""
        await self._require_document(document_id)
        analysis_id = await self._current.find_current_analysis_id(document_id)
        if analysis_id is None:
            raise AnalysisEditNotFoundError("This document has no active analysis")
        return await self.load_editor(document_id, analysis_id)

    async def list_history(self, document_id: str, analysis_id: str | None = None) -> list:
        """Return the durable command stream for one base analysis."""
        document = await self._require_document(document_id)
        base = await self._load_base_analysis(document, analysis_id)
        stream = await self._edits.find_stream(base.id)
        return await self._edits.list_commands(base.id) if stream else []

    async def list_history_entries(
        self, document_id: str, analysis_id: str | None = None
    ) -> list[EditHistoryEntry]:
        """The command stream with each entry's state, as the history shows it."""
        records = await self.list_history(document_id, analysis_id)
        _, states = resolve_active_edit_commands(records)
        return [EditHistoryEntry(record, states.get(record.sequence)) for record in records]

    async def preview(
        self,
        document_id: str,
        pending_commands: list[EditCommand],
        analysis_id: str | None = None,
    ) -> EditorSnapshot:
        document = await self._require_document(document_id)
        base = await self._load_base_analysis(document, analysis_id)
        stream = await self._edits.find_stream(base.id)
        stored = await self._edits.list_commands(base.id) if stream else []
        commands, _ = resolve_active_edit_commands(stored, pending_commands)
        projection = await self._project(base, commands, operation="preview")
        sequence = get_last_sequence(stored) + len(pending_commands)
        return await self._build_snapshot(document, base, projection, sequence)

    async def save(
        self,
        document_id: str,
        pending_commands: list[EditCommand],
        expected_sequence: int,
        analysis_id: str | None = None,
    ) -> EditorSnapshot:
        if not pending_commands:
            return await self.load_editor(document_id, analysis_id)
        document = await self._require_document(document_id)
        base = await self._load_base_analysis(document, analysis_id)
        if not base.document_json:
            raise AnalysisEditUnavailableError("This analysis has no canonical Docling document")
        stream = await self._ensure_stream(base)

        stored = await self._edits.list_commands(base.id)
        actual_sequence = get_last_sequence(stored)
        check_expected_sequence(expected_sequence, actual_sequence)
        all_commands, _ = resolve_active_edit_commands(stored, pending_commands)
        projection = await self._project(base, all_commands, operation="save")
        sequence = actual_sequence + len(pending_commands)
        cache = _build_cache(
            base.id, projection, sequence, hash_command_stream(stored, pending_commands)
        )
        # The graph mirrors the current analysis only.
        activate = await self._current.find_current_analysis_id(document_id) == base.id
        await self._edits.save_commands_and_cache(
            stream=stream,
            commands=pending_commands,
            expected_sequence=actual_sequence,
            cache=cache,
        )
        if activate:
            await self._refresh_graph(document_id, document.filename, projection.document_json)
        return await self._build_snapshot(document, base, projection, sequence)

    async def set_command_active(
        self,
        document_id: str,
        activation: CommandActivation,
        expected_sequence: int,
        analysis_id: str | None = None,
    ) -> EditorSnapshot:
        target_sequence = activation.target_sequence
        stored = await self.list_history(document_id, analysis_id)
        check_expected_sequence(expected_sequence, get_last_sequence(stored))
        _, states = resolve_active_edit_commands(stored)
        if target_sequence not in states:
            raise AnalysisEditError(f"Saved edit #{target_sequence} does not exist")
        if states[target_sequence] == activation.active:
            raise AnalysisEditError(f"Saved edit #{target_sequence} is already in that state")
        action = "reapply" if activation.active else "revert"
        try:
            return await self.save(
                document_id, [activation.to_command()], expected_sequence, analysis_id
            )
        except AnalysisEditConflictError:
            raise
        except AnalysisEditError as exc:
            raise AnalysisEditError(
                f"Cannot {action} edit #{target_sequence}; a remaining edit cannot be replayed: {exc}"
            ) from exc

    async def _ensure_stream(self, base) -> EditStream:
        """The base analysis's edit stream, created on its first save.

        Refuses a stream whose recorded base no longer hashes like the base.
        """
        base_hash = hash_result(base.document_json)
        stream = await self._edits.find_stream(base.id)
        if stream is None:
            stream = EditStream(
                analysis_id=base.id,
                base_document_hash=base_hash,
                engine_version=ENGINE_VERSION,
                created_at=datetime.now(UTC),
            )
            await self._edits.create_stream(stream)
            # Another writer may have created this stream first.
            stream = await self._edits.find_stream(base.id)
            if stream is None:
                raise AnalysisEditConflictError("The editor stream could not be created")
        if stream.base_document_hash != base_hash:
            raise AnalysisEditConflictError("The immutable base analysis changed")
        return stream

    async def _refresh_graph(self, document_id: str, filename: str, document_json: str) -> None:
        """Mirror the saved projection into the graph store, when one is wired."""
        if self._graph_writer is None:
            return
        try:
            await self._graph_writer.write_document_tree(
                doc_id=document_id,
                filename=filename,
                document_json=document_json,
            )
        except Exception:
            # SQLite is authoritative; graph storage is a rebuildable
            # projection and must not make a saved user edit disappear.
            logger.exception("Graph refresh failed after analysis edit for %s", document_id)

    async def _require_document(self, document_id: str):
        document = await self._documents.find_by_id(document_id)
        if document is None:
            raise AnalysisEditNotFoundError(f"Document not found: {document_id}")
        return document

    async def _load_base_analysis(self, document, analysis_id: str | None = None):
        if analysis_id is not None:
            base = await self._analyses.find_by_id(analysis_id)
            if base is None or base.document_id != document.id:
                raise AnalysisEditNotFoundError(f"Analysis not found: {analysis_id}")
        else:
            analysis_id = await self._current.find_current_analysis_id(document.id)
            if analysis_id is None:
                raise AnalysisEditNotFoundError("This document has no active analysis")
            base = await self._analyses.find_by_id(analysis_id)
        if base is None:
            raise AnalysisEditNotFoundError(f"Analysis not found: {analysis_id}")
        if not base.has_docling_document():
            raise AnalysisEditUnavailableError(
                "This analysis has no canonical Docling document. Re-run the analysis to enable "
                "the editor and document tree."
            )
        return base

    async def _project_cache(self, base, cache: EditedAnalysisCache) -> ProjectedAnalysis | None:
        """Project the stored working copy, or None when it cannot be read (#395).

        The cache is a rebuildable projection of the command stream: a corrupt
        one must not fail the request, the caller replays the stream instead.
        """
        try:
            return await asyncio.to_thread(
                self._engine.project_serialized,
                cache.document_json,
                base_analysis_id=base.id,
                editor_model_json=cache.editor_model_json,
            )
        except Exception:
            logger.warning(
                "Ignoring corrupt edited cache; replaying the edit stream",
                extra={
                    "editor_operation": "load",
                    "document_id": base.document_id,
                    "base_analysis_id": base.id,
                },
                exc_info=True,
            )
            return None

    async def _replay(self, base, stored) -> ProjectedAnalysis:
        commands, _ = resolve_active_edit_commands(stored)
        return await self._project(base, commands, operation="replay")

    async def _project(
        self, base, commands: list[EditCommand], *, operation: str
    ) -> ProjectedAnalysis:
        """Replay and project in a worker thread: the engine is CPU-bound (#394)."""
        try:
            return await asyncio.to_thread(
                self._engine.project,
                base.document_json,
                base_analysis_id=base.id,
                commands=commands,
            )
        except Exception:
            logger.exception(
                "Analysis editor projection failed",
                extra={
                    "editor_operation": operation,
                    "document_id": base.document_id,
                    "base_analysis_id": base.id,
                    "command_count": len(commands),
                    "command_types": [command.command_type for command in commands],
                },
            )
            raise

    async def _build_snapshot(self, document, base, projection, sequence: int) -> EditorSnapshot:
        job = AnalysisJob(
            # One working result per base analysis: the id must not collide
            # between two analyses of the same document (#395).
            id=f"working:{document.id}:{base.id}",
            document_id=document.id,
            status=AnalysisStatus.COMPLETED,
            content_markdown=projection.content_markdown,
            content_html=projection.content_html,
            pages_json=projection.pages_json,
            document_json=projection.document_json,
            document_filename=document.filename,
            completed_at=datetime.now(UTC),
            created_at=base.created_at,
        )
        stale = await self._has_stale_chunks(document.id, base.id, projection.document_json)
        return EditorSnapshot(job, projection, sequence, stale, base.id)

    async def _has_stale_chunks(self, document_id: str, base_id: str, document_json: str) -> bool:
        """Whether the live chunks may not match this analysis result (the rule
        is `DocumentAnalysisState.are_chunks_stale`)."""
        state = await self._states.find_state(document_id)
        if state is not None and state.chunk_source is not None:
            # Hashing the whole result only pays when there is a hash to compare.
            return state.are_chunks_stale(base_id, hash_result(document_json), has_chunks=True)
        # No recorded source: only whether there are chunks at all matters.
        return self._chunks is not None and await self._chunks.count_for_document(document_id) > 0


def _build_cache(
    analysis_id: str, projection: ProjectedAnalysis, sequence: int, stream_hash: str
) -> EditedAnalysisCache:
    """The working copy of `projection`, applied through `sequence` of the stream."""
    return EditedAnalysisCache(
        analysis_id=analysis_id,
        applied_through_sequence=sequence,
        document_json=projection.document_json,
        content_markdown=projection.content_markdown,
        content_html=projection.content_html,
        pages_json=projection.pages_json,
        editor_model_json=projection.editor_model_json,
        command_stream_hash=stream_hash,
        result_hash=hash_result(projection.document_json),
        updated_at=datetime.now(UTC),
    )
