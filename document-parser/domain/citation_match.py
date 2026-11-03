"""Where a quote sits in a parse — the matching rules behind `verify_citation`.

Verification is deliberately tolerant in three ways, each covering how an
honest agent quotes: a partial quote, a quote from inside the section an
anchor covers, and a quote that runs from one element into the next. It is
strict about the failure that matters: a quote that is nowhere in what the
anchor covers.

Pure: it takes the parse's `DocumentIndex` and the quote, already in its
comparison form (`domain.anchors.normalise_quote`), and returns the element
that holds the quote. Loading the parse, and what to tell the agent about the
match, stay with `CitationService`. Matching at the level of the PDF's glyphs
is another question, answered by `domain.quote_marks`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.anchors import normalise_quote
from domain.element_reader import element_text, resolve, section_refs
from domain.spans import is_span, span_ref

if TYPE_CHECKING:
    from domain.navigation import ResolvedElement
    from domain.parse_index import DocumentIndex

# Below this, a match proves nothing: "e" or "mois" is in most sections.
MIN_QUOTE_CHARS = 10


def locate_quote(
    index: DocumentIndex,
    ref: str,
    element: ResolvedElement,
    claimed: str,
) -> ResolvedElement | None:
    """Return the element carrying `claimed`, or None.

    `element` is `ref` resolved against `index`, and `claimed` is the quote
    in its normalised form.

    Three passes, narrowest first: the anchor itself, then each element it
    covers, then runs of consecutive elements. The third is what makes a
    quote that finishes in the next paragraph verifiable instead of
    drifted — and it answers with a span anchor, so the citation the agent
    publishes covers the whole passage it quoted.
    """
    # A span's own text is all of its members: answering with it would
    # hand back the range as sent, however wide. Look inside it instead.
    if not is_span(ref) and claimed in normalise_quote(element.text):
        return element
    covered = section_refs(index, ref)
    for candidate in covered:
        if candidate == ref:
            continue
        found = resolve(index, candidate)
        if found is not None and claimed in normalise_quote(found.text):
            return found
    return _locate_across(index, covered, claimed)


def _locate_across(
    index: DocumentIndex,
    refs: list[str],
    claimed: str,
) -> ResolvedElement | None:
    """The smallest run of consecutive elements containing `claimed`.

    Windows grow from each starting element and stop as soon as the text
    *before* the window's last addition is already longer than the claim:
    past that point no match could still involve the element the window
    starts at, so extending it only re-tests what the next start will.
    That bound is what keeps this linear-ish over a long section instead
    of quadratic.
    """
    texts = [(ref, normalise_quote(element_text(index, ref))) for ref in refs]
    texts = [(ref, text) for ref, text in texts if text]
    # Longer than everything the anchor covers, joined: no window can hold it.
    if len(claimed) > sum(len(text) + 1 for _, text in texts):
        return None
    for start, (_, head) in enumerate(texts):
        joined = head
        for end in range(start + 1, len(texts)):
            if len(joined) > len(claimed) + len(head):
                break
            joined = f"{joined} {texts[end][1]}"
            if claimed in joined:
                first = _trim_left(texts, start, end, claimed)
                return resolve(index, span_ref(texts[first][0], texts[end][0]))
    return None


def _trim_left(
    texts: list[tuple[str, str]],
    start: int,
    end: int,
    claimed: str,
) -> int:
    """Drop leading elements the quote does not actually reach into.

    The scan finds the leftmost start that works, and the section's own
    heading works for every quote inside it — so without this, quoting one
    paragraph of Article 12 would come back as a span opening on the title
    of Article 12. The end needs no such trim: the scan already stops at
    the first one that matches.
    """
    while start < end and claimed in " ".join(text for _, text in texts[start + 1 : end + 1]):
        start += 1
    return start
