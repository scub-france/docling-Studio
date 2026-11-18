"""Provider-agnostic PDF splitting, page-range batching, parallel execution, and Docling JSON merging."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from docling_studio_cli.models import PipelineOptions
    from docling_studio_cli.providers.base import ConversionProvider
    from docling_studio_cli.settings import CliSettings


def split_pdf(pdf: Path, output_dir: Path, workers: int) -> list[tuple[int, int, Path]]:
    """Split `pdf` into `workers` nearly equal part PDFs under `output_dir`."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf))
    page_count = len(reader.pages)
    pages_per_part = (page_count + workers - 1) // workers
    parts: list[tuple[int, int, Path]] = []
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


def run_worker_session(
    pdf: Path,
    result_path: Path,
    provider: ConversionProvider,
    settings: CliSettings,
    batch_pages: int | None = None,
) -> None:
    """Run a single provider session on `pdf`, optionally chunked into `batch_pages` ranges."""
    page_count: int | None = None
    if batch_pages is not None:
        from docling_core.types.doc import DoclingDocument
        from pypdf import PdfReader

        page_count = len(PdfReader(str(pdf)).pages)

    with provider.open_session(pdf, settings) as session:
        if batch_pages is None:
            session.convert_range(None, result_path)
            return

        assert page_count is not None
        from docling_core.types.doc import DoclingDocument

        parts_dir = result_path.parent / "parts"
        parts_dir.mkdir(exist_ok=True)
        documents = []
        for start in range(1, page_count + 1, batch_pages):
            end = min(start + batch_pages - 1, page_count)
            local_part = parts_dir / f"pages-{start:04d}-{end:04d}.docling.json"
            session.convert_range((start, end), local_part)
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


def _convert_parallel_part(
    part: tuple[int, int, Path],
    provider: ConversionProvider,
    settings: CliSettings,
    batch_pages: int | None,
) -> tuple[int, int, Path]:
    from docling_core.types.doc import DoclingDocument

    start, end, part_pdf = part
    part_result = part_pdf.with_suffix(".docling.json")
    run_worker_session(part_pdf, part_result, provider, settings, batch_pages)
    document = DoclingDocument.model_validate_json(part_result.read_text())
    if len(document.pages) != end - start + 1:
        raise RuntimeError(f"Part {start}-{end} has {len(document.pages)} pages")
    print(f"Finished source pages {start}-{end}", flush=True)
    return start, end, part_result


def run_conversion_pipeline(
    pdf: Path,
    result_path: Path,
    provider: ConversionProvider,
    pipeline_options: PipelineOptions,
    settings: CliSettings,
) -> None:
    """Execute single-worker or multi-worker PDF conversion against any `ConversionProvider`."""
    if pipeline_options.workers <= 1:
        run_worker_session(
            pdf,
            result_path,
            provider,
            settings,
            pipeline_options.batch_pages,
        )
        return

    from docling_core.types.doc import DoclingDocument

    output_dir = result_path.parent
    parts = split_pdf(pdf, output_dir, pipeline_options.workers)
    print(
        "Parallel page ranges: " + ", ".join(f"{start}-{end}" for start, end, _ in parts),
        flush=True,
    )
    batch_pages = pipeline_options.batch_pages or 25
    results: dict[int, Path] = {}
    failed_parts: list[tuple[tuple[int, int, Path], Exception]] = []

    with ThreadPoolExecutor(max_workers=pipeline_options.workers) as executor:
        futures = {
            executor.submit(
                _convert_parallel_part,
                part,
                provider,
                settings,
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
        if not provider.is_transient_capacity_error(error):
            raise RuntimeError(
                f"Part {start}-{end} failed: {error}. Completed parts remain in {output_dir}"
            ) from error
        print(
            f"Retrying pages {start}-{end} after a worker slot opened",
            flush=True,
        )
        _, _, part_result = _convert_parallel_part(part, provider, settings, batch_pages)
        results[start] = part_result

    documents = [
        DoclingDocument.model_validate_json(results[start].read_text()) for start in sorted(results)
    ]
    merged = DoclingDocument.concatenate(documents)
    merged.name = pdf.stem
    merged.origin = None
    expected_pages = parts[-1][1]
    if len(merged.pages) != expected_pages:
        raise RuntimeError(f"Merged {len(merged.pages)} of {expected_pages} pages")
    result_path.write_text(json.dumps(merged.export_to_dict()), encoding="utf-8")
