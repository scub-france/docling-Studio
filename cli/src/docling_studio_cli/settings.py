"""CLI configuration and persistent user defaults powered by `pydantic-settings`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from docling_studio_cli.models import (
    ColabProviderSettings,
    DoclingServeProviderSettings,
    LocalProviderSettings,
    PipelineOptions,
    ProviderName,
    validate_http_url,
)


def default_config_path() -> Path:
    """Return the default path for the user's JSON settings file."""
    override = os.environ.get("DOCLING_STUDIO_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "docling-studio" / "settings.json"


class _JsonConfigFileSettingsSource(PydanticBaseSettingsSource):
    """Settings source that reads user defaults from a JSON config file if present."""

    def __init__(self, settings_cls: type[BaseSettings], config_path: Path) -> None:
        super().__init__(settings_cls)
        self.config_path = config_path

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        data = self._read_file()
        if field_name in data:
            return data[field_name], field_name, False
        return None, field_name, False

    def _read_file(self) -> dict[str, Any]:
        if not self.config_path.is_file():
            return {}
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}

    def __call__(self) -> dict[str, Any]:
        return self._read_file()


class CliSettings(BaseSettings):
    """Default settings for `docling-studio`, loaded from CLI overrides, env vars, `.env`, and `settings.json`.

    Top-level settings are provider-agnostic (`studio_url`, `provider`, `workers`,
    `batch_pages`, `output_dir`, `request_timeout_seconds`), while provider-specific
    settings are cleanly isolated under nested models (`colab`, `local`, `docling_serve`)
    configurable via `DOCLING_STUDIO_<PROVIDER>__<FIELD>` (e.g. `DOCLING_STUDIO_COLAB__GPU=T4`,
    `DOCLING_STUDIO_DOCLING_SERVE__URL=http://gpu-host:5001`).
    """

    model_config = SettingsConfigDict(
        env_prefix="DOCLING_STUDIO_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    studio_url: str | None = Field(
        default=None,
        description="Default Docling Studio base URL (e.g. http://localhost:3000)",
    )
    provider: str = Field(
        default=ProviderName.COLAB.value,
        min_length=1,
        description="Default conversion provider (colab, local, docling-serve)",
    )
    workers: int = Field(
        default=1,
        ge=1,
        description="Default number of parallel worker sessions to split a PDF across",
    )
    batch_pages: int | None = Field(
        default=None,
        ge=1,
        description="Default page batch size per conversion step",
    )
    output_dir: Path = Field(
        default_factory=lambda: Path.home() / "Downloads",
        description="Default parent directory for saved PDFs and Docling JSONs",
    )
    request_timeout_seconds: int = Field(
        default=600,
        ge=1,
        description="Default HTTP timeout in seconds for Studio API requests",
    )

    colab: ColabProviderSettings = Field(
        default_factory=ColabProviderSettings,
        description="Google Colab provider settings",
    )
    local: LocalProviderSettings = Field(
        default_factory=LocalProviderSettings,
        description="Local Docling provider settings",
    )
    docling_serve: DoclingServeProviderSettings = Field(
        default_factory=DoclingServeProviderSettings,
        description="Remote Docling Serve HTTP provider settings",
    )

    @field_validator("studio_url", mode="before")
    @classmethod
    def _normalize_studio_url(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return validate_http_url(text)

    @field_validator("output_dir", mode="after")
    @classmethod
    def _expand_output_dir(cls, value: Path) -> Path:
        return value.expanduser()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        config_path = getattr(cls, "_active_config_path", None) or default_config_path()
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _JsonConfigFileSettingsSource(settings_cls, config_path),
            file_secret_settings,
        )

    def to_pipeline_options(
        self,
        *,
        workers: int | None = None,
        batch_pages: int | None = None,
    ) -> PipelineOptions:
        return PipelineOptions(
            workers=workers if workers is not None else self.workers,
            batch_pages=batch_pages if batch_pages is not None else self.batch_pages,
        )

    def save(self, config_path: Path | None = None) -> Path:
        """Persist current settings to the user JSON configuration file."""
        target = (config_path or default_config_path()).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self.model_dump(mode="json")
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return target


def load_settings(
    config_path: Path | None = None,
    **overrides: Any,
) -> CliSettings:
    """Load `CliSettings` combining explicit overrides, environment variables, `.env`, and JSON config."""
    clean_overrides: dict[str, Any] = {k: v for k, v in overrides.items() if v is not None}
    if (
        "studio_url" not in clean_overrides
        and "DOCLING_STUDIO_STUDIO_URL" not in os.environ
        and os.environ.get("DOCLING_STUDIO_URL")
    ):
        clean_overrides["studio_url"] = os.environ["DOCLING_STUDIO_URL"]

    resolved_path = (config_path or default_config_path()).expanduser().resolve()
    prev_path = getattr(CliSettings, "_active_config_path", None)
    CliSettings._active_config_path = resolved_path  # type: ignore[attr-defined]
    try:
        base = CliSettings()
        if not clean_overrides:
            return base
        merged = base.model_dump()
        for key, value in clean_overrides.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                nested = dict(merged[key])
                for nk, nv in value.items():
                    if nv is not None:
                        nested[nk] = nv
                merged[key] = nested
            else:
                merged[key] = value
        return CliSettings.model_validate(merged)
    finally:
        CliSettings._active_config_path = prev_path  # type: ignore[attr-defined]
