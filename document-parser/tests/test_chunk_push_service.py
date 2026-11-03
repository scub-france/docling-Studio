"""Tests for ChunkPushService — diff, push and push history (#256, #283).

Moved out of `test_chunk_service.py` with the push code itself (audit 0.7.4,
03 MAJ 3.3.2). The assertions are the ones `ChunkService` answered; only the
construction changed, and chunks are seeded through `ChunkService.add_chunk`
as before.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from domain.models import Chunk, Document, Store
from domain.value_objects import DocumentStoreLinkState, StoreKind
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_edit_repo import SqliteChunkEditRepository, SqliteChunkPushRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.store_repo import SqliteStoreRepository
from services.chunk_errors import ChunkServiceError
from services.chunk_push_service import ChunkPushService
from services.chunk_service import ChunkService
from services.ingestion_service import IngestionResult
from services.navigation_errors import DocumentNotFoundError


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    monkeypatch.setattr("persistence.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()


@pytest.fixture
async def doc():
    document = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
    await SqliteDocumentRepository().insert(document)
    return document


@pytest.fixture
def repos():
    return {
        "chunks": SqliteChunkRepository(),
        "pushes": SqliteChunkPushRepository(),
        "documents": SqliteDocumentRepository(),
    }


@pytest.fixture
def service(repos):
    return ChunkPushService(
        chunk_repo=repos["chunks"],
        chunk_push_repo=repos["pushes"],
        document_repo=repos["documents"],
    )


async def _add_chunk(document_id: str, text: str) -> Chunk:
    """Seed a chunk the way the editor does."""
    editor = ChunkService(
        chunk_repo=SqliteChunkRepository(),
        chunk_edit_repo=SqliteChunkEditRepository(),
        document_repo=SqliteDocumentRepository(),
        analysis_repo=SqliteAnalysisRepository(),
    )
    return await editor.add_chunk(document_id, text=text)


# ---------------------------------------------------------------------------
# diff_against_store
# ---------------------------------------------------------------------------


class TestDiff:
    async def test_no_push_history_returns_all_added(self, service, doc):
        c1 = await _add_chunk(doc.id, "a")
        c2 = await _add_chunk(doc.id, "b")
        diffs = await service.diff_against_store(doc.id, "store-1")
        statuses = {d["chunkId"]: d["status"] for d in diffs}
        assert statuses == {c1.id: "added", c2.id: "added"}

    async def test_against_the_last_push(self, service, repos, doc):
        """Added / modified / unchanged / removed, in canonical order then
        the removed ids, all without a text diff."""
        from domain.models import ChunkPush

        await SqliteStoreRepository().insert(
            Store(id="s-1", name="S", slug="s", kind=StoreKind.OPENSEARCH, embedder="e")
        )
        pushed_at = datetime(2026, 5, 19, 10, 0, tzinfo=UTC)
        same = Chunk(document_id=doc.id, sequence=0, text="same", updated_at=pushed_at)
        edited = Chunk(
            document_id=doc.id,
            sequence=1,
            text="edited",
            updated_at=datetime(2026, 5, 19, 10, 5, tzinfo=UTC),
        )
        fresh = Chunk(document_id=doc.id, sequence=2, text="fresh")
        await repos["chunks"].insert_many([same, edited, fresh])
        await repos["pushes"].insert(
            ChunkPush(
                id="p-1",
                document_id=doc.id,
                store_id="s-1",
                chunkset_hash="h",
                chunk_ids=[same.id, edited.id, "gone"],
                pushed_at=pushed_at,
            )
        )

        diffs = await service.diff_against_store(doc.id, "s-1")

        assert diffs == [
            {"chunkId": same.id, "status": "unchanged", "textDiff": None},
            {"chunkId": edited.id, "status": "modified", "textDiff": None},
            {"chunkId": fresh.id, "status": "added", "textDiff": None},
            {"chunkId": "gone", "status": "removed", "textDiff": None},
        ]

    async def test_unknown_document_is_the_shared_404(self, service):
        with pytest.raises(DocumentNotFoundError):
            await service.diff_against_store("ghost", "s-1")


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
        return ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=mock_ingestion,
            store_repo=store_repo,
            link_repo=link_repo,
        )

    async def test_resolves_slug_to_store_id_before_recording_push(
        self, service_with_store, repos, doc, mock_ingestion
    ):
        await _add_chunk(doc.id, "hello")
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
        await _add_chunk(doc.id, "hello")
        await service_with_store.push_to_store(doc.id, "store-uuid-1")
        latest = await repos["pushes"].find_latest(doc.id, "store-uuid-1")
        assert latest is not None
        assert latest.store_id == "store-uuid-1"

    async def test_unknown_store_raises_404(self, service_with_store, doc):
        await _add_chunk(doc.id, "hello")
        with pytest.raises(ChunkServiceError) as excinfo:
            await service_with_store.push_to_store(doc.id, "nope-not-a-store")
        assert excinfo.value.http_status == 404
        assert "nope-not-a-store" in str(excinfo.value)

    async def test_no_ingestion_service_raises_503(self, repos, store_repo, doc):
        # Service constructed without an IngestionService (#199 — backend
        # has neither OpenSearch nor Neo4j configured) must surface a
        # 503, not a generic 500.
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
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
        await _add_chunk(doc.id, "hello")
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
        await _add_chunk(doc.id, "first")
        await service_with_store.push_to_store(doc.id, "rh-corpus-v3")
        first = await link_repo.find_one(doc.id, "store-uuid-1")

        # Edit the chunkset so the hash changes.
        await _add_chunk(doc.id, "second")
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
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=failing,
            store_repo=store_repo,
            link_repo=link_repo,
        )
        await _add_chunk(doc.id, "hello")

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

        resolved = IngestionTargets(vector_store="vs-sentinel", graph_writer=None)
        resolver = AsyncMock()
        resolver.resolve = AsyncMock(return_value=resolved)
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=mock_ingestion,
            store_repo=store_repo,
            link_repo=link_repo,
            backend_resolver=resolver,
        )
        await _add_chunk(doc.id, "hello")
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
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=mock_ingestion,
            store_repo=store_repo,
            link_repo=link_repo,
            backend_resolver=resolver,
        )
        await _add_chunk(doc.id, "hello")

        with pytest.raises(ChunkServiceError) as excinfo:
            await service.push_to_store(doc.id, "rh-corpus-v3")
        assert excinfo.value.http_status == 503

        # The Ingestion call should never happen if resolution fails.
        mock_ingestion.ingest.assert_not_awaited()

        link = await link_repo.find_one(doc.id, "store-uuid-1")
        assert link is not None
        assert link.state == DocumentStoreLinkState.FAILED

    async def test_push_result_and_record(self, service_with_store, repos, link_repo, doc):
        """The summary counts what the ingestion indexed and the known tokens;
        the push row lists the canonical ids in order, and the link points at
        that row with the same hash and date."""
        a = Chunk(document_id=doc.id, sequence=0, text="a", token_count=5)
        b = Chunk(document_id=doc.id, sequence=1, text="b")
        await repos["chunks"].insert_many([a, b])

        result = await service_with_store.push_to_store(doc.id, "rh-corpus-v3")

        push = await repos["pushes"].find_latest(doc.id, "store-uuid-1")
        assert result == {"pushId": push.id, "summary": {"embeds": 2, "tokens": 5}}
        assert push.chunk_ids == [a.id, b.id]
        link = await link_repo.find_one(doc.id, "store-uuid-1")
        assert (link.last_run_id, link.chunkset_hash, link.last_push_at) == (
            push.id,
            push.chunkset_hash,
            push.pushed_at,
        )

    async def test_without_a_store_repo_the_value_is_used_as_the_store_id(
        self, repos, store_repo, doc, mock_ingestion
    ):
        """Legacy wiring: no store repo, no link repo — the value the caller
        passed is recorded verbatim, and no link is written."""
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=mock_ingestion,
        )
        await _add_chunk(doc.id, "hello")

        await service.push_to_store(doc.id, "store-uuid-1")

        assert (await repos["pushes"].find_latest(doc.id, "store-uuid-1")) is not None
        assert mock_ingestion.ingest.await_args.kwargs["targets"] is None
        assert await SqliteDocumentStoreLinkRepository().find_one(doc.id, "store-uuid-1") is None

    async def test_without_a_store_repo_the_resolver_is_not_asked(
        self, repos, store_repo, doc, mock_ingestion
    ):
        """No store row, no per-store backends: the ingestion's defaults are
        used. The single-block push read an unbound local here and failed."""
        resolver = AsyncMock()
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=mock_ingestion,
            backend_resolver=resolver,
        )
        await _add_chunk(doc.id, "hello")

        await service.push_to_store(doc.id, "store-uuid-1")

        resolver.resolve.assert_not_awaited()
        assert mock_ingestion.ingest.await_args.kwargs["targets"] is None
        assert (await repos["pushes"].find_latest(doc.id, "store-uuid-1")) is not None

    async def test_a_failing_link_write_never_hides_the_push_error(self, repos, store_repo, doc):
        """Recording Failed on the link is best effort: if that write fails
        too, the ingestion's own error is what the caller sees."""
        failing = AsyncMock()
        failing.ingest.side_effect = RuntimeError("opensearch unreachable")
        broken_links = AsyncMock()
        broken_links.find_one.side_effect = RuntimeError("database is locked")
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=failing,
            store_repo=store_repo,
            link_repo=broken_links,
        )
        await _add_chunk(doc.id, "hello")

        with pytest.raises(RuntimeError, match="opensearch unreachable"):
            await service.push_to_store(doc.id, "rh-corpus-v3")
        assert await repos["pushes"].find_latest(doc.id, "store-uuid-1") is None

    async def test_a_long_failure_message_is_cut_on_the_link(
        self, repos, store_repo, link_repo, doc
    ):
        failing = AsyncMock()
        failing.ingest.side_effect = RuntimeError("x" * 900)
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=failing,
            store_repo=store_repo,
            link_repo=link_repo,
        )
        await _add_chunk(doc.id, "hello")
        with pytest.raises(RuntimeError):
            await service.push_to_store(doc.id, "rh-corpus-v3")
        link = await link_repo.find_one(doc.id, "store-uuid-1")
        assert link.error_message == "x" * 500


class TestListPushes:
    """Coverage for the push-history feed (#283).

    Three properties to pin:
      - Newest-first order (the UI bets on this).
      - Pagination envelope shape (items / total / limit / offset).
      - The store fields are joined from the store_repo and survive
        the store being deleted later (audit log is immutable).
    """

    @pytest.fixture
    async def store_repo(self):
        repo = SqliteStoreRepository()
        await repo.insert(
            Store(
                id="s-rh",
                name="RH Corpus",
                slug="rh-corpus",
                kind=StoreKind.OPENSEARCH,
                embedder="bge-m3",
            )
        )
        return repo

    @pytest.fixture
    def service_with_pushes(self, repos, store_repo, doc):
        return ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            ingestion_service=None,
            store_repo=store_repo,
        )

    async def _seed_pushes(self, repos, *, doc_id, store_id, count, base_minute=0):
        from domain.models import ChunkPush

        for i in range(count):
            await repos["pushes"].insert(
                ChunkPush(
                    id=f"push-{i}",
                    document_id=doc_id,
                    store_id=store_id,
                    chunkset_hash=f"hash-{i}",
                    chunk_ids=[f"c-{j}" for j in range(i + 1)],
                    pushed_at=datetime(2026, 5, 19, 10, base_minute + i, tzinfo=UTC),
                )
            )

    async def test_empty_history(self, service_with_pushes, doc):
        result = await service_with_pushes.list_pushes(doc.id)
        assert result == {"items": [], "total": 0, "limit": 50, "offset": 0}

    async def test_returns_newest_first(self, service_with_pushes, repos, doc):
        await self._seed_pushes(repos, doc_id=doc.id, store_id="s-rh", count=3)
        result = await service_with_pushes.list_pushes(doc.id)
        assert result["total"] == 3
        # Reversed order: the highest minute lands first.
        ids = [item["id"] for item in result["items"]]
        assert ids == ["push-2", "push-1", "push-0"]

    async def test_joins_store_name_and_kind(self, service_with_pushes, repos, doc):
        await self._seed_pushes(repos, doc_id=doc.id, store_id="s-rh", count=1)
        result = await service_with_pushes.list_pushes(doc.id)
        entry = result["items"][0]
        assert entry["storeSlug"] == "rh-corpus"
        assert entry["storeName"] == "RH Corpus"
        assert entry["storeKind"] == "opensearch"
        assert entry["chunkCount"] == 1  # i=0 → one chunk_id

    # Note: a "store deleted after the push" case can't exist with the
    # current schema — `chunk_pushes.store_id` is a FK with ON DELETE
    # CASCADE, so deleting the store wipes its push history. The
    # service's defensive None handling
    # (`storeSlug`/`storeName`/`storeKind` may be None) is kept
    # because a future schema change to ON DELETE SET NULL would
    # rehabilitate the audit log as a survivor of store deletion —
    # see follow-up notes in #283 / the audit-trail thread.

    async def test_pagination_limit_and_offset(self, service_with_pushes, repos, doc):
        await self._seed_pushes(repos, doc_id=doc.id, store_id="s-rh", count=5)
        page_1 = await service_with_pushes.list_pushes(doc.id, limit=2, offset=0)
        page_2 = await service_with_pushes.list_pushes(doc.id, limit=2, offset=2)
        assert [item["id"] for item in page_1["items"]] == ["push-4", "push-3"]
        assert [item["id"] for item in page_2["items"]] == ["push-2", "push-1"]
        assert page_2["total"] == 5
        assert page_2["limit"] == 2
        assert page_2["offset"] == 2

    async def test_unknown_document_raises_404(self, service_with_pushes):
        with pytest.raises(DocumentNotFoundError):
            await service_with_pushes.list_pushes("ghost-doc")

    async def test_without_a_store_repo_the_store_fields_are_none(self, repos, store_repo, doc):
        await self._seed_pushes(repos, doc_id=doc.id, store_id="s-rh", count=1)
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
        )
        (entry,) = (await service.list_pushes(doc.id))["items"]
        assert entry == {
            "id": "push-0",
            "documentId": doc.id,
            "storeId": "s-rh",
            "storeSlug": None,
            "storeName": None,
            "storeKind": None,
            "chunksetHash": "hash-0",
            "chunkCount": 1,
            "pushedAt": "2026-05-19T10:00:00+00:00",
        }

    async def test_each_store_is_read_once(self, repos, store_repo, doc):
        from domain.models import ChunkPush

        await store_repo.insert(
            Store(id="s-2", name="Other", slug="other", kind=StoreKind.NEO4J, embedder="e")
        )
        for i, store_id in enumerate(["s-rh", "s-2", "s-rh"]):
            await repos["pushes"].insert(
                ChunkPush(
                    id=f"p-{i}",
                    document_id=doc.id,
                    store_id=store_id,
                    chunkset_hash="h",
                    chunk_ids=[],
                    pushed_at=datetime(2026, 5, 19, 10, i, tzinfo=UTC),
                )
            )
        spy = AsyncMock(side_effect=store_repo.find_by_id)
        store_repo.find_by_id = spy
        service = ChunkPushService(
            chunk_repo=repos["chunks"],
            chunk_push_repo=repos["pushes"],
            document_repo=repos["documents"],
            store_repo=store_repo,
        )

        result = await service.list_pushes(doc.id)

        assert [(e["id"], e["storeSlug"], e["storeKind"]) for e in result["items"]] == [
            ("p-2", "rh-corpus", "opensearch"),
            ("p-1", "other", "neo4j"),
            ("p-0", "rh-corpus", "opensearch"),
        ]
        assert [c.args for c in spy.await_args_list] == [("s-rh",), ("s-2",)]
