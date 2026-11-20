"""Docling implementation of the analysis editor engine port (#394)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from infra.docling_editor import DoclingDocumentEditor
from infra.docling_projector import DoclingAnalysisProjector

if TYPE_CHECKING:
    from domain.analysis_editing import EditCommand, ProjectedAnalysis


class DoclingAnalysisEngine:
    """Compose the Docling editor and projector behind `AnalysisDocumentEngine`.

    The edited `DoclingDocument` goes straight from the editor to the
    projector here, so no Docling type crosses into the service layer.
    """

    def __init__(
        self,
        editor: DoclingDocumentEditor | None = None,
        projector: DoclingAnalysisProjector | None = None,
    ) -> None:
        self._editor = editor or DoclingDocumentEditor()
        self._projector = projector or DoclingAnalysisProjector()

    def project(
        self,
        document_json: str,
        *,
        base_analysis_id: str,
        commands: list[EditCommand],
    ) -> ProjectedAnalysis:
        mutation = self._editor.apply(
            document_json,
            base_analysis_id=base_analysis_id,
            commands=commands,
        )
        return self._projector.project(
            mutation.document,
            base_analysis_id=base_analysis_id,
            logical_ids=mutation.logical_ids,
        )

    def project_serialized(
        self,
        document_json: str,
        *,
        base_analysis_id: str,
        editor_model_json: str,
    ) -> ProjectedAnalysis:
        return self._projector.project_serialized(
            document_json,
            base_analysis_id=base_analysis_id,
            editor_model_json=editor_model_json,
        )
