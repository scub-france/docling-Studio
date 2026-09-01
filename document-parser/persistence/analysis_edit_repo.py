"""SQLite adapter for durable analysis edit streams."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from domain.analysis_editing import EditCommand, EditStream, StoredEditCommand, WorkingCopy
from persistence.database import get_connection


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _stream(row) -> EditStream:
    return EditStream(
        id=row["id"],
        document_id=row["document_id"],
        base_analysis_id=row["base_analysis_id"],
        base_document_hash=row["base_document_hash"],
        engine_version=row["engine_version"],
        created_at=_dt(row["created_at"]),
    )


def _command(row) -> StoredEditCommand:
    return StoredEditCommand(
        id=row["id"],
        stream_id=row["stream_id"],
        sequence=row["sequence"],
        command=EditCommand(
            command_type=row["command_type"],
            payload=json.loads(row["payload_json"]),
            command_version=row["command_version"],
        ),
        command_hash=row["command_hash"],
        created_at=_dt(row["created_at"]),
    )


def _working(row) -> WorkingCopy:
    return WorkingCopy(
        document_id=row["document_id"],
        stream_id=row["stream_id"],
        base_analysis_id=row["base_analysis_id"],
        applied_through_sequence=row["applied_through_sequence"],
        document_json=row["document_json"],
        content_markdown=row["content_markdown"],
        content_html=row["content_html"],
        pages_json=row["pages_json"],
        editor_model_json=row["editor_model_json"],
        command_stream_hash=row["command_stream_hash"],
        result_hash=row["result_hash"],
        updated_at=_dt(row["updated_at"]),
    )


class SqliteAnalysisEditRepository:
    """One transaction owns command sequencing and projection replacement."""

    async def find_stream(self, document_id: str, base_analysis_id: str) -> EditStream | None:
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM analysis_edit_streams
                   WHERE document_id = ? AND base_analysis_id = ?""",
                (document_id, base_analysis_id),
            )
            row = await cursor.fetchone()
            return _stream(row) if row else None

    async def create_stream(self, stream: EditStream) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO analysis_edit_streams
                   (id, document_id, base_analysis_id, base_document_hash,
                    engine_version, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    stream.id,
                    stream.document_id,
                    stream.base_analysis_id,
                    stream.base_document_hash,
                    stream.engine_version,
                    str(stream.created_at),
                ),
            )
            await db.commit()

    async def list_commands(self, stream_id: str) -> list[StoredEditCommand]:
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM analysis_edit_commands
                   WHERE stream_id = ? ORDER BY sequence""",
                (stream_id,),
            )
            return [_command(row) for row in await cursor.fetchall()]

    async def find_working_copy(
        self, document_id: str, base_analysis_id: str
    ) -> WorkingCopy | None:
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM analysis_working_copies
                   WHERE document_id = ? AND base_analysis_id = ?""",
                (document_id, base_analysis_id),
            )
            row = await cursor.fetchone()
            return _working(row) if row else None

    async def save_commands_and_working_copy(
        self,
        *,
        stream: EditStream,
        commands: list[EditCommand],
        expected_sequence: int,
        working_copy: WorkingCopy,
        activate: bool = False,
    ) -> list[StoredEditCommand]:
        """Append commands and replace the projection under one write lock."""
        async with get_connection() as db:
            try:
                await db.execute("BEGIN IMMEDIATE")
                cursor = await db.execute(
                    """SELECT sequence, command_hash FROM analysis_edit_commands
                       WHERE stream_id = ? ORDER BY sequence DESC LIMIT 1""",
                    (stream.id,),
                )
                last = await cursor.fetchone()
                actual_sequence = int(last["sequence"]) if last else 0
                if actual_sequence != expected_sequence:
                    raise ValueError(
                        f"Edit stream changed: expected sequence {expected_sequence}, "
                        f"actual sequence {actual_sequence}"
                    )
                previous_hash = last["command_hash"] if last else ""
                saved: list[StoredEditCommand] = []
                for offset, command in enumerate(commands, start=1):
                    sequence = actual_sequence + offset
                    payload = json.dumps(command.payload, sort_keys=True, separators=(",", ":"))
                    command_hash = _hash_command(
                        previous_hash, sequence, command.command_type, command.command_version, payload
                    )
                    record_id = uuid.uuid4().hex
                    created = datetime.now(UTC)
                    await db.execute(
                        """INSERT INTO analysis_edit_commands
                           (id, stream_id, sequence, command_version, command_type,
                            payload_json, previous_hash, command_hash, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            record_id,
                            stream.id,
                            sequence,
                            command.command_version,
                            command.command_type,
                            payload,
                            previous_hash or None,
                            command_hash,
                            str(created),
                        ),
                    )
                    saved.append(StoredEditCommand(record_id, stream.id, sequence, command, command_hash, created))
                    previous_hash = command_hash

                await db.execute(
                    """INSERT INTO analysis_working_copies
                       (document_id, stream_id, base_analysis_id, applied_through_sequence,
                        document_json, content_markdown, content_html, pages_json,
                        editor_model_json, command_stream_hash, result_hash, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(stream_id) DO UPDATE SET
                         base_analysis_id=excluded.base_analysis_id,
                         applied_through_sequence=excluded.applied_through_sequence,
                         document_json=excluded.document_json,
                         content_markdown=excluded.content_markdown,
                         content_html=excluded.content_html,
                         pages_json=excluded.pages_json,
                         editor_model_json=excluded.editor_model_json,
                         command_stream_hash=excluded.command_stream_hash,
                         result_hash=excluded.result_hash,
                         updated_at=excluded.updated_at""",
                    (
                        working_copy.document_id,
                        working_copy.stream_id,
                        working_copy.base_analysis_id,
                        working_copy.applied_through_sequence,
                        working_copy.document_json,
                        working_copy.content_markdown,
                        working_copy.content_html,
                        working_copy.pages_json,
                        working_copy.editor_model_json,
                        working_copy.command_stream_hash,
                        working_copy.result_hash,
                        str(working_copy.updated_at),
                    ),
                )
                if activate:
                    await db.execute(
                        """UPDATE documents
                           SET active_analysis_id = ?, active_edit_stream_id = ?
                           WHERE id = ?""",
                        (stream.base_analysis_id, stream.id, stream.document_id),
                    )
                await db.commit()
                return saved
            except Exception:
                await db.rollback()
                raise

    async def replace_working_copy(self, working_copy: WorkingCopy) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT INTO analysis_working_copies
                   (document_id, stream_id, base_analysis_id, applied_through_sequence,
                    document_json, content_markdown, content_html, pages_json,
                    editor_model_json, command_stream_hash, result_hash, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(stream_id) DO UPDATE SET
                    base_analysis_id=excluded.base_analysis_id,
                    applied_through_sequence=excluded.applied_through_sequence,
                    document_json=excluded.document_json, content_markdown=excluded.content_markdown,
                    content_html=excluded.content_html, pages_json=excluded.pages_json,
                    editor_model_json=excluded.editor_model_json,
                    command_stream_hash=excluded.command_stream_hash,
                    result_hash=excluded.result_hash, updated_at=excluded.updated_at""",
                (
                    working_copy.document_id,
                    working_copy.stream_id,
                    working_copy.base_analysis_id,
                    working_copy.applied_through_sequence,
                    working_copy.document_json,
                    working_copy.content_markdown,
                    working_copy.content_html,
                    working_copy.pages_json,
                    working_copy.editor_model_json,
                    working_copy.command_stream_hash,
                    working_copy.result_hash,
                    str(working_copy.updated_at),
                ),
            )
            await db.commit()


def _hash_command(previous: str, sequence: int, kind: str, version: int, payload: str) -> str:
    import hashlib

    raw = f"{previous}|{sequence}|{kind}|{version}|{payload}".encode()
    return hashlib.sha256(raw).hexdigest()
