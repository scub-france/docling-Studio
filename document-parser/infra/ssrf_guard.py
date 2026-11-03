"""SSRF guard for user-supplied network targets.

Shared by the Ollama host probe (MAJ-08a, 0.7.0) and the per-store
connection URIs of OpenSearch and Neo4j (#audit-08, 0.7.4): both let a caller
of the API make the backend open a connection to an address of their choice.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_TARGET_REASON = "link-local/metadata/multicast/reserved/unspecified"


def resolved_target_is_blocked(url: str) -> bool:
    """Whether `url`'s host resolves to an address no legitimate target uses.

    The legitimate targets — an Ollama daemon, an OpenSearch cluster, a Neo4j
    server — live on loopback or the LAN by default
    (`http://localhost:11434`, `bolt://neo4j:7687`), so we deliberately DO NOT
    block loopback or the RFC1918 private ranges: doing so would break the
    normal features. We only reject addresses that are never a legitimate
    target:
      - link-local (covers the cloud metadata endpoint 169.254.169.254 and
        fe80::/10),
      - multicast,
      - reserved,
      - unspecified (0.0.0.0, ::).

    Loopback is allowed explicitly and takes precedence: IPv6 `::1` is flagged
    `is_reserved` by `ipaddress`, so without this guard `localhost` (which
    resolves to `::1` on most hosts) would be wrongly blocked. RFC1918 private
    addresses carry none of the four blocked flags, so they pass through
    naturally without an explicit allow (unlike `is_private`, which in the
    stdlib also covers 169.254.0.0/16 and would let the metadata endpoint slip
    past — so we must not allow-gate on it).

    Any URL scheme with a network location works (`http`, `https`, `bolt`,
    `neo4j+s`, ...). Resolution failures (including a name IDNA cannot
    encode) are treated as "not blocked": the caller then lets its client
    surface the connection error. The name is resolved here once; one
    re-pointed between this check and the client's own lookup is not caught.
    Returns True when at least one resolved address falls in a blocked class.
    """
    hostname = urlparse(url).hostname
    if not hostname:
        return False
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError):
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_loopback:
            continue
        if ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True
    return False
