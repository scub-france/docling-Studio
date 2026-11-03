"""The steps of `build_index`, one at a time.

`test_navigation_domain.py` pins the index as a whole on the shared fixtures;
these pin each step `build_index` is assembled from, including the cases those
fixtures do not have: an inline group, which takes its runs' provenance, and
a `pages` map with holes.
"""

from __future__ import annotations

from typing import Any

from domain.parse_index import (
    _heading_paths,
    _items_by_ref,
    _page_sizes,
    _provenance,
    build_index,
)
from infra.docling_tree import DoclingTreeReader

READER = DoclingTreeReader()


def _prov(page: int | None, top: float = 10.0) -> dict[str, Any]:
    return {"page_no": page, "bbox": {"l": 10.0, "t": top, "r": 50.0, "b": top + 5}}


def _doc(texts, *, groups=(), pages=None, body=None) -> dict[str, Any]:
    refs = [item["self_ref"] for item in [*texts, *groups] if "self_ref" in item]
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "doc",
        "pages": pages or {},
        "body": {
            "self_ref": "#/body",
            "children": [{"$ref": ref} for ref in (body or refs)],
        },
        "texts": list(texts),
        "tables": [],
        "pictures": [],
        "groups": list(groups),
    }


def _heading(n: int, level: int, text: str) -> dict[str, Any]:
    return {
        "self_ref": f"#/texts/{n}",
        "label": "section_header",
        "level": level,
        "text": text,
        "prov": [_prov(1)],
    }


def _text(n: int, text: str = "corps", page: int | None = 1) -> dict[str, Any]:
    return {"self_ref": f"#/texts/{n}", "label": "text", "text": text, "prov": [_prov(page)]}


class TestItemsByRef:
    def test_an_item_without_a_self_ref_is_not_addressable(self):
        doc = _doc([_text(0), {"label": "text", "text": "orphan"}])
        assert list(_items_by_ref(doc, READER)) == ["#/texts/0"]


class TestHeadingPaths:
    @staticmethod
    def paths(*items):
        doc = _doc(items)
        by_ref = _items_by_ref(doc, READER)
        return _heading_paths(list(by_ref), by_ref, {})

    def test_a_peer_heading_closes_the_section_before_it(self):
        heading_path, section_end = self.paths(
            _heading(0, 1, "A"), _text(1), _heading(2, 1, "B"), _text(3)
        )
        assert section_end == {"#/texts/0": 2, "#/texts/2": 4}
        assert heading_path["#/texts/1"] == ["A"]
        assert heading_path["#/texts/3"] == ["B"]

    def test_a_deeper_heading_nests_and_its_section_ends_with_its_parent(self):
        heading_path, section_end = self.paths(
            _heading(0, 1, "A"), _heading(1, 2, "A.1"), _text(2), _heading(3, 1, "B")
        )
        assert heading_path["#/texts/2"] == ["A", "A.1"]
        assert section_end["#/texts/1"] == 3
        assert section_end["#/texts/0"] == 3

    def test_a_skipped_level_still_nests(self):
        heading_path, _ = self.paths(_heading(0, 1, "A"), _heading(1, 3, "A.x"), _text(2))
        assert heading_path["#/texts/2"] == ["A", "A.x"]

    def test_a_heading_carries_only_its_ancestors(self):
        heading_path, _ = self.paths(_heading(0, 1, "A"), _heading(1, 2, "A.1"))
        assert heading_path["#/texts/1"] == ["A"]

    def test_text_before_any_heading_has_no_breadcrumb(self):
        heading_path, section_end = self.paths(_text(0), _heading(1, 1, "A"))
        assert heading_path["#/texts/0"] == []
        assert section_end == {"#/texts/1": 2}


class TestPageSizes:
    def test_only_pages_with_a_full_size_are_kept(self):
        doc = _doc(
            [_text(0)],
            pages={
                "1": {"page_no": 1, "size": {"width": 612, "height": 792}},
                "2": {"page_no": 2},
                "3": {"page_no": 3, "size": {"width": 0, "height": 792}},
                "x": {"page_no": 4, "size": {"width": 1, "height": 1}},
            },
        )
        assert _page_sizes(doc, READER) == {1: (612.0, 792.0)}


class TestProvenance:
    def test_an_element_without_a_page_is_left_out(self):
        doc = _doc([_text(0, page=None), _text(1, page=2)])
        provenance = _provenance(_items_by_ref(doc, READER), {}, READER, {})
        assert provenance.page_of == {"#/texts/1": 2}
        assert set(provenance.bbox_of) == {"#/texts/1"}

    def test_a_box_carries_its_page_size_when_known(self):
        doc = _doc([_text(0, page=2)])
        provenance = _provenance(_items_by_ref(doc, READER), {}, READER, {2: (612.0, 792.0)})
        box = provenance.bbox_of["#/texts/0"]
        assert (box.page, box.page_width, box.page_height) == (2, 612.0, 792.0)

    def test_an_inline_group_takes_the_provenance_of_its_runs(self):
        run_one = _text(1, "run one", page=1)
        run_two = _text(2, "run two", page=2)
        group = {
            "self_ref": "#/groups/0",
            "label": "inline",
            "children": [{"$ref": "#/texts/1"}, {"$ref": "#/texts/2"}],
        }
        doc = _doc([run_one, run_two], groups=[group], body=["#/groups/0"])
        index = build_index(doc, READER)
        assert index.order == ["#/groups/0"]
        assert index.page_of["#/groups/0"] == 1
        assert index.pages_of["#/groups/0"] == frozenset({1, 2})
        assert [box.page for box in index.boxes_of["#/groups/0"]] == [1, 2]


class TestPageNumbers:
    def test_a_page_only_an_element_mentions_is_still_a_page(self):
        doc = _doc(
            [_text(0, page=1), _text(1, page=3)],
            pages={"1": {"page_no": 1, "size": {"width": 612, "height": 792}}},
        )
        assert build_index(doc, READER).page_numbers == [1, 3]
