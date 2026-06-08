# HuggingFace Hub dependency map

Where the Docling Studio project touches `huggingface.co` and how to keep
those touches contained.

## Why this exists

HuggingFace Hub anonymous downloads share a single rate-limit bucket per
client IP. GitHub Actions shared runners pool IPs across all open-source
projects on the platform, so any build that hits HF Hub anonymously
during a release window will eventually 429 — regardless of how small
the file or how unique your workflow.

The audit `0.6.2 #10` traced two cascading CI failures (Backend tests
and Release Gate E2E API) to model bakes / runtime fetches landing on
those rate-limited paths. Fixing the immediate symptoms wasn't enough:
the root cause is that **the project had no principled stance on which
build paths are allowed to talk to HF Hub**. This document is that
stance.

## Sanctioned HF Hub touch points

There is exactly **one** sanctioned HF Hub touch point in our build /
release toolchain:

| Touch point | When | Why | Owner |
|-------------|------|-----|-------|
| `release.yml` → `latest-local` GHCR image (`BAKE_MODELS=true`) | On `v*` tag push | Publishes a self-contained image so end users get an instant first `/api/convert` from a single `docker pull` | Release pipeline |

That single sanctioned touch is fenced by:

- An explicit `build-args: BAKE_MODELS=true` in `release.yml`, scoped
  by matrix condition to the `local` target only.
- The Dockerfile `ARG BAKE_MODELS=false` default — any other build
  inherits the off state.

Every other build path defaults to `BAKE_MODELS=false` (Docling) and
`BAKE_MODEL=false` (embedding-service). They never call HF Hub
implicitly.

## All HF call sites in the project

### Build-time

| Location | Trigger | Default | Notes |
|----------|---------|---------|-------|
| `Dockerfile:103` (`docling-tools models download`) | `BAKE_MODELS=true` build-arg on `local` target | **false** | Only triggered by `release.yml` matrix `local`. |
| `document-parser/Dockerfile:79` | same | **false** | Duplicate of the top-level Dockerfile path. |
| `embedding-service/Dockerfile:24` (`SentenceTransformer('${EMBEDDING_MODEL}')`) | `BAKE_MODEL=true` build-arg | **false** | No release pipeline currently builds this with bake=true. |

### Runtime (only when the relevant feature is enabled)

| Location | Trigger | Notes |
|----------|---------|-------|
| `infra/local_chunker.py` → `HybridChunker(...)` | First chunking call when `CONVERSION_ENGINE=local` | Tokenizer `sentence-transformers/all-MiniLM-L6-v2`. Cached at `~/.cache/huggingface` inside the container — mount a volume to persist. |
| `infra/local_converter.py` → Docling pipeline | First `/api/convert` when `CONVERSION_ENGINE=local` and `BAKE_MODELS=false` | Layout / OCR / table models. Same cache path. |
| `embedding-service/main.py:33` | Service startup, if model not baked | Cached at `~/.cache/huggingface`. |
| `mellea` / `docling-agent` (reasoning) | First `/api/reasoning` call when `WITH_REASONING=true` was built in **and** `RAG_PIPELINE_ENABLED=true` at runtime | LLM weights (IBM Granite). Reasoning is opt-in twice — at build (`WITH_REASONING`) and at runtime (`RAG_PIPELINE_ENABLED`). HF-free deployments don't enable it. |

### Test-time

| Location | Status |
|----------|--------|
| `tests/test_chunking.py::test_rechunk_with_serve_document_json` | Fixed in `29ab575` — DocumentChunker port is mocked, no HF call. |

## How to deploy HF-free

The remote conversion path has zero HF dependency from our side:

1. Run the official `docling-serve` container (it ships with models
   baked at the source by the docling-project — that's their problem
   to keep on a stable mirror, not ours):

   ```yaml
   # docker-compose.yml — already wired behind the `remote` profile
   docling-serve:
     profiles: ["remote"]
     image: quay.io/docling-project/docling-serve-cpu:v1.21.0
   ```

2. Build the backend with `CONVERSION_MODE=remote`:

   ```bash
   CONVERSION_MODE=remote docker compose --profile remote up -d --build
   ```

3. Skip the embedding service (or run it with a mounted HF cache volume
   if you want vector ingestion):

   ```bash
   docker compose --profile remote up -d --build  # no ingestion → no embedding container
   ```

CI (`ci.yml`, `release-gate.yml`) follows this pattern exactly.

## How to deploy with bake (HF touched at build, never at runtime)

The official end-user path. Pull the published image:

```bash
docker pull ghcr.io/scub-france/docling-studio:latest-local
```

That image was built with `BAKE_MODELS=true` by `release.yml`. The HF
call already happened at release time. Once the image is on your host,
no HF call is needed.

## Maintenance rule

When adding a new component that needs an HF model:

1. Default to `false` on any bake build-arg.
2. If you need a fast-first-call experience for a published end-user
   image, add an explicit override in `release.yml` (do not flip the
   Dockerfile default).
3. Document the new touch point in the table above.

Reviewers: any new build path (Dockerfile RUN, CI step, compose
service) that calls HF Hub without an explicit opt-in build-arg is a
red flag.
