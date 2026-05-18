"""Tests for ChunkService — canonical chunk lifecycle (#256)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.models import AnalysisJob, AnalysisStatus, Chunk, Document, Store
from domain.value_objects import (
    ChunkDocItem,
    ChunkEditAction,
    ChunkResult,
    DocumentStoreLinkState,
    StoreKind,
)
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_edit_repo import (
    SqliteChunkEditRepository,
    SqliteChunkPushRepository,
)
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.store_repo import SqliteStoreRepository
from services.chunk_service import (
    ChunkConflictError,
    ChunkNotFoundError,
    ChunkService,
    ChunkServiceError,
    ChunkValidationError,
    DocumentNotFoundError,
)
from services.ingestion_service import IngestionResult

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
        "pushes": SqliteChunkPushRepository(),
        "documents": SqliteDocumentRepository(),
        "analyses": SqliteAnalysisRepository(),
    }


@pytest.fixture
def service(repos):
    return ChunkService(
        chunk_repo=repos["chunks"],
        chunk_edit_repo=repos["edits"],
        chunk_push_repo=repos["pushes"],
        document_repo=repos["documents"],
        analysis_repo=repos["analyses"],
        chunker=None,
        ingestion_service=None,
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


# ---------------------------------------------------------------------------
# diff_against_store
# ---------------------------------------------------------------------------


class TestDiff:
    async def test_no_push_history_returns_all_added(self, service, doc):
        c1 = await service.add_chunk(doc.id, text="a")
        c2 = await service.add_chunk(doc.id, text="b")
        diffs = await service.diff_against_store(doc.id, "store-1")
        statuses = {d["chunkId"]: d["status"] for d in diffs}
        assert statuses == {c1.id: "added", c2.id: "added"}


# ---------------------------------------------------------------------------
# get_tree
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# push_to_store (slug → id resolution, 503/404/409 surfaces)
# ---------------------------------------------------------------------------


class TestPushToStore:
    """Covers the #225 fix: the API sends a store **slug**, but
    `chunk_pushes.store_id` is a FK to `stores.id`. The service must
    resolve the slug before inserting the audit row — otherwise the
    insert 500s with an opaque `IntegrityError: FOREIGN KEY constraint
    failed`.

    Also covers the #199-related 503 surface (no IngestionService
    wired) and the 409 surface (no chunks to push).
    """

    @pytest.fixture
    async def store_repo(self):
        repo = SqliteStoreRepository()
        store = Store(
            id="store-uuid-1",
            name="RH Corpus",
            slug="rh-corpus-v3",
            kind=StoreKind.OPENSEARCH,
            embedder="bge-m3",
        )
        await repo.insert(store)
        return repo

    @pytest.fixture
    def mock_ingestion(self):
        ing = AsyncMock()
        ing.ingest.return_value = IngestionResult(
            doc_id="doc-1", chunks_indexed=2, embedding_dimension=3
        )
        return ing

    @pytest.fixture
    def link_repo(self):
        return SqliteDocumentStoreLinkRepository()

    @pytest.fixture
    def service_with_store(self, repos, store_repo, link_repo, mock_ingestion):
        return ChunkService(
            chunk_repo=repos["chunks"],
            chunk_edit_repo=repos["edits"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            analysis_repo=repos["analyses"],
            chunker=None,
            ingestion_service=mock_ingestion,
            store_repo=store_repo,
            link_repo=link_repo,
        )

    async def test_resolves_slug_to_store_id_before_recording_push(
        self, service_with_store, repos, doc, mock_ingestion
    ):
        await service_with_store.add_chunk(doc.id, text="hello")
        result = await service_with_store.push_to_store(doc.id, "rh-corpus-v3")
        assert result["summary"]["embeds"] == 2
        # The audit row must carry the resolved UUID, not the slug —
        # otherwise the FK insert into `chunk_pushes` fails with a
        # generic IntegrityError 500.
        latest = await repos["pushes"].find_latest(doc.id, "store-uuid-1")
        assert latest is not None
        assert latest.store_id == "store-uuid-1"
        # And NOT keyed by slug.
        by_slug = await repos["pushes"].find_latest(doc.id, "rh-corpus-v3")
        assert by_slug is None
        mock_ingestion.ingest.assert_awaited_once()

    async def test_also_accepts_an_explicit_store_id(self, service_with_store, repos, doc):
        """Backwards compat: older callers pass the id directly. The
        service must accept that too (try slug first, fall back to id).
        """
        await service_with_store.add_chunk(doc.id, text="hello")
        await service_with_store.push_to_store(doc.id, "store-uuid-1")
        latest = await repos["pushes"].find_latest(doc.id, "store-uuid-1")
        assert latest is not None
        assert latest.store_id == "store-uuid-1"

    async def test_unknown_store_raises_404(self, service_with_store, doc):
        await service_with_store.add_chunk(doc.id, text="hello")
        with pytest.raises(ChunkServiceError) as excinfo:
            await service_with_store.push_to_store(doc.id, "nope-not-a-store")
        assert excinfo.value.http_status == 404
        assert "nope-not-a-store" in str(excinfo.value)

    async def test_no_ingestion_service_raises_503(self, repos, store_repo, doc):
        # Service constructed without an IngestionService (#199 — backend
        # has neither OpenSearch nor Neo4j configured) must surface a
        # 503, not a generic 500.
        service = ChunkService(
            chunk_repo=repos["chunks"],
            chunk_edit_repo=repos["edits"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            analysis_repo=repos["analyses"],
            chunker=None,
            ingestion_service=None,
            store_repo=store_repo,
        )
        with pytest.raises(ChunkServiceError) as excinfo:
            await service.push_to_store(doc.id, "rh-corpus-v3")
        assert excinfo.value.http_status == 503
        # The error message must be actionable — it's what the user
        # sees in the toast when push fails.
        assert "EMBEDDING_URL" in str(excinfo.value)
        assert "NEO4J_URI" in str(excinfo.value)

    async def test_empty_canonical_raises_409(self, service_with_store, doc):
        with pytest.raises(ChunkServiceError) as excinfo:
            await service_with_store.push_to_store(doc.id, "rh-corpus-v3")
        assert excinfo.value.http_status == 409

    async def test_unknown_document_raises_404_before_store_resolution(self, service_with_store):
        with pytest.raises(DocumentNotFoundError):
            await service_with_store.push_to_store("ghost-doc", "rh-corpus-v3")

    async def test_upserts_document_store_link_on_success(self, service_with_store, link_repo, doc):
        """The push must populate `document_store_links` — that's the
        table the UI reads from for the per-store state badge. Without
        the upsert, the row stays NotPushed forever even though the
        audit log (`chunk_pushes`) shows the push happened.

        Regression for the bug observed locally ("j'ai pas de mise à
        jour du statut une fois poussé"): the audit log was being
        written but the live link wasn't.
        """
        await service_with_store.add_chunk(doc.id, text="hello")
        await service_with_store.push_to_store(doc.id, "rh-corpus-v3")

        link = await link_repo.find_one(doc.id, "store-uuid-1")
        assert link is not None
        assert link.state == DocumentStoreLinkState.INGESTED
        assert link.chunkset_hash is not None
        assert link.last_push_at is not None
        assert link.error_message is None
        # last_run_id should point at the ChunkPush row so the UI can
        # cross-reference back to the audit log.
        assert link.last_run_id is not None

    async def test_second_push_updates_the_same_link_row(self, service_with_store, link_repo, doc):
        """Re-pushing the same (doc, store) pair must update the
        existing link, not create a duplicate. The chunkset hash on
        the link must reflect the *latest* push.
        """
        await service_with_store.add_chunk(doc.id, text="first")
        await service_with_store.push_to_store(doc.id, "rh-corpus-v3")
        first = await link_repo.find_one(doc.id, "store-uuid-1")

        # Edit the chunkset so the hash changes.
        await service_with_store.add_chunk(doc.id, text="second")
        await service_with_store.push_to_store(doc.id, "rh-corpus-v3")
        second = await link_repo.find_one(doc.id, "store-uuid-1")

        assert second is not None
        assert second.id == first.id  # same row, upsert path
        assert second.chunkset_hash != first.chunkset_hash
        assert second.state == DocumentStoreLinkState.INGESTED

    async def test_marks_link_failed_when_ingestion_raises(self, repos, store_repo, link_repo, doc):
        """If the ingestion step fails (OpenSearch/Neo4j down), the
        link must transition to Failed with the error message
        attached — otherwise the UI shows nothing changed and the
        user re-clicks blindly.
        """
        failing = AsyncMock()
        failing.ingest.side_effect = RuntimeError("opensearch unreachable")
        service = ChunkService(
            chunk_repo=repos["chunks"],
            chunk_edit_repo=repos["edits"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            analysis_repo=repos["analyses"],
            chunker=None,
            ingestion_service=failing,
            store_repo=store_repo,
            link_repo=link_repo,
        )
        await service.add_chunk(doc.id, text="hello")

        with pytest.raises(RuntimeError, match="opensearch unreachable"):
            await service.push_to_store(doc.id, "rh-corpus-v3")

        link = await link_repo.find_one(doc.id, "store-uuid-1")
        assert link is not None
        assert link.state == DocumentStoreLinkState.FAILED
        assert link.error_message == "opensearch unreachable"

    async def test_calls_backend_resolver_and_forwards_targets(
        self, repos, store_repo, link_repo, doc, mock_ingestion
    ):
        """When a backend resolver is wired (#279), push_to_store
        resolves the per-store backends and forwards them as the
        `targets` kwarg of the ingest call. The resolver is what gives
        each store its own Neo4j/OpenSearch destination.
        """
        from services.store_backend_resolver import IngestionTargets

        resolved = IngestionTargets(vector_store="vs-sentinel", neo4j_driver=None)
        resolver = AsyncMock()
        resolver.resolve = AsyncMock(return_value=resolved)
        service = ChunkService(
            chunk_repo=repos["chunks"],
            chunk_edit_repo=repos["edits"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            analysis_repo=repos["analyses"],
            chunker=None,
            ingestion_service=mock_ingestion,
            store_repo=store_repo,
            link_repo=link_repo,
            backend_resolver=resolver,
        )
        await service.add_chunk(doc.id, text="hello")
        await service.push_to_store(doc.id, "rh-corpus-v3")

        resolver.resolve.assert_awaited_once()
        # The Store passed to resolve is the row from the repo —
        # ensures the per-store identity reaches the resolver.
        resolved_store = resolver.resolve.await_args.args[0]
        assert resolved_store.slug == "rh-corpus-v3"
        # ingest received the resolver's IngestionTargets, not None.
        ingest_call = mock_ingestion.ingest.await_args
        assert ingest_call.kwargs["targets"] is resolved

    async def test_resolver_failure_raises_503_and_marks_link_failed(
        self, repos, store_repo, link_repo, doc, mock_ingestion
    ):
        """If the resolver cannot map a Store to a backend (e.g. store
        has no connection_uri and no env fallback), surface a 503 — not
        a generic 500 — and record Failed on the link so the UI can
        communicate.
        """
        from services.store_backend_resolver import StoreBackendNotConfiguredError

        resolver = AsyncMock()
        resolver.resolve = AsyncMock(side_effect=StoreBackendNotConfiguredError("no NEO4J_URI"))
        service = ChunkService(
            chunk_repo=repos["chunks"],
            chunk_edit_repo=repos["edits"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            analysis_repo=repos["analyses"],
            chunker=None,
            ingestion_service=mock_ingestion,
            store_repo=store_repo,
            link_repo=link_repo,
            backend_resolver=resolver,
        )
        await service.add_chunk(doc.id, text="hello")

        with pytest.raises(ChunkServiceError) as excinfo:
            await service.push_to_store(doc.id, "rh-corpus-v3")
        assert excinfo.value.http_status == 503

        # The Ingestion call should never happen if resolution fails.
        mock_ingestion.ingest.assert_not_awaited()

        link = await link_repo.find_one(doc.id, "store-uuid-1")
        assert link is not None
        assert link.state == DocumentStoreLinkState.FAILED


class TestGetTree:
    async def test_tree_empty_when_no_analysis(self, service, doc):
        assert await service.get_tree(doc.id) == []

    async def test_tree_groups_by_label(self, service, repos, doc):
        job = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        await repos["analyses"].insert(job)
        job.document_json = json.dumps(
            {
                "texts": [
                    {"self_ref": "#/texts/0", "label": "title", "text": "Hi"},
                    {"self_ref": "#/texts/1", "label": "text", "text": "Body"},
                ],
                "tables": [],
                "pictures": [],
            }
        )
        job.completed_at = datetime.now(UTC)
        await repos["analyses"].update_status(job)
        tree = await service.get_tree(doc.id)
        labels = {n["type"] for n in tree}
        assert labels == {"group"}
        # Both Titles and Paragraphs groups should be present
        group_titles = {n["label"] for n in tree}
        assert "Titles" in group_titles
        assert "Paragraphs" in group_titles
