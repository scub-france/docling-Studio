"""Tests for `infra.ssrf_guard` — the SSRF guard shared by the Ollama probe
and the store connection URIs (#audit-08).

IP literals resolve without DNS, so these tests run offline. Name resolution
is patched where a name is needed.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from infra.ssrf_guard import resolved_target_is_blocked


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata (link-local)
        "http://2852039166/",  # the same address, written as one decimal
        "http://[::ffff:169.254.169.254]:9200",  # the same, IPv4-mapped IPv6
        "bolt://169.254.169.254:7687",  # any scheme with a host
        "neo4j+s://[fe80::1]:7687",  # IPv6 link-local
        "http://0.0.0.0:9200",  # unspecified
        "http://[::]:9200",
        "http://224.0.0.1/",  # multicast
    ],
)
def test_blocked_targets(url):
    assert resolved_target_is_blocked(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:9200",
        "http://127.0.0.1:11434",
        "http://[::1]:9200",  # loopback wins over `is_reserved`
        "http://10.0.0.5:9200",  # the LAN is where these services live
        "http://192.168.1.2:9200",
        "bolt://172.18.0.3:7687",
    ],
)
def test_loopback_and_private_targets_are_allowed(url):
    assert resolved_target_is_blocked(url) is False


def test_a_name_resolving_to_the_metadata_address_is_blocked():
    infos = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 0))]
    with patch("infra.ssrf_guard.socket.getaddrinfo", return_value=infos):
        assert resolved_target_is_blocked("bolt://innocent.example:7687") is True


def test_an_unresolvable_name_is_not_blocked():
    with patch("infra.ssrf_guard.socket.getaddrinfo", side_effect=socket.gaierror("nope")):
        assert resolved_target_is_blocked("http://does-not-exist.invalid:9200") is False


def test_a_name_idna_cannot_encode_is_not_blocked_and_does_not_raise():
    assert resolved_target_is_blocked(f"http://{'a' * 64}.example:9200") is False


def test_a_url_without_host_is_not_blocked():
    assert resolved_target_is_blocked("not a url") is False
