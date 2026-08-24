#!/usr/bin/env bash
set -euo pipefail

# Generic worktree setup. Integrations should provide the source checkout and
# destination paths rather than making this script depend on one workspace tool.
SOURCE_CHECKOUT_PATH="${SOURCE_CHECKOUT_PATH:?SOURCE_CHECKOUT_PATH is required}"
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
