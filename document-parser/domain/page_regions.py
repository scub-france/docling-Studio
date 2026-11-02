"""Where a reading sits on the page — the boxes the sources card draws.

A round reads a section; a section is a run of elements, each with a box per
page it touches. Drawn one box per element, a section is a stack of thin
rectangles that hides the page under it. Drawn as one rectangle per page, a
section that ends at the bottom of the left column and resumes at the top of
the right one covers the whole page, including what was not read.

So the boxes are merged into blocks: one per column run on each page. Two
boxes join when they share a column (they overlap across at least half of the
narrower one) and nothing but a small gap separates them vertically.

Fractions of the page, from the top-left corner, so a viewer lays them over a
raster of any size without knowing the dpi it was rendered at.

Pure: it reads the `DocumentIndex` it is given and returns value objects.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from domain.parse_index import label_of

if TYPE_CHECKING:
    from collections.abc import Iterable

    from domain.parse_index import DocumentIndex

# Two boxes in one column join across a gap up to this share of the page
# height: a paragraph break, a short caption, a heading's own margin.
_GAP = 0.035
# The share of the narrower box two boxes must overlap across to count as one
# column.
_SAME_COLUMN = 0.5
# Plenty for a section over a few pages; a guard against a read that covered
# a hundred-page appendix filling the card's payload with rectangles.
MAX_REGIONS = 24
# Running headers and footers sit inside a section's range in reading order,
# but nobody reads them: boxed, they would stretch a block to the page edge.
_FURNITURE = frozenset({"page_header", "page_footer"})


@dataclass(frozen=True)
class PageRegion:
    """A block of a page, as fractions of its width and height."""

    page: int
    left: float
    top: float
    right: float
    bottom: float

    def joins(self, other: PageRegion) -> bool:
        """Same page, same column, and close enough to read as one block."""
        if other.page != self.page:
            return False
        overlap = min(self.right, other.right) - max(self.left, other.left)
        narrower = min(self.right - self.left, other.right - other.left)
        if narrower <= 0 or overlap < _SAME_COLUMN * narrower:
            return False
        gap = max(other.top - self.bottom, self.top - other.bottom)
        return gap <= _GAP

    def merged(self, other: PageRegion) -> PageRegion:
        return replace(
            self,
            left=min(self.left, other.left),
            top=min(self.top, other.top),
            right=max(self.right, other.right),
            bottom=max(self.bottom, other.bottom),
        )


def regions_of(
    index: DocumentIndex, refs: Iterable[str], *, limit: int = MAX_REGIONS
) -> list[PageRegion]:
    """The blocks `refs` cover, page by page, each page's in reading order.

    A box with no page size, or with no area, has nowhere to be drawn and is
    left out, as are running headers and footers. Past `limit` blocks the
    rest are dropped: the first pages of a long read are the ones a reader
    checks.
    """
    by_page: dict[int, list[PageRegion]] = {}
    for ref in refs:
        if label_of(index.by_ref.get(ref) or {}) in _FURNITURE:
            continue
        for box in index.boxes_of.get(ref, ()):
            share = box.page_fraction()
            if share is None or share[2] <= share[0] or share[3] <= share[1]:
                continue
            _add(by_page.setdefault(box.page, []), PageRegion(box.page, *share))
    regions = [region for page in sorted(by_page) for region in by_page[page]]
    return regions[:limit]


def _add(blocks: list[PageRegion], region: PageRegion) -> None:
    """Add `region`, then merge until no two blocks join.

    Until none, not once: a block that grows can reach one it did not touch
    before, and the order the boxes arrive in must not leave two blocks that
    should have been one. The earlier block keeps its place, so the page's
    blocks stay in reading order. A page holds a few dozen boxes at most.
    """
    blocks.append(region)
    while True:
        pair = next(
            (
                (i, j)
                for i in range(len(blocks))
                for j in range(i + 1, len(blocks))
                if blocks[i].joins(blocks[j])
            ),
            None,
        )
        if pair is None:
            return
        i, j = pair
        blocks[i] = blocks[i].merged(blocks.pop(j))
