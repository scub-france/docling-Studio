"""Pydantic schemas — API request/response DTOs.

All responses use camelCase serialization to match the existing frontend contract
(originally served by the Spring Boot backend).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

# Document lifecycle status — currently single-state (uploaded). Kept as a
# constant so future statuses (e.g. "archived", "deleted") can extend the
# vocabulary without hunting magic strings across the codebase.
DOCUMENT_STATUS_UPLOADED = "uploaded"


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class _CamelModel(BaseModel):
    """Base model that serializes field names to camelCase."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class HealthResponse(_CamelModel):
    status: str
    version: str
    engine: str
    deployment_mode: str
    database: str
    max_page_count: int | None = None
    max_file_size_mb: int | None = None
    max_paste_image_size_mb: int | None = None
    paste_allowed_image_types: list[str] = Field(default_factory=list)
    ingestion_available: bool = False
    # True when the live-reasoning runner (docling-agent + Ollama) is
    # available: REASONING_ENABLED=true AND deps importable. Doesn't imply
    # Ollama itself is reachable — that's checked per-call.
    reasoning_available: bool = False


class DocumentResponse(_CamelModel):
    id: str
    filename: str
    status: str = DOCUMENT_STATUS_UPLOADED
    content_type: str | None = None
    file_size: int | None = None
    page_count: int | None = None
    created_at: str | datetime
    # 0.6.0 — Document lifecycle state machine (#202). The lifecycle
    # describes the document as a whole; `status` above is kept for
    # backwards compat and currently still maps to `DOCUMENT_STATUS_UPLOADED`.
    lifecycle_state: str = "Uploaded"
    lifecycle_state_at: str | datetime | None = None


class AnalysisResponse(_CamelModel):
    id: str
    document_id: str = ""
    document_filename: str | None = None
    status: str
    content_markdown: str | None = None
    content_html: str | None = None
    pages_json: str | None = None
    chunks_json: str | None = None
    has_document_json: bool = False
    error_message: str | None = None
    progress_current: int | None = None
    progress_total: int | None = None
    started_at: str | datetime | None = None
    completed_at: str | datetime | None = None
    created_at: str | datetime


class PipelineOptionsRequest(BaseModel):
    """Docling pipeline configuration options."""

    model_config = ConfigDict(populate_by_name=True)

    do_ocr: bool = Field(default=True, validation_alias=AliasChoices("do_ocr", "doOcr"))
    do_table_structure: bool = Field(
        default=True, validation_alias=AliasChoices("do_table_structure", "doTableStructure")
    )
    table_mode: str = Field(
        default="accurate", validation_alias=AliasChoices("table_mode", "tableMode")
    )
    do_code_enrichment: bool = Field(
        default=False, validation_alias=AliasChoices("do_code_enrichment", "doCodeEnrichment")
    )
    do_formula_enrichment: bool = Field(
        default=False, validation_alias=AliasChoices("do_formula_enrichment", "doFormulaEnrichment")
    )
    do_picture_classification: bool = Field(
        default=False,
        validation_alias=AliasChoices("do_picture_classification", "doPictureClassification"),
    )
    do_picture_description: bool = Field(
        default=False,
        validation_alias=AliasChoices("do_picture_description", "doPictureDescription"),
    )
    generate_picture_images: bool = Field(
        default=False,
        validation_alias=AliasChoices("generate_picture_images", "generatePictureImages"),
    )
    generate_page_images: bool = Field(
        default=False, validation_alias=AliasChoices("generate_page_images", "generatePageImages")
    )
    images_scale: float = Field(
        default=1.0, validation_alias=AliasChoices("images_scale", "imagesScale")
    )

    @field_validator("table_mode")
    @classmethod
    def validate_table_mode(cls, v: str) -> str:
        if v not in ("accurate", "fast"):
            raise ValueError('table_mode must be "accurate" or "fast"')
        return v

    @field_validator("images_scale")
    @classmethod
    def validate_images_scale(cls, v: float) -> float:
        if v <= 0 or v > 10:
            raise ValueError("images_scale must be between 0 (exclusive) and 10")
        return v


class ChunkingOptionsRequest(BaseModel):
    """Docling chunking configuration options."""

    model_config = ConfigDict(populate_by_name=True)

    chunker_type: str = Field(
        default="hybrid", validation_alias=AliasChoices("chunker_type", "chunkerType")
    )
    max_tokens: int = Field(default=512, validation_alias=AliasChoices("max_tokens", "maxTokens"))
    merge_peers: bool = Field(
        default=True, validation_alias=AliasChoices("merge_peers", "mergePeers")
    )
    repeat_table_header: bool = Field(
        default=True, validation_alias=AliasChoices("repeat_table_header", "repeatTableHeader")
    )

    @field_validator("chunker_type")
    @classmethod
    def validate_chunker_type(cls, v: str) -> str:
        if v not in ("hybrid", "hierarchical"):
            raise ValueError('chunker_type must be "hybrid" or "hierarchical"')
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        if v < 64 or v > 8192:
            raise ValueError("max_tokens must be between 64 and 8192")
        return v


class ChunkBboxResponse(_CamelModel):
    page: int
    bbox: list[float]


class ChunkResponse(_CamelModel):
    text: str
    headings: list[str] = []
    source_page: int | None = None
    token_count: int = 0
    bboxes: list[ChunkBboxResponse] = []
    modified: bool = False
    deleted: bool = False


class UpdateChunkTextRequest(BaseModel):
    text: str


class CreateAnalysisRequest(BaseModel):
    documentId: str = Field(validation_alias=AliasChoices("documentId", "document_id"))
    pipelineOptions: PipelineOptionsRequest | None = Field(
        default=None, validation_alias=AliasChoices("pipelineOptions", "pipeline_options")
    )
    chunkingOptions: ChunkingOptionsRequest | None = Field(
        default=None, validation_alias=AliasChoices("chunkingOptions", "chunking_options")
    )


class RechunkRequest(BaseModel):
    chunkingOptions: ChunkingOptionsRequest = Field(
        validation_alias=AliasChoices("chunkingOptions", "chunking_options")
    )


class IngestionResponse(_CamelModel):
    doc_id: str
    chunks_indexed: int
    embedding_dimension: int


class IngestionStatusResponse(_CamelModel):
    available: bool
    opensearch_connected: bool = False


class SearchResultItem(_CamelModel):
    """A single search result with content and metadata."""

    doc_id: str
    filename: str
    content: str
    chunk_index: int
    page_number: int
    score: float
    headings: list[str] = []
    highlights: list[str] = []


class SearchResponse(_CamelModel):
    results: list[SearchResultItem]
    total: int
    query: str
