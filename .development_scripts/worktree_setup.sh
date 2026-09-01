#!/usr/bin/env bash
set -euo pipefail

# Generic worktree setup. Integrations can provide paths through environment
# variables or command-line options rather than depending on one workspace tool.
usage() {
  cat <<'EOF'
Usage: worktree_setup.sh [options]

Prepare dependencies and copy local state into a worktree.

Options:
  -s PATH  Source checkout containing optional .env and SQLite state
  -w PATH  Worktree destination (defaults to the current directory)
  -h       Show this help

Environment:
  SOURCE_CHECKOUT_PATH  Default source checkout path
  WORKTREE_PATH         Default worktree destination
EOF
}

while getopts ":s:w:h" option; do
  case "$option" in
    s) SOURCE_CHECKOUT_PATH="$OPTARG" ;;
    w) WORKTREE_PATH="$OPTARG" ;;
    h)
      usage
      exit 0
      ;;
    :)
      printf 'Error: option -%s requires an argument.\n' "$OPTARG" >&2
      usage >&2
      exit 2
      ;;
    \?)
      printf 'Error: invalid option -%s.\n' "$OPTARG" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SOURCE_CHECKOUT_PATH="${SOURCE_CHECKOUT_PATH:?SOURCE_CHECKOUT_PATH is required (use -s PATH)}"
WORKTREE_PATH="${WORKTREE_PATH:-$PWD}"

mkdir -p "$WORKTREE_PATH/document-parser/data" "$WORKTREE_PATH/document-parser/uploads"

if [[ -f "$SOURCE_CHECKOUT_PATH/document-parser/data/docling_studio.db" ]]; then
  cp "$SOURCE_CHECKOUT_PATH/document-parser/data/docling_studio.db" \
    "$WORKTREE_PATH/document-parser/data/docling_studio.db"
fi

if [[ -f "$SOURCE_CHECKOUT_PATH/.env" ]]; then
  cp "$SOURCE_CHECKOUT_PATH/.env" "$WORKTREE_PATH/.env"
fi

uv sync --directory "$WORKTREE_PATH/document-parser" --group dev
npm ci --prefix "$WORKTREE_PATH/frontend"
