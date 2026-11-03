@ui @regression
Feature: UI — Parse view: selecting a structure node fills the Properties panel (#265)

  # The Parse view only exists on the saved analysis page (/analyses/:id): the
  # document workspace (/docs/:id) shows the document without it. Selecting a
  # node in the Structure tree fills the right-side Properties panel. The page
  # shows a saved analysis read-only, so the inline "Edit chunk" action of
  # #265 is not offered there.

  Background:
    * url baseUrl

  Scenario: Select a node → Properties populated, no inline chunk edit
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    # Analyse with chunks: the edit button lives in the Linked chunk section,
    # which only renders for an element a chunk covers. The hierarchical
    # chunker needs no tokenizer, so nothing is fetched from Hugging Face.
    Given url baseUrl
    And path '/api/analyses'
    And request { documentId: '#(docId)', chunkingOptions: { chunkerType: 'hierarchical' } }
    When method POST
    Then status 200
    * def analysisId = response.id

    Given url baseUrl
    And path '/api/analyses', analysisId
    And retry until response.status == 'COMPLETED' || response.status == 'FAILED'
    When method GET
    Then status 200
    And match response.status == 'COMPLETED'

    # An element the first chunk covers
    * json chunks = response.chunksJson
    * assert karate.sizeOf(chunks) > 0
    * def chunkedRef = chunks[0].docItems[0].selfRef

    * driver uiBaseUrl + '/analyses/' + analysisId
    * waitFor('[data-e2e=parse-tab]')
    * waitFor('[data-e2e=element-properties]')

    # Empty state visible before any selection.
    * waitFor('[data-e2e=element-properties-empty]')

    # Click the first tree node: Properties fills in, the empty state goes.
    * waitFor('[data-e2e=tree-node-row]')
    * click('[data-e2e=tree-node-row]')
    * waitUntil("!document.querySelector('[data-e2e=element-properties-empty]')")
    * waitFor('[data-e2e=properties-extracted-text]')

    # Read-only: open the chunked element (deep link, as a citation does).
    # Its Linked chunk section shows, without the inline chunk editor.
    * driver uiBaseUrl + '/analyses/' + analysisId + '?ref=' + encodeURIComponent(chunkedRef)
    * waitFor('[data-e2e=properties-linked-chunk]')
    * match karate.sizeOf(locateAll('[data-e2e=properties-edit-btn]')) == 0

    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }
