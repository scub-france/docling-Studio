"""The persisted and wire shapes of a chunk, and the chunkset hash, pinned.

Each shape is read back later by something that is not this code: the
`chunk_edits` journal (`before_json` / `after_json`), the payload handed to
`IngestionService.ingest`, the `document_versions.chunks_snapshot` a restore
reads, and the `chunks_json` an analysis wrote. They differ on purpose —
`self_ref` in the journal and `selfRef` elsewhere, `tokenCount` 0 for the
ingestion and null elsewhere — so every one is pinned byte for byte, through
the public path that writes or reads it.

The chunkset hash is written on `chunk_pushes` and `document_store_links`:
the golden values below were computed by the rule that shipped, and must not
move.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from domain.models import Chunk, Document, DocumentVersion, DocumentVersionKind, Store
from domain.value_objects import ChunkBbox, ChunkDocItem, StoreKind
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_edit_repo import SqliteChunkEditRepository, SqliteChunkPushRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.database import get_connection, init_db
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository
from persistence.store_repo import SqliteStoreRepository
from services.chunk_push_service import ChunkPushService
from services.chunk_service import ChunkService
from services.ingestion_service import IngestionResult
from services.version_service import VersionService

DOC = "doc-1"
T0 = datetime(2026, 5, 19, 10, 0, tzinfo=UTC)
T1 = datetime(2026, 5, 19, 10, 1, 2, 345678, tzinfo=UTC)
T2 = datetime(2026, 5, 19, 10, 2, tzinfo=UTC)


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    monkeypatch.setattr("persistence.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()
    await SqliteDocumentRepository().insert(
        Document(id=DOC, filename="a.pdf", storage_path="/tmp/a.pdf")
    )
    await SqliteStoreRepository().insert(
        Store(id="s-1", name="RH", slug="rh", kind=StoreKind.OPENSEARCH, embedder="bge-m3")
    )


@pytest.fixture
def chunks():
    return SqliteChunkRepository()


@pytest.fixture
def ingestion():
    ing = AsyncMock()
    ing.ingest.return_value = IngestionResult(doc_id=DOC, chunks_indexed=3, embedding_dimension=3)
    return ing


@pytest.fixture
def chunk_service(chunks):
    return ChunkService(
        chunk_repo=chunks,
        chunk_edit_repo=SqliteChunkEditRepository(),
        document_repo=SqliteDocumentRepository(),
        analysis_repo=SqliteAnalysisRepository(),
    )


@pytest.fixture
def push_service(chunks, ingestion):
    return ChunkPushService(
        chunk_repo=chunks,
        chunk_push_repo=SqliteChunkPushRepository(),
        document_repo=SqliteDocumentRepository(),
        ingestion_service=ingestion,
        store_repo=SqliteStoreRepository(),
        link_repo=SqliteDocumentStoreLinkRepository(),
    )


@pytest.fixture
def version_service(chunks):
    return VersionService(
        version_repo=SqliteDocumentVersionRepository(),
        chunk_repo=chunks,
        document_repo=SqliteDocumentRepository(),
    )


def _rich_chunks() -> list[Chunk]:
    """Every field set, a null token count, a non-ASCII text, a bare chunk."""
    return [
        Chunk(
            id="c-1",
            document_id=DOC,
            sequence=0,
            text="Intro paragraph.",
            headings=["Intro", "Scope"],
            source_page=2,
            bboxes=[
                ChunkBbox(page=2, bbox=[1.0, 2.5, 3.0, 4.0]),
                ChunkBbox(page=3, bbox=[0.0, 0.0, 10.0, 10.0]),
            ],
            doc_items=[
                ChunkDocItem(self_ref="#/texts/0", label="text"),
                ChunkDocItem(self_ref="#/tables/1", label="table"),
            ],
            token_count=None,
            created_at=T0,
            updated_at=T0,
        ),
        Chunk(
            id="c-2",
            document_id=DOC,
            sequence=1,
            text="Body — été ✓",
            source_page=None,
            token_count=7,
            created_at=T0,
            updated_at=T1,
        ),
        Chunk(id="c-3", document_id=DOC, sequence=2, text="", created_at=T0, updated_at=T2),
    ]


async def _edit_rows() -> list[dict]:
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT * FROM chunk_edits WHERE document_id = ? ORDER BY rowid", (DOC,)
        )
        return [dict(r) for r in await cursor.fetchall()]


# ---------------------------------------------------------------------------
# chunk_edits.before_json / after_json
# ---------------------------------------------------------------------------


def _audit(c: Chunk, **overrides) -> dict:
    shape = {
        "id": c.id,
        "sequence": c.sequence,
        "text": c.text,
        "headings": list(c.headings),
        "sourcePage": c.source_page,
        "tokenCount": c.token_count,
        "bboxes": [{"page": b.page, "bbox": list(b.bbox)} for b in c.bboxes],
        "docItems": [{"self_ref": d.self_ref, "label": d.label} for d in c.doc_items],
    }
    shape.update(overrides)
    return shape


class TestJournalSnapshot:
    async def test_update_writes_before_and_after_with_snake_case_doc_items(
        self, chunk_service, chunks
    ):
        rich = _rich_chunks()
        await chunks.insert_many(rich)

        await chunk_service.update_chunk(DOC, "c-1", text="Edited", headings=["New"])

        (row,) = await _edit_rows()
        assert row["before_json"] == json.dumps(_audit(rich[0]))
        assert row["after_json"] == json.dumps(_audit(rich[0], text="Edited", headings=["New"]))

    async def test_null_token_count_stays_null(self, chunk_service, chunks):
        await chunks.insert_many(_rich_chunks())
        await chunk_service.delete_chunk(DOC, "c-1")
        (row,) = await _edit_rows()
        assert json.loads(row["before_json"])["tokenCount"] is None
        assert row["after_json"] is None

    async def test_merge_and_split_rows_use_the_same_shape(self, chunk_service, chunks):
        rich = _rich_chunks()
        await chunks.insert_many(rich[:2])

        merged = await chunk_service.merge_chunks(DOC, ["c-1", "c-2"])
        head, _tail = await chunk_service.split_chunk(DOC, merged.id, cursor_offset=5)

        merge_row, split_row = await _edit_rows()
        assert merge_row["before_json"] is None
        assert merge_row["after_json"] == json.dumps(_audit(merged))
        assert split_row["after_json"] is None
        assert split_row["before_json"] == json.dumps(_audit(merged))
        assert head.doc_items == merged.doc_items


# ---------------------------------------------------------------------------
# IngestionService.ingest(chunks_json=...)
# ---------------------------------------------------------------------------


class TestIngestionPayload:
    async def test_camel_case_with_token_count_zero_when_unknown(
        self, push_service, chunks, ingestion
    ):
        await chunks.insert_many(_rich_chunks())

        await push_service.push_to_store(DOC, "rh")

        payload = ingestion.ingest.await_args.kwargs["chunks_json"]
        assert payload == json.dumps(
            [
                {
                    "text": "Intro paragraph.",
                    "headings": ["Intro", "Scope"],
                    "sourcePage": 2,
                    "tokenCount": 0,
                    "bboxes": [
                        {"page": 2, "bbox": [1.0, 2.5, 3.0, 4.0]},
                        {"page": 3, "bbox": [0.0, 0.0, 10.0, 10.0]},
                    ],
                    "docItems": [
                        {"selfRef": "#/texts/0", "label": "text"},
                        {"selfRef": "#/tables/1", "label": "table"},
                    ],
                },
                {
                    "text": "Body — été ✓",
                    "headings": [],
                    "sourcePage": None,
                    "tokenCount": 7,
                    "bboxes": [],
                    "docItems": [],
                },
                {
                    "text": "",
                    "headings": [],
                    "sourcePage": None,
                    "tokenCount": 0,
                    "bboxes": [],
                    "docItems": [],
                },
            ]
        )
        assert ingestion.ingest.await_args.kwargs["filename"] == "a.pdf"


# ---------------------------------------------------------------------------
# document_versions.chunks_snapshot — written, then read back by a restore
# ---------------------------------------------------------------------------


class TestVersionSnapshot:
    async def test_snapshot_is_camel_case_with_null_token_count(self, version_service, chunks):
        await chunks.insert_many(_rich_chunks())

        version = await version_service.record_on_rechunk(DOC, None)

        assert version.chunks_snapshot == json.dumps(
            [
                {
                    "id": "c-1",
                    "documentId": DOC,
                    "sequence": 0,
                    "text": "Intro paragraph.",
                    "headings": ["Intro", "Scope"],
                    "sourcePage": 2,
                    "tokenCount": None,
                    "bboxes": [
                        {"page": 2, "bbox": [1.0, 2.5, 3.0, 4.0]},
                        {"page": 3, "bbox": [0.0, 0.0, 10.0, 10.0]},
                    ],
                    "docItems": [
                        {"selfRef": "#/texts/0", "label": "text"},
                        {"selfRef": "#/tables/1", "label": "table"},
                    ],
                    "createdAt": "2026-05-19 10:00:00+00:00",
                    "updatedAt": "2026-05-19 10:00:00+00:00",
                },
                {
                    "id": "c-2",
                    "documentId": DOC,
                    "sequence": 1,
                    "text": "Body — été ✓",
                    "headings": [],
                    "sourcePage": None,
                    "tokenCount": 7,
                    "bboxes": [],
                    "docItems": [],
                    "createdAt": "2026-05-19 10:00:00+00:00",
                    "updatedAt": "2026-05-19 10:01:02.345678+00:00",
                },
                {
                    "id": "c-3",
                    "documentId": DOC,
                    "sequence": 2,
                    "text": "",
                    "headings": [],
                    "sourcePage": None,
                    "tokenCount": None,
                    "bboxes": [],
                    "docItems": [],
                    "createdAt": "2026-05-19 10:00:00+00:00",
                    "updatedAt": "2026-05-19 10:02:00+00:00",
                },
            ]
        )

    async def test_restore_reads_the_snapshot_back_under_fresh_ids(self, version_service, chunks):
        snapshot = [
            {
                "id": "old-1",
                "sequence": 4,
                "text": "kept",
                "headings": ["H"],
                "sourcePage": 3,
                "tokenCount": 9,
                "bboxes": [{"page": 3, "bbox": [1, 2, 3, 4]}],
                "docItems": [{"selfRef": "#/texts/2", "label": "text"}],
            },
            {"text": "bare"},
        ]
        await SqliteDocumentVersionRepository().insert(
            DocumentVersion(
                id="v-1",
                document_id=DOC,
                kind=DocumentVersionKind.CHUNKS,
                chunks_snapshot=json.dumps(snapshot),
                created_at=T0,
            )
        )

        await version_service.restore(DOC, "v-1")

        bare, kept = await chunks.find_for_document(DOC)  # ordered by sequence
        assert re.fullmatch(r"[0-9a-f]{32}", kept.id)
        assert (kept.sequence, kept.text, kept.headings, kept.source_page) == (
            4,
            "kept",
            ["H"],
            3,
        )
        assert kept.token_count == 9
        assert kept.bboxes == [ChunkBbox(page=3, bbox=[1, 2, 3, 4])]
        assert kept.doc_items == [ChunkDocItem(self_ref="#/texts/2", label="text")]
        assert (bare.sequence, bare.text, bare.headings, bare.source_page) == (0, "bare", [], None)
        assert (bare.token_count, bare.bboxes, bare.doc_items) == (None, [], [])


# ---------------------------------------------------------------------------
# analysis_jobs.chunks_json — read by the promotion
# ---------------------------------------------------------------------------


class TestAnalysisChunksRead:
    async def test_promotion_reads_camel_case_and_legacy_self_ref(self, chunk_service, chunks):
        chunks_json = json.dumps(
            [
                {
                    "text": "first",
                    "headings": ["H"],
                    "sourcePage": 1,
                    "tokenCount": 2,
                    "bboxes": [{"page": 1, "bbox": [0, 1, 2, 3]}],
                    "docItems": [
                        {"selfRef": "#/texts/0", "label": "text"},
                        {"self_ref": "#/texts/1", "label": "list_item"},
                        {"label": "picture"},
                    ],
                },
                {"text": "gone", "deleted": True},
                {"sequence": 99},
            ]
        )

        assert await chunk_service.promote_from_analysis_if_empty(DOC, chunks_json) == 2

        first, empty = await chunks.find_for_document(DOC)
        assert re.fullmatch(r"[0-9a-f-]{36}", first.id)
        assert (first.sequence, first.text, first.headings, first.source_page) == (
            0,
            "first",
            ["H"],
            1,
        )
        assert first.token_count == 2
        assert first.bboxes == [ChunkBbox(page=1, bbox=[0, 1, 2, 3])]
        assert first.doc_items == [
            ChunkDocItem(self_ref="#/texts/0", label="text"),
            ChunkDocItem(self_ref="#/texts/1", label="list_item"),
            ChunkDocItem(self_ref="", label="picture"),
        ]
        # The sequence is the position in the analysis list, deleted entries
        # included — the `sequence` key of the entry is not read.
        assert (empty.sequence, empty.text, empty.token_count) == (2, "", None)
        rows = await _edit_rows()
        assert [r["actor"] for r in rows] == ["system:initial-analysis"] * 2
        assert rows[0]["after_json"] == json.dumps(_audit(first))


# ---------------------------------------------------------------------------
# chunk_pushes.chunkset_hash / document_store_links.chunkset_hash
# ---------------------------------------------------------------------------


def _reference_hash(chunks: list[Chunk]) -> str:
    """The rule that shipped: id, text and `str(updated_at)` per chunk."""
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.id.encode())
        h.update(b"\x00")
        h.update(c.text.encode())
        h.update(b"\x00")
        h.update(str(c.updated_at).encode())
        h.update(b"\x01")
    return h.hexdigest()


class TestChunksetHash:
    # Computed once with `services.chunk_service._compute_chunkset_hash`, the
    # function that wrote every hash stored before it moved to domain/hashing.
    GOLDEN_THREE = "fee1efd47fb90ba0d763258ae55b566f80c039af08999961bf0e7cbb065decb2"
    GOLDEN_ONE = "3e6e2c8d4c62cae8b2486e0678cc78230c752d62a528acc7816a2c4fe9813bfa"

    async def test_push_records_the_shipped_hash_on_push_and_link(self, push_service, chunks):
        await chunks.insert_many(_rich_chunks())

        await push_service.push_to_store(DOC, "rh")

        push = await SqliteChunkPushRepository().find_latest(DOC, "s-1")
        link = await SqliteDocumentStoreLinkRepository().find_one(DOC, "s-1")
        assert push.chunkset_hash == self.GOLDEN_THREE
        assert link.chunkset_hash == self.GOLDEN_THREE
        assert _reference_hash(_rich_chunks()) == self.GOLDEN_THREE

    async def test_one_chunk(self, push_service, chunks):
        await chunks.insert_many(_rich_chunks()[:1])
        await push_service.push_to_store(DOC, "rh")
        push = await SqliteChunkPushRepository().find_latest(DOC, "s-1")
        assert push.chunkset_hash == self.GOLDEN_ONE
