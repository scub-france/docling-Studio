"""SQLite adapter for durable analysis edit streams and their cache."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from domain.analysis_editing import (
    STORED_SEQUENCE_CONFLICT,
    EditCommand,
    EditedAnalysisCache,
    EditStream,
    StoredEditCommand,
    check_expected_sequence,
    hash_command,
    serialize_command_payload,
)
from persistence.database import get_connection
from persistence.iso_datetime import require_iso


def _to_stream(row) -> EditStream:
    return EditStream(
        analysis_id=row["analysis_id"],
        base_document_hash=row["base_document_hash"],
        engine_version=row["engine_version"],
        created_at=require_iso(row["created_at"]),
    )


def _to_stored_command(row) -> StoredEditCommand:
    return StoredEditCommand(
        id=row["id"],
        analysis_id=row["analysis_id"],
        sequence=row["sequence"],
        command=EditCommand(
            command_type=row["command_type"],
            payload=json.loads(row["payload_json"]),
            command_version=row["command_version"],
        ),
        command_hash=row["command_hash"],
        created_at=require_iso(row["created_at"]),
    )


def _to_cache(row) -> EditedAnalysisCache:
    return EditedAnalysisCache(
        analysis_id=row["analysis_id"],
        applied_through_sequence=row["applied_through_sequence"],
        document_json=row["document_json"],
        content_markdown=row["content_markdown"],
        content_html=row["content_html"],
        pages_json=row["pages_json"],
        editor_model_json=row["editor_model_json"],
        command_stream_hash=row["command_stream_hash"],
        result_hash=row["result_hash"],
        updated_at=require_iso(row["updated_at"]),
    )


_CACHE_UPSERT = """INSERT INTO edited_analysis_cache
    (analysis_id, applied_through_sequence, document_json, content_markdown,
     content_html, pages_json, editor_model_json, command_stream_hash,
     result_hash, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(analysis_id) DO UPDATE SET
      applied_through_sequence=excluded.applied_through_sequence,
      document_json=excluded.document_json,
      content_markdown=excluded.content_markdown,
      content_html=excluded.content_html,
      pages_json=excluded.pages_json,
      editor_model_json=excluded.editor_model_json,
      command_stream_hash=excluded.command_stream_hash,
      result_hash=excluded.result_hash,
      updated_at=excluded.updated_at"""


def _to_cache_params(cache: EditedAnalysisCache) -> tuple:
    return (
        cache.analysis_id,
        cache.applied_through_sequence,
        cache.document_json,
        cache.content_markdown,
        cache.content_html,
        cache.pages_json,
        cache.editor_model_json,
        cache.command_stream_hash,
        cache.result_hash,
        str(cache.updated_at),
    )


async def _read_chain_tip(db, analysis_id: str) -> tuple[int, str]:
    """The last stored sequence and hash of a stream: (0, "") when it is empty."""
    cursor = await db.execute(
        """SELECT sequence, command_hash FROM analysis_edit_commands
           WHERE analysis_id = ? ORDER BY sequence DESC LIMIT 1""",
        (analysis_id,),
    )
    last = await cursor.fetchone()
    actual_sequence = int(last["sequence"]) if last else 0
    previous_hash = last["command_hash"] if last else ""
    return actual_sequence, previous_hash


def _chain_commands(
    analysis_id: str,
    commands: list[EditCommand],
    actual_sequence: int,
    previous_hash: str,
) -> tuple[list[tuple], list[StoredEditCommand]]:
    """Number and hash-chain `commands` after the tip: insert rows and stored records."""
    saved: list[StoredEditCommand] = []
    rows: list[tuple] = []
    for offset, command in enumerate(commands, start=1):
        sequence = actual_sequence + offset
        command_hash = hash_command(previous_hash, sequence, command)
        record_id = uuid.uuid4().hex
        created = datetime.now(UTC)
        rows.append(
            (
                record_id,
                analysis_id,
                sequence,
                command.command_version,
                command.command_type,
                serialize_command_payload(command.payload),
                previous_hash or None,
                command_hash,
                str(created),
            )
        )
        saved.append(
            StoredEditCommand(record_id, analysis_id, sequence, command, command_hash, created)
        )
        previous_hash = command_hash
    return rows, saved


class SqliteAnalysisEditRepository:
    """One transaction owns command sequencing and cache replacement."""

    async def find_stream(self, analysis_id: str) -> EditStream | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM analysis_edit_streams WHERE analysis_id = ?", (analysis_id,)
            )
            row = await cursor.fetchone()
            return _to_stream(row) if row else None

    async def create_stream(self, stream: EditStream) -> None:
        async with get_connection() as db:
            await db.execute(
                """INSERT OR IGNORE INTO analysis_edit_streams
                   (analysis_id, base_document_hash, engine_version, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    stream.analysis_id,
                    stream.base_document_hash,
                    stream.engine_version,
                    str(stream.created_at),
                ),
            )
            await db.commit()

    async def list_commands(self, analysis_id: str) -> list[StoredEditCommand]:
        async with get_connection() as db:
            cursor = await db.execute(
                """SELECT * FROM analysis_edit_commands
                   WHERE analysis_id = ? ORDER BY sequence""",
                (analysis_id,),
            )
            return [_to_stored_command(row) for row in await cursor.fetchall()]

    async def find_cache(self, analysis_id: str) -> EditedAnalysisCache | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM edited_analysis_cache WHERE analysis_id = ?", (analysis_id,)
            )
            row = await cursor.fetchone()
            return _to_cache(row) if row else None

    async def save_commands_and_cache(
        self,
        *,
        stream: EditStream,
        commands: list[EditCommand],
        expected_sequence: int,
        cache: EditedAnalysisCache,
    ) -> list[StoredEditCommand]:
        """Append commands and replace the cache under one write lock."""
        if cache.analysis_id != stream.analysis_id:
            raise ValueError("Cache and stream must belong to the same analysis")
        async with get_connection() as db:
            try:
                await db.execute("BEGIN IMMEDIATE")
                actual_sequence, previous_hash = await _read_chain_tip(db, stream.analysis_id)
                check_expected_sequence(
                    expected_sequence, actual_sequence, STORED_SEQUENCE_CONFLICT
                )
                rows, saved = _chain_commands(
                    stream.analysis_id, commands, actual_sequence, previous_hash
                )
                # One statement for the whole batch, still inside BEGIN IMMEDIATE.
                await db.executemany(
                    """INSERT INTO analysis_edit_commands
                       (id, analysis_id, sequence, command_version, command_type,
                        payload_json, previous_hash, command_hash, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    rows,
                )
                await db.execute(_CACHE_UPSERT, _to_cache_params(cache))
                await db.execute(
                    "UPDATE analysis_edit_streams SET engine_version = ? WHERE analysis_id = ?",
                    (stream.engine_version, stream.analysis_id),
                )
                await db.commit()
                return saved
            except Exception:
                await db.rollback()
                raise
