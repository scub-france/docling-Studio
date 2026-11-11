"""Unit tests for the installable `docling-studio-cli` package, Pydantic models, and settings."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError

from pydantic import ValidationError

CLI_SRC = Path(__file__).resolve().parents[1] / "src"
if str(CLI_SRC) not in sys.path:
    sys.path.insert(0, str(CLI_SRC))

from docling_studio_cli import (  # noqa: E402
    CliSettings,
    ColabAuthMethod,
    ConversionOptions,
    ConversionProvider,
    GpuType,
    StudioImportResult,
    cli,
    get_provider,
    import_into_studio,
    list_providers,
    load_settings,
    providers,
    register_provider,
    studio,
)


class SettingsAndModelsTests(unittest.TestCase):
    def test_pydantic_settings_loads_from_json_config_env_and_cli_overrides(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "settings.json"
            saved = CliSettings(
                studio_url="https://studio.example.com/",
                gpu=GpuType.T4,
                workers=2,
                batch_pages=25,
                colab_auth=ColabAuthMethod.ADC,
            )
            saved.save(config_file)

            loaded = load_settings(config_path=config_file)
            self.assertEqual(loaded.studio_url, "https://studio.example.com")
            self.assertEqual(loaded.gpu, GpuType.T4)
            self.assertEqual(loaded.workers, 2)
            self.assertEqual(loaded.batch_pages, 25)
            self.assertEqual(loaded.colab_auth, ColabAuthMethod.ADC)

            with patch.dict(
                os.environ,
                {
                    "DOCLING_STUDIO_GPU": "L4",
                    "DOCLING_STUDIO_WORKERS": "4",
                },
                clear=False,
            ):
                env_loaded = load_settings(config_path=config_file)
                self.assertEqual(env_loaded.gpu, GpuType.L4)
                self.assertEqual(env_loaded.workers, 4)

                cli_override = load_settings(
                    config_path=config_file,
                    gpu="A100",
                    workers=1,
                )
                self.assertEqual(cli_override.gpu, GpuType.A100)
                self.assertEqual(cli_override.workers, 1)

    def test_config_subcommand_set_show_and_reset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "settings.json"
            code = cli.main(
                [
                    "--config",
                    str(config_file),
                    "config",
                    "set",
                    "--studio-url",
                    "http://localhost:3000/",
                    "--gpu",
                    "T4",
                    "--workers",
                    "3",
                    "--batch-pages",
                    "20",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue(config_file.is_file())
            loaded = load_settings(config_path=config_file)
            self.assertEqual(loaded.studio_url, "http://localhost:3000")
            self.assertEqual(loaded.gpu, GpuType.T4)
            self.assertEqual(loaded.workers, 3)
            self.assertEqual(loaded.batch_pages, 20)

            self.assertEqual(cli.main(["--config", str(config_file), "config", "show"]), 0)
            self.assertEqual(cli.main(["--config", str(config_file), "config", "reset"]), 0)
            self.assertFalse(config_file.is_file())

    def test_models_reject_invalid_values(self):
        with self.assertRaises(ValidationError):
            ConversionOptions(workers=0)
        with self.assertRaises(ValidationError):
            ConversionOptions(batch_pages=0)
        with self.assertRaises(ValidationError):
            CliSettings(studio_url="not-a-valid-url")


class ProviderRegistryTests(unittest.TestCase):
    def test_lists_builtin_providers_and_allows_custom_registration(self):
        names = [p.name for p in list_providers()]
        self.assertIn("colab", names)
        self.assertIn("local", names)

        class CustomProvider:
            name = "custom-test"
            description = "Custom provider for testing"

            def convert(self, pdf: Path, result_path: Path, options) -> None:
                result_path.write_text('{"schema_name":"DoclingDocument"}')

        custom: ConversionProvider = CustomProvider()
        register_provider(custom)
        try:
            self.assertIs(get_provider("custom-test"), custom)
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf = Path(temp_dir) / "sample.pdf"
                pdf.write_bytes(b"%PDF-1.4\n")
                code = cli.main(
                    [
                        "convert",
                        str(pdf),
                        "--provider",
                        "custom-test",
                        "--output-dir",
                        temp_dir,
                    ]
                )
                self.assertEqual(code, 0)
                saved = list(Path(temp_dir).glob("sample-*/sample.docling.json"))
                self.assertEqual(len(saved), 1)
        finally:
            providers._PROVIDERS.pop("custom-test", None)


class ColabProviderTests(unittest.TestCase):
    def fake_api(self, *, conversion_error=False, batched=False):
        events = []

        class Accelerator(StrEnum):
            NONE = "NONE"
            T4 = "T4"

        class Variant(StrEnum):
            DEFAULT = "DEFAULT"
            GPU = "GPU"

        class Client:
            def assign(self, _request_id, *, variant, accelerator):
                events.append(("assign", variant, accelerator))
                return SimpleNamespace(
                    endpoint="ep-1",
                    runtime_proxy_info=SimpleNamespace(token="token", url="https://colab.example"),
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

    def test_colab_cli_convert_uses_saved_settings_and_imports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "settings.json"
            CliSettings(
                studio_url="http://localhost:3000",
                gpu=GpuType.T4,
                output_dir=Path(temp_dir),
            ).save(config_file)

            pdf = Path(temp_dir) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            events, api = self.fake_api()
            fake_result = StudioImportResult(
                studio_url="http://localhost:3000",
                document_id="doc-1",
                analysis_id="analysis-1",
            )
            with (
                patch.object(providers, "_colab_api", return_value=api),
                patch.object(cli, "import_into_studio", return_value=fake_result) as mock_import,
            ):
                code = cli.main(
                    [
                        "--config",
                        str(config_file),
                        "convert",
                        str(pdf),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                [event[0] for event in events],
                ["assign", "upload", "download", "stop", "unassign"],
            )
            self.assertEqual(events[0][2], api[1].T4)
            mock_import.assert_called_once()

    @unittest.skipUnless(
        importlib.util.find_spec("pypdf") and importlib.util.find_spec("docling_core"),
        "batch dependencies are not installed",
    )
    def test_parallel_workers_split_and_merge(self):
        from pypdf import PdfWriter

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "book.pdf"
            writer = PdfWriter()
            for _ in range(4):
                writer.add_blank_page(width=100, height=100)
            with pdf.open("wb") as stream:
                writer.write(stream)
            _events, api = self.fake_api(batched=True)
            with patch.object(providers, "_colab_api", return_value=api):
                code = cli.main(
                    [
                        "convert",
                        str(pdf),
                        "--provider",
                        "colab",
                        "--workers",
                        "2",
                        "--batch-pages",
                        "1",
                        "--output-dir",
                        temp_dir,
                    ]
                )
            self.assertEqual(code, 0)
            merged_files = list(Path(temp_dir).glob("book-parallel-*/book.docling.json"))
            self.assertEqual(len(merged_files), 1)
            merged = json.loads(merged_files[0].read_text())
            self.assertEqual(list(merged["pages"]), ["1", "2", "3", "4"])


class StudioImportSubcommandTests(unittest.TestCase):
    def test_import_subcommand_uses_default_json_and_retries_schema_version(self):
        requests = []

        def fake_urlopen(request, *, timeout):
            requests.append((request.full_url, request.data or b""))
            if request.full_url.endswith("/api/health"):
                return io.BytesIO(b'{"status":"ok"}')
            if request.full_url.endswith("/api/documents/upload"):
                return io.BytesIO(b'{"id":"doc-1"}')
            payload = json.loads(request.data.decode("utf-8"))
            if payload["document"].get("version") == "1.11.0":
                raise studio.HTTPError(
                    request.full_url,
                    400,
                    "Bad Request",
                    hdrs=None,
                    fp=io.BytesIO(
                        b'{"detail":"Invalid DoclingDocument: Input should be \'1.10.0\' for version"}'
                    ),
                )
            return io.BytesIO(b'{"analysisId":"analysis-1","status":"COMPLETED"}')

        with (
            patch.object(studio, "urlopen", side_effect=fake_urlopen),
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            pdf = Path(temp_dir) / "paper.pdf"
            json_path = Path(temp_dir) / "paper.docling.json"
            pdf.write_bytes(b"%PDF-1.4\n")
            json_path.write_text(
                json.dumps({"schema_name": "DoclingDocument", "version": "1.11.0"})
            )
            code = cli.main(
                [
                    "import",
                    str(pdf),
                    "--studio-url",
                    "http://localhost:3000",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(json_path.read_text())["version"],
                "1.11.0",
            )
            retried_doc = json.loads(requests[-1][1].decode("utf-8"))["document"]
            self.assertEqual(retried_doc["version"], "1.10.0")

    def test_unreachable_studio_retains_converted_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            _events, api = ColabProviderTests().fake_api()
            with (
                patch.object(providers, "_colab_api", return_value=api),
                patch.object(cli, "import_into_studio", side_effect=URLError("offline")),
            ):
                code = cli.main(
                    [
                        "convert",
                        str(pdf),
                        "--output-dir",
                        temp_dir,
                        "--studio-url",
                        "http://localhost:3000",
                    ]
                )
            self.assertEqual(code, 0)
            saved = list(Path(temp_dir).glob("paper-*/paper.docling.json"))
            self.assertEqual(len(saved), 1)
            self.assertIsNotNone(import_into_studio)


if __name__ == "__main__":
    unittest.main()
