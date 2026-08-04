# Ask demo — automated capture

Records the "Ask" walkthrough (`docs/demo/303-ask-demo-script.md`) with zero manual
editing: Karate drives Chrome, ffmpeg captures the screen, and the voiceover is placed
from timestamps the run itself emitted.

**Nothing here is a test.** `demo/ask-demo.feature` asserts almost nothing and
deliberately uses `delay()`, which `e2e/CONVENTIONS.md` forbids — in a video the pacing
*is* the deliverable. The split is strict: `waitFor()` for "is the app ready", `delay()`
only to hold a shot for the camera. It's tagged `@demo` in a directory `UIRunner` doesn't
scan, so it can't leak into `@ui` / `@critical`.

## Why it stays in sync

The naive approach — record, then drag audio onto a waveform — dies on the first
re-record, because the two Ollama runs take 20–40s and never the same. So:

1. **Audio is rendered first.** Its measured durations become `pace.json`, which the
   feature reads back as its `delay()` values. The picture can never be shorter than the
   voice over it.
2. **The run stamps itself.** Karate writes an absolute epoch per shot; `record.sh` stamps
   the epoch of ffmpeg's first frame. `assemble.py` subtracts them to get each clip's
   offset. Ollama can take 20s or 40s — the audio still lands.
3. **The waits are cut.** Each Ask run is trimmed to `keepSpinnerMs` (6s). Nobody watches
   30s of a spinner. The feature's hold arithmetic uses `min(elapsed, keepSpinner)`, so a
   run leg lasts *exactly* its clip's length once trimmed — which is why **the final cut is
   a constant ~3:07 whatever the model did**. Both sides read `_keepSpinnerMs` from
   `pace.json`; they cannot drift.

Accurate to a few hundred ms. That is nothing for a voiceover; it is not lip-sync.

## Why shots 5 and 6 are merged

The first cut explained the RAG loop over a frozen timeline and clicked through it
afterwards: 53% of the film was a static screen with a voice over it, including 43s where
literally nothing moved. The loop mechanics now ride on the row clicks — each sentence
lands as the page jumps, the tree opens, Properties fills. Same content, half the dead air,
and the words describe what you're watching instead of what you watched a minute ago.

## Prerequisites

```bash
brew install ffmpeg jq          # ffmpeg 5.1.2+ verified
export ELEVENLABS_API_KEY='…'   # in your shell — never as a script argument
```

**The JDK is pinned for you.** `e2e/ui/pom.xml` targets Java 17 (class file 61), but an
interactive shell here resolves `java` to Java 8, and surefire forks with whatever
`JAVA_HOME` says — so `mvn test` dies on `UnsupportedClassVersionError ... 61.0 ... up to
52.0` before Karate ever starts. `record.sh` detects this and pins `JAVA_HOME` to a JDK 17
via `/usr/libexec/java_home`, leaving an already-adequate `JAVA_HOME` (17+) alone.

Same trap as the backend's bare `uvicorn` resolving to the conda base: **a repeatable
recording cannot depend on ambient shell state.** Note this also means `mvn test` on the
*existing* UI suite fails from that shell for the same reason — those runs presumably go
through IntelliJ, which carries its own JDK setting.

Grant **Screen Recording** to your terminal (System Settings › Privacy & Security), or
ffmpeg captures a black frame and `record.sh` aborts on it.

Find your screen index — it is very unlikely to be `0`:

```bash
ffmpeg -f avfoundation -list_devices true -i ""   # → [2] Capture screen 0
```

## You start the runtime

```bash
# backend — .venv/bin/uvicorn, NOT bare uvicorn (that resolves to the conda base
# and its docling-agent 0.1.0, and the Ask panel silently vanishes)
cd document-parser
REASONING_ENABLED=true OLLAMA_HOST=http://localhost:11434 \
REASONING_MODEL_ID=granite4.1:3b \
.venv/bin/uvicorn main:app --port 8000

# frontend
cd frontend && npm run dev        # :3000

# warm the model — a cold first call adds ~10s of dead air on camera
ollama run granite4.1:3b "hi"
```

`record.sh` refuses to start unless `/api/health` reports `reasoningAvailable: true`.

## Pick the document

Must have a **COMPLETED analysis** and **real section headers** — a paper, not
`small.pdf`. Without headers, docling-agent falls back to returning the whole document
with `iterations=[]`, and the timeline you came to film is empty.

## Run

```bash
scripts/demo/render-narration.sh              # ElevenLabs → clips + pace.json
scripts/demo/render-narration.sh --say        # or: local macOS voice, timing rehearsal only

# Full UUID — record.sh rejects a truncated one. The questions are overridable;
# the run logs `trace rows:` and warns if the agent converged in one pass, which
# makes for a one-line timeline and a shot 5 the narration no longer matches.
DEMO_DOC_ID=538449bb-a0b6-4aba-b43a-51f0825e54d7 SCREEN=2 \
DEMO_Q1="What datasets were used to evaluate the model?" \
scripts/demo/record.sh
scripts/demo/assemble.sh                      # trim + mux → out/demo/ask-demo.mp4
```

Iterate on wording by editing `narration.json` and re-running `render-narration.sh`; the
feature's pacing follows automatically. Only re-record when the *visuals* change.

## Knobs

| Var | Default | Notes |
|---|---|---|
| `SCREEN` | `2` | avfoundation index, from `-list_devices` |
| `CROP` | full screen | `2880:1800:0:0` for the 1440×900 Chrome window on a retina display (2×) |
| `FPS` | `30` | |
| `PAD_MS` | `900` | silence after each clip, so the cut never lands on the last syllable |
| `BBOX_POINT` | unset | `"x,y"` to include the click-a-region beat — see below |

## The canvas caveat

Bboxes are painted on a `<canvas>` (`BboxCanvas.vue`), so they have **no DOM node** to
target and no selector can click one. The beat is coordinate-driven and off by default.
To include it: dry-run once at the fixed 1440×900 geometry, read the pixel coordinates of
a box off a screenshot, and pass `BBOX_POINT="x,y"`. Stable across takes as long as the
window geometry and document don't change.

Everything else — tree, tabs, composer, trace rows — is real DOM with `data-e2e`
attributes and needs no coordinates.

## Known: the bars are not durations

docling-agent 0.6.0 carries no per-step `duration_ms`, so the timeline renders uniform
bars plus a *"Per-step timing not available for this run"* footnote. The **total** is real
(Studio measures wall-clock). The narration says so out loud rather than hoping nobody
notices. Upstream PR docling-project/docling-agent#42 is what fixes it; `record.sh` logs
`degradedTiming` so you know which take you got.
