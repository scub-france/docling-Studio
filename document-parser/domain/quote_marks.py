"""Where a quote sits on its page, line by line — the highlight the card draws.

The parse places a paragraph, not a sentence: a quote boxed by its element's
block lights up the whole paragraph around it. The PDF's own text layer knows
where every character is, so the quote is found there and returned as one
rectangle per line it runs over, like a highlighter pen.

The match ignores everything but letters and digits, case folded and
compatibility-normalised: the parse and the text layer disagree on spaces,
line-end hyphens, ligatures and quote marks, never on the words. One more
disagreement is forgiven: a parse that dropped a ligature glyph whole ("model
ts" for "model fits") still matches the text layer that kept it. It looks
only inside the passage's own blocks, so a sentence repeated elsewhere on the
page cannot be the one marked.

Pure: it takes the page's characters with their boxes and returns value
objects. Reading the PDF is the `PageTextReader` port's job.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.page_regions import PageRegion

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

# A character counts as inside a block when its centre is within this share
# of the page of the block's edges: provenance boxes hug the ink, character
# boxes take the whole line height.
_MARGIN = 0.012
# Below this many letters and digits a match proves nothing: "4" is on every
# page. A table cell like "29.54" still clears it.
_MIN_CHARS = 3
# A highlight is a few lines; a quote running over more is drawn as its first
# lines, which is where a reader starts.
MAX_MARKS = 40
# The letters a ligature glyph stands for, which a parse may have lost.
_LIGATURE = "(?:ff[il]?|f[il])?"


@dataclass(frozen=True)
class Glyph:
    """One character of the page's text layer.

    `box` is `(left, top, right, bottom)` in fractions of the page from its
    top-left corner, or None for a character with no ink (a space or a line
    break the text layer generated).
    """

    char: str
    box: tuple[float, float, float, float] | None


def quote_marks(
    glyphs: Sequence[Glyph], quote: str, *, page: int, within: Sequence[PageRegion] = ()
) -> list[PageRegion]:
    """The lines `quote` covers on `page`, or nothing when it is not there.

    Looked for whole first. A quote out of a table (`cell | cell | cell`) is
    then looked for cell by cell, since the text layer may read the row in
    another order or with other cells between.
    """
    hay, owners = _haystack(glyphs, within)
    whole = _key(quote)
    if len(whole) >= _MIN_CHARS and (spans := _find_all([whole], hay)):
        return _lines(glyphs, owners, spans, page)
    parts = [_key(part) for part in quote.split("|")]
    parts = [part for part in parts if len(part) >= _MIN_CHARS]
    if len(parts) < 2:
        return []
    return _lines(glyphs, owners, _find_all(parts, hay), page)


def _key(text: str) -> str:
    """Letters and digits only, case folded, ligatures and widths unfolded."""
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def _haystack(glyphs: Sequence[Glyph], within: Sequence[PageRegion]) -> tuple[str, list[int]]:
    """The page's letters and digits inside the blocks, and the glyph each
    one came from (a ligature gives several)."""
    chars: list[str] = []
    owners: list[int] = []
    for index, glyph in enumerate(glyphs):
        if glyph.box is None or not _inside(glyph.box, within):
            continue
        for char in _key(glyph.char):
            chars.append(char)
            owners.append(index)
    return "".join(chars), owners


def _inside(box: tuple[float, float, float, float], within: Sequence[PageRegion]) -> bool:
    if not within:
        return True
    x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return any(
        r.left - _MARGIN <= x <= r.right + _MARGIN and r.top - _MARGIN <= y <= r.bottom + _MARGIN
        for r in within
    )


def _find_all(needles: Iterable[str], hay: str) -> list[tuple[int, int]]:
    """Each needle's first place after the previous one's, else its first
    place anywhere: cells are quoted in reading order, mostly."""
    spans: list[tuple[int, int]] = []
    cursor = 0
    for needle in needles:
        found = _find(needle, hay, cursor) or _find(needle, hay, 0)
        if found is None:
            continue
        spans.append(found)
        cursor = found[1]
    return spans


def _find(needle: str, hay: str, start: int) -> tuple[int, int] | None:
    """Where `needle` is in `hay` from `start`: as is, else with the letters
    of a lost ligature allowed back between any two of its characters."""
    at = hay.find(needle, start)
    if at >= 0:
        return at, at + len(needle)
    match = re.compile(_LIGATURE.join(map(re.escape, needle))).search(hay, start)
    return match.span() if match else None


def _lines(
    glyphs: Sequence[Glyph], owners: list[int], spans: list[tuple[int, int]], page: int
) -> list[PageRegion]:
    """One rectangle per run of matched glyphs on one line.

    A glyph opens a new line when it sits lower or higher than the line by
    more than half its own height, or starts left of where the line ended.
    """
    marks: list[PageRegion] = []
    for start, end in spans:
        line: list[float] | None = None
        for index in sorted(set(owners[start:end])):
            box = glyphs[index].box
            if box is None:
                continue
            left, top, right, bottom = box
            if line is not None and _same_line(line, box):
                line = [
                    min(line[0], left),
                    min(line[1], top),
                    max(line[2], right),
                    max(line[3], bottom),
                ]
                continue
            if line is not None:
                marks.append(PageRegion(page, *line))
            line = [left, top, right, bottom]
        if line is not None:
            marks.append(PageRegion(page, *line))
    return marks[:MAX_MARKS]


def _same_line(line: list[float], box: tuple[float, float, float, float]) -> bool:
    height = max(box[3] - box[1], 1e-6)
    centre, line_centre = (box[1] + box[3]) / 2, (line[1] + line[3]) / 2
    return abs(centre - line_centre) < height / 2 and box[0] >= line[2] - height
