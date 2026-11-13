"""Datetime decoding shared by the SQLite repositories (#396).

SQLite stores datetimes as ISO-8601 text. Rows written by `datetime('now')`
carry no offset, rows written from Python carry `+00:00`; both are UTC, so
a naive value is read as UTC and every datetime leaving a repository is
timezone-aware.
"""

from __future__ import annotations

from datetime import UTC, datetime


def parse_iso(value: str | datetime | None) -> datetime | None:
    """Decode a stored datetime; None or an empty string give None."""
    if value is None or value == "":
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def require_iso(value: str | datetime) -> datetime:
    """Decode a datetime from a NOT NULL column."""
    parsed = parse_iso(value)
    if parsed is None:
        raise ValueError("Expected a stored datetime, got an empty value")
    return parsed
