"""Stores API router — CRUD on ingestion targets (#251)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from api.schemas import (
    StoreCreateRequest,
    StoreDocEntryResponse,
    StoreInfoResponse,
    StoreResponse,
    StoreUpdateRequest,
)
from domain.value_objects import StoreKind
from services.store_service import (
    StoreService,
    StoreServiceError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stores", tags=["stores"])


def _get_service(request: Request) -> StoreService:
    return request.app.state.store_service


ServiceDep = Annotated[StoreService, Depends(_get_service)]


def _parse_kind(value: str) -> StoreKind:
    try:
        return StoreKind(value)
    except ValueError as exc:
        valid = ", ".join(k.value for k in StoreKind)
        raise HTTPException(
            status_code=422,
            detail=f"Unknown store kind '{value}'. Valid kinds: {valid}.",
        ) from exc


def _store_to_response(store) -> StoreResponse:
    return StoreResponse(
        id=store.id,
        name=store.name,
        slug=store.slug,
        kind=store.kind.value,
        embedder=store.embedder,
        is_default=store.is_default,
        config=store.config,
        created_at=str(store.created_at),
    )


def _info_to_response(view) -> StoreInfoResponse:
    return StoreInfoResponse(
        name=view.name,
        slug=view.slug,
        type=view.kind,
        embedder=view.embedder,
        is_default=view.is_default,
        document_count=view.document_count,
        chunk_count=view.chunk_count,
        connected=view.connected,
        error_message=view.error_message,
    )


def _doc_entry_to_response(entry) -> StoreDocEntryResponse:
    return StoreDocEntryResponse(
        doc_id=entry.doc_id,
        filename=entry.filename,
        state=entry.state,
        chunk_count=entry.chunk_count,
        pushed_at=entry.pushed_at,
    )


@router.get("", response_model=list[StoreInfoResponse])
async def list_stores(service: ServiceDep) -> list[StoreInfoResponse]:
    views = await service.list_stores()
    return [_info_to_response(v) for v in views]


@router.post("", response_model=StoreResponse, status_code=201)
async def create_store(
    payload: StoreCreateRequest,
    service: ServiceDep,
) -> StoreResponse:
    kind = _parse_kind(payload.kind)
    try:
        store = await service.create_store(
            name=payload.name,
            slug=payload.slug,
            kind=kind,
            embedder=payload.embedder,
            config=payload.config,
            is_default=payload.is_default,
        )
    except StoreServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return _store_to_response(store)


@router.get("/{slug}", response_model=StoreResponse)
async def get_store(slug: str, service: ServiceDep) -> StoreResponse:
    try:
        store = await service.get_by_slug(slug)
    except StoreServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return _store_to_response(store)


@router.patch("/{slug}", response_model=StoreResponse)
async def update_store(
    slug: str,
    payload: StoreUpdateRequest,
    service: ServiceDep,
) -> StoreResponse:
    kind = _parse_kind(payload.kind) if payload.kind is not None else None
    try:
        store = await service.update_store(
            slug,
            name=payload.name,
            new_slug=payload.slug,
            kind=kind,
            embedder=payload.embedder,
            config=payload.config,
            is_default=payload.is_default,
        )
    except StoreServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return _store_to_response(store)


@router.delete("/{slug}", status_code=204)
async def delete_store(slug: str, service: ServiceDep) -> Response:
    try:
        await service.delete_store(slug)
    except StoreServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return Response(status_code=204)


@router.get("/{slug}/documents", response_model=list[StoreDocEntryResponse])
async def list_store_documents(
    slug: str,
    service: ServiceDep,
) -> list[StoreDocEntryResponse]:
    try:
        entries = await service.list_documents(slug)
    except StoreServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return [_doc_entry_to_response(e) for e in entries]


@router.delete("/{slug}/documents/{doc_id}", status_code=204)
async def remove_store_document(
    slug: str,
    doc_id: str,
    service: ServiceDep,
) -> Response:
    try:
        await service.remove_document(slug, doc_id)
    except StoreServiceError as exc:
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return Response(status_code=204)
