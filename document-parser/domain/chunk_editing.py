"""Pure-domain operations on a chunkset.

These functions take a chunkset as input and return a new chunkset
(plus, where appropriate, the chunks that were created). They do not
touch the database, do not record audit rows, and do not raise
infrastructure errors. The `ChunkEditingService` (in `services/`)
wraps each call with audit-record generation and atomic persistence.

All operations preserve `sequence` ordering: insertions and splits
shift subsequent sequences upward; deletions / merges leave gaps.
Sequences are 0-based and only required to be strictly increasing
within a document; gaps are explicitly allowed so we never rewrite
many rows for a single edit.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.models import Chunk


class ChunkEditingError(Exception):
    """Raised by chunk-editing operations on invalid input (missing id,
    out-of-range offset, etc.). Subclasses `Exception` rather than
    `DomainError` so the API layer can map all of them to 4xx without
    a wider catch."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid.uuid4().hex


def _index_of(chunks: list[Chunk], chunk_id: str) -> int:
    for idx, c in enumerate(chunks):
        if c.id == chunk_id:
            return idx
    raise ChunkEditingError(f"chunk not found: {chunk_id}")


def insert(
    chunks: list[Chunk],
    *,
    at_position: int,
    text: str,
    document_id: str,
    headings: list[str] | None = None,
    source_page: int | None = None,
) -> tuple[list[Chunk], Chunk]:
    """Insert a fresh chunk at position `at_position`.

    Returns the updated chunkset and the new chunk. Subsequent chunks'
    sequences are shifted by +1.
    """
    if at_position < 0 or at_position > len(chunks):
        raise ChunkEditingError(f"insert position out of range: {at_position}")
    now = _utcnow()
    new_chunk = Chunk(
        id=_new_id(),
        document_id=document_id,
        sequence=at_position,
        text=text,
        headings=list(headings or []),
        source_page=source_page,
        created_at=now,
        updated_at=now,
    )
    out = list(chunks)
    for c in out[at_position:]:
        c.sequence += 1
    out.insert(at_position, new_chunk)
    return out, new_chunk


def update(
    chunks: list[Chunk],
    chunk_id: str,
    *,
    text: str | None = None,
    headings: list[str] | None = None,
) -> tuple[list[Chunk], Chunk]:
    """Update text and/or headings of a chunk in-place.

    Returns the updated chunkset and the modified chunk. The chunk's
    id and sequence are preserved.
    """
    idx = _index_of(chunks, chunk_id)
    target = chunks[idx]
    if target.deleted_at is not None:
        raise ChunkEditingError(f"chunk is deleted: {chunk_id}")
    if text is not None:
        target.text = text
    if headings is not None:
        target.headings = list(headings)
    target.updated_at = _utcnow()
    return list(chunks), target


def delete(chunks: list[Chunk], chunk_id: str) -> tuple[list[Chunk], Chunk]:
    """Soft-delete a chunk. Returns the updated chunkset and the
    deleted chunk (still present in the list, with `deleted_at` set)."""
    idx = _index_of(chunks, chunk_id)
    target = chunks[idx]
    if target.deleted_at is not None:
        return list(chunks), target  # idempotent
    target.deleted_at = _utcnow()
    target.updated_at = target.deleted_at
    return list(chunks), target


def merge(
    chunks: list[Chunk],
    chunk_ids: list[str],
    *,
    separator: str = "\n",
) -> tuple[list[Chunk], Chunk]:
    """Merge `chunk_ids` (in order) into a single new chunk.

    The new chunk takes the headings of the first source and the
    smallest source page. The `id`s of the sources are returned in
    the new chunk's lineage via the audit row written by the service
    layer.

    Returns the updated chunkset and the new merged chunk. The sources
    are removed from the chunkset (hard-removed from the list — the
    service is responsible for soft-deleting their persisted rows so
    history queries still resolve them).
    """
    if len(chunk_ids) < 2:
        raise ChunkEditingError("merge requires at least two chunks")
    indices = [_index_of(chunks, cid) for cid in chunk_ids]
    sources = [chunks[i] for i in indices]
    if any(c.deleted_at for c in sources):
        raise ChunkEditingError("cannot merge a deleted chunk")

    document_id = sources[0].document_id
    if any(c.document_id != document_id for c in sources):
        raise ChunkEditingError("merge across documents is not allowed")

    merged_text = separator.join(c.text for c in sources)
    merged_headings = list(sources[0].headings)
    merged_page = min((c.source_page for c in sources if c.source_page is not None), default=None)
    merged_sequence = min(c.sequence for c in sources)

    now = _utcnow()
    new_chunk = Chunk(
        id=_new_id(),
        document_id=document_id,
        sequence=merged_sequence,
        text=merged_text,
        headings=merged_headings,
        source_page=merged_page,
        created_at=now,
        updated_at=now,
    )

    source_ids = {c.id for c in sources}
    out = [c for c in chunks if c.id not in source_ids]
    out.append(new_chunk)
    out.sort(key=lambda c: c.sequence)
    return out, new_chunk


def split(
    chunks: list[Chunk], chunk_id: str, *, at_offset: int
) -> tuple[list[Chunk], Chunk, Chunk]:
    """Split a chunk's text at `at_offset` into two new chunks.

    The source chunk is removed from the chunkset (the service-layer
    persistence path soft-deletes its row so history queries can
    resolve it). The two new chunks inherit headings and source_page
    from the source.

    Returns the updated chunkset and the two new chunks `(left, right)`.
    """
    idx = _index_of(chunks, chunk_id)
    target = chunks[idx]
    if target.deleted_at is not None:
        raise ChunkEditingError(f"chunk is deleted: {chunk_id}")
    if at_offset <= 0 or at_offset >= len(target.text):
        raise ChunkEditingError(f"split offset out of range for chunk of length {len(target.text)}")

    now = _utcnow()
    left = Chunk(
        id=_new_id(),
        document_id=target.document_id,
        sequence=target.sequence,
        text=target.text[:at_offset],
        headings=list(target.headings),
        source_page=target.source_page,
        created_at=now,
        updated_at=now,
    )
    right = Chunk(
        id=_new_id(),
        document_id=target.document_id,
        sequence=target.sequence + 1,
        text=target.text[at_offset:],
        headings=list(target.headings),
        source_page=target.source_page,
        created_at=now,
        updated_at=now,
    )

    out = [c for c in chunks if c.id != target.id]
    for c in out:
        if c.sequence > target.sequence:
            c.sequence += 1
    out.extend((left, right))
    out.sort(key=lambda c: c.sequence)
    return out, left, right
