"""Tests for the navigation domain — anchor grammar and pure projections.

Covers `domain.navigation` (URI grammar, quote hashing) and
`domain.navigation_builder` (index, outline, resolution, rendering) against
the shared docling fixtures. No repository, no service, no MCP.
"""

from __future__ import annotations

import re

import pytest

from domain.navigation import (
    AnchorParseError,
    DocumentAnchor,
    estimate_tokens,
    normalise_quote,
    quote_hash,
)
from domain.navigation_builder import (
    build_index,
    build_outline,
    element_text,
    page_ref,
    parse_page_ref,
    render_markdown,
    resolve,
    section_refs,
)
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
