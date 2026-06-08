FROM python:3.12-slim

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.6

# Install dependencies first (cache layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Optionally pre-download the default sentence-transformers model into
# the image. Default is `false` so no build ever depends on HuggingFace
# Hub by accident — on shared CI runner IP pools (and parallel builds
# of the docling-studio backend) this is exactly what produced the
# anonymous 429 rate-limit cascade traced in audit 0.6.2 #10.
#
# When false, the model is downloaded on first /embed call and lives
# under ~/.cache/huggingface inside the container — mount that path
# as a volume to persist across image rebuilds.
#
# When true, sentence-transformers fetches the model at build time
# (~90 MB for all-MiniLM-L6-v2). Reserve this for release-publishing
# pipelines that want a self-contained image (none today; this opt-in
# exists so operators publishing their own embedding image can keep
# the historical bake-at-build behaviour).
ARG EMBEDDING_MODEL=all-MiniLM-L6-v2
ARG BAKE_MODEL=false
RUN if [ "$BAKE_MODEL" = "true" ]; then \
        python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"; \
    fi

COPY main.py .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
