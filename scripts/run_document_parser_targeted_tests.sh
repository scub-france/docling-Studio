#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$ROOT_DIR/document-parser/tests"

declare -a selected_tests=()

add_test() {
  local test_path="$1"
  local existing
  for existing in "${selected_tests[@]:-}"; do
    if [ "$existing" = "$test_path" ]; then
      return
    fi
  done

  if [ -f "$ROOT_DIR/document-parser/$test_path" ]; then
    selected_tests+=("$test_path")
  fi
}

collect_source_candidates() {
  local relative_path="$1"
  local filename stem parent singular_stem

  filename="$(basename "$relative_path")"
  stem="${filename%.py}"
  parent="$(basename "$(dirname "$relative_path")")"
  singular_stem="${stem%s}"

  add_test "tests/test_${stem}.py"
  add_test "tests/test_${parent}_${stem}.py"
  add_test "tests/test_${stem}_${parent}.py"

  if [ "$singular_stem" != "$stem" ]; then
    add_test "tests/test_${singular_stem}.py"
    add_test "tests/test_${parent}_${singular_stem}.py"
    add_test "tests/test_${singular_stem}_${parent}.py"
  fi

  if [ "$relative_path" = "main.py" ]; then
    add_test "tests/test_api_endpoints.py"
    add_test "tests/test_lifecycle.py"
    add_test "tests/test_lifecycle_aggregation.py"
    add_test "tests/test_settings.py"
  fi
}

for path in "$@"; do
  case "$path" in
  document-parser/tests/*.py)
    add_test "${path#document-parser/}"
    ;;
  document-parser/*.py | document-parser/api/*.py | document-parser/domain/*.py | document-parser/infra/*.py | document-parser/persistence/*.py | document-parser/services/*.py)
    collect_source_candidates "${path#document-parser/}"
    ;;
  esac
done

if [ "${#selected_tests[@]}" -eq 0 ]; then
  printf 'No targeted document-parser tests matched the changed files; skipping.\n'
  exit 0
fi

printf 'Running document-parser targeted tests:\n'
printf '  %s\n' "${selected_tests[@]}"

cd "$ROOT_DIR/document-parser"
uv run pytest -q "${selected_tests[@]}"
