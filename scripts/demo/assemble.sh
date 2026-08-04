#!/usr/bin/env bash
# Trim the Ollama waits out of the raw capture and mux the narration onto it.
#
#   out/demo/raw.mp4 + out/narration/*.mp3 + out/demo/timing.json
#     → out/demo/ask-demo.mp4
#
# The offset arithmetic (cuts, and every clip's position on the trimmed
# timeline) lives in assemble.py — it outgrew bash the moment the cuts started
# shifting everything downstream of them.
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/assemble.py" "$@"
