"""Analysis job repository — SQLite CRUD for analysis_jobs table."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from domain.models import AnalysisJob, AnalysisStatus
from persistence.database import get_connection
from persistence.document_analysis_repo import read_document_analysis_state, write_selection
from persistence.iso_datetime import parse_iso

if TYPE_CHECKING:
    import aiosqlite


def _row_to_job(row) -> AnalysisJob:
    keys = row.keys()
    return AnalysisJob(
        id=row["id"],
        document_id=row["document_id"],
        status=AnalysisStatus(row["status"]),
        content_markdown=row["content_markdown"] if "content_markdown" in keys else None,
        content_html=row["content_html"] if "content_html" in keys else None,
        pages_json=row["pages_json"] if "pages_json" in keys else None,
        document_json=row["document_json"] if "document_json" in keys else None,
        chunks_json=row["chunks_json"] if "chunks_json" in keys else None,
        error_message=row["error_message"],
        progress_current=row["progress_current"] if "progress_current" in keys else None,
        progress_total=row["progress_total"] if "progress_total" in keys else None,
        started_at=parse_iso(row["started_at"]),
        completed_at=parse_iso(row["completed_at"]),
        created_at=parse_iso(row["created_at"]) or datetime.now(UTC),
        document_filename=row["filename"] if "filename" in keys else None,
    )


_SELECT_WITH_DOC = """
    SELECT aj.*, d.filename
    FROM analysis_jobs aj
    JOIN documents d ON d.id = aj.document_id
"""

# Everything but the content (markdown, HTML, pages, chunks, Docling document):
# what following the statuses of many analyses needs (#354).
_SELECT_SUMMARY = """
    SELECT aj.id, aj.document_id, aj.status, aj.error_message, aj.progress_current,
           aj.progress_total, aj.started_at, aj.completed_at, aj.created_at, d.filename
    FROM analysis_jobs aj
    JOIN documents d ON d.id = aj.document_id
"""


class SqliteAnalysisRepository:
    """SQLite implementation of the AnalysisRepository port."""

    async def insert(self, job: AnalysisJob) -> None:
        """Persist a new analysis job record."""
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO analysis_jobs (id, document_id, status, created_at)
                   VALUES (?, ?, ?, ?)""",
                (job.id, job.document_id, job.status.value, str(job.created_at)),
            )
            await db.commit()

    async def find_all(self, *, limit: int = 200, offset: int = 0) -> list[AnalysisJob]:
        """Return analysis jobs with document info, newest first."""
        async with get_connection() as db:
            cursor = await db.execute(
                f"{_SELECT_WITH_DOC} ORDER BY aj.created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cursor.fetchall()
            return [_row_to_job(r) for r in rows]

    async def find_all_summaries(self, *, limit: int = 200, offset: int = 0) -> list[AnalysisJob]:
        """Return analysis jobs without their content, newest first (#354)."""
        async with get_connection() as db:
            cursor = await db.execute(
                f"{_SELECT_SUMMARY} ORDER BY aj.created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cursor.fetchall()
            return [_row_to_job(r) for r in rows]

    async def find_summaries_by_document(self, document_id: str) -> list[AnalysisJob]:
        """Every analysis of one document without its content, newest first.

        No cap: the 200-row cap bounds the cross-document listing, and one
        document's analyses are what a user ran on it — a count that must not
        come out short.
        """
        async with get_connection() as db:
            cursor = await db.execute(
                f"{_SELECT_SUMMARY} WHERE aj.document_id = ? ORDER BY aj.created_at DESC",
                (document_id,),
            )
            rows = await cursor.fetchall()
            return [_row_to_job(r) for r in rows]

    async def find_by_document(
        self, document_id: str, *, limit: int = 200, offset: int = 0
    ) -> list[AnalysisJob]:
        """Return analysis jobs for a given document, newest first."""
        async with get_connection() as db:
            cursor = await db.execute(
                f"{_SELECT_WITH_DOC} WHERE aj.document_id = ? "
                "ORDER BY aj.created_at DESC LIMIT ? OFFSET ?",
                (document_id, limit, offset),
            )
            rows = await cursor.fetchall()
            return [_row_to_job(r) for r in rows]

    async def find_by_id(self, job_id: str) -> AnalysisJob | None:
        """Find an analysis job by ID (with document filename), or return None."""
        async with get_connection() as db:
            cursor = await db.execute(f"{_SELECT_WITH_DOC} WHERE aj.id = ?", (job_id,))
            row = await cursor.fetchone()
            return _row_to_job(row) if row else None

    async def find_latest_parsed_ids(self, document_ids: list[str]) -> dict[str, str]:
        """For each document, the id of its latest completed analysis with a parse.

        The fallback of `resolve_current_analysis_id` for documents with no
        state row; `CurrentAnalysisResolver` is its only caller.
        """
        if not document_ids:
            return {}
        async with get_connection() as db:
            return await _find_latest_parsed_ids(db, document_ids)

    async def find_parsed_document_id(self, job_id: str) -> str | None:
        """The document an analysis with a parse belongs to, or None."""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT document_id FROM analysis_jobs WHERE id = ? AND document_json IS NOT NULL",
                (job_id,),
            )
            row = await cursor.fetchone()
            return row["document_id"] if row else None

    async def find_parsed_ids(self, job_ids: list[str]) -> set[str]:
        """The ids among `job_ids` of analyses that kept a parse."""
        if not job_ids:
            return set()
        placeholders = ",".join("?" for _ in job_ids)
        async with get_connection() as db:
            cursor = await db.execute(
                f"SELECT id FROM analysis_jobs WHERE id IN ({placeholders}) "
                "AND document_json IS NOT NULL",
                tuple(job_ids),
            )
            return {row["id"] for row in await cursor.fetchall()}

    async def parse_json(self, job_id: str) -> str | None:
        """The stored docling JSON of an analysis — the one heavy column, alone."""
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT document_json FROM analysis_jobs WHERE id = ?", (job_id,)
            )
            row = await cursor.fetchone()
            return row["document_json"] if row else None

    async def update_status(self, job: AnalysisJob) -> None:
        """Persist all mutable fields of an analysis job (status, results, timestamps)."""
        async with get_connection() as db:
            await _write_job_state(db, job)
            await db.commit()

    async def complete_and_select(self, job: AnalysisJob) -> None:
        """Persist a completed analysis and make it the document's active one.

        Both writes share one transaction: a completed job never exists
        without its selection, and a failed selection rolls the job back.
        """
        if not job.can_be_current():
            raise ValueError("Only a completed analysis can become active")
        async with get_connection() as db:
            await _write_job_state(db, job)
            # Only the selection: the chunk source stays as the last rechunk
            # left it. The state SQL lives in the state repository; it joins
            # this transaction through the shared connection.
            await write_selection(db, job.document_id, job.id)
            await db.commit()

    async def update_progress(self, job_id: str, current: int, total: int) -> None:
        """Update only the progress columns for a running analysis."""
        async with get_connection() as db:
            await db.execute(
                "UPDATE analysis_jobs SET progress_current = ?, progress_total = ? WHERE id = ?",
                (current, total, job_id),
            )
            await db.commit()

    async def update_chunks(self, job_id: str, chunks_json: str) -> bool:
        """Update only the chunks_json column for a completed analysis."""
        async with get_connection() as db:
            cursor = await db.execute(
                "UPDATE analysis_jobs SET chunks_json = ? WHERE id = ?",
                (chunks_json, job_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete(self, job_id: str) -> bool:
        """Delete an analysis job by ID. Returns True if a row was removed.

        Deleting the document's active analysis hands the selection to the
        latest remaining completed analysis with a Docling document
        (`DocumentAnalysisState.resolve_selection_after_deleting`), in the same
        transaction: the foreign key alone would leave the document without
        a current analysis while a usable one remains.
        """
        async with get_connection() as db:
            # Take the write lock first: the state read below must still hold
            # when the delete and the new selection are written.
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT document_id FROM analysis_jobs WHERE id = ?", (job_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                await db.rollback()
                return False
            document_id = row["document_id"]
            state = await read_document_analysis_state(db, document_id)
            await db.execute("DELETE FROM analysis_jobs WHERE id = ?", (job_id,))
            if state is not None and state.active_analysis_id == job_id:
                latest = await _find_latest_parsed_ids(db, [document_id])
                await write_selection(
                    db,
                    document_id,
                    state.resolve_selection_after_deleting(job_id, latest.get(document_id)),
                )
            await db.commit()
            return True

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all analysis jobs for a given document. Returns count deleted."""
        async with get_connection() as db:
            cursor = await db.execute(
                "DELETE FROM analysis_jobs WHERE document_id = ?", (document_id,)
            )
            await db.commit()
            return cursor.rowcount


async def _find_latest_parsed_ids(
    db: aiosqlite.Connection, document_ids: list[str]
) -> dict[str, str]:
    """Each document's latest completed analysis with a Docling document, on `db`.

    The SQL form of `AnalysisJob.has_docling_document`, ranked by completion.
    """
    placeholders = ",".join("?" for _ in document_ids)
    cursor = await db.execute(
        f"""SELECT document_id, id FROM (
                SELECT document_id, id, ROW_NUMBER() OVER (
                    PARTITION BY document_id ORDER BY completed_at DESC
                ) AS rank
                FROM analysis_jobs
                WHERE document_id IN ({placeholders})
                  AND status = 'COMPLETED' AND document_json IS NOT NULL
            ) WHERE rank = 1""",
        tuple(document_ids),
    )
    return {row["document_id"]: row["id"] for row in await cursor.fetchall()}


async def _write_job_state(db, job: AnalysisJob) -> None:
    await db.execute(
        """UPDATE analysis_jobs
           SET status = ?, content_markdown = ?, content_html = ?,
               pages_json = ?, document_json = ?, chunks_json = ?,
               error_message = ?, progress_current = ?, progress_total = ?,
               started_at = ?, completed_at = ?
           WHERE id = ?""",
        (
            job.status.value,
            job.content_markdown,
            job.content_html,
            job.pages_json,
            job.document_json,
            job.chunks_json,
            job.error_message,
            job.progress_current,
            job.progress_total,
            str(job.started_at) if job.started_at else None,
            str(job.completed_at) if job.completed_at else None,
            job.id,
        ),
    )
