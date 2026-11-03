"""Reading timestamp columns back (#audit-05).

The application writes every timestamp as `str()` of an aware UTC
`datetime`, but SQLite's own defaults (`datetime('now')` on `documents`,
`stores`, `analysis_jobs`) and the `updated_at` triggers write naive UTC
text. Every repository reads both through this module, so a timestamp
leaving persistence is always an aware UTC `datetime`.
"""

from __future__ import annotations

from datetime import UTC, datetime


def parse_iso(value: str | datetime | None) -> datetime | None:
    """An aware UTC `datetime` from an ISO-8601 column value, None when empty.

    Naive values are read as UTC (what both writers mean); values carrying
    another offset are converted to UTC, same instant.
    """
    if value is None or value == "":
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_required_iso(value: str | datetime | None, *, column: str) -> datetime:
    """`parse_iso` for a NOT NULL column: an empty value is corrupt data.

    Raises `ValueError` naming `column` rather than inventing a date — the
    repositories used to fall back to "now", which rewrote audit dates.
    """
    parsed = parse_iso(value)
    if parsed is None:
        raise ValueError(f"empty timestamp in NOT NULL column {column!r}")
    return parsed
