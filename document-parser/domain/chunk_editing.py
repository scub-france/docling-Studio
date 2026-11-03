"""Chunk-editing rules: where a new chunk lands, how one splits, how several merge.

Pure: chunks in, chunks out. Nothing here reads or writes the database or
the `chunk_edits` journal. `services/chunk_service.py` loads the live
chunkset, asks these functions what an edit produces, then persists the
result with the journal rows `journal_entry` builds, in one write.

These are the rules the chunk editor ships. An earlier draft of this module
worked on whole chunksets and disagreed with the service on four points:
its merge kept the smallest source page and accepted non-contiguous chunks,
its split dropped the bboxes and doc items, and it minted hex ids. Nothing
in production called it; the service's rules replaced it when they moved
here (audit 0.7.4, 01 MAJ-1).

Sequences are 0-based and strictly increasing within a document. Gaps are
allowed, so an edit never renumbers more than it must.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from domain.chunk_serialization import chunk_to_audit_dict
from domain.models import Chunk, ChunkEdit

if TYPE_CHECKING:
    from datetime import datetime

    from domain.value_objects import ChunkEditAction

# What a merge puts between the texts of two consecutive sources.
MERGE_SEPARATOR = "\n"


class ChunkEditingError(Exception):
    """An edit the chunkset refuses. The subclass says why, so the service can
    answer each reason with its own status."""


class InvalidChunkEditError(ChunkEditingError):
    """The edit's arguments are out of range (offset, number of chunks)."""


class UnknownChunkError(ChunkEditingError):
    """The edit names a chunk that is not live in the document."""


class NonContiguousMergeError(ChunkEditingError):
    """The chunks to merge do not occupy consecutive sequences."""


def sequence_after(chunks: list[Chunk], after_id: str | None) -> int:
    """The sequence a new chunk takes: right after `after_id`, or at the end."""
    if after_id is None:
        return max((c.sequence for c in chunks), default=-1) + 1
    anchor = next((c for c in chunks if c.id == after_id), None)
    if anchor is None:
        raise UnknownChunkError(f"Anchor chunk not found: {after_id}")
    return anchor.sequence + 1


def split(source: Chunk, offset: int) -> tuple[Chunk, Chunk]:
    """Cut `source` at character `offset` into a head and a tail.

    The offset must leave at least one character on each side. Both halves
    are new chunks (new ids): the head takes the source's sequence, the tail
    the next one. Both inherit the headings, source page, bboxes and doc
    items; the token count is unknown after a cut, so it is left unset.
    """
    if offset <= 0 or offset >= len(source.text):
        raise InvalidChunkEditError(
            f"cursorOffset {offset} out of range for chunk of length {len(source.text)}"
        )
    return (
        _split_half(source, source.sequence, source.text[:offset]),
        _split_half(source, source.sequence + 1, source.text[offset:]),
    )


def _split_half(source: Chunk, sequence: int, text: str) -> Chunk:
    return Chunk(
        document_id=source.document_id,
        sequence=sequence,
        text=text,
        headings=list(source.headings),
        source_page=source.source_page,
        bboxes=list(source.bboxes),
        doc_items=list(source.doc_items),
    )


def merge(chunks: list[Chunk], ids: list[str]) -> tuple[list[Chunk], Chunk]:
    """Merge the live chunks `ids` names into one new chunk.

    `chunks` is the document's live chunkset. The order of `ids` does not
    matter: the sources are taken in sequence order, and must occupy
    consecutive sequences. The merged chunk takes the first source's
    sequence, headings and source page; it joins the texts with
    `MERGE_SEPARATOR`, concatenates the bboxes and doc items, and sums the
    known token counts (unknown when none is known, or all are zero).

    Returns the sources, in sequence order, and the merged chunk.
    """
    if len(ids) < 2:
        raise InvalidChunkEditError("merge requires at least 2 chunk ids")
    by_id = {c.id: c for c in chunks}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise UnknownChunkError(f"Chunks not found: {missing}")

    sources = sorted((by_id[i] for i in ids), key=lambda c: c.sequence)
    first = sources[0]
    if [c.sequence for c in sources] != list(range(first.sequence, first.sequence + len(sources))):
        raise NonContiguousMergeError("merge requires contiguous chunks (by sequence)")

    merged = Chunk(
        document_id=first.document_id,
        sequence=first.sequence,
        text=MERGE_SEPARATOR.join(c.text for c in sources),
        headings=list(first.headings),
        source_page=first.source_page,
        bboxes=[b for c in sources for b in c.bboxes],
        doc_items=[d for c in sources for d in c.doc_items],
        token_count=sum(c.token_count or 0 for c in sources) or None,
    )
    return sources, merged


def journal_entry(
    document_id: str,
    chunk_id: str,
    action: ChunkEditAction,
    *,
    actor: str,
    at: datetime,
    before: Chunk | None = None,
    after: Chunk | None = None,
    parents: list[str] | None = None,
    children: list[str] | None = None,
    edit_id: str | None = None,
) -> ChunkEdit:
    """One `chunk_edits` row: `actor` did `action` to `chunk_id` at `at`.

    `before` / `after` are the chunk as it was and as it is, recorded in the
    journal shape (`chunk_to_audit_dict`); a path that journals no snapshot
    leaves them out. `parents` / `children` carry a merge's sources and a
    split's halves. The row gets a fresh uuid4 id unless `edit_id` is given.
    """
    return ChunkEdit(
        id=edit_id or str(uuid.uuid4()),
        document_id=document_id,
        chunk_id=chunk_id,
        action=action,
        actor=actor,
        at=at,
        before=None if before is None else chunk_to_audit_dict(before),
        after=None if after is None else chunk_to_audit_dict(after),
        parents=list(parents or []),
        children=list(children or []),
    )
