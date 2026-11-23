"""Tests for API schemas — camelCase serialization and validation."""

from typing import get_args

import pytest

from api.schemas import (
    AnalysisEditCommandRequest,
    AnalysisResponse,
    CreateAnalysisRequest,
    DeleteElementEditRequest,
    DeleteElementPayloadResponse,
    DeleteElementsEditRequest,
    DeleteElementsPayloadResponse,
    DocumentResponse,
    EditCommandPayloadResponse,
    MergeTextEditRequest,
    MergeTextPayloadResponse,
    MoveElementEditRequest,
    MoveElementPayloadResponse,
    PipelineOptionsRequest,
    ReplaceTextEditRequest,
    ReplaceTextPayloadResponse,
    SetCommandActivePayloadResponse,
    SetHeadingLevelEditRequest,
    SetHeadingLevelPayloadResponse,
    _to_camel,
)


class TestToCamel:
    def test_single_word(self):
        assert _to_camel("status") == "status"

    def test_two_words(self):
        assert _to_camel("document_id") == "documentId"

    def test_three_words(self):
        assert _to_camel("content_html_raw") == "contentHtmlRaw"

    def test_already_camel(self):
        assert _to_camel("documentId") == "documentId"


class TestDocumentResponse:
    def test_serializes_to_camel_case(self):
        doc = DocumentResponse(
            id="1",
            filename="test.pdf",
            content_type="application/pdf",
            file_size=1024,
            page_count=5,
            created_at="2024-01-01",
        )
        data = doc.model_dump(by_alias=True)
        assert "contentType" in data
        assert "fileSize" in data
        assert "pageCount" in data
        assert "createdAt" in data
        # Original snake_case should not appear
        assert "content_type" not in data
        assert "file_size" not in data

    def test_optional_fields_default_to_none(self):
        doc = DocumentResponse(id="1", filename="test.pdf", created_at="2024-01-01")
        assert doc.content_type is None
        assert doc.file_size is None
        assert doc.page_count is None


class TestAnalysisResponse:
    def test_serializes_to_camel_case(self):
        resp = AnalysisResponse(
            id="1",
            document_id="d1",
            status="COMPLETED",
            content_markdown="# Hello",
            pages_json="[]",
            created_at="2024-01-01",
        )
        data = resp.model_dump(by_alias=True)
        assert "documentId" in data
        assert "contentMarkdown" in data
        assert "pagesJson" in data
        assert "errorMessage" in data
        assert "startedAt" in data
        assert "completedAt" in data

    def test_populate_by_name(self):
        """Can create using snake_case field names."""
        resp = AnalysisResponse(
            id="1",
            document_id="d1",
            status="PENDING",
            created_at="2024-01-01",
        )
        assert resp.document_id == "d1"


class TestPipelineOptionsRequest:
    def test_defaults(self):
        opts = PipelineOptionsRequest()
        assert opts.do_ocr is True
        assert opts.do_table_structure is True
        assert opts.table_mode == "accurate"
        assert opts.do_code_enrichment is False
        assert opts.do_formula_enrichment is False
        assert opts.do_picture_classification is False
        assert opts.do_picture_description is False
        assert opts.generate_picture_images is False
        assert opts.generate_page_images is False
        assert opts.images_scale == 1.0

    def test_custom_values(self):
        opts = PipelineOptionsRequest(
            do_ocr=False,
            table_mode="fast",
            do_code_enrichment=True,
            images_scale=2.0,
        )
        assert opts.do_ocr is False
        assert opts.table_mode == "fast"
        assert opts.do_code_enrichment is True
        assert opts.images_scale == 2.0

    def test_model_dump(self):
        opts = PipelineOptionsRequest(do_ocr=False)
        data = opts.model_dump()
        assert data["do_ocr"] is False
        assert data["do_table_structure"] is True  # default preserved

    def test_invalid_table_mode_rejected(self):
        with pytest.raises(ValueError, match='table_mode must be "accurate" or "fast"'):
            PipelineOptionsRequest(table_mode="invalid")

    def test_negative_images_scale_rejected(self):
        with pytest.raises(ValueError, match="images_scale must be between"):
            PipelineOptionsRequest(images_scale=-1.0)

    def test_zero_images_scale_rejected(self):
        with pytest.raises(ValueError, match="images_scale must be between"):
            PipelineOptionsRequest(images_scale=0)

    def test_excessive_images_scale_rejected(self):
        with pytest.raises(ValueError, match="images_scale must be between"):
            PipelineOptionsRequest(images_scale=11.0)

    def test_boundary_images_scale_accepted(self):
        opts = PipelineOptionsRequest(images_scale=0.1)
        assert opts.images_scale == 0.1
        opts2 = PipelineOptionsRequest(images_scale=10.0)
        assert opts2.images_scale == 10.0


class TestCreateAnalysisRequest:
    def test_parses_document_id(self):
        req = CreateAnalysisRequest(documentId="doc-42")
        assert req.documentId == "doc-42"
        assert req.pipelineOptions is None

    def test_parses_with_pipeline_options(self):
        req = CreateAnalysisRequest(
            documentId="doc-42",
            pipelineOptions=PipelineOptionsRequest(do_ocr=False, table_mode="fast"),
        )
        assert req.documentId == "doc-42"
        assert req.pipelineOptions.do_ocr is False
        assert req.pipelineOptions.table_mode == "fast"


# Each editor command's request model and the model its stored payload reads into.
_PAYLOAD_TWINS = [
    (ReplaceTextEditRequest, ReplaceTextPayloadResponse),
    (MergeTextEditRequest, MergeTextPayloadResponse),
    (SetHeadingLevelEditRequest, SetHeadingLevelPayloadResponse),
    (MoveElementEditRequest, MoveElementPayloadResponse),
    (DeleteElementEditRequest, DeleteElementPayloadResponse),
    (DeleteElementsEditRequest, DeleteElementsPayloadResponse),
]


class TestStoredPayloadModels:
    """Each stored payload model has its request's fields, minus `type`."""

    @pytest.mark.parametrize(("request_model", "payload_model"), _PAYLOAD_TWINS)
    def test_payload_mirrors_request(self, request_model, payload_model):
        expected = {
            name: info.alias for name, info in request_model.model_fields.items() if name != "type"
        }
        actual = {name: info.alias for name, info in payload_model.model_fields.items()}
        assert actual == expected

    def test_every_command_has_a_payload_twin(self):
        requests = set(get_args(get_args(AnalysisEditCommandRequest)[0]))
        assert {request for request, _ in _PAYLOAD_TWINS} == requests
        assert set(get_args(EditCommandPayloadResponse)) == {
            *(payload for _, payload in _PAYLOAD_TWINS),
            SetCommandActivePayloadResponse,
        }
