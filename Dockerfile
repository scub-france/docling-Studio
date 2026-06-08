# syntax=docker/dockerfile:1
# =============================================================================
# Docling Studio — single-image build (frontend + backend, multi-target)
#
# Usage:
#   docker build --target remote -t docling-studio:remote .
#   docker build --target local  -t docling-studio:local  .
# =============================================================================

# --- Stage 1: Build frontend assets ---
FROM node:20-alpine AS frontend-build

ARG APP_VERSION=dev

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN VITE_APP_VERSION=${APP_VERSION} npm run build

# --- Stage 2: Base runtime (Python + Nginx) ---
FROM python:3.12-slim AS base

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# System deps: poppler (pdf2image), nginx, gettext-base (envsubst for nginx template)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    nginx \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.6

# Python deps (common)
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/usr/local
COPY document-parser/pyproject.toml document-parser/uv.lock ./
RUN uv sync --frozen --no-dev

# Backend code
COPY document-parser/ .

# Frontend static files
COPY --from=frontend-build /build/dist /usr/share/nginx/html

# Nginx config (template stored outside sites-enabled to avoid nginx loading it raw)
COPY nginx.conf.template /etc/nginx/default.template

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Data directories
RUN mkdir -p /app/uploads /app/data && chown -R appuser:appuser /app

ENV UPLOAD_DIR=/app/uploads
ENV DB_PATH=/app/data/docling_studio.db
ENV NGINX_MAX_BODY_SIZE=200M

EXPOSE 3000

CMD ["sh", "-c", "envsubst '${NGINX_MAX_BODY_SIZE}' < /etc/nginx/default.template > /etc/nginx/sites-enabled/default && nginx && exec su appuser -c 'uvicorn main:app --host 127.0.0.1 --port 8000'"]

# --- Remote: lightweight, delegates to Docling Serve ---
FROM base AS remote
ENV CONVERSION_ENGINE=remote

# --- Local: full Docling in-process ---
FROM base AS local

# Pre-fetch the Docling model checkpoints into the image so the very
# first /api/convert is instant (no inline HuggingFace download with
# the user staring at a spinner). Costs ~+1.3 GB on the image AND
# requires HuggingFace Hub connectivity at build time — on shared CI
# runner IP pools this hits anonymous 429 rate limits.
#
# Default is `false` so no build ever depends on HuggingFace Hub by
# accident. `release.yml` flips this to `true` only when publishing
# the `latest-local` end-user image (single sanctioned HF touch point
# for the project — see docs/architecture/huggingface-dependency-map.md).
# When false, docling downloads on first /api/convert; mount
# /home/appuser/.cache/docling as a volume to persist between restarts.
ARG BAKE_MODELS=false
# Opt in to the R&D reasoning stack (docling-agent + mellea + their
# transitive LLM SDK weight). Off by default — `/api/reasoning` 503s
# gracefully when the deps aren't present (see infra/docling_agent_reasoning.py).
ARG WITH_REASONING=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# torch + torchvision come from the PyTorch CPU index via the
# [tool.uv.sources] section of document-parser/pyproject.toml — no
# separate --index-url step. `uv sync --group local` resolves them
# straight to the +cpu builds locked in uv.lock. The reasoning group
# is only pulled in when WITH_REASONING=true.
RUN if [ "$WITH_REASONING" = "true" ]; then \
        uv sync --frozen --no-dev --group local --group reasoning; \
    else \
        uv sync --frozen --no-dev --group local; \
    fi

RUN if [ "$BAKE_MODELS" = "true" ]; then \
        mkdir -p /home/appuser/.cache/docling \
        && docling-tools models download \
             --output-dir /home/appuser/.cache/docling/models --quiet \
        && chown -R appuser:appuser /home/appuser/.cache; \
    fi

RUN chown -R appuser:appuser /app \
    && chown -R appuser:appuser /usr/local/lib/python3.12/site-packages/rapidocr/models
ENV CONVERSION_ENGINE=local
