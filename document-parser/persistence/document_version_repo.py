"""Document-version repository — SQLite CRUD for frozen (analysis, chunks)
pairs (#267).
"""

from __future__ import annotations

from domain.models import DocumentVersion, DocumentVersionKind
from persistence.database import get_connection
from persistence.iso_datetime import require_iso


def _row_to_version(row) -> DocumentVersion:
    return DocumentVersion(
        id=row["id"],
        document_id=row["document_id"],
        kind=DocumentVersionKind(row["kind"]),
        analysis_id=row["analysis_id"],
        chunks_source_analysis_id=row["chunks_source_analysis_id"],
        chunks_source_result_hash=row["chunks_source_result_hash"],
        chunks_snapshot=row["chunks_snapshot"],
        summary=row["summary"] or "",
        created_at=require_iso(row["created_at"]),
    )


_INSERT_SQL = """INSERT INTO document_versions
    (id, document_id, kind, analysis_id, chunks_source_analysis_id, chunks_source_result_hash,
     chunks_snapshot, summary, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""


class SqliteDocumentVersionRepository:
    """Persists `DocumentVersion` rows ordered newest-first per document."""

    async def insert(self, version: DocumentVersion) -> None:
        async with get_connection() as conn:
            await conn.execute(
                _INSERT_SQL,
                (
                    version.id,
                    version.document_id,
                    version.kind.value,
                    version.analysis_id,
                    version.chunks_source_analysis_id,
                    version.chunks_source_result_hash,
                    version.chunks_snapshot,
                    version.summary,
                    str(version.created_at),
                ),
            )
            await conn.commit()

    async def find_by_id(self, version_id: str) -> DocumentVersion | None:
        async with get_connection() as conn:
            cur = await conn.execute(
                "SELECT * FROM document_versions WHERE id = ?",
                (version_id,),
            )
            row = await cur.fetchone()
            return _row_to_version(row) if row else None

    async def find_for_document(self, document_id: str) -> list[DocumentVersion]:
        """Returns all versions for the document, newest-first."""
        async with get_connection() as conn:
            cur = await conn.execute(
                "SELECT * FROM document_versions WHERE document_id = ? ORDER BY created_at DESC",
                (document_id,),
            )
            rows = await cur.fetchall()
            return [_row_to_version(r) for r in rows]
