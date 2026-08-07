#!/usr/bin/env bash

set -euo pipefail

require_pair() {
  local manifest="$1"
  local lockfile="$2"
  shift 2

  local manifest_changed=0
  local lockfile_changed=0
  local path

  for path in "$@"; do
    if [ "$path" = "$manifest" ]; then
      manifest_changed=1
    fi
    if [ "$path" = "$lockfile" ]; then
      lockfile_changed=1
    fi
  done

  if [ "$manifest_changed" -eq 1 ] && [ "$lockfile_changed" -eq 0 ]; then
    printf 'Lockfile mismatch: %s changed without %s\n' "$manifest" "$lockfile" >&2
    exit 1
  fi
}

require_pair frontend/package.json frontend/package-lock.json "$@"
require_pair document-parser/pyproject.toml document-parser/uv.lock "$@"
require_pair embedding-service/pyproject.toml embedding-service/uv.lock "$@"
