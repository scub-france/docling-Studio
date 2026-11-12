#!/usr/bin/env python3
"""Convert a large PDF in parallel Colab runtimes and merge the Docling JSON."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError

from docling_core.types.doc import DoclingDocument
from pypdf import PdfReader, PdfWriter

SCRIPT = Path(__file__).with_name("docling-cloud.py")
spec = importlib.util.spec_from_file_location("docling_cloud", SCRIPT)
assert spec and spec.loader
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)


def split_pdf(pdf: Path, output_dir: Path, workers: int) -> list[tuple[int, int, Path]]:
    reader = PdfReader(str(pdf))
    page_count = len(reader.pages)
    pages_per_part = (page_count + workers - 1) // workers
    parts = []
    for index, start_index in enumerate(range(0, page_count, pages_per_part), 1):
        end_index = min(start_index + pages_per_part, page_count)
        part_dir = output_dir / f"part-{index:02d}"
        part_dir.mkdir()
        part_pdf = part_dir / f"part-{index:02d}.pdf"
        writer = PdfWriter()
        for page_index in range(start_index, end_index):
            writer.add_page(reader.pages[page_index])
        with part_pdf.open("wb") as stream:
            writer.write(stream)
        parts.append((start_index + 1, end_index, part_pdf))
    return parts


def convert_part(
    part: tuple[int, int, Path], gpu: str, auth: str, batch_pages: int
) -> tuple[int, int, Path]:
    start, end, part_pdf = part
    result_path = part_pdf.with_suffix(".docling.json")
    cloud.convert_with_colab(part_pdf, result_path, gpu, auth, batch_pages)
    document = DoclingDocument.model_validate_json(result_path.read_text())
    if len(document.pages) != end - start + 1:
        raise RuntimeError(f"Part {start}-{end} has {len(document.pages)} pages")
    print(f"Finished source pages {start}-{end}", flush=True)
    return start, end, result_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-pages", type=int, default=25)
    parser.add_argument("--gpu", default="T4")
    parser.add_argument("--colab-auth", default="oauth2")
    parser.add_argument(
        "--studio-url", help="Studio base URL, for example http://localhost:3000"
    )
    parser.add_argument("--output-dir", type=Path, default=Path.home() / "Downloads")
    args = parser.parse_args()
    if args.workers < 1 or args.batch_pages < 1:
        parser.error("--workers and --batch-pages must be positive")
    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        parser.error("pdf must be an existing PDF")
    output_dir = (
        args.output_dir.expanduser().resolve()
        / f"{pdf.stem}-parallel-{uuid.uuid4().hex[:8]}"
    )
    output_dir.mkdir(parents=True)
    saved_pdf = output_dir / pdf.name
    shutil.copy2(pdf, saved_pdf)
    parts = split_pdf(pdf, output_dir, args.workers)
    print(
        "Parallel page ranges: "
        + ", ".join(f"{start}-{end}" for start, end, _ in parts),
        flush=True,
    )

    results = {}
    failed_parts = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                convert_part, part, args.gpu, args.colab_auth, args.batch_pages
            ): part
            for part in parts
        }
        for future in as_completed(futures):
            start, end, _ = futures[future]
            try:
                _, _, result_path = future.result()
                results[start] = result_path
            except Exception as exc:  # noqa: BLE001 - each worker must finish cleanup
                failed_parts.append((futures[future], exc))
                print(f"Part {start}-{end} failed: {exc}", file=sys.stderr, flush=True)
    for part, error in failed_parts:
        start, end, _ = part
        if "Precondition Failed" not in str(error):
            print(f"Completed parts remain in {output_dir}", file=sys.stderr)
            return 1
        print(f"Retrying pages {start}-{end} after a runtime slot opened", flush=True)
        try:
            _, _, result_path = convert_part(
                part, args.gpu, args.colab_auth, args.batch_pages
            )
        except Exception as exc:  # noqa: BLE001 - provider exceptions vary
            print(
                f"Retry failed: {exc}\nCompleted parts remain in {output_dir}",
                file=sys.stderr,
            )
            return 1
        results[start] = result_path

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
    merged_dict = merged.export_to_dict()
    result_path = output_dir / f"{pdf.stem}.docling.json"
    result_path.write_text(json.dumps(merged_dict), encoding="utf-8")
    print(f"Saved {expected_pages}-page Docling JSON to {result_path}")
    if args.studio_url:
        try:
            doc_id, analysis_id = cloud.import_into_studio(
                args.studio_url, saved_pdf, merged_dict
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
