"""Local machine Docling conversion provider implementation."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from docling_studio_cli.providers.base import ProviderSession
    from docling_studio_cli.settings import CliSettings


class _LocalSession:
    """Active local `DocumentConverter` session for a single PDF."""

    def __init__(self, pdf: Path, converter) -> None:
        self._pdf = pdf
        self._converter = converter

    def convert_range(
        self,
        page_range: tuple[int, int] | None,
        output_path: Path,
    ) -> None:
        if page_range is None:
            result = self._converter.convert(str(self._pdf))
        else:
            result = self._converter.convert(str(self._pdf), page_range=page_range)
        output_path.write_text(
            json.dumps(result.document.export_to_dict()),
            encoding="utf-8",
        )


class LocalProvider:
    """Conversion provider that runs Docling locally on the user's machine."""

    name = "local"
    description = "Local Docling installation on this machine"
    settings_model = "LocalProviderSettings"

    @contextmanager
    def open_session(
        self,
        pdf: Path,
        settings: CliSettings,
    ) -> Iterator[ProviderSession]:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise RuntimeError(
                "Local conversion requires docling installed (e.g. `uv tool install './cli[local]'`)"
            ) from exc

        if settings.local.device:
            os.environ["DOCLING_DEVICE"] = settings.local.device
        converter = DocumentConverter()
        yield _LocalSession(pdf, converter)

    def is_transient_capacity_error(self, error: Exception) -> bool:
        return False
