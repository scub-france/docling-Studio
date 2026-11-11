"""CLI entry point for `docling-studio`."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError

from pydantic import ValidationError

from docling_studio_cli.models import (
    ColabAuthMethod,
    ConversionJobConfig,
    GpuType,
    ImportJobConfig,
)
from docling_studio_cli.providers import (
    get_provider,
    list_provider_descriptors,
    list_providers,
)
from docling_studio_cli.settings import (
    CliSettings,
    default_config_path,
    load_settings,
)
from docling_studio_cli.studio import import_into_studio


def _cmd_convert(args: argparse.Namespace) -> int:
    try:
        settings = load_settings(
            config_path=args.config,
            provider=args.provider,
            gpu=args.gpu,
            workers=args.workers,
            batch_pages=args.batch_pages,
            colab_auth=args.colab_auth,
            studio_url=args.studio_url,
            output_dir=args.output_dir,
        )
        job = ConversionJobConfig(
            pdf=args.pdf,
            provider=settings.provider,
            options=settings.to_conversion_options(),
            output_dir=settings.output_dir,
            studio_url=settings.studio_url,
            request_timeout_seconds=settings.request_timeout_seconds,
        )
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"])
            print(f"Error ({loc}): {err['msg']}", file=sys.stderr)
        return 2

    provider = get_provider(job.provider)
    suffix = "parallel-" if job.options.workers > 1 else ""
    output_dir = job.output_dir / f"{job.pdf.stem}-{suffix}{uuid.uuid4().hex[:8]}"
    output_dir.mkdir(parents=True)
    saved_pdf = output_dir / job.pdf.name
    saved_json = output_dir / f"{job.pdf.stem}.docling.json"
    shutil.copy2(job.pdf, saved_pdf)

    try:
        provider.convert(job.pdf, saved_json, job.options)
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
    if job.studio_url:
        try:
            result = import_into_studio(
                job.studio_url,
                saved_pdf,
                document,
                timeout=job.request_timeout_seconds,
            )
        except (HTTPError, ValidationError, ValueError, KeyError) as exc:
            print(
                f"Studio import failed; files remain at {output_dir}: {exc}",
                file=sys.stderr,
            )
            return 1
        except (URLError, TimeoutError) as exc:
            print(f"Studio unavailable; files are ready for manual import: {exc}")
        else:
            print(
                f"Imported into Studio: document={result.document_id} "
                f"analysis={result.analysis_id} url={result.document_url}"
            )
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    try:
        settings = load_settings(
            config_path=args.config,
            studio_url=args.studio_url,
        )
        if not settings.studio_url:
            print(
                "Error: --studio-url (or DOCLING_STUDIO_STUDIO_URL / saved config) is required for import",
                file=sys.stderr,
            )
            return 2
        pdf_resolved = args.pdf.expanduser().resolve()
        json_candidate = (
            args.json if args.json is not None else pdf_resolved.with_suffix(".docling.json")
        )
        job = ImportJobConfig(
            pdf=args.pdf,
            json_path=json_candidate,
            studio_url=settings.studio_url,
            request_timeout_seconds=settings.request_timeout_seconds,
        )
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"])
            print(f"Error ({loc}): {err['msg']}", file=sys.stderr)
        return 2

    document = json.loads(job.json_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        print(
            "Error: JSON file does not contain a Docling document object",
            file=sys.stderr,
        )
        return 2

    try:
        result = import_into_studio(
            job.studio_url,
            job.pdf,
            document,
            timeout=job.request_timeout_seconds,
        )
    except (HTTPError, URLError, TimeoutError, ValidationError, ValueError, KeyError) as exc:
        print(f"Studio import failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Imported into Studio: document={result.document_id} "
        f"analysis={result.analysis_id} url={result.document_url}"
    )
    return 0


def _cmd_providers(_args: argparse.Namespace) -> int:
    for descriptor in list_provider_descriptors():
        print(f"{descriptor.name}\t{descriptor.description}")
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    config_path = (args.config or default_config_path()).expanduser().resolve()
    if args.config_action == "path":
        print(config_path)
        return 0
    if args.config_action == "reset":
        if config_path.is_file():
            config_path.unlink()
        print(f"Reset configuration at {config_path}")
        return 0
    if args.config_action == "show":
        try:
            settings = load_settings(config_path=config_path)
        except ValidationError as exc:
            print(f"Invalid configuration: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(settings.model_dump(mode="json"), indent=2))
        return 0
    if args.config_action == "set":
        existing: dict = {}
        if config_path.is_file():
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                existing = dict(raw)
        updates = {
            "studio_url": args.studio_url,
            "provider": args.provider,
            "gpu": None if args.clear_gpu else args.gpu,
            "workers": args.workers,
            "batch_pages": None if args.clear_batch_pages else args.batch_pages,
            "colab_auth": args.colab_auth,
            "output_dir": args.output_dir,
            "request_timeout_seconds": args.request_timeout_seconds,
        }
        for key, value in updates.items():
            if value is not None:
                existing[key] = value
        if args.clear_gpu:
            existing["gpu"] = None
        if args.clear_batch_pages:
            existing["batch_pages"] = None
        if args.clear_studio_url:
            existing["studio_url"] = None

        try:
            validated = CliSettings(**existing)
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(part) for part in err["loc"])
                print(f"Error ({loc}): {err['msg']}", file=sys.stderr)
            return 2
        saved_path = validated.save(config_path)
        print(f"Saved settings to {saved_path}")
        print(json.dumps(validated.model_dump(mode="json"), indent=2))
        return 0
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docling-studio",
        description="Convert PDFs with Google Colab or local Docling and import them into Docling Studio.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to JSON settings file (default: ~/.config/docling-studio/settings.json)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    provider_names = [p.name for p in list_providers()]
    gpu_choices = tuple(g.value for g in GpuType)
    auth_choices = tuple(a.value for a in ColabAuthMethod)

    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a PDF with a compute provider and optionally upload to Docling Studio",
    )
    convert_parser.add_argument("pdf", type=Path, help="PDF file to convert")
    convert_parser.add_argument(
        "--provider",
        choices=provider_names,
        default=None,
        help="Compute provider to run Docling (overrides settings/env; default: colab)",
    )
    convert_parser.add_argument(
        "--gpu",
        choices=gpu_choices,
        default=None,
        help="GPU accelerator to request on Colab (overrides settings/env)",
    )
    convert_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel Colab runtimes to split the PDF across (overrides settings/env)",
    )
    convert_parser.add_argument(
        "--batch-pages",
        type=int,
        default=None,
        help="Convert and save this many pages at a time to limit peak memory use",
    )
    convert_parser.add_argument(
        "--colab-auth",
        choices=auth_choices,
        default=None,
        help="Colab CLI authentication method (oauth2 or adc)",
    )
    convert_parser.add_argument(
        "--studio-url",
        default=None,
        help="Docling Studio base URL (overrides settings/env)",
    )
    convert_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the saved PDF and Docling JSON (overrides settings/env)",
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
        default=None,
        help="Docling JSON file (defaults to <pdf-stem>.docling.json beside the PDF)",
    )
    import_parser.add_argument(
        "--studio-url",
        default=None,
        help="Docling Studio base URL (overrides settings/env)",
    )
    import_parser.set_defaults(func=_cmd_import)

    providers_parser = subparsers.add_parser(
        "providers",
        help="List available PDF conversion providers",
    )
    providers_parser.set_defaults(func=_cmd_providers)

    config_parser = subparsers.add_parser(
        "config",
        help="Inspect or update persistent CLI default settings (backed by pydantic-settings)",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_action", required=True)

    config_show = config_subparsers.add_parser(
        "show",
        help="Show effective CLI settings (merged from env, .env, and settings.json)",
    )
    config_show.set_defaults(func=_cmd_config)

    config_path_cmd = config_subparsers.add_parser(
        "path",
        help="Print the path to the persistent JSON settings file",
    )
    config_path_cmd.set_defaults(func=_cmd_config)

    config_reset = config_subparsers.add_parser(
        "reset",
        help="Remove the persistent JSON settings file and restore built-in defaults",
    )
    config_reset.set_defaults(func=_cmd_config)

    config_set = config_subparsers.add_parser(
        "set",
        help="Persist default values to settings.json",
    )
    config_set.add_argument("--studio-url", help="Default Docling Studio URL")
    config_set.add_argument(
        "--clear-studio-url",
        action="store_true",
        help="Clear the default Docling Studio URL",
    )
    config_set.add_argument(
        "--provider",
        choices=provider_names,
        help="Default conversion provider",
    )
    config_set.add_argument(
        "--gpu",
        choices=gpu_choices,
        help="Default GPU accelerator on Colab",
    )
    config_set.add_argument(
        "--clear-gpu",
        action="store_true",
        help="Reset default GPU back to CPU (None)",
    )
    config_set.add_argument(
        "--workers",
        type=int,
        help="Default number of parallel Colab runtimes",
    )
    config_set.add_argument(
        "--batch-pages",
        type=int,
        help="Default page batch size",
    )
    config_set.add_argument(
        "--clear-batch-pages",
        action="store_true",
        help="Clear default page batch size",
    )
    config_set.add_argument(
        "--colab-auth",
        choices=auth_choices,
        help="Default Colab CLI authentication method",
    )
    config_set.add_argument(
        "--output-dir",
        type=Path,
        help="Default output directory for saved conversions",
    )
    config_set.add_argument(
        "--request-timeout-seconds",
        type=int,
        help="Default HTTP timeout in seconds for Studio requests",
    )
    config_set.set_defaults(func=_cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
