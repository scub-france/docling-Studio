"""CLI entry point for `docling-studio`."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError

from docling_studio_cli.providers import (
    ConversionOptions,
    get_provider,
    list_providers,
)
from docling_studio_cli.studio import import_into_studio


def _resolve_studio_url(cli_value: str | None) -> str | None:
    return cli_value or os.environ.get("DOCLING_STUDIO_URL")


def _cmd_convert(args: argparse.Namespace) -> int:
    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        print("Error: pdf must be an existing PDF file", file=sys.stderr)
        return 2
    if args.batch_pages is not None and args.batch_pages < 1:
        print("Error: --batch-pages must be a positive integer", file=sys.stderr)
        return 2
    if args.workers < 1:
        print("Error: --workers must be a positive integer", file=sys.stderr)
        return 2

    provider = get_provider(args.provider)
    suffix = "parallel-" if args.workers > 1 else ""
    output_dir = (
        args.output_dir.expanduser().resolve() / f"{pdf.stem}-{suffix}{uuid.uuid4().hex[:8]}"
    )
    output_dir.mkdir(parents=True)
    saved_pdf = output_dir / pdf.name
    saved_json = output_dir / f"{pdf.stem}.docling.json"
    shutil.copy2(pdf, saved_pdf)

    options = ConversionOptions(
        gpu=args.gpu,
        colab_auth=args.colab_auth,
        batch_pages=args.batch_pages,
        workers=args.workers,
    )
    try:
        provider.convert(pdf, saved_json, options)
        document = json.loads(saved_json.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise TypeError("Provider returned JSON that is not a Docling document")
    except Exception as exc:
        detail = (
            str(exc)
            if isinstance(exc, (RuntimeError, OSError, TypeError, ValueError))
            else type(exc).__name__
        )
        print(
            f"Conversion failed: {detail}\nPDF retained at {saved_pdf}",
            file=sys.stderr,
        )
        return 1

    print(f"Saved PDF and Docling JSON to {output_dir}")
    studio_url = _resolve_studio_url(args.studio_url)
    if studio_url:
        try:
            doc_id, analysis_id = import_into_studio(studio_url, saved_pdf, document)
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


def _cmd_import(args: argparse.Namespace) -> int:
    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        print("Error: pdf must be an existing PDF file", file=sys.stderr)
        return 2
    studio_url = _resolve_studio_url(args.studio_url)
    if not studio_url:
        print(
            "Error: --studio-url (or DOCLING_STUDIO_URL) is required for import",
            file=sys.stderr,
        )
        return 2

    json_path = args.json.expanduser().resolve() if args.json else pdf.with_suffix(".docling.json")
    if not json_path.is_file():
        print(f"Error: Docling JSON file not found: {json_path}", file=sys.stderr)
        return 2

    document = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        print("Error: JSON file does not contain a Docling document object", file=sys.stderr)
        return 2

    try:
        doc_id, analysis_id = import_into_studio(studio_url, pdf, document)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        print(f"Studio import failed: {exc}", file=sys.stderr)
        return 1

    print(f"Imported into Studio: document={doc_id} analysis={analysis_id}")
    return 0


def _cmd_providers(_args: argparse.Namespace) -> int:
    for provider in list_providers():
        print(f"{provider.name}\t{provider.description}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docling-studio",
        description="Convert PDFs with Google Colab or local Docling and import them into Docling Studio.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    provider_names = [p.name for p in list_providers()]
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a PDF with a compute provider and optionally upload to Docling Studio",
    )
    convert_parser.add_argument("pdf", type=Path, help="PDF file to convert")
    convert_parser.add_argument(
        "--provider",
        choices=provider_names,
        default="colab",
        help="Compute provider to run Docling (default: colab)",
    )
    convert_parser.add_argument(
        "--gpu",
        choices=("T4", "L4", "G4", "H100", "A100"),
        help="GPU accelerator to request on Colab (default: CPU)",
    )
    convert_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel Colab runtimes to split the PDF across (default: 1)",
    )
    convert_parser.add_argument(
        "--batch-pages",
        type=int,
        help="Convert and save this many pages at a time to limit peak memory use",
    )
    convert_parser.add_argument(
        "--colab-auth",
        choices=("oauth2", "adc"),
        default="oauth2",
        help="Colab CLI authentication method (default: oauth2)",
    )
    convert_parser.add_argument(
        "--studio-url",
        help="Docling Studio base URL (or set DOCLING_STUDIO_URL)",
    )
    convert_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Downloads",
        help="Directory for the saved PDF and Docling JSON (default: ~/Downloads)",
    )
    convert_parser.set_defaults(func=_cmd_convert)

    import_parser = subparsers.add_parser(
        "import",
        help="Upload a PDF and an existing Docling JSON directly to a Docling Studio instance",
    )
    import_parser.add_argument("pdf", type=Path, help="PDF file to upload")
    import_parser.add_argument(
        "--json",
        type=Path,
        help="Docling JSON file (defaults to <pdf-stem>.docling.json beside the PDF)",
    )
    import_parser.add_argument(
        "--studio-url",
        help="Docling Studio base URL (or set DOCLING_STUDIO_URL)",
    )
    import_parser.set_defaults(func=_cmd_import)

    providers_parser = subparsers.add_parser(
        "providers",
        help="List available PDF conversion providers",
    )
    providers_parser.set_defaults(func=_cmd_providers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
