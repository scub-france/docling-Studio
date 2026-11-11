"""Docling Studio HTTP client for uploading PDFs and importing Docling JSON analyses."""

from __future__ import annotations

import json
import re
import uuid
from http.client import IncompleteRead
from typing import TYPE_CHECKING
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from docling_studio_cli.models import (
    StudioAnalysisImportPayload,
    StudioAnalysisResponse,
    StudioDocumentUploadResponse,
    StudioHealthResponse,
    StudioImportResult,
    validate_http_url,
)

if TYPE_CHECKING:
    from pathlib import Path


def request_json(
    url: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    timeout: int = 600,
) -> dict | list:
    headers = {"Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _import_analysis_payload(base: str, doc_id: str, document: dict, *, timeout: int = 600) -> str:
    payload = StudioAnalysisImportPayload(document_id=doc_id, document=document)
    try:
        imported_raw = request_json(
            f"{base}/api/analyses/import",
            data=payload.model_dump_json(by_alias=True).encode("utf-8"),
            content_type="application/json",
            timeout=timeout,
        )
    except IncompleteRead:
        analyses_raw = request_json(f"{base}/api/analyses?documentId={doc_id}", timeout=60)
        for item in analyses_raw if isinstance(analyses_raw, list) else []:
            parsed_item = StudioAnalysisResponse.model_validate(item)
            if parsed_item.status == "COMPLETED" and (parsed_item.id or parsed_item.analysis_id):
                return parsed_item.resolved_id
        raise
    parsed = StudioAnalysisResponse.model_validate(imported_raw)
    return parsed.resolved_id


def import_into_studio(
    studio_url: str,
    pdf: Path,
    document: dict,
    *,
    timeout: int = 600,
) -> StudioImportResult:
    try:
        base = validate_http_url(studio_url)
    except ValueError as exc:
        raise ValueError("--studio-url must be an http:// or https:// URL") from exc

    # A connection failure is distinct from an HTTP rejection. Callers may
    # fall back to local files for the former; the latter needs investigation.
    health_raw = request_json(f"{base}/api/health", timeout=5)
    StudioHealthResponse.model_validate(health_raw)

    boundary = f"docling-{uuid.uuid4().hex}"
    filename = pdf.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode()
        + pdf.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    uploaded_raw = request_json(
        f"{base}/api/documents/upload",
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
        timeout=timeout,
    )
    uploaded = StudioDocumentUploadResponse.model_validate(uploaded_raw)
    doc_id = uploaded.id
    try:
        analysis_id = _import_analysis_payload(base, doc_id, document, timeout=timeout)
    except HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace") if err.fp else ""
        match = re.search(r"version\s+['\"]?(\d+\.\d+\.\d+)['\"]?", err_body) or (
            re.search(r"\b(1\.\d+\.\d+)\b", err_body) if "version" in err_body.lower() else None
        )
        if err.code == 400 and match and match.group(1) != document.get("version"):
            compat_doc = dict(document)
            compat_doc["version"] = match.group(1)
            analysis_id = _import_analysis_payload(base, doc_id, compat_doc, timeout=timeout)
        else:
            raise
    return StudioImportResult(studio_url=base, document_id=doc_id, analysis_id=analysis_id)
