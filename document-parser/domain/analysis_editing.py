"""Pure domain contracts for analysis editing.

The edit stream is the durable user intent.  Rendered analysis data is only a
materialized projection and may be rebuilt at any time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

CommandType = Literal["replaceText", "mergeText", "setHeadingLevel", "moveElement", "deleteElement"]


@dataclass(frozen=True)
class EditCommand:
    """One replayable user operation, addressed by stable logical IDs."""

    command_type: CommandType
    payload: dict[str, Any]
    command_version: int = 1


@dataclass(frozen=True)
class StoredEditCommand:
    id: str
    stream_id: str
    sequence: int
    command: EditCommand
    command_hash: str
    created_at: datetime


@dataclass(frozen=True)
class EditStream:
    id: str
    document_id: str
    base_analysis_id: str
    base_document_hash: str
    engine_version: str
    created_at: datetime


@dataclass(frozen=True)
class EditorProvenance:
    page: int
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class EditorElement:
    id: str
    self_ref: str
    parent_id: str | None
    type: str
    text: str | None
    heading_level: int | None
    children: tuple[str, ...] = ()
    provenance: tuple[EditorProvenance, ...] = ()
    editable: bool = False
    supported_operations: tuple[CommandType, ...] = ()
    non_editable_reason: str | None = None


@dataclass(frozen=True)
class EditorTreeNode:
    element_id: str
    type: str
    label: str
    children: tuple[EditorTreeNode, ...] = ()


@dataclass(frozen=True)
class ProjectedAnalysis:
    document_json: str
    content_markdown: str
    content_html: str
    pages_json: str
    editor_model_json: str
    tree: tuple[EditorTreeNode, ...]
    elements: tuple[EditorElement, ...]
    reference_changes: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkingCopy:
    document_id: str
    stream_id: str
    base_analysis_id: str
    applied_through_sequence: int
    document_json: str
    content_markdown: str
    content_html: str
    pages_json: str
    editor_model_json: str
    command_stream_hash: str
    result_hash: str
    updated_at: datetime


class AnalysisEditError(ValueError):
    """Base error for invalid edit requests."""


class AnalysisEditConflictError(AnalysisEditError):
    """Raised when a caller saved against an old command sequence."""


class AnalysisEditUnavailableError(AnalysisEditError):
    """Raised when a document has no editable canonical Docling JSON."""
