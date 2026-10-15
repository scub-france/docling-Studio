from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    PageItem,
    ProvenanceItem,
    Size,
    TableData,
)

from domain.analysis_editing import AnalysisEditError, EditCommand
from domain.models import AnalysisJob, AnalysisStatus, Document
from infra.docling_editor import DoclingDocumentEditor
from infra.docling_projector import DoclingAnalysisProjector
from persistence import database
from persistence.analysis_edit_repo import SqliteAnalysisEditRepository
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository
from services.analysis_edit_service import AnalysisEditService


def _document() -> tuple[str, str, str]:
    doc = DoclingDocument(name="fixture")
    first = doc.add_text(label=DocItemLabel.TEXT, text="First")
    second = doc.add_text(label=DocItemLabel.TEXT, text="Second")
    doc.add_heading(text="Heading", level=1)
    return doc.model_dump_json(), first.self_ref, second.self_ref


def _realistic_document() -> str:
    """Build a text-free structural fixture resembling a parsed document."""
    doc = DoclingDocument(name="structural-fixture")
    doc.pages[1] = PageItem(page_no=1, size=Size(width=600, height=800))
    doc.pages[2] = PageItem(page_no=2, size=Size(width=600, height=800))
    prov = ProvenanceItem(
        page_no=1,
        bbox=BoundingBox(l=10, t=100, r=200, b=50, coord_origin=CoordOrigin.TOPLEFT),
        charspan=(0, 0),
    )
    doc.add_text(label=DocItemLabel.PAGE_HEADER, text="[header]", prov=prov)
    title = doc.add_title(text="[title]", prov=prov)
    section = doc.add_heading(text="[section]", level=1, prov=prov)
    paragraph = doc.add_text(label=DocItemLabel.TEXT, text="[paragraph]", parent=section, prov=prov)
    list_group = doc.add_group(label=GroupLabel.LIST, name="[list]", parent=section)
    doc.add_list_item(text="[item-a]", parent=list_group, prov=prov)
    doc.add_list_item(text="[item-b]", parent=list_group, prov=prov)
    doc.add_table(data=TableData(num_rows=1, num_cols=1, table_cells=[]), parent=section, prov=prov)
    doc.add_picture(parent=section, prov=prov)
    doc.add_text(label=DocItemLabel.PAGE_FOOTER, text="[footer]", prov=prov)
    # Deliberately retain a realistic but incorrect sibling order for repair tests.
    section.children = [section.children[-1], section.children[0], section.children[1], section.children[2]]
    assert title and paragraph
    return doc.model_dump_json()


def test_merge_preserves_logical_target_and_validates_round_trip():
    raw, first_ref, second_ref = _document()
    editor = DoclingDocumentEditor()
    result = editor.apply(
        raw,
        base_analysis_id="base",
        commands=[
            EditCommand(
                "mergeText",
                {
                    "elementIds": [f"base:{first_ref}", f"base:{second_ref}"],
                    "separator": " ",
                },
            )
        ],
    )
    assert result.logical_ids[f"base:{first_ref}"] == first_ref
    assert f"base:{second_ref}" not in result.logical_ids
    assert result.document.export_to_markdown().startswith("First Second")


def test_merge_moves_non_adjacent_items_before_merging():
    raw, first_ref, _second_ref = _document()
    third_doc = DoclingDocument.model_validate_json(raw)
    third = third_doc.add_text(label=DocItemLabel.TEXT, text="Third")
    editor = DoclingDocumentEditor()
    result = editor.apply(
        third_doc.model_dump_json(),
        base_analysis_id="base",
        commands=[
            EditCommand(
                "mergeText",
                {
                    "elementIds": [f"base:{first_ref}", f"base:{third.self_ref}"],
                    "separator": " ",
                },
            )
        ],
    )
    assert result.document.export_to_markdown().startswith("First Third")


def test_merge_moves_text_from_another_parent_before_merging():
    doc = DoclingDocument(name="cross-parent")
    first = doc.add_text(label=DocItemLabel.TEXT, text="[first]")
    section = doc.add_heading(text="[section]", level=1)
    nested = doc.add_text(label=DocItemLabel.TEXT, text="[nested]", parent=section)
    result = DoclingDocumentEditor().apply(
        doc.model_dump_json(),
        base_analysis_id="base",
        commands=[
            EditCommand(
                "mergeText",
                {
                    "elementIds": [f"base:{first.self_ref}", f"base:{nested.self_ref}"],
                    "separator": " ",
                },
            )
        ],
    )
    assert result.document.export_to_markdown().startswith("[first] [nested]")
    result.document.validate_tree(result.document.body, raise_on_error=True)


def test_merge_removes_word_break_hyphen_and_preserves_links():
    doc = DoclingDocument(name="merge")
    first = doc.add_text(label=DocItemLabel.TEXT, text="inter-")
    second = doc.add_text(label=DocItemLabel.TEXT, text="national")
    raw = doc.model_dump_json()
    result = DoclingDocumentEditor().apply(
        raw,
        base_analysis_id="base",
        commands=[
            EditCommand(
                "mergeText",
                {
                    "elementIds": [f"base:{first.self_ref}", f"base:{second.self_ref}"],
                    "separator": " ",
                },
            )
        ],
    )
    merged = next(item for item, _ in result.document.iterate_items() if item.self_ref == first.self_ref)
    assert merged.text == "international"


def test_heading_can_be_converted_to_text():
    doc = DoclingDocument(name="heading")
    heading = doc.add_heading(text="Body", level=1)
    result = DoclingDocumentEditor().apply(
        doc.model_dump_json(),
        base_analysis_id="base",
        commands=[
            EditCommand(
                "setHeadingLevel",
                {"elementId": f"base:{heading.self_ref}", "level": -1},
            )
        ],
    )
    assert result.document.texts[0].label == DocItemLabel.TEXT


def test_delete_element_uses_docling_tree_deletion():
    raw, first_ref, _second_ref = _document()
    result = DoclingDocumentEditor().apply(
        raw,
        base_analysis_id="base",
        commands=[EditCommand("deleteElement", {"elementId": f"base:{first_ref}"})],
    )
    assert f"base:{first_ref}" not in result.logical_ids
    assert all(item.text != "First" for item, _ in result.document.iterate_items() if hasattr(item, "text"))


def test_delete_elements_prunes_selected_descendants():
    document = DoclingDocument(name="range-delete")
    first = document.add_text(label=DocItemLabel.TEXT, text="[first]")
    section = document.add_heading(text="[section]", level=1)
    nested = document.add_text(label=DocItemLabel.TEXT, text="[nested]", parent=section)
    result = DoclingDocumentEditor().apply(
        document.model_dump_json(),
        base_analysis_id="base",
        commands=[
            EditCommand(
                "deleteElements",
                {
                    "elementIds": [
                        f"base:{first.self_ref}",
                        f"base:{section.self_ref}",
                        f"base:{nested.self_ref}",
                    ]
                },
            )
        ],
    )
    assert not list(result.document.iterate_items())
    result.document.validate_tree(result.document.body, raise_on_error=True)


def test_realistic_structure_reorders_without_moving_provenance():
    raw = _realistic_document()
    document = DoclingDocument.model_validate_json(raw)
    section = next(item for item, _ in document.iterate_items() if item.label == DocItemLabel.SECTION_HEADER)
    children = list(section.children)
    original = children[0].resolve(document)
    result = DoclingDocumentEditor().apply(
        raw,
        base_analysis_id="base",
        commands=[
            EditCommand(
                "moveElement",
                {
                    "elementId": f"base:{children[0].cref}",
                    "beforeElementId": f"base:{children[-1].cref}",
                },
            )
        ],
    )
    moved = next(item for item, _ in result.document.iterate_items() if item.self_ref == children[0].cref)
    assert moved.prov[0].bbox == original.prov[0].bbox
    assert result.document.validate_tree(result.document.body)


def test_move_moves_subtree_to_the_drop_target_parent():
    document = DoclingDocument(name="cross-parent-move")
    first = document.add_text(label=DocItemLabel.TEXT, text="[first]")
    section = document.add_heading(text="[section]", level=1)
    nested = document.add_text(label=DocItemLabel.TEXT, text="[nested]", parent=section)
    result = DoclingDocumentEditor().apply(
        document.model_dump_json(),
        base_analysis_id="base",
        commands=[
            EditCommand(
                "moveElement",
                {
                    "elementId": f"base:{first.self_ref}",
                    "beforeElementId": f"base:{nested.self_ref}",
                },
            )
        ],
    )
    moved_section = next(item for item, _ in result.document.iterate_items() if item.self_ref == section.self_ref)
    assert [child.resolve(result.document).text for child in moved_section.children] == ["[first]", "[nested]"]
    result.document.validate_tree(result.document.body, raise_on_error=True)


def test_move_supports_explicit_after_and_inside_destinations():
    document = DoclingDocument(name="explicit-move")
    first = document.add_text(label=DocItemLabel.TEXT, text="[first]")
    second = document.add_text(label=DocItemLabel.TEXT, text="[second]")
    section = document.add_heading(text="[section]", level=1)
    result = DoclingDocumentEditor().apply(
        document.model_dump_json(),
        base_analysis_id="base",
        commands=[
            EditCommand(
                "moveElement",
                {
                    "elementId": f"base:{first.self_ref}",
                    "targetElementId": f"base:{second.self_ref}",
                    "placement": "after",
                },
            ),
            EditCommand(
                "moveElement",
                {
                    "elementId": f"base:{second.self_ref}",
                    "targetElementId": f"base:{section.self_ref}",
                    "placement": "inside",
                },
            ),
        ],
    )
    moved_section = next(item for item, _ in result.document.iterate_items() if item.self_ref == section.self_ref)
    assert [child.resolve(result.document).text for child in moved_section.children] == ["[second]"]
    assert result.document.export_to_markdown().startswith("[first]\n\n## [section]\n\n[second]")
    result.document.validate_tree(result.document.body, raise_on_error=True)


def test_move_subtree_rejects_an_incompatible_docling_private_api():
    class IncompatibleDocument:
        def _move_subtree(self, unexpected):
            return unexpected

    with pytest.raises(AnalysisEditError, match="incompatible subtree move API"):
        DoclingDocumentEditor._move_subtree(IncompatibleDocument(), object(), object(), 0)


def test_projector_normalizes_bottom_left_bboxes_for_the_frontend():
    document = DoclingDocument(name="bbox")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=200))
    document.add_text(
        label=DocItemLabel.TEXT,
        text="located",
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(
                l=10,
                t=180,
                r=40,
                b=160,
                coord_origin=CoordOrigin.BOTTOMLEFT,
            ),
            charspan=(0, 7),
        ),
    )
    raw = document.model_dump_json()
    mutation = DoclingDocumentEditor().apply(raw, base_analysis_id="bbox", commands=[])
    projected = DoclingAnalysisProjector().project(
        mutation.document,
        base_analysis_id="bbox",
        logical_ids=mutation.logical_ids,
    )
    page = json.loads(projected.pages_json)[0]
    assert page["elements"][0]["bbox"] == [10.0, 20.0, 40.0, 40.0]


@pytest.mark.parametrize(
    "command_type,payload",
    [
        ("replaceText", {"elementId": "first", "text": "Edited"}),
        ("setHeadingLevel", {"elementId": "heading", "level": 2}),
        ("mergeText", {"elementIds": ["first", "second"], "separator": " "}),
        ("moveElement", {"elementId": "first", "beforeElementId": "nested"}),
        ("deleteElement", {"elementId": "second"}),
        ("deleteElements", {"elementIds": ["first", "second"]}),
    ],
)
def test_projection_round_trips_every_supported_command(command_type, payload):
    document = DoclingDocument(name="projection-round-trip")
    first = document.add_text(label=DocItemLabel.TEXT, text="First")
    second = document.add_text(label=DocItemLabel.TEXT, text="Second")
    heading = document.add_heading(text="Heading", level=1)
    nested = document.add_text(label=DocItemLabel.TEXT, text="Nested", parent=heading)
    logical_ids = {
        "first": f"base:{first.self_ref}",
        "second": f"base:{second.self_ref}",
        "heading": f"base:{heading.self_ref}",
        "nested": f"base:{nested.self_ref}",
    }
    resolved_payload = {
        key: [logical_ids[value] for value in values] if isinstance(values, list) else logical_ids.get(values, values)
        for key, values in payload.items()
    }
    mutation = DoclingDocumentEditor().apply(
        document.model_dump_json(),
        base_analysis_id="base",
        commands=[EditCommand(command_type, resolved_payload)],
    )
    projector = DoclingAnalysisProjector()
    projected = projector.project(
        mutation.document,
        base_analysis_id="base",
        logical_ids=mutation.logical_ids,
    )
    reprojected = projector.project_serialized(
        projected.document_json,
        base_analysis_id="base",
        editor_model_json=projected.editor_model_json,
    )

    assert reprojected.document_json == projected.document_json
    assert reprojected.content_markdown == projected.content_markdown
    assert reprojected.content_html == projected.content_html
    assert reprojected.pages_json == projected.pages_json
    assert reprojected.editor_model_json == projected.editor_model_json
    assert reprojected.tree == projected.tree


def test_realistic_projection_round_trip_preserves_nested_structure_and_provenance():
    raw = _realistic_document()
    document = DoclingDocument.model_validate_json(raw)
    paragraph = next(
        item
        for item, _ in document.iterate_items()
        if item.label == DocItemLabel.TEXT and item.text == "[paragraph]"
    )
    mutation = DoclingDocumentEditor().apply(
        raw,
        base_analysis_id="base",
        commands=[
            EditCommand(
                "replaceText",
                {"elementId": f"base:{paragraph.self_ref}", "text": "[edited paragraph]"},
            )
        ],
    )
    projector = DoclingAnalysisProjector()
    projected = projector.project(
        mutation.document,
        base_analysis_id="base",
        logical_ids=mutation.logical_ids,
    )
    reprojected = projector.project_serialized(
        projected.document_json,
        base_analysis_id="base",
        editor_model_json=projected.editor_model_json,
    )

    assert [page["page_number"] for page in json.loads(projected.pages_json)] == [1, 2]
    assert "[edited paragraph]" in projected.content_markdown
    assert any(node.children for node in projected.tree)
    assert reprojected.pages_json == projected.pages_json
    assert reprojected.editor_model_json == projected.editor_model_json
    assert reprojected.tree == projected.tree


@pytest.fixture
async def edit_service(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "editor.db"))
    await database.init_db()
    documents = SqliteDocumentRepository()
    analyses = SqliteAnalysisRepository()
    edits = SqliteAnalysisEditRepository()
    document = Document(id="doc-1", filename="fixture.pdf", storage_path="/tmp/fixture.pdf")
    await documents.insert(document)
    raw, _, _ = _document()
    job = AnalysisJob(
        id="analysis-1",
        document_id=document.id,
        status=AnalysisStatus.COMPLETED,
        content_markdown="First",
        content_html="<p>First</p>",
        pages_json="[]",
        document_json=raw,
    )
    await analyses.insert(job)
    await analyses.update_status(job)
    await documents.update_active_analysis(document.id, job.id, None)
    service = AnalysisEditService(
        analysis_repo=analyses,
        document_repo=documents,
        edit_repo=edits,
        editor=DoclingDocumentEditor(),
        projector=DoclingAnalysisProjector(),
    )
    return service, edits, analyses


@pytest.mark.asyncio
async def test_save_persists_commands_and_rebuilds_working_copy(edit_service):
    service, edits, _ = edit_service
    initial = await service.load_editor("doc-1")
    text_id = next(element.id for element in initial.projection.elements if element.type == "text")
    saved = await service.save(
        "doc-1",
        [EditCommand("replaceText", {"elementId": text_id, "text": "Edited"})],
        expected_sequence=0,
    )
    assert saved.applied_through_sequence == 1
    assert "Edited" in saved.job.content_markdown
    stream = await edits.find_stream("doc-1", "analysis-1")
    assert stream is not None
    commands = await edits.list_commands(stream.id)
    assert len(commands) == 1
    assert commands[0].command.payload["text"] == "Edited"
    rebuilt = await service.rebuild("doc-1")
    assert rebuilt.job.document_json == saved.job.document_json


@pytest.mark.parametrize(
    "command_type,payload",
    [
        ("replaceText", {"element": "First", "text": "Edited"}),
        ("setHeadingLevel", {"element": "Heading", "level": 2}),
        ("mergeText", {"elements": ["First", "Second"], "separator": " "}),
        ("moveElement", {"element": "First", "target": "Second", "placement": "after"}),
        ("deleteElement", {"element": "Second"}),
        ("deleteElements", {"elements": ["First", "Second"]}),
    ],
)
@pytest.mark.asyncio
async def test_every_durable_command_saves_and_replays(edit_service, command_type, payload):
    service, _edits, _ = edit_service
    initial = await service.load_editor("doc-1")
    ids = {element.text: element.id for element in initial.projection.elements if element.text}
    if command_type == "mergeText":
        command_payload = {
            "elementIds": [ids[text] for text in payload["elements"]],
            "separator": payload["separator"],
        }
    elif command_type == "deleteElements":
        command_payload = {"elementIds": [ids[text] for text in payload["elements"]]}
    elif command_type == "moveElement":
        command_payload = {
            "elementId": ids[payload["element"]],
            "targetElementId": ids[payload["target"]],
            "placement": payload["placement"],
        }
    else:
        command_payload = {"elementId": ids[payload["element"]]} | {
            key: value for key, value in payload.items() if key != "element"
        }

    saved = await service.save(
        "doc-1", [EditCommand(command_type, command_payload)], expected_sequence=0
    )
    rebuilt = await service.rebuild("doc-1")

    assert saved.applied_through_sequence == rebuilt.applied_through_sequence == 1
    assert _projection_values(saved) == _projection_values(rebuilt)


def _projection_values(snapshot):
    return (
        snapshot.job.document_json,
        snapshot.job.content_markdown,
        snapshot.job.content_html,
        snapshot.job.pages_json,
        snapshot.projection.editor_model_json,
        snapshot.projection.tree,
        snapshot.projection.reference_changes,
    )


@pytest.mark.asyncio
async def test_preview_and_save_project_the_same_document(edit_service):
    service, _edits, _ = edit_service
    initial = await service.load_editor("doc-1")
    text_id = next(element.id for element in initial.projection.elements if element.type == "text")
    commands = [EditCommand("replaceText", {"elementId": text_id, "text": "Edited"})]

    preview = await service.preview("doc-1", commands)
    saved = await service.save("doc-1", commands, expected_sequence=0)

    assert preview.applied_through_sequence == saved.applied_through_sequence == 1
    assert _projection_values(preview) == _projection_values(saved)


@pytest.mark.asyncio
async def test_load_replays_saved_stream_when_working_copy_is_missing(edit_service):
    service, _edits, _ = edit_service
    initial = await service.load_editor("doc-1")
    text_id = next(element.id for element in initial.projection.elements if element.type == "text")
    saved = await service.save(
        "doc-1",
        [EditCommand("replaceText", {"elementId": text_id, "text": "Replayed"})],
        expected_sequence=0,
    )

    async with database.get_connection() as connection:
        await connection.execute(
            "DELETE FROM analysis_working_copies WHERE document_id = ? AND base_analysis_id = ?",
            ("doc-1", "analysis-1"),
        )
        await connection.commit()

    reloaded = await service.load_editor("doc-1")
    assert reloaded.applied_through_sequence == saved.applied_through_sequence
    assert _projection_values(reloaded) == _projection_values(saved)


@pytest.mark.asyncio
async def test_preview_failure_logs_safe_editor_context(edit_service, caplog):
    service, _edits, _ = edit_service
    caplog.set_level(logging.ERROR, logger="services.analysis_edit_service")

    with pytest.raises(AnalysisEditError):
        await service.preview(
            "doc-1",
            [EditCommand("replaceText", {"elementId": "missing", "text": "private editor text"})],
        )

    record = caplog.records[-1]
    assert record.editor_operation == "preview"
    assert record.document_id == "doc-1"
    assert record.base_analysis_id == "analysis-1"
    assert record.command_count == 1
    assert record.command_types == ["replaceText"]
    assert "private editor text" not in caplog.text


@pytest.mark.asyncio
async def test_save_sequence_conflict_does_not_append(edit_service):
    service, _edits, _ = edit_service
    initial = await service.load_editor("doc-1")
    text_id = next(element.id for element in initial.projection.elements if element.type == "text")
    await service.save(
        "doc-1",
        [EditCommand("replaceText", {"elementId": text_id, "text": "One"})],
        expected_sequence=0,
    )
    with pytest.raises(ValueError):
        await service.save(
            "doc-1",
            [EditCommand("replaceText", {"elementId": text_id, "text": "Two"})],
            expected_sequence=0,
        )


@pytest.mark.asyncio
async def test_each_base_analysis_has_an_independent_working_copy(edit_service):
    service, _edits, analyses = edit_service
    raw, _, _ = _document()
    second = AnalysisJob(
        id="analysis-2",
        document_id="doc-1",
        status=AnalysisStatus.COMPLETED,
        content_markdown="Second base",
        content_html="<p>Second base</p>",
        pages_json="[]",
        document_json=raw,
    )
    await analyses.insert(second)
    await analyses.update_status(second)
    second_loaded = await service.load_editor("doc-1", "analysis-2")
    text_id = next(element.id for element in second_loaded.projection.elements if element.type == "text")
    await service.save(
        "doc-1",
        [EditCommand("replaceText", {"elementId": text_id, "text": "Second edit"})],
        expected_sequence=0,
        analysis_id="analysis-2",
    )
    first = await service.load_editor("doc-1", "analysis-1")
    second_after = await service.load_editor("doc-1", "analysis-2")
    assert "Second edit" not in first.job.content_markdown
    assert "Second edit" in second_after.job.content_markdown
