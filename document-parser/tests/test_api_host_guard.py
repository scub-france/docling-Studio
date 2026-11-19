"""`Host` check on `/api/*` (08 MAJ: DNS rebinding against a local instance).

Exercised on a throwaway app, like the MCP transport tests, so the
assertions are about the guard and not about the backend booting.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infra.host_guard import (
    ApiHostGuardMiddleware,
    describe_host_check,
    is_host_check_on,
    log_host_check,
    parse_host_name,
)
from infra.settings import Settings


def _app(allowed_hosts: list[str]) -> FastAPI:
    app = FastAPI()

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/documents")
    async def documents() -> list:
        return []

    @app.get("/outside")
    async def outside() -> dict:
        return {"ok": True}

    app.add_middleware(ApiHostGuardMiddleware, allowed_hosts=allowed_hosts)
    return app


def _get(allowed_hosts: list[str], base_url: str, path: str = "/api/documents"):
    with TestClient(_app(allowed_hosts), base_url=base_url) as client:
        return client.get(path)


def _status_for_host(allowed_hosts: list[str], host: str) -> int:
    # The test client builds `Host` from its base URL; send odd values by hand.
    with TestClient(_app(allowed_hosts)) as client:
        return client.get("/api/documents", headers={"host": host}).status_code


class TestMiddleware:
    def test_serves_a_listed_host(self):
        response = _get(["studio.example.com"], "http://studio.example.com")
        assert response.status_code == 200

    def test_rejects_a_foreign_host_with_421_and_a_json_detail(self):
        response = _get(["studio.example.com"], "http://evil.example.com")
        assert response.status_code == 421
        assert response.json() == {"detail": "Invalid Host header"}

    def test_a_rejection_is_logged_at_debug_only(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="infra.host_guard"):
            _get(["studio.example.com"], "http://evil.example.com")
        levels = [r.levelno for r in caplog.records if r.name == "infra.host_guard"]
        assert levels == [logging.DEBUG]

    def test_loopback_is_always_allowed(self):
        for base in ("http://localhost:8000", "http://127.0.0.1"):
            assert _get(["studio.example.com"], base).status_code == 200, base

    def test_ipv6_loopback_is_allowed(self):
        assert _status_for_host(["studio.example.com"], "[::1]:8000") == 200
        assert _status_for_host(["studio.example.com"], "[::1]") == 200

    def test_health_answers_a_container_health_check(self):
        response = _get(["studio.example.com"], "http://127.0.0.1:8000", "/api/health")
        assert response.status_code == 200

    def test_health_is_still_checked_for_a_foreign_host(self):
        response = _get(["studio.example.com"], "http://evil.example.com", "/api/health")
        assert response.status_code == 421

    def test_paths_outside_api_are_not_checked(self):
        response = _get(["studio.example.com"], "http://evil.example.com", "/outside")
        assert response.status_code == 200

    @pytest.mark.parametrize("entry", ["studio.lan", "studio.lan:*", "studio.lan:3000"])
    def test_the_port_of_an_entry_is_ignored(self, entry):
        # nginx forwards `/api` with `Host $host`, which drops the port.
        assert _get([entry], "http://studio.lan").status_code == 200
        assert _get([entry], "http://studio.lan:3000").status_code == 200
        assert _get([entry], "http://studio.lan:8080").status_code == 200

    @pytest.mark.parametrize(
        "host",
        [
            "localhost:80@evil.com",
            "[::1]evil",
            "[::1",
            "localhost:abc",
            "localhost:*",
            "localhost:",
            "localhost:123456",
            "local host",
            "localhost/x",
            "evil.com@localhost",
            "localhost.evil.com",
            "localhost.",
            "",
        ],
    )
    def test_a_malformed_or_foreign_host_is_refused(self, host):
        assert _status_for_host(["studio.lan"], host) == 421


class TestParseHostName:
    @pytest.mark.parametrize(
        ("host", "name"),
        [
            ("Studio.LAN:3000", "studio.lan"),
            ("studio.lan", "studio.lan"),
            ("[::1]:8000", "[::1]"),
            ("127.0.0.1", "127.0.0.1"),
            ("localhost:80@evil.com", None),
            ("[::1]evil", None),
            ("caf\xe9.lan", None),
            ("", None),
            (None, None),
        ],
    )
    def test_reads_the_name_or_refuses(self, host, name):
        assert parse_host_name(host) == name

    def test_a_port_wildcard_is_for_allow_list_entries_only(self):
        assert parse_host_name("studio.lan:*") is None
        assert parse_host_name("studio.lan:*", port_wildcard=True) == "studio.lan"


class TestStartupLine:
    def test_off_by_default(self):
        assert is_host_check_on([]) is False
        assert "off (API_ALLOWED_HOSTS unset)" in describe_host_check([])

    def test_off_with_the_wildcard(self):
        assert is_host_check_on(["*"]) is False
        assert "API_ALLOWED_HOSTS=*" in describe_host_check(["*"])

    def test_on_names_the_hosts(self):
        assert is_host_check_on(["studio.lan:*"]) is True
        line = describe_host_check(["studio.lan:*"])
        assert line == "API Host check on: /api accepts loopback, studio.lan"

    def test_names_only_the_hosts_kept(self):
        line = describe_host_check(["http://studio.lan", "studio.lan:3000", "*.example.com"])
        assert line == "API Host check on: /api accepts loopback, studio.lan"

    def test_warns_once_naming_each_ignored_entry(self, caplog):
        with caplog.at_level(logging.INFO, logger="infra.host_guard"):
            log_host_check(["http://studio.lan", "studio.lan", "*.example.com"])
        warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings == [
            "API_ALLOWED_HOSTS entries ignored, not a host name: http://studio.lan, *.example.com"
        ]
        assert "API Host check on: /api accepts loopback, studio.lan" in caplog.messages

    def test_no_warning_when_every_entry_is_kept_or_the_check_is_off(self, caplog):
        with caplog.at_level(logging.INFO, logger="infra.host_guard"):
            log_host_check(["studio.lan:*"])
            log_host_check(["*"])
            log_host_check([])
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


class TestSetting:
    def test_unset_means_no_check(self, monkeypatch):
        monkeypatch.delenv("API_ALLOWED_HOSTS", raising=False)
        assert Settings.from_env().api_allowed_hosts == []

    def test_empty_means_no_check(self, monkeypatch):
        monkeypatch.setenv("API_ALLOWED_HOSTS", "")
        assert Settings.from_env().api_allowed_hosts == []

    def test_comma_separated_like_mcp_allowed_hosts(self, monkeypatch):
        monkeypatch.setenv("API_ALLOWED_HOSTS", " localhost:* , studio.lan:3000 ,")
        assert Settings.from_env().api_allowed_hosts == ["localhost:*", "studio.lan:3000"]
