"""Document lifecycle state machine — pure domain logic.

Defines the canonical state model for a Document in Docling Studio:
  Uploaded → Parsed → Chunked → Ingested → (Stale|Chunked) → Ingested

Stale is set by the auto-detect logic (#204) — never reached by a manual
action. Failed is reachable from any state and represents a pipeline error.

This module contains:
  - The transition table (which (from → to) pairs are allowed).
  - `is_allowed_transition`: the pure check.
  - `assert_transition`: raises `InvalidLifecycleTransitionError` when not allowed.

The dataclass that carries the state lives in `domain.models.Document`. The
domain event emitted on transition lives in `domain.events`.
"""

from __future__ import annotations

from domain.exceptions import InvalidLifecycleTransitionError
from domain.value_objects import DocumentLifecycleState

# Allowed transitions: from → set of allowed targets.
# Failed is always reachable as a terminal-ish state (see notes below).
# Self-loops are allowed only where they make pipeline sense (e.g. re-chunk).
_TRANSITIONS: dict[DocumentLifecycleState, frozenset[DocumentLifecycleState]] = {
    DocumentLifecycleState.UPLOADED: frozenset(
        {
            DocumentLifecycleState.PARSED,
            DocumentLifecycleState.CHUNKED,  # parse + chunk in one pipeline call
            DocumentLifecycleState.FAILED,
        }
    ),
    DocumentLifecycleState.PARSED: frozenset(
        {
            DocumentLifecycleState.PARSED,  # idempotent re-parse
            DocumentLifecycleState.CHUNKED,
            DocumentLifecycleState.FAILED,
        }
    ),
    DocumentLifecycleState.CHUNKED: frozenset(
        {
            DocumentLifecycleState.CHUNKED,  # re-chunk
            DocumentLifecycleState.INGESTED,
            DocumentLifecycleState.FAILED,
        }
    ),
    DocumentLifecycleState.INGESTED: frozenset(
        {
            DocumentLifecycleState.STALE,
            DocumentLifecycleState.CHUNKED,  # re-chunk after ingest
            DocumentLifecycleState.INGESTED,  # re-push (idempotent)
            DocumentLifecycleState.FAILED,
        }
    ),
    DocumentLifecycleState.STALE: frozenset(
        {
            DocumentLifecycleState.INGESTED,
            DocumentLifecycleState.CHUNKED,
            DocumentLifecycleState.FAILED,
        }
    ),
    # Failed is a recoverable state — the operator (or a retry) can move
    # back to a non-terminal state by re-running the relevant pipeline step.
    DocumentLifecycleState.FAILED: frozenset(
        {
            DocumentLifecycleState.UPLOADED,
            DocumentLifecycleState.PARSED,
            DocumentLifecycleState.CHUNKED,
        }
    ),
}


def is_allowed_transition(source: DocumentLifecycleState, target: DocumentLifecycleState) -> bool:
    """Return True iff transitioning from `source` to `target` is allowed."""
    return target in _TRANSITIONS.get(source, frozenset())


def assert_transition(source: DocumentLifecycleState, target: DocumentLifecycleState) -> None:
    """Raise `InvalidLifecycleTransitionError` if the transition is not allowed."""
    if not is_allowed_transition(source, target):
        raise InvalidLifecycleTransitionError(source=source, target=target)
