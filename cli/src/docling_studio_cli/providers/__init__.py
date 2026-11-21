"""Pluggable PDF conversion providers package."""

from __future__ import annotations

from docling_studio_cli.providers.base import (
    ConversionProvider,
    ProviderSession,
    get_provider,
    list_provider_descriptors,
    list_providers,
    register_provider,
)
from docling_studio_cli.providers.colab import ColabProvider
from docling_studio_cli.providers.docling_serve import DoclingServeProvider
from docling_studio_cli.providers.local import LocalProvider

register_provider(ColabProvider())
register_provider(LocalProvider())
register_provider(DoclingServeProvider())

__all__ = [
    "ColabProvider",
    "ConversionProvider",
    "DoclingServeProvider",
    "LocalProvider",
    "ProviderSession",
    "get_provider",
    "list_provider_descriptors",
    "list_providers",
    "register_provider",
]
