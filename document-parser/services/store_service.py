"""Store service — CRUD orchestration for ingestion targets (#251).

Sits between the API layer and the SQLite repositories. Owns:
- input validation (per-kind config schema, slug shape, name uniqueness)
- single-default invariant (only one Store can be `is_default = True`)
- delete safety (refuse on seeded `default` slug or non-empty links)
- list enrichment (per-store document counts read from
  `document_store_links`)
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.models import Store
from domain.value_objects import StoreKind

if TYPE_CHECKING:
    from persistence.document_repo import SqliteDocumentRepository
    from persistence.document_store_link_repo import SqliteDocumentStoreLinkRepository
    from persistence.store_repo import SqliteStoreRepository
    from services.store_backend_resolver import StoreBackendResolver

logger = logging.getLogger(__name__)


_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


class StoreServiceError(Exception):
    """Base service error. Carries an `http_status` hint for the API layer."""

    http_status: int = 400

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class StoreNotFoundError(StoreServiceError):
    http_status = 404


class StoreConflictError(StoreServiceError):
    http_status = 409


class StoreValidationError(StoreServiceError):
    http_status = 422


@dataclass
class StoreInfoView:
    """Read model for `GET /api/stores`. Mirrors the frontend `StoreInfo`."""

    name: str
    slug: str
    kind: str
    embedder: str
    is_default: bool
    document_count: int
    chunk_count: int
    connected: bool
    error_message: str | None = None


@dataclass
class StoreDocEntryView:
    """Read model for `GET /api/stores/{slug}/documents`."""

    doc_id: str
    filename: str
    state: str
    chunk_count: int
    pushed_at: str | None


def _validate_slug(slug: str) -> None:
    if not slug or not _SLUG_PATTERN.match(slug):
        raise StoreValidationError(
            "slug must be lowercase alphanumeric with optional dashes (e.g. 'rh-corpus-v3')"
        )


_NEO4J_URI_SCHEMES = (
    "bolt://",
    "bolt+s://",
    "bolt+ssc://",
    "neo4j://",
    "neo4j+s://",
    "neo4j+ssc://",
)
_OPENSEARCH_URI_SCHEMES = ("http://", "https://")


def _normalise_optional(value: str | None) -> str | None:
    """Return None for empty / whitespace-only input; trimmed value otherwise."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalise_uri_for_kind(kind: StoreKind, value: str | None) -> str | None:
    """Validate the URI scheme against the store kind (#279).

    Empty / None values are allowed — the env-var fallback in the
    resolver covers stores without their own URI.
    """
    normalised = _normalise_optional(value)
    if normalised is None:
        return None
    if kind is StoreKind.NEO4J and not normalised.lower().startswith(_NEO4J_URI_SCHEMES):
        raise StoreValidationError(
            f"connection_uri must start with one of {', '.join(_NEO4J_URI_SCHEMES)} for Neo4j stores"
        )
    if kind is StoreKind.OPENSEARCH and not normalised.lower().startswith(_OPENSEARCH_URI_SCHEMES):
        raise StoreValidationError(
            "connection_uri must start with http:// or https:// for OpenSearch stores"
        )
    return normalised


def _validate_config_for_kind(kind: StoreKind, config: dict) -> None:
    """Per-kind config schema. New kinds plug in here without touching the
    rest of the pipeline. Authentication for remote stores comes from the
    deployment env (see `infra/settings.py`)."""
    if kind is StoreKind.OPENSEARCH:
        index_name = config.get("index_name") or config.get("indexName")
        if not isinstance(index_name, str) or not index_name.strip():
            raise StoreValidationError("OpenSearch config requires a non-empty 'index_name'")
    elif kind is StoreKind.NEO4J:
        index_name = config.get("index_name") or config.get("indexName")
        if not isinstance(index_name, str) or not index_name.strip():
            raise StoreValidationError("Neo4j config requires a non-empty 'index_name'")


class StoreService:
    """Orchestrates store CRUD on top of SQLite repositories."""

    def __init__(
        self,
        store_repo: SqliteStoreRepository,
        link_repo: SqliteDocumentStoreLinkRepository,
        document_repo: SqliteDocumentRepository | None = None,
        backend_resolver: StoreBackendResolver | None = None,
    ):
        self._stores = store_repo
        self._links = link_repo
        self._documents = document_repo
        # Optional — required by `test_connection`. When None, the
        # endpoint returns a 503-shaped failure rather than 500.
        self._backend_resolver = backend_resolver

    async def list_stores(self) -> list[StoreInfoView]:
        stores = await self._stores.find_all()
        views: list[StoreInfoView] = []
        for store in stores:
            links = await self._links.find_for_store(store.id)
            views.append(
                StoreInfoView(
                    name=store.name,
                    slug=store.slug,
                    kind=store.kind.value,
                    embedder=store.embedder,
                    is_default=store.is_default,
                    document_count=len(links),
                    chunk_count=0,
                    connected=True,
                )
            )
        return views

    async def get_by_slug(self, slug: str) -> Store:
        store = await self._stores.find_by_slug(slug)
        if store is None:
            raise StoreNotFoundError(f"Store '{slug}' not found")
        return store

    async def create_store(
        self,
        *,
        name: str,
        slug: str,
        kind: StoreKind,
        embedder: str,
        config: dict,
        is_default: bool = False,
        connection_uri: str | None = None,
        connection_username: str | None = None,
        connection_password: str | None = None,
    ) -> Store:
        name = (name or "").strip()
        slug = (slug or "").strip().lower()
        embedder = (embedder or "").strip()

        if not name:
            raise StoreValidationError("name is required")
        if not embedder:
            raise StoreValidationError("embedder is required")
        _validate_slug(slug)
        _validate_config_for_kind(kind, config)
        connection_uri = _normalise_uri_for_kind(kind, connection_uri)
        connection_username = _normalise_optional(connection_username)

        if await self._stores.find_by_slug(slug) is not None:
            raise StoreConflictError(f"slug '{slug}' is already in use")
        if await self._stores.find_by_name(name) is not None:
            raise StoreConflictError(f"name '{name}' is already in use")

        store = Store(
            id=str(uuid.uuid4()),
            name=name,
            slug=slug,
            kind=kind,
            embedder=embedder,
            config=config,
            connection_uri=connection_uri,
            connection_username=connection_username,
            is_default=is_default,
        )
        # Empty-string password → no seal at create-time (the column
        # stays NULL). Only a non-empty value triggers Fernet.
        seal_password = connection_password if connection_password else None
        await self._stores.insert(store, password=seal_password)
        if is_default:
            await self._stores.clear_default_except(store.id)
        # Re-read so `has_connection_password` reflects what landed.
        return await self._stores.find_by_id(store.id) or store

    async def update_store(
        self,
        slug: str,
        *,
        name: str | None = None,
        new_slug: str | None = None,
        kind: StoreKind | None = None,
        embedder: str | None = None,
        config: dict | None = None,
        is_default: bool | None = None,
        connection_uri: str | None = None,
        connection_username: str | None = None,
        connection_password: str | None = None,
    ) -> Store:
        store = await self.get_by_slug(slug)

        if name is not None:
            name = name.strip()
            if not name:
                raise StoreValidationError("name cannot be empty")
            other = await self._stores.find_by_name(name)
            if other is not None and other.id != store.id:
                raise StoreConflictError(f"name '{name}' is already in use")
            store.name = name

        if new_slug is not None:
            new_slug = new_slug.strip().lower()
            _validate_slug(new_slug)
            if new_slug != store.slug:
                other = await self._stores.find_by_slug(new_slug)
                if other is not None and other.id != store.id:
                    raise StoreConflictError(f"slug '{new_slug}' is already in use")
                store.slug = new_slug

        if kind is not None:
            store.kind = kind

        if embedder is not None:
            embedder = embedder.strip()
            if not embedder:
                raise StoreValidationError("embedder cannot be empty")
            store.embedder = embedder

        if config is not None:
            store.config = config

        # Validate the (kind, config) pair as a whole — even when only one of
        # the two changed, the combination must still satisfy the schema.
        _validate_config_for_kind(store.kind, store.config)

        if connection_uri is not None:
            store.connection_uri = _normalise_uri_for_kind(store.kind, connection_uri)
        if connection_username is not None:
            store.connection_username = _normalise_optional(connection_username)

        promote_default = False
        if is_default is not None:
            store.is_default = is_default
            promote_default = is_default

        await self._stores.update(store)

        # Password write is separate (#279). Three behaviours per the
        # DTO contract: None=untouched, ""=clear, other=replace.
        if connection_password is not None:
            cleared_or_replaced = connection_password if connection_password else None
            await self._stores.set_connection_password(store.id, cleared_or_replaced)

        if promote_default:
            await self._stores.clear_default_except(store.id)
        # Re-read so the response reflects the new sealed-flag state.
        return await self._stores.find_by_id(store.id) or store

    async def test_connection(self, slug: str) -> tuple[bool, str | None]:
        """Open a probe connection to the store's backend.

        Returns `(ok, error_message)`. Success means the resolver
        could build a driver/client AND the underlying ping returned
        OK. Failure modes:
          - `StoreBackendNotConfiguredError` → "no URI configured"
          - Driver/connection error → the exception message (passwords
            never appear in the message — we strip the password from
            the resolver before raising).
          - `_backend_resolver` not wired → ("connection probe not
            available", 503-shaped).
        """
        store = await self.get_by_slug(slug)
        if self._backend_resolver is None:
            return False, "connection probe not available (backend resolver not configured)"
        try:
            targets = await self._backend_resolver.resolve(store)
        except Exception as exc:
            return False, str(exc)
        try:
            if targets.vector_store is not None:
                ok = await targets.vector_store.ping()
                if not ok:
                    return False, "OpenSearch ping returned not-ok"
                return True, None
            if targets.neo4j_driver is not None:
                await targets.neo4j_driver.driver.verify_connectivity()
                return True, None
        except Exception as exc:
            return False, str(exc)
        return False, "no backend resolved for this store"

    async def list_documents(self, slug: str) -> list[StoreDocEntryView]:
        store = await self.get_by_slug(slug)
        links = await self._links.find_for_store(store.id)
        if self._documents is None:
            return [
                StoreDocEntryView(
                    doc_id=link.document_id,
                    filename=link.document_id,
                    state=link.state.value,
                    chunk_count=0,
                    pushed_at=str(link.last_push_at) if link.last_push_at else None,
                )
                for link in links
            ]
        entries: list[StoreDocEntryView] = []
        for link in links:
            doc = await self._documents.find_by_id(link.document_id)
            entries.append(
                StoreDocEntryView(
                    doc_id=link.document_id,
                    filename=doc.filename if doc else link.document_id,
                    state=link.state.value,
                    chunk_count=0,
                    pushed_at=str(link.last_push_at) if link.last_push_at else None,
                )
            )
        return entries

    async def remove_document(self, slug: str, doc_id: str) -> None:
        store = await self.get_by_slug(slug)
        removed = await self._links.delete(doc_id, store.id)
        if not removed:
            raise StoreNotFoundError(f"document '{doc_id}' is not linked to store '{slug}'")

    async def delete_store(self, slug: str) -> None:
        store = await self.get_by_slug(slug)
        if store.slug == "default":
            raise StoreConflictError(
                "the seeded 'default' store cannot be deleted",
                http_status=409,
            )
        links = await self._links.find_for_store(store.id)
        if links:
            raise StoreConflictError(
                f"store '{slug}' has {len(links)} linked document(s); remove the documents first",
                http_status=409,
            )
        await self._stores.delete(store.id)
