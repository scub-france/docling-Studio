"""Tests for the chunkset hash recorded on a push (#204, audit 0.7.4 01 MAJ-1).

The rule is the one `push_to_store` has always written: id, text and
`str(updated_at)` per chunk. The golden values are the hashes the service's
own function produced before the rule moved to the domain; they pin that
every hash already stored still matches a fresh one on unchanged chunks.
`test_chunk_formats.py` checks the same values end to end, through a push.
"""

from __future__ import annotations

from datetime import UTC, datetime

from domain.hashing import chunkset_hash
from domain.models import Chunk
from domain.value_objects import ChunkBbox, ChunkDocItem

T0 = datetime(2026, 5, 19, 10, 0, tzinfo=UTC)


def _chunk(id_: str = "c-1", text: str = "alpha", *, at: datetime = T0, **fields) -> Chunk:
    return Chunk(id=id_, document_id="doc-1", text=text, updated_at=at, **fields)


def _golden_chunks() -> list[Chunk]:
    return [
        _chunk("c-1", "Intro paragraph."),
        _chunk("c-2", "Body — été ✓", at=datetime(2026, 5, 19, 10, 1, 2, 345678, tzinfo=UTC)),
        _chunk("c-3", "", at=datetime(2026, 5, 19, 10, 2, tzinfo=UTC)),
    ]


def test_empty_chunkset_returns_empty_sha256() -> None:
    assert chunkset_hash([]) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_golden_values_of_the_rule_that_shipped() -> None:
    """Computed with `services.chunk_service._compute_chunkset_hash` before it
    moved here. A drift re-flips every stored link: release-note it."""
    chunks = _golden_chunks()
    assert chunkset_hash(chunks) == (
        "fee1efd47fb90ba0d763258ae55b566f80c039af08999961bf0e7cbb065decb2"
    )
    assert chunkset_hash(chunks[:1]) == (
        "3e6e2c8d4c62cae8b2486e0678cc78230c752d62a528acc7816a2c4fe9813bfa"
    )


def test_determinism_across_invocations() -> None:
    chunks = _golden_chunks()
    assert chunkset_hash(chunks) == chunkset_hash(iter(chunks))


def test_text_change_changes_hash() -> None:
    assert chunkset_hash([_chunk(text="alpha")]) != chunkset_hash([_chunk(text="alpha!")])


def test_id_change_changes_hash() -> None:
    assert chunkset_hash([_chunk("c-1")]) != chunkset_hash([_chunk("c-2")])


def test_an_edit_that_keeps_the_text_still_changes_the_hash() -> None:
    later = datetime(2026, 5, 19, 10, 0, 1, tzinfo=UTC)
    assert chunkset_hash([_chunk(at=T0)]) != chunkset_hash([_chunk(at=later)])


def test_fields_outside_the_rule_do_not_change_the_hash() -> None:
    bare = _chunk()
    dressed = _chunk(
        sequence=9,
        headings=["Section"],
        source_page=4,
        token_count=999,
        bboxes=[ChunkBbox(page=1, bbox=[0, 0, 10, 10])],
        doc_items=[ChunkDocItem(self_ref="#/x", label="text")],
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    assert chunkset_hash([bare]) == chunkset_hash([dressed])


def test_join_attack_resistance() -> None:
    """Splitting one chunk's text across two chunks never hashes the same."""
    one = [_chunk("c", "HelloWorld")]
    two = [_chunk("c", "Hello"), _chunk("c", "World")]
    assert chunkset_hash(one) != chunkset_hash(two)


def test_order_matters() -> None:
    a, b = _chunk("c-1", "alpha"), _chunk("c-2", "bravo")
    assert chunkset_hash([a, b]) != chunkset_hash([b, a])
