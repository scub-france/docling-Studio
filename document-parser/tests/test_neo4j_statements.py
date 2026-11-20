"""Characterization test for the Cypher the Neo4j adapters send.

No Neo4j server runs in CI, so the integration tests under `tests/neo4j/`
are skipped there. This test pins, without a server, the exact sequence of
driver calls made by `write_document`, `write_chunks` and `fetch_graph`
(statement text with whitespace collapsed, parameters, commits), their
return values and their log lines, against the snapshot in
`tests/fixtures/neo4j_statements.json`.

To regenerate the snapshot after an intended change in the statements:
`NEO4J_SNAPSHOT_UPDATE=1 pytest tests/test_neo4j_statements.py`, then
review the diff of the JSON file.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from infra.neo4j import tree_writer
from infra.neo4j.chunk_writer import write_chunks
from infra.neo4j.queries import fetch_graph
from infra.neo4j.tree_writer import GraphDocument, write_document

if TYPE_CHECKING:
    import pytest

SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "neo4j_statements.json"


# ---------------------------------------------------------------------------
# Fake driver: records every call in order, answers `.single()` from a queue.
# ---------------------------------------------------------------------------


class _Recorder:
    def __init__(self, answers: list[Any]) -> None:
        self.events: list[dict[str, Any]] = []
        self._answers = list(answers)

    def record_run(self, op: str, query: str, params: dict[str, Any]) -> _FakeResult:
        self.events.append({"op": op, "query": " ".join(query.split()), "params": params})
        return _FakeResult(self)

    def next_answer(self) -> Any:
        self.events.append({"op": "single"})
        return self._answers.pop(0) if self._answers else None


class _FakeResult:
    def __init__(self, recorder: _Recorder) -> None:
        self._recorder = recorder

    async def single(self) -> Any:
        return self._recorder.next_answer()


class _FakeTx:
    def __init__(self, recorder: _Recorder) -> None:
        self._recorder = recorder

    async def __aenter__(self) -> _FakeTx:
        self._recorder.events.append({"op": "tx.enter"})
        return self

    async def __aexit__(self, *_: object) -> None:
        self._recorder.events.append({"op": "tx.exit"})

    async def run(self, query: str, **params: Any) -> _FakeResult:
        return self._recorder.record_run("tx.run", query, params)

    async def commit(self) -> None:
        self._recorder.events.append({"op": "tx.commit"})


class _FakeSession:
    def __init__(self, recorder: _Recorder) -> None:
        self._recorder = recorder

    async def __aenter__(self) -> _FakeSession:
        self._recorder.events.append({"op": "session.enter"})
        return self

    async def __aexit__(self, *_: object) -> None:
        self._recorder.events.append({"op": "session.exit"})

    async def begin_transaction(self) -> _FakeTx:
        self._recorder.events.append({"op": "session.begin_transaction"})
        return _FakeTx(self._recorder)

    async def run(self, query: str, **params: Any) -> _FakeResult:
        return self._recorder.record_run("session.run", query, params)


class _FakeAsyncDriver:
    def __init__(self, recorder: _Recorder) -> None:
        self._recorder = recorder

    def session(self, database: str | None = None) -> _FakeSession:
        self._recorder.events.append({"op": "driver.session", "database": database})
        return _FakeSession(self._recorder)


class _FakeNeo:
    def __init__(self, answers: list[Any] | None = None) -> None:
        self.recorder = _Recorder(answers or [])
        self.driver = _FakeAsyncDriver(self.recorder)
        self.database = "graphdb"


class _FakeNode(dict):
    """A neo4j `Node`: mapping access plus a `.labels` set-like attribute."""

    def __init__(self, labels: list[str], **props: Any) -> None:
        super().__init__(**props)
        self.labels = labels


class _FrozenDatetime:
    @staticmethod
    def now(tz: Any = None) -> datetime:
        return datetime(2026, 1, 2, 3, 4, 5, tzinfo=tz or UTC)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def _ref(r: str) -> dict[str, str]:
    return {"$ref": r}


def _prov(page_no: int | None, bbox: Any, charspan: list[int] | None = None) -> dict[str, Any]:
    prov: dict[str, Any] = {"bbox": bbox}
    if page_no is not None:
        prov["page_no"] = page_no
    if charspan is not None:
        prov["charspan"] = charspan
    return prov


def _box(left: float, top: float, right: float, bottom: float) -> dict[str, Any]:
    return {"l": left, "t": top, "r": right, "b": bottom, "coord_origin": "BOTTOMLEFT"}


def _docling_document() -> dict[str, Any]:
    """Two pages: title, heading with a paragraph and an inline group under it,
    a table, a picture with an internal label, a list, an unknown label and an
    item with no self_ref."""
    return {
        "schema_name": "DoclingDocument",
        "name": "sample",
        "body": {
            "self_ref": "#/body",
            "children": [
                _ref("#/texts/0"),
                _ref("#/texts/1"),
                _ref("#/tables/0"),
                _ref("#/pictures/0"),
                _ref("#/groups/1"),
                _ref("#/texts/8"),
            ],
        },
        "texts": [
            {
                "self_ref": "#/texts/0",
                "parent": _ref("#/body"),
                "label": "title",
                "text": "Annual report",
                "prov": [_prov(1, _box(10, 800, 500, 780), [0, 13])],
            },
            {
                "self_ref": "#/texts/1",
                "parent": _ref("#/body"),
                "label": "section_header",
                "level": 1,
                "text": "Results",
                "children": [_ref("#/texts/2"), _ref("#/groups/0")],
                "prov": [_prov(1, [10, 760, 300, 740], [0, 7])],
            },
            {
                "self_ref": "#/texts/2",
                "parent": _ref("#/texts/1"),
                "label": "paragraph",
                "text": "Revenue grew.",
                "prov": [
                    _prov(1, _box(10, 700, 500, 600), [0, 8]),
                    _prov(2, _box(10, 800, 500, 750), [8, 13]),
                ],
            },
            {
                "self_ref": "#/texts/3",
                "parent": _ref("#/groups/0"),
                "label": "text",
                "text": "Bold run",
                "prov": [_prov(2, _box(10, 700, 100, 690), [0, 8])],
            },
            {
                "self_ref": "#/texts/4",
                "parent": _ref("#/groups/0"),
                "label": "text",
                "text": "plain run",
                "prov": [_prov(2, _box(100, 700, 200, 690), [0, 9])],
            },
            {
                "self_ref": "#/texts/5",
                "parent": _ref("#/pictures/0"),
                "label": "text",
                "text": "axis label",
                "prov": [_prov(2, _box(300, 400, 320, 390))],
            },
            {
                "self_ref": "#/texts/6",
                "parent": _ref("#/groups/1"),
                "label": "list_item",
                "text": "First point",
                "prov": [_prov(None, _box(10, 300, 200, 290))],
            },
            {"parent": _ref("#/body"), "label": "text", "text": "orphan without ref"},
            {
                "self_ref": "#/texts/8",
                "parent": _ref("#/body"),
                "label": "checkbox_selected",
                "text": "",
            },
        ],
        "tables": [
            {
                "self_ref": "#/tables/0",
                "parent": _ref("#/body"),
                "label": "table",
                "caption": "Table 1",
                "data": {
                    "num_rows": 1,
                    "num_cols": 2,
                    "table_cells": [{"text": "a"}, {"text": "b"}],
                },
                "prov": [_prov(2, _box(10, 600, 500, 450))],
            }
        ],
        "pictures": [
            {
                "self_ref": "#/pictures/0",
                "parent": _ref("#/body"),
                "label": "picture",
                "children": [_ref("#/texts/5")],
                "prov": [_prov(2, _box(250, 420, 450, 350))],
            }
        ],
        "groups": [
            {
                "self_ref": "#/groups/0",
                "parent": _ref("#/texts/1"),
                "label": "inline",
                "children": [_ref("#/texts/3"), _ref("#/texts/4")],
            },
            {
                "self_ref": "#/groups/1",
                "parent": _ref("#/body"),
                "label": "list",
                "children": [_ref("#/texts/6")],
            },
        ],
        "pages": {
            "1": {"size": {"width": 595.0, "height": 842.0}, "page_no": 1},
            "2": {"size": {"width": 595.0, "height": 842.0}, "page_no": 2},
            "cover": {"size": {"width": 1, "height": 1}},
        },
    }


def _chunks() -> list[dict[str, Any]]:
    return [
        {
            "text": "Annual report. Results.",
            "tokenCount": 5,
            "docItems": [{"selfRef": "#/texts/0"}, {"selfRef": "#/texts/1"}],
        },
        {"text": "removed", "tokenCount": 1, "deleted": True, "docItems": [{"selfRef": "#/x"}]},
        {"text": "Revenue grew.", "docItems": ["#/texts/2", {"selfRef": ""}, {"other": 1}]},
        {"text": None, "tokenCount": 3},
    ]


def _graph_record() -> dict[str, Any]:
    doc = _FakeNode(["Document"], id="doc-1", title="sample.pdf", stages_applied=["tree", "chunks"])
    heading = _FakeNode(
        ["Element", "SectionHeader"],
        self_ref="#/texts/1",
        docling_label="section_header",
        text="Results",
        level=1,
    )
    para = _FakeNode(
        ["Element", "Paragraph"], self_ref="#/texts/2", docling_label="paragraph", text="x" * 250
    )
    bare = _FakeNode(
        ["Element"], self_ref="#/texts/8", docling_label="checkbox_selected", text=None
    )
    prov = {"order": 0, "page_no": 2, "bbox_l": 1.0, "bbox_t": 2.0, "bbox_r": 3.0, "bbox_b": 4.0}
    return {
        "document": doc,
        "elements": [
            {"element": heading, "provs": [prov, None, {**prov, "order": 1, "page_no": 3}]},
            {"element": para, "provs": None},
            {"element": bare},
            None,
            {"element": None, "provs": []},
            "not-a-dict",
        ],
        "pages": [_FakeNode(["Page"], page_no=1, width=595.0, height=842.0), None],
        "chunks": [
            _FakeNode(
                ["Chunk"], id="doc-1::chunk::0", chunk_index=0, text="y" * 300, token_count=7
            ),
            None,
        ],
        "parent_edges": [
            {"from": "#/texts/1", "to": "#/texts/2", "order": 0, "type": "PARENT_OF"},
            {"from": None, "to": "#/texts/2", "order": 1, "type": "PARENT_OF"},
        ],
        "next_edges": [{"from": "#/texts/1", "to": "#/texts/2", "type": "NEXT"}],
        "on_page_edges": [
            {"from": "#/texts/1", "to": 2, "type": "ON_PAGE"},
            {"from": "#/texts/1", "to": None, "type": "ON_PAGE"},
        ],
        "has_root_edges": [{"from": "doc-1", "to": "#/texts/1", "type": "HAS_ROOT"}],
        "has_chunk_edges": [{"from": "doc-1", "to": "doc-1::chunk::0", "type": "HAS_CHUNK"}],
        "derived_from_edges": [
            {"from": "doc-1::chunk::0", "to": "#/texts/2", "type": "DERIVED_FROM"}
        ],
    }


def _graph_record_empty() -> dict[str, Any]:
    keys = ["elements", "pages", "chunks", "parent_edges", "next_edges", "on_page_edges"]
    keys += ["has_root_edges", "has_chunk_edges", "derived_from_edges"]
    return {"document": None, **dict.fromkeys(keys)}


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def _result_to_json(result: Any) -> Any:
    return dataclasses.asdict(result) if dataclasses.is_dataclass(result) else result


async def _run_scenario(
    call: Any, answers: list[Any], caplog: pytest.LogCaptureFixture
) -> dict[str, Any]:
    neo = _FakeNeo(answers)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="infra.neo4j"):
        try:
            result: Any = _result_to_json(await call(neo))
        except Exception as exc:  # the snapshot pins the error, not just the happy path
            result = {"raised": type(exc).__name__, "message": str(exc)}
    logs = [
        [r.name, r.levelname, r.getMessage()]
        for r in caplog.records
        if r.name.startswith("infra.neo4j")
    ]
    return {"events": neo.recorder.events, "result": result, "logs": logs}


def _scenarios() -> dict[str, tuple[Any, list[Any]]]:
    doc_json = json.dumps(_docling_document())
    chunks_json = json.dumps(_chunks())
    return {
        "write_document": (
            lambda neo: write_document(
                neo,
                GraphDocument(
                    doc_id="doc-1",
                    filename="sample.pdf",
                    document_json=doc_json,
                    tenant_id="acme",
                    source_uri="s3://bucket/sample.pdf",
                    docling_version="2.1.0",
                ),
            ),
            [],
        ),
        "write_document_defaults_empty_doc": (
            lambda neo: write_document(
                neo, GraphDocument(doc_id="doc-2", filename="empty.pdf", document_json="{}")
            ),
            [],
        ),
        "write_chunks": (
            lambda neo: write_chunks(neo, doc_id="doc-1", chunks_json=chunks_json),
            [{"created": 3}],
        ),
        "write_chunks_count_mismatch": (
            lambda neo: write_chunks(neo, doc_id="doc-1", chunks_json=chunks_json),
            [{"created": 2}],
        ),
        "write_chunks_empty": (
            lambda neo: write_chunks(neo, doc_id="doc-3", chunks_json="[]"),
            [],
        ),
        "fetch_graph": (
            lambda neo: fetch_graph(neo, "doc-1"),
            [{"n": 2}, {"n": 1}, _graph_record()],
        ),
        "fetch_graph_empty_record": (
            lambda neo: fetch_graph(neo, "doc-1", max_pages=5),
            [{"n": 0}, {"n": 1}, _graph_record_empty()],
        ),
        "fetch_graph_unknown_document": (
            lambda neo: fetch_graph(neo, "nope"),
            [{"n": 0}, {"n": 0}],
        ),
        "fetch_graph_no_page_count_row": (
            lambda neo: fetch_graph(neo, "nope"),
            [None],
        ),
        "fetch_graph_no_exists_row": (
            lambda neo: fetch_graph(neo, "nope"),
            [{"n": 0}, None],
        ),
        "fetch_graph_too_many_pages": (
            lambda neo: fetch_graph(neo, "doc-1", max_pages=3),
            [{"n": 4}, {"n": 1}],
        ),
        "fetch_graph_no_graph_row": (
            lambda neo: fetch_graph(neo, "doc-1"),
            [{"n": 1}, {"n": 1}, None],
        ),
    }


def _dump(value: Any) -> str:
    return json.dumps(value, indent=1, ensure_ascii=False)


async def test_neo4j_statements_match_snapshot(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tree_writer, "datetime", _FrozenDatetime)
    actual = {
        name: await _run_scenario(call, answers, caplog)
        for name, (call, answers) in _scenarios().items()
    }

    if os.environ.get("NEO4J_SNAPSHOT_UPDATE"):
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(_dump(actual) + "\n", encoding="utf-8")

    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert list(actual) == list(expected)
    for name in actual:
        assert _dump(actual[name]) == _dump(expected[name]), name
