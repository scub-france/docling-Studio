@ui @critical
Feature: UI — Doc tab chunk mode renders canonical chunks (#256)

  # Regression coverage for the bug where opening the chunks tab on a
  # document returned 404 because /api/documents/{id}/chunks was not
  # implemented backend-side. Setup is API-driven (upload + analyse) so
  # the test is fast and deterministic; the UI portion only exercises
  # navigation + chunk rendering, not the parse pipeline.

  Background:
    * url baseUrl

  Scenario: Open the chunks tab and see the canonical chunkset (no 404)
    # 1. Setup via API: upload + run an analysis (with chunking) and wait
    #    until the doc-centric chunkset gets promoted by the analysis hook.
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    Given url baseUrl
    And path '/api/analyses'
    And request { documentId: '#(docId)', chunkingOptions: { chunkerType: 'hybrid', maxTokens: 256, mergePeers: true, repeatTableHeader: true } }
    When method POST
    Then status 200
    * def analysisId = response.id

    # Poll until the analysis is COMPLETED (chunks get promoted in the
    # same step via AnalysisService → ChunkService.promote_from_analysis).
    Given url baseUrl
    And path '/api/analyses', analysisId
    And retry until response.status == 'COMPLETED' || response.status == 'FAILED'
    When method GET
    Then status 200
    And match response.status == 'COMPLETED'

    # 2. Sanity-check the new endpoint over HTTP — proves the 404 is gone.
    Given url baseUrl
    And path '/api/documents', docId, 'chunks'
    When method GET
    Then status 200
    And assert karate.sizeOf(response) > 0

    # 3. Drive the UI: open the workspace page and click the chunks tab.
    * driver uiBaseUrl + '/docs/' + docId
    * waitFor('[data-e2e=tab-strip]')
    * click('[data-e2e=tab-chunks]')

    # 4. Verify the chunks list rendered (no 404 banner, chunk-list visible).
    * waitFor('[data-e2e=chunks-editor]')
    * waitFor('[data-e2e=chunk-list]')
    * assert karate.sizeOf(locateAll('[data-e2e=chunk-list] .chunk-card')) > 0

    # 5. Cleanup via API.
    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
