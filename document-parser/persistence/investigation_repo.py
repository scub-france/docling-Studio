"""SQLite adapter for the `InvestigationRepository` port (#329).

Three tables, one aggregate. `find_by_id` reads all three in one connection
and assembles the tree, because every consumer of an investigation wants the
tree — the alternative is a join whose duplicate rows the caller has to undo.

The interesting method is `record_attempt`. The attempt cap has to hold under
`stateless_http`, where two requests may land on two workers with no session
between them, so the count and the insert are one statement: SQLite either
inserts the row with the next ordinal or inserts nothing. `UNIQUE(step_id,
ordinal)` closes the remaining window — two callers that both computed the
same ordinal cannot both land, and the loser retries against the new count.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any

from domain.investigation import (
    Attempt,
    AttemptOutcome,
    Investigation,
    InvestigationState,
    Step,
    StepState,
)
from domain.ports import AttemptBudgetSpentError
from persistence.database import get_connection

if TYPE_CHECKING:
    import aiosqlite

# One statement: count the step's attempts, and insert only if the budget
# allows it. `HAVING` without `GROUP BY` filters the single aggregate row, so
# a spent budget yields no row and therefore no insert.
_INSERT_ATTEMPT = """
INSERT INTO investigation_attempts
    (id, step_id, ordinal, thought, uri, quote, created_at)
SELECT ?, ?, COUNT(*) + 1, ?, ?, ?, ?
  FROM investigation_attempts
 WHERE step_id = ?
HAVING COUNT(*) < ?
"""


class SqliteInvestigationRepository:
    """aiosqlite-backed implementation of `InvestigationRepository`."""

    async def create(self, investigation: Investigation) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO investigations
                   (id, document_id, version_id, question, state, stale, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    investigation.id,
                    investigation.document_id,
                    investigation.version_id,
                    investigation.question,
                    str(investigation.state),
                    int(investigation.stale),
                    investigation.created_at.isoformat(),
                ),
            )
            await db.commit()

    async def find_by_id(self, investigation_id: str) -> Investigation | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM investigations WHERE id = ?", (investigation_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return await self._hydrate(db, row)

    async def find_for_document(
        self,
        document_id: str,
        *,
        limit: int = 20,
    ) -> list[Investigation]:
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM investigations WHERE document_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (document_id, limit),
            )
            rows = await cursor.fetchall()
            return [await self._hydrate(db, row) for row in rows]

    async def count_open_for_document(self, document_id: str) -> int:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) AS n FROM investigations WHERE document_id = ? AND state = 'open'",
                (document_id,),
            )
            row = await cursor.fetchone()
        return int(row["n"]) if row else 0

    async def add_steps(self, investigation_id: str, steps: list[Step]) -> None:
        if not steps:
            return
        async with get_connection() as db:
            await db.executemany(
                """INSERT INTO investigation_steps
                   (id, investigation_id, ordinal, question, why, state, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                [
                    (
                        step.id,
                        investigation_id,
                        step.ordinal,
                        step.question,
                        step.why,
                        str(step.state),
                    )
                    for step in steps
                ],
            )
            await db.commit()

    async def record_attempt(self, attempt: Attempt, *, cap: int) -> Attempt:
        """Insert `attempt` iff the step has budget left. Atomic by statement."""
        async with get_connection() as db:
            for _ in range(2):
                try:
                    cursor = await db.execute(
                        _INSERT_ATTEMPT,
                        (
                            attempt.id,
                            attempt.step_id,
                            attempt.thought,
                            attempt.uri,
                            attempt.quote,
                            attempt.created_at.isoformat(),
                            attempt.step_id,
                            cap,
                        ),
                    )
                except sqlite3.IntegrityError:
                    # Another caller took this ordinal between the count and
                    # the insert. Re-run: the count is higher now, and either
                    # there is still budget or `HAVING` refuses.
                    continue
                if cursor.rowcount:
                    await db.commit()
                    return await self._reload_attempt(db, attempt)
                break
        raise AttemptBudgetSpentError(attempt.step_id)

    async def settle_attempt(self, attempt: Attempt) -> None:
        async with get_connection() as db:
            await db.execute(
                """UPDATE investigation_attempts
                      SET outcome = ?, detail = ?, kept_uri = ?, actual_quote = ?
                    WHERE id = ?""",
                (
                    str(attempt.outcome) if attempt.outcome else None,
                    attempt.detail,
                    attempt.kept_uri,
                    attempt.actual_quote,
                    attempt.id,
                ),
            )
            await db.commit()

    async def set_step_state(self, step_id: str, state: StepState) -> None:
        async with get_connection() as db:
            await db.execute(
                "UPDATE investigation_steps SET state = ? WHERE id = ?",
                (str(state), step_id),
            )
            await db.commit()

    async def mark_stale(self, investigation_id: str) -> None:
        async with get_connection() as db:
            await db.execute(
                "UPDATE investigations SET stale = 1 WHERE id = ?", (investigation_id,)
            )
            await db.commit()

    async def close(self, investigation_id: str, *, answer: str, at: datetime) -> None:
        async with get_connection() as db:
            await db.execute(
                """UPDATE investigations
                      SET state = 'closed', answer = ?, closed_at = ?
                    WHERE id = ?""",
                (answer, at.isoformat(), investigation_id),
            )
            await db.commit()

    # ------------------------------------------------------------------
    # Row assembly
    # ------------------------------------------------------------------

    async def _hydrate(self, db: aiosqlite.Connection, row: Any) -> Investigation:
        cursor = await db.execute(
            "SELECT * FROM investigation_steps WHERE investigation_id = ? ORDER BY ordinal",
            (row["id"],),
        )
        step_rows = await cursor.fetchall()
        steps = [await self._step(db, step_row) for step_row in step_rows]
        return Investigation(
            id=row["id"],
            document_id=row["document_id"],
            version_id=row["version_id"],
            question=row["question"],
            created_at=_dt(row["created_at"]) or datetime.now().astimezone(),
            state=InvestigationState(row["state"]),
            stale=bool(row["stale"]),
            answer=row["answer"],
            steps=steps,
            closed_at=_dt(row["closed_at"]),
        )

    async def _step(self, db: aiosqlite.Connection, row: Any) -> Step:
        cursor = await db.execute(
            "SELECT * FROM investigation_attempts WHERE step_id = ? ORDER BY ordinal",
            (row["id"],),
        )
        attempts = [_attempt(attempt_row) for attempt_row in await cursor.fetchall()]
        return Step(
            id=row["id"],
            ordinal=row["ordinal"],
            question=row["question"],
            why=row["why"],
            state=StepState(row["state"]),
            attempts=attempts,
        )

    async def _reload_attempt(self, db: aiosqlite.Connection, attempt: Attempt) -> Attempt:
        """Read back the ordinal SQLite computed — the caller never guesses it."""
        cursor = await db.execute(
            "SELECT * FROM investigation_attempts WHERE id = ?", (attempt.id,)
        )
        row = await cursor.fetchone()
        return _attempt(row) if row else attempt


def _attempt(row: Any) -> Attempt:
    return Attempt(
        id=row["id"],
        step_id=row["step_id"],
        ordinal=row["ordinal"],
        thought=row["thought"],
        uri=row["uri"],
        created_at=_dt(row["created_at"]) or datetime.now().astimezone(),
        quote=row["quote"],
        outcome=AttemptOutcome(row["outcome"]) if row["outcome"] else None,
        detail=row["detail"] or "",
        kept_uri=row["kept_uri"],
        actual_quote=row["actual_quote"],
    )


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
