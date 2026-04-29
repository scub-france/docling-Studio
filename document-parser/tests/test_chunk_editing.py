"""Tests for the pure-domain chunk-editing operations (#205)."""

from __future__ import annotations

import pytest

from domain.chunk_editing import (
    ChunkEditingError,
    delete,
    insert,
    merge,
    split,
    update,
)
from domain.models import Chunk


def _make(document_id: str = "doc-1", count: int = 3) -> list[Chunk]:
    out: list[Chunk] = []
    for i in range(count):
        out.append(
            Chunk(
                id=f"c-{i}",
                document_id=document_id,
                sequence=i,
                text=f"text {i}",
                headings=[f"H{i}"],
                source_page=i + 1,
            )
        )
    return out


# ---------------------------------------------------------------------------
# insert
# ---------------------------------------------------------------------------


def test_insert_at_end_appends_chunk_with_correct_sequence() -> None:
    chunks = _make(count=2)
    out, new = insert(chunks, at_position=2, text="new", document_id="doc-1")
    assert len(out) == 3
    assert out[2].id == new.id
    assert new.sequence == 2
    # Existing chunks untouched.
    assert out[0].sequence == 0
    assert out[1].sequence == 1


def test_insert_in_middle_shifts_subsequent_sequences() -> None:
    chunks = _make(count=3)
    out, new = insert(chunks, at_position=1, text="middle", document_id="doc-1")
    sequences = [c.sequence for c in out]
    assert sequences == [0, 1, 2, 3]
    assert out[1].id == new.id
    # Original chunk-1 was shifted to sequence 2.
    assert next(c for c in out if c.id == "c-1").sequence == 2


def test_insert_out_of_range_raises() -> None:
    chunks = _make(count=2)
    with pytest.raises(ChunkEditingError):
        insert(chunks, at_position=99, text="x", document_id="doc-1")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_update_changes_text_in_place() -> None:
    chunks = _make()
    out, modified = update(chunks, "c-1", text="edited")
    assert modified.id == "c-1"
    assert modified.text == "edited"
    # Identity preserved.
    assert next(c for c in out if c.id == "c-1").text == "edited"


def test_update_can_change_headings_only() -> None:
    chunks = _make()
    _, modified = update(chunks, "c-0", headings=["X"])
    assert modified.headings == ["X"]


def test_update_unknown_chunk_raises() -> None:
    chunks = _make()
    with pytest.raises(ChunkEditingError):
        update(chunks, "missing", text="x")


def test_update_deleted_chunk_raises() -> None:
    chunks = _make()
    delete(chunks, "c-1")
    with pytest.raises(ChunkEditingError):
        update(chunks, "c-1", text="x")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_marks_deleted_at() -> None:
    chunks = _make()
    out, deleted = delete(chunks, "c-1")
    target = next(c for c in out if c.id == "c-1")
    assert target.deleted_at is not None
    assert deleted is target


def test_delete_is_idempotent() -> None:
    chunks = _make()
    out_a, _ = delete(chunks, "c-1")
    out_b, _ = delete(out_a, "c-1")
    target_a = next(c for c in out_a if c.id == "c-1")
    target_b = next(c for c in out_b if c.id == "c-1")
    assert target_a.deleted_at == target_b.deleted_at


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


def test_merge_removes_sources_and_returns_new_chunk() -> None:
    chunks = _make(count=3)
    out, merged = merge(chunks, ["c-0", "c-1"])
    ids = {c.id for c in out}
    assert "c-0" not in ids
    assert "c-1" not in ids
    assert merged.id in ids
    assert merged.text == "text 0\ntext 1"
    # Merged chunk inherits headings from first source.
    assert merged.headings == ["H0"]
    # Source page is the min.
    assert merged.source_page == 1


def test_merge_requires_at_least_two_chunks() -> None:
    chunks = _make()
    with pytest.raises(ChunkEditingError):
        merge(chunks, ["c-0"])


def test_merge_across_documents_raises() -> None:
    chunks = _make(document_id="doc-1", count=2)
    other = Chunk(id="x-0", document_id="doc-2", sequence=10, text="other")
    chunks.append(other)
    with pytest.raises(ChunkEditingError):
        merge(chunks, ["c-0", "x-0"])


# ---------------------------------------------------------------------------
# split
# ---------------------------------------------------------------------------


def test_split_creates_two_new_chunks() -> None:
    chunks = _make(count=2)
    out, left, right = split(chunks, "c-0", at_offset=4)
    assert left.text == "text"
    assert right.text == " 0"
    ids = {c.id for c in out}
    # Source replaced by two new chunks.
    assert "c-0" not in ids
    assert left.id in ids
    assert right.id in ids


def test_split_preserves_headings_on_both_halves() -> None:
    chunks = _make(count=1)
    _, left, right = split(chunks, "c-0", at_offset=2)
    assert left.headings == ["H0"]
    assert right.headings == ["H0"]


def test_split_shifts_subsequent_sequences() -> None:
    chunks = _make(count=3)
    out, _, _ = split(chunks, "c-0", at_offset=2)
    # After split, c-1 (was seq=1) and c-2 (was seq=2) shift up by 1.
    seqs = sorted(c.sequence for c in out)
    assert seqs == [0, 1, 2, 3]


def test_split_at_zero_offset_raises() -> None:
    chunks = _make()
    with pytest.raises(ChunkEditingError):
        split(chunks, "c-0", at_offset=0)


def test_split_beyond_text_length_raises() -> None:
    chunks = _make()
    target = next(c for c in chunks if c.id == "c-0")
    with pytest.raises(ChunkEditingError):
        split(chunks, "c-0", at_offset=len(target.text))
