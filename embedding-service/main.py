"""Embedding microservice — exposes sentence-transformers models via REST API.

POST /embed  {"texts": ["...", "..."]}  →  {"embeddings": [[...], [...]], "model": "...", "dimension": N}
GET  /health                            →  {"status": "ok", "model": "...", "dimension": N}
"""

from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "64"))

app = FastAPI(title="Docling Studio — Embedding Service", version="0.4.0")

# Load model at startup (downloaded / cached in HF cache dir)
model: SentenceTransformer | None = None


def _embedding_dimension(current_model: SentenceTransformer) -> int:
    dimension = current_model.get_sentence_embedding_dimension()
    if dimension is None:
        raise RuntimeError("Embedding model did not report a dimension")
    return dimension


@app.on_event("startup")
async def _load_model() -> None:
    global model
    logger.info("Loading sentence-transformers model '%s' …", MODEL_NAME)
    t0 = time.monotonic()
    model = SentenceTransformer(MODEL_NAME)
    elapsed = time.monotonic() - t0
    dim = _embedding_dimension(model)
    logger.info("Model loaded in %.1fs — dimension=%d", elapsed, dim)


# -- Schemas -------------------------------------------------------------------


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="Texts to embed")


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str
    dimension: int


class HealthResponse(BaseModel):
    status: str
    model: str
    dimension: int


# -- Endpoints -----------------------------------------------------------------


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest) -> EmbedResponse:
    """Generate embeddings for a batch of texts."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    vectors = model.encode(
        request.texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return EmbedResponse(
        embeddings=vectors.tolist(),
        model=MODEL_NAME,
        dimension=_embedding_dimension(model),
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check — verifies the model is loaded."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    return HealthResponse(
        status="ok",
        model=MODEL_NAME,
        dimension=_embedding_dimension(model),
    )
