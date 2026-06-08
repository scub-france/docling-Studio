"""Generate deterministic test PDFs for E2E tests.

Uses fpdf2 to create valid PDFs with real text content so Docling
can extract and chunk them. No binary files committed to the repo.

Usage:
    python e2e/generate-test-data.py

Dependencies:
    pip install fpdf2
"""

from __future__ import annotations

import os

from fpdf import FPDF

OUTPUT_DIRS = [
    os.path.join(os.path.dirname(__file__), "api", "src", "test", "resources", "common", "data", "generated"),
    os.path.join(os.path.dirname(__file__), "ui", "src", "test", "resources", "common", "data", "generated"),
]

_PARAGRAPHS = [
    "Document processing is a critical step in building retrieval-augmented generation systems.",
    "Docling Studio provides tools for analyzing PDF documents and extracting structured content.",
    "The conversion pipeline supports OCR, table detection, and formula enrichment features.",
    "Chunking splits document content into semantically meaningful segments for vector indexing.",
    "Each chunk preserves metadata such as page number, bounding boxes, and heading hierarchy.",
    "The hybrid chunker combines hierarchical document structure with token-based splitting.",
    "Vector stores like OpenSearch enable fast similarity search over embedded chunk vectors.",
    "Quality control requires visual inspection of chunk boundaries and extracted text accuracy.",
    "Batch processing of large documents uses page ranges to prevent memory exhaustion.",
    "Progress reporting allows users to monitor long-running document conversion tasks.",
]


def _make_pdf(page_count: int, path: str) -> None:
    """Create a valid PDF with N pages containing text paragraphs."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)

    for page_num in range(page_count):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Page {page_num + 1} of {page_count}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 11)
        for i in range(5):
            para = _PARAGRAPHS[(page_num * 5 + i) % len(_PARAGRAPHS)]
            pdf.multi_cell(0, 6, para)
            pdf.ln(3)

    pdf.output(path)
    size_kb = os.path.getsize(path) / 1024
    print(f"  {os.path.basename(path)}: {page_count} pages, {size_kb:.1f} KB")


def _make_non_pdf(path: str) -> None:
    """Create a non-PDF file for negative testing."""
    with open(path, "wb") as f:
        f.write(b"This is not a PDF file.\n")
    print(f"  {os.path.basename(path)}: not-a-pdf")


def main() -> None:
    for output_dir in OUTPUT_DIRS:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Generating test data in {output_dir}")

        # `small.pdf` MUST stay at 1 page — `documents/upload.feature::
        # "Upload valid single-page PDF"` asserts `response.pageCount == 1`
        # against this fixture. Tests that hit the docling-serve cpu
        # pipeline must use medium.pdf or larger to dodge the upstream
        # 1-page-PDF / "Task result not found" bug
        # (https://github.com/docling-project/docling-serve/issues/466).
        _make_pdf(1, os.path.join(output_dir, "small.pdf"))
        _make_pdf(5, os.path.join(output_dir, "medium.pdf"))
        _make_pdf(25, os.path.join(output_dir, "large.pdf"))
        _make_non_pdf(os.path.join(output_dir, "not-a-pdf.txt"))

    print("Done.")


if __name__ == "__main__":
    main()
