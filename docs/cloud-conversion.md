# Convert a PDF with Colab

`scripts/docling-cloud.py` runs Docling on a temporary Google Colab runtime and
saves the PDF and its Docling JSON together in a new folder. You can optionally
send both to a running Docling Studio instance. The command runs on your own
machine; Google authentication stays in the official Colab CLI package and is
never passed to Studio. It calls that package's Python classes directly.

Use the [Google Colab CLI package](https://github.com/googlecolab/google-colab-cli)
in the same Python environment as the script. The first run prompts for Google
OAuth login if needed. To check your compute-unit balance first:

```bash
uvx --from google-colab-cli==0.7.5 colab --auth=oauth2 usage
```

Convert a PDF using a CPU runtime:

```bash
uv run --with google-colab-cli==0.7.5 python scripts/docling-cloud.py /path/to/document.pdf
```

Request a GPU and import into Studio if it is reachable:

```bash
uv run --with google-colab-cli==0.7.5 python scripts/docling-cloud.py /path/to/document.pdf \
  --gpu T4 --studio-url http://localhost:3000
```

For a large PDF, process smaller page ranges to limit peak memory use. This
requires `pypdf` and `docling-core` in the local Python environment:

```bash
uv run --with google-colab-cli==0.7.5 --with pypdf --with docling-core \
  python scripts/docling-cloud.py /path/to/large-document.pdf \
  --gpu T4 --batch-pages 25
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
`--import-json`:

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
