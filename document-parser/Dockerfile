# syntax=docker/dockerfile:1
# =============================================================================
# Docling Studio — backend image (multi-target: remote / local)
#
# Usage:
#   docker build --target remote -t docling-studio-backend:remote .
#   docker build --target local  -t docling-studio-backend:local  .
# =============================================================================

# --- Base: common deps for both targets ---
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.6

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/uploads /app/data \
    && chown -R appuser:appuser /app

EXPOSE 8000

ENV UPLOAD_DIR=/app/uploads
ENV DB_PATH=/app/data/docling_studio.db

USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Remote: lightweight, delegates to Docling Serve ---
FROM base AS remote
ENV CONVERSION_ENGINE=remote

# --- Local: full Docling in-process ---
FROM base AS local

# Pre-fetch the Docling model checkpoints into the image so the very
# first /api/convert is instant (no inline HuggingFace download with
# the user staring at a spinner). Costs ~+1.3 GB on the image.
# Opt out with `--build-arg BAKE_MODELS=false` to ship the slim variant;
# in that mode docling downloads on first call and you'll want to
# mount /home/appuser/.cache/docling as a volume to persist them.
ARG BAKE_MODELS=true

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# torch + torchvision come from the PyTorch CPU index via the
# [tool.uv.sources] section of pyproject.toml — no need for a separate
# --index-url install step. `uv sync --group local` resolves them
# straight to the +cpu builds locked in uv.lock.
RUN uv sync --frozen --no-dev --group local

RUN if [ "$BAKE_MODELS" = "true" ]; then \
        mkdir -p /home/appuser/.cache/docling \
        && docling-tools models download \
             --output-dir /home/appuser/.cache/docling/models --quiet \
        && chown -R appuser:appuser /home/appuser/.cache; \
    fi

RUN chown -R appuser:appuser /app \
    && chown -R appuser:appuser /usr/local/lib/python3.12/site-packages/rapidocr/models
USER appuser
ENV CONVERSION_ENGINE=local
