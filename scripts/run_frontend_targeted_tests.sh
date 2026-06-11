#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

declare -a related_files=()

add_related_file() {
  local path="$1"
  local existing

  if [ ! -f "$ROOT_DIR/$path" ]; then
    return
  fi

  for existing in "${related_files[@]:-}"; do
    if [ "$existing" = "$path" ]; then
      return
    fi
  done

  related_files+=("$path")
}

for path in "$@"; do
  case "$path" in
  frontend/src/*)
    add_related_file "$path"
    ;;
  esac
done

if [ "${#related_files[@]}" -eq 0 ]; then
  printf 'No frontend files eligible for targeted tests; skipping.\n'
  exit 0
fi

printf 'Running frontend targeted tests for related files:\n'
printf '  %s\n' "${related_files[@]}"

declare -a frontend_relative_files=()
for path in "${related_files[@]}"; do
  frontend_relative_files+=("${path#frontend/}")
done

cd "$ROOT_DIR/frontend"
npx vitest related --run "${frontend_relative_files[@]}"
