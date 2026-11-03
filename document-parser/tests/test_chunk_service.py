"""Tests for ChunkService — canonical chunk lifecycle (#256)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.models import AnalysisJob, AnalysisStatus, Chunk, Document
from domain.value_objects import (
    ChunkBbox,
    ChunkDocItem,
    ChunkEditAction,
    ChunkResult,
)
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_edit_repo import (
    SqliteChunkEditRepository,
)
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from services.chunk_errors import (
    ChunkConflictError,
    ChunkNotFoundError,
    ChunkServiceError,
    ChunkValidationError,
)
from services.chunk_service import ChunkService
from services.navigation_errors import DocumentNotFoundError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()
    yield


@pytest.fixture
async def doc():
    repo = SqliteDocumentRepository()
    document = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
    await repo.insert(document)
    return document


@pytest.fixture
def repos():
    return {
        "chunks": SqliteChunkRepository(),
        "edits": SqliteChunkEditRepository(),
        "documents": SqliteDocumentRepository(),
        "analyses": SqliteAnalysisRepository(),
    }


@pytest.fixture
def service(repos):
    return ChunkService(
        chunk_repo=repos["chunks"],
        chunk_edit_repo=repos["edits"],
        document_repo=repos["documents"],
        analysis_repo=repos["analyses"],
        chunker=None,
    )


# ---------------------------------------------------------------------------
# list_chunks
# ---------------------------------------------------------------------------


class TestListChunks:
    async def test_list_empty(self, service, doc):
        assert await service.list_chunks(doc.id) == []

    async def test_list_filters_deleted(self, service, repos, doc):
        a = Chunk(document_id=doc.id, sequence=0, text="alpha")
        b = Chunk(document_id=doc.id, sequence=1, text="beta", deleted_at=datetime.now(UTC))
        await repos["chunks"].insert_many([a, b])
        chunks = await service.list_chunks(doc.id)
        assert [c.id for c in chunks] == [a.id]

    async def test_404_on_missing_doc(self, service):
        with pytest.raises(DocumentNotFoundError):
            await service.list_chunks("no-such")


# ---------------------------------------------------------------------------
# add_chunk
# ---------------------------------------------------------------------------


class TestAddChunk:
    async def test_append_to_empty(self, service, repos, doc):
        new = await service.add_chunk(doc.id, text="hello")
        assert new.sequence == 0
        chunks = await service.list_chunks(doc.id)
        assert [c.text for c in chunks] == ["hello"]
        edits = await repos["edits"].find_for_document(doc.id)
        assert len(edits) == 1
        assert edits[0].action == ChunkEditAction.INSERT
        assert edits[0].after is not None

    async def test_append_after_anchor_shifts_sequences(self, service, repos, doc):
        first = await service.add_chunk(doc.id, text="a")
        last = await service.add_chunk(doc.id, text="c")
        middle = await service.add_chunk(doc.id, text="b", after_id=first.id)

        chunks = await service.list_chunks(doc.id)
        # Order should now be a, b, c
        assert [c.text for c in chunks] == ["a", "b", "c"]
        # Sequences must be dense ascending
        assert [c.sequence for c in chunks] == [0, 1, 2]
        assert chunks[1].id == middle.id
        # `last` was shifted from sequence=1 to sequence=2
        refreshed_last = next(c for c in chunks if c.id == last.id)
        assert refreshed_last.sequence == 2

    async def test_anchor_not_found(self, service, doc):
        with pytest.raises(ChunkNotFoundError):
            await service.add_chunk(doc.id, text="x", after_id="no-such")


# ---------------------------------------------------------------------------
# update_chunk
# ---------------------------------------------------------------------------


class TestUpdateChunk:
    async def test_update_text_records_audit(self, service, repos, doc):
        new = await service.add_chunk(doc.id, text="hi")
        updated = await service.update_chunk(doc.id, new.id, text="hi there")
        assert updated.text == "hi there"
        edits = await repos["edits"].find_for_document(doc.id)
        assert {e.action for e in edits} == {ChunkEditAction.INSERT, ChunkEditAction.UPDATE}
        update_edit = next(e for e in edits if e.action == ChunkEditAction.UPDATE)
        assert update_edit.before["text"] == "hi"
        assert update_edit.after["text"] == "hi there"

    async def test_404_on_missing_chunk(self, service, doc):
        with pytest.raises(ChunkNotFoundError):
            await service.update_chunk(doc.id, "no-such", text="x")

    async def test_404_on_chunk_from_other_doc(self, service, repos, doc):
        other = Document(id="doc-2", filename="o.pdf", storage_path="/tmp/o.pdf")
        await repos["documents"].insert(other)
        new = await service.add_chunk(other.id, text="x")
        with pytest.raises(ChunkNotFoundError):
            await service.update_chunk(doc.id, new.id, text="y")


# ---------------------------------------------------------------------------
# delete_chunk
# ---------------------------------------------------------------------------


class TestDeleteChunk:
    async def test_soft_deletes_and_records_audit(self, service, repos, doc):
        new = await service.add_chunk(doc.id, text="x")
        await service.delete_chunk(doc.id, new.id)
        # Soft-deleted: still in repo with deleted_at set, list filters it.
        assert await service.list_chunks(doc.id) == []
        edits = await repos["edits"].find_for_document(doc.id)
        assert any(e.action == ChunkEditAction.DELETE for e in edits)


# ---------------------------------------------------------------------------
# split_chunk
# ---------------------------------------------------------------------------


class TestSplitChunk:
    async def test_split_produces_two_chunks(self, service, repos, doc):
        src = await service.add_chunk(doc.id, text="abcdef")
        head, tail = await service.split_chunk(doc.id, src.id, cursor_offset=3)
        assert head.text == "abc"
        assert tail.text == "def"
        chunks = await service.list_chunks(doc.id)
        assert [c.text for c in chunks] == ["abc", "def"]
        edits = await repos["edits"].find_for_document(doc.id)
        split_edit = next(e for e in edits if e.action == ChunkEditAction.SPLIT)
        assert split_edit.children == [head.id, tail.id]
        assert split_edit.before is not None

    async def test_split_400_on_offset_out_of_range(self, service, doc):
        src = await service.add_chunk(doc.id, text="abc")
        with pytest.raises(ChunkValidationError):
            await service.split_chunk(doc.id, src.id, cursor_offset=0)
        with pytest.raises(ChunkValidationError):
            await service.split_chunk(doc.id, src.id, cursor_offset=99)

    async def test_split_shifts_subsequent_chunks(self, service, doc):
        a = await service.add_chunk(doc.id, text="abcdef")
        await service.add_chunk(doc.id, text="next")
        await service.split_chunk(doc.id, a.id, cursor_offset=3)
        chunks = await service.list_chunks(doc.id)
        # New head, new tail, then `next` at sequence 2
        assert [c.text for c in chunks] == ["abc", "def", "next"]
        assert [c.sequence for c in chunks] == [0, 1, 2]


# ---------------------------------------------------------------------------
# merge_chunks
# ---------------------------------------------------------------------------


class TestMergeChunks:
    async def test_merge_contiguous(self, service, repos, doc):
        a = await service.add_chunk(doc.id, text="a")
        b = await service.add_chunk(doc.id, text="b")
        await service.add_chunk(doc.id, text="c")
        merged = await service.merge_chunks(doc.id, [b.id, a.id])  # order irrelevant
        # Merged contains a,b
        assert merged.text == "a\nb"
        chunks = await service.list_chunks(doc.id)
        # New chunk at sequence 0, then `c` still at 2 (gap is allowed)
        assert {c2.text for c2 in chunks} == {"a\nb", "c"}
        edit = next(
            e
            for e in await repos["edits"].find_for_document(doc.id)
            if e.action == ChunkEditAction.MERGE
        )
        assert set(edit.parents) == {a.id, b.id}

    async def test_merge_409_on_non_contiguous(self, service, doc):
        a = await service.add_chunk(doc.id, text="a")
        await service.add_chunk(doc.id, text="b")
        c = await service.add_chunk(doc.id, text="c")
        with pytest.raises(ChunkConflictError):
            await service.merge_chunks(doc.id, [a.id, c.id])

    async def test_merge_validates_min_two(self, service, doc):
        a = await service.add_chunk(doc.id, text="a")
        with pytest.raises(ChunkValidationError):
            await service.merge_chunks(doc.id, [a.id])


class TestSplitRules:
    """The split the editor ships, pinned on its edges (audit 0.7.4, 01 MAJ-1)."""

    async def test_both_halves_inherit_everything_but_the_token_count(self, service, repos, doc):
        src = Chunk(
            document_id=doc.id,
            sequence=4,
            text="abcdef",
            headings=["H1", "H2"],
            source_page=3,
            bboxes=[ChunkBbox(page=3, bbox=[1.0, 2.0, 3.0, 4.0])],
            doc_items=[ChunkDocItem(self_ref="#/texts/7", label="text")],
            token_count=12,
        )
        await repos["chunks"].insert(src)

        head, tail = await service.split_chunk(doc.id, src.id, cursor_offset=2)

        assert (head.sequence, tail.sequence) == (4, 5)
        assert (head.text, tail.text) == ("ab", "cdef")
        for half in (head, tail):
            assert half.document_id == doc.id
            assert half.headings == ["H1", "H2"]
            assert half.source_page == 3
            assert half.bboxes == src.bboxes
            assert half.doc_items == src.doc_items
            assert half.token_count is None
        assert len({head.id, tail.id, src.id}) == 3
        retired = await repos["chunks"].find_by_id(src.id)
        assert retired.deleted_at is not None

    @pytest.mark.parametrize("offset", [-1, 0, 6, 7])
    async def test_offset_must_fall_strictly_inside_the_text(self, service, doc, offset):
        src = await service.add_chunk(doc.id, text="abcdef")
        expected = f"cursorOffset {offset} out of range for chunk of length 6"
        with pytest.raises(ChunkValidationError, match=re.escape(expected)):
            await service.split_chunk(doc.id, src.id, cursor_offset=offset)
        assert [c.id for c in await service.list_chunks(doc.id)] == [src.id]

    @pytest.mark.parametrize(("offset", "texts"), [(1, ("a", "bcdef")), (5, ("abcde", "f"))])
    async def test_the_extreme_offsets_leave_one_character(self, service, doc, offset, texts):
        src = await service.add_chunk(doc.id, text="abcdef")
        head, tail = await service.split_chunk(doc.id, src.id, cursor_offset=offset)
        assert (head.text, tail.text) == texts

    async def test_the_offset_counts_characters_not_bytes(self, service, doc):
        src = await service.add_chunk(doc.id, text="été✓x")
        head, tail = await service.split_chunk(doc.id, src.id, cursor_offset=3)
        assert (head.text, tail.text) == ("été", "✓x")

    async def test_a_deleted_chunk_cannot_be_split(self, service, doc):
        src = await service.add_chunk(doc.id, text="abcdef")
        await service.delete_chunk(doc.id, src.id)
        with pytest.raises(ChunkNotFoundError):
            await service.split_chunk(doc.id, src.id, cursor_offset=2)


class TestMergeRules:
    """The merge the editor ships, pinned on its edges (audit 0.7.4, 01 MAJ-1)."""

    async def test_sources_follow_the_sequence_not_the_ids_given(self, service, repos, doc):
        box = [ChunkBbox(page=p, bbox=[float(p), 0.0, 1.0, 1.0]) for p in range(4)]
        item_a = ChunkDocItem(self_ref="#/texts/0", label="text")
        item_b = ChunkDocItem(self_ref="#/texts/1", label="list_item")
        a = Chunk(
            document_id=doc.id,
            sequence=0,
            text="a",
            headings=["Ha"],
            source_page=5,
            bboxes=[box[0]],
            doc_items=[item_a],
            token_count=3,
        )
        b = Chunk(
            document_id=doc.id,
            sequence=1,
            text="b",
            headings=["Hb"],
            source_page=1,
            bboxes=[box[1]],
            doc_items=[item_b],
        )
        c = Chunk(
            document_id=doc.id,
            sequence=2,
            text="c",
            source_page=2,
            bboxes=[box[2], box[3]],
            token_count=4,
        )
        await repos["chunks"].insert_many([a, b, c])

        merged = await service.merge_chunks(doc.id, [c.id, a.id, b.id])

        assert merged.text == "a\nb\nc"
        assert merged.sequence == 0
        assert merged.headings == ["Ha"]
        assert merged.source_page == 5, "the first source's page, not the smallest"
        assert merged.bboxes == box
        assert merged.doc_items == [item_a, item_b]
        assert merged.token_count == 7
        assert merged.id not in {a.id, b.id, c.id}
        assert [x.id for x in await service.list_chunks(doc.id)] == [merged.id]

    @pytest.mark.parametrize("counts", [(None, None), (0, None), (0, 0)])
    async def test_no_known_token_count_stays_unknown(self, service, repos, doc, counts):
        pair = [
            Chunk(document_id=doc.id, sequence=i, text=str(i), token_count=n)
            for i, n in enumerate(counts)
        ]
        await repos["chunks"].insert_many(pair)
        merged = await service.merge_chunks(doc.id, [c.id for c in pair])
        assert merged.token_count is None

    async def test_a_sequence_gap_refuses_the_merge(self, service, doc):
        """Contiguity is read on `sequence`: a deleted chunk between two live
        ones leaves a gap the merge refuses, though the two look adjacent."""
        a = await service.add_chunk(doc.id, text="a")
        b = await service.add_chunk(doc.id, text="b")
        c = await service.add_chunk(doc.id, text="c")
        await service.delete_chunk(doc.id, b.id)
        with pytest.raises(
            ChunkConflictError, match=re.escape("merge requires contiguous chunks (by sequence)")
        ):
            await service.merge_chunks(doc.id, [a.id, c.id])

    async def test_the_same_id_twice_is_not_contiguous(self, service, doc):
        a = await service.add_chunk(doc.id, text="a")
        await service.add_chunk(doc.id, text="b")
        with pytest.raises(ChunkConflictError):
            await service.merge_chunks(doc.id, [a.id, a.id])

    async def test_unknown_ids_are_named(self, service, doc):
        a = await service.add_chunk(doc.id, text="a")
        with pytest.raises(ChunkNotFoundError, match=re.escape("Chunks not found: ['ghost']")):
            await service.merge_chunks(doc.id, [a.id, "ghost"])

    async def test_a_deleted_or_foreign_chunk_is_not_found(self, service, repos, doc):
        other = Document(id="doc-2", filename="o.pdf", storage_path="/tmp/o.pdf")
        await repos["documents"].insert(other)
        foreign = await service.add_chunk(other.id, text="x")
        a = await service.add_chunk(doc.id, text="a")
        gone = await service.add_chunk(doc.id, text="gone")
        await service.delete_chunk(doc.id, gone.id)
        for intruder in (foreign, gone):
            with pytest.raises(ChunkNotFoundError):
                await service.merge_chunks(doc.id, [a.id, intruder.id])

    @pytest.mark.parametrize("ids", [[], ["only"]])
    async def test_fewer_than_two_ids(self, service, doc, ids):
        with pytest.raises(
            ChunkValidationError, match=re.escape("merge requires at least 2 chunk ids")
        ):
            await service.merge_chunks(doc.id, ids)


# ---------------------------------------------------------------------------
# rechunk_document
# ---------------------------------------------------------------------------


class TestRechunkDocument:
    async def test_rechunk_replaces_canonical(self, service, repos, doc):
        # Seed an existing canonical chunk
        await service.add_chunk(doc.id, text="old")
        # Seed a completed analysis with document_json
        job = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        await repos["analyses"].insert(job)
        job.document_json = json.dumps({"texts": []})
        job.completed_at = datetime.now(UTC)
        await repos["analyses"].update_status(job)

        chunker = MagicMock()
        chunker.chunk = AsyncMock(
            return_value=[
                ChunkResult(text="new1", source_page=1, token_count=4),
                ChunkResult(text="new2", source_page=2, token_count=4),
            ]
        )
        service._chunker = chunker

        result = await service.rechunk_document(doc.id)
        assert [c.text for c in result] == ["new1", "new2"]
        chunks = await service.list_chunks(doc.id)
        assert [c.text for c in chunks] == ["new1", "new2"]

    async def test_rechunk_409_when_no_completed_analysis(self, service, doc):
        service._chunker = MagicMock()
        with pytest.raises(ChunkServiceError):
            await service.rechunk_document(doc.id)

    async def test_rechunk_503_when_no_chunker(self, service, doc):
        with pytest.raises(ChunkServiceError) as exc:
            await service.rechunk_document(doc.id)
        assert exc.value.http_status == 503

    async def test_rechunk_preserves_doc_items_from_chunker(self, service, repos, doc):
        """0.6.1 — the bbox↔chunk linking on the Chunk view depends on
        the canonical chunks carrying `doc_items`. The previous implementation
        dropped them on a stale "ChunkResult has no doc_items" comment.
        """
        # Seed a completed analysis.
        job = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        await repos["analyses"].insert(job)
        job.document_json = json.dumps({"texts": []})
        job.completed_at = datetime.now(UTC)
        await repos["analyses"].update_status(job)

        chunker = MagicMock()
        chunker.chunk = AsyncMock(
            return_value=[
                ChunkResult(
                    text="t",
                    source_page=1,
                    token_count=4,
                    doc_items=[
                        ChunkDocItem(self_ref="#/texts/0", label="text"),
                        ChunkDocItem(self_ref="#/texts/1", label="text"),
                    ],
                ),
            ]
        )
        service._chunker = chunker

        result = await service.rechunk_document(doc.id)
        assert len(result) == 1
        assert [d.self_ref for d in result[0].doc_items] == ["#/texts/0", "#/texts/1"]
        # Persisted chunks carry doc_items too.
        chunks = await service.list_chunks(doc.id)
        assert [d.self_ref for d in chunks[0].doc_items] == ["#/texts/0", "#/texts/1"]


# ---------------------------------------------------------------------------
# promote_from_analysis_if_empty
# ---------------------------------------------------------------------------


class TestPromote:
    async def test_promotes_when_canonical_empty(self, service, repos, doc):
        chunks_json = json.dumps(
            [
                {"text": "first", "headings": ["H"], "sourcePage": 1, "tokenCount": 2},
                {"text": "second", "sourcePage": 2, "tokenCount": 3},
            ]
        )
        promoted = await service.promote_from_analysis_if_empty(doc.id, chunks_json)
        assert promoted == 2
        chunks = await service.list_chunks(doc.id)
        assert [c.text for c in chunks] == ["first", "second"]
        # Audit should record both INSERTs
        edits = await repos["edits"].find_for_document(doc.id)
        assert sum(1 for e in edits if e.action == ChunkEditAction.INSERT) == 2

    async def test_idempotent_when_canonical_not_empty(self, service, doc):
        await service.add_chunk(doc.id, text="manual")
        promoted = await service.promote_from_analysis_if_empty(
            doc.id, json.dumps([{"text": "auto"}])
        )
        assert promoted == 0
        chunks = await service.list_chunks(doc.id)
        assert [c.text for c in chunks] == ["manual"]

    async def test_skips_invalid_json(self, service, doc):
        promoted = await service.promote_from_analysis_if_empty(doc.id, "not-json")
        assert promoted == 0

    async def test_skips_deleted_chunks_from_analysis(self, service, doc):
        chunks_json = json.dumps(
            [
                {"text": "keep"},
                {"text": "drop", "deleted": True},
            ]
        )
        promoted = await service.promote_from_analysis_if_empty(doc.id, chunks_json)
        assert promoted == 1
        chunks = await service.list_chunks(doc.id)
        assert [c.text for c in chunks] == ["keep"]
