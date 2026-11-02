@ui @regression
Feature: UI — Parse view: Show all clears the element focus (#338)

  # Selecting an element dims every other bbox (focus mode); the Show all
  # button in the LAYERS bar leaves that mode. The overlay is a <canvas>, so
  # the dimming has no DOM to assert on — the Properties panel reads the same
  # shared focus, so its empty state is what proves the focus is gone.

  Background:
    * url baseUrl

  Scenario: Select an element → Show all → focus cleared, button disabled again
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId
    * def analysis = call read('classpath:common/helpers/analyze.feature') { docId: '#(docId)' }
    * match analysis.response.status == 'COMPLETED'

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitFor('[data-e2e=parse-tab]')
    * waitFor('[data-e2e=element-properties-empty]')

    # Nothing is focused yet, so there is nothing to clear.
    * waitFor('[data-e2e=parse-show-all]')
    * waitUntil("document.querySelector('[data-e2e=parse-show-all]').disabled")

    # Focus the first structure node: Properties fills in, the button enables.
    # waitUntil(js), not retry().until(...) — see the note in demo/ask-demo.feature.
    * waitFor('[data-e2e=tree-node-row]')
    * click('[data-e2e=tree-node-row]')
    * waitUntil("!document.querySelector('[data-e2e=element-properties-empty]')")
    * waitUntil("!document.querySelector('[data-e2e=parse-show-all]').disabled")

    # Show all: focus dropped — Properties back to empty, button disabled again.
    * click('[data-e2e=parse-show-all]')
    * waitFor('[data-e2e=element-properties-empty]')
    * waitUntil("document.querySelector('[data-e2e=parse-show-all]').disabled")

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
