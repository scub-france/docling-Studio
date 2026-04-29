"""Aggregate the per-(document, store) link states into a single
document-level lifecycle state.

The doc lifecycle column is the materialized result of this rule. It is
recomputed any time a link write happens. Read paths use the stored
column directly (cheap) — they do not call this rule on every GET.

The rule prefers "more concerning" states first:

    any link FAILED   -> Document FAILED
    any link STALE    -> Document STALE
    any link INGESTED -> Document INGESTED
    no links          -> keep the document's current pre-link state
                        (Uploaded / Parsed / Chunked) — the caller is
                        responsible for not overwriting that.

If you find yourself wanting a fourth case, you probably want a new
link state, not a new aggregation branch.

This module is pure: no I/O, no datetime — just data in / data out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.value_objects import DocumentLifecycleState, DocumentStoreLinkState

if TYPE_CHECKING:
    from collections.abc import Iterable

    from domain.models import DocumentStoreLink


def aggregate_lifecycle(
    links: Iterable[DocumentStoreLink],
    *,
    fallback: DocumentLifecycleState,
) -> DocumentLifecycleState:
    """Compute the aggregate document lifecycle state.

    Args:
        links: every `DocumentStoreLink` for the document. May be empty.
        fallback: the lifecycle state to return when there are no links —
            typically the document's current pre-link state (`Uploaded`,
            `Parsed`, or `Chunked`).

    Returns:
        The aggregate `DocumentLifecycleState`.
    """
    states = {link.state for link in links}
    if DocumentStoreLinkState.FAILED in states:
        return DocumentLifecycleState.FAILED
    if DocumentStoreLinkState.STALE in states:
        return DocumentLifecycleState.STALE
    if DocumentStoreLinkState.INGESTED in states:
        return DocumentLifecycleState.INGESTED
    return fallback
