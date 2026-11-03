"""Tests for DocumentTreeService — the Chunks view outline (#256).

Moved out of `test_chunk_service.py` with the tree itself (audit 0.7.4, 03
MAJ 3.3.2); the assertions are the ones `ChunkService.get_tree` answered.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from domain.models import AnalysisJob, AnalysisStatus, Document
from infra.docling_tree import DoclingTreeReader
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from services.chunk_errors import ChunkNotFoundError
from services.document_tree_service import DocumentTreeService
from services.navigation_errors import DocumentNotFoundError


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    monkeypatch.setattr("persistence.database.DB_PATH", str(tmp_path / "test.db"))
    await init_db()


@pytest.fixture
async def doc():
    document = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
    await SqliteDocumentRepository().insert(document)
    return document


@pytest.fixture
def repos():
    return {"documents": SqliteDocumentRepository(), "analyses": SqliteAnalysisRepository()}


@pytest.fixture
def service(repos):
    return DocumentTreeService(
        document_repo=repos["documents"],
        analysis_repo=repos["analyses"],
        tree_reader=DoclingTreeReader(),
    )


class TestGetTree:
    async def test_tree_empty_when_no_analysis(self, service, doc):
        assert await service.get_tree(doc.id) == []

    async def test_tree_uses_requested_completed_analysis(self, service, repos, doc):
        older = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        older.document_json = json.dumps(
            {
                "body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]},
                "texts": [{"self_ref": "#/texts/0", "label": "title", "text": "Older"}],
                "tables": [],
                "pictures": [],
                "groups": [],
            }
        )
        newer = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        newer.document_json = json.dumps(
            {
                "body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]},
                "texts": [{"self_ref": "#/texts/0", "label": "title", "text": "Newer"}],
                "tables": [],
                "pictures": [],
                "groups": [],
            }
        )
        await repos["analyses"].insert(older)
        await repos["analyses"].insert(newer)
        await repos["analyses"].update_status(older)
        await repos["analyses"].update_status(newer)

        tree = await service.get_tree(doc.id, older.id)

        assert tree[0]["label"] == "Older"

    async def test_tree_rejects_analysis_from_another_document(self, service, repos, doc):
        other = Document(filename="other.pdf")
        await repos["documents"].insert(other)
        analysis = AnalysisJob(document_id=other.id, status=AnalysisStatus.COMPLETED)
        await repos["analyses"].insert(analysis)

        with pytest.raises(ChunkNotFoundError):
            await service.get_tree(doc.id, analysis.id)

    async def test_tree_follows_document_hierarchy(self, service, repos, doc):
        """Title → H1 → H2 nest by heading level, leaves under their section."""
        job = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        await repos["analyses"].insert(job)
        job.document_json = json.dumps(
            {
                "body": {
                    "self_ref": "#/body",
                    "children": [
                        {"$ref": "#/texts/0"},
                        {"$ref": "#/texts/1"},
                        {"$ref": "#/texts/2"},
                        {"$ref": "#/texts/3"},
                        {"$ref": "#/texts/4"},
                        {"$ref": "#/texts/5"},
                    ],
                },
                "texts": [
                    {"self_ref": "#/texts/0", "label": "title", "text": "Doc Title"},
                    {
                        "self_ref": "#/texts/1",
                        "label": "section_header",
                        "text": "Chapter 1",
                        "level": 1,
                    },
                    {"self_ref": "#/texts/2", "label": "text", "text": "Intro paragraph"},
                    {
                        "self_ref": "#/texts/3",
                        "label": "section_header",
                        "text": "Section 1.1",
                        "level": 2,
                    },
                    {"self_ref": "#/texts/4", "label": "text", "text": "Nested paragraph"},
                    {
                        "self_ref": "#/texts/5",
                        "label": "section_header",
                        "text": "Chapter 2",
                        "level": 1,
                    },
                ],
                "tables": [],
                "pictures": [],
                "groups": [],
            }
        )
        job.completed_at = datetime.now(UTC)
        await repos["analyses"].update_status(job)
        tree = await service.get_tree(doc.id)

        # Single top-level title containing both chapters.
        assert len(tree) == 1
        title = tree[0]
        assert title["type"] == "title"
        assert title["label"] == "Doc Title"
        assert [c["label"] for c in title["children"]] == ["Chapter 1", "Chapter 2"]

        chapter1 = title["children"][0]
        # Intro paragraph then Section 1.1 (which owns the nested paragraph).
        assert [c["type"] for c in chapter1["children"]] == ["text", "section_header"]
        section_1_1 = chapter1["children"][1]
        assert [c["label"] for c in section_1_1["children"]] == ["Nested paragraph"]

        # Chapter 2 is a sibling, not a child of Section 1.1.
        chapter2 = title["children"][1]
        assert chapter2["children"] == []

    async def test_tree_keeps_list_items_under_list(self, service, repos, doc):
        """`list` containers preserve their `list_item` descendants."""
        job = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        await repos["analyses"].insert(job)
        job.document_json = json.dumps(
            {
                "body": {
                    "self_ref": "#/body",
                    "children": [{"$ref": "#/groups/0"}],
                },
                "groups": [
                    {
                        "self_ref": "#/groups/0",
                        "label": "list",
                        "children": [
                            {"$ref": "#/texts/0"},
                            {"$ref": "#/texts/1"},
                        ],
                    }
                ],
                "texts": [
                    {"self_ref": "#/texts/0", "label": "list_item", "text": "First"},
                    {"self_ref": "#/texts/1", "label": "list_item", "text": "Second"},
                ],
                "tables": [],
                "pictures": [],
            }
        )
        job.completed_at = datetime.now(UTC)
        await repos["analyses"].update_status(job)
        tree = await service.get_tree(doc.id)

        assert len(tree) == 1
        list_node = tree[0]
        assert list_node["type"] == "list"
        assert [c["label"] for c in list_node["children"]] == ["First", "Second"]


class TestTreeHeadingLevels:
    """How a heading's `level` places it in the tree (audit 0.7.4, 01 MAJ-1)."""

    @staticmethod
    async def _tree(service, repos, doc, texts: list[dict]) -> list[dict]:
        job = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        await repos["analyses"].insert(job)
        for i, text in enumerate(texts):
            text.setdefault("self_ref", f"#/texts/{i}")
        job.document_json = json.dumps(
            {
                "body": {
                    "self_ref": "#/body",
                    "children": [{"$ref": t["self_ref"]} for t in texts],
                },
                "texts": texts,
                "tables": [],
                "pictures": [],
                "groups": [],
            }
        )
        job.completed_at = datetime.now(UTC)
        await repos["analyses"].update_status(job)
        return await service.get_tree(doc.id)

    @staticmethod
    def _shape(nodes: list[dict]) -> list:
        return [(n["label"], TestTreeHeadingLevels._shape(n["children"])) for n in nodes]

    async def test_a_deeper_heading_nests_and_a_shallower_one_pops(self, service, repos, doc):
        tree = await self._tree(
            service,
            repos,
            doc,
            [
                {"label": "title", "text": "T"},
                {"label": "section_header", "text": "A", "level": 1},
                {"label": "section_header", "text": "A.1.1", "level": 3},
                {"label": "section_header", "text": "A.2", "level": 2},
                {"label": "text", "text": "p"},
                {"label": "section_header", "text": "B", "level": 1},
            ],
        )
        assert self._shape(tree) == [
            ("T", [("A", [("A.1.1", []), ("A.2", [("p", [])])]), ("B", [])]),
        ]

    @pytest.mark.parametrize("level", [None, 0, -3, 1, "1", 1.0, True])
    async def test_a_missing_or_low_level_reads_as_one(self, service, repos, doc, level):
        header = {"label": "section_header", "text": "H"}
        if level is not None:
            header["level"] = level
        tree = await self._tree(
            service,
            repos,
            doc,
            [
                {"label": "section_header", "text": "Parent", "level": 1},
                header,
            ],
        )
        assert self._shape(tree) == [("Parent", []), ("H", [])]

    @pytest.mark.parametrize("level", ["deep", "2.5", [2], {"n": 2}])
    async def test_a_non_numeric_level_reads_as_one(self, service, repos, doc, level):
        """Docling only writes an int; anything else used to raise inside the
        walk and fail the whole tree with a 500. It now reads as 1, as in the
        MCP outline (`parse_index.heading_level`)."""
        tree = await self._tree(
            service,
            repos,
            doc,
            [
                {"label": "section_header", "text": "Parent", "level": 2},
                {"label": "section_header", "text": "H", "level": level},
                {"label": "text", "text": "p"},
            ],
        )
        assert self._shape(tree) == [("Parent", []), ("H", [("p", [])])]

    async def test_a_numeric_string_level_is_read_as_its_number(self, service, repos, doc):
        tree = await self._tree(
            service,
            repos,
            doc,
            [
                {"label": "section_header", "text": "Parent", "level": 1},
                {"label": "section_header", "text": "Child", "level": "2"},
            ],
        )
        assert self._shape(tree) == [("Parent", [("Child", [])])]

    async def test_title_opens_level_zero_whatever_its_level(self, service, repos, doc):
        tree = await self._tree(
            service,
            repos,
            doc,
            [
                {"label": "section_header", "text": "H", "level": 1},
                {"label": "Title", "text": "T", "level": 5},
                {"label": "section_header", "text": "H2", "level": 1},
            ],
        )
        assert self._shape(tree) == [("H", []), ("T", [("H2", [])])]


class TestGuards:
    async def test_unknown_document_is_the_shared_404(self, service):
        with pytest.raises(DocumentNotFoundError):
            await service.get_tree("ghost")

    async def test_unreadable_document_json_gives_an_empty_tree(self, service, repos, doc):
        job = AnalysisJob(document_id=doc.id, status=AnalysisStatus.COMPLETED)
        await repos["analyses"].insert(job)
        job.document_json = "{not json"
        job.completed_at = datetime.now(UTC)
        await repos["analyses"].update_status(job)
        assert await service.get_tree(doc.id) == []
