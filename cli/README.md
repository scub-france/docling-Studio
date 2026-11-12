# `docling-studio-cli`

Installable CLI to convert PDFs with pluggable compute providers (**Google Colab**, **Remote Docling Serve HTTP**, or **Local Docling**), save the PDF and validated Docling JSON locally, and directly upload them into a running Docling Studio instance.

## Architecture: Provider-Agnostic Pipeline + Isolated Providers

- **Orchestration Pipeline (`pipeline.py`)**: Handles PDF page-count inspection, splitting large books across `--workers N` parallel worker sessions (`split_pdf`), running `--batch-pages M` chunks within each session, validating each chunk with `DoclingDocument.model_validate_json`, and merging batches/parts via `DoclingDocument.concatenate`.
- **Provider Abstraction (`providers/base.py`)**: A provider only implements `open_session(pdf, settings) -> ContextManager[ProviderSession]`, where a `ProviderSession` exposes a single primitive:
  ```python
  session.convert_range(page_range: tuple[int, int] | None, output_path: Path) -> None
  ```
  Every provider automatically inherits single-pass conversion, `--batch-pages` chunking, and `--workers` parallel execution without duplicating PDF splitting or merging logic.
- **Built-in Providers (`providers/`)**:
  - `colab` (`providers/colab.py`, settings: `ColabProviderSettings`): Ephemeral Google Colab CPU/GPU runtimes via `google-colab-cli`.
  - `docling-serve` (`providers/docling_serve.py`, settings: `DoclingServeProviderSettings`): Remote `docling-serve` HTTP API (`/v1/convert/file`).
  - `local` (`providers/local.py`, settings: `LocalProviderSettings`): Local `docling` installation on the user's machine.

## Installation

Install directly from this repository with `uv` or `pipx`:

```bash
# From a local checkout:
uv tool install ./cli

# Or directly from GitHub:
uv tool install "git+https://github.com/scub-france/docling-Studio.git#subdirectory=cli"

# Include local Docling dependencies if you also want `--provider local`:
uv tool install "./cli[local]"
```

## Guided Provider Setup & Verification (`docling-studio configure` / `verify`)

Run the interactive setup wizard to choose a provider, configure its provider-specific settings, set pipeline defaults, save to `~/.config/docling-studio/settings.json`, and immediately verify authentication/connectivity:

```bash
# Interactive wizard (prompts for provider, provider settings, workers, batch size, and Studio URL):
docling-studio configure

# Or configure a specific provider directly:
docling-studio configure colab
docling-studio configure docling-serve
docling-studio configure local

# Non-interactive setup + verification:
docling-studio configure colab \
  --no-input \
  --colab-gpu T4 \
  --workers 3 \
  --batch-pages 25 \
  --studio-url https://your-studio.example.com

# Verify provider credentials/balance and Studio reachability at any time:
docling-studio verify
docling-studio verify colab
```

When verifying `colab`, the CLI authenticates via `google-colab-cli` (opening the OAuth browser login if needed) and reports your remaining Colab compute units and active runtime count:
```text
[OK] Provider 'colab': Authenticated with Google Colab (oauth2, default accelerator=T4, balance=1344.0 compute units, active_runtimes=0)
[OK] Docling Studio: Reachable Docling Studio at https://your-studio.example.com (version=0.8.0)
```

## Persistent Defaults & Nested Provider Settings (`pydantic-settings`)

`CliSettings` separates provider-agnostic pipeline settings (`studio_url`, `provider`, `workers`, `batch_pages`, `output_dir`) from nested provider-specific settings (`colab`, `local`, `docling_serve`) using `env_nested_delimiter="__"`:

1. Explicit CLI flags (`--studio-url`, `--provider`, `--workers`, `--batch-pages`, `--colab-gpu`, `--docling-serve-url`, `--local-device`, etc.)
2. Environment variables:
   - Pipeline: `DOCLING_STUDIO_STUDIO_URL` (or `DOCLING_STUDIO_URL`), `DOCLING_STUDIO_PROVIDER`, `DOCLING_STUDIO_WORKERS`, `DOCLING_STUDIO_BATCH_PAGES`, `DOCLING_STUDIO_OUTPUT_DIR`
   - Colab provider: `DOCLING_STUDIO_COLAB__GPU`, `DOCLING_STUDIO_COLAB__AUTH`
   - Docling Serve provider: `DOCLING_STUDIO_DOCLING_SERVE__URL`, `DOCLING_STUDIO_DOCLING_SERVE__API_KEY`
   - Local provider: `DOCLING_STUDIO_LOCAL__DEVICE`
3. Local `.env` file
4. Persistent JSON settings file (`~/.config/docling-studio/settings.json`, or override path with `--config` / `DOCLING_STUDIO_CONFIG`)

```bash
# Inspect effective merged settings:
docling-studio config show

# Now convert or import without repeating flags:
docling-studio convert /path/to/book.pdf
docling-studio import /path/to/book.pdf
```

## Usage Examples

### 1. Google Colab (`--provider colab`)

```bash
# Single T4 runtime with 25-page batches:
docling-studio convert /path/to/book.pdf \
  --provider colab --colab-gpu T4 --batch-pages 25 \
  --studio-url https://your-studio.example.com

# Parallel Colab runtimes (4 concurrent T4 runtimes):
docling-studio convert /path/to/large-book.pdf \
  --provider colab --workers 4 --colab-gpu T4 --batch-pages 25 \
  --studio-url https://your-studio.example.com
```

### 2. Remote Docling Serve (`--provider docling-serve`)

```bash
docling-studio convert /path/to/book.pdf \
  --provider docling-serve \
  --docling-serve-url http://gpu-box:5001 \
  --batch-pages 25 \
  --studio-url https://your-studio.example.com
```

### 3. Local Docling (`--provider local`)

```bash
docling-studio convert /path/to/document.pdf \
  --provider local --local-device mps --batch-pages 25 \
  --studio-url http://localhost:3000
```

### 4. Import an existing PDF + Docling JSON pair into Studio (zero compute)

```bash
docling-studio import /path/to/book.pdf \
  --json /path/to/book.docling.json \
  --studio-url https://your-studio.example.com
```

### 5. List registered providers

```bash
docling-studio providers
```
