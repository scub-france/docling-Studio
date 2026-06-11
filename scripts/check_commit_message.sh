#!/usr/bin/env bash

set -euo pipefail

commit_message_file="$1"
first_line="$(sed -n '1p' "$commit_message_file")"

if [[ "$first_line" =~ ^Merge ]] || [[ "$first_line" =~ ^Revert ]]; then
  exit 0
fi

if [[ "$first_line" =~ ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9._/-]+\))?(!)?:\ .+ ]]; then
  exit 0
fi

printf 'Commit message must follow Conventional Commits.\n' >&2
printf 'Example: chore(dev): add targeted pre-commit hooks\n' >&2
printf 'Got: %s\n' "$first_line" >&2
exit 1
