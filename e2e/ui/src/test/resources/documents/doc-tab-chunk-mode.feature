@ui @critical
Feature: UI — Doc Linked view renders canonical chunks (#256, refreshed #263 / #264)

  # Regression coverage for the bug where opening the chunks tab on a
  # document returned 404 because /api/documents/{id}/chunks was not
  # implemented backend-side. After #263 the tab strip became a top-right
  # switcher and the mode renamed chunks → linked; after #264 the page
  # restructured into LayersBar + PagePreviewWithOverlay + ChunksPanel.
  # The selectors were refreshed accordingly. Setup is API-driven so the
  # test stays fast and deterministic.

  Background:
    * url baseUrl

  Scenario: Open the Linked view and see the canonical chunkset (no 404)
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

    # 2. Sanity-check the chunks endpoint over HTTP — proves the 404 is gone
    #    AND that the new DocChunkResponse fields (bboxes, docItems) land.
    Given url baseUrl
    And path '/api/documents', docId, 'chunks'
    When method GET
    Then status 200
    And assert karate.sizeOf(response) > 0
    And match each response contains { bboxes: '#array', docItems: '#array' }

    # 3. Drive the UI: open the workspace, default mode is Linked.
    * driver uiBaseUrl + '/docs/' + docId
    * waitFor('[data-e2e=view-switcher]')
    * waitFor('[data-e2e=linked-tab]')

    # 4. Verify the LAYERS bar + chunks panel rendered.
    * waitFor('[data-e2e=layers-bar]')
    * waitFor('[data-e2e=chunks-panel]')
    * waitFor('[data-e2e=chunks-panel-list]')
    * assert karate.sizeOf(locateAll('[data-e2e=chunks-panel-list] li')) > 0

    # 5. Cleanup via API.
    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
