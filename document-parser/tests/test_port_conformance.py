"""Each adapter implements its whole port, with the port's signatures.

The ports are structural `Protocol`s and nothing type-checks the code base,
so a port can fall behind what its services call (audit 0.7.4, 06 MAJ-2) and
an adapter can drift from its port without any test failing. This checks
both directions the cheap way: every member a port declares exists on the
adapter, with the same parameters (names, kinds, which ones have a default).
"""

from __future__ import annotations

import inspect

import pytest

from domain import ports
from infra.neo4j.driver_pool import Neo4jDriverPool
from infra.opensearch_pool import OpenSearchClientPool
from infra.opensearch_store import OpenSearchStore
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.chunk_edit_repo import SqliteChunkEditRepository, SqliteChunkPushRepository
from persistence.chunk_repo import SqliteChunkRepository
from persistence.document_repo import SqliteDocumentRepository
from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
from persistence.document_version_repo import SqliteDocumentVersionRepository
from persistence.store_repo import SqliteStoreRepository

PAIRS = [
    (ports.DocumentRepository, SqliteDocumentRepository),
    (ports.StoreRepository, SqliteStoreRepository),
    (ports.DocumentStoreLinkRepository, SqliteDocumentStoreLinkRepository),
    (ports.ChunkRepository, SqliteChunkRepository),
    (ports.ChunkEditRepository, SqliteChunkEditRepository),
    (ports.ChunkPushRepository, SqliteChunkPushRepository),
    (ports.DocumentVersionRepository, SqliteDocumentVersionRepository),
    (ports.AnalysisRepository, SqliteAnalysisRepository),
    (ports.VectorStore, OpenSearchStore),
    (ports.VectorStorePool, OpenSearchClientPool),
    (ports.GraphDriverPool, Neo4jDriverPool),
]


def _port_members(port: type) -> list[str]:
    return [
        name
        for name, value in vars(port).items()
        if not name.startswith("_") and inspect.isfunction(value)
    ]


def _params(fn) -> list[tuple[str, inspect._ParameterKind, bool]]:
    """(name, kind, has a default) per parameter: what decides whether a call
    written against the port binds on the adapter. The default *value* may
    differ — `OpenSearchStore.get_chunks` resolves `limit=None` to its pool's
    configured limit."""
    return [
        (p.name, p.kind, p.default is not inspect.Parameter.empty)
        for p in inspect.signature(fn).parameters.values()
    ]


@pytest.mark.parametrize(("port", "adapter"), PAIRS, ids=lambda c: c.__name__)
def test_adapter_implements_every_port_member(port: type, adapter: type):
    missing = [name for name in _port_members(port) if not hasattr(adapter, name)]
    assert not missing, f"{adapter.__name__} lacks {port.__name__} members: {missing}"


@pytest.mark.parametrize(("port", "adapter"), PAIRS, ids=lambda c: c.__name__)
def test_port_signatures_are_a_prefix_of_the_adapter(port: type, adapter: type):
    """Same parameters, in order; the adapter may add trailing keyword-only
    options with a default (e.g. `OpenSearchClientPool.get(verify_certs=)`)."""
    for name in _port_members(port):
        declared = _params(getattr(port, name))
        actual = _params(getattr(adapter, name))
        assert actual[: len(declared)] == declared, (
            f"{adapter.__name__}.{name}{actual} does not match {port.__name__}.{name}{declared}"
        )
        extra = actual[len(declared) :]
        assert all(
            kind is inspect.Parameter.KEYWORD_ONLY and has_default for _, kind, has_default in extra
        ), f"{adapter.__name__}.{name} adds a required parameter: {extra}"
