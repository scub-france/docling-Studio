"""Where a quote sits under an anchor: the element, or the run of elements, carrying it.

Pure functions over a parse index, used by citation verification. The rules
are tolerant in the ways an honest agent quotes (a quote from inside the
section an anchor covers, a quote running into the next paragraph) and strict
about a quote that is nowhere in what the anchor covers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.anchors import normalise_quote
from domain.element_reader import list_section_refs, read_element_text, resolve
from domain.spans import build_span_ref, is_span

if TYPE_CHECKING:
    from domain.navigation import ResolvedElement
    from domain.parse_index import DocumentIndex


def locate_quote(
    index: DocumentIndex,
    ref: str,
    element: ResolvedElement,
    claimed: str,
) -> ResolvedElement | None:
    """Return the element carrying `claimed`, or None.

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
    covered = list_section_refs(index, ref)
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
    texts = [(ref, normalise_quote(read_element_text(index, ref))) for ref in refs]
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
                return resolve(index, build_span_ref(texts[first][0], texts[end][0]))
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
