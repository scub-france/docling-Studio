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


def _validate_config_for_kind(kind: StoreKind, config: dict) -> None:
    """Per-kind config schema. Today only OpenSearch is wired; new kinds plug
    in here without touching the rest of the pipeline."""
    if kind is StoreKind.OPENSEARCH:
        index_name = config.get("index_name") or config.get("indexName")
        if not isinstance(index_name, str) or not index_name.strip():
            raise StoreValidationError("OpenSearch config requires a non-empty 'index_name'")
    # Future: add LlamaIndex / LangChain / pgvector branches here.


class StoreService:
    """Orchestrates store CRUD on top of SQLite repositories."""

    def __init__(
        self,
        store_repo: SqliteStoreRepository,
        link_repo: SqliteDocumentStoreLinkRepository,
        document_repo: SqliteDocumentRepository | None = None,
    ):
        self._stores = store_repo
        self._links = link_repo
        self._documents = document_repo

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
            is_default=is_default,
        )
        await self._stores.insert(store)
        if is_default:
            await self._stores.clear_default_except(store.id)
        return store

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

        promote_default = False
        if is_default is not None:
            store.is_default = is_default
            promote_default = is_default

        await self._stores.update(store)
        if promote_default:
            await self._stores.clear_default_except(store.id)
        return store

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
