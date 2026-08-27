"""Tests for the navigation domain — anchor grammar and pure projections.

Covers `domain.navigation` (URI grammar, quote hashing) and
`domain.navigation_builder` (index, outline, resolution, rendering) against
the shared docling fixtures. No repository, no service, no MCP.
"""

from __future__ import annotations

import re

import pytest

from domain.anchors import AnchorParseError, DocumentAnchor, normalise_quote, quote_hash
from domain.element_reader import element_text, render_markdown, resolve, section_refs
from domain.navigation import BoundingBox, estimate_tokens
from domain.outline_builder import build_outline
from domain.parse_index import build_index, page_ref, parse_page_ref
from domain.spans import is_span, parse_span, span_members
from infra.docling_tree import DoclingTreeReader
from tests.navigation_fixtures import FLAT, MESSY, SECTIONED


def _index(payload=None):
    return build_index(payload or SECTIONED, DoclingTreeReader())


class TestAnchorGrammar:
    def test_round_trips(self):
        anchor = DocumentAnchor("doc-1", "an-7", "#/texts/91")
        assert anchor.uri == "dstudio://doc/doc-1@an-7#/texts/91"
        assert DocumentAnchor.parse(anchor.uri) == anchor

    def test_keeps_the_full_ref_including_slashes(self):
        parsed = DocumentAnchor.parse("dstudio://doc/d@v#/tables/3")
        assert parsed.ref == "#/tables/3"

    def test_accepts_a_virtual_page_ref(self):
        parsed = DocumentAnchor.parse(f"dstudio://doc/d@v{page_ref(7)}")
        assert parse_page_ref(parsed.ref) == 7

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "not-an-anchor",
            "dstudio://doc/d#/texts/1",  # no version
            "dstudio://doc/d@v",  # no ref
            "http://doc/d@v#/texts/1",  # wrong scheme
        ],
    )
    def test_rejects_malformed_input(self, bad: str):
        with pytest.raises(AnchorParseError, match="Malformed anchor"):
            DocumentAnchor.parse(bad)

    def test_error_message_teaches_the_shape(self):
        with pytest.raises(AnchorParseError, match=r"dstudio://doc/\{document_id\}"):
            DocumentAnchor.parse("oops")


class TestQuoteHashing:
    def test_is_insensitive_to_whitespace_reflow(self):
        assert quote_hash("le préavis\n  est de trois mois") == quote_hash(
            "le préavis est de trois mois"
        )

    def test_differs_on_a_changed_word(self):
        assert quote_hash("trois mois") != quote_hash("six mois")

    def test_normalisation_strips_and_collapses(self):
        assert normalise_quote("  a \n\t b  ") == "a b"

    def test_estimate_tokens_is_never_zero_for_text(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("a") == 1
        assert estimate_tokens("x" * 400) == 100


class TestIndex:
    def test_reading_order_skips_captions_hanging_off_a_picture(self):
        index = _index()
        assert index.order == [
            "#/texts/0",
            "#/texts/1",
            "#/texts/2",
            "#/texts/3",
            "#/texts/4",
            "#/tables/0",
            "#/pictures/0",
            "#/texts/6",
            "#/texts/7",
        ]

    def test_heading_breadcrumbs_follow_the_stack(self):
        index = _index()
        assert index.heading_path["#/texts/4"] == [
            "Contrat de prestation",
            "Article 12 — Résiliation",
            "12.2 Préavis",
        ]
        # A sibling chapter closes the previous one rather than nesting in it.
        assert index.heading_path["#/texts/7"] == [
            "Contrat de prestation",
            "Article 13 — Facturation",
        ]

    def test_provenance_carries_page_and_bbox(self):
        index = _index()
        bbox = index.bbox_of["#/texts/4"]
        assert index.page_of["#/texts/4"] == 1
        assert (bbox.left, bbox.top, bbox.right, bbox.bottom) == (72.0, 290.0, 523.0, 332.0)
        assert bbox.coord_origin == "TOPLEFT"

    def test_page_count_comes_from_the_pages_map(self):
        assert _index().page_count == 2


class TestOutline:
    def test_sections_mode_nests_by_heading_level(self):
        draft = build_outline(_index(), depth=2)
        assert draft.mode == "sections"
        assert draft.depth_limited is False
        assert draft.node_limited is False
        assert [node.title for node in draft.nodes] == ["Contrat de prestation"]
        chapters = draft.nodes[0].children
        assert [c.title for c in chapters] == [
            "Article 12 — Résiliation",
            "Article 13 — Facturation",
        ]
        assert [c.title for c in chapters[0].children] == ["12.2 Préavis"]
        assert draft.total_est_tokens > 0

    def test_est_tokens_aggregate_the_whole_subtree(self):
        draft = build_outline(_index(), depth=2)
        root = draft.nodes[0]
        assert root.est_tokens == draft.total_est_tokens
        assert root.est_tokens > root.children[0].est_tokens

    def test_depth_elides_deeper_levels_and_says_so(self):
        draft = build_outline(_index(), depth=1)
        assert draft.depth_limited is True
        assert draft.node_limited is False
        assert draft.nodes[0].children[0].children == []
        # The elided subsection still counts towards its parent's budget.
        assert draft.nodes[0].children[0].est_tokens > 0

    def test_node_cap_is_reported_apart_from_depth(self):
        draft = build_outline(_index(), depth=3, max_nodes=2)
        assert draft.node_limited is True
        assert sum(1 + len(n.children) for n in draft.nodes) <= 3

    def test_child_count_reports_direct_subsections(self):
        draft = build_outline(_index(), depth=1)
        assert draft.nodes[0].child_count == 2
        assert draft.nodes[0].children[0].child_count == 1

    def test_child_count_survives_a_skipped_heading_level(self):
        # docling reads visual hierarchy, so h1 -> h3 is routine. The count must
        # agree with the nesting the outline actually builds, or a payload
        # advertises `child_count: 0` next to a non-empty `children` list.
        draft = build_outline(_index(MESSY), depth=2)
        chapter = draft.nodes[0]
        assert chapter.title == "Chapitre A"
        assert [c.title for c in chapter.children] == ["A.1 Sous-section"]
        assert chapter.child_count == 1

    def test_falls_back_to_pages_without_headings(self):
        draft = build_outline(_index(FLAT), depth=2)
        assert draft.mode == "pages"
        assert [node.ref for node in draft.nodes] == ["#/pages/1", "#/pages/2"]
        assert draft.nodes[0].title.startswith("Première ligne")
        assert draft.nodes[1].est_tokens > 0


class TestResolution:
    def test_resolves_text_page_and_breadcrumbs(self):
        element = resolve(_index(), "#/texts/4")
        assert element is not None
        assert element.text.startswith("Le préavis est de trois mois")
        assert element.page == 1
        assert element.headings[-1] == "12.2 Préavis"

    def test_unknown_ref_resolves_to_none(self):
        assert resolve(_index(), "#/texts/999") is None

    def test_unknown_page_resolves_to_none(self):
        assert resolve(_index(), "#/pages/99") is None

    def test_section_of_a_heading_stops_at_the_next_peer(self):
        refs = section_refs(_index(), "#/texts/1")
        assert refs == [
            "#/texts/1",
            "#/texts/2",
            "#/texts/3",
            "#/texts/4",
            "#/tables/0",
            "#/pictures/0",
        ]
        assert "#/texts/6" not in refs  # Article 13 is a sibling, not content

    def test_section_of_a_leaf_is_itself(self):
        assert section_refs(_index(), "#/texts/2") == ["#/texts/2"]

    def test_page_ref_collects_everything_on_that_page(self):
        assert section_refs(_index(FLAT), "#/pages/2") == ["#/texts/2"]

    def test_table_renders_as_markdown(self):
        text = element_text(_index(), "#/tables/0")
        assert text.splitlines()[0] == "| Motif | Préavis |"
        assert "| Faute grave | Aucun |" in text

    def test_picture_falls_back_to_its_caption(self):
        assert element_text(_index(), "#/pictures/0") == (
            "[figure] Figure 1 — Processus de résiliation"
        )

    def test_render_markdown_keeps_heading_structure(self):
        index = _index()
        elements = [resolve(index, ref) for ref in ("#/texts/1", "#/texts/2")]
        rendered = render_markdown(elements)
        assert rendered.startswith("## Article 12 — Résiliation")
        assert rendered.endswith("Chaque partie peut résilier le contrat.")


class TestPageProvenance:
    def test_an_element_spanning_a_break_belongs_to_both_pages(self):
        index = _index(MESSY)
        assert sorted(index.pages_of["#/texts/3"]) == [1, 2]
        # It starts on page 1 — that is what a citation reports…
        assert index.page_of["#/texts/3"] == 1
        # …but reading page 2 must still surface it: it is visible there.
        assert "#/texts/3" in section_refs(index, "#/pages/2")
        assert "#/texts/3" in section_refs(index, "#/pages/1")

    def test_bbox_carries_the_page_dimensions(self):
        bbox = resolve(_index(MESSY), "#/texts/1").bbox
        assert (bbox.page_width, bbox.page_height) == (612.0, 792.0)

    def test_running_headers_and_footers_carry_no_readable_text(self):
        index = _index(MESSY)
        assert element_text(index, "#/texts/0") == ""  # page_header
        assert element_text(index, "#/texts/4") == ""  # page_footer
        # And they never reach a rendered excerpt.
        elements = [resolve(index, ref) for ref in section_refs(index, "#/pages/2")]
        assert "page 2/2" not in render_markdown(elements)


class TestTableRendering:
    def test_renders_the_grid_payload_variant(self):
        text = element_text(_index(MESSY), "#/tables/0")
        assert text.splitlines()[1] == "| --- | --- |"
        assert "| Ligne 1 | 42 |" in text

    def test_escapes_a_pipe_inside_a_cell(self):
        # An unescaped pipe silently shifts every column of the table the
        # agent is reading.
        text = element_text(_index(MESSY), "#/tables/0")
        header = text.splitlines()[0]
        assert r"Colonne \| pipe" in header
        # Three *unescaped* pipes: the cell's own pipe no longer opens a column.
        assert len(re.findall(r"(?<!\\)\|", header)) == 3

    def test_figure_children_are_pruned_but_the_caption_survives(self):
        index = _index(MESSY)
        # The internal label extracted from the figure is not a reading-order node.
        assert "#/texts/6" not in index.order
        assert element_text(index, "#/pictures/0") == "[figure] Figure A — schéma"


class TestPartialMetadata:
    """What a real scan looks like: provenance without page geometry."""

    def test_a_page_missing_its_size_still_appears_on_the_map(self):
        import copy

        payload = copy.deepcopy(FLAT)
        payload["pages"]["2"] = {"page_no": 2}  # no `size`
        index = _index(payload)
        draft = build_outline(index, depth=2)
        # The page fallback exists for scans, where this metadata is the first
        # thing missing — dropping the page would hide its content entirely.
        assert index.page_numbers == [1, 2]
        assert [node.ref for node in draft.nodes] == ["#/pages/1", "#/pages/2"]
        assert resolve(index, "#/pages/2") is not None
        assert section_refs(index, "#/pages/2") == ["#/texts/2"]

    def test_an_unreadable_table_says_so_instead_of_reading_empty(self):
        import copy

        from domain.element_reader import UNREADABLE_TABLE

        payload = copy.deepcopy(SECTIONED)
        # A payload shape this version does not know — what a docling upgrade
        # looks like from here.
        payload["tables"][0]["data"] = {"cells_v2": [{"content": "Motif"}]}
        text = element_text(_index(payload), "#/tables/0")
        # Not "": an empty element is skipped by the reader, so the agent would
        # be told the table is empty rather than that it could not be read.
        assert text == UNREADABLE_TABLE

    def test_a_genuinely_empty_table_still_reads_empty(self):
        import copy

        payload = copy.deepcopy(SECTIONED)
        payload["tables"][0]["data"] = {}
        assert element_text(_index(payload), "#/tables/0") == ""


class TestSpanRefs:
    """A citation covering several elements — the grammar and its resolution."""

    def test_a_plain_ref_is_not_a_span(self):
        assert parse_span("#/texts/2") is None
        assert parse_span("#/pages/1") is None
        assert not is_span("#/tables/0")

    def test_the_second_endpoint_may_omit_its_hash(self):
        # `#/texts/2..#/texts/4` reads better than `#/texts/2../texts/4`, and
        # both name the same range.
        assert parse_span("#/texts/2..#/texts/4") == ("#/texts/2", "#/texts/4")
        assert parse_span("#/texts/2../texts/4") == ("#/texts/2", "#/texts/4")

    def test_a_span_covers_everything_between_its_ends_in_reading_order(self):
        index = _index()
        assert span_members(index, "#/texts/2", "#/texts/4") == [
            "#/texts/2",
            "#/texts/3",
            "#/texts/4",
        ]

    def test_reversed_endpoints_are_read_in_the_document_s_order(self):
        index = _index()
        assert span_members(index, "#/texts/4", "#/texts/2") == span_members(
            index, "#/texts/2", "#/texts/4"
        )

    def test_an_endpoint_from_another_parse_covers_nothing(self):
        # Guessing at the overlap would produce a citation nobody asked for.
        assert span_members(_index(), "#/texts/2", "#/texts/999") == []

    def test_resolving_a_span_joins_the_members_own_text(self):
        element = resolve(_index(), "#/texts/2..#/texts/4")
        assert element is not None
        assert element.label == "span"
        assert element.text == (
            "Chaque partie peut résilier le contrat.\n\n"
            "12.2 Préavis\n\n"
            "Le préavis est de trois mois à compter de la notification."
        )

    def test_a_heading_inside_a_span_keeps_its_own_words(self):
        # Not rendered markdown: a `##` prefix would put characters in the
        # citation that are nowhere in the document, and a quote crossing the
        # heading would stop verifying.
        assert "##" not in resolve(_index(), "#/texts/2..#/texts/4").text

    def test_a_span_reports_the_page_it_opens_on(self):
        element = resolve(_index(), "#/texts/4..#/tables/0")
        assert element.page == 1

    def test_a_span_s_box_covers_its_members_on_that_page(self):
        index = _index()
        element = resolve(index, "#/texts/2..#/texts/4")
        first = index.bbox_of["#/texts/2"]
        last = index.bbox_of["#/texts/4"]
        assert element.bbox.top == first.top
        assert element.bbox.bottom == last.bottom

    def test_a_span_that_straddles_a_page_break_boxes_only_the_first_page(self):
        # A rectangle spanning two pages is not a rectangle.
        index = _index()
        element = resolve(index, "#/texts/4..#/tables/0")
        assert element.bbox.page == 1
        assert element.bbox.bottom == index.bbox_of["#/texts/4"].bottom

    def test_a_span_of_nothing_readable_does_not_resolve(self):
        assert resolve(_index(), "#/texts/99..#/texts/100") is None

    def test_reading_a_span_as_a_section_yields_its_members(self):
        assert section_refs(_index(), "#/texts/2..#/texts/4") == [
            "#/texts/2",
            "#/texts/3",
            "#/texts/4",
        ]


class TestBoxUnion:
    def test_no_boxes_no_union(self):
        assert BoundingBox.union([]) is None

    def test_topleft_grows_downwards(self):
        boxes = [
            BoundingBox(page=1, left=72, top=100, right=500, bottom=140),
            BoundingBox(page=1, left=60, top=200, right=520, bottom=260),
        ]
        union = BoundingBox.union(boxes)
        assert (union.left, union.top, union.right, union.bottom) == (60, 100, 520, 260)

    def test_bottomleft_grows_upwards(self):
        # Docling's PDF-native origin: `top` is the LARGER number.
        boxes = [
            BoundingBox(page=1, left=72, top=700, right=500, bottom=660, coord_origin="BOTTOMLEFT"),
            BoundingBox(page=1, left=60, top=600, right=520, bottom=540, coord_origin="BOTTOMLEFT"),
        ]
        union = BoundingBox.union(boxes)
        assert (union.top, union.bottom) == (700, 540)

    def test_a_box_from_another_page_is_dropped_not_merged(self):
        boxes = [
            BoundingBox(page=1, left=72, top=100, right=500, bottom=140),
            BoundingBox(page=2, left=10, top=10, right=600, bottom=700),
        ]
        union = BoundingBox.union(boxes)
        assert union.page == 1
        assert (union.left, union.right) == (72, 500)

    def test_two_coordinate_origins_are_never_reconciled(self):
        boxes = [
            BoundingBox(page=1, left=72, top=100, right=500, bottom=140),
            BoundingBox(page=1, left=10, top=700, right=600, bottom=660, coord_origin="BOTTOMLEFT"),
        ]
        assert BoundingBox.union(boxes).bottom == 140
