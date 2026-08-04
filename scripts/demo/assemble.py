#!/usr/bin/env python3
"""Cut the Ollama waits out of the raw capture and lay the narration onto it.

Two jobs, and the timing log is what makes both exact:

1. **Trim.** Each Ask run is 20-40s of spinner. No demo shows that. We cut each
   wait down to `keepSpinnerMs`, using the epochs Karate stamped at run start
   (41/71) and at the answer's arrival (42/72).

2. **Place.** Every clip is dropped at the epoch of the shot it belongs to,
   shifted left by whatever we cut before it. Ollama can take 20s or 40s and the
   audio still lands, because the offsets come from the run rather than from a
   stopwatch someone held.

Invoked by assemble.sh. Inputs are all produced by render-narration.sh + record.sh.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "out/demo"
NAR = ROOT / "out/narration"
RAW = OUT / "raw.mp4"
FINAL = OUT / "ask-demo.mp4"

# Which narration clip hangs off which mark. Marks 42/72 (the answer landing)
# are deliberately unused as anchors: the clip riding over the wait is still
# speaking then. 43/73 are stamped once it has finished, which is why the next
# clip hangs off those instead.
CLIP_AT = {
    "1": 1, "2a": 2, "2b": 2, "3": 3,
    "4a": 4, "4b": 41,
    "5a": 5, "5b": 51, "5c": 52, "5d": 53, "5e": 54,
    "7a": 7, "7b": 71, "7c": 73,
    "8": 8,
}

# (run-start mark, answer mark) — the legs whose spinner gets cut.
WAIT_LEGS = [(41, 42), (71, 72)]


def die(msg: str) -> None:
    sys.exit(f"error: {msg}")


def ms(path: pathlib.Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return int(float(out) * 1000)


def main() -> None:
    for f in (RAW, OUT / "timing.json", OUT / "capture-epoch.txt", NAR / "pace.json"):
        if not f.exists():
            die(f"missing {f} — run render-narration.sh then record.sh")

    timing = json.loads((OUT / "timing.json").read_text())
    pace = json.loads((NAR / "pace.json").read_text())
    capture_epoch = int((OUT / "capture-epoch.txt").read_text().strip())
    keep = int(pace["_keepSpinnerMs"])
    video_ms = ms(RAW)

    # mark → offset into the raw capture
    marks = {m["shot"]: m["epochMs"] - capture_epoch for m in timing["marks"]}

    # ── 1. Work out the cuts ────────────────────────────────────────────────
    cuts: list[tuple[int, int]] = []
    for start_mark, end_mark in WAIT_LEGS:
        if start_mark not in marks or end_mark not in marks:
            print(f"  marks {start_mark}/{end_mark} absent — that wait left untrimmed")
            continue
        cut_from = marks[start_mark] + keep
        cut_to = marks[end_mark]
        run_ms = cut_to - marks[start_mark]
        if cut_to <= cut_from:
            print(f"  run at mark {start_mark} took {run_ms}ms (< {keep}ms kept) — nothing to cut")
            continue
        cuts.append((cut_from, cut_to))
        print(f"  cut {cut_from:>7}ms → {cut_to:>7}ms   (run took {run_ms}ms, keeping {keep}ms)")

    cuts.sort()
    cut_total = sum(b - a for a, b in cuts)

    def shift(offset: int) -> int:
        """Raw offset → trimmed offset. Subtract every cut that ends at or before
        it; an offset landing inside a cut collapses to that cut's start."""
        out = offset
        for a, b in cuts:
            if offset >= b:
                out -= b - a
            elif offset > a:
                out -= offset - a
        return max(0, out)

    print(f"\n  trimming {cut_total}ms out of {video_ms}ms → {video_ms - cut_total}ms\n")

    # ── 2. Place the clips ──────────────────────────────────────────────────
    # Clips sharing a mark (2a+2b; nothing else, post-merge) play back-to-back
    # behind consecutive delay()s, so stagger by cumulative pace — pace, not raw
    # duration, since pace is what the feature actually waited (it includes PAD_MS).
    cursor: dict[int, int] = {}
    placements = []
    trimmed_ms = video_ms - cut_total
    overruns = 0

    for key in [k for k in pace if not k.startswith("_")]:
        clip = NAR / f"{key}.mp3"
        if not clip.exists():
            continue
        mark = CLIP_AT.get(key)
        if mark is None:
            print(f"  no mark mapped for clip '{key}' — skipped", file=sys.stderr)
            continue
        if mark not in marks:
            print(f"  mark {mark} absent from timing.json — clip '{key}' skipped", file=sys.stderr)
            continue

        offset = shift(marks[mark]) + cursor.get(mark, 0)
        cursor[mark] = cursor.get(mark, 0) + pace[key]

        dur = ms(clip)
        flag = ""
        if offset + dur > trimmed_ms:
            flag = f"  ⚠ OVERRUNS by {offset + dur - trimmed_ms}ms"
            overruns += 1
        print(f"  {key:<4} mark {mark:<3} @ {offset:>7}ms  ({dur:>5}ms){flag}")
        placements.append((clip, offset))

    if not placements:
        die("no clips placed — nothing to mux")

    # ── 3. Build the graph ──────────────────────────────────────────────────
    # Video: keep the segments between the cuts, concat them. Trimming forces a
    # re-encode — `-c:v copy` can only cut on keyframes, which would drift.
    segs, prev = [], 0
    for a, b in cuts:
        segs.append((prev, a))
        prev = b
    segs.append((prev, None))

    vfilters, vlabels = [], []
    for i, (a, b) in enumerate(segs):
        window = f"start={a / 1000}" + (f":end={b / 1000}" if b else "")
        vfilters.append(f"[0:v]trim={window},setpts=PTS-STARTPTS[v{i}]")
        vlabels.append(f"[v{i}]")
    vfilters.append(f"{''.join(vlabels)}concat=n={len(segs)}:v=1:a=0[v]")

    afilters, alabels = [], []
    for i, (_, offset) in enumerate(placements, start=1):
        afilters.append(f"[{i}]adelay={offset}|{offset}[a{i}]")
        alabels.append(f"[a{i}]")
    # normalize=0: amix otherwise divides every clip's gain by the input count
    # and the voice comes out inaudible. They never overlap, so nothing clips.
    afilters.append(f"{''.join(alabels)}amix=inputs={len(placements)}:normalize=0[a]")

    cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-i", str(RAW)]
    for clip, _ in placements:
        cmd += ["-i", str(clip)]
    cmd += [
        "-filter_complex", ";".join(vfilters + afilters),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(FINAL),
    ]
    subprocess.run(cmd, check=True)

    if overruns:
        print(f"\n⚠ {overruns} clip(s) run past the picture — raise PAD_MS or trim the text "
              f"in narration.json, re-render, re-assemble (no re-record needed)")
    print(f"\nfinal → {FINAL}  ({ms(FINAL) / 1000:.1f}s)")


if __name__ == "__main__":
    main()
