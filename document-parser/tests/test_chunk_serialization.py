"""Unit tests for the chunk ↔ dict shapes (audit 0.7.4, 05 MIN).

`test_chunk_formats.py` pins the bytes each write path persists; these pin
the module's own contract: the key order of each shape, and that one reader
reads all of them back.
"""

from __future__ import annotations

from datetime import UTC, datetime

from domain.chunk_serialization import (
    chunk_from_dict,
    chunk_to_audit_dict,
    chunk_to_ingestion_dict,
    chunk_to_snapshot_dict,
)
from domain.models import Chunk
from domain.value_objects import ChunkBbox, ChunkDocItem

CORE_KEYS = ["text", "headings", "sourcePage", "tokenCount", "bboxes", "docItems"]


def _chunk(**fields) -> Chunk:
    return Chunk(
        id="c-1",
        document_id="doc-1",
        sequence=3,
        text="t",
        headings=["H"],
        source_page=2,
        bboxes=[ChunkBbox(page=2, bbox=[1.0, 2.0, 3.0, 4.0])],
        doc_items=[ChunkDocItem(self_ref="#/texts/1", label="text")],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        **fields,
    )


def test_each_shape_keeps_its_key_order() -> None:
    c = _chunk()
    assert list(chunk_to_audit_dict(c)) == ["id", "sequence", *CORE_KEYS]
    assert list(chunk_to_ingestion_dict(c)) == CORE_KEYS
    assert list(chunk_to_snapshot_dict(c)) == [
        "id",
        "documentId",
        "sequence",
        *CORE_KEYS,
        "createdAt",
        "updatedAt",
    ]


def test_the_journal_spells_doc_items_self_ref_and_the_others_self_ref_camel() -> None:
    c = _chunk()
    assert chunk_to_audit_dict(c)["docItems"] == [{"self_ref": "#/texts/1", "label": "text"}]
    for shape in (chunk_to_ingestion_dict(c), chunk_to_snapshot_dict(c)):
        assert shape["docItems"] == [{"selfRef": "#/texts/1", "label": "text"}]


def test_only_the_ingestion_turns_an_unknown_token_count_into_zero() -> None:
    c = _chunk()
    assert chunk_to_ingestion_dict(c)["tokenCount"] == 0
    assert chunk_to_audit_dict(c)["tokenCount"] is None
    assert chunk_to_snapshot_dict(c)["tokenCount"] is None


def test_the_reader_reads_every_written_shape_back() -> None:
    c = _chunk(token_count=5)
    for shape in (chunk_to_audit_dict(c), chunk_to_ingestion_dict(c), chunk_to_snapshot_dict(c)):
        back = chunk_from_dict(shape, document_id="doc-2", sequence=7, chunk_id="new")
        assert (back.id, back.document_id, back.sequence) == ("new", "doc-2", 7)
        assert (back.text, back.headings, back.source_page) == ("t", ["H"], 2)
        assert (back.bboxes, back.doc_items, back.token_count) == (c.bboxes, c.doc_items, 5)


def test_without_an_id_the_reader_mints_one_and_fresh_dates() -> None:
    back = chunk_from_dict(chunk_to_snapshot_dict(_chunk()), document_id="d", sequence=0)
    assert back.id != "c-1"
    assert back.created_at != datetime(2026, 1, 1, tzinfo=UTC)


def test_an_empty_entry_reads_as_an_empty_chunk() -> None:
    back = chunk_from_dict({}, document_id="d", sequence=0)
    assert (back.text, back.headings, back.source_page, back.token_count) == ("", [], None, None)
    assert (back.bboxes, back.doc_items) == ([], [])
