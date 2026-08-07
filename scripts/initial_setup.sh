#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$command_name" >&2
    exit 1
  fi
}

printf '==> Verifying required tools\n'
require_command uv
require_command npm
require_command git

cd "$ROOT_DIR"

printf '==> Installing frontend dependencies\n'
npm --prefix "$ROOT_DIR/frontend" install

printf '==> Syncing document-parser dev environment\n'
uv sync --directory "$ROOT_DIR/document-parser" --group dev

printf '==> Syncing embedding-service dev environment\n'
uv sync --directory "$ROOT_DIR/embedding-service" --group dev

printf '==> Ensuring pre-commit is installed\n'
uv tool install pre-commit

printf '==> Installing git hooks\n'
pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push --hook-type commit-msg

printf '\nInitial setup complete.\n'
printf 'Run the frontend with: npm --prefix %s/frontend run dev\n' "$ROOT_DIR"
printf 'Run the backend with: uv run --directory %s/document-parser uvicorn main:app --reload --port 8000\n' "$ROOT_DIR"
