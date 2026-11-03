"""Resolve a `Store` entity to its concrete ingestion backend (#279).

Sits at the boundary between the per-store CRUD world (services /
persistence) and the per-connection driver pools (infra). Given a
`Store`, the resolver returns the right (vector_store, neo4j_driver)
pair so the IngestionService can write to the correct physical
target.

Resolution policy:

  - `kind = opensearch` → resolves to an `OpenSearchStore` from the
    OpenSearch pool. The pool key is `(url, username)`, where
    `username` may be None for anonymous clusters.
  - `kind = neo4j` → resolves to a `Neo4jDriver` from the Neo4j pool.
    The pool key is `(uri, user)`.
  - `connection_uri` / `connection_username` on the store entity win.
    When unset, env-var fallbacks (`OPENSEARCH_URL`, `NEO4J_URI`)
    supply the URI — this keeps the seeded `default` store working on
    installs that haven't filled the connection form yet.
  - `NEO4J_USER` / `NEO4J_PASSWORD` are only ever sent to `NEO4J_URI`
    (#audit-08): a store whose own URI points elsewhere must carry its
    own password, or it is not resolved at all. A store's URI is chosen
    by whoever calls the API, so falling back to the operator's
    credentials for it would hand them to any server the caller names.
    OpenSearch has no credential fallback: a store authenticates with
    its own credentials or not at all.

The URI fallback is a transitional convenience. Long-term every store
will carry its own connection identity; the env vars become a default
pre-fill for the create-store UI, not a runtime authority. See #279
acceptance criteria.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from domain.value_objects import StoreKind

if TYPE_CHECKING:
    from domain.models import Store
    from domain.ports import (
        GraphDriverPool,
        GraphWriter,
        StoreRepository,
        VectorStore,
        VectorStorePool,
    )

logger = logging.getLogger(__name__)

# The Neo4j driver's own defaults: the port of every bolt/neo4j scheme, and
# the built-in admin user a store's password goes with when it names none.
_NEO4J_DEFAULT_PORT = 7687
_NEO4J_DEFAULT_USER = "neo4j"


def _neo4j_endpoint(uri: str) -> tuple[str, str, int] | None:
    """The `(scheme, host, port)` a Neo4j URI connects to; None if unparseable.

    The port defaults as the driver's does. The scheme stays part of the
    endpoint: `bolt+s://` and `bolt://` on the same host differ in whether the
    password crosses the network in clear. The host is compared as written
    (lowercased): `localhost` and `127.0.0.1` are different endpoints, which
    errs on the side of not sending the credentials.
    """
    try:
        parts = urlsplit(uri.strip())
        port = parts.port
    except ValueError:
        return None
    if not parts.scheme or not parts.hostname:
        return None
    return (
        parts.scheme.lower(),
        parts.hostname,
        port if port is not None else _NEO4J_DEFAULT_PORT,
    )


@dataclass(frozen=True)
class IngestionTargets:
    """Resolved backends for a single ingest call.

    Exactly one of `vector_store` / `graph_writer` is non-None today
    (a store has one kind). Carrying both as Optional makes the
    dispatch shape uniform with the legacy multi-backend ingest path
    inside `IngestionService.ingest`. The Neo4j-backed `graph_writer`
    is now a domain-port handle (#audit-01) — the resolver owns the
    `Neo4jDriver` -> `Neo4jGraphWriter` wrap so the service layer
    never sees the raw driver.
    """

    vector_store: VectorStore | None = None
    graph_writer: GraphWriter | None = None


class StoreBackendNotConfiguredError(RuntimeError):
    """Raised when a store cannot be resolved to a usable backend.

    Concrete causes: store has `kind=neo4j` but no `connection_uri`
    and no `NEO4J_URI` env fallback; analogous for OpenSearch. The
    message names the missing piece so the API layer can pass it
    through to the user.
    """


class StoreBackendResolver:
    """Turn a `Store` entity into the concrete backend(s) for ingestion."""

    def __init__(
        self,
        *,
        store_repo: StoreRepository,
        neo4j_pool: GraphDriverPool,
        opensearch_pool: VectorStorePool,
        graph_writer_factory: Callable[[Any], GraphWriter],
        env_neo4j_uri: str = "",
        env_neo4j_user: str = "neo4j",
        env_neo4j_password: str = "",
        env_opensearch_url: str = "",
    ) -> None:
        self._stores = store_repo
        self._neo4j_pool = neo4j_pool
        self._opensearch_pool = opensearch_pool
        # Injected by main.py with `Neo4jGraphWriter` — kept here as an
        # opaque factory so services/ never has to runtime-import infra
        # (#audit-01). The factory takes a Neo4jDriver and returns a port.
        self._make_graph_writer = graph_writer_factory
        self._env_neo4j_uri = env_neo4j_uri
        self._env_neo4j_user = env_neo4j_user
        self._env_neo4j_password = env_neo4j_password
        self._env_opensearch_url = env_opensearch_url

    async def resolve(self, store: Store) -> IngestionTargets:
        """Return the backend pair for `store`.

        Raises `StoreBackendNotConfiguredError` when neither the store
        nor the env fallback supplies the connection details required
        for `store.kind`.
        """
        if store.kind == StoreKind.OPENSEARCH:
            return await self._resolve_opensearch(store)
        if store.kind == StoreKind.NEO4J:
            return await self._resolve_neo4j(store)
        raise StoreBackendNotConfiguredError(
            f"Unknown store kind: {store.kind!r} (store={store.slug})"
        )

    async def _resolve_opensearch(self, store: Store) -> IngestionTargets:
        url = store.connection_uri or self._env_opensearch_url
        if not url:
            raise StoreBackendNotConfiguredError(
                f"Store {store.slug!r} has kind=opensearch but no connection URL "
                "(set `connection_uri` on the store or OPENSEARCH_URL in the "
                "backend environment)."
            )
        username = store.connection_username or None
        password: str | None = None
        if store.has_connection_password:
            password = await self._stores.get_connection_password(store.id)
        client = await self._opensearch_pool.get(url, username=username, password=password)
        return IngestionTargets(vector_store=client)

    async def _resolve_neo4j(self, store: Store) -> IngestionTargets:
        uri = store.connection_uri or self._env_neo4j_uri
        if not uri:
            raise StoreBackendNotConfiguredError(
                f"Store {store.slug!r} has kind=neo4j but no connection URI "
                "(set `connection_uri` on the store or NEO4J_URI in the "
                "backend environment)."
            )
        user, password = await self._neo4j_credentials(store, uri)
        # The store can pin a specific Neo4j database via config; falls
        # back to the cluster default "neo4j" when unspecified.
        database = (store.config or {}).get("database", "neo4j")
        driver = await self._neo4j_pool.get(uri, user, password, database=database)
        # Wrap the raw driver in the injected `GraphWriter` factory so the
        # IngestionService consumes a port, not infra.
        return IngestionTargets(graph_writer=self._make_graph_writer(driver))

    async def _neo4j_credentials(self, store: Store, uri: str) -> tuple[str, str]:
        """The `(user, password)` to open `uri` with, for `store` (#audit-08).

        The store's own credentials win. `NEO4J_USER` / `NEO4J_PASSWORD` fill
        in only when `uri` is `NEO4J_URI` — same scheme, host and port: a
        store URI is chosen by the API caller, and the env password must never
        reach a server they pick. Elsewhere, a store without its own password
        is refused before any connection.
        """
        stored: str | None = None
        if store.has_connection_password:
            stored = await self._stores.get_connection_password(store.id)
        env_endpoint = _neo4j_endpoint(self._env_neo4j_uri)
        if env_endpoint is not None and _neo4j_endpoint(uri) == env_endpoint:
            user = store.connection_username or self._env_neo4j_user
            password = stored if stored is not None else self._env_neo4j_password
            return user, password
        if stored is None:
            raise StoreBackendNotConfiguredError(
                f"Store {store.slug!r} connects to its own URI, not the backend's NEO4J_URI, "
                "and has no password of its own: credentials required. Set the store's "
                "password (and username, if not 'neo4j'); NEO4J_USER and NEO4J_PASSWORD "
                "are only sent to NEO4J_URI."
            )
        return store.connection_username or _NEO4J_DEFAULT_USER, stored
