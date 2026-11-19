"""The shared heading walk, and how each view nests the same document.

The outline, the parse index, the chunk tree and the editor tree all nest by
`nest_by_heading`, each with its own reading of what a heading is and which
level it has. The per-view tests pin the edge cases so the shared walk cannot
quietly change one of them: text before the first heading, a level jump, a
title after a section, an empty document, and a heading with no usable level.
"""

from __future__ import annotations

from typing import Any

import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument

from domain.heading_tree import nest_by_heading
from domain.outline_builder import build_outline
from domain.parse_index import build_index
from infra.docling_analysis_engine import DoclingAnalysisEngine
from infra.docling_tree import DoclingTreeReader
from services.chunk_service import _build_tree_nodes

# Reading order of the shared fixture: (label, level, text). It has text
# before any heading, an H1 -> H3 jump, an H2 that closes the H3, and a
# title after the sections.
_ITEMS: list[tuple[str, int | None, str]] = [
    ("text", None, "Intro"),
    ("section_header", 1, "A"),
    ("text", None, "a"),
    ("section_header", 3, "C"),
    ("text", None, "c"),
    ("section_header", 2, "B"),
    ("text", None, "b"),
    ("title", None, "T"),
    ("text", None, "t"),
]

# Every view nests it the same way.
_EXPECTED_SHAPE = [
    ("Intro", []),
    ("A", [("a", []), ("C", [("c", [])]), ("B", [("b", [])])]),
    ("T", [("t", [])]),
]


def _payload(items: list[tuple[str, Any, str]]) -> dict[str, Any]:
    texts = []
    for position, (label, level, text) in enumerate(items):
        entry: dict[str, Any] = {
            "self_ref": f"#/texts/{position}",
            "label": label,
            "text": text,
            "prov": [],
        }
        if level is not None:
            entry["level"] = level
        texts.append(entry)
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "headings",
        "pages": {},
        "body": {"self_ref": "#/body", "children": [{"$ref": t["self_ref"]} for t in texts]},
        "texts": texts,
        "tables": [],
        "pictures": [],
        "groups": [],
    }


# ---------------------------------------------------------------------------
# nest_by_heading
# ---------------------------------------------------------------------------


class TestNestByHeading:
    def test_items_before_the_first_heading_sit_at_the_root(self):
        nesting = nest_by_heading([None, None, 1], level_of=lambda level: level)
        assert [step.parent for step in nesting.steps] == [None, None, None]
        assert nesting.still_open == (2,)

    def test_a_level_jump_nests_under_the_open_heading(self):
        nesting = nest_by_heading([1, 3, None, 2, None], level_of=lambda level: level)
        assert [step.parent for step in nesting.steps] == [None, 0, 1, 0, 3]
        assert nesting.steps[3].closed == (1,)
        assert nesting.steps[4].ancestors == (0, 3)

    def test_a_heading_closes_its_level_and_deeper_innermost_first(self):
        nesting = nest_by_heading([1, 2, 3, 0], level_of=lambda level: level)
        assert nesting.steps[3].closed == (2, 1, 0)
        assert nesting.steps[3].parent is None
        assert nesting.still_open == (3,)

    def test_an_empty_walk(self):
        nesting = nest_by_heading([], level_of=lambda level: level)
        assert nesting.steps == ()
        assert nesting.still_open == ()

    def test_a_refused_heading_closes_but_does_not_open(self):
        nesting = nest_by_heading(
            [1, 2, None, 2],
            level_of=lambda level: level,
            may_open=lambda open_levels: len(open_levels) < 1,
        )
        assert [step.opened for step in nesting.steps] == [True, False, False, False]
        # The text after the refused H2 belongs to the H1.
        assert nesting.steps[2].parent == 0
        assert nesting.still_open == (0,)

    def test_may_open_sees_the_levels_left_open(self):
        seen: list[tuple[int, ...]] = []

        def record(open_levels: tuple[int, ...]) -> bool:
            seen.append(open_levels)
            return True

        nest_by_heading([0, 1, 3, 2], level_of=lambda level: level, may_open=record)
        assert seen == [(), (0,), (0, 1), (0, 1)]


# ---------------------------------------------------------------------------
# Parse index (heading_path, section_end)
# ---------------------------------------------------------------------------


class TestParseIndexNesting:
    def test_breadcrumbs_and_section_ends(self):
        index = build_index(_payload(_ITEMS), DoclingTreeReader())
        refs = [f"#/texts/{position}" for position in range(len(_ITEMS))]
        assert [index.heading_path[ref] for ref in refs] == [
            [],
            [],
            ["A"],
            ["A"],
            ["A", "C"],
            ["A"],
            ["A", "B"],
            [],
            ["T"],
        ]
        assert index.section_end == {refs[3]: 5, refs[5]: 7, refs[1]: 7, refs[7]: 9}
        # Pop order is kept: innermost first, then what the end closes.
        assert list(index.section_end) == [refs[3], refs[5], refs[1], refs[7]]

    def test_a_level_that_is_not_a_number_counts_as_one(self):
        items = [("section_header", 2, "A"), ("section_header", "x", "B"), ("text", None, "b")]
        index = build_index(_payload(items), DoclingTreeReader())
        # B reads as level 1, so it closes A instead of nesting in it.
        assert index.heading_path["#/texts/1"] == []
        assert index.heading_path["#/texts/2"] == ["B"]

    def test_a_section_header_without_level_is_level_one(self):
        items = [("section_header", 2, "A"), ("section_header", None, "B")]
        index = build_index(_payload(items), DoclingTreeReader())
        assert index.heading_path["#/texts/1"] == []

    def test_an_empty_document(self):
        index = build_index(_payload([]), DoclingTreeReader())
        assert index.heading_path == {}
        assert index.section_end == {}


# ---------------------------------------------------------------------------
# Outline (MCP map)
# ---------------------------------------------------------------------------


def _outline_shape(nodes) -> list:
    return [(node.title, _outline_shape(node.children)) for node in nodes]


class TestOutlineNesting:
    def test_sections_nest_like_the_other_views(self):
        draft = build_outline(build_index(_payload(_ITEMS), DoclingTreeReader()), depth=3)
        assert draft.mode == "sections"
        assert [node.kind for node in draft.nodes] == ["preamble", "section", "section"]
        assert _outline_shape(draft.nodes[1:]) == [
            ("A", [("C", []), ("B", [])]),
            ("T", []),
        ]
        assert [node.child_count for node in draft.nodes[1:]] == [2, 0]
        assert draft.nodes[2].level == 0

    def test_depth_one_keeps_the_children_out_but_counts_them(self):
        draft = build_outline(build_index(_payload(_ITEMS), DoclingTreeReader()), depth=1)
        assert _outline_shape(draft.nodes[1:]) == [("A", []), ("T", [])]
        assert draft.nodes[1].child_count == 2
        assert draft.depth_limited

    def test_a_title_does_not_consume_depth(self):
        items = [("title", None, "T"), ("section_header", 1, "A"), ("section_header", 2, "B")]
        draft = build_outline(build_index(_payload(items), DoclingTreeReader()), depth=1)
        assert _outline_shape(draft.nodes) == [("T", [("A", [])])]
        assert draft.depth_limited

    def test_an_empty_document_falls_back_to_pages(self):
        draft = build_outline(build_index(_payload([]), DoclingTreeReader()), depth=2)
        assert draft.mode == "pages"
        assert draft.nodes == []


# ---------------------------------------------------------------------------
# Chunk tree (`ChunkService.get_tree`)
# ---------------------------------------------------------------------------


def _chunk_tree_shape(nodes: list[dict]) -> list:
    return [(node["label"], _chunk_tree_shape(node["children"])) for node in nodes]


class TestChunkTreeNesting:
    def test_nests_like_the_other_views(self):
        tree = _build_tree_nodes(_payload(_ITEMS), DoclingTreeReader())
        assert _chunk_tree_shape(tree) == _EXPECTED_SHAPE
        assert [node["type"] for node in tree] == ["text", "section_header", "title"]

    def test_a_section_header_without_level_is_level_one(self):
        items = [("section_header", 2, "A"), ("section_header", None, "B")]
        tree = _build_tree_nodes(_payload(items), DoclingTreeReader())
        assert _chunk_tree_shape(tree) == [("A", []), ("B", [])]

    def test_a_level_that_is_not_a_number_fails(self):
        # Unlike the parse index, the chunk tree has never guessed a level.
        items = [("section_header", 1, "A"), ("section_header", "x", "B")]
        with pytest.raises(ValueError):
            _build_tree_nodes(_payload(items), DoclingTreeReader())

    def test_an_empty_document(self):
        assert _build_tree_nodes(_payload([]), DoclingTreeReader()) == []


# ---------------------------------------------------------------------------
# Editor tree (Docling projector)
# ---------------------------------------------------------------------------


def _editor_tree_shape(nodes) -> list:
    return [(node.label, _editor_tree_shape(node.children)) for node in nodes]


def _project_tree(doc: DoclingDocument):
    projected = DoclingAnalysisEngine().project(
        doc.model_dump_json(), base_analysis_id="base", commands=[]
    )
    return projected.tree


class TestEditorTreeNesting:
    def test_nests_like_the_other_views(self):
        doc = DoclingDocument(name="headings")
        for label, level, text in _ITEMS:
            if label == "title":
                doc.add_title(text=text)
            elif label == "section_header":
                doc.add_heading(text=text, level=level)
            else:
                doc.add_text(label=DocItemLabel.TEXT, text=text)
        tree = _project_tree(doc)
        assert _editor_tree_shape(tree) == _EXPECTED_SHAPE
        assert [node.type for node in tree] == ["text", "section_header", "title"]

    def test_an_empty_document(self):
        assert _project_tree(DoclingDocument(name="empty")) == ()
