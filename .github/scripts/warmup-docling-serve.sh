#!/usr/bin/env bash
# Warm up the docling-serve container before running E2E tests.
#
# Why this exists
# ---------------
# docling-serve registers its `/v1/convert/*` route decorators at FastAPI
# import time, so they show up in `/openapi.json` immediately. But the
# handler returns HTTP 404 transiently until the lifespan startup has
# finished wiring up the converter pipeline (~60-90s on shared GHA
# runners, sometimes longer). Compose `--wait` + a `/version` (or even
# an empty-POST → 422) healthcheck both report "healthy" well before
# this window closes.
#
# The only way to know the converter is *actually* serving is to send a
# real PDF and check we get a 200. This script does that: copies one
# of the e2e fixture PDFs into the docling-serve container, then loops
# `curl -X POST /v1/convert/file` until success, with a generous
# timeout. The fixture is already generated upstream by
# `e2e/generate-test-data.py`.
#
# Outputs every attempt so a flake in CI gives an actionable timeline.
# On failure, dumps the last 100 lines of docling-serve logs.

set -euo pipefail

SERVICE=docling-serve
# Either of these is fine — the same file is generated under both api/ and ui/.
PDF_CANDIDATES=(
  "e2e/api/src/test/resources/common/data/generated/small.pdf"
  "e2e/ui/src/test/resources/common/data/generated/small.pdf"
)
DEST_IN_CONTAINER=/tmp/warmup.pdf

PDF=""
for candidate in "${PDF_CANDIDATES[@]}"; do
  if [ -f "$candidate" ]; then
    PDF="$candidate"
    break
  fi
done

if [ -z "$PDF" ]; then
  echo "::error::no warm-up PDF fixture found (run 'python e2e/generate-test-data.py' first)"
  exit 1
fi

echo "Warming up $SERVICE with fixture: $PDF"
docker compose --profile remote cp "$PDF" "$SERVICE:$DEST_IN_CONTAINER"

MAX_ATTEMPTS=60
SLEEP_SECONDS=5

for i in $(seq 1 "$MAX_ATTEMPTS"); do
  code=$(docker compose --profile remote exec -T "$SERVICE" sh -c "
    curl -s -o /dev/null -w '%{http_code}' \
      -X POST \
      -F 'files=@$DEST_IN_CONTAINER' \
      -F 'to_formats=md' \
      http://localhost:5001/v1/convert/file
  ")
  echo "Attempt $i/$MAX_ATTEMPTS: $SERVICE responded $code"
  if [ "$code" = "200" ]; then
    echo "✓ $SERVICE fully ready"
    exit 0
  fi
  sleep "$SLEEP_SECONDS"
done

echo "::error::$SERVICE never returned 200 after $MAX_ATTEMPTS attempts ($(($MAX_ATTEMPTS * $SLEEP_SECONDS))s)"
echo "--- $SERVICE logs (last 100 lines) ---"
docker compose --profile remote logs --tail 100 "$SERVICE"
exit 1
