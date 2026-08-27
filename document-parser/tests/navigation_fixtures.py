"""Hand-crafted `DoclingDocument` payloads for the navigation tests.

Kept beside the tests that need them (the codebase's convention is a literal
per test module) but shared here because the domain, service and MCP layers
all need the *same* document to assert consistent refs, pages and quotes.

`SECTIONED` — a title, two chapters, a nested sub-section, a table, and a
figure with a caption, spanning two pages. `FLAT` — no heading at all, which
is what most scanned PDFs look like and what forces the page fallback.
"""

from __future__ import annotations

from typing import Any


def _prov(page: int, top: float) -> list[dict[str, Any]]:
    return [
        {
            "page_no": page,
            "bbox": {"l": 72.0, "t": top, "r": 523.0, "b": top + 42.0, "coord_origin": "TOPLEFT"},
            "charspan": [0, 10],
        }
    ]


SECTIONED: dict[str, Any] = {
    "schema_name": "DoclingDocument",
    "version": "1.0.0",
    "name": "contrat",
    "pages": {
        "1": {"page_no": 1, "size": {"width": 612.0, "height": 792.0}},
        "2": {"page_no": 2, "size": {"width": 612.0, "height": 792.0}},
    },
    "body": {
        "self_ref": "#/body",
        "children": [
            {"$ref": "#/texts/0"},
            {"$ref": "#/texts/1"},
            {"$ref": "#/texts/2"},
            {"$ref": "#/texts/3"},
            {"$ref": "#/texts/4"},
            {"$ref": "#/tables/0"},
            {"$ref": "#/pictures/0"},
            {"$ref": "#/texts/6"},
            {"$ref": "#/texts/7"},
        ],
    },
    "texts": [
        {
            "self_ref": "#/texts/0",
            "label": "title",
            "text": "Contrat de prestation",
            "prov": _prov(1, 80.0),
        },
        {
            "self_ref": "#/texts/1",
            "label": "section_header",
            "level": 1,
            "text": "Article 12 — Résiliation",
            "prov": _prov(1, 140.0),
        },
        {
            "self_ref": "#/texts/2",
            "label": "text",
            "text": "Chaque partie peut résilier le contrat.",
            "prov": _prov(1, 190.0),
        },
        {
            "self_ref": "#/texts/3",
            "label": "section_header",
            "level": 2,
            "text": "12.2 Préavis",
            "prov": _prov(1, 240.0),
        },
        {
            "self_ref": "#/texts/4",
            "label": "text",
            "text": "Le préavis est de trois mois à compter de la notification.",
            "prov": _prov(1, 290.0),
        },
        {
            "self_ref": "#/texts/5",
            "label": "caption",
            "text": "Figure 1 — Processus de résiliation",
            "prov": _prov(2, 400.0),
        },
        {
            "self_ref": "#/texts/6",
            "label": "section_header",
            "level": 1,
            "text": "Article 13 — Facturation",
            "prov": _prov(2, 500.0),
        },
        {
            "self_ref": "#/texts/7",
            "label": "text",
            "text": "Les factures sont émises mensuellement.",
            "prov": _prov(2, 560.0),
        },
    ],
    "tables": [
        {
            "self_ref": "#/tables/0",
            "label": "table",
            "prov": _prov(2, 200.0),
            "data": {
                "num_rows": 2,
                "num_cols": 2,
                "table_cells": [
                    {"start_row_offset_idx": 0, "start_col_offset_idx": 0, "text": "Motif"},
                    {"start_row_offset_idx": 0, "start_col_offset_idx": 1, "text": "Préavis"},
                    {"start_row_offset_idx": 1, "start_col_offset_idx": 0, "text": "Faute grave"},
                    {"start_row_offset_idx": 1, "start_col_offset_idx": 1, "text": "Aucun"},
                ],
            },
        }
    ],
    "pictures": [
        {
            "self_ref": "#/pictures/0",
            "label": "picture",
            "prov": _prov(2, 330.0),
            "captions": [{"$ref": "#/texts/5"}],
        }
    ],
    "groups": [],
}

FLAT: dict[str, Any] = {
    "schema_name": "DoclingDocument",
    "version": "1.0.0",
    "name": "scan",
    "pages": {
        "1": {"page_no": 1, "size": {"width": 612.0, "height": 792.0}},
        "2": {"page_no": 2, "size": {"width": 612.0, "height": 792.0}},
    },
    "body": {
        "self_ref": "#/body",
        "children": [
            {"$ref": "#/texts/3"},
            {"$ref": "#/texts/0"},
            {"$ref": "#/texts/1"},
            {"$ref": "#/texts/4"},
            {"$ref": "#/texts/2"},
        ],
    },
    "texts": [
        {
            "self_ref": "#/texts/0",
            "label": "text",
            "text": "Première ligne du scan.",
            "prov": _prov(1, 100.0),
        },
        {
            "self_ref": "#/texts/1",
            "label": "text",
            "text": "Deuxième ligne du scan.",
            "prov": _prov(1, 160.0),
        },
        {
            "self_ref": "#/texts/2",
            "label": "text",
            "text": "Une ligne sur la page deux.",
            "prov": _prov(2, 100.0),
        },
        {
            "self_ref": "#/texts/3",
            "label": "page_header",
            "text": "CONFIDENTIEL",
            "prov": _prov(1, 40.0),
        },
        {
            "self_ref": "#/texts/4",
            "label": "page_footer",
            "text": "Page 1 sur 9",
            "prov": _prov(1, 740.0),
        },
    ],
    "tables": [],
    "pictures": [],
    "groups": [],
}


# A parse with everything the hand-made fixtures above are too tidy to have:
# running headers/footers, an element straddling a page break, a picture with
# internal label children (pruned by the collapse index), a `grid`-shaped
# table containing a pipe, and headings that skip a level — which docling does
# routinely, because it reads visual hierarchy, not a numbering scheme.
MESSY: dict[str, Any] = {
    "schema_name": "DoclingDocument",
    "version": "1.0.0",
    "name": "messy",
    "pages": {
        "1": {"page_no": 1, "size": {"width": 612.0, "height": 792.0}},
        "2": {"page_no": 2, "size": {"width": 612.0, "height": 792.0}},
    },
    "body": {
        "self_ref": "#/body",
        "children": [
            {"$ref": "#/texts/0"},
            {"$ref": "#/texts/1"},
            {"$ref": "#/texts/2"},
            {"$ref": "#/texts/3"},
            {"$ref": "#/texts/4"},
            {"$ref": "#/tables/0"},
            {"$ref": "#/pictures/0"},
        ],
    },
    "texts": [
        {
            "self_ref": "#/texts/0",
            "label": "page_header",
            "text": "CONFIDENTIEL",
            "prov": _prov(1, 20.0),
        },
        {
            "self_ref": "#/texts/1",
            "label": "section_header",
            "level": 1,
            "text": "Chapitre A",
            "prov": _prov(1, 80.0),
        },
        {
            # Skipped level: docling jumps h1 -> h3 when the visual hierarchy says so.
            "self_ref": "#/texts/2",
            "label": "section_header",
            "level": 3,
            "text": "A.1 Sous-section",
            "prov": _prov(1, 140.0),
        },
        {
            # Straddles the page break: two provs, pages 1 and 2.
            "self_ref": "#/texts/3",
            "label": "text",
            "text": "Ce paragraphe commence page un et se termine page deux.",
            "prov": [
                {"page_no": 1, "bbox": {"l": 72.0, "t": 700.0, "r": 523.0, "b": 780.0}},
                {"page_no": 2, "bbox": {"l": 72.0, "t": 40.0, "r": 523.0, "b": 90.0}},
            ],
        },
        {
            "self_ref": "#/texts/4",
            "label": "page_footer",
            "text": "page 2/2",
            "prov": _prov(2, 760.0),
        },
        {
            "self_ref": "#/texts/5",
            "label": "caption",
            "text": "Figure A — schéma",
            "prov": _prov(2, 300.0),
        },
        {
            "self_ref": "#/texts/6",
            "label": "text",
            "text": "étiquette interne",
            "prov": _prov(2, 260.0),
        },
    ],
    "tables": [
        {
            "self_ref": "#/tables/0",
            "label": "table",
            "prov": _prov(2, 150.0),
            "data": {
                "grid": [
                    [{"text": "Colonne | pipe"}, {"text": "Valeur"}],
                    [{"text": "Ligne 1"}, {"text": "42"}],
                ]
            },
        }
    ],
    "pictures": [
        {
            "self_ref": "#/pictures/0",
            "label": "picture",
            "prov": _prov(2, 200.0),
            "captions": [{"$ref": "#/texts/5"}],
            # Internal labels extracted from the figure — collapse index drops them.
            "children": [{"$ref": "#/texts/6"}],
        }
    ],
    "groups": [],
}


# ---------------------------------------------------------------------------
# Builders — shared by the domain, service and MCP adapter tests so all three
# assert against the same refs, quotes and pages.
# ---------------------------------------------------------------------------

DOC_ID = "doc-1"
JOB_ID = "an-1"
PREAVIS_REF = "#/texts/4"
PREAVIS_TEXT = "Le préavis est de trois mois à compter de la notification."


def make_document(doc_id: str = DOC_ID, filename: str = "contrat.pdf"):
    from datetime import UTC, datetime

    from domain.models import Document

    return Document(
        id=doc_id,
        filename=filename,
        page_count=2,
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def make_job(payload: dict | None = None, job_id: str = JOB_ID, doc_id: str = DOC_ID):
    import json

    from domain.models import AnalysisJob, AnalysisStatus

    return AnalysisJob(
        id=job_id,
        document_id=doc_id,
        status=AnalysisStatus.COMPLETED,
        document_json=json.dumps(payload or SECTIONED),
    )


_UNSET = object()


class FakeRasterizer:
    """A `PageRasterizer` that renders blank pages of a fixed size.

    The port exists so the citation view can be tested without poppler; this
    is what it bought. `renders` records every (page, dpi) asked for, which is
    how the dpi ladder is asserted.
    """

    def __init__(self, *, width: int = 1275, height: int = 1650, png_bytes: int | None = None):
        self._size = (width, height)
        self._forced = png_bytes
        self.renders: list[tuple[int, int]] = []
        self.formats: list[str] = []

    def render_page(self, storage_path: str, *, page: int, dpi: int) -> bytes:
        self.renders.append((page, dpi))
        return self._png(*self._size)

    def crop(self, png: bytes, box, *, fmt: str = "PNG"):
        from domain.navigation import RasterCrop

        # Clamped to the rendered page, exactly as `PdfPageRasterizer.crop`
        # does. Without it the "whole page" box the thumbnail asks for
        # (0, 0, 10_000, 10_000) produced a 10_000 x 10_000 raster — a
        # hundred megapixels of fixture per call, and a page whose reported
        # size had nothing to do with the page.
        page_width, page_height = self._size
        left, top, right, bottom = box
        left, top = max(0, min(left, page_width - 1)), max(0, min(top, page_height - 1))
        right, bottom = min(right, page_width), min(bottom, page_height)
        width, height = max(1, right - left), max(1, bottom - top)
        self.formats.append(fmt)
        raw = self._encode(width, height, fmt)
        if self._forced is not None:
            # Pad to a size the budget cannot satisfy, to drive the ladder.
            raw = raw + b"\0" * max(0, self._forced - len(raw))
        return RasterCrop(png=raw, width=width, height=height)

    @staticmethod
    def _png(width: int, height: int) -> bytes:
        return FakeRasterizer._encode(width, height, "PNG")

    @staticmethod
    def _encode(width: int, height: int, fmt: str) -> bytes:
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (max(1, width), max(1, height)), "white").save(buffer, format=fmt.upper())
        return buffer.getvalue()


def make_document_tools(
    *,
    documents=None,
    job=_UNSET,
    jobs=None,
    config=None,
    rasterizer=None,
):
    """The three document-agent services over AsyncMock repositories.

    `jobs` takes several analyses of the same document — the last one is the
    latest completed parse, the others are only reachable by pinning their id,
    which is what the anchor grammar exists for.
    """
    from unittest.mock import AsyncMock

    from infra.docling_tree import DoclingTreeReader
    from services.citation_image_service import CitationImageService
    from services.citation_service import CitationService
    from services.document_tools import DocumentTools
    from services.navigation_config import NavigationConfig
    from services.navigation_service import NavigationService
    from services.parse_loader import ParseLoader

    docs = documents if documents is not None else [make_document()]
    if jobs is not None:
        analyses = list(jobs)
    elif job is _UNSET:
        analyses = [make_job()]
    elif job is None:
        analyses = []
    else:
        analyses = [job]
    latest = analyses[-1] if analyses else None

    document_repo = AsyncMock()
    document_repo.find_all = AsyncMock(return_value=docs)
    document_repo.find_by_id = AsyncMock(
        side_effect=lambda doc_id: next((d for d in docs if d.id == doc_id), None)
    )
    analysis_repo = AsyncMock()
    analysis_repo.find_latest_completed_by_document = AsyncMock(return_value=latest)
    analysis_repo.find_by_id = AsyncMock(
        side_effect=lambda job_id: next((j for j in analyses if j.id == job_id), None)
    )

    settings = config or NavigationConfig(studio_base_url="http://localhost:3000")
    parses = ParseLoader(
        document_repo=document_repo,
        analysis_repo=analysis_repo,
        tree_reader=DoclingTreeReader(),
        config=settings,
    )
    citations = CitationService(parses=parses, config=settings)
    return DocumentTools(
        navigation=NavigationService(parses=parses, citations=citations, config=settings),
        citations=citations,
        images=CitationImageService(
            parses=parses, rasterizer=rasterizer or FakeRasterizer(), config=settings
        ),
    )


def make_navigation_service(**kwargs):
    """The reading service alone — most tests only need this one."""
    return make_document_tools(**kwargs).navigation


def anchor_uri(ref: str, *, doc_id: str = DOC_ID, job_id: str = JOB_ID) -> str:
    from domain.anchors import DocumentAnchor

    return DocumentAnchor(doc_id, job_id, ref).uri
