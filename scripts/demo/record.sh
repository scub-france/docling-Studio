#!/usr/bin/env bash
# Record the demo: start ffmpeg screen capture, drive Chrome with Karate, stop.
#
# YOU start the runtime first (backend + frontend + Ollama) — see README.md.
# This script only captures and drives.
#
# The tricky part is the shared clock. ffmpeg and Karate have no common origin,
# so we stamp CAPTURE_EPOCH the moment ffmpeg's output file starts growing (its
# first frame) and let Karate stamp absolute epochs per shot. assemble.sh
# subtracts the two. Accurate to a few hundred ms — irrelevant for a voiceover,
# which is not lip-sync.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$ROOT/out/demo"

DOC_ID="${DEMO_DOC_ID:-}"
SCREEN="${SCREEN:-2}"           # avfoundation index: `Capture screen 0` (ffmpeg -f avfoundation -list_devices true -i "")
FPS="${FPS:-30}"
CROP="${CROP:-}"                # e.g. 2880:1800:0:0 (retina = 2× the Chrome window). Empty = full screen.
BBOX_POINT="${BBOX_POINT:-}"    # "x,y" to include the canvas-click beat

[[ -n "$DOC_ID" ]] || { echo "DEMO_DOC_ID=<uuid> required (a doc with a COMPLETED analysis + section headers)" >&2; exit 1; }
# Catch a pasted placeholder ("538449bb-…") here rather than 40s later as an
# opaque 404 from Karate, after ffmpeg and Chrome have already started.
[[ "$DOC_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] || {
  echo "DEMO_DOC_ID is not a UUID: '$DOC_ID'" >&2
  echo "Looks like a truncated example was pasted — use the full id." >&2
  exit 1
}
[[ -f "$ROOT/e2e/ui/src/test/resources/demo/pace.json" ]] || { echo "pace.json missing — run scripts/demo/render-narration.sh first" >&2; exit 1; }

mkdir -p "$OUT"
RAW="$OUT/raw.mp4"
rm -f "$RAW" "$OUT/capture-epoch.txt"

echo "── preflight ─────────────────────────────────────────"

# Maven forks surefire with whatever JAVA_HOME points at, and an interactive
# shell here defaults to Java 8 — which cannot load the pom's Java 17 target
# (class file 61 vs 52). Pin it, for the same reason the backend must run from
# .venv/bin/uvicorn: a recording must not depend on ambient shell state.
jdk_major() {
  local home="$1" v
  [[ -x "$home/bin/java" ]] || return 1
  v=$("$home/bin/java" -version 2>&1 | head -1 | sed -E 's/.*version "([0-9]+)(\.[0-9]+)*.*/\1/')
  # Java 8 reports 1.8.0_x → major "1"; anything else reports its real major.
  [[ "$v" == "1" ]] && v=8
  echo "$v"
}
need=17
have=$(jdk_major "${JAVA_HOME:-}" 2>/dev/null || true)
if [[ -z "$have" ]] || (( have < need )); then
  JAVA_HOME="$(/usr/libexec/java_home -v "$need" 2>/dev/null)" || {
    echo "no JDK $need found. e2e/ui/pom.xml targets Java $need; this shell's java is:" >&2
    java -version 2>&1 | sed 's/^/  /' >&2
    echo "install one (brew install --cask temurin@17) or point JAVA_HOME at it." >&2
    exit 1
  }
  export JAVA_HOME
fi
echo "jdk          $(jdk_major "$JAVA_HOME") — $JAVA_HOME"

health=$(curl -sf http://localhost:8000/api/health) || { echo "backend down on :8000 — you start it, see README" >&2; exit 1; }
echo "$health" | jq -e '.reasoningAvailable == true' >/dev/null \
  || { echo "reasoningAvailable=false — backend is not running from .venv/bin/uvicorn with REASONING_ENABLED=true" >&2; exit 1; }
curl -sfI http://localhost:3000 >/dev/null || { echo "frontend down on :3000" >&2; exit 1; }
echo "backend ok (reasoning wired) · frontend ok"

echo "── capture ───────────────────────────────────────────"
vf="fps=$FPS"
[[ -n "$CROP" ]] && vf="crop=$CROP,$vf"

# -pix_fmt uyvy422 on the INPUT: avfoundation screen capture offers uyvy422 /
# yuyv422 / nv12 / 0rgb / bgr0 and not yuv420p, so without this ffmpeg logs a
# "not supported by the input device" warning and silently overrides. Say it
# explicitly on the way in; yuv420p is an OUTPUT concern (libx264, for players).
ffmpeg -y -loglevel warning \
  -f avfoundation -capture_cursor 1 -pix_fmt uyvy422 -framerate "$FPS" -i "$SCREEN" \
  -vf "$vf" -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p \
  "$RAW" &
FFMPEG_PID=$!
trap 'kill -INT $FFMPEG_PID 2>/dev/null || true' EXIT

# Stamp the epoch at ffmpeg's first frame, not at launch — the difference is
# ~1s of Chrome-less desktop we'd otherwise misattribute to shot 1.
for _ in $(seq 1 100); do
  [[ -s "$RAW" ]] && break
  sleep 0.1
done
[[ -s "$RAW" ]] || { echo "ffmpeg never produced a frame — grant Screen Recording to your terminal in System Settings › Privacy" >&2; exit 1; }
CAPTURE_EPOCH=$(python3 -c 'import time; print(int(time.time()*1000))')
echo "$CAPTURE_EPOCH" > "$OUT/capture-epoch.txt"
echo "recording screen $SCREEN @ ${FPS}fps → $RAW"

echo "── drive ─────────────────────────────────────────────"
MVN_ARGS=(-f "$ROOT/e2e/ui/pom.xml" -Dtest=DemoRunner -Ddemo=true -DdemoDocId="$DOC_ID")
[[ -n "$BBOX_POINT" ]] && MVN_ARGS+=(-DdemoBboxPoint="$BBOX_POINT")
# The questions decide whether the timeline has rows to talk about. Try a few
# with DEMO_Q1/DEMO_Q2 before committing to a take — the run logs `trace rows:`
# and warns when the agent converged in one pass.
[[ -n "${DEMO_Q1:-}" ]] && MVN_ARGS+=(-DdemoQ1="$DEMO_Q1")
[[ -n "${DEMO_Q2:-}" ]] && MVN_ARGS+=(-DdemoQ2="$DEMO_Q2")
mvn test "${MVN_ARGS[@]}" || { echo "karate run failed — the raw capture is still at $RAW" >&2; }

sleep 1
kill -INT $FFMPEG_PID 2>/dev/null || true
wait $FFMPEG_PID 2>/dev/null || true
trap - EXIT

cp "$ROOT/e2e/ui/target/demo-timing.json" "$OUT/timing.json" 2>/dev/null \
  || { echo "no timing log — karate did not reach the end" >&2; exit 1; }

echo
echo "raw video    → $RAW  ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$RAW")s)"
echo "timing log   → $OUT/timing.json"
echo "next         → scripts/demo/assemble.sh"
