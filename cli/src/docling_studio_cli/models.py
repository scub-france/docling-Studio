"""Pydantic domain models for CLI conversion options, Studio API responses, and provider metadata."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderName(StrEnum):
    COLAB = "colab"
    LOCAL = "local"


class GpuType(StrEnum):
    T4 = "T4"
    L4 = "L4"
    G4 = "G4"
    H100 = "H100"
    A100 = "A100"


class ColabAuthMethod(StrEnum):
    OAUTH2 = "oauth2"
    ADC = "adc"


def validate_http_url(url: str) -> str:
    cleaned = url.strip().rstrip("/")
    parsed = urlsplit(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be a valid http:// or https:// URL")
    return cleaned


class ConversionOptions(BaseModel):
    """Validated options passed to a conversion provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gpu: GpuType | None = None
    colab_auth: ColabAuthMethod = ColabAuthMethod.OAUTH2
    batch_pages: int | None = Field(default=None, ge=1)
    workers: int = Field(default=1, ge=1)


class ProviderDescriptor(BaseModel):
    """Metadata describing a registered conversion provider."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class StudioHealthResponse(BaseModel):
    """Response from Docling Studio `GET /api/health`."""

    model_config = ConfigDict(extra="ignore")

    status: str
    version: str | None = None


class StudioDocumentUploadResponse(BaseModel):
    """Response from Docling Studio `POST /api/documents/upload`."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    filename: str | None = None
    page_count: int | None = Field(default=None, alias="pageCount")


class StudioAnalysisImportPayload(BaseModel):
    """Request payload for Docling Studio `POST /api/analyses/import`."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    document_id: str = Field(serialization_alias="documentId", min_length=1)
    document: dict


class StudioAnalysisResponse(BaseModel):
    """Response from Docling Studio `POST /api/analyses/import` or `GET /api/analyses`."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str | None = None
    analysis_id: str | None = Field(default=None, alias="analysisId")
    document_id: str | None = Field(default=None, alias="documentId")
    status: str | None = None

    @property
    def resolved_id(self) -> str:
        value = self.id or self.analysis_id
        if not value:
            raise ValueError("Studio analysis response did not include id or analysisId")
        return value


class StudioImportResult(BaseModel):
    """Validated result of uploading a PDF and importing its Docling JSON into Studio."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    studio_url: str
    document_id: str = Field(min_length=1)
    analysis_id: str = Field(min_length=1)

    @field_validator("studio_url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        return validate_http_url(value)

    @property
    def document_url(self) -> str:
        return f"{self.studio_url}/docs/{self.document_id}"


class ConversionJobConfig(BaseModel):
    """Validated configuration for a `docling-studio convert` invocation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pdf: Path
    provider: str = Field(default=ProviderName.COLAB.value, min_length=1)
    options: ConversionOptions = Field(default_factory=ConversionOptions)
    output_dir: Path
    studio_url: str | None = None
    request_timeout_seconds: int = Field(default=600, ge=1)

    @field_validator("pdf")
    @classmethod
    def _validate_pdf(cls, value: Path) -> Path:
        resolved = value.expanduser().resolve()
        if not resolved.is_file() or resolved.suffix.lower() != ".pdf":
            raise ValueError("pdf must be an existing PDF file")
        return resolved

    @field_validator("output_dir")
    @classmethod
    def _validate_output_dir(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("studio_url")
    @classmethod
    def _validate_studio_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_http_url(value)


class ImportJobConfig(BaseModel):
    """Validated configuration for a `docling-studio import` invocation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pdf: Path
    json_path: Path
    studio_url: str
    request_timeout_seconds: int = Field(default=600, ge=1)

    @field_validator("pdf")
    @classmethod
    def _validate_pdf(cls, value: Path) -> Path:
        resolved = value.expanduser().resolve()
        if not resolved.is_file() or resolved.suffix.lower() != ".pdf":
            raise ValueError("pdf must be an existing PDF file")
        return resolved

    @field_validator("json_path")
    @classmethod
    def _validate_json_path(cls, value: Path) -> Path:
        resolved = value.expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"Docling JSON file not found: {resolved}")
        return resolved

    @field_validator("studio_url")
    @classmethod
    def _validate_studio_url(cls, value: str) -> str:
        return validate_http_url(value)
