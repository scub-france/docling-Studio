"""Setting a document's analysis state directly, for tests that need one.

Production writes the state only through the writers that own each part
(completion, deletion, rechunk, restore); these helpers use the same
persistence functions, one committed write each.
"""

from __future__ import annotations

from domain.models import DocumentChunkSource
from persistence.database import get_connection
from persistence.document_analysis_repo import write_chunk_source, write_selection


async def set_selection(document_id: str, analysis_id: str | None) -> None:
    """Select `analysis_id`; None clears an existing selection, never creating a row."""
    async with get_connection() as db:
        await write_selection(db, document_id, analysis_id)
        await db.commit()


async def set_chunk_source(
    document_id: str, analysis_id: str | None, result_hash: str | None = None
) -> None:
    """Record the chunk source; None forgets it, never creating a row."""
    source = (
        DocumentChunkSource(document_id, analysis_id, result_hash)
        if analysis_id is not None and result_hash is not None
        else None
    )
    async with get_connection() as db:
        await write_chunk_source(db, document_id, source)
        await db.commit()
