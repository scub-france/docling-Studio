"""Pure domain contracts for analysis editing.

The edit stream is the durable user intent.  Rendered analysis data is only a
materialized projection and may be rebuilt at any time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from domain.models import AnalysisJob

CommandType = Literal[
    "replaceText",
    "mergeText",
    "setHeadingLevel",
    "moveElement",
    "deleteElement",
    "deleteElements",
    "setCommandActive",
]


@dataclass(frozen=True)
class EditCommand:
    """One replayable user operation, addressed by stable logical IDs."""

    command_type: CommandType
    payload: dict[str, Any]
    command_version: int = 1


@dataclass(frozen=True)
class StoredEditCommand:
    id: str
    analysis_id: str
    sequence: int
    command: EditCommand
    command_hash: str
    created_at: datetime


@dataclass(frozen=True)
class EditHistoryEntry:
    """A stored command with its state: True or False for an edit that is
    applied or reverted, None for a `setCommandActive` event itself."""

    record: StoredEditCommand
    active: bool | None


@dataclass(frozen=True)
class EditStream:
    analysis_id: str
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

    def read_editor_model(self) -> dict[str, Any]:
        """The editor model, decoded from the JSON the projection stores."""
        return json.loads(self.editor_model_json)


@dataclass(frozen=True)
class EditedAnalysisCache:
    analysis_id: str
    applied_through_sequence: int
    document_json: str
    content_markdown: str
    content_html: str
    pages_json: str
    editor_model_json: str
    command_stream_hash: str
    result_hash: str
    updated_at: datetime


@dataclass(frozen=True)
class EditorSnapshot:
    job: AnalysisJob
    projection: ProjectedAnalysis
    applied_through_sequence: int
    chunks_stale: bool
    base_analysis_id: str


def hash_result(document_json: str) -> str:
    """Fingerprint of an analysis result.

    Chunks record it as their source, and the editor compares it to decide
    whether they are stale: both sides must compute it the same way.
    """
    return hashlib.sha256(document_json.encode("utf-8")).hexdigest()


def serialize_command_payload(payload: dict[str, Any]) -> str:
    """The canonical JSON of a command payload: what is stored and hashed.

    Stored command rows and cached stream hashes depend on these exact bytes:
    sorted keys, no spaces, ASCII escapes (`json.dumps` default).
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def hash_command(previous_hash: str, sequence: int, command: EditCommand) -> str:
    """One link of the command chain, stored with each command row.

    `previous_hash` is the hash of the command before it, "" for the first.
    """
    payload = serialize_command_payload(command.payload)
    kind, version = command.command_type, command.command_version
    raw = f"{previous_hash}|{sequence}|{kind}|{version}|{payload}".encode()
    return hashlib.sha256(raw).hexdigest()


def get_last_sequence(stored: list[StoredEditCommand]) -> int:
    """The sequence of the last stored command, 0 for an empty stream."""
    return stored[-1].sequence if stored else 0


def hash_command_stream(stored: list[StoredEditCommand], pending: list[EditCommand]) -> str:
    """Fingerprint of a whole stream, stored commands then pending ones.

    The edited-analysis cache records it: a cache whose hash no longer matches
    the stored stream is stale. It digests the chain hashes in order, the
    stored ones as persisted and the pending ones as `hash_command` will
    persist them.
    """
    digest = hashlib.sha256()
    previous = stored[-1].command_hash if stored else ""
    for record in stored:
        digest.update(record.command_hash.encode())
    last_sequence = get_last_sequence(stored)
    for offset, command in enumerate(pending, start=1):
        previous = hash_command(previous, last_sequence + offset, command)
        digest.update(previous.encode())
    return digest.hexdigest()


class AnalysisEditError(ValueError):
    """Base error for invalid edit requests."""


class AnalysisEditConflictError(AnalysisEditError):
    """Raised when a caller saved against an old command sequence."""


class AnalysisEditUnavailableError(AnalysisEditError):
    """Raised when a document has no editable canonical Docling JSON."""


class AnalysisEditNotFoundError(AnalysisEditUnavailableError):
    """Raised when the document or the requested analysis does not exist (#395).

    It stays an `AnalysisEditUnavailableError` so callers that only need "no
    editable result" keep working; the editor API answers 404 for it.
    """


# The service answers before any work and the repository checks again inside
# its transaction; the two have always worded the conflict differently.
EDITOR_SEQUENCE_CONFLICT = "The editor stream changed: expected {expected}, actual {actual}"
STORED_SEQUENCE_CONFLICT = (
    "Edit stream changed: expected sequence {expected}, actual sequence {actual}"
)


def check_expected_sequence(
    expected: int, actual: int, message: str = EDITOR_SEQUENCE_CONFLICT
) -> None:
    """Optimistic concurrency: an edit applies only to the sequence it was made on."""
    if actual != expected:
        raise AnalysisEditConflictError(message.format(expected=expected, actual=actual))


# Edit rules that hold on plain values. The Docling adapter calls them; the
# rules that need the live document (item classes, the root, cycles) stay
# there. `frontend/src/features/analysis-editor/commands.ts` mirrors some.

# Labels whose items can be merged, and only with items of the same label.
MERGEABLE_TEXT_LABELS = frozenset({"text", "paragraph"})
MOVE_PLACEMENTS = frozenset({"before", "after", "inside"})


def check_command_version(version: int) -> None:
    """Only version 1 of each command exists."""
    if version != 1:
        raise AnalysisEditError(f"Unsupported command version: {version}")


def check_heading_level(level: int, *, title_exists: bool) -> None:
    """A heading level is -1 (demote to text), 0 (title) or 1 to 6.

    `title_exists` is whether the document already has a title; it only
    matters for level 0, since a document has at most one title.
    """
    if level < -1 or level > 6:
        raise AnalysisEditError("Heading level must be -1, 0, or between 1 and 6")
    if level == 0 and title_exists:
        raise AnalysisEditError("A document can contain only one title")


def check_merge_request(element_ids: Any, separator: Any) -> None:
    """A merge names at least two elements, as a list, and a string separator."""
    if not isinstance(element_ids, list) or len(element_ids) < 2 or not isinstance(separator, str):
        raise AnalysisEditError("mergeText requires at least two element IDs and a separator")


def check_mergeable_labels(labels: set[str]) -> None:
    """Merged items share one label, and it is a paragraph-like text label."""
    if len(labels) != 1 or next(iter(labels)).lower() not in MERGEABLE_TEXT_LABELS:
        raise AnalysisEditError("Only compatible paragraph text items can be merged")


def check_delete_request(element_ids: Any) -> None:
    """A multi-delete names at least one element, as a list."""
    if not isinstance(element_ids, list) or not element_ids:
        raise AnalysisEditError("deleteElements requires at least one element")


def check_move_target(target_id: Any, placement: Any) -> None:
    """A targeted move names a target element and a known placement."""
    if not isinstance(target_id, str) or placement not in MOVE_PLACEMENTS:
        raise AnalysisEditError("moveElement requires a target and placement")


def resolve_active_edit_commands(
    stored: list[StoredEditCommand], pending: list[EditCommand] | None = None
) -> tuple[list[EditCommand], dict[int, bool]]:
    """Resolve append-only history events into the edits to replay."""
    operations: list[tuple[int, EditCommand]] = []
    active: dict[int, bool] = {}
    next_sequence = get_last_sequence(stored)
    entries = [(record.sequence, record.command) for record in stored]
    entries.extend(
        (next_sequence + offset, command) for offset, command in enumerate(pending or [], start=1)
    )
    for sequence, command in entries:
        if command.command_type == "setCommandActive":
            target = command.payload.get("targetSequence")
            enabled = command.payload.get("active")
            if (
                command.command_version != 1
                or type(target) is not int
                or target not in active
                or type(enabled) is not bool
            ):
                raise AnalysisEditError(f"Invalid saved edit state at sequence {sequence}")
            active[target] = enabled
        else:
            operations.append((sequence, command))
            active[sequence] = True
    return [command for sequence, command in operations if active[sequence]], active
