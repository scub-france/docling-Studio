"""Tests for the document lifecycle aggregation rule (#203)."""

from __future__ import annotations

from domain.lifecycle_aggregation import aggregate_lifecycle
from domain.models import DocumentStoreLink
from domain.value_objects import DocumentLifecycleState, DocumentStoreLinkState


def _link(state: DocumentStoreLinkState) -> DocumentStoreLink:
    return DocumentStoreLink(
        id=f"link-{state.value}",
        document_id="doc-1",
        store_id=f"store-{state.value}",
        state=state,
    )


def test_no_links_returns_fallback() -> None:
    assert (
        aggregate_lifecycle([], fallback=DocumentLifecycleState.CHUNKED)
        == DocumentLifecycleState.CHUNKED
    )


def test_single_ingested_link_makes_doc_ingested() -> None:
    assert (
        aggregate_lifecycle(
            [_link(DocumentStoreLinkState.INGESTED)],
            fallback=DocumentLifecycleState.CHUNKED,
        )
        == DocumentLifecycleState.INGESTED
    )


def test_any_stale_link_makes_doc_stale() -> None:
    """Stale outranks Ingested — a doc with one stale store is considered stale."""
    assert (
        aggregate_lifecycle(
            [
                _link(DocumentStoreLinkState.INGESTED),
                _link(DocumentStoreLinkState.STALE),
            ],
            fallback=DocumentLifecycleState.CHUNKED,
        )
        == DocumentLifecycleState.STALE
    )


def test_any_failed_link_makes_doc_failed() -> None:
    """Failed outranks every other link state."""
    assert (
        aggregate_lifecycle(
            [
                _link(DocumentStoreLinkState.INGESTED),
                _link(DocumentStoreLinkState.STALE),
                _link(DocumentStoreLinkState.FAILED),
            ],
            fallback=DocumentLifecycleState.CHUNKED,
        )
        == DocumentLifecycleState.FAILED
    )


def test_only_failed_link_makes_doc_failed() -> None:
    assert (
        aggregate_lifecycle(
            [_link(DocumentStoreLinkState.FAILED)],
            fallback=DocumentLifecycleState.CHUNKED,
        )
        == DocumentLifecycleState.FAILED
    )
