"""Tests for the Document lifecycle state machine (#202)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from domain.events import DocumentLifecycleChanged
from domain.exceptions import InvalidLifecycleTransitionError
from domain.lifecycle import assert_transition, is_allowed_transition
from domain.models import Document
from domain.value_objects import DocumentLifecycleState

ALLOWED_TRANSITIONS = [
    # Uploaded
    (DocumentLifecycleState.UPLOADED, DocumentLifecycleState.PARSED),
    (DocumentLifecycleState.UPLOADED, DocumentLifecycleState.CHUNKED),
    (DocumentLifecycleState.UPLOADED, DocumentLifecycleState.FAILED),
    # Parsed
    (DocumentLifecycleState.PARSED, DocumentLifecycleState.PARSED),
    (DocumentLifecycleState.PARSED, DocumentLifecycleState.CHUNKED),
    (DocumentLifecycleState.PARSED, DocumentLifecycleState.FAILED),
    # Chunked
    (DocumentLifecycleState.CHUNKED, DocumentLifecycleState.CHUNKED),
    (DocumentLifecycleState.CHUNKED, DocumentLifecycleState.INGESTED),
    (DocumentLifecycleState.CHUNKED, DocumentLifecycleState.FAILED),
    # Ingested
    (DocumentLifecycleState.INGESTED, DocumentLifecycleState.STALE),
    (DocumentLifecycleState.INGESTED, DocumentLifecycleState.CHUNKED),
    (DocumentLifecycleState.INGESTED, DocumentLifecycleState.INGESTED),
    (DocumentLifecycleState.INGESTED, DocumentLifecycleState.FAILED),
    # Stale
    (DocumentLifecycleState.STALE, DocumentLifecycleState.INGESTED),
    (DocumentLifecycleState.STALE, DocumentLifecycleState.CHUNKED),
    (DocumentLifecycleState.STALE, DocumentLifecycleState.FAILED),
    # Failed (recoverable)
    (DocumentLifecycleState.FAILED, DocumentLifecycleState.UPLOADED),
    (DocumentLifecycleState.FAILED, DocumentLifecycleState.PARSED),
    (DocumentLifecycleState.FAILED, DocumentLifecycleState.CHUNKED),
]


@pytest.mark.parametrize(("source", "target"), ALLOWED_TRANSITIONS)
def test_allowed_transitions_pass(
    source: DocumentLifecycleState, target: DocumentLifecycleState
) -> None:
    assert is_allowed_transition(source, target)
    # assert_transition does not raise.
    assert_transition(source, target)


def test_disallowed_transitions_are_rejected() -> None:
    """Spot-check the most surprising disallowed pairs.

    Exhaustive enumeration of every disallowed pair would just mirror the
    transition table; this list captures the cases a reader is most
    likely to argue about.
    """
    forbidden = [
        # Uploaded cannot skip directly to Ingested or Stale.
        (DocumentLifecycleState.UPLOADED, DocumentLifecycleState.INGESTED),
        (DocumentLifecycleState.UPLOADED, DocumentLifecycleState.STALE),
        # Parsed cannot become Ingested without going through Chunked.
        (DocumentLifecycleState.PARSED, DocumentLifecycleState.INGESTED),
        # Stale is not directly reachable from Parsed (no per-store yet).
        (DocumentLifecycleState.PARSED, DocumentLifecycleState.STALE),
        # Failed cannot be reached as a "self-loop" — it always reflects a
        # new failure, never an idempotent re-mark.
        (DocumentLifecycleState.FAILED, DocumentLifecycleState.FAILED),
        # Failed cannot jump directly to Ingested or Stale — must re-do
        # the relevant pipeline step first.
        (DocumentLifecycleState.FAILED, DocumentLifecycleState.INGESTED),
        (DocumentLifecycleState.FAILED, DocumentLifecycleState.STALE),
    ]
    for source, target in forbidden:
        assert not is_allowed_transition(source, target)
        with pytest.raises(InvalidLifecycleTransitionError) as excinfo:
            assert_transition(source, target)
        assert excinfo.value.source == source
        assert excinfo.value.target == target


def test_document_default_state_is_uploaded() -> None:
    doc = Document(filename="test.pdf", storage_path="/tmp/test.pdf")
    assert doc.lifecycle_state == DocumentLifecycleState.UPLOADED
    assert doc.lifecycle_state_at is None


def test_transition_returns_event_and_mutates_state() -> None:
    doc = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
    before = datetime(2026, 4, 29, 10, tzinfo=UTC)

    event = doc.transition_to(DocumentLifecycleState.PARSED, now=before)

    assert isinstance(event, DocumentLifecycleChanged)
    assert event.document_id == "doc-1"
    assert event.previous == DocumentLifecycleState.UPLOADED
    assert event.current == DocumentLifecycleState.PARSED
    assert event.at == before
    # State mutated on the dataclass.
    assert doc.lifecycle_state == DocumentLifecycleState.PARSED
    assert doc.lifecycle_state_at == before


def test_invalid_transition_does_not_mutate_state() -> None:
    doc = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
    assert doc.lifecycle_state == DocumentLifecycleState.UPLOADED

    with pytest.raises(InvalidLifecycleTransitionError):
        doc.transition_to(DocumentLifecycleState.STALE)

    # State is untouched.
    assert doc.lifecycle_state == DocumentLifecycleState.UPLOADED
    assert doc.lifecycle_state_at is None


def test_idempotent_self_transitions_emit_event() -> None:
    """Self-loops (re-parse, re-chunk, re-push) are explicitly allowed
    so the pipeline can drive transitions without checking the source
    state first. They still emit an event for observability."""
    doc = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
    doc.transition_to(DocumentLifecycleState.CHUNKED)
    assert doc.lifecycle_state == DocumentLifecycleState.CHUNKED

    event = doc.transition_to(DocumentLifecycleState.CHUNKED)

    assert event.previous == DocumentLifecycleState.CHUNKED
    assert event.current == DocumentLifecycleState.CHUNKED
