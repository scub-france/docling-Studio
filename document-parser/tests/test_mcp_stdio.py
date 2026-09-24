"""The stdio entry point reads Studio's database, wherever the client spawns it."""

from __future__ import annotations

import os
import subprocess
import sys

import mcp_stdio


def test_a_relative_db_path_is_the_backend_s_not_the_caller_s(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DB_PATH", raising=False)
    assert mcp_stdio.db_path() == mcp_stdio.BACKEND_DIR / "data" / "docling_studio.db"


def test_a_missing_database_stops_the_server_with_a_message(tmp_path):
    missing = tmp_path / "nope.db"
    run = subprocess.run(
        [sys.executable, str(mcp_stdio.BACKEND_DIR / "mcp_stdio.py")],
        cwd=tmp_path,
        env={**os.environ, "DB_PATH": str(missing)},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 1
    assert f"No Docling Studio database at {missing}" in run.stderr
    assert run.stdout == ""  # stdout is the protocol channel
    assert not missing.exists()
