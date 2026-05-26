"""Tests for the ServeConverter adapter (Docling Serve HTTP client)."""

from __future__ import annotations

import importlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from domain.value_objects import ConversionOptions, ConversionResult
from infra.serve_converter import (
    ServeConverter,
    _build_form_data,
    _extract_bbox,
    _parse_response,
)


def _has_docling() -> bool:
    """Return True if the heavy docling library is available."""
    return importlib.util.find_spec("docling") is not None


# ---------------------------------------------------------------------------
# Unit tests — form data building
# ---------------------------------------------------------------------------


class TestBuildFormData:
    def test_default_options(self):
        data = _build_form_data(ConversionOptions())
        assert data["do_ocr"] == "true"
        assert data["do_table_structure"] == "true"
        assert data["table_mode"] == "accurate"
        assert data["do_code_enrichment"] == "false"
        assert data["do_formula_enrichment"] == "false"
        assert data["do_picture_classification"] == "false"
        assert data["do_picture_description"] == "false"
        assert data["include_images"] == "false"
        assert data["images_scale"] == "1.0"
        assert set(data["to_formats"]) == {"md", "html", "json"}

    def test_custom_options(self):
        opts = ConversionOptions(
            do_ocr=False,
            table_mode="fast",
            images_scale=2.0,
            generate_picture_images=True,
        )
        data = _build_form_data(opts)
        assert data["do_ocr"] == "false"
        assert data["table_mode"] == "fast"
        assert data["images_scale"] == "2.0"
        assert data["include_images"] == "true"

    def test_no_generate_page_images_field(self):
        """generate_page_images is a PdfPipelineOptions field, not a Serve field."""
        data = _build_form_data(ConversionOptions())
        assert "generate_page_images" not in data

    def test_page_range_as_repeated_fields(self):
        data = _build_form_data(ConversionOptions(), page_range=(11, 20))
        assert data["page_range"] == ["11", "20"]

    def test_page_range_absent_when_none(self):
        data = _build_form_data(ConversionOptions())
        assert "page_range" not in data


# ---------------------------------------------------------------------------
# Unit tests — response parsing
# ---------------------------------------------------------------------------


class TestParseResponse:
    def test_minimal_response(self):
        data = {
            "document": {
                "md_content": "# Hello",
                "html_content": "<h1>Hello</h1>",
                "json_content": {
                    "pages": {"1": {"size": {"width": 612.0, "height": 792.0}}},
                    "texts": [],
                    "tables": [],
                    "pictures": [],
                },
            }
        }
        result = _parse_response(data)
        assert isinstance(result, ConversionResult)
        assert result.content_markdown == "# Hello"
        assert result.content_html == "<h1>Hello</h1>"
        assert result.page_count == 1
        assert result.pages[0].width == 612.0
        # document_json mirrors the json_content stub
        assert result.document_json is not None
        assert '"texts"' in result.document_json
        assert '"pages"' in result.document_json

    def test_response_with_elements(self):
        data = {
            "document": {
                "md_content": "# Title\nText",
                "html_content": "<h1>Title</h1><p>Text</p>",
                "json_content": {
                    "pages": {"1": {"size": {"width": 612.0, "height": 792.0}}},
                    "texts": [
                        {
                            "self_ref": "#/texts/0",
                            "label": "title",
                            "text": "Title",
                            "prov": [
                                {
                                    "page_no": 1,
                                    "bbox": {
                                        "l": 10,
                                        "t": 20,
                                        "r": 200,
                                        "b": 40,
                                        "coord_origin": "TOPLEFT",
                                    },
                                }
                            ],
                        },
                        {
                            "self_ref": "#/texts/1",
                            "label": "paragraph",
                            "text": "Text",
                            "prov": [
                                {
                                    "page_no": 1,
                                    "bbox": {
                                        "l": 10,
                                        "t": 50,
                                        "r": 200,
                                        "b": 70,
                                        "coord_origin": "TOPLEFT",
                                    },
                                }
                            ],
                        },
                    ],
                    "tables": [],
                    "pictures": [],
                },
            }
        }
        result = _parse_response(data)
        assert len(result.pages[0].elements) == 2
        assert result.pages[0].elements[0].type == "title"
        assert result.pages[0].elements[0].content == "Title"
        assert result.pages[0].elements[0].bbox == [10, 20, 200, 40]
        # `self_ref` is the linchpin for chunk <-> bbox correlation on the
        # Linked-view canvas (see frontend `linkedView.ts`). The remote
        # converter was dropping it pre-#audit-remote-bbox, leaving the
        # overlay empty on every Docling-Serve-converted document.
        assert result.pages[0].elements[0].self_ref == "#/texts/0"
        assert result.pages[0].elements[1].type == "text"
        assert result.pages[0].elements[1].self_ref == "#/texts/1"

    def test_self_ref_missing_falls_back_to_empty_string(self):
        """Docling Serve responses without `self_ref` (legacy / partial)
        must not crash — fall back to '' so downstream code keeps the
        empty-string contract that `PageElement.self_ref` defaults to."""
        data = {
            "document": {
                "json_content": {
                    "pages": {"1": {"size": {"width": 612.0, "height": 792.0}}},
                    "texts": [
                        {
                            "label": "paragraph",
                            "text": "no ref here",
                            "prov": [
                                {
                                    "page_no": 1,
                                    "bbox": {
                                        "l": 0,
                                        "t": 0,
                                        "r": 100,
                                        "b": 20,
                                        "coord_origin": "TOPLEFT",
                                    },
                                }
                            ],
                        }
                    ],
                },
            }
        }
        result = _parse_response(data)
        assert result.pages[0].elements[0].self_ref == ""

    def test_multi_page(self):
        data = {
            "document": {
                "md_content": "",
                "html_content": "",
                "json_content": {
                    "pages": {
                        "1": {"size": {"width": 612.0, "height": 792.0}},
                        "2": {"size": {"width": 595.0, "height": 842.0}},
                    },
                    "texts": [],
                    "tables": [],
                    "pictures": [],
                },
            }
        }
        result = _parse_response(data)
        assert result.page_count == 2
        assert result.pages[1].width == 595.0

    def test_no_json_content(self):
        data = {
            "document": {
                "md_content": "text",
                "html_content": "<p>text</p>",
            }
        }
        result = _parse_response(data)
        assert result.content_markdown == "text"
        assert result.pages == []
        assert result.page_count == 1
        assert result.document_json is None

    def test_json_content_as_string(self):
        json_doc = {
            "pages": {"1": {"size": {"width": 612.0, "height": 792.0}}},
            "texts": [],
            "tables": [],
            "pictures": [],
        }
        data = {
            "document": {
                "md_content": "",
                "html_content": "",
                "json_content": json.dumps(json_doc),
            }
        }
        result = _parse_response(data)
        assert result.page_count == 1

    def test_json_content_malformed_string_falls_back(self):
        """Bug #5: malformed JSON string in json_content must not crash."""
        data = {
            "document": {
                "md_content": "# Hello",
                "html_content": "<h1>Hello</h1>",
                "json_content": "NOT VALID JSON {{{",
            }
        }
        result = _parse_response(data)
        assert isinstance(result, ConversionResult)
        assert result.content_markdown == "# Hello"
        assert result.pages == []
        assert result.page_count == 1

    def test_tables_and_pictures(self):
        data = {
            "document": {
                "md_content": "",
                "html_content": "",
                "json_content": {
                    "pages": {"1": {"size": {"width": 612.0, "height": 792.0}}},
                    "texts": [],
                    "tables": [
                        {
                            "label": "table",
                            "text": "",
                            "prov": [
                                {
                                    "page_no": 1,
                                    "bbox": {
                                        "l": 10,
                                        "t": 10,
                                        "r": 300,
                                        "b": 200,
                                        "coord_origin": "TOPLEFT",
                                    },
                                }
                            ],
                        },
                    ],
                    "pictures": [
                        {
                            "label": "picture",
                            "text": "",
                            "prov": [
                                {
                                    "page_no": 1,
                                    "bbox": {
                                        "l": 50,
                                        "t": 300,
                                        "r": 250,
                                        "b": 500,
                                        "coord_origin": "TOPLEFT",
                                    },
                                }
                            ],
                        },
                    ],
                },
            }
        }
        result = _parse_response(data)
        types = [e.type for e in result.pages[0].elements]
        assert "table" in types
        assert "picture" in types


# ---------------------------------------------------------------------------
# Unit tests — bbox extraction
# ---------------------------------------------------------------------------


class TestExtractBbox:
    def test_topleft_passthrough(self):
        bbox = _extract_bbox(
            {"l": 10, "t": 20, "r": 100, "b": 50, "coord_origin": "TOPLEFT"}, 792.0
        )
        assert bbox == [10, 20, 100, 50]

    def test_bottomleft_conversion(self):
        # In BOTTOMLEFT: t (top of box) has higher y than b (bottom of box)
        bbox = _extract_bbox(
            {"l": 10, "t": 772, "r": 100, "b": 742, "coord_origin": "BOTTOMLEFT"}, 792.0
        )
        # new_top = 792 - 772 = 20, new_bottom = 792 - 742 = 50
        assert bbox == [10, 20, 100, 50]

    def test_missing_coord_origin_defaults_topleft(self):
        bbox = _extract_bbox({"l": 10, "t": 20, "r": 100, "b": 50}, 792.0)
        assert bbox == [10, 20, 100, 50]

    def test_empty_dict(self):
        bbox = _extract_bbox({}, 792.0)
        assert bbox == [0.0, 0.0, 0.0, 0.0]

    def test_non_dict_returns_zeros(self):
        bbox = _extract_bbox("invalid", 792.0)
        assert bbox == [0.0, 0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# Unit tests — label mapping
# ---------------------------------------------------------------------------


class TestLabelMapping:
    def test_known_labels(self):
        from infra.serve_converter import _LABEL_MAP

        assert _LABEL_MAP["table"] == "table"
        assert _LABEL_MAP["picture"] == "picture"
        assert _LABEL_MAP["figure"] == "picture"
        assert _LABEL_MAP["title"] == "title"
        assert _LABEL_MAP["section_header"] == "section_header"
        assert _LABEL_MAP["list_item"] == "list"
        assert _LABEL_MAP["formula"] == "formula"
        assert _LABEL_MAP["code"] == "code"
        assert _LABEL_MAP["paragraph"] == "text"

    def test_unknown_label_defaults_to_text(self):
        from infra.serve_converter import _LABEL_MAP

        assert _LABEL_MAP.get("unknown_thing", "text") == "text"


# ---------------------------------------------------------------------------
# Unit tests — ServeConverter
# ---------------------------------------------------------------------------


class TestServeConverter:
    def test_headers_with_api_key(self):
        conv = ServeConverter(base_url="http://localhost:5001", api_key="secret")
        assert conv._headers() == {"X-Api-Key": "secret"}

    def test_headers_without_api_key(self):
        conv = ServeConverter(base_url="http://localhost:5001")
        assert conv._headers() == {}

    def test_base_url_trailing_slash_stripped(self):
        conv = ServeConverter(base_url="http://localhost:5001/")
        assert conv._base_url == "http://localhost:5001"


# ---------------------------------------------------------------------------
# Integration tests — HTTP calls (mocked)
# ---------------------------------------------------------------------------


class TestServeConverterConvert:
    @pytest.mark.asyncio
    async def test_successful_conversion(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        serve_response = {
            "document": {
                "md_content": "# Converted",
                "html_content": "<h1>Converted</h1>",
                "json_content": {
                    "pages": {"1": {"size": {"width": 612.0, "height": 792.0}}},
                    "texts": [
                        {
                            "label": "title",
                            "text": "Converted",
                            "prov": [
                                {
                                    "page_no": 1,
                                    "bbox": {
                                        "l": 10,
                                        "t": 20,
                                        "r": 200,
                                        "b": 40,
                                        "coord_origin": "TOPLEFT",
                                    },
                                }
                            ],
                        },
                    ],
                    "tables": [],
                    "pictures": [],
                },
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = serve_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        conv = ServeConverter(base_url="http://localhost:5001", api_key="test-key")

        with patch("infra.serve_converter.httpx.AsyncClient", return_value=mock_client):
            result = await conv.convert(str(test_file), ConversionOptions())

        assert isinstance(result, ConversionResult)
        assert result.content_markdown == "# Converted"
        assert result.page_count == 1
        assert len(result.pages[0].elements) == 1
        assert result.pages[0].elements[0].type == "title"

        # Verify form fields sent correctly
        call_kwargs = mock_client.post.call_args
        sent_data = call_kwargs.kwargs.get("data", {})
        assert sent_data["do_ocr"] == "true"
        assert set(sent_data["to_formats"]) == {"md", "html", "json"}
        assert "generate_page_images" not in sent_data

    @pytest.mark.asyncio
    async def test_http_error_raises(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        conv = ServeConverter(base_url="http://localhost:5001")

        with (
            patch("infra.serve_converter.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await conv.convert(str(test_file), ConversionOptions())

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        conv = ServeConverter(base_url="http://localhost:5001")

        with patch("infra.serve_converter.httpx.AsyncClient", return_value=mock_client):
            assert await conv.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        conv = ServeConverter(base_url="http://localhost:5001")

        with patch("infra.serve_converter.httpx.AsyncClient", return_value=mock_client):
            assert await conv.health_check() is False


# ---------------------------------------------------------------------------
# Integration — converter wiring in main.py
# ---------------------------------------------------------------------------


class TestConverterWiring:
    @pytest.mark.skipif(
        not _has_docling(),
        reason="docling library not installed",
    )
    def test_local_engine_builds_local_converter(self):
        from infra.local_converter import LocalConverter
        from infra.settings import Settings

        with patch("main.settings", Settings(conversion_engine="local")):
            from main import _build_converter

            converter = _build_converter()
        assert isinstance(converter, LocalConverter)

    def test_remote_engine_builds_serve_converter(self):
        from infra.settings import Settings

        with patch(
            "main.settings",
            Settings(conversion_engine="remote", docling_serve_url="http://serve:5001"),
        ):
            from main import _build_converter

            converter = _build_converter()
        assert isinstance(converter, ServeConverter)
        assert converter._base_url == "http://serve:5001"

    def test_remote_engine_passes_api_key(self):
        from infra.settings import Settings

        with patch(
            "main.settings",
            Settings(
                conversion_engine="remote",
                docling_serve_url="http://serve:5001",
                docling_serve_api_key="my-key",
            ),
        ):
            from main import _build_converter

            converter = _build_converter()
        assert isinstance(converter, ServeConverter)
        assert converter._api_key == "my-key"

    def test_remote_engine_builds_chunker(self):
        """Chunker must be available in remote mode (hybrid local chunking)."""
        from infra.local_chunker import LocalChunker
        from infra.settings import Settings

        with patch(
            "main.settings",
            Settings(conversion_engine="remote", docling_serve_url="http://serve:5001"),
        ):
            from main import _build_chunker

            chunker = _build_chunker()
        assert isinstance(chunker, LocalChunker)
