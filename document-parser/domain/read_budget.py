"""Reading under a token budget — the rules behind `read_element`.

A read covers one element, or the whole section it opens, and stops when the
budget is spent. Where it stopped travels back to the agent as a cursor, so
the next read resumes there:

    #/texts/12           resume at this element
    #/texts/12@840       resume inside it, at character 840

The second form exists for an element larger than a whole read, which is cut
at a word boundary rather than skipped or handed out whole.

Pure: everything here takes the parse's `DocumentIndex` and returns refs and
resolved elements. Loading the parse, the configured budgets and the anchors
handed to the agent stay with `NavigationService`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from domain.element_reader import resolve, section_refs
from domain.navigation import ANCHOR_TOKENS, clip_point, clip_to_tokens, read_cost
from domain.parse_index import parse_page_ref
from domain.spans import span_members, span_ref

if TYPE_CHECKING:
    from domain.navigation import ResolvedElement
    from domain.parse_index import DocumentIndex

# `self` reads the element alone; `section` reads everything it opens.
READ_MODES = ("self", "section")

_CURSOR_OFFSET = "@"


class InvalidCursorError(ValueError):
    """A cursor that does not resume this read. The message is written for
    an LLM reader: it says what to pass instead."""


@dataclass(frozen=True)
class BudgetedRead:
    """The elements one read returns, and where the budget stopped it.

    `next_cursor` is None when the read reached the end of what it covers.
    """

    elements: list[ResolvedElement]
    spent: int
    truncated: bool
    next_cursor: str | None = None


def refs_to_read(
    index: DocumentIndex,
    ref: str,
    *,
    include: str,
    cursor: str | None,
) -> tuple[list[str], int]:
    """The refs this read covers from the cursor on, and the character of
    the first to start at — past 0 when the cursor is `ref@offset`.

    Raises:
        InvalidCursorError: the cursor names no element of this read, or an
            offset outside the element it names.
    """
    # A page ref carries no text of its own, so `self` would read nothing
    # at all — for it, both modes mean "everything on this page".
    read_whole = include == "section" or parse_page_ref(ref) is not None
    # `section_refs` is empty for a ref that resolves but sits outside
    # reading order — a caption, or text pruned from inside a picture.
    # Those refs carry text and `include="self"` returns it, so the
    # default mode must not answer "this element is empty" for them.
    refs = (section_refs(index, ref) or [ref]) if read_whole else [ref]
    if not cursor:
        return refs, 0
    resume, at, offset = cursor.partition(_CURSOR_OFFSET)
    start = int(offset) if offset.isdecimal() else 0
    element = resolve(index, resume) if resume in refs else None
    if element is None or (at and not 0 < start < len(element.text)):
        raise InvalidCursorError(
            f"Cursor {cursor!r} does not belong to this section — pass back the "
            "`next_cursor` returned by the previous read, unchanged."
        )
    return refs[refs.index(resume) :], start


def pick_within_budget(
    index: DocumentIndex,
    refs: list[str],
    budget: int,
    start: int = 0,
) -> BudgetedRead:
    """Take elements in reading order until the budget is spent — the
    first from character `start`, where a previous read cut it.

    A read always returns something: an element larger than the whole budget
    is cut at a word boundary, and the cursor resumes inside it.
    """
    picked: list[ResolvedElement] = []
    spent = 0

    for position, candidate in enumerate(refs):
        element = resolve(index, candidate)
        if element is None or not element.text.strip():
            continue
        offset = start if position == 0 else 0
        if offset:
            element = replace(element, text=element.text[offset:])
        cost = read_cost(element.text)
        if picked and spent + cost > budget:
            return BudgetedRead(picked, spent, truncated=True, next_cursor=candidate)
        if not picked and cost > budget:
            # Larger than the whole budget: cut at a word boundary, and
            # the cursor resumes inside the element where the cut fell.
            room = budget - ANCHOR_TOKENS
            cut = clip_point(element.text, room)
            if cut < len(element.text):
                clipped = replace(element, text=clip_to_tokens(element.text, room))
                return BudgetedRead(
                    [clipped],
                    read_cost(clipped.text),
                    truncated=True,
                    next_cursor=f"{candidate}{_CURSOR_OFFSET}{offset + cut}",
                )
        picked.append(element)
        spent += cost

    return BudgetedRead(picked, spent, truncated=False)


def read_span_ref(
    index: DocumentIndex,
    refs: list[str],
    picked: list[ResolvedElement],
) -> str | None:
    """The span ref covering exactly this read — nothing more.

    A quote that runs from one paragraph into the next has no single ref
    to hang on, and truncating it to whichever half fits one is how a
    citation becomes an approximation. This hands the range back so the
    agent never has to assemble one.

    The span is withheld unless every ref between its endpoints was part
    of this read: a page read can pick up elements that are not contiguous
    in reading order, and a span over them would silently cover text the
    caller never saw.
    """
    if len(picked) < 2:
        return None
    read = set(refs)
    members = span_members(index, picked[0].ref, picked[-1].ref)
    if not members or any(member not in read for member in members):
        return None
    return span_ref(picked[0].ref, picked[-1].ref)
