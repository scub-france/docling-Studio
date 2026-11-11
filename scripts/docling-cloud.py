#!/usr/bin/env python3
"""Convert one PDF on Colab and optionally import the result into Docling Studio.

This command runs on the user's machine. It uses the Python modules in Google's
Colab CLI package for compute and Studio's existing HTTP API for import. No
Google credentials are passed to Studio.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


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


def convert_with_colab(
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

    client, Accelerator, Variant, ContentsClient, ColabRuntime, SessionState = (
        _colab_api(auth)
    )
    run_id = f"docling-{uuid.uuid4().hex[:10]}"
    remote_pdf = f"/content/{run_id}-{pdf.name}"
    remote_json = f"/content/{run_id}.docling.json"
    endpoint = None
    runtime = None
    try:
        print("Allocating Colab runtime...", flush=True)
        assigned = client.assign(
            uuid.uuid4(),
            variant=Variant.GPU if gpu else Variant.DEFAULT,
            accelerator=Accelerator(gpu.upper()) if gpu else Accelerator.NONE,
        )
        endpoint = assigned.endpoint
        info = assigned.runtime_proxy_info
        state = SessionState(
            name=run_id, token=info.token, url=info.url, endpoint=endpoint
        )
        contents = ContentsClient(state)
        runtime = ColabRuntime(info.url, info.token)
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
                    raise RuntimeError(
                        f"Pages {start}-{end} produced {len(document.pages)} pages"
                    )
                documents.append(document)
                print(f"Converted pages {start}-{end} of {page_count}", flush=True)
            merged = DoclingDocument.concatenate(documents)
            merged.name = pdf.stem
            if len(merged.pages) != page_count:
                raise RuntimeError(
                    f"Merged document has {len(merged.pages)} of {page_count} pages"
                )
            result_path.write_text(
                json.dumps(merged.export_to_dict()), encoding="utf-8"
            )
    finally:
        if runtime is not None:
            try:
                runtime.stop(shutdown_kernel=True)
            except Exception as exc:  # noqa: BLE001 - still release the billable runtime
                print(f"Warning: Colab kernel cleanup failed: {exc}", file=sys.stderr)
        if endpoint is not None:
            client.unassign(endpoint)
            print("Colab runtime released", flush=True)


def request_json(
    url: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    timeout: int = 600,
) -> dict:
    headers = {"Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    request = Request(
        url, data=data, headers=headers, method="POST" if data is not None else "GET"
    )
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
    doc_id = uploaded["id"]
    try:
        analysis_id = _import_analysis_payload(base, doc_id, document)
    except HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace") if err.fp else ""
        match = re.search(r"version\s+['\"]?(\d+\.\d+\.\d+)['\"]?", err_body) or (
            re.search(r"\b(1\.\d+\.\d+)\b", err_body)
            if "version" in err_body.lower()
            else None
        )
        if err.code == 400 and match and match.group(1) != document.get("version"):
            compat_doc = dict(document)
            compat_doc["version"] = match.group(1)
            analysis_id = _import_analysis_payload(base, doc_id, compat_doc)
        else:
            raise
    return doc_id, analysis_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="PDF to convert or import")
    parser.add_argument(
        "--gpu",
        choices=("T4", "L4", "G4", "H100", "A100"),
        help="Colab GPU; default is CPU",
    )
    parser.add_argument(
        "--colab-auth",
        choices=("oauth2", "adc"),
        default="oauth2",
        help="Colab CLI authentication method (default: oauth2)",
    )
    parser.add_argument(
        "--batch-pages",
        type=int,
        help="Convert and save this many pages at a time to limit memory use",
    )
    parser.add_argument(
        "--import-json",
        type=Path,
        help="Import an existing Docling JSON into --studio-url without running Colab",
    )
    parser.add_argument(
        "--studio-url", help="Studio base URL, for example http://localhost:3000"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Downloads",
        help="Directory for the PDF and Docling JSON (default: ~/Downloads)",
    )
    args = parser.parse_args()
    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        parser.error("pdf must be an existing PDF file")
    if args.batch_pages is not None and args.batch_pages < 1:
        parser.error("--batch-pages must be a positive integer")
    if args.import_json is not None:
        if not args.studio_url:
            parser.error("--import-json requires --studio-url")
        json_path = args.import_json.expanduser().resolve()
        if not json_path.is_file():
            parser.error("--import-json must be an existing JSON file")
        document = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            parser.error("--import-json does not contain a Docling JSON object")
        try:
            doc_id, analysis_id = import_into_studio(args.studio_url, pdf, document)
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            print(f"Studio import failed: {exc}", file=sys.stderr)
            return 1
        print(f"Imported into Studio: document={doc_id} analysis={analysis_id}")
        return 0

    output_dir = (
        args.output_dir.expanduser().resolve() / f"{pdf.stem}-{uuid.uuid4().hex[:8]}"
    )
    output_dir.mkdir(parents=True)
    saved_pdf = output_dir / pdf.name
    saved_json = output_dir / f"{pdf.stem}.docling.json"
    shutil.copy2(pdf, saved_pdf)
    try:
        convert_with_colab(pdf, saved_json, args.gpu, args.colab_auth, args.batch_pages)
        document = json.loads(saved_json.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise TypeError("Colab returned JSON that is not a Docling document")
    except Exception as exc:  # noqa: BLE001 - provider exceptions vary by package version
        detail = (
            str(exc)
            if isinstance(exc, (RuntimeError, OSError, TypeError, ValueError))
            else type(exc).__name__
        )
        print(
            f"Conversion failed: {detail}\nPDF retained at {saved_pdf}", file=sys.stderr
        )
        return 1

    print(f"Saved PDF and Docling JSON to {output_dir}")
    if args.studio_url:
        try:
            doc_id, analysis_id = import_into_studio(
                args.studio_url, saved_pdf, document
            )
        except (HTTPError, ValueError, KeyError) as exc:
            print(
                f"Studio import failed; files remain at {output_dir}: {exc}",
                file=sys.stderr,
            )
            return 1
        except (URLError, TimeoutError) as exc:
            print(f"Studio unavailable; files are ready for manual import: {exc}")
        else:
            print(f"Imported into Studio: document={doc_id} analysis={analysis_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
