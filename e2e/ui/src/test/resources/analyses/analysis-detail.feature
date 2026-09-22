@ui @regression
Feature: UI — Saved analysis detail page

  # The detail page shows one saved analysis read-only: no New analysis
  # action, downloads scoped to the analysis on screen rather than the
  # document's latest one, and a link back to the document workspace.

  Background:
    * url baseUrl

  Scenario: Older analysis → read-only view, scoped export, link to its document
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    # Two analyses over the same document; the older one is the one we open.
    Given url baseUrl
    And path '/api/analyses'
    And request { documentId: '#(docId)', chunkingOptions: { chunkerType: 'hybrid', maxTokens: 512, mergePeers: true, repeatTableHeader: true } }
    When method POST
    Then status 200
    * def analysisOldId = response.id

    Given url baseUrl
    And path '/api/analyses', analysisOldId
    And retry until response.status == 'COMPLETED' || response.status == 'FAILED'
    When method GET
    Then status 200
    And match response.status == 'COMPLETED'

    Given url baseUrl
    And path '/api/analyses'
    And request { documentId: '#(docId)', chunkingOptions: { chunkerType: 'hybrid', maxTokens: 1024, mergePeers: true, repeatTableHeader: true } }
    When method POST
    Then status 200
    * def analysisNewId = response.id

    Given url baseUrl
    And path '/api/analyses', analysisNewId
    And retry until response.status == 'COMPLETED' || response.status == 'FAILED'
    When method GET
    Then status 200
    And match response.status == 'COMPLETED'

    # The export honours the requested analysis — an unknown one is refused
    # instead of silently falling back to the latest.
    Given url baseUrl
    And path '/api/documents', docId, 'export'
    And param format = 'md'
    And param analysisId = analysisOldId
    When method GET
    Then status 200

    Given url baseUrl
    And path '/api/documents', docId, 'export'
    And param format = 'md'
    And param analysisId = 'non-existent-id'
    When method GET
    Then status 404

    # UI — the detail page is read-only and links back to its document.
    * driver uiBaseUrl + '/analyses/' + analysisOldId
    * waitFor('[data-e2e=parse-tab]')
    * assert !exists('[data-e2e=parse-new-analysis]')
    * click('[data-e2e=analysis-open-document]')
    * waitForUrl('/docs/' + docId)
    * waitFor('[data-e2e=document-viewer]')

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
