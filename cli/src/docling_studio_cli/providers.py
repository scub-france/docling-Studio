"""Pluggable PDF conversion providers (Google Colab, local Docling, and custom extensions)."""

from __future__ import annotations

import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ConversionOptions:
    gpu: str | None = None
    colab_auth: str = "oauth2"
    batch_pages: int | None = None
    workers: int = 1


class ConversionProvider(Protocol):
    name: str
    description: str

    def convert(self, pdf: Path, result_path: Path, options: ConversionOptions) -> None: ...


def _colab_api(auth: str):
    try:
        from colab_cli.auth import AuthProvider, get_credentials
        from colab_cli.client import Accelerator, Client, Prod, Variant
        from colab_cli.contents import ContentsClient
        from colab_cli.runtime import ColabRuntime
        from colab_cli.state import SessionState
    except ImportError as exc:
        raise RuntimeError(
            "Install google-colab-cli in this Python environment; see docs/cloud-conversion.md"
        ) from exc

    client = Client(Prod(), get_credentials(provider=AuthProvider(auth)))
    return client, Accelerator, Variant, ContentsClient, ColabRuntime, SessionState


def _execute(runtime, code: str, expected_marker: str, *, timeout: int = 900) -> None:
    outputs = runtime.execute_code(code, timeout=timeout)
    for item in outputs:
        if item.get("output_type") == "error":
            raise RuntimeError(f"Colab execution failed: {item.get('evalue') or item}")
    if not any(expected_marker in str(item.get("text", "")) for item in outputs):
        raise RuntimeError(f"Colab did not report {expected_marker}")


def convert_single_colab(
    pdf: Path,
    result_path: Path,
    gpu: str | None,
    auth: str = "oauth2",
    batch_pages: int | None = None,
) -> None:
    page_count = None
    if batch_pages is not None:
        try:
            from docling_core.types.doc import DoclingDocument
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "Page batches require pypdf and docling-core in this Python environment"
            ) from exc
        page_count = len(PdfReader(str(pdf)).pages)

    client, accelerator_cls, variant_cls, contents_cls, runtime_cls, state_cls = _colab_api(auth)
    run_id = f"docling-{uuid.uuid4().hex[:10]}"
    remote_pdf = f"/content/{run_id}-{pdf.name}"
    remote_json = f"/content/{run_id}.docling.json"
    endpoint = None
    runtime = None
    try:
        print("Allocating Colab runtime...", flush=True)
        assigned = client.assign(
            uuid.uuid4(),
            variant=variant_cls.GPU if gpu else variant_cls.DEFAULT,
            accelerator=accelerator_cls(gpu.upper()) if gpu else accelerator_cls.NONE,
        )
        endpoint = assigned.endpoint
        info = assigned.runtime_proxy_info
        state = state_cls(name=run_id, token=info.token, url=info.url, endpoint=endpoint)
        contents = contents_cls(state)
        runtime = runtime_cls(info.url, info.token)
        contents.upload(str(pdf), remote_pdf)
        print("Installing Docling on Colab...", flush=True)
        _execute(
            runtime,
            "import importlib.util, subprocess, sys\n"
            "if importlib.util.find_spec('docling') is None:\n"
            "    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', "
            "'docling>=2.80,<3.0'])\n"
            "print('DOCLING_READY')\n",
            "DOCLING_READY",
        )
        print("Converting PDF on Colab...", flush=True)
        gpu_check = (
            "import torch\n"
            "if not torch.cuda.is_available():\n"
            "    raise RuntimeError('Colab GPU is unavailable')\n"
            if gpu
            else ""
        )
        setup = (
            "import json, os, gc\n"
            "from pathlib import Path\n"
            f"os.environ['DOCLING_DEVICE'] = {'cuda' if gpu else 'cpu'!r}\n"
            f"{gpu_check}"
            "from docling.document_converter import DocumentConverter\n"
            "converter = DocumentConverter()\n"
            "print('DOCLING_READY_TO_CONVERT')\n"
        )
        _execute(runtime, setup, "DOCLING_READY_TO_CONVERT")
        if batch_pages is None:
            script = (
                f"result = converter.convert({remote_pdf!r})\n"
                f"Path({remote_json!r}).write_text("
                "json.dumps(result.document.export_to_dict()), encoding='utf-8')\n"
                "print('DOCLING_CONVERTED')\n"
            )
            _execute(runtime, script, "DOCLING_CONVERTED", timeout=3600)
            contents.download(remote_json, str(result_path))
        else:
            assert page_count is not None
            parts_dir = result_path.parent / "parts"
            parts_dir.mkdir(exist_ok=True)
            documents = []
            for start in range(1, page_count + 1, batch_pages):
                end = min(start + batch_pages - 1, page_count)
                remote_part = f"/content/{run_id}-{start}-{end}.docling.json"
                local_part = parts_dir / f"pages-{start:04d}-{end:04d}.docling.json"
                script = (
                    f"result = converter.convert({remote_pdf!r}, page_range=({start}, {end}))\n"
                    f"Path({remote_part!r}).write_text("
                    "json.dumps(result.document.export_to_dict()), encoding='utf-8')\n"
                    "del result\n"
                    "gc.collect()\n"
                    "print('DOCLING_CONVERTED')\n"
                )
                _execute(runtime, script, "DOCLING_CONVERTED")
                contents.download(remote_part, str(local_part))
                document = DoclingDocument.model_validate_json(local_part.read_text())
                if len(document.pages) != end - start + 1:
                    raise RuntimeError(f"Pages {start}-{end} produced {len(document.pages)} pages")
                documents.append(document)
                print(f"Converted pages {start}-{end} of {page_count}", flush=True)
            merged = DoclingDocument.concatenate(documents)
            merged.name = pdf.stem
            if len(merged.pages) != page_count:
                raise RuntimeError(f"Merged document has {len(merged.pages)} of {page_count} pages")
            result_path.write_text(json.dumps(merged.export_to_dict()), encoding="utf-8")
    finally:
        if runtime is not None:
            try:
                runtime.stop(shutdown_kernel=True)
            except Exception as exc:
                print(f"Warning: Colab kernel cleanup failed: {exc}", file=sys.stderr)
        if endpoint is not None:
            client.unassign(endpoint)
            print("Colab runtime released", flush=True)


def split_pdf(pdf: Path, output_dir: Path, workers: int) -> list[tuple[int, int, Path]]:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf))
    page_count = len(reader.pages)
    pages_per_part = (page_count + workers - 1) // workers
    parts = []
    for index, start_index in enumerate(range(0, page_count, pages_per_part), 1):
        end_index = min(start_index + pages_per_part, page_count)
        part_dir = output_dir / f"part-{index:02d}"
        part_dir.mkdir(exist_ok=True)
        part_pdf = part_dir / f"part-{index:02d}.pdf"
        writer = PdfWriter()
        for page_index in range(start_index, end_index):
            writer.add_page(reader.pages[page_index])
        with part_pdf.open("wb") as stream:
            writer.write(stream)
        parts.append((start_index + 1, end_index, part_pdf))
    return parts


def _convert_colab_part(
    part: tuple[int, int, Path],
    gpu: str | None,
    auth: str,
    batch_pages: int | None,
) -> tuple[int, int, Path]:
    from docling_core.types.doc import DoclingDocument

    start, end, part_pdf = part
    result_path = part_pdf.with_suffix(".docling.json")
    convert_single_colab(part_pdf, result_path, gpu, auth, batch_pages)
    document = DoclingDocument.model_validate_json(result_path.read_text())
    if len(document.pages) != end - start + 1:
        raise RuntimeError(f"Part {start}-{end} has {len(document.pages)} pages")
    print(f"Finished source pages {start}-{end}", flush=True)
    return start, end, result_path


class ColabProvider:
    name = "colab"
    description = "Google Colab CPU/GPU runtime via google-colab-cli (single or parallel workers)"

    def convert(self, pdf: Path, result_path: Path, options: ConversionOptions) -> None:
        if options.workers <= 1:
            convert_single_colab(
                pdf,
                result_path,
                options.gpu,
                options.colab_auth,
                options.batch_pages,
            )
            return

        from docling_core.types.doc import DoclingDocument

        output_dir = result_path.parent
        parts = split_pdf(pdf, output_dir, options.workers)
        print(
            "Parallel page ranges: " + ", ".join(f"{start}-{end}" for start, end, _ in parts),
            flush=True,
        )
        batch_pages = options.batch_pages or 25
        results: dict[int, Path] = {}
        failed_parts = []
        with ThreadPoolExecutor(max_workers=options.workers) as executor:
            futures = {
                executor.submit(
                    _convert_colab_part,
                    part,
                    options.gpu,
                    options.colab_auth,
                    batch_pages,
                ): part
                for part in parts
            }
            for future in as_completed(futures):
                start, end, _ = futures[future]
                try:
                    _, _, part_result = future.result()
                    results[start] = part_result
                except Exception as exc:
                    failed_parts.append((futures[future], exc))
                    print(
                        f"Part {start}-{end} failed: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )

        for part, error in failed_parts:
            start, end, _ = part
            if "Precondition Failed" not in str(error):
                raise RuntimeError(
                    f"Part {start}-{end} failed: {error}. Completed parts remain in {output_dir}"
                ) from error
            print(
                f"Retrying pages {start}-{end} after a runtime slot opened",
                flush=True,
            )
            _, _, part_result = _convert_colab_part(
                part, options.gpu, options.colab_auth, batch_pages
            )
            results[start] = part_result

        documents = [
            DoclingDocument.model_validate_json(results[start].read_text())
            for start in sorted(results)
        ]
        merged = DoclingDocument.concatenate(documents)
        merged.name = pdf.stem
        merged.origin = None
        expected_pages = parts[-1][1]
        if len(merged.pages) != expected_pages:
            raise RuntimeError(f"Merged {len(merged.pages)} of {expected_pages} pages")
        result_path.write_text(json.dumps(merged.export_to_dict()), encoding="utf-8")


class LocalProvider:
    name = "local"
    description = "Local Docling installation on this machine"

    def convert(self, pdf: Path, result_path: Path, options: ConversionOptions) -> None:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise RuntimeError(
                "Local conversion requires docling installed (e.g. `uv tool install './cli[local]'`)"
            ) from exc

        if options.gpu:
            os.environ.setdefault("DOCLING_DEVICE", "cuda")
        converter = DocumentConverter()
        if options.batch_pages is None:
            result = converter.convert(str(pdf))
            result_path.write_text(json.dumps(result.document.export_to_dict()), encoding="utf-8")
            return

        from docling_core.types.doc import DoclingDocument
        from pypdf import PdfReader

        page_count = len(PdfReader(str(pdf)).pages)
        parts_dir = result_path.parent / "parts"
        parts_dir.mkdir(exist_ok=True)
        documents = []
        for start in range(1, page_count + 1, options.batch_pages):
            end = min(start + options.batch_pages - 1, page_count)
            local_part = parts_dir / f"pages-{start:04d}-{end:04d}.docling.json"
            result = converter.convert(str(pdf), page_range=(start, end))
            local_part.write_text(json.dumps(result.document.export_to_dict()), encoding="utf-8")
            doc = DoclingDocument.model_validate_json(local_part.read_text())
            documents.append(doc)
            print(f"Converted pages {start}-{end} of {page_count}", flush=True)
        merged = DoclingDocument.concatenate(documents)
        merged.name = pdf.stem
        result_path.write_text(json.dumps(merged.export_to_dict()), encoding="utf-8")


_PROVIDERS: dict[str, ConversionProvider] = {
    ColabProvider.name: ColabProvider(),
    LocalProvider.name: LocalProvider(),
}


def register_provider(provider: ConversionProvider) -> None:
    _PROVIDERS[provider.name] = provider


def get_provider(name: str) -> ConversionProvider:
    if name not in _PROVIDERS:
        available = ", ".join(sorted(_PROVIDERS))
        raise KeyError(f"Unknown provider {name!r}; available providers: {available}")
    return _PROVIDERS[name]


def list_providers() -> list[ConversionProvider]:
    return [_PROVIDERS[name] for name in sorted(_PROVIDERS)]
