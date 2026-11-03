"""Chunk ↔ dict: the persisted and wire shapes of a chunk, in one place.

Three shapes are written, and each is read back later by something else, so
each keeps its exact keys — these are formats on disk, not a style choice:

- **journal** (`chunk_to_audit_dict`): the `before` / `after` snapshot of a
  `chunk_edits` row. Its doc items say `self_ref`, and an unknown token count
  stays `null`.
- **ingestion** (`chunk_to_ingestion_dict`): what `IngestionService.ingest`
  reads from `chunks_json` on a push. An unknown token count is `0`.
- **version snapshot** (`chunk_to_snapshot_dict`): one entry of
  `document_versions.chunks_snapshot`, which a restore reads back.

All three share the camelCase core (`text`, `headings`, `sourcePage`,
`tokenCount`, `bboxes`, `docItems` with `selfRef`) that an analysis also
writes in `analysis_jobs.chunks_json`. One reader, `chunk_from_dict`, turns
the core back into a `Chunk`: the promotion of an analysis's chunks and a
version restore both go through it. It also takes the journal's `self_ref`
spelling of a doc item, so it reads every shape above.

Pure: no I/O. Dict key order is part of the bytes written, so it is kept.
"""

from __future__ import annotations

from typing import Any

from domain.models import Chunk
from domain.value_objects import ChunkBbox, ChunkDocItem


def chunk_to_audit_dict(c: Chunk) -> dict[str, Any]:
    """The journal snapshot of a chunk (`ChunkEdit.before` / `.after`)."""
    return {
        "id": c.id,
        "sequence": c.sequence,
        **_core(c),
        "docItems": [{"self_ref": d.self_ref, "label": d.label} for d in c.doc_items],
    }


def chunk_to_ingestion_dict(c: Chunk) -> dict[str, Any]:
    """One entry of the `chunks_json` a push hands to the ingestion."""
    return {**_core(c), "tokenCount": c.token_count or 0}


def chunk_to_snapshot_dict(c: Chunk) -> dict[str, Any]:
    """One entry of a version's `chunks_snapshot`."""
    return {
        "id": c.id,
        "documentId": c.document_id,
        "sequence": c.sequence,
        **_core(c),
        "createdAt": str(c.created_at),
        "updatedAt": str(c.updated_at),
    }


def chunk_from_dict(
    raw: dict[str, Any],
    *,
    document_id: str,
    sequence: int,
    chunk_id: str | None = None,
) -> Chunk:
    """A new `Chunk` of `document_id` at `sequence` from a serialized one.

    Reads the camelCase core only: the entry's own id, sequence and dates are
    left out, the chunk gets `chunk_id` (or a fresh id) and new timestamps.
    """
    identity = {} if chunk_id is None else {"id": chunk_id}
    return Chunk(
        **identity,
        document_id=document_id,
        sequence=sequence,
        text=raw.get("text", ""),
        headings=list(raw.get("headings", [])),
        source_page=raw.get("sourcePage"),
        bboxes=[ChunkBbox(page=b["page"], bbox=list(b["bbox"])) for b in raw.get("bboxes", [])],
        doc_items=[_doc_item_from_dict(d) for d in raw.get("docItems", [])],
        token_count=raw.get("tokenCount"),
    )


def _core(c: Chunk) -> dict[str, Any]:
    return {
        "text": c.text,
        "headings": list(c.headings),
        "sourcePage": c.source_page,
        "tokenCount": c.token_count,
        "bboxes": [{"page": b.page, "bbox": list(b.bbox)} for b in c.bboxes],
        "docItems": [{"selfRef": d.self_ref, "label": d.label} for d in c.doc_items],
    }


def _doc_item_from_dict(d: dict[str, Any]) -> ChunkDocItem:
    return ChunkDocItem(
        self_ref=d.get("selfRef") or d.get("self_ref", ""), label=d.get("label", "")
    )
