"""SQLite adapter for durable analysis edit streams and their cache."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from domain.analysis_editing import (
    AnalysisEditConflictError,
    EditCommand,
    EditedAnalysisCache,
    EditStream,
    StoredEditCommand,
)
from persistence.database import get_connection


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _stream(row) -> EditStream:
    return EditStream(
        analysis_id=row["analysis_id"],
        base_document_hash=row["base_document_hash"],
        engine_version=row["engine_version"],
        created_at=_dt(row["created_at"]),
    )


def _command(row) -> StoredEditCommand:
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
        created_at=_dt(row["created_at"]),
    )


def _cache(row) -> EditedAnalysisCache:
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
        updated_at=_dt(row["updated_at"]),
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


def _cache_values(cache: EditedAnalysisCache) -> tuple:
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


class SqliteAnalysisEditRepository:
    """One transaction owns command sequencing and cache replacement."""

    async def find_stream(self, analysis_id: str) -> EditStream | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM analysis_edit_streams WHERE analysis_id = ?", (analysis_id,)
            )
            row = await cursor.fetchone()
            return _stream(row) if row else None

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
            return [_command(row) for row in await cursor.fetchall()]

    async def find_cache(self, analysis_id: str) -> EditedAnalysisCache | None:
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT * FROM edited_analysis_cache WHERE analysis_id = ?", (analysis_id,)
            )
            row = await cursor.fetchone()
            return _cache(row) if row else None

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
                cursor = await db.execute(
                    """SELECT sequence, command_hash FROM analysis_edit_commands
                       WHERE analysis_id = ? ORDER BY sequence DESC LIMIT 1""",
                    (stream.analysis_id,),
                )
                last = await cursor.fetchone()
                actual_sequence = int(last["sequence"]) if last else 0
                if actual_sequence != expected_sequence:
                    raise AnalysisEditConflictError(
                        f"Edit stream changed: expected sequence {expected_sequence}, "
                        f"actual sequence {actual_sequence}"
                    )
                previous_hash = last["command_hash"] if last else ""
                saved: list[StoredEditCommand] = []
                for offset, command in enumerate(commands, start=1):
                    sequence = actual_sequence + offset
                    payload = json.dumps(command.payload, sort_keys=True, separators=(",", ":"))
                    command_hash = _hash_command(
                        previous_hash,
                        sequence,
                        command.command_type,
                        command.command_version,
                        payload,
                    )
                    record_id = uuid.uuid4().hex
                    created = datetime.now(UTC)
                    await db.execute(
                        """INSERT INTO analysis_edit_commands
                           (id, analysis_id, sequence, command_version, command_type,
                            payload_json, previous_hash, command_hash, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            record_id,
                            stream.analysis_id,
                            sequence,
                            command.command_version,
                            command.command_type,
                            payload,
                            previous_hash or None,
                            command_hash,
                            str(created),
                        ),
                    )
                    saved.append(
                        StoredEditCommand(
                            record_id, stream.analysis_id, sequence, command, command_hash, created
                        )
                    )
                    previous_hash = command_hash

                await db.execute(_CACHE_UPSERT, _cache_values(cache))
                await db.commit()
                return saved
            except Exception:
                await db.rollback()
                raise

    async def replace_cache(self, cache: EditedAnalysisCache) -> None:
        async with get_connection() as db:
            await db.execute(_CACHE_UPSERT, _cache_values(cache))
            await db.commit()


def _hash_command(previous: str, sequence: int, kind: str, version: int, payload: str) -> str:
    import hashlib

    raw = f"{previous}|{sequence}|{kind}|{version}|{payload}".encode()
    return hashlib.sha256(raw).hexdigest()
