"""Where a reading sits on the page — the blocks the sources card draws.

Boxes are given in points on a 600 x 1000 page, so a box's fraction reads off
its numbers: `top=300` is 0.3 of the way down.
"""

from __future__ import annotations

import pytest

from domain.navigation import BoundingBox
from domain.page_regions import PageRegion, regions_of
from domain.parse_index import DocumentIndex, build_index
from infra.docling_tree import DoclingTreeReader
from tests.navigation_fixtures import MESSY

W, H = 600.0, 1000.0


def box(left, top, right, bottom, *, page=1, size=True):
    return BoundingBox(
        page=page,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        page_width=W if size else None,
        page_height=H if size else None,
    )


def index_of(**boxes: list[BoundingBox]) -> DocumentIndex:
    """An index that only knows boxes: the one thing `regions_of` reads."""
    return DocumentIndex(
        by_ref={},
        order=list(boxes),
        position={},
        heading_path={},
        section_end={},
        page_of={},
        pages_of={},
        bbox_of={},
        inline_meta={},
        boxes_of={ref: tuple(value) for ref, value in boxes.items()},
    )


def edges(region: PageRegion):
    return tuple(
        round(value, 4) for value in (region.left, region.top, region.right, region.bottom)
    )


class TestBlocks:
    def test_paragraphs_stacked_in_one_column_are_one_block(self):
        index = index_of(a=[box(60, 100, 540, 200)], b=[box(60, 210, 540, 300)])
        [region] = regions_of(index, ["a", "b"])
        assert region.page == 1
        assert edges(region) == (0.1, 0.1, 0.9, 0.3)

    def test_a_wide_gap_keeps_two_blocks(self):
        index = index_of(a=[box(60, 100, 540, 200)], b=[box(60, 400, 540, 500)])
        assert len(regions_of(index, ["a", "b"])) == 2

    def test_two_columns_stay_two_blocks_in_reading_order(self):
        """A section that runs from the foot of the left column to the head of
        the right one is not the whole page."""
        index = index_of(
            left=[box(40, 700, 290, 950)],
            right=[box(310, 50, 560, 300)],
        )
        regions = regions_of(index, ["left", "right"])
        assert [round(r.left, 3) for r in regions] == [0.067, 0.517]

    def test_the_order_boxes_arrive_in_cannot_leave_a_split_block(self):
        # The middle paragraph arrives last and bridges the other two.
        index = index_of(
            top=[box(60, 100, 540, 200)],
            bottom=[box(60, 260, 540, 360)],
            middle=[box(60, 205, 540, 255)],
        )
        [region] = regions_of(index, ["top", "bottom", "middle"])
        assert (region.top, region.bottom) == pytest.approx((0.1, 0.36))

    def test_an_element_across_a_page_break_has_a_block_on_each_page(self):
        index = build_index(MESSY, DoclingTreeReader())
        regions = regions_of(index, ["#/texts/3"])
        assert [r.page for r in regions] == [1, 2]

    def test_pages_come_in_order_whatever_the_reading_order(self):
        index = index_of(a=[box(60, 100, 540, 200, page=3)], b=[box(60, 100, 540, 200, page=1)])
        assert [r.page for r in regions_of(index, ["a", "b"])] == [1, 3]


class TestWhatIsLeftOut:
    def test_a_box_on_a_page_of_unknown_size(self):
        index = index_of(a=[box(60, 100, 540, 200, size=False)])
        assert regions_of(index, ["a"]) == []

    def test_a_box_with_no_area(self):
        index = index_of(a=[box(60, 100, 60, 200)])
        assert regions_of(index, ["a"]) == []

    def test_running_headers_and_footers(self):
        """Inside a section's range in reading order, but nobody reads them."""
        index = build_index(MESSY, DoclingTreeReader())
        assert regions_of(index, ["#/texts/0", "#/texts/4"]) == []

    def test_a_ref_with_no_box(self):
        assert regions_of(index_of(), ["#/groups/0"]) == []

    def test_blocks_past_the_limit(self):
        index = index_of(**{f"p{n}": [box(60, 100, 540, 200, page=n)] for n in range(1, 6)})
        regions = regions_of(index, [f"p{n}" for n in range(1, 6)], limit=3)
        assert [r.page for r in regions] == [1, 2, 3]
