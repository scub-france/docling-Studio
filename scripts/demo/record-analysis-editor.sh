#!/usr/bin/env bash
# Record the analysis-editor Karate UI suite to an MP4 screen capture.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${VIDEO_OUT:-$ROOT/out/demo/analysis-editor.mp4}"
SCREEN="${SCREEN:-2}"
FPS="${FPS:-30}"
CROP="${CROP:-}"
BASE_URL="${BASE_URL:-http://localhost:3000}"

command -v ffmpeg >/dev/null || { echo "ffmpeg required (brew install ffmpeg)" >&2; exit 1; }
command -v mvn >/dev/null || { echo "Maven is required to run Karate UI" >&2; exit 1; }
curl -fsS "$BASE_URL/api/health" >/dev/null || {
  echo "Docling Studio is not healthy at $BASE_URL; start the remote Docker stack first." >&2
  exit 1
}

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"

vf="fps=$FPS"
[[ -n "$CROP" ]] && vf="crop=$CROP,$vf"

ffmpeg -y -loglevel warning \
  -f avfoundation -capture_cursor 1 -pixel_format uyvy422 -framerate "$FPS" -i "${SCREEN}:none" \
  -vf "$vf" -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$OUT" &
FFMPEG_PID=$!
stop_capture() {
  kill -INT "$FFMPEG_PID" 2>/dev/null || true
  wait "$FFMPEG_PID" 2>/dev/null || true
}
trap stop_capture EXIT

for _ in $(seq 1 100); do
  [[ -s "$OUT" ]] && break
  sleep 0.1
done
[[ -s "$OUT" ]] || {
  echo "ffmpeg did not capture a frame from avfoundation device '$SCREEN'." >&2
  echo "Grant Screen Recording to the terminal app running this shell in System Settings > Privacy & Security, then recheck the screen device index." >&2
  exit 1
}

set +e
mvn test -f "$ROOT/e2e/ui/pom.xml" \
  -Dtest=AnalysisEditorRunner \
  -Ddemo=true \
  -DbaseUrl="$BASE_URL" \
  -DuiBaseUrl="$BASE_URL" &
MVN_PID=$!
while kill -0 "$MVN_PID" 2>/dev/null; do
  osascript -e 'tell application "Google Chrome" to activate' >/dev/null 2>&1 || true
  sleep 2
done
wait "$MVN_PID"
TEST_STATUS=$?
set -e

stop_capture
trap - EXIT

if [[ ! -s "$OUT" ]]; then
  echo "No video was produced at $OUT" >&2
  exit 1
fi
echo "Analysis editor video: $OUT"
exit "$TEST_STATUS"
