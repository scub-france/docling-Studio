# syntax=docker/dockerfile:1
# =============================================================================
# Docling Studio — backend image (multi-stage, multi-target: remote / local)
#
# Standard usage:
#   docker build --target remote -t docling-studio-backend:remote .
#   docker build --target local  -t docling-studio-backend:local  .
#
# R&D variant — opt in to the reasoning-trace runner (docling-agent + mellea,
# heavy transitive deps; runtime-gated by REASONING_ENABLED):
#   docker build --target local --build-arg WITH_REASONING=true \
#     -t docling-studio-backend:local-reasoning .
#
# Cache notes:
#   - Source is COPYed only in the final stages, never in the builders.
#     A code-only change reuses every pip-install layer.
#   - Each builder owns a venv at /opt/venv that the final stage copies in
#     wholesale (no pip in the runtime image).
# =============================================================================

# --- Builder: remote (lightweight HTTP-only deps) ----------------------------
FROM python:3.12-slim AS builder-remote

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Builder: local (torch CPU + full Docling, optional reasoning deps) ------
FROM python:3.12-slim AS builder-local

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt requirements-local.txt requirements-reasoning.txt ./

# torch CPU wheels in their own layer — pinned to the CPU-only index so the
# transitive resolution of docling does not re-pull a CUDA build.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Full local stack (requirements-local.txt re-includes requirements.txt).
RUN pip install -r requirements-local.txt

# Reasoning is opt-in; off by default keeps the standard image lean.
ARG WITH_REASONING=false
RUN if [ "$WITH_REASONING" = "true" ]; then \
        pip install -r requirements-reasoning.txt; \
    fi

# --- Runtime base (no pip, no source — shared by both final targets) ---------
FROM python:3.12-slim AS runtime-base

RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/uploads /app/data /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /app /home/appuser/.cache

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UPLOAD_DIR=/app/uploads \
    DB_PATH=/app/data/docling_studio.db \
    HF_HOME=/home/appuser/.cache/huggingface

EXPOSE 8000
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Final: remote -----------------------------------------------------------
FROM runtime-base AS remote
COPY --from=builder-remote --chown=appuser:appuser /opt/venv /opt/venv
COPY --chown=appuser:appuser . /app
ENV CONVERSION_ENGINE=remote

# --- Final: local ------------------------------------------------------------
FROM runtime-base AS local

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
USER appuser

COPY --from=builder-local --chown=appuser:appuser /opt/venv /opt/venv

# Pre-fetch Docling model checkpoints into the appuser HF cache so the very
# first conversion does not pay the ~400 MB cold-start download. Opt out
# with --build-arg BAKE_MODELS=false for an even smaller image (will then
# download on first request).
ARG BAKE_MODELS=true
RUN if [ "$BAKE_MODELS" = "true" ]; then \
        docling-tools models download; \
    fi

COPY --chown=appuser:appuser . /app
ENV CONVERSION_ENGINE=local
