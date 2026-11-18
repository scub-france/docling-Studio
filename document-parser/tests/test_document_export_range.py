"""Byte-range contract of the source PDF export, the URL PDF.js loads by ranges (#401).

The viewer asks for 256 KB slices with `Range: bytes=a-b`; it only renders
progressively if the export answers 206 with the slice. These tests run the
real export route, the real ExportService, SQLite and a real PDF on disk, so a
change in the response class or in Starlette's range handling shows up here.
"""

from __future__ import annotations

import asyncio
import io

import pypdfium2 as pdfium
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.documents import router
from api.state import AppState, get_app_state
from domain.models import Document
from persistence import database
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.document_repo import SqliteDocumentRepository
from services.export_service import ExportService

URL = "/api/documents/doc-1/export?format=pdf"


def _real_pdf(pages: int) -> bytes:
    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(612, 792).close()
    buffer = io.BytesIO()
    pdf.save(buffer)
    pdf.close()
    return buffer.getvalue()


@pytest.fixture
def pdf_bytes(tmp_path) -> bytes:
    data = _real_pdf(pages=40)
    assert data.startswith(b"%PDF")
    assert len(data) > 4096, "the fixture must be larger than the ranges requested"
    (tmp_path / "source.pdf").write_bytes(data)
    return data


async def _seed(storage_path: str) -> ExportService:
    await database.init_db()
    documents = SqliteDocumentRepository()
    await documents.insert(Document(id="doc-1", filename="source.pdf", storage_path=storage_path))
    return ExportService(document_repo=documents, analysis_repo=SqliteAnalysisRepository())


@pytest.fixture
def client(tmp_path, monkeypatch, pdf_bytes):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "export-range.db"))
    service = asyncio.run(_seed(str(tmp_path / "source.pdf")))
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_app_state] = lambda: AppState(export_service=service)
    with TestClient(app) as test_client:
        yield test_client


def test_without_range_the_whole_file_is_served(client, pdf_bytes):
    response = client.get(URL)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["accept-ranges"] == "bytes"
    assert int(response.headers["content-length"]) == len(pdf_bytes)
    assert response.content == pdf_bytes


def test_a_leading_range_answers_206_with_that_slice(client, pdf_bytes):
    response = client.get(URL, headers={"Range": "bytes=0-1023"})

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes 0-1023/{len(pdf_bytes)}"
    assert response.headers["accept-ranges"] == "bytes"
    assert int(response.headers["content-length"]) == 1024
    assert response.content == pdf_bytes[:1024]


def test_a_middle_range_answers_206_with_that_slice(client, pdf_bytes):
    response = client.get(URL, headers={"Range": "bytes=1024-2047"})

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes 1024-2047/{len(pdf_bytes)}"
    assert response.content == pdf_bytes[1024:2048]


def test_a_range_ending_past_the_file_is_clamped_to_its_end(client, pdf_bytes):
    size = len(pdf_bytes)

    response = client.get(URL, headers={"Range": f"bytes=1024-{size + 10_000}"})

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes 1024-{size - 1}/{size}"
    assert response.content == pdf_bytes[1024:]


def test_a_suffix_range_answers_206_with_the_last_bytes(client, pdf_bytes):
    size = len(pdf_bytes)

    response = client.get(URL, headers={"Range": "bytes=-500"})

    assert response.status_code == 206
    assert response.headers["content-range"] == f"bytes {size - 500}-{size - 1}/{size}"
    assert response.content == pdf_bytes[-500:]


def test_a_range_starting_past_the_end_is_not_satisfiable(client, pdf_bytes):
    size = len(pdf_bytes)

    response = client.get(URL, headers={"Range": f"bytes={size}-{size + 1023}"})

    assert response.status_code == 416
    assert response.headers["content-range"] == f"bytes */{size}"
