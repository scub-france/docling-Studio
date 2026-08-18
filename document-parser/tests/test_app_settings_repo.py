"""Tests for `SqliteAppSettingsRepository` — the namespaced runtime-config
override store (#317). Temp-file SQLite, same fixture pattern as
`test_repos.py`."""

from __future__ import annotations

import pytest

from persistence.app_settings_repo import SqliteAppSettingsRepository
from persistence.database import init_db


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    """Use a temp file SQLite database for all repo tests."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()


@pytest.fixture
def repo():
    return SqliteAppSettingsRepository()


class TestAppSettingsRepo:
    async def test_get_namespace_empty(self, repo):
        assert await repo.get_namespace("reasoning") == {}

    async def test_set_many_and_get(self, repo):
        await repo.set_many("reasoning", {"enabled": "true", "model_id": "granite3.3:8b"})

        rows = await repo.get_namespace("reasoning")
        assert rows == {"enabled": "true", "model_id": "granite3.3:8b"}

    async def test_set_many_upserts_existing_keys(self, repo):
        await repo.set_many("reasoning", {"enabled": "true"})
        await repo.set_many("reasoning", {"enabled": "false", "model_id": "m"})

        rows = await repo.get_namespace("reasoning")
        assert rows == {"enabled": "false", "model_id": "m"}

    async def test_set_many_empty_is_noop(self, repo):
        await repo.set_many("reasoning", {})
        assert await repo.get_namespace("reasoning") == {}

    async def test_namespaces_are_isolated(self, repo):
        await repo.set_many("reasoning", {"enabled": "true"})
        await repo.set_many("other", {"enabled": "false"})

        assert await repo.get_namespace("reasoning") == {"enabled": "true"}
        assert await repo.get_namespace("other") == {"enabled": "false"}

    async def test_delete_namespace_returns_count_and_spares_others(self, repo):
        await repo.set_many("reasoning", {"a": "1", "b": "2"})
        await repo.set_many("other", {"c": "3"})

        removed = await repo.delete_namespace("reasoning")

        assert removed == 2
        assert await repo.get_namespace("reasoning") == {}
        assert await repo.get_namespace("other") == {"c": "3"}

    async def test_delete_empty_namespace_returns_zero(self, repo):
        assert await repo.delete_namespace("reasoning") == 0
