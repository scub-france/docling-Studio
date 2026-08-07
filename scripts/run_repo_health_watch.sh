#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${1:-300}"

while true; do
  bash "$ROOT_DIR/scripts/write_repo_health_report.sh"
  sleep "$INTERVAL_SECONDS"
done
