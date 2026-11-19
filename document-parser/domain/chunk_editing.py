"""Pure-domain operations on a chunkset.

These functions take chunks as input and return new chunks. They do not
touch the database or raise infrastructure errors.

`split` and `merge` are the rules `ChunkService` applies: they build the
new chunks and the service persists them (shifting later sequences,
soft-deleting the sources).

Sequences are 0-based and only required to be strictly increasing
within a document; gaps are explicitly allowed so we never rewrite
many rows for a single edit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.models import Chunk

if TYPE_CHECKING:
    from domain.value_objects import ChunkBbox, ChunkDocItem


class ChunkEditingError(Exception):
    """Raised by chunk-editing operations on invalid input (missing id,
    out-of-range offset, etc.). Subclasses `Exception` rather than
    `DomainError` so the API layer can map all of them to 4xx without
    a wider catch."""


class ChunkMergeGapError(ChunkEditingError):
    """Raised when the chunks to merge are not contiguous by sequence.

    The request is well formed but conflicts with the current chunkset,
    so the service answers it apart from the other editing errors.
    """


def check_merge_count(chunk_ids: list[str]) -> None:
    """A merge needs at least two chunks; checked before any lookup."""
    if len(chunk_ids) < 2:
        raise ChunkEditingError("merge requires at least 2 chunk ids")


def merge(sources: list[Chunk], *, document_id: str) -> tuple[list[Chunk], Chunk]:
    """Merge live chunks of one document into a single new chunk.

    The sources are taken in sequence order, whatever order they were
    given in, and must have consecutive sequences. The new chunk sits at
    the first source's sequence, joins the texts with a newline, keeps the
    first source's headings and source page, concatenates bboxes and doc
    items, and sums the token counts (None when the sum is 0).

    Returns the sources in sequence order and the new chunk; its id and
    timestamps come from the `Chunk` defaults. The caller retires the
    sources.
    """
    check_merge_count([c.id for c in sources])
    ordered = sorted(sources, key=lambda c: c.sequence)
    sequences = [c.sequence for c in ordered]
    if sequences != list(range(sequences[0], sequences[0] + len(sequences))):
        raise ChunkMergeGapError("merge requires contiguous chunks (by sequence)")

    bboxes: list[ChunkBbox] = []
    doc_items: list[ChunkDocItem] = []
    for c in ordered:
        bboxes.extend(c.bboxes)
        doc_items.extend(c.doc_items)
    merged = Chunk(
        document_id=document_id,
        sequence=ordered[0].sequence,
        text="\n".join(c.text for c in ordered),
        headings=list(ordered[0].headings),
        source_page=ordered[0].source_page,
        bboxes=bboxes,
        doc_items=doc_items,
        token_count=sum((c.token_count or 0) for c in ordered) or None,
    )
    return ordered, merged


def split(source: Chunk, *, at_offset: int, document_id: str) -> tuple[Chunk, Chunk]:
    """Split a live chunk's text at `at_offset` into two new chunks.

    Both halves inherit headings, source page, bboxes and doc items; the
    token count is unknown after a split and stays None. The head takes the
    source's sequence and the tail the next one; their ids and timestamps
    come from the `Chunk` defaults. The caller shifts the later chunks and
    retires the source.
    """
    if at_offset <= 0 or at_offset >= len(source.text):
        raise ChunkEditingError(
            f"cursorOffset {at_offset} out of range for chunk of length {len(source.text)}"
        )
    head = Chunk(
        document_id=document_id,
        sequence=source.sequence,
        text=source.text[:at_offset],
        headings=list(source.headings),
        source_page=source.source_page,
        bboxes=list(source.bboxes),
        doc_items=list(source.doc_items),
    )
    tail = Chunk(
        document_id=document_id,
        sequence=source.sequence + 1,
        text=source.text[at_offset:],
        headings=list(source.headings),
        source_page=source.source_page,
        bboxes=list(source.bboxes),
        doc_items=list(source.doc_items),
    )
    return head, tail
