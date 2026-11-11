"""Base protocols and registry for PDF conversion providers."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Protocol

from docling_studio_cli.models import ProviderDescriptor

if TYPE_CHECKING:
    from pathlib import Path

    from docling_studio_cli.settings import CliSettings


class ProviderSession(Protocol):
    """An active conversion session for a single PDF (e.g. an allocated remote runtime or local converter).

    The pipeline calls `convert_range` once (when `batch_pages` is None) or
    repeatedly for each `(start_page, end_page)` batch within the same session,
    and guarantees `close()` is called via the context manager on exit.
    """

    def convert_range(
        self,
        page_range: tuple[int, int] | None,
        output_path: Path,
    ) -> None: ...


class ConversionProvider(Protocol):
    """Protocol implemented by all PDF-to-Docling conversion backends."""

    name: str
    description: str
    settings_model: str

    def open_session(
        self,
        pdf: Path,
        settings: CliSettings,
    ) -> AbstractContextManager[ProviderSession]:
        """Open a conversion session for `pdf` using provider settings from `settings`."""
        ...

    def is_transient_capacity_error(self, error: Exception) -> bool:
        """Return True if a parallel worker failure was due to temporary capacity limits and can be retried."""
        ...


_PROVIDERS: dict[str, ConversionProvider] = {}


def register_provider(provider: ConversionProvider) -> None:
    """Register a `ConversionProvider` implementation by its `name`."""
    _PROVIDERS[provider.name] = provider


def get_provider(name: str) -> ConversionProvider:
    if name not in _PROVIDERS:
        available = ", ".join(sorted(_PROVIDERS))
        raise KeyError(f"Unknown provider {name!r}; available providers: {available}")
    return _PROVIDERS[name]


def list_providers() -> list[ConversionProvider]:
    return [_PROVIDERS[name] for name in sorted(_PROVIDERS)]


def list_provider_descriptors() -> list[ProviderDescriptor]:
    return [
        ProviderDescriptor(
            name=p.name,
            description=p.description,
            settings_model=getattr(p, "settings_model", "CliSettings"),
        )
        for p in list_providers()
    ]
