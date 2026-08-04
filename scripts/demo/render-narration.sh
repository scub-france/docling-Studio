#!/usr/bin/env bash
# Render the voiceover clips and emit the pacing the Karate feature reads back.
#
# ElevenLabs by default; --say falls back to macOS `say` (free, local, robotic —
# fine for a timing rehearsal, not for publication).
#
# The key is read from $ELEVENLABS_API_KEY and never printed, logged, or written
# to disk. Export it in your shell; don't pass it as an argument (it would land
# in your shell history and in ps output).
#
# Output (out/narration/):
#   <key>.mp3            one clip per camera hold
#   pace.json            { "1": 20480, "2a": 14200, ... } — measured ms, padded
#   durations.txt        human-readable table
# pace.json is copied to e2e/ui/src/test/resources/demo/ so the feature's
# delay() calls always outlast the audio placed over them.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$ROOT/out/narration"
NARRATION="$HERE/narration.json"
PACE_DEST="$ROOT/e2e/ui/src/test/resources/demo/pace.json"

# Silence padded after each clip so the picture never cuts on the last syllable.
PAD_MS="${PAD_MS:-900}"
ENGINE="elevenlabs"
[[ "${1:-}" == "--say" ]] && ENGINE="say"

command -v jq >/dev/null || { echo "jq required: brew install jq" >&2; exit 1; }
command -v ffprobe >/dev/null || { echo "ffprobe required: brew install ffmpeg" >&2; exit 1; }

if [[ "$ENGINE" == "elevenlabs" && -z "${ELEVENLABS_API_KEY:-}" ]]; then
  cat >&2 <<'EOF'
ELEVENLABS_API_KEY is not set.

  export ELEVENLABS_API_KEY='...'      # in your shell, not in this script
  scripts/demo/render-narration.sh

Or rehearse the timing with the local macOS voice (robotic, do not publish):

  scripts/demo/render-narration.sh --say
EOF
  exit 1
fi

# Purge stale clips: renaming a key in narration.json would otherwise leave the
# old .mp3 on disk, and a mis-mapped CLIP_AT would happily mux the dead take.
mkdir -p "$OUT"
rm -f "$OUT"/*.mp3 "$OUT"/*.aiff
: > "$OUT/durations.txt"

VOICE_ID=$(jq -r '.voice.voice_id' "$NARRATION")
MODEL_ID=$(jq -r '.voice.model_id' "$NARRATION")
STABILITY=$(jq -r '.voice.stability' "$NARRATION")
SIMILARITY=$(jq -r '.voice.similarity_boost' "$NARRATION")
SPEED=$(jq -r '.voice.speed' "$NARRATION")

echo "engine: $ENGINE | pad: ${PAD_MS}ms | out: $OUT"
echo

pace_pairs=()

for key in $(jq -r '.shots[].key' "$NARRATION"); do
  text=$(jq -r --arg k "$key" '.shots[] | select(.key==$k) | .text' "$NARRATION")
  clip="$OUT/$key.mp3"

  if [[ "$ENGINE" == "elevenlabs" ]]; then
    # --fail-with-body so an API error surfaces instead of writing an HTML body
    # into a .mp3 and failing mysteriously three steps later.
    jq -n --arg t "$text" --arg m "$MODEL_ID" \
          --argjson s "$STABILITY" --argjson sb "$SIMILARITY" --argjson sp "$SPEED" \
      '{text:$t, model_id:$m, voice_settings:{stability:$s, similarity_boost:$sb, speed:$sp}}' \
    | curl -sS --fail-with-body \
        -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID" \
        -H "xi-api-key: $ELEVENLABS_API_KEY" \
        -H "Content-Type: application/json" \
        -d @- -o "$clip"
  else
    say -v Samantha -o "$OUT/$key.aiff" "$text"
    ffmpeg -y -loglevel error -i "$OUT/$key.aiff" "$clip"
    rm -f "$OUT/$key.aiff"
  fi

  [[ -s "$clip" ]] || { echo "empty clip for '$key' — TTS failed" >&2; exit 1; }

  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$clip")
  ms=$(python3 -c "print(int(float('$dur')*1000) + $PAD_MS)")
  pace_pairs+=("$(jq -n --arg k "$key" --argjson v "$ms" '{($k): $v}')")

  printf '%-4s %7.2fs → hold %6dms  %s…\n' "$key" "$dur" "$ms" "$(echo "$text" | cut -c1-48)" \
    | tee -a "$OUT/durations.txt"
done

# `_`-prefixed keys are config, not holds — the feature and assemble.py both
# read _keepSpinnerMs from here so they can never drift apart. Sums below filter
# them out.
KEEP_SPINNER=$(jq -r '.trim.keepSpinnerMs' "$NARRATION")
printf '%s\n' "${pace_pairs[@]}" \
  | jq -s --argjson ks "$KEEP_SPINNER" 'add + {_keepSpinnerMs: $ks}' > "$OUT/pace.json"
cp "$OUT/pace.json" "$PACE_DEST"

total=$(jq '[to_entries[] | select(.key | startswith("_") | not) | .value] | add / 1000' "$OUT/pace.json")
p4b=$(jq '.["4b"] / 1000' "$OUT/pace.json")
p7b=$(jq '.["7b"] / 1000' "$OUT/pace.json")

echo
echo "pace.json → $PACE_DEST"
printf 'total camera holds: %.1fs\n' "$total"

# On the RAW capture a run leg lasts max(runMs, pace[clip] - min(runMs, keep)).
# assemble.py then cuts each wait to keepSpinnerMs, which normalises every leg to
# exactly its pace value — so the trimmed film is just the sum of the holds,
# whatever Ollama did. That invariance is the whole point of the trim.
python3 - "$total" "$p4b" "$p7b" "$KEEP_SPINNER" <<'PY'
import sys
total, p4b, p7b = (float(x) for x in sys.argv[1:4])
keep = float(sys.argv[4]) / 1000
print(f"  final cut  → {int(total//60)}:{int(total%60):02d}  (constant — spinners trimmed to {keep:.0f}s each)")
for label, run in (("fast Ollama (20s)", 20.0), ("slow Ollama (40s)", 40.0)):
    raw = total + sum(max(0.0, r - keep) for r in (run, run))
    print(f"  raw capture, {label:<18} → {int(raw//60)}:{int(raw%60):02d}")
for clip, pace in (("4b", p4b), ("7b", p7b)):
    if pace < keep:
        print(f"  ⚠ clip {clip} ({pace:.0f}s) is shorter than the {keep:.0f}s of spinner kept — "
              f"there will be silence on it")
PY
