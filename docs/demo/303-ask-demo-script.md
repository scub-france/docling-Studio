# Docling Studio — "Ask" demo video script

**Target:** ~3:07 final cut, English voiceover, screen recording.
**Feature:** Reasoning Trace v2 (#303) — Ask panel + trace timeline in the Parse view.

Everything below is grounded in the code as of `feature/303-reasoning-trace-v2-parse-view`.
Claims the UI does *not* support are called out in **Accuracy guardrails** at the bottom —
read those before recording.

**This script is not recorded by hand.** `scripts/demo/` drives it: the narration is rendered
first, its measured durations become the camera holds, Karate plays the shots, and the audio is
placed from timestamps the run itself emitted. The two Ollama waits are trimmed to 6 s in post,
which is why the final cut is a constant 3:07 no matter how slow the model was. Edit the words
in `scripts/demo/narration.json` and the pacing follows — see `scripts/demo/README.md`.

The timecodes below are indicative; `render-narration.sh` prints the real ones.

---

## Pre-flight (not filmed)

| Check | Why |
|---|---|
| Start the backend with **`.venv/bin/uvicorn`**, not bare `uvicorn` | Bare `uvicorn` resolves to the conda base and its docling-agent 0.1.0 → the Ask tab silently disappears |
| Boot log must read `Reasoning runner enabled (docling-agent 0.6.0 from .../.venv/...)` | Confirms the right install won |
| `ollama ps` shows `granite4.1:3b` warm | First call on a cold model adds ~10s of dead air |
| Pick a document **with section headers** (the ScreenParse paper works) | No headers → the agent falls back to returning the whole document, `iterations=[]`, and **the timeline is empty** |
| Run both questions once before recording | You need to know how many rows appear and whether it converges |
| Parse tab selected, one analysis already completed | The demo starts on a parsed doc, not on an upload |

A run takes **20–40 s**. Plan to cut, or talk over it — the script below talks over it.

---

## Shot 1 — Open on the parsed document · 0:00–0:20

**Screen:** Parse view, already loaded. Left rail "Structure" with the node tree, PDF preview
centre, "Properties" panel right. Slowly scroll the tree once.

> This is Docling Studio. We've parsed a PDF, and what came back isn't a wall of text —
> it's a document tree. Every title, paragraph, table and figure is a node, and every node
> knows where it lives on the page.

---

## Shot 2 — Structure is addressable · 0:20–1:00

**Screen:** Click a section header in the tree → its bbox highlights in the PDF.
Then click a *different* bbox directly on the page → the tree reveals and scrolls to that node.
Let the Properties panel land on both.

> Click a node, and the preview highlights the exact region it came from. Click a region,
> and the tree opens up to the node behind it. The Properties panel is showing what Docling
> actually extracted: the node's self-reference, its type, the page, and its bounding box.
>
> Keep that self-reference in mind — the string starting with `#/texts`. It's about to do
> the heavy lifting.

**Note:** the bbox values render as **percentages**, not raw PDF coordinates. Don't call them points.

---

## Shot 3 — Reveal the Ask panel · 1:00–1:15

**Screen:** Click the **"Ask"** tab in the right panel. The trace dock appears under the PDF
preview and the preview shrinks. Pause a beat so the layout change reads on camera.

> The Ask tab. Two things just appeared: a composer on the right, and an empty timeline
> below the page. That timeline is the point of this whole feature.

---

## Shot 4 — First question, and what actually happens · 1:15–2:10

**Screen:** Type **"What problem does this paper address?"** → click **Run**.
The status goes to "Reading the document…". Talk over the wait.

> Now — Docling Studio does not implement retrieval. Not a single line of it. We hand the
> parsed document to **docling-agent**, the agent library from the Docling project, and let
> its RAG agent do the work.
>
> And it works differently from what you'd expect. There's no chunking here. No embeddings.
> No vector database. The library calls it *chunkless* RAG, and here's the loop: it builds
> a table-of-contents outline of the document, shows that outline to the model, and asks
> one question — *which section should I read next, and why?* It reads only that section.
> Then it asks the model: *can you answer now?* If not, it goes back to the outline and
> picks another section. Up to five times, until the model says it has enough.
>
> So the model never sees the whole paper. It navigates it — the same way you would.

---

## Shot 5 — The trace, read by clicking through it · 1:35–3:00

> **This was two shots.** The first draft explained the loop over a frozen timeline, then
> clicked through it afterwards — 43 s of dead picture while a voice lectured. Merged: every
> explanatory beat now lands on a click that makes the page jump, the tree open and Properties
> fill. The words describe what the viewer is watching happen. `ask-demo.feature` drives this.

**Screen:** the answer lands, rows appear. Beat, then click the **first** row.

> There's the answer. But look underneath: that's every step the agent took, in order.
> That timeline is the loop it just ran.

**Screen:** first row clicked → page jumps, tree opens, Properties fills.

> Each row is one pass. It never saw the whole paper — it saw an outline, just the headings,
> and picked one section. The title you're reading is the model's own reason for picking it.
> Then it read that section, and only that section.

**Screen:** click the **last** row (the bright / answered one).

> Then it asked itself: can I answer now? The dimmed rows are where the answer was no, and it
> went back to the outline for another section. The bright one is where it said yes. Five
> passes, maximum. So the model navigates the document, the way you would.

**Screen:** click the *same* row again — it re-scrolls (`focusTick`, deliberate).

> And this is the part I actually care about. That chip is a self-reference into the very same
> document tree the viewer is rendering. So the page jumps to what it read. The tree opens to
> it. Properties fills in. Every claim in the trace points at a real region of a real page.
> That's the difference between a model telling you it read something, and showing you.

**Screen:** rest on the header stats + footnote.

> Up top: the step count, the total time, and the model — Granite 4.1 3B, local, through
> Ollama. One honest caveat: the per-step timings aren't in the released library yet, so those
> bars are step order, not duration. The total is real.

---

## Shot 7 — Second question, a longer walk · 3:00–3:30

**Screen:** Ask **"What datasets were used for evaluation?"** → Run.
This one typically explores more sections before converging — more rows, more dimmed ones.
Click through two of them.

> One more, harder — something that isn't in the abstract.
>
> Four steps this time. Watch the reasons: it guessed, read, admitted it wasn't enough,
> and tried somewhere else. That's not a failure — it's the loop working, and it's on the
> record. Every dead end it walked down is right there.

---

## Shot 8 — Close · 4:25–4:45

**Screen:** Back out to the full Parse view, both turns in the Ask panel.

> So: Docling parses the document. docling-agent reasons over its structure. Docling Studio
> makes that reasoning inspectable and clickable.
>
> The trace surface we're consuming here — `run_with_trace` — is a contribution we
> upstreamed to docling-agent. It shipped in 0.6.0. If you're building on the library, it's
> already there for you.

---

## Accuracy guardrails — do not say these

| Don't say | Reality |
|---|---|
| "the bars show how long each step took" | Per-step `duration_ms` is absent in docling-agent 0.6.0 → uniform bars + a "timing not available" footnote. Total duration is real (Studio measures wall-clock in `reasoning_service.py:108-114`) |
| "it's marked converged" | No textual label. Convergence shows only as the **green dot** on the turn card |
| "you can see how many characters it read" / "the per-step response" | `section_text_length` and per-step `response` are **not rendered**. Only the final answer is |
| "the highlight follows in the Parse/markdown view too" | Only **three** surfaces: PDF preview, doc tree, Properties. `MarkdownViewer.vue` has no focus wiring |
| "token counts" | Hardcoded to 0 in `trace_builder.py:95-96`, never rendered |
| "it chunks the document" | It explicitly does **not**. Outline + section reads. Saying "chunk" here is the one thing that would make a Docling person wince |
| "it reads until it's confident" | It reads until `can_answer` is true **or** it hits `max_iterations = 5` — those are different, and a non-converged run is a real outcome |

## Facts you can state on camera

- Chunkless RAG: outline → select section (with a stated reason) → read only that section →
  attempt answer → repeat. `docling_agent/agent/rag.py:_rag_loop`.
- `max_iterations = 5` (docling-agent default; Studio doesn't override it).
- Studio passes `tools=[]` and a per-instance Ollama backend — no global `OLLAMA_HOST` mutation.
- Section refs are `DoclingDocument` self-refs → that's *why* the trace rows are clickable.
- `run_with_trace()` is upstream PR docling-project/docling-agent#39, released in 0.6.0.
- Per-step timing is upstream PR #42, still open.
