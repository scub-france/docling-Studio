# `docling-studio-cli`

Installable CLI to convert PDFs with Google Colab (single or parallel runtimes) or local Docling, save the PDF and validated Docling JSON locally, and directly upload them into a running Docling Studio instance.

## Installation

Install directly from this repository with `uv` or `pipx`:

```bash
# From a local checkout:
uv tool install ./cli

# Or directly from GitHub:
uv tool install "git+https://github.com/scub-france/docling-Studio.git#subdirectory=cli"
```

Include local Docling support if you also want `--provider local`:

```bash
uv tool install "./cli[local]"
```

## Persistent Defaults & Settings (`pydantic-settings`)

You can configure persistent defaults via `docling-studio config set` (saved to `~/.config/docling-studio/settings.json`), environment variables (`DOCLING_STUDIO_*`), or a `.env` file. Precedence is:

1. Explicit CLI flags (`--studio-url`, `--gpu`, `--workers`, etc.)
2. Environment variables (`DOCLING_STUDIO_STUDIO_URL` / `DOCLING_STUDIO_URL`, `DOCLING_STUDIO_GPU`, `DOCLING_STUDIO_WORKERS`, `DOCLING_STUDIO_BATCH_PAGES`, `DOCLING_STUDIO_PROVIDER`, `DOCLING_STUDIO_COLAB_AUTH`, `DOCLING_STUDIO_OUTPUT_DIR`)
3. Local `.env` file
4. Persistent user settings file (`~/.config/docling-studio/settings.json`, or override path with `--config` / `DOCLING_STUDIO_CONFIG`)

```bash
# Save your preferred defaults once:
docling-studio config set \
  --studio-url https://your-studio.example.com \
  --gpu T4 \
  --workers 3 \
  --batch-pages 25

# Inspect effective merged settings:
docling-studio config show

# Now convert or import without repeating flags:
docling-studio convert /path/to/book.pdf
docling-studio import /path/to/book.pdf
```

## Quick Start

### 1. Convert a PDF on Google Colab and upload to Docling Studio

```bash
docling-studio convert /path/to/book.pdf \
  --provider colab \
  --gpu T4 \
  --batch-pages 25 \
  --studio-url https://your-studio.example.com
```

### 2. Split a large book across parallel Colab GPU runtimes

```bash
docling-studio convert /path/to/large-book.pdf \
  --provider colab \
  --workers 4 \
  --gpu T4 \
  --batch-pages 25 \
  --studio-url https://your-studio.example.com
```

### 3. Convert locally

```bash
docling-studio convert /path/to/document.pdf \
  --provider local \
  --batch-pages 25 \
  --studio-url http://localhost:3000
```

### 4. Import an existing PDF + Docling JSON pair into Studio (no compute used)

```bash
docling-studio import /path/to/book.pdf \
  --json /path/to/book.docling.json \
  --studio-url https://your-studio.example.com
```

If `--json` is omitted, `docling-studio import` looks for `<pdf-stem>.docling.json` next to the PDF.

### 5. List registered providers

```bash
docling-studio providers
```
