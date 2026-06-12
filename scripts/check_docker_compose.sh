#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
docker compose -f docker-compose.dev.yml config -q
docker compose --profile ingestion -f docker-compose.yml -f docker-compose.ingestion.yml config -q
