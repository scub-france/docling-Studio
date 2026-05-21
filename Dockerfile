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

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN uv pip install --python /usr/local/bin/python --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && uv sync --frozen --no-dev --group local

RUN chown -R appuser:appuser /app \
    && chown -R appuser:appuser /usr/local/lib/python3.12/site-packages/rapidocr/models
ENV CONVERSION_ENGINE=local
