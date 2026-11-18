"""Tests for the chunkset hash function (#204)."""

from __future__ import annotations

from domain.hashing import hash_chunkset
from domain.value_objects import ChunkBbox, ChunkDocItem, ChunkResult


def _chunk(text: str, *, page: int | None = 1, headings=()) -> ChunkResult:
    return ChunkResult(text=text, headings=list(headings), source_page=page)


def test_empty_chunkset_returns_empty_sha256() -> None:
    """Empty input has a stable, well-known hash."""
    h = hash_chunkset([])
    # SHA-256 of nothing is the well-known constant.
    assert h == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_determinism_across_invocations() -> None:
    chunks = [_chunk("a"), _chunk("b"), _chunk("c")]
    assert hash_chunkset(chunks) == hash_chunkset(chunks)


def test_text_change_changes_hash() -> None:
    base = [_chunk("alpha")]
    edited = [_chunk("alpha!")]
    assert hash_chunkset(base) != hash_chunkset(edited)


def test_page_change_changes_hash() -> None:
    a = [_chunk("alpha", page=1)]
    b = [_chunk("alpha", page=2)]
    assert hash_chunkset(a) != hash_chunkset(b)


def test_headings_change_changes_hash() -> None:
    a = [_chunk("alpha", headings=("Section A",))]
    b = [_chunk("alpha", headings=("Section B",))]
    assert hash_chunkset(a) != hash_chunkset(b)


def test_excluded_fields_do_not_change_hash() -> None:
    """token_count, bboxes, doc_items are deliberately excluded."""
    a = ChunkResult(text="alpha", headings=[], source_page=1, token_count=100, bboxes=[])
    b = ChunkResult(
        text="alpha",
        headings=[],
        source_page=1,
        token_count=999,  # different
        bboxes=[ChunkBbox(page=1, bbox=[0, 0, 10, 10])],  # different
        doc_items=[ChunkDocItem(self_ref="#/x", label="text")],  # different
    )
    assert hash_chunkset([a]) == hash_chunkset([b])


def test_join_attack_resistance() -> None:
    """Splitting one chunk into two with the same combined content must
    produce a different hash from the original single-chunk version."""
    one = [_chunk("HelloWorld")]
    two = [_chunk("Hello"), _chunk("World")]
    assert hash_chunkset(one) != hash_chunkset(two)


def test_order_matters() -> None:
    a = [_chunk("alpha"), _chunk("bravo")]
    b = [_chunk("bravo"), _chunk("alpha")]
    assert hash_chunkset(a) != hash_chunkset(b)


def test_locked_fixture_three_chunks() -> None:
    """Locked fixture: a hand-built 3-chunk input has a fixed expected
    hash. CI fails loud if anyone changes the canonical input list
    without updating the fixture deliberately.

    The expected hash below was computed once with the function as
    pinned in this commit. To regenerate after a deliberate canonical
    change, run:

        python -c 'from domain.hashing import hash_chunkset; \\
                   from domain.value_objects import ChunkResult; \\
                   print(hash_chunkset([
                     ChunkResult(text="Intro paragraph.", source_page=1,
                                 headings=["Intro"]),
                     ChunkResult(text="Body of section A.", source_page=2,
                                 headings=["A"]),
                     ChunkResult(text="Conclusion.", source_page=3,
                                 headings=["Conclusion"]),
                   ]))'
    """
    chunks = [
        ChunkResult(text="Intro paragraph.", source_page=1, headings=["Intro"]),
        ChunkResult(text="Body of section A.", source_page=2, headings=["A"]),
        ChunkResult(text="Conclusion.", source_page=3, headings=["Conclusion"]),
    ]
    expected = "6ac365ae403e53675e57884b69b0629684f2209c39730093231caa11a40e5225"
    actual = hash_chunkset(chunks)
    assert actual == expected, (
        f"Hash drift detected. Expected {expected}, got {actual}. "
        "If you intentionally changed the canonical inputs, update this "
        "fixture and document the breaking change in the release notes."
    )
