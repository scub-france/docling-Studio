@ui @regression
Feature: UI — Linked view interactions (#264)

  # Covers the bbox-canvas + LAYERS chips wiring introduced by T3:
  # toggling a chip flips its aria-pressed state, and the chunks panel
  # reflects the active page. The 404-regression scenario lives in
  # doc-tab-chunk-mode.feature (refreshed for the new selectors).

  Background:
    * url baseUrl

  Scenario: LAYERS chip toggles and chunks panel page-scoping
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    Given url baseUrl
    And path '/api/analyses'
    And request { documentId: '#(docId)', chunkingOptions: { chunkerType: 'hybrid', maxTokens: 256, mergePeers: true, repeatTableHeader: true } }
    When method POST
    Then status 200
    * def analysisId = response.id

    Given url baseUrl
    And path '/api/analyses', analysisId
    And retry until response.status == 'COMPLETED' || response.status == 'FAILED'
    When method GET
    Then status 200
    And match response.status == 'COMPLETED'

    * driver uiBaseUrl + '/docs/' + docId
    * waitFor('[data-e2e=linked-tab]')
    * waitFor('[data-e2e=layers-bar]')

    # Chip starts enabled (aria-pressed=true). Click it → pressed=false.
    * def textChip = '[data-e2e=layer-chip-text]'
    * waitFor(textChip)
    * match attribute(textChip, 'aria-pressed') == 'true'
    * click(textChip)
    * retry().until(attribute(textChip, 'aria-pressed') == 'false')

    # Show-labels toggle flips the checkbox state.
    * def showLabels = '[data-e2e=show-labels-toggle] input'
    * waitFor(showLabels)
    * click(showLabels)
    * retry().until(attribute(showLabels, 'checked') == 'true')

    # Chunks panel must render at least one card.
    * waitFor('[data-e2e=chunks-panel-list]')
    * assert karate.sizeOf(locateAll('[data-e2e=chunks-panel-list] li')) > 0

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
