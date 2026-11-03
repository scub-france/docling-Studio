"""Tests for the pure chunk-editing rules (#205, audit 0.7.4 01 MAJ-1).

These are the rules `ChunkService` ships. The draft this module used to hold
(whole-chunkset `insert` / `update` / `delete`, a merge that kept the smallest
page and accepted gaps, a split that dropped bboxes) was never called and is
gone with its tests; the service-level tests in `test_chunk_service.py` pin
the same rules end to end, persistence and journal included.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.chunk_editing import (
    MERGE_SEPARATOR,
    ChunkEditingError,
    InvalidChunkEditError,
    NonContiguousMergeError,
    UnknownChunkError,
    chunkset_from_results,
    journal_entry,
    merge,
    sequence_after,
    split,
)
from domain.chunk_serialization import chunk_to_audit_dict
from domain.models import Chunk
from domain.value_objects import ChunkBbox, ChunkDocItem, ChunkEditAction, ChunkResult

AT = datetime(2026, 1, 1, tzinfo=UTC)


def _make(count: int = 3, document_id: str = "doc-1") -> list[Chunk]:
    return [
        Chunk(
            id=f"c-{i}",
            document_id=document_id,
            sequence=i,
            text=f"text {i}",
            headings=[f"H{i}"],
            source_page=i + 1,
            bboxes=[ChunkBbox(page=i + 1, bbox=[float(i), 0.0, 1.0, 1.0])],
            doc_items=[ChunkDocItem(self_ref=f"#/texts/{i}", label="text")],
            token_count=i + 1,
        )
        for i in range(count)
    ]


def test_every_refusal_is_a_chunk_editing_error() -> None:
    for error in (InvalidChunkEditError, UnknownChunkError, NonContiguousMergeError):
        assert issubclass(error, ChunkEditingError)


# ---------------------------------------------------------------------------
# sequence_after
# ---------------------------------------------------------------------------


def test_sequence_after_none_appends_after_the_highest_sequence() -> None:
    chunks = _make(3)
    chunks[1].sequence = 7  # gaps allowed
    assert sequence_after(chunks, None) == 8


def test_sequence_after_none_on_an_empty_chunkset_is_zero() -> None:
    assert sequence_after([], None) == 0


def test_sequence_after_an_anchor_is_the_next_slot() -> None:
    assert sequence_after(_make(3), "c-1") == 2


def test_sequence_after_an_unknown_anchor_is_refused() -> None:
    with pytest.raises(UnknownChunkError, match="Anchor chunk not found: ghost"):
        sequence_after(_make(), "ghost")


# ---------------------------------------------------------------------------
# split
# ---------------------------------------------------------------------------


def test_split_cuts_the_text_into_two_new_chunks() -> None:
    source = _make(1)[0]
    head, tail = split(source, 4)
    assert (head.text, tail.text) == ("text", " 0")
    assert (head.sequence, tail.sequence) == (0, 1)
    assert len({head.id, tail.id, source.id}) == 3


def test_split_halves_inherit_everything_but_the_token_count() -> None:
    source = _make(1)[0]
    for half in split(source, 2):
        assert half.document_id == source.document_id
        assert half.headings == source.headings
        assert half.headings is not source.headings
        assert half.source_page == source.source_page
        assert half.bboxes == source.bboxes
        assert half.doc_items == source.doc_items
        assert half.token_count is None


def test_split_leaves_the_source_untouched() -> None:
    source = _make(1)[0]
    split(source, 2)
    assert (source.text, source.sequence, source.deleted_at) == ("text 0", 0, None)


@pytest.mark.parametrize("offset", [-1, 0, 6, 99])
def test_split_offset_must_leave_a_character_on_each_side(offset: int) -> None:
    source = _make(1)[0]
    with pytest.raises(InvalidChunkEditError, match="out of range for chunk of length 6"):
        split(source, offset)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


def test_merge_takes_the_sources_in_sequence_order() -> None:
    chunks = _make(3)
    sources, merged = merge(chunks, ["c-2", "c-0", "c-1"])
    assert [c.id for c in sources] == ["c-0", "c-1", "c-2"]
    assert merged.text == MERGE_SEPARATOR.join(["text 0", "text 1", "text 2"])
    assert merged.text == "text 0\ntext 1\ntext 2"


def test_merge_keeps_the_first_sources_place_headings_and_page() -> None:
    chunks = _make(2)
    chunks[0].source_page = 9  # not the smallest: the first source's wins
    _, merged = merge(chunks, ["c-1", "c-0"])
    assert merged.sequence == 0
    assert merged.headings == ["H0"]
    assert merged.source_page == 9
    assert merged.id not in {"c-0", "c-1"}


def test_merge_concatenates_bboxes_and_doc_items_and_sums_tokens() -> None:
    chunks = _make(2)
    _, merged = merge(chunks, ["c-0", "c-1"])
    assert merged.bboxes == chunks[0].bboxes + chunks[1].bboxes
    assert merged.doc_items == chunks[0].doc_items + chunks[1].doc_items
    assert merged.token_count == 3


@pytest.mark.parametrize("counts", [(None, None), (0, 0), (None, 0)])
def test_merge_without_a_known_token_count_leaves_it_unknown(counts) -> None:
    chunks = _make(2)
    for chunk, count in zip(chunks, counts, strict=True):
        chunk.token_count = count
    _, merged = merge(chunks, ["c-0", "c-1"])
    assert merged.token_count is None


@pytest.mark.parametrize("ids", [[], ["c-0"]])
def test_merge_requires_at_least_two_ids(ids) -> None:
    with pytest.raises(InvalidChunkEditError, match="merge requires at least 2 chunk ids"):
        merge(_make(), ids)


def test_merge_names_the_ids_it_cannot_find() -> None:
    with pytest.raises(UnknownChunkError, match=r"Chunks not found: \['x', 'y'\]"):
        merge(_make(), ["c-0", "x", "y"])


def test_merge_refuses_a_gap_in_sequences() -> None:
    with pytest.raises(NonContiguousMergeError, match="contiguous chunks"):
        merge(_make(3), ["c-0", "c-2"])


def test_merge_refuses_the_same_chunk_twice() -> None:
    with pytest.raises(NonContiguousMergeError):
        merge(_make(2), ["c-0", "c-0"])


def test_merge_leaves_the_sources_untouched() -> None:
    chunks = _make(2)
    merge(chunks, ["c-0", "c-1"])
    assert [(c.id, c.sequence, c.deleted_at) for c in chunks] == [
        ("c-0", 0, None),
        ("c-1", 1, None),
    ]


# ---------------------------------------------------------------------------
# chunkset_from_results
# ---------------------------------------------------------------------------


def test_chunkset_from_results_numbers_new_chunks_from_zero() -> None:
    box = ChunkBbox(page=2, bbox=[0.0, 1.0, 2.0, 3.0])
    item = ChunkDocItem(self_ref="#/texts/4", label="text")
    results = [
        ChunkResult(text="a", headings=["H"], source_page=2, token_count=7, bboxes=[box]),
        ChunkResult(text="b", token_count=0, doc_items=[item]),
    ]
    a, b = chunkset_from_results("doc-9", results)
    assert [(c.document_id, c.sequence, c.text) for c in (a, b)] == [
        ("doc-9", 0, "a"),
        ("doc-9", 1, "b"),
    ]
    assert (a.headings, a.source_page, a.bboxes, a.token_count) == (["H"], 2, [box], 7)
    assert (b.doc_items, b.token_count) == ([item], None)
    assert a.id != b.id


# ---------------------------------------------------------------------------
# journal_entry
# ---------------------------------------------------------------------------


def test_journal_entry_records_snapshots_in_the_journal_shape() -> None:
    before, after = _make(2)
    edit = journal_entry(
        "doc-1", "c-0", ChunkEditAction.UPDATE, actor="user", at=AT, before=before, after=after
    )
    assert (edit.document_id, edit.chunk_id, edit.action, edit.actor, edit.at) == (
        "doc-1",
        "c-0",
        ChunkEditAction.UPDATE,
        "user",
        AT,
    )
    assert edit.before == chunk_to_audit_dict(before)
    assert edit.after == chunk_to_audit_dict(after)
    assert (edit.parents, edit.children, edit.reason) == ([], [], None)
    assert len(edit.id) == 36  # str(uuid4()), as the chunk paths always wrote


def test_journal_entry_without_snapshots_or_with_lineage() -> None:
    bare = journal_entry("d", "c", ChunkEditAction.DELETE, actor="system", at=AT, edit_id="e1")
    assert (bare.id, bare.before, bare.after) == ("e1", None, None)
    merged = journal_entry("d", "m", ChunkEditAction.MERGE, actor="u", at=AT, parents=["a", "b"])
    split_ = journal_entry("d", "s", ChunkEditAction.SPLIT, actor="u", at=AT, children=["h", "t"])
    assert (merged.parents, split_.children) == (["a", "b"], ["h", "t"])
