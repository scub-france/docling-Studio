"""Application service for the durable analysis editor."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.analysis_editing import (
    AnalysisEditConflictError,
    AnalysisEditError,
    AnalysisEditUnavailableError,
    EditCommand,
    EditedAnalysisCache,
    EditStream,
    ProjectedAnalysis,
    active_edit_commands,
)
from domain.models import AnalysisJob, AnalysisStatus

if TYPE_CHECKING:
    from domain.ports import (
        AnalysisEditRepository,
        AnalysisRepository,
        AnalysisSelectionRepository,
        ChunkSourceRepository,
        DocumentRepository,
    )


ENGINE_VERSION = "analysis-editor-1"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EditorSnapshot:
    job: AnalysisJob
    projection: ProjectedAnalysis
    applied_through_sequence: int
    chunks_stale: bool
    base_analysis_id: str


class AnalysisEditService:
    """Coordinates replay, projection, and transactional materialization."""

    def __init__(
        self,
        *,
        analysis_repo: AnalysisRepository,
        document_repo: DocumentRepository,
        selection_repo: AnalysisSelectionRepository,
        chunk_source_repo: ChunkSourceRepository,
        edit_repo: AnalysisEditRepository,
        editor,
        projector,
        graph_writer=None,
    ) -> None:
        self._analyses = analysis_repo
        self._documents = document_repo
        self._selection = selection_repo
        self._chunk_sources = chunk_source_repo
        self._edits = edit_repo
        self._editor = editor
        self._projector = projector
        self._graph_writer = graph_writer
        self._unedited_projection: tuple[str, str, ProjectedAnalysis] | None = None

    async def load_editor(self, document_id: str, analysis_id: str | None = None) -> EditorSnapshot:
        document = await self._require_document(document_id)
        base = await self._base_analysis(document, analysis_id)
        stream = await self._edits.find_stream(base.id)
        stored = await self._edits.list_commands(base.id) if stream else []
        sequence = stored[-1].sequence if stored else 0
        if not stored:
            base_hash = _sha256(base.document_json)
            cached = self._unedited_projection
            if cached is not None and cached[0] == base.id and cached[1] == base_hash:
                return await self._snapshot(document, base, cached[2], sequence)
        cache = await self._edits.find_cache(base.id) if stream else None
        if (
            stream is not None
            and cache is not None
            and cache.analysis_id == base.id
            and cache.applied_through_sequence == sequence
            and cache.command_stream_hash == _stream_hash(stored, [])
        ):
            projection = self._projector.project_serialized(
                cache.document_json,
                base_analysis_id=base.id,
                editor_model_json=cache.editor_model_json,
            )
        else:
            projection = self._replay(base, stored)
        if not stored:
            self._unedited_projection = (base.id, base_hash, projection)
        return await self._snapshot(document, base, projection, sequence)

    async def active_result(self, document_id: str) -> EditorSnapshot:
        """Resolve the result used by document-scoped downstream features."""
        await self._require_document(document_id)
        selection = await self._selection.get_selection(document_id)
        if selection is None:
            raise AnalysisEditUnavailableError("This document has no active analysis")
        return await self.load_editor(document_id, selection.analysis_id)

    async def history(self, document_id: str, analysis_id: str | None = None) -> list:
        """Return the durable command stream for one base analysis."""
        document = await self._require_document(document_id)
        base = await self._base_analysis(document, analysis_id)
        stream = await self._edits.find_stream(base.id)
        return await self._edits.list_commands(base.id) if stream else []

    async def preview(
        self,
        document_id: str,
        pending_commands: list[EditCommand],
        analysis_id: str | None = None,
    ) -> EditorSnapshot:
        document = await self._require_document(document_id)
        base = await self._base_analysis(document, analysis_id)
        stream = await self._edits.find_stream(base.id)
        stored = await self._edits.list_commands(base.id) if stream else []
        commands, _ = active_edit_commands(stored, pending_commands)
        projection = self._project(base, commands, operation="preview")
        sequence = (stored[-1].sequence if stored else 0) + len(pending_commands)
        return await self._snapshot(document, base, projection, sequence)

    async def save(
        self,
        document_id: str,
        pending_commands: list[EditCommand],
        expected_sequence: int,
        analysis_id: str | None = None,
    ) -> EditorSnapshot:
        if not pending_commands:
            return await self.load_editor(document_id)
        document = await self._require_document(document_id)
        base = await self._base_analysis(document, analysis_id)
        if not base.document_json:
            raise AnalysisEditUnavailableError("This analysis has no canonical Docling document")
        base_hash = _sha256(base.document_json)
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

        stored = await self._edits.list_commands(base.id)
        actual_sequence = stored[-1].sequence if stored else 0
        if actual_sequence != expected_sequence:
            raise AnalysisEditConflictError(
                f"The editor stream changed: expected {expected_sequence}, actual {actual_sequence}"
            )
        all_commands, _ = active_edit_commands(stored, pending_commands)
        projection = self._project(base, all_commands, operation="save")
        sequence = actual_sequence + len(pending_commands)
        stream_hash = _stream_hash(stored, pending_commands)
        result_hash = _sha256(projection.document_json)
        cache = EditedAnalysisCache(
            analysis_id=base.id,
            applied_through_sequence=sequence,
            document_json=projection.document_json,
            content_markdown=projection.content_markdown,
            content_html=projection.content_html,
            pages_json=projection.pages_json,
            editor_model_json=projection.editor_model_json,
            command_stream_hash=stream_hash,
            result_hash=result_hash,
            updated_at=datetime.now(UTC),
        )
        selection = await self._selection.get_selection(document_id)
        activate = selection is not None and selection.analysis_id == base.id
        await self._edits.save_commands_and_cache(
            stream=stream,
            commands=pending_commands,
            expected_sequence=actual_sequence,
            cache=cache,
        )
        if activate and self._graph_writer is not None:
            try:
                await self._graph_writer.write_document_tree(
                    doc_id=document_id,
                    filename=document.filename,
                    document_json=projection.document_json,
                )
            except Exception:
                # SQLite is authoritative; graph storage is a rebuildable
                # projection and must not make a saved user edit disappear.
                logger.exception("Graph refresh failed after analysis edit for %s", document_id)
        return await self._snapshot(document, base, projection, sequence)

    async def set_command_active(
        self,
        document_id: str,
        target_sequence: int,
        active: bool,
        expected_sequence: int,
        analysis_id: str | None = None,
    ) -> EditorSnapshot:
        stored = await self.history(document_id, analysis_id)
        actual_sequence = stored[-1].sequence if stored else 0
        if actual_sequence != expected_sequence:
            raise AnalysisEditConflictError(
                f"The editor stream changed: expected {expected_sequence}, actual {actual_sequence}"
            )
        _, states = active_edit_commands(stored)
        if target_sequence not in states:
            raise AnalysisEditError(f"Saved edit #{target_sequence} does not exist")
        if states[target_sequence] == active:
            raise AnalysisEditError(f"Saved edit #{target_sequence} is already in that state")
        action = "reapply" if active else "revert"
        try:
            return await self.save(
                document_id,
                [
                    EditCommand(
                        "setCommandActive",
                        {"targetSequence": target_sequence, "active": active},
                    )
                ],
                expected_sequence,
                analysis_id,
            )
        except AnalysisEditConflictError:
            raise
        except AnalysisEditError as exc:
            raise AnalysisEditError(
                f"Cannot {action} edit #{target_sequence}; a remaining edit cannot be replayed: {exc}"
            ) from exc

    async def rebuild(self, document_id: str, analysis_id: str | None = None) -> EditorSnapshot:
        document = await self._require_document(document_id)
        base = await self._base_analysis(document, analysis_id)
        stream = await self._edits.find_stream(base.id)
        stored = await self._edits.list_commands(base.id) if stream else []
        projection = self._replay(base, stored)
        sequence = stored[-1].sequence if stored else 0
        if stream is not None:
            cache = EditedAnalysisCache(
                analysis_id=base.id,
                applied_through_sequence=sequence,
                document_json=projection.document_json,
                content_markdown=projection.content_markdown,
                content_html=projection.content_html,
                pages_json=projection.pages_json,
                editor_model_json=projection.editor_model_json,
                command_stream_hash=_stream_hash(stored, []),
                result_hash=_sha256(projection.document_json),
                updated_at=datetime.now(UTC),
            )
            await self._edits.replace_cache(cache)
        return await self._snapshot(document, base, projection, sequence)

    async def _require_document(self, document_id: str):
        document = await self._documents.find_by_id(document_id)
        if document is None:
            raise AnalysisEditUnavailableError(f"Document not found: {document_id}")
        return document

    async def _base_analysis(self, document, analysis_id: str | None = None):
        if analysis_id is not None:
            base = await self._analyses.find_by_id(analysis_id)
            if base is not None and base.document_id != document.id:
                base = None
        else:
            selection = await self._selection.get_selection(document.id)
            if selection is None:
                raise AnalysisEditUnavailableError("This document has no active analysis")
            base = await self._analyses.find_by_id(selection.analysis_id)
        if base is None or base.status != AnalysisStatus.COMPLETED or not base.document_json:
            raise AnalysisEditUnavailableError(
                "This analysis has no canonical Docling document. Re-run the analysis to enable "
                "the editor and document tree."
            )
        return base

    def _replay(self, base, stored) -> ProjectedAnalysis:
        commands, _ = active_edit_commands(stored)
        return self._project(base, commands, operation="replay")

    def _project(self, base, commands: list[EditCommand], *, operation: str) -> ProjectedAnalysis:
        try:
            mutation = self._editor.apply(
                base.document_json,
                base_analysis_id=base.id,
                commands=commands,
            )
            return self._projector.project(
                mutation.document,
                base_analysis_id=base.id,
                logical_ids=mutation.logical_ids,
                reference_changes=mutation.reference_changes,
                warnings=mutation.warnings,
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

    async def _snapshot(self, document, base, projection, sequence: int) -> EditorSnapshot:
        job = AnalysisJob(
            id=f"working:{document.id}",
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
        source = await self._chunk_sources.get_chunk_source(document.id)
        stale = source is not None and (
            source.analysis_id != base.id or source.result_hash != _sha256(projection.document_json)
        )
        return EditorSnapshot(job, projection, sequence, stale, base.id)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stream_hash(stored, pending: list[EditCommand]) -> str:
    digest = hashlib.sha256()
    previous = stored[-1].command_hash if stored else ""
    for record in stored:
        digest.update(record.command_hash.encode())
    for offset, command in enumerate(pending, start=1):
        payload = json.dumps(command.payload, sort_keys=True, separators=(",", ":"))
        previous = _command_hash(
            previous, (stored[-1].sequence if stored else 0) + offset, command, payload
        )
        digest.update(previous.encode())
    return digest.hexdigest()


def _command_hash(previous: str, sequence: int, command: EditCommand, payload: str) -> str:
    raw = (
        f"{previous}|{sequence}|{command.command_type}|{command.command_version}|{payload}".encode()
    )
    return hashlib.sha256(raw).hexdigest()
