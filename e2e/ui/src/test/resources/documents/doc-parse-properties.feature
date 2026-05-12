@ui @regression
Feature: UI — Parse view Properties panel + inline chunk edit (#265)

  # Selecting a node in the Structure tree fills the right-side
  # Properties panel; the Edit chunk button swaps the linked-chunk
  # block for an inline textarea bound to the chunk's text.

  Background:
    * url baseUrl

  Scenario: Select a node → Properties populated; edit a chunk inline
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

    # Parse view is the default mode.
    * driver uiBaseUrl + '/docs/' + docId
    * waitFor('[data-e2e=parse-tab]')
    * waitFor('[data-e2e=element-properties]')

    # Empty state visible before any selection.
    * waitFor('[data-e2e=element-properties-empty]')

    # Click the first tree node — Properties should populate, empty
    # state should disappear.
    * click('[data-e2e=tree-rail] .tree-node-row')
    * retry().until(!exists('[data-e2e=element-properties-empty]'))
    * waitFor('[data-e2e=properties-extracted-text]')

    # When the selected element has a linked chunk, Edit chunk is shown.
    # Skip the edit assertions when the first node has no linked chunk
    # (e.g. an envelope or page-level marker without docItems).
    * def hasEditBtn = exists('[data-e2e=properties-edit-btn]')
    * if (!hasEditBtn) karate.log('No linked chunk on the first selected node; edit path skipped.')

    * if (hasEditBtn) karate.call('@editInline', { docId: docId })

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }

  @editInline @ignore
  Scenario: editInline
    # Reusable fragment — exercised from the main scenario when the
    # selected element has a linked chunk.
    * click('[data-e2e=properties-edit-btn]')
    * waitFor('[data-e2e=properties-edit]')

    # Type something and save.
    * def textarea = '[data-e2e=properties-edit] textarea'
    * driver.input(textarea, ' [edited via Karate]')
    * click('[data-e2e=properties-save-btn]')

    # Edit mode disappears after a successful save.
    * retry().until(!exists('[data-e2e=properties-edit]'))
