"""Docling Studio HTTP client for uploading PDFs and importing Docling JSON analyses."""

from __future__ import annotations

import json
import re
import uuid
from http.client import IncompleteRead
from typing import TYPE_CHECKING
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

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


def _import_analysis_payload(base: str, doc_id: str, document: dict) -> str:
    try:
        imported = request_json(
            f"{base}/api/analyses/import",
            data=json.dumps({"documentId": doc_id, "document": document}).encode(),
            content_type="application/json",
        )
    except IncompleteRead:
        analyses = request_json(f"{base}/api/analyses?documentId={doc_id}", timeout=60)
        for item in analyses if isinstance(analyses, list) else []:
            if item.get("status") == "COMPLETED" and item.get("id"):
                return str(item["id"])
        raise
    assert isinstance(imported, dict)
    analysis_id = imported.get("id") or imported.get("analysisId")
    if not analysis_id:
        raise KeyError("id")
    return str(analysis_id)


def import_into_studio(studio_url: str, pdf: Path, document: dict) -> tuple[str, str]:
    base = studio_url.rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("--studio-url must be an http:// or https:// URL")

    # A connection failure is distinct from an HTTP rejection. Callers may
    # fall back to local files for the former; the latter needs investigation.
    request_json(f"{base}/api/health", timeout=5)
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
    uploaded = request_json(
        f"{base}/api/documents/upload",
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    assert isinstance(uploaded, dict)
    doc_id = str(uploaded["id"])
    try:
        analysis_id = _import_analysis_payload(base, doc_id, document)
    except HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace") if err.fp else ""
        match = re.search(r"version\s+['\"]?(\d+\.\d+\.\d+)['\"]?", err_body) or (
            re.search(r"\b(1\.\d+\.\d+)\b", err_body) if "version" in err_body.lower() else None
        )
        if err.code == 400 and match and match.group(1) != document.get("version"):
            compat_doc = dict(document)
            compat_doc["version"] = match.group(1)
            analysis_id = _import_analysis_payload(base, doc_id, compat_doc)
        else:
            raise
    return doc_id, analysis_id
