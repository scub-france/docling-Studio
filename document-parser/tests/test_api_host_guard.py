"""`Host` check on `/api/*` (08 MAJ: DNS rebinding against a local instance).

Exercised on a throwaway app, like the MCP transport tests, so the
assertions are about the guard and not about the backend booting.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infra.host_guard import (
    ApiHostGuardMiddleware,
    describe_host_check,
    is_allowed_host,
    is_host_check_on,
    split_host,
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


class TestMiddleware:
    def test_serves_a_listed_host(self):
        response = _get(["studio.example.com"], "http://studio.example.com")
        assert response.status_code == 200

    def test_rejects_a_foreign_host_with_421(self):
        response = _get(["studio.example.com"], "http://evil.example.com")
        assert response.status_code == 421
        assert response.text == "Invalid Host header"

    def test_loopback_is_always_allowed(self):
        for base in ("http://localhost:8000", "http://127.0.0.1"):
            assert _get(["studio.example.com"], base).status_code == 200, base

    def test_ipv6_loopback_is_allowed(self):
        # The test client cannot build an IPv6 base URL: send the Host header itself.
        with TestClient(_app(["studio.example.com"])) as client:
            response = client.get("/api/documents", headers={"host": "[::1]:8000"})
        assert response.status_code == 200

    def test_health_answers_a_container_health_check(self):
        response = _get(["studio.example.com"], "http://127.0.0.1:8000", "/api/health")
        assert response.status_code == 200

    def test_health_is_still_checked_for_a_foreign_host(self):
        response = _get(["studio.example.com"], "http://evil.example.com", "/api/health")
        assert response.status_code == 421

    def test_paths_outside_api_are_not_checked(self):
        response = _get(["studio.example.com"], "http://evil.example.com", "/outside")
        assert response.status_code == 200

    def test_a_port_wildcard_accepts_the_name_behind_nginx(self):
        # nginx forwards `/api` with `Host $host`, which drops the port.
        assert _get(["studio.lan:*"], "http://studio.lan").status_code == 200
        assert _get(["studio.lan:*"], "http://studio.lan:3000").status_code == 200

    def test_an_exact_pattern_wants_the_same_port(self):
        assert _get(["studio.lan:3000"], "http://studio.lan:3000").status_code == 200
        assert _get(["studio.lan:3000"], "http://studio.lan:8080").status_code == 421


class TestIsAllowedHost:
    @pytest.mark.parametrize(
        ("host", "expected"),
        [
            ("studio.lan", True),
            ("STUDIO.LAN:3000", True),
            ("evil.example.com", False),
            ("studio.lan.evil.com", False),
            ("localhost", True),
            ("[::1]:3000", True),
            ("", False),
            (None, False),
        ],
    )
    def test_matches_like_the_mcp_allow_list(self, host, expected):
        assert is_allowed_host(host, ["studio.lan:*"]) is expected

    def test_wildcard_allows_everything(self):
        assert is_allowed_host("evil.example.com", ["*"]) is True

    def test_split_host_keeps_ipv6_brackets(self):
        assert split_host("[::1]:8000") == ("[::1]", "8000")
        assert split_host("Example.com") == ("example.com", None)


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
        assert line == "API Host check on: /api accepts loopback and studio.lan:*"


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
