# Convert a PDF with Colab (`docling-studio` CLI)

The installable `docling-studio` CLI (in [`cli/`](https://github.com/scub-france/docling-Studio/tree/main/cli))
converts PDFs on a temporary Google Colab runtime (or local Docling) and saves
the PDF and its Docling JSON together in a new folder. You can optionally
upload both directly to a running Docling Studio instance. The command runs on
your own machine; Google authentication stays in the official Colab CLI package
and is never passed to Studio.

## Install the CLI

Install with `uv` (or `pipx`):

```bash
# From a local checkout:
uv tool install ./cli

# Or directly from GitHub:
uv tool install "git+https://github.com/scub-france/docling-Studio.git#subdirectory=cli"
```

The first Colab run prompts for Google OAuth login if needed. To check your
compute-unit balance first:

```bash
uvx --from google-colab-cli==0.7.5 colab --auth=oauth2 usage
```

## Configure Default Settings (`pydantic-settings`)

The CLI uses `pydantic-settings` (`CliSettings`) so you can persist your default
Studio URL, provider, GPU, parallel worker count, and page batch size once
instead of passing flags on every command:

```bash
# Save defaults to ~/.config/docling-studio/settings.json:
docling-studio config set \
  --studio-url http://localhost:3000 \
  --gpu T4 \
  --workers 3 \
  --batch-pages 25

# Inspect effective settings (merged from CLI, DOCLING_STUDIO_* env vars, .env, and settings.json):
docling-studio config show

# Convert or import using saved defaults:
docling-studio convert /path/to/document.pdf
docling-studio import /path/to/document.pdf
```

## Convert and Upload to Docling Studio

Convert a PDF using a Colab GPU and upload directly to Studio:

```bash
docling-studio convert /path/to/document.pdf \
  --provider colab --gpu T4 --studio-url http://localhost:3000
```

For a large PDF, process smaller page ranges (`--batch-pages`) and/or split the
book across multiple concurrent Colab runtimes (`--workers`):

```bash
docling-studio convert /path/to/large-document.pdf \
  --provider colab --workers 4 --gpu T4 --batch-pages 25 \
  --studio-url http://localhost:3000
```

To upload an already-converted PDF and Docling JSON pair into a Studio instance
without running compute again:

```bash
docling-studio import /path/to/document.pdf \
  --json /path/to/document.docling.json \
  --studio-url http://localhost:3000
```

## Standalone Scripts (`scripts/`)

You can also run the standalone scripts directly via `uv run` without installing
the CLI globally:

```bash
uv run --with google-colab-cli==0.7.5 --with pypdf --with docling-core \
  python scripts/docling-cloud.py /path/to/large-document.pdf \
  --gpu T4 --batch-pages 25 --studio-url http://localhost:3000
```

The command saves each completed range under `parts/` as it runs, then
concatenates them into one Docling JSON with consecutive page numbers. If a
runtime fails, the completed parts remain available for inspection.

To split one PDF across four Colab runtimes and process the parts concurrently:

```bash
uv run --with google-colab-cli==0.7.5 --with pypdf --with docling-core \
  python scripts/docling-cloud-parallel.py /path/to/large-document.pdf \
  --workers 4 --gpu T4 --batch-pages 25 --studio-url http://localhost:3000
```

The parallel command divides the pages into four nearly equal PDFs, saves each
part's PDF and JSON, and merges the JSON files when every part succeeds. The
number of active Colab runtimes, and therefore the hourly compute-unit rate,
can increase with `--workers`.

The command saves both files under `~/Downloads/<document>-<run-id>/` by
default. Use `--output-dir` to choose another parent directory. If Studio is
unreachable, the files remain there for import through Studio's UI or with
`docling-studio import` / `--import-json`:

```bash
python3 scripts/docling-cloud.py /path/to/document.pdf \
  --import-json /path/to/document.docling.json --studio-url http://localhost:3000
```

An HTTP error from Studio is reported as a failed import so that a rejected
document is not mistaken for a connection failure (if Studio requires an older
Docling schema version label, the import automatically retries with the
expected version label without altering the saved file). The Colab runtime is
stopped after the download, including after a conversion error.

The command uses the Colab package's OAuth login by default. If you already use
Google Application Default Credentials, pass `--colab-auth adc` instead and
check that account with `uvx --from google-colab-cli==0.7.5 colab --auth=adc usage`.
Version `0.7.5` is pinned because the Python classes are currently implementation
details of the CLI package, not a separately documented SDK.

Each run installs Docling into a fresh runtime and downloads its models as
needed. This makes the first conversion relatively slow. The default Docling
device is set to CPU for CPU runtimes and CUDA for GPU runtimes. Colab compute
availability and charges depend on your account and runtime choice; use
`colab usage` before and after a run to observe consumption. PDFs are sent to
Google's runtime for processing.
Use Colab through your own account for your own processing, and check that you
have the right to send each PDF to Google. The [Colab terms](https://research.google.com/colaboratory/tos_v6.html)
prohibit providing other people direct or indirect access to Colab through you.

The conversion function is separate from the Studio import function in the
script. A future provider can produce the same Docling JSON and use the same
local save and Studio import path.
