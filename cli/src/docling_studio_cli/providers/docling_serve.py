"""Remote Docling Serve HTTP API conversion provider implementation."""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from urllib.request import Request, urlopen

from docling_studio_cli.models import (
    DoclingServeProviderSettings,
    ProviderCheckResult,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from docling_studio_cli.providers.base import PromptFn, ProviderSession
    from docling_studio_cli.settings import CliSettings


def _encode_multipart_form(
    fields: list[tuple[str, str]],
    file_field: tuple[str, str, bytes],
) -> tuple[bytes, str]:
    boundary = f"docling-serve-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
            ).encode()
        )
    field_name, filename, content = file_field
    safe_name = filename.replace('"', "_").replace("\r", "_").replace("\n", "_")
    chunks.append(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field_name}"; filename="{safe_name}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class _DoclingServeSession:
    """HTTP session that converts a PDF (or page range) via a remote `docling-serve` endpoint."""

    def __init__(self, pdf: Path, cfg: DoclingServeProviderSettings) -> None:
        assert cfg.url is not None
        self._pdf = pdf
        self._base_url = cfg.url.rstrip("/")
        self._api_key = cfg.api_key
        self._timeout = cfg.timeout_seconds

    def convert_range(
        self,
        page_range: tuple[int, int] | None,
        output_path: Path,
    ) -> None:
        fields: list[tuple[str, str]] = [("to_formats", "json")]
        if page_range is not None:
            fields.append(("page_range", str(page_range[0])))
            fields.append(("page_range", str(page_range[1])))

        body, content_type = _encode_multipart_form(
            fields,
            ("files", self._pdf.name, self._pdf.read_bytes()),
        )
        headers = {
            "Accept": "application/json",
            "Content-Type": content_type,
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        request = Request(
            f"{self._base_url}/v1/convert/file",
            data=body,
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=self._timeout) as response:
            payload = json.load(response)

        doc = payload.get("document", {}).get("json_content") or payload.get("document") or payload
        if not isinstance(doc, dict):
            raise RuntimeError("docling-serve response did not contain a JSON document")
        output_path.write_text(json.dumps(doc), encoding="utf-8")


class DoclingServeProvider:
    """Conversion provider that sends PDFs to a remote `docling-serve` HTTP service."""

    name = "docling-serve"
    description = "Remote Docling Serve HTTP API (/v1/convert/file)"
    settings_model = "DoclingServeProviderSettings"

    @contextmanager
    def open_session(
        self,
        pdf: Path,
        settings: CliSettings,
    ) -> Iterator[ProviderSession]:
        cfg = settings.docling_serve
        if not cfg.url:
            raise RuntimeError(
                "docling-serve provider requires a URL (--docling-serve-url or DOCLING_STUDIO_DOCLING_SERVE__URL)"
            )
        yield _DoclingServeSession(pdf, cfg)

    def is_transient_capacity_error(self, error: Exception) -> bool:
        return "429" in str(error) or "503" in str(error)

    def configure_interactive(
        self,
        current: CliSettings,
        prompt: PromptFn,
    ) -> dict[str, Any]:
        default_url = current.docling_serve.url or "http://localhost:5001"
        default_key = current.docling_serve.api_key or ""
        url_val = prompt("Docling Serve base URL", default_url)
        key_val = prompt("Docling Serve API key (leave empty if none)", default_key)
        validated = DoclingServeProviderSettings(
            url=url_val.strip(),
            api_key=key_val.strip() or None,
            timeout_seconds=current.docling_serve.timeout_seconds,
        )
        return {"docling_serve": validated.model_dump(mode="json")}

    def verify(self, settings: CliSettings) -> ProviderCheckResult:
        cfg = settings.docling_serve
        if not cfg.url:
            return ProviderCheckResult(
                provider=self.name,
                ok=False,
                summary="Docling Serve URL is not configured (run `docling-studio configure docling-serve`)",
            )
        headers = {"Accept": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        try:
            req = Request(f"{cfg.url.rstrip('/')}/health", headers=headers, method="GET")
            with urlopen(req, timeout=10) as response:
                data = json.load(response)
            return ProviderCheckResult(
                provider=self.name,
                ok=True,
                summary=f"Reachable Docling Serve endpoint at {cfg.url}",
                details={"url": cfg.url, "health": data},
            )
        except Exception as exc:
            return ProviderCheckResult(
                provider=self.name,
                ok=False,
                summary=f"Docling Serve health check failed at {cfg.url}: {exc}",
                details={"url": cfg.url},
            )
