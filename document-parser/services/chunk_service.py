"""Chunk service — canonical chunk lifecycle for a document (#256).

Sits between the API layer and the chunk / chunk_edit / chunk_push
repositories. Owns the invariants of the canonical chunkset:

- ordering by `sequence` (dense ascending, gaps allowed after split)
- soft-delete (audit log keeps before/after pointers valid)
- atomic mutation + audit row (one ChunkEdit per mutation)
- promotion from the first completed analysis (idempotent)

Re-uses `DocumentChunker` for rechunk (same port that
`AnalysisService.rechunk` uses), so chunking strategy logic is not
duplicated.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.models import Chunk, ChunkEdit, ChunkPush
from domain.value_objects import (
    ChunkBbox,
    ChunkDocItem,
    ChunkEditAction,
    ChunkingOptions,
)

if TYPE_CHECKING:
    from domain.ports import (
        AnalysisRepository,
        ChunkEditRepository,
        ChunkPushRepository,
        ChunkRepository,
        DocumentChunker,
        DocumentRepository,
    )
    from services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors — carry an http_status hint, mirrors store_service.py convention.
# ---------------------------------------------------------------------------


class ChunkServiceError(Exception):
    http_status: int = 400

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class ChunkNotFoundError(ChunkServiceError):
    http_status = 404


class DocumentNotFoundError(ChunkServiceError):
    http_status = 404


class ChunkConflictError(ChunkServiceError):
    http_status = 409


class ChunkValidationError(ChunkServiceError):
    http_status = 400


# ---------------------------------------------------------------------------
# Helpers — chunk ↔ dict conversions for audit log + analysis chunks_json.
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


def _chunk_to_audit_dict(c: Chunk) -> dict:
    """Serializable snapshot for ChunkEdit.before / .after."""
    return {
        "id": c.id,
        "sequence": c.sequence,
        "text": c.text,
        "headings": list(c.headings),
        "sourcePage": c.source_page,
        "tokenCount": c.token_count,
        "bboxes": [asdict(b) for b in c.bboxes],
        "docItems": [asdict(d) for d in c.doc_items],
    }


def _bbox_from_dict(d: dict) -> ChunkBbox:
    return ChunkBbox(page=d["page"], bbox=list(d["bbox"]))


def _doc_item_from_dict(d: dict) -> ChunkDocItem:
    return ChunkDocItem(
        self_ref=d.get("selfRef") or d.get("self_ref", ""), label=d.get("label", "")
    )


def _analysis_chunk_to_canonical(
    document_id: str,
    sequence: int,
    raw: dict,
) -> Chunk:
    """Convert an entry from `AnalysisJob.chunks_json` (camelCase) into a
    canonical `Chunk`. Used by `_promote_from_analysis`."""
    return Chunk(
        document_id=document_id,
        sequence=sequence,
        text=raw.get("text", ""),
        headings=list(raw.get("headings", [])),
        source_page=raw.get("sourcePage"),
        bboxes=[_bbox_from_dict(b) for b in raw.get("bboxes", [])],
        doc_items=[_doc_item_from_dict(d) for d in raw.get("docItems", [])],
        token_count=raw.get("tokenCount"),
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ChunkService:
    """Orchestrates canonical chunk operations for a document."""

    def __init__(
        self,
        chunk_repo: ChunkRepository,
        chunk_edit_repo: ChunkEditRepository,
        chunk_push_repo: ChunkPushRepository,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        chunker: DocumentChunker | None = None,
        ingestion_service: IngestionService | None = None,
        actor: str = "user",
    ) -> None:
        self._chunks = chunk_repo
        self._edits = chunk_edit_repo
        self._pushes = chunk_push_repo
        self._documents = document_repo
        self._analyses = analysis_repo
        self._chunker = chunker
        self._ingestion = ingestion_service
        self._actor = actor
        # Duck-typed recorder for document versions (#267). Wired in
        # main.py to `VersionService.record_on_rechunk` so each
        # `+ Generate chunks` call appends a frozen pair to History.
        self._version_recorder = None

    def set_version_recorder(self, version_service) -> None:
        """Inject the document-version recorder (#267). Contract: a
        coroutine `(document_id: str, analysis_id: str | None) -> DocumentVersion`."""
        self._version_recorder = version_service

    # -- promotion (called by AnalysisService after first successful analysis)

    async def promote_from_analysis_if_empty(self, document_id: str, chunks_json: str) -> int:
        """Populate the canonical chunkset from an analysis result, ONLY if
        the document has no canonical chunks yet. Idempotent.

        Returns the number of chunks promoted (0 if skipped).
        """
        if await self._chunks.count_for_document(document_id) > 0:
            return 0
        try:
            raw_chunks = json.loads(chunks_json)
        except json.JSONDecodeError:
            logger.exception("Invalid chunks_json for doc %s — skipping promotion", document_id)
            return 0
        if not isinstance(raw_chunks, list) or not raw_chunks:
            return 0

        canonical = [
            _analysis_chunk_to_canonical(document_id, seq, raw)
            for seq, raw in enumerate(raw_chunks)
            if not raw.get("deleted")
        ]
        if not canonical:
            return 0

        await self._chunks.insert_many(canonical)
        for c in canonical:
            await self._edits.insert(
                ChunkEdit(
                    id=_new_id(),
                    document_id=document_id,
                    chunk_id=c.id,
                    action=ChunkEditAction.INSERT,
                    actor="system:initial-analysis",
                    at=_utcnow(),
                    after=_chunk_to_audit_dict(c),
                )
            )
        logger.info(
            "chunk.promote docId=%s count=%d (initial-analysis)", document_id, len(canonical)
        )
        return len(canonical)

    # -- read

    async def list_chunks(self, document_id: str) -> list[Chunk]:
        await self._require_doc(document_id)
        return await self._chunks.find_for_document(document_id)

    # -- mutations

    async def add_chunk(self, document_id: str, *, text: str, after_id: str | None = None) -> Chunk:
        await self._require_doc(document_id)
        existing = await self._chunks.find_for_document(document_id)
        sequence = self._sequence_after(existing, after_id)
        await self._shift_sequences(existing, from_sequence=sequence)

        new_chunk = Chunk(
            document_id=document_id,
            sequence=sequence,
            text=text,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        await self._chunks.insert(new_chunk)
        await self._edits.insert(
            ChunkEdit(
                id=_new_id(),
                document_id=document_id,
                chunk_id=new_chunk.id,
                action=ChunkEditAction.INSERT,
                actor=self._actor,
                at=_utcnow(),
                after=_chunk_to_audit_dict(new_chunk),
            )
        )
        logger.info(
            "chunk.add docId=%s chunkId=%s sequence=%d", document_id, new_chunk.id, sequence
        )
        return new_chunk

    async def update_chunk(
        self,
        document_id: str,
        chunk_id: str,
        *,
        text: str | None = None,
        headings: list[str] | None = None,
    ) -> Chunk:
        chunk = await self._require_chunk(document_id, chunk_id)
        before = _chunk_to_audit_dict(chunk)
        if text is not None:
            chunk.text = text
        if headings is not None:
            chunk.headings = list(headings)
        chunk.updated_at = _utcnow()
        await self._chunks.update(chunk)
        await self._edits.insert(
            ChunkEdit(
                id=_new_id(),
                document_id=document_id,
                chunk_id=chunk.id,
                action=ChunkEditAction.UPDATE,
                actor=self._actor,
                at=_utcnow(),
                before=before,
                after=_chunk_to_audit_dict(chunk),
            )
        )
        logger.info("chunk.update docId=%s chunkId=%s", document_id, chunk.id)
        return chunk

    async def delete_chunk(self, document_id: str, chunk_id: str) -> None:
        chunk = await self._require_chunk(document_id, chunk_id)
        before = _chunk_to_audit_dict(chunk)
        deleted = await self._chunks.soft_delete(chunk_id, at=_utcnow())
        if not deleted:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
        await self._edits.insert(
            ChunkEdit(
                id=_new_id(),
                document_id=document_id,
                chunk_id=chunk_id,
                action=ChunkEditAction.DELETE,
                actor=self._actor,
                at=_utcnow(),
                before=before,
            )
        )
        logger.info("chunk.delete docId=%s chunkId=%s", document_id, chunk.id)

    async def split_chunk(self, document_id: str, chunk_id: str, cursor_offset: int) -> list[Chunk]:
        source = await self._require_chunk(document_id, chunk_id)
        if cursor_offset <= 0 or cursor_offset >= len(source.text):
            raise ChunkValidationError(
                f"cursorOffset {cursor_offset} out of range for chunk of length {len(source.text)}"
            )
        existing = await self._chunks.find_for_document(document_id)
        before = _chunk_to_audit_dict(source)

        # Both halves inherit headings, source_page, bboxes, doc_items.
        # Token counts are unknown post-split; leave as None.
        head_text = source.text[:cursor_offset]
        tail_text = source.text[cursor_offset:]
        head = Chunk(
            document_id=document_id,
            sequence=source.sequence,
            text=head_text,
            headings=list(source.headings),
            source_page=source.source_page,
            bboxes=list(source.bboxes),
            doc_items=list(source.doc_items),
        )
        tail = Chunk(
            document_id=document_id,
            sequence=source.sequence + 1,
            text=tail_text,
            headings=list(source.headings),
            source_page=source.source_page,
            bboxes=list(source.bboxes),
            doc_items=list(source.doc_items),
        )

        # Push subsequent sequences by 1 to make room for `tail`.
        await self._shift_sequences(existing, from_sequence=source.sequence + 1)
        await self._chunks.soft_delete(source.id, at=_utcnow())
        await self._chunks.insert_many([head, tail])

        await self._edits.insert(
            ChunkEdit(
                id=_new_id(),
                document_id=document_id,
                chunk_id=source.id,
                action=ChunkEditAction.SPLIT,
                actor=self._actor,
                at=_utcnow(),
                before=before,
                children=[head.id, tail.id],
            )
        )
        logger.info(
            "chunk.split docId=%s sourceId=%s newIds=[%s,%s]",
            document_id,
            source.id,
            head.id,
            tail.id,
        )
        return [head, tail]

    async def merge_chunks(self, document_id: str, ids: list[str]) -> Chunk:
        if len(ids) < 2:
            raise ChunkValidationError("merge requires at least 2 chunk ids")
        existing = await self._chunks.find_for_document(document_id)
        by_id = {c.id: c for c in existing}
        targets = [by_id.get(i) for i in ids]
        if any(t is None for t in targets):
            missing = [i for i, t in zip(ids, targets, strict=True) if t is None]
            raise ChunkNotFoundError(f"Chunks not found: {missing}")

        ordered = sorted(targets, key=lambda c: c.sequence)
        sequences = [c.sequence for c in ordered]
        if sequences != list(range(sequences[0], sequences[0] + len(sequences))):
            raise ChunkConflictError("merge requires contiguous chunks (by sequence)")

        merged_text = "\n".join(c.text for c in ordered)
        bboxes: list[ChunkBbox] = []
        doc_items: list[ChunkDocItem] = []
        for c in ordered:
            bboxes.extend(c.bboxes)
            doc_items.extend(c.doc_items)
        token_total = sum((c.token_count or 0) for c in ordered) or None

        merged = Chunk(
            document_id=document_id,
            sequence=ordered[0].sequence,
            text=merged_text,
            headings=list(ordered[0].headings),
            source_page=ordered[0].source_page,
            bboxes=bboxes,
            doc_items=doc_items,
            token_count=token_total,
        )

        for c in ordered:
            await self._chunks.soft_delete(c.id, at=_utcnow())
        await self._chunks.insert(merged)

        await self._edits.insert(
            ChunkEdit(
                id=_new_id(),
                document_id=document_id,
                chunk_id=merged.id,
                action=ChunkEditAction.MERGE,
                actor=self._actor,
                at=_utcnow(),
                parents=[c.id for c in ordered],
                after=_chunk_to_audit_dict(merged),
            )
        )
        logger.info(
            "chunk.merge docId=%s sourceIds=%s newId=%s",
            document_id,
            [c.id for c in ordered],
            merged.id,
        )
        return merged

    async def rechunk_document(self, document_id: str, options: dict | None = None) -> list[Chunk]:
        """Re-run the chunker on the latest completed analysis JSON and
        replace the canonical chunkset.

        Emits one INSERT edit per new chunk and one DELETE per old chunk
        — keeps the audit log within the existing `ChunkEditAction` enum.
        """
        await self._require_doc(document_id)
        if not self._chunker:
            raise ChunkServiceError("Chunker not configured", http_status=503)

        job = await self._analyses.find_latest_completed_by_document(document_id)
        if not job or not job.document_json:
            raise ChunkServiceError(
                "No completed analysis with document_json available for rechunk",
                http_status=409,
            )

        chunk_opts = ChunkingOptions(**options) if options else ChunkingOptions()
        new_results = await self._chunker.chunk(job.document_json, chunk_opts)

        existing = await self._chunks.find_for_document(document_id)
        now = _utcnow()
        for c in existing:
            await self._chunks.soft_delete(c.id, at=now)
            await self._edits.insert(
                ChunkEdit(
                    id=_new_id(),
                    document_id=document_id,
                    chunk_id=c.id,
                    action=ChunkEditAction.DELETE,
                    actor="system:rechunk",
                    at=now,
                    before=_chunk_to_audit_dict(c),
                )
            )

        new_chunks = [
            Chunk(
                document_id=document_id,
                sequence=seq,
                text=r.text,
                headings=list(r.headings),
                source_page=r.source_page,
                bboxes=list(r.bboxes),
                doc_items=list(r.doc_items),
                token_count=r.token_count or None,
            )
            for seq, r in enumerate(new_results)
        ]
        if new_chunks:
            await self._chunks.insert_many(new_chunks)
            for c in new_chunks:
                await self._edits.insert(
                    ChunkEdit(
                        id=_new_id(),
                        document_id=document_id,
                        chunk_id=c.id,
                        action=ChunkEditAction.INSERT,
                        actor="system:rechunk",
                        at=now,
                        after=_chunk_to_audit_dict(c),
                    )
                )
        logger.info(
            "chunk.rechunk docId=%s oldCount=%d newCount=%d",
            document_id,
            len(existing),
            len(new_chunks),
        )

        # Record a frozen (analysis, chunks_snapshot) pair in the
        # workspace History timeline (#267). Snapshots the chunks we
        # just wrote, paired with the analysis they came from.
        if self._version_recorder is not None:
            try:
                await self._version_recorder.record_on_rechunk(document_id, job.id)
            except Exception:
                # Best-effort hook — never fail the rechunk if the
                # version snapshot write hits a snag.
                logger.exception(
                    "Version snapshot failed for doc %s after rechunk",
                    document_id,
                )

        return new_chunks

    # -- diff (against last push to a store)

    async def diff_against_store(self, document_id: str, store_id: str) -> list[dict]:
        """Compare the canonical chunkset to the last push for `store_id`.

        Returns a list of `ChunkDiff`-shaped dicts (camelCase) covering:
          - canonical chunks not in the last push → status "added"
          - canonical chunks updated since last push → status "modified"
          - canonical chunks unchanged since push → status "unchanged"
          - chunk ids in last push absent from canonical → status "removed"

        Coarse-grained — does not produce a textDiff today (follow-up).
        """
        await self._require_doc(document_id)
        canonical = await self._chunks.find_for_document(document_id)
        last_push = await self._pushes.find_latest(document_id, store_id)
        if last_push is None:
            return [{"chunkId": c.id, "status": "added", "textDiff": None} for c in canonical]

        pushed_ids = set(last_push.chunk_ids)
        diffs: list[dict] = []
        for c in canonical:
            if c.id not in pushed_ids:
                diffs.append({"chunkId": c.id, "status": "added", "textDiff": None})
                continue
            if c.updated_at > last_push.pushed_at:
                diffs.append({"chunkId": c.id, "status": "modified", "textDiff": None})
            else:
                diffs.append({"chunkId": c.id, "status": "unchanged", "textDiff": None})
        canonical_ids = {c.id for c in canonical}
        for cid in pushed_ids - canonical_ids:
            diffs.append({"chunkId": cid, "status": "removed", "textDiff": None})
        return diffs

    # -- push (delegates to IngestionService; per-store dispatch is a follow-up)

    async def push_to_store(self, document_id: str, store_id: str) -> dict:
        """Push the canonical chunkset to a store and record a `ChunkPush`.

        Today this delegates to the globally-configured `IngestionService`
        (single index). Per-store dispatch by slug is a follow-up issue —
        the `store_id` argument is recorded on the `ChunkPush` row so the
        diff endpoint can answer "what was last pushed to store X" even
        once the dispatch lands.
        """
        await self._require_doc(document_id)
        if self._ingestion is None:
            raise ChunkServiceError(
                "Ingestion not available (EMBEDDING_URL and OPENSEARCH_URL required)",
                http_status=503,
            )
        doc = await self._documents.find_by_id(document_id)
        canonical = await self._chunks.find_for_document(document_id)
        if not canonical:
            raise ChunkServiceError(
                "No canonical chunks to push — run analysis or rechunk first",
                http_status=409,
            )

        chunks_payload = [_chunk_to_ingestion_dict(c) for c in canonical]
        chunks_json_payload = json.dumps(chunks_payload)
        ingestion_result = await self._ingestion.ingest(
            doc_id=document_id,
            filename=(doc.filename if doc else document_id),
            chunks_json=chunks_json_payload,
        )

        chunk_ids = [c.id for c in canonical]
        push = ChunkPush(
            id=_new_id(),
            document_id=document_id,
            store_id=store_id,
            chunkset_hash=_compute_chunkset_hash(canonical),
            chunk_ids=chunk_ids,
            pushed_at=_utcnow(),
        )
        await self._pushes.insert(push)

        token_total = sum((c.token_count or 0) for c in canonical)
        logger.info(
            "chunk.push docId=%s store=%s count=%d tokens=%d",
            document_id,
            store_id,
            ingestion_result.chunks_indexed,
            token_total,
        )
        return {
            "jobId": push.id,
            "summary": {
                "embeds": ingestion_result.chunks_indexed,
                "tokens": token_total,
            },
        }

    # -- tree (read from latest analysis document_json)

    async def get_tree(self, document_id: str) -> list[dict]:
        """Build a doc tree from the latest completed analysis.

        Returns a list of `DocTreeNode`-shaped dicts (camelCase). Empty
        list if no analysis is available yet — caller decides if that is
        an error or just "not parsed yet".
        """
        await self._require_doc(document_id)
        job = await self._analyses.find_latest_completed_by_document(document_id)
        if not job or not job.document_json:
            return []
        try:
            doc_data = json.loads(job.document_json)
        except json.JSONDecodeError:
            logger.exception("Invalid document_json for analysis %s", job.id)
            return []
        return _build_tree_nodes(doc_data)

    # -- guards

    async def _require_doc(self, document_id: str) -> None:
        doc = await self._documents.find_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Document not found: {document_id}")

    async def _require_chunk(self, document_id: str, chunk_id: str) -> Chunk:
        chunk = await self._chunks.find_by_id(chunk_id)
        if not chunk or chunk.document_id != document_id or chunk.deleted_at is not None:
            raise ChunkNotFoundError(f"Chunk not found: {chunk_id}")
        return chunk

    # -- sequence helpers

    @staticmethod
    def _sequence_after(existing: list[Chunk], after_id: str | None) -> int:
        if after_id is None:
            return (max((c.sequence for c in existing), default=-1)) + 1
        anchor = next((c for c in existing if c.id == after_id), None)
        if anchor is None:
            raise ChunkNotFoundError(f"Anchor chunk not found: {after_id}")
        return anchor.sequence + 1

    async def _shift_sequences(self, existing: list[Chunk], *, from_sequence: int) -> None:
        """Push chunks at >= from_sequence one slot up to make room."""
        affected = [c for c in existing if c.sequence >= from_sequence]
        for c in affected:
            c.sequence += 1
            c.updated_at = _utcnow()
            await self._chunks.update(c)


# ---------------------------------------------------------------------------
# Tree projection — extract a hierarchical outline from a DoclingDocument.
# Kept module-level so it stays cheap to test in isolation.
# ---------------------------------------------------------------------------


def _chunk_to_ingestion_dict(c: Chunk) -> dict:
    """Convert a canonical `Chunk` into the legacy chunks_json shape that
    `IngestionService.ingest` consumes (camelCase, modeled after
    `analysis_service._chunk_to_dict`)."""
    return {
        "text": c.text,
        "headings": list(c.headings),
        "sourcePage": c.source_page,
        "tokenCount": c.token_count or 0,
        "bboxes": [{"page": b.page, "bbox": list(b.bbox)} for b in c.bboxes],
        "docItems": [{"selfRef": d.self_ref, "label": d.label} for d in c.doc_items],
    }


def _compute_chunkset_hash(chunks: list[Chunk]) -> str:
    """Stable hash of the canonical chunkset content.

    Used by `ChunkPush` snapshots so we can answer 'is the store in sync
    with the current canonical state' without listing chunks from the
    vector store.
    """
    import hashlib

    h = hashlib.sha256()
    for c in chunks:
        h.update(c.id.encode("utf-8"))
        h.update(b"\x00")
        h.update(c.text.encode("utf-8"))
        h.update(b"\x00")
        h.update(str(c.updated_at).encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()


def _build_tree_nodes(doc_data: dict) -> list[dict]:
    """Project a Docling document JSON into a `[DocTreeNode]` outline.

    The Docling document layout has top-level lists like `texts`, `tables`,
    `pictures`, `groups`, etc. Each entry carries a `self_ref` and a
    `label`. We surface a flat outline grouped by label families, which
    is enough for the Inspect tab — full hierarchy reconstruction is a
    follow-up (#216).
    """
    sections = (
        ("section_header", "Sections", []),
        ("title", "Titles", []),
        ("text", "Paragraphs", []),
        ("table", "Tables", []),
        ("picture", "Pictures", []),
    )
    section_map = {label: bucket for label, _, bucket in sections}

    for collection in ("texts", "tables", "pictures", "groups"):
        for item in doc_data.get(collection, []) or []:
            label = item.get("label") or collection.rstrip("s")
            ref = item.get("self_ref") or item.get("selfRef") or ""
            display = item.get("text") or item.get("name") or label
            bucket = section_map.get(label)
            if bucket is None:
                continue
            bucket.append({"ref": ref, "type": label, "label": display, "children": []})

    return [
        {"ref": f"#group/{key}", "type": "group", "label": title, "children": children}
        for key, title, children in sections
        if children
    ]
