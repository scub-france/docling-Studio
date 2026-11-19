"""Tests for the pure-domain chunk-editing operations (#205)."""

from __future__ import annotations

import pytest

from domain.chunk_editing import (
    ChunkEditingError,
    ChunkMergeGapError,
    check_merge_count,
    delete,
    insert,
    merge,
    split,
    update,
)
from domain.models import Chunk
from domain.value_objects import ChunkBbox, ChunkDocItem


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
                bboxes=[ChunkBbox(page=i + 1, bbox=[0.0, 0.0, 1.0, 1.0])],
                doc_items=[ChunkDocItem(self_ref=f"#/texts/{i}", label="text")],
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


def test_insert_gives_a_compact_id() -> None:
    _, new = insert(_make(count=1), at_position=0, text="x", document_id="doc-1")
    assert len(new.id) == 32
    assert "-" not in new.id


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
# merge — the rules `ChunkService.merge_chunks` applies
# ---------------------------------------------------------------------------


def test_merge_orders_the_sources_by_sequence() -> None:
    c0, c1, _ = _make(count=3)
    ordered, merged = merge([c1, c0], document_id="doc-1")
    assert [c.id for c in ordered] == ["c-0", "c-1"]
    assert merged.text == "text 0\ntext 1"
    assert merged.sequence == 0


def test_merge_keeps_the_first_source_headings_and_page() -> None:
    c0, c1, _ = _make(count=3)
    c0.source_page = None
    _, merged = merge([c0, c1], document_id="doc-1")
    assert merged.headings == ["H0"]
    # The first source's page, even when it has none: not the smallest.
    assert merged.source_page is None


def test_merge_concatenates_bboxes_and_doc_items() -> None:
    c0, c1, c2 = _make(count=3)
    _, merged = merge([c2, c0, c1], document_id="doc-1")
    assert [b.page for b in merged.bboxes] == [1, 2, 3]
    assert [d.self_ref for d in merged.doc_items] == ["#/texts/0", "#/texts/1", "#/texts/2"]


def test_merge_sums_token_counts() -> None:
    c0, c1, _ = _make(count=3)
    c0.token_count = 3
    _, merged = merge([c0, c1], document_id="doc-1")
    assert merged.token_count == 3


def test_merge_token_count_is_none_when_the_sum_is_zero() -> None:
    c0, c1, _ = _make(count=3)
    c0.token_count = 0
    _, merged = merge([c0, c1], document_id="doc-1")
    assert merged.token_count is None


def test_merge_gives_a_fresh_chunk_of_the_document() -> None:
    c0, c1, _ = _make(count=3)
    _, merged = merge([c0, c1], document_id="doc-1")
    assert merged.id not in {"c-0", "c-1"}
    assert len(merged.id) == 36  # the `Chunk` default, dashed UUID4
    assert merged.document_id == "doc-1"
    assert merged.deleted_at is None


def test_merge_requires_contiguous_sequences() -> None:
    c0, _, c2 = _make(count=3)
    with pytest.raises(ChunkMergeGapError, match=r"^merge requires contiguous chunks \(by"):
        merge([c0, c2], document_id="doc-1")


def test_merge_of_the_same_chunk_twice_is_not_contiguous() -> None:
    c0, _, _ = _make(count=3)
    with pytest.raises(ChunkMergeGapError):
        merge([c0, c0], document_id="doc-1")


def test_merge_requires_at_least_two_chunks() -> None:
    c0, _, _ = _make(count=3)
    with pytest.raises(ChunkEditingError, match="^merge requires at least 2 chunk ids$"):
        merge([c0], document_id="doc-1")
    with pytest.raises(ChunkEditingError, match="^merge requires at least 2 chunk ids$"):
        check_merge_count(["c-0"])
    check_merge_count(["c-0", "c-1"])


def test_a_gap_is_a_chunk_editing_error() -> None:
    assert issubclass(ChunkMergeGapError, ChunkEditingError)


# ---------------------------------------------------------------------------
# split — the rules `ChunkService.split_chunk` applies
# ---------------------------------------------------------------------------


def test_split_cuts_the_text_at_the_offset() -> None:
    source = _make(count=1)[0]
    head, tail = split(source, at_offset=4, document_id="doc-1")
    assert head.text == "text"
    assert tail.text == " 0"


def test_split_halves_follow_the_source_sequence() -> None:
    source = _make(count=3)[1]
    head, tail = split(source, at_offset=2, document_id="doc-1")
    assert (head.sequence, tail.sequence) == (1, 2)


def test_split_halves_inherit_the_source_metadata() -> None:
    source = _make(count=1)[0]
    source.token_count = 12
    head, tail = split(source, at_offset=2, document_id="doc-1")
    for half in (head, tail):
        assert half.headings == ["H0"]
        assert half.source_page == 1
        assert half.bboxes == source.bboxes
        assert half.doc_items == source.doc_items
        # Unknown after a split.
        assert half.token_count is None
        assert half.id != source.id
        assert half.document_id == "doc-1"
    # Copies, not the source's lists.
    assert head.headings is not source.headings
    assert head.bboxes is not source.bboxes


def test_split_leaves_the_source_untouched() -> None:
    source = _make(count=1)[0]
    split(source, at_offset=2, document_id="doc-1")
    assert source.text == "text 0"
    assert source.deleted_at is None


@pytest.mark.parametrize("offset", [0, -1, 6, 99])
def test_split_offset_out_of_range_raises(offset: int) -> None:
    source = _make(count=1)[0]
    with pytest.raises(ChunkEditingError) as caught:
        split(source, at_offset=offset, document_id="doc-1")
    assert str(caught.value) == f"cursorOffset {offset} out of range for chunk of length 6"
