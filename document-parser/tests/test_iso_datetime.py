"""The one datetime decoder shared by the repositories (#396)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from persistence.iso_datetime import parse_iso, require_iso


def test_naive_sqlite_timestamps_are_read_as_utc():
    assert parse_iso("2026-11-13 10:00:00") == datetime(2026, 11, 13, 10, tzinfo=UTC)


def test_offsets_written_by_python_are_kept():
    plus_two = timezone(timedelta(hours=2))

    assert parse_iso("2026-11-13T10:00:00+02:00") == datetime(2026, 11, 13, 10, tzinfo=plus_two)


def test_datetime_values_are_made_aware():
    assert parse_iso(datetime(2026, 11, 13, 10)) == datetime(2026, 11, 13, 10, tzinfo=UTC)


@pytest.mark.parametrize("empty", [None, ""])
def test_empty_values_are_none(empty):
    assert parse_iso(empty) is None


def test_required_columns_reject_empty_values():
    with pytest.raises(ValueError, match="Expected a stored datetime"):
        require_iso("")
