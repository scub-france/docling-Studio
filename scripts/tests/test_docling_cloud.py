"""Boundary tests for the Colab Python client and Studio HTTP integration."""

from __future__ import annotations

import importlib.util
import io
import json
import re
import tempfile
import unittest
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError

SCRIPT = Path(__file__).resolve().parents[1] / "docling-cloud.py"
spec = importlib.util.spec_from_file_location("docling_cloud", SCRIPT)
assert spec and spec.loader
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)


class ColabConversionTests(unittest.TestCase):
    def fake_api(self, *, conversion_error=False, batched=False):
        events = []

        class Accelerator(str, Enum):
            NONE = "NONE"
            T4 = "T4"

        class Variant(str, Enum):
            DEFAULT = "DEFAULT"
            GPU = "GPU"

        class Client:
            def list_assignments(self):
                return []

            def assign(self, _request_id, *, variant, accelerator):
                events.append(("assign", variant, accelerator))
                return SimpleNamespace(
                    endpoint="ep-1",
                    runtime_proxy_info=SimpleNamespace(
                        token="token", url="https://colab.example"
                    ),
                )

            def unassign(self, endpoint):
                events.append(("unassign", endpoint))

        class Contents:
            def __init__(self, _state):
                pass

            def upload(self, local, remote):
                events.append(("upload", local, remote))

            def download(self, remote, local):
                events.append(("download", remote, local))
                if batched:
                    from docling_core.types.doc import DoclingDocument, PageItem, Size

                    match = re.search(r"-(\d+)-(\d+)\.docling\.json$", remote)
                    assert match
                    start, end = map(int, match.groups())
                    doc = DoclingDocument(
                        name="part",
                        pages={
                            page: PageItem(page_no=page, size=Size(width=1, height=1))
                            for page in range(start, end + 1)
                        },
                    )
                    Path(local).write_text(json.dumps(doc.export_to_dict()))
                else:
                    Path(local).write_text('{"schema_name":"DoclingDocument"}')

        class Runtime:
            def __init__(self, _url, _token):
                pass

            def execute_code(self, code, *, timeout):
                if "DOCLING_READY_TO_CONVERT" in code:
                    assert timeout == 900
                    return [
                        {
                            "output_type": "stream",
                            "text": "DOCLING_READY_TO_CONVERT\n",
                        }
                    ]
                if "DOCLING_READY" in code:
                    assert timeout == 900
                    return [{"output_type": "stream", "text": "DOCLING_READY\n"}]
                assert timeout == (900 if "page_range=" in code else 3600)
                if conversion_error:
                    return [{"output_type": "error", "evalue": "conversion failed"}]
                return [{"output_type": "stream", "text": "DOCLING_CONVERTED\n"}]

            def stop(self, *, shutdown_kernel):
                events.append(("stop", shutdown_kernel))

        return events, (
            Client(),
            Accelerator,
            Variant,
            Contents,
            Runtime,
            SimpleNamespace,
        )

    def test_downloads_result_and_releases_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "paper.pdf"
            result = Path(temp_dir) / "paper.json"
            pdf.write_bytes(b"%PDF-1.4\n")
            events, api = self.fake_api()
            with patch.object(cloud, "_colab_api", return_value=api):
                cloud.convert_with_colab(pdf, result, "T4")
            self.assertEqual(
                [event[0] for event in events],
                ["assign", "upload", "download", "stop", "unassign"],
            )
            self.assertEqual(events[0][2], api[1].T4)
            self.assertEqual(
                json.loads(result.read_text())["schema_name"], "DoclingDocument"
            )

    def test_releases_session_when_conversion_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            events, api = self.fake_api(conversion_error=True)
            with (
                patch.object(cloud, "_colab_api", return_value=api),
                self.assertRaises(RuntimeError),
            ):
                cloud.convert_with_colab(pdf, Path(temp_dir) / "paper.json", None)
            self.assertEqual([event[0] for event in events][-2:], ["stop", "unassign"])

    @unittest.skipUnless(
        importlib.util.find_spec("pypdf") and importlib.util.find_spec("docling_core"),
        "batch dependencies are not installed",
    )
    def test_page_batches_merge_and_release_session(self):
        from pypdf import PdfWriter

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "paper.pdf"
            writer = PdfWriter()
            for _ in range(3):
                writer.add_blank_page(width=100, height=100)
            with pdf.open("wb") as stream:
                writer.write(stream)
            result = Path(temp_dir) / "paper.docling.json"
            events, api = self.fake_api(batched=True)
            with patch.object(cloud, "_colab_api", return_value=api):
                cloud.convert_with_colab(pdf, result, "T4", batch_pages=2)
            merged = json.loads(result.read_text())
            self.assertEqual(list(merged["pages"]), ["1", "2", "3"])
            self.assertEqual(len(list((Path(temp_dir) / "parts").glob("*.json"))), 2)
            self.assertEqual([event[0] for event in events][-2:], ["stop", "unassign"])


class StudioImportTests(unittest.TestCase):
    def test_unreachable_studio_keeps_both_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            pdf = parent / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")

            def fake_convert(_pdf, result_path, _gpu, _auth, _batch_pages):
                result_path.write_text('{"schema_name":"DoclingDocument"}')

            with (
                patch.object(
                    cloud.sys,
                    "argv",
                    [
                        "docling-cloud.py",
                        str(pdf),
                        "--output-dir",
                        temp_dir,
                        "--studio-url",
                        "http://localhost:3000",
                    ],
                ),
                patch.object(cloud, "convert_with_colab", side_effect=fake_convert),
                patch.object(
                    cloud, "import_into_studio", side_effect=URLError("offline")
                ),
            ):
                self.assertEqual(cloud.main(), 0)

            saved = list(parent.glob("paper-*/"))
            self.assertEqual(len(saved), 1)
            self.assertEqual((saved[0] / "paper.pdf").read_bytes(), pdf.read_bytes())
            self.assertTrue((saved[0] / "paper.docling.json").is_file())

    def test_uploads_pdf_then_imports_docling_json(self):
        requests = []

        def fake_urlopen(request, *, timeout):
            requests.append((request.full_url, request.data or b"", request.headers))
            if request.full_url.endswith("/api/health"):
                payload = {"status": "ok"}
            elif request.full_url.endswith("/api/documents/upload"):
                payload = {"id": "doc-1"}
            else:
                payload = {"id": "analysis-1"}
            return io.BytesIO(json.dumps(payload).encode())

        with (
            patch.object(cloud, "urlopen", side_effect=fake_urlopen),
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            pdf = Path(temp_dir) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            ids = cloud.import_into_studio(
                "http://localhost:3000", pdf, {"schema_name": "DoclingDocument"}
            )
        self.assertEqual(ids, ("doc-1", "analysis-1"))
        self.assertEqual(
            [url.removeprefix("http://localhost:3000") for url, _, _ in requests],
            ["/api/health", "/api/documents/upload", "/api/analyses/import"],
        )
        self.assertIn(b"%PDF-1.4", requests[1][1])
        self.assertEqual(json.loads(requests[2][1])["documentId"], "doc-1")

    def test_retries_import_when_studio_requires_older_schema_version(self):
        requests = []

        def fake_urlopen(request, *, timeout):
            requests.append((request.full_url, request.data or b""))
            if request.full_url.endswith("/api/health"):
                return io.BytesIO(b'{"status":"ok"}')
            if request.full_url.endswith("/api/documents/upload"):
                return io.BytesIO(b'{"id":"doc-1"}')
            payload = json.loads(request.data.decode("utf-8"))
            if payload["document"].get("version") == "1.11.0":
                raise cloud.HTTPError(
                    request.full_url,
                    400,
                    "Bad Request",
                    hdrs=None,
                    fp=io.BytesIO(
                        b"{\"detail\":\"Invalid DoclingDocument: Input should be '1.10.0' [type=literal_error, input_value='1.11.0', input_type=str] for version\"}"
                    ),
                )
            return io.BytesIO(b'{"analysisId":"analysis-1","status":"COMPLETED"}')

        with (
            patch.object(cloud, "urlopen", side_effect=fake_urlopen),
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            pdf = Path(temp_dir) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            doc = {"schema_name": "DoclingDocument", "version": "1.11.0"}
            ids = cloud.import_into_studio("http://localhost:3000", pdf, doc)
        self.assertEqual(ids, ("doc-1", "analysis-1"))
        self.assertEqual(doc["version"], "1.11.0")
        retried_doc = json.loads(requests[-1][1].decode("utf-8"))["document"]
        self.assertEqual(retried_doc["version"], "1.10.0")

    def test_import_json_flag_skips_colab_and_imports_existing_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            pdf = parent / "paper.pdf"
            json_file = parent / "paper.docling.json"
            pdf.write_bytes(b"%PDF-1.4\n")
            json_file.write_text('{"schema_name":"DoclingDocument"}')

            with (
                patch.object(
                    cloud.sys,
                    "argv",
                    [
                        "docling-cloud.py",
                        str(pdf),
                        "--import-json",
                        str(json_file),
                        "--studio-url",
                        "http://localhost:3000",
                    ],
                ),
                patch.object(cloud, "convert_with_colab") as mock_convert,
                patch.object(
                    cloud, "import_into_studio", return_value=("doc-1", "analysis-1")
                ) as mock_import,
            ):
                self.assertEqual(cloud.main(), 0)
                mock_convert.assert_not_called()
                mock_import.assert_called_once_with(
                    "http://localhost:3000",
                    pdf.resolve(),
                    {"schema_name": "DoclingDocument"},
                )


if __name__ == "__main__":
    unittest.main()
