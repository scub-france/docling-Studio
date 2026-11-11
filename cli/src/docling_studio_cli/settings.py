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
    ColabAuthMethod,
    ConversionOptions,
    GpuType,
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

    Environment variables use the `DOCLING_STUDIO_` prefix (for example:
    `DOCLING_STUDIO_STUDIO_URL` or `DOCLING_STUDIO_URL`, `DOCLING_STUDIO_PROVIDER`,
    `DOCLING_STUDIO_GPU`, `DOCLING_STUDIO_BATCH_PAGES`, `DOCLING_STUDIO_WORKERS`).
    """

    model_config = SettingsConfigDict(
        env_prefix="DOCLING_STUDIO_",
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
        description="Default conversion provider (e.g. colab, local)",
    )
    gpu: GpuType | None = Field(
        default=None,
        description="Default GPU accelerator on Colab (T4, L4, G4, H100, A100)",
    )
    workers: int = Field(
        default=1,
        ge=1,
        description="Default number of parallel Colab runtimes",
    )
    batch_pages: int | None = Field(
        default=None,
        ge=1,
        description="Default page batch size per conversion step",
    )
    colab_auth: ColabAuthMethod = Field(
        default=ColabAuthMethod.OAUTH2,
        description="Default Colab CLI auth method (oauth2 or adc)",
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

    @field_validator("studio_url", mode="before")
    @classmethod
    def _normalize_studio_url(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return validate_http_url(text)

    @field_validator("gpu", mode="before")
    @classmethod
    def _normalize_gpu(cls, value: Any) -> GpuType | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"none", "cpu", "null"}:
            return None
        return GpuType(text.upper())

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

    def to_conversion_options(
        self,
        *,
        gpu: GpuType | str | None = None,
        colab_auth: ColabAuthMethod | str | None = None,
        batch_pages: int | None = None,
        workers: int | None = None,
    ) -> ConversionOptions:
        resolved_gpu = (
            GpuType(gpu.upper()) if isinstance(gpu, str) else (gpu if gpu is not None else self.gpu)
        )
        resolved_auth = (
            ColabAuthMethod(colab_auth)
            if isinstance(colab_auth, str)
            else (colab_auth if colab_auth is not None else self.colab_auth)
        )
        return ConversionOptions(
            gpu=resolved_gpu,
            colab_auth=resolved_auth,
            batch_pages=batch_pages if batch_pages is not None else self.batch_pages,
            workers=workers if workers is not None else self.workers,
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
    clean_overrides = {k: v for k, v in overrides.items() if v is not None}
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
        return CliSettings(**clean_overrides)
    finally:
        CliSettings._active_config_path = prev_path  # type: ignore[attr-defined]
