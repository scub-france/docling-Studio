#!/usr/bin/env bash

set -euo pipefail

blocked_files=()

for path in "$@"; do
  case "$path" in
  .repo-health/* | .coverage | coverage.xml | document-parser/coverage.xml)
    blocked_files+=("$path")
    ;;
  frontend/dist/* | site/* | uploads/* | data/* | profiles/*)
    blocked_files+=("$path")
    ;;
  document-parser/local-experiments/*)
    case "$path" in
    *.py | *.md)
      ;;
    *)
      blocked_files+=("$path")
      ;;
    esac
    ;;
  esac
done

if [ "${#blocked_files[@]}" -eq 0 ]; then
  exit 0
fi

printf 'Refusing to commit local/generated artifacts:\n' >&2
for path in "${blocked_files[@]}"; do
  printf '  - %s\n' "$path" >&2
done
printf 'Move them out of the repo or add them to .gitignore if they are local-only.\n' >&2
exit 1
