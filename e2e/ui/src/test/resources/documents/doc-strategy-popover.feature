@ui @regression
Feature: UI — Strategy popover rechunks from the Chunk view (#268)

  # The Strategy button in the Chunk panel opens a popover with the
  # chunker options. Apply triggers POST /rechunk and replaces the
  # canonical chunkset. Setup is API-driven; the UI portion only
  # exercises the popover form.

  Background:
    * url baseUrl

  Scenario: Open Strategy, change max tokens, apply, chunks refresh
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    Given url baseUrl
    And path '/api/analyses'
    And request { documentId: '#(docId)', chunkingOptions: { chunkerType: 'hybrid', maxTokens: 512, mergePeers: true, repeatTableHeader: true } }
    When method POST
    Then status 200
    * def analysisId = response.id

    Given url baseUrl
    And path '/api/analyses', analysisId
    And retry until response.status == 'COMPLETED' || response.status == 'FAILED'
    When method GET
    Then status 200
    And match response.status == 'COMPLETED'

    * driver uiBaseUrl + '/docs/' + docId + '?mode=chunk'
    * waitFor('[data-e2e=chunk-tab]')
    * waitFor('[data-e2e=chunks-panel]')

    # Snapshot the current count of cards before rechunking.
    * def before = karate.sizeOf(locateAll('[data-e2e=chunks-panel-list] li'))
    * assert before > 0

    # Open Strategy → form visible.
    * click('[data-e2e=strategy-btn]')
    * waitFor('[data-e2e=strategy-popover]')
    * waitFor('[data-e2e=strategy-form]')

    # Change max tokens to a smaller value to force a new chunking pass.
    * driver.input('[data-e2e=strategy-max-tokens]', '128')

    # Apply → no manual edits so no confirm step; popover closes.
    * click('[data-e2e=strategy-apply]')
    * retry().until(!exists('[data-e2e=strategy-popover]'))

    # Chunks panel still renders (smaller max_tokens should usually
    # produce equal-or-more chunks; we just assert presence).
    * waitFor('[data-e2e=chunks-panel-list]')
    * assert karate.sizeOf(locateAll('[data-e2e=chunks-panel-list] li')) > 0

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
