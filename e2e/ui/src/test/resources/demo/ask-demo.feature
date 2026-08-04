@demo
Feature: DEMO — Ask panel walkthrough, driven for video capture (#303)

  # ⚠️ THIS IS NOT A TEST. It asserts almost nothing.
  #
  # It drives the browser through the 8 shots of docs/demo/303-ask-demo-script.md
  # so a screen recording can be captured deterministically, and writes a timing
  # log the audio pipeline uses to place the voiceover.
  #
  # ── Deliberate deviation from CONVENTIONS.md ──────────────────────────────
  # CONVENTIONS.md forbids `delay()`. That rule is right for tests and wrong
  # here: in a video, the pacing *is* the deliverable. The split is strict —
  #   * waitFor()/retry() → "is the app ready?"   (never a delay for this)
  #   * delay()           → "hold the shot for the camera"
  # Every delay() below is a camera hold whose duration comes from the measured
  # narration audio (classpath:demo/pace.json, written by render-narration.sh),
  # so the picture can never run shorter than the voice over it.
  #
  # This feature lives in demo/ which UIRunner does not scan, and is tagged
  # @demo so it can never leak into @ui / @critical runs.
  #
  # ── Requires (the runtime is yours to start) ──────────────────────────────
  #   backend  .venv/bin/uvicorn with REASONING_ENABLED=true + a warm Ollama
  #   frontend vite on :3000
  #   -Ddemo=true                  → non-headless Chrome at a fixed geometry
  #   -DdemoDocId=<uuid>           → a document with a COMPLETED analysis AND
  #                                  section headers (a paper, not small.pdf —
  #                                  no headers means docling-agent returns the
  #                                  whole doc, iterations=[], empty timeline)
  #
  # Run:
  #   mvn test -f e2e/ui/pom.xml -Dtest=DemoRunner#demo \
  #     -Ddemo=true -DdemoDocId=538449bb-a0b6-4aba-b43a-51f0825e54d7

  Background:
    * url baseUrl

  Scenario: Ask walkthrough — 8 shots, timing log emitted

    # ── Preconditions, failed loudly rather than filmed broken ──────────────
    * def docId = karate.properties['demoDocId']
    * if (!docId) karate.fail('-DdemoDocId=<uuid> is required — see the header')

    Given path '/api/health'
    When method GET
    Then status 200
    And match response.reasoningAvailable == true

    Given path '/api/documents', docId
    When method GET
    Then status 200

    # ── Timing log ──────────────────────────────────────────────────────────
    # Absolute epoch per shot. record.sh captures the epoch at which ffmpeg's
    # first frame landed; assemble.sh subtracts it to get each shot's offset
    # into the video. Absolute time is what survives the variable Ollama run.
    * def now = function(){ return java.lang.System.currentTimeMillis() }
    * def marks = []
    * def mark =
      """
      function(shot) {
        var t = now();
        marks.push({ shot: shot, epochMs: t });
        karate.log('=== SHOT', shot, '@', t);
      }
      """

    # Camera holds, in ms, keyed by shot — measured from the rendered
    # narration so the picture always outlasts the voice.
    * def pace = read('classpath:demo/pace.json')

    # assemble.py cuts each Ollama wait down to this. The rem4/rem7 arithmetic
    # below holds as if the spinner were already this short, so the narration
    # lands correctly on the TRIMMED timeline rather than the raw capture. Both
    # sides read it from pace.json — they must never disagree.
    * def keepSpinner = pace['_keepSpinnerMs']
    * def elapsedSince = function(t0){ return now() - t0 }

    # ── SHOT 1 — intro, then open on the parsed document ────────────────────
    # THREE holds on the SAME still picture: 0a welcomes, 0b says what Studio is
    # for, 1 reads the tree. Nothing moves for any of them — ~40s of static
    # opening, the same dead-picture problem that got shots 5 and 6 merged.
    # docs/demo/303-ask-demo-script.md shot 1 says "slowly scroll the tree once"
    # and this feature never did; doing it under the intro is the fix, and is
    # why the marks are split — assemble.py can place a scroll between them.
    * driver uiBaseUrl + '/docs/' + docId
    * waitFor('[data-e2e=parse-tab]')
    * waitFor('[data-e2e=tree-rail]')
    * waitFor('[data-e2e=preview-with-overlay]')
    * mark(0)
    * delay(pace['0a'])
    * delay(pace['0b'])
    * mark(1)
    * delay(pace['1'])

    # ── SHOT 2 — structure is addressable ───────────────────────────────────
    # Tree → PDF. The reverse leg (click a bbox → tree reveals) is NOT here:
    # the overlay is a <canvas>, so bboxes have no DOM node to target. Set
    # -DdemoBboxPoint=x,y (viewport coords, found from a dry-run screenshot at
    # the fixed window geometry) to include that beat; omitted, it's skipped.
    * mark(2)
    * def rows = locateAll('[data-e2e=tree-rail] .tree-node-row')
    * assert karate.sizeOf(rows) > 0
    * click('[data-e2e=tree-rail] .tree-node-row')
    # waitUntil(js), not retry().until(...) — `until` is not a method on Karate's
    # Driver in 1.4 or 1.5 (checked with javap against karate-core-1.5.0.jar), so
    # that form dies on a GraalJS TypeError. Several features under documents/
    # still carry it; see the note in scripts/demo/README.md.
    * waitUntil("!document.querySelector('[data-e2e=element-properties-empty]')")
    * waitFor('[data-e2e=element-properties]')
    * delay(pace['2a'])

    * def bboxPoint = karate.properties['demoBboxPoint']
    * if (bboxPoint) karate.call('@clickBbox', { point: bboxPoint })
    * if (!bboxPoint) karate.log('demoBboxPoint unset — canvas-click beat skipped')
    * delay(pace['2b'])

    # ── SHOT 3 — reveal the Ask panel ───────────────────────────────────────
    # The Ask tab is NOT the default (props is). Clicking it is what makes the
    # trace dock appear and the preview shrink — that layout shift is the shot.
    * mark(3)
    * click('[data-e2e=ask-tab]')
    * waitFor('[data-e2e=ask-panel]')
    * waitFor('[data-e2e=trace-panel]')
    * delay(pace['3'])

    # ── SHOT 4 — first question ─────────────────────────────────────────────
    # The question decides whether you get a timeline or a single row, and the
    # narration for shot 5 ("each row is one pass", "the dimmed rows") is only
    # true when the agent actually explores. "What problem does this paper
    # address?" converged in ONE pass on the first take — the answer sits in the
    # abstract, the agent read it and stopped. Q1 must be something it has to
    # hunt for. Override without touching this file:
    #   -DdemoQ1='...' -DdemoQ2='...'
    * def q1 = karate.properties['demoQ1'] || 'What datasets were used to evaluate the model, and how large are they?'
    * def q2 = karate.properties['demoQ2'] || 'What are the stated limitations of this approach?'
    * mark(4)
    * driver.input('[data-e2e=ask-composer-input]', q1)
    * delay(pace['4a'])
    * click('[data-e2e=ask-run-btn]')

    # The run is 20–40s and NOT deterministic — this is the one place the video
    # length floats. waitFor, never delay. The timing log absorbs the variance.
    * mark(41)
    * def t41 = now()
    * retry(60, 1000).waitFor('[data-e2e=ask-turn-card]')
    * retry(60, 1000).waitFor('[data-e2e=trace-row]')
    * mark(42)

    # Clip 4b starts at mark 41 and plays OVER the wait, so we hold only what's
    # LEFT of it. `min(elapsed, keepSpinner)` — not the raw elapsed — because
    # assemble.py will cut the spinner down to keepSpinner: on the trimmed
    # timeline this leg lasts exactly pace['4b'], which is where clip 5a starts.
    # Charging the full run here would leave 5a talking over 4b after the cut.
    * def rem4 = pace['4b'] - Math.min(elapsedSince(t41), keepSpinner)
    * karate.log('q1 run took', elapsedSince(t41), 'ms; holding a further', rem4, 'ms')
    * if (rem4 > 0) delay(rem4)

    # ── SHOT 5 — the trace, read by clicking through it ─────────────────────
    # The original script's shots 5 and 6 are merged. Explaining the loop over a
    # frozen timeline was 43s of dead picture; now every explanatory clip lands
    # on a click that makes the page jump, the tree open and Properties fill.
    * mark(5)
    * def rowCount = karate.sizeOf(locateAll('[data-e2e=trace-row]'))
    * assert rowCount > 0
    * waitFor('[data-e2e=trace-stats]')
    * waitFor('[data-e2e=trace-model-chip]')

    # docling-agent 0.6.0 carries no per-step duration_ms → uniform bars + the
    # footnote. Clip 5e says so out loud; this logs which take you actually got.
    * def degraded = exists('[data-e2e=trace-footnote]')
    * karate.log('trace rows:', rowCount, '| per-step timing degraded:', degraded)
    * if (rowCount < 2) karate.log('WARNING: converged in one pass — a single-row timeline makes for a poor demo. Pick a question that has to explore.')
    * delay(pace['5a'])

    # First step — the page jumps to what it read first. Clicking a row calls
    # focusElement(citations[0]) → PDF highlight + tree reveal.
    #
    # NOT Properties: `ElementProperties` and `ConversationPanel` are v-if'd on
    # the same `rightTab` in the same 360px column (DocParseTab.vue:107-140), so
    # with Ask open, [data-e2e=element-properties] is not in the DOM at all.
    # Waiting on it here burned 120s and failed the run. The visible surfaces
    # during this shot are the PDF preview and the tree — two, not three.
    * mark(51)
    * locateAll('[data-e2e=trace-row]')[0].click()
    * delay(pace['5b'])

    # Last step — where it committed. Indexed off locateAll rather than a
    # :nth-last-of-type selector, which would silently bind to the wrong node the
    # day the dock grows a sibling. Collapses onto row 0 when rowCount == 1;
    # harmless, and the warning above already flagged that run as a weak take.
    * mark(52)
    * def lastIdx = rowCount - 1
    * locateAll('[data-e2e=trace-row]')[lastIdx].click()
    * delay(pace['5c'])

    # Re-click the same row: focusTick bumps, so it re-scrolls even though it's
    # already focused (deliberate — see document/store.ts). That's the beat that
    # proves the link is live rather than a one-shot.
    * mark(53)
    * locateAll('[data-e2e=trace-row]')[lastIdx].click()
    * delay(pace['5d'])

    # Stats + footnote.
    * mark(54)
    * delay(pace['5e'])

    # ── SHOT 7 — second question, a longer walk ─────────────────────────────
    * mark(7)
    * driver.clear('[data-e2e=ask-composer-input]')
    * driver.input('[data-e2e=ask-composer-input]', q2)
    * delay(pace['7a'])
    * click('[data-e2e=ask-run-btn]')

    # Same arithmetic as shot 4 — trimmed-timeline remainder, not raw elapsed.
    * mark(71)
    * def t71 = now()
    # waitForResultCount is the purpose-built API for "wait until N of these
    # exist" — cleaner than polling karate.sizeOf, and it actually exists.
    * retry(60, 1000).waitForResultCount('[data-e2e=ask-turn-card]', 2)
    * mark(72)
    * def rem7 = pace['7b'] - Math.min(elapsedSince(t71), keepSpinner)
    * karate.log('q2 run took', elapsedSince(t71), 'ms; holding a further', rem7, 'ms')
    * if (rem7 > 0) delay(rem7)
    * mark(73)

    * def rows2 = karate.sizeOf(locateAll('[data-e2e=trace-row]'))
    * karate.log('trace rows, 2nd question:', rows2)
    * click('[data-e2e=trace-row]')
    * delay(pace['7c'])

    # ── SHOT 8 — close ──────────────────────────────────────────────────────
    * mark(8)
    * click('[data-e2e=props-tab]')
    * waitFor('[data-e2e=element-properties]')
    * delay(pace['8'])
    * mark(99)

    # ── Emit the timing log ─────────────────────────────────────────────────
    * def report = { marks: '#(marks)', traceRowsQ1: '#(rowCount)', traceRowsQ2: '#(rows2)', degradedTiming: '#(degraded)' }
    * karate.write(report, 'demo-timing.json')
    * karate.log('timing log →', 'target/demo-timing.json')

  @clickBbox @ignore
  Scenario: clickBbox
    # Canvas overlay → no DOM node per bbox. Coordinates only.
    # point is "x,y" in viewport pixels at the fixed demo window geometry.
    * def xy = point.split(',')
    * def x = parseInt(xy[0])
    * def y = parseInt(xy[1])
    * driver.mouse(x, y).click()
    * waitFor('[data-e2e=element-properties]')
