"""The response contract the app publishes in its OpenAPI (#audit-07, 7.4.2).

FastAPI publishes a response model's *serialization* schema. A model with a
`model_serializer` gets that schema from the serializer's return annotation,
so a `-> dict[str, Any]` there published `StoreConfigResponse`, `GraphNode`
and `GraphProvenance` as free objects while the code declared their fields.
These tests read the schema the app actually serves.
"""

from __future__ import annotations

from typing import Any

import pytest

from main import app


@pytest.fixture(scope="module")
def openapi() -> dict[str, Any]:
    return app.openapi()


def _component(openapi: dict[str, Any], name: str) -> dict[str, Any]:
    return openapi["components"]["schemas"][name]


class TestProvidedKeysModelsPublishTheirFields:
    def test_store_config_lists_the_keys_the_backend_reads(self, openapi) -> None:
        schema = _component(openapi, "StoreConfigResponse")
        assert schema["type"] == "object"
        assert set(schema["properties"]) == {"index_name", "indexName", "database"}
        assert "additionalProperties" not in schema

    def test_store_response_points_its_config_at_that_schema(self, openapi) -> None:
        config = _component(openapi, "StoreResponse")["properties"]["config"]
        assert config == {"$ref": "#/components/schemas/StoreConfigResponse"}

    def test_graph_node_lists_its_fields_and_requires_id_and_group(self, openapi) -> None:
        schema = _component(openapi, "GraphNode")
        assert {"id", "group", "label", "doc_id", "provs", "page_no", "chunk_index"} <= set(
            schema["properties"]
        )
        assert schema["required"] == ["id", "group"]
        assert schema["properties"]["group"]["enum"] == ["document", "element", "page", "chunk"]
        assert "additionalProperties" not in schema

    def test_graph_provenance_lists_its_fields(self, openapi) -> None:
        schema = _component(openapi, "GraphProvenance")
        assert {"order", "page_no", "bbox_l", "bbox_t", "bbox_r", "bbox_b"} <= set(
            schema["properties"]
        )
        assert "additionalProperties" not in schema


def _free_objects(openapi: dict[str, Any], node: Any, path: str, seen: set[str]) -> list[str]:
    """Every free object (`additionalProperties: true`, no properties) reachable
    from `node`, following `$ref`s once each."""
    found: list[str] = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", 1)[-1]
            if name not in seen:
                seen.add(name)
                found += _free_objects(openapi, _component(openapi, name), name, seen)
        if node.get("additionalProperties") is True and "properties" not in node:
            found.append(path)
        for key, value in node.items():
            found += _free_objects(openapi, value, f"{path}/{key}", seen)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found += _free_objects(openapi, value, f"{path}/{i}", seen)
    return found


def test_no_response_publishes_a_free_object(openapi) -> None:
    """Rule 7.4.2: a response documents its contract, so none of them — nor
    any schema one of them references — is a bare `dict`."""
    seen: set[str] = set()
    free: list[str] = []
    for route, operations in openapi["paths"].items():
        for method, operation in operations.items():
            for status, response in operation.get("responses", {}).items():
                free += _free_objects(
                    openapi, response.get("content", {}), f"{method} {route} {status}", seen
                )
    assert free == []
