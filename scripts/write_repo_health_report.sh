#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/.repo-health"
REPORT_PATH="$REPORT_DIR/report.json"
STATE_PATH="$REPORT_DIR/state.txt"
TMP_DIR="$REPORT_DIR/tmp"
FORCE_REFRESH="${REPO_HEALTH_FORCE:-0}"

mkdir -p "$REPORT_DIR" "$TMP_DIR"

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$command_name" >&2
    exit 1
  fi
}

sha256_text() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | awk '{print $1}'
    return
  fi

  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
    return
  fi

  printf 'Missing required command: sha256sum or shasum\n' >&2
  exit 1
}

require_command git
require_command jq

cd "$ROOT_DIR"

branch="$(git branch --show-current 2>/dev/null || true)"
head_sha="$(git rev-parse HEAD)"
status_porcelain="$(git status --short --untracked-files=all)"
status_hash="$(printf '%s' "$status_porcelain" | sha256_text)"
fingerprint="$head_sha:$status_hash"

if [ "$FORCE_REFRESH" != "1" ] && [ -f "$STATE_PATH" ] && [ "$(<"$STATE_PATH")" = "$fingerprint" ]; then
  exit 0
fi

changed_files_json="$({
  if [ -n "$status_porcelain" ]; then
    printf '%s\n' "$status_porcelain"
  fi
} | jq -R -s 'split("\n") | map(select(length > 0)) | map(if length > 3 then .[3:] else . end)')"
printf '%s\n' "$changed_files_json" >"$TMP_DIR/changed-files.json"

run_check() {
  local check_id="$1"
  local workdir="$2"
  shift 2
  local command_display="$*"
  local stdout_path="$TMP_DIR/${check_id}.stdout"
  local stderr_path="$TMP_DIR/${check_id}.stderr"
  local exit_code=0
  local started_at ended_at duration_ms

  started_at="$(date +%s)"
  if (cd "$workdir" && "$@" >"$stdout_path" 2>"$stderr_path"); then
    exit_code=0
  else
    exit_code=$?
  fi
  ended_at="$(date +%s)"
  duration_ms="$(((ended_at - started_at) * 1000))"

  jq -n \
    --arg id "$check_id" \
    --arg status "$([ "$exit_code" -eq 0 ] && printf 'passed' || printf 'failed')" \
    --arg stdout "$(<"$stdout_path")" \
    --arg stderr "$(<"$stderr_path")" \
    --arg command "$command_display" \
    --arg workingDirectory "$workdir" \
    --argjson exitCode "$exit_code" \
    --argjson durationMs "$duration_ms" \
    '{
      id: $id,
      status: $status,
      exitCode: $exitCode,
      durationMs: $durationMs,
      command: $command,
      workingDirectory: $workingDirectory,
      stdout: $stdout,
      stderr: $stderr
    }' >"$TMP_DIR/${check_id}.json"

  return 0
}

run_check backend_lint "$ROOT_DIR/document-parser" uv run ruff check main.py conftest.py api domain infra persistence services tests
run_check backend_tests "$ROOT_DIR/document-parser" uv run pytest tests/ -q
run_check frontend_lint "$ROOT_DIR/frontend" npm run lint
run_check frontend_typecheck "$ROOT_DIR/frontend" npm run type-check
run_check frontend_tests "$ROOT_DIR/frontend" npm run test:run

jq -n \
  --arg generatedAt "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  --arg branch "$branch" \
  --arg head "$head_sha" \
  --arg fingerprint "$fingerprint" \
  --slurpfile changedFiles "$TMP_DIR/changed-files.json" \
  --slurpfile backendLint "$TMP_DIR/backend_lint.json" \
  --slurpfile backendTests "$TMP_DIR/backend_tests.json" \
  --slurpfile frontendLint "$TMP_DIR/frontend_lint.json" \
  --slurpfile frontendTypecheck "$TMP_DIR/frontend_typecheck.json" \
  --slurpfile frontendTests "$TMP_DIR/frontend_tests.json" \
  '
    [
      $backendLint[0],
      $backendTests[0],
      $frontendLint[0],
      $frontendTypecheck[0],
      $frontendTests[0]
    ] as $checks
    | {
        generatedAt: $generatedAt,
        branch: $branch,
        head: $head,
        fingerprint: $fingerprint,
        repoDirty: (($changedFiles[0] | length) > 0),
        changedFiles: $changedFiles[0],
        totalDurationMs: ($checks | map(.durationMs) | add),
        status: (if all($checks[]; .status == "passed") then "passed" else "failed" end),
        checks: $checks
      }
  ' >"$REPORT_PATH"

printf '%s' "$fingerprint" >"$STATE_PATH"
