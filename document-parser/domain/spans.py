"""Span refs — one citation covering several elements.

    #/texts/91..#/texts/94

A docling `self_ref` names one block. A quote rarely respects that boundary:
a sentence finishes in the next paragraph, a clause is split across two list
items, a number lives in a caption below the figure it describes. Cited one
block at a time, such a passage either gets truncated to whichever half fits
one ref, or fails verification because it is in neither.

A span is the inclusive range between two refs **in reading order**, inside
one parse. It resolves like any other ref — text, page, provenance — so
everything downstream (reading, verification, the crop, the deep link) works
on it without knowing it is composite.

Two rules keep it honest:

- **The endpoints come from the server.** An agent gets a span back from
  `read_element` (`span_uri`) or from `verify_citation`, which builds the
  smallest span that actually contains the quote. The "never assemble an
  anchor" rule is unchanged.
- **Reading order, not document order.** The range is a slice of
  `DocumentIndex.order`, so it covers exactly what a reader would read
  between the two ends, and nothing that was pruned out of that order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.parse_index import DocumentIndex

SPAN_SEPARATOR = ".."


def parse_span(ref: str) -> tuple[str, str] | None:
    """Split a span ref into its two endpoints, or None if it is not one.

    The right-hand endpoint is accepted with or without its `#`: an anchor
    reads better as `#/texts/91..#/texts/94` than as `#/texts/91../texts/94`,
    and both forms name the same range.
    """
    text = (ref or "").strip()
    if SPAN_SEPARATOR not in text:
        return None
    start, _, end = text.partition(SPAN_SEPARATOR)
    start, end = start.strip(), end.strip()
    if not start or not end:
        return None
    return start, end if end.startswith("#") else "#" + end


def is_span(ref: str) -> bool:
    return parse_span(ref) is not None


def span_ref(start: str, end: str) -> str:
    """The canonical span ref for a pair of endpoints."""
    return f"{start}{SPAN_SEPARATOR}{end}"


def span_start(ref: str) -> str:
    """The first endpoint of a span, or `ref` itself when it is not one.

    For everything that needs *a* single element to stand for the span — the
    Studio deep link, chiefly, whose viewer scrolls to one ref.
    """
    span = parse_span(ref)
    return span[0] if span else ref


def span_members(index: DocumentIndex, start: str, end: str) -> list[str]:
    """The refs a span covers, in reading order.

    Empty when either endpoint is unknown to this parse — a span from another
    version names positions that do not exist here, and guessing at the
    overlap would produce a citation nobody asked for. Reversed endpoints are
    read in the order the document has them rather than rejected.
    """
    first, last = index.position.get(start), index.position.get(end)
    if first is None or last is None:
        return []
    low, high = sorted((first, last))
    return index.order[low : high + 1]
