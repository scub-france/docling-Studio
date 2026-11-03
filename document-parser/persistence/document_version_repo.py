"""Document-version repository — SQLite CRUD for frozen (analysis, chunks)
pairs (#267).
"""

from __future__ import annotations

from domain.models import DocumentVersion, DocumentVersionKind
from domain.ports import DocumentVersionEntry
from persistence.database import get_connection
from persistence.timestamps import parse_required_iso


def _row_to_version(row) -> DocumentVersion:
    # The history list selects every column but the snapshot (`_LIST_SQL`).
    keys = row.keys()
    return DocumentVersion(
        id=row["id"],
        document_id=row["document_id"],
        kind=DocumentVersionKind(row["kind"]),
        analysis_id=row["analysis_id"],
        chunks_snapshot=row["chunks_snapshot"] if "chunks_snapshot" in keys else None,
        summary=row["summary"] or "",
        created_at=parse_required_iso(row["created_at"], column="document_versions.created_at"),
    )


_INSERT_SQL = """INSERT INTO document_versions
    (id, document_id, kind, analysis_id, chunks_snapshot, summary, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)"""

# Every column but the snapshot, plus its length counted by SQLite: listing
# never ships the snapshots (a full chunkset each) to Python. `json_valid`
# keeps a corrupt snapshot from failing the whole list — it counts 0.
_LIST_SQL = """SELECT id, document_id, kind, analysis_id, summary, created_at,
           CASE WHEN json_valid(chunks_snapshot)
                THEN json_array_length(chunks_snapshot) ELSE 0 END AS chunk_count
    FROM document_versions
    WHERE document_id = ?
    ORDER BY created_at DESC"""


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

    async def list_for_document(self, document_id: str) -> list[DocumentVersionEntry]:
        """All versions of the document, newest first, snapshot bodies left
        out (`chunks_snapshot` is None) and their chunk counts computed by
        SQLite."""
        async with get_connection() as conn:
            cur = await conn.execute(_LIST_SQL, (document_id,))
            rows = await cur.fetchall()
            return [
                DocumentVersionEntry(version=_row_to_version(r), chunk_count=r["chunk_count"])
                for r in rows
            ]

    async def find_latest_for_document(self, document_id: str) -> DocumentVersion | None:
        """Most recent version for the document, or None."""
        async with get_connection() as conn:
            cur = await conn.execute(
                "SELECT * FROM document_versions WHERE document_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (document_id,),
            )
            row = await cur.fetchone()
            return _row_to_version(row) if row else None
