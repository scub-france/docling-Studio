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
    When unset, env-var fallbacks (`OPENSEARCH_URL`, `NEO4J_URI`,
    `NEO4J_USER`, `NEO4J_PASSWORD`) supply the values — this keeps
    the seeded `default` store working on installs that haven't
    filled the connection form yet.

The fallback is a transitional convenience. Long-term every store
will carry its own connection identity; the env vars become a default
pre-fill for the create-store UI, not a runtime authority. See #279
acceptance criteria.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.value_objects import StoreKind

if TYPE_CHECKING:
    from domain.models import Store
    from infra.neo4j.driver import Neo4jDriver
    from infra.neo4j.driver_pool import Neo4jDriverPool
    from infra.opensearch_pool import OpenSearchClientPool
    from infra.opensearch_store import OpenSearchStore
    from persistence.store_repo import SqliteStoreRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionTargets:
    """Resolved backends for a single ingest call.

    Exactly one of `vector_store` / `neo4j_driver` is non-None today
    (a store has one kind). Carrying both as Optional makes the
    dispatch shape uniform with the legacy multi-backend ingest path
    inside `IngestionService.ingest`.
    """

    vector_store: OpenSearchStore | None = None
    neo4j_driver: Neo4jDriver | None = None


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
        store_repo: SqliteStoreRepository,
        neo4j_pool: Neo4jDriverPool,
        opensearch_pool: OpenSearchClientPool,
        env_neo4j_uri: str = "",
        env_neo4j_user: str = "neo4j",
        env_neo4j_password: str = "",
        env_opensearch_url: str = "",
    ) -> None:
        self._stores = store_repo
        self._neo4j_pool = neo4j_pool
        self._opensearch_pool = opensearch_pool
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
        user = store.connection_username or self._env_neo4j_user
        password = self._env_neo4j_password
        if store.has_connection_password:
            stored = await self._stores.get_connection_password(store.id)
            if stored is not None:
                password = stored
        # The store can pin a specific Neo4j database via config; falls
        # back to the cluster default "neo4j" when unspecified.
        database = (store.config or {}).get("database", "neo4j")
        driver = await self._neo4j_pool.get(uri, user, password, database=database)
        return IngestionTargets(neo4j_driver=driver)
