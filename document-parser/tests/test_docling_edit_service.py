"""Tests for the experimental DoclingEditService."""

from __future__ import annotations

import json

import pytest
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.labels import DocItemLabel, GroupLabel

from domain.models import AnalysisJob, AnalysisStatus, Document
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository
from services.docling_edit_service import DoclingEditService


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()
    yield


@pytest.fixture
def repos():
    return {
        "documents": SqliteDocumentRepository(),
        "analyses": SqliteAnalysisRepository(),
    }


@pytest.fixture
def service(repos):
    return DoclingEditService(repos["documents"], repos["analyses"])


async def _seed_analysis(repos) -> tuple[Document, AnalysisJob, dict[str, str]]:
    doc = Document(id="doc-1", filename="test.pdf", storage_path="/tmp/test.pdf")
    await repos["documents"].insert(doc)

    parsed = DoclingDocument(name="Editable")
    list_group = parsed.add_list_group(name="List")
    section = parsed.add_group(label=GroupLabel.SECTION, name="Section")
    text_a = parsed.add_text(parent=list_group, label=DocItemLabel.TEXT, text="alpha")
    text_b = parsed.add_text(parent=list_group, label=DocItemLabel.TEXT, text="beta")

    analysis = AnalysisJob(
        id="a-1",
        document_id=doc.id,
        status=AnalysisStatus.COMPLETED,
        content_markdown=parsed.export_to_markdown(),
        content_html=parsed.export_to_html(),
        pages_json="[]",
        document_json=json.dumps(parsed.export_to_dict()),
        chunks_json="[]",
    )
    await repos["analyses"].insert(analysis)
    await repos["analyses"].update_status(analysis)
    return (
        doc,
        analysis,
        {
            "list": list_group.self_ref,
            "section": section.self_ref,
            "text_a": text_a.self_ref,
            "text_b": text_b.self_ref,
        },
    )


class TestEditSession:
    async def test_edit_text_then_undo_redo(self, service, repos):
        _, _, refs = await _seed_analysis(repos)

        edited = await service.edit_text("doc-1", refs["text_a"], "alpha updated")
        edited_doc = json.loads(edited["documentJson"])
        assert edited["hasChanges"] is True
        assert edited_doc["texts"][0]["text"] == "alpha updated"

        undone = await service.undo("doc-1")
        undone_doc = json.loads(undone["documentJson"])
        assert undone_doc["texts"][0]["text"] == "alpha"
        assert undone["canRedo"] is True

        redone = await service.redo("doc-1")
        redone_doc = json.loads(redone["documentJson"])
        assert redone_doc["texts"][0]["text"] == "alpha updated"

    async def test_reparent_item_moves_parent_reference(self, service, repos):
        _, _, refs = await _seed_analysis(repos)

        result = await service.reparent_item("doc-1", refs["text_b"], refs["section"])
        doc_json = json.loads(result["documentJson"])
        moved = next(item for item in doc_json["texts"] if item["self_ref"] == refs["text_b"])
        assert moved["parent"]["$ref"] == refs["section"]

    async def test_merge_texts_deletes_trailing_item(self, service, repos):
        _, _, refs = await _seed_analysis(repos)

        result = await service.merge_texts("doc-1", refs["text_a"], refs["text_b"], " ")
        doc_json = json.loads(result["documentJson"])
        assert len(doc_json["texts"]) == 1
        assert doc_json["texts"][0]["text"] == "alpha beta"

    async def test_commit_creates_new_completed_analysis(self, service, repos):
        _, _, refs = await _seed_analysis(repos)

        await service.edit_text("doc-1", refs["text_a"], "alpha updated")
        committed = await service.commit("doc-1")
        saved = await repos["analyses"].find_by_id(committed.id)

        assert saved is not None
        assert saved.id != "a-1"
        assert saved.status is AnalysisStatus.COMPLETED
        assert "alpha updated" in (saved.content_markdown or "")
        assert json.loads(saved.document_json or "{}")["texts"][0]["text"] == "alpha updated"
