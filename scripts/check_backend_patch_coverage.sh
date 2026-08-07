#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_BRANCH="${1:-${GITHUB_BASE_REF:-origin/main}}"
THRESHOLD="${PATCH_COVERAGE_THRESHOLD:-80}"

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$command_name" >&2
    exit 1
  fi
}

printf '==> Verifying required tools\n'
require_command uv
require_command git

cd "$ROOT_DIR/document-parser"

printf '==> Running backend tests with coverage\n'
uv run pytest tests/ -q --cov --cov-report=xml --cov-report=term

printf '==> Enforcing patch coverage against %s (threshold: %s%%)\n' "$BASE_BRANCH" "$THRESHOLD"
uv run diff-cover coverage.xml --compare-branch="$BASE_BRANCH" --fail-under="$THRESHOLD"
