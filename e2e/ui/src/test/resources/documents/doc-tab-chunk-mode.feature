@ui @critical
Feature: UI — Doc Chunk view renders canonical chunks (#256, refreshed #263 / #264 / #266)

  # Regression coverage for the bug where opening the chunks tab on a
  # document returned 404 because /api/documents/{id}/chunks was not
  # implemented backend-side. After #263 the tab strip became a top-right
  # switcher; after #264 the page restructured into LayersBar +
  # PagePreviewWithOverlay + ChunksPanel and the mode was renamed
  # `linked` → `chunk` (Parse owns the extraction view, Chunk owns the
  # chunk-aligned preview). Selectors and ?mode= values updated.
  #
  # Refreshed for #266: analysis and chunk are now independent — running
  # an analysis no longer auto-promotes a canonical chunkset. The test
  # therefore POSTs /api/documents/{id}/rechunk explicitly after the
  # analysis completes, mirroring what the Strategy popover (#268) does
  # in the UI.

  Background:
    * url baseUrl

  Scenario: Open the Linked view and see the canonical chunkset (no 404)
    # 1. Setup via API: upload + run an analysis. Since #266 the analysis
    #    no longer implicitly creates the canonical chunkset, so we ask
    #    for chunking on the analysis (kept for parity with the legacy
    #    payload) and then trigger an explicit rechunk in step 2.
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    Given url baseUrl
    And path '/api/analyses'
    And request { documentId: '#(docId)', chunkingOptions: { chunkerType: 'hybrid', maxTokens: 256, mergePeers: true, repeatTableHeader: true } }
    When method POST
    Then status 200
    * def analysisId = response.id

    # Poll until the analysis is COMPLETED. After #266 this only produces
    # per-analysis chunks_json; the canonical /api/documents/{id}/chunks
    # set is populated by the explicit rechunk call below.
    Given url baseUrl
    And path '/api/analyses', analysisId
    And retry until response.status == 'COMPLETED' || response.status == 'FAILED'
    When method GET
    Then status 200
    And match response.status == 'COMPLETED'

    # 2. Promote chunks explicitly via the doc-centric endpoint — same
    #    contract the UI uses from the Strategy popover (#268).
    Given url baseUrl
    And path '/api/documents', docId, 'rechunk'
    And request { chunkingOptions: { chunkerType: 'hybrid', maxTokens: 256, mergePeers: true, repeatTableHeader: true } }
    When method POST
    Then status 200
    And assert karate.sizeOf(response) > 0

    # 3. Sanity-check the chunks endpoint over HTTP — proves the 404 is gone
    #    AND that the new DocChunkResponse fields (bboxes, docItems) land.
    Given url baseUrl
    And path '/api/documents', docId, 'chunks'
    When method GET
    Then status 200
    And assert karate.sizeOf(response) > 0
    And match each response contains { bboxes: '#array', docItems: '#array' }

    # 4. Drive the UI: open the workspace on the Chunk view directly.
    * driver uiBaseUrl + '/docs/' + docId + '?mode=chunk'
    * waitFor('[data-e2e=view-switcher]')
    * waitFor('[data-e2e=chunk-tab]')

    # 5. Verify the LAYERS bar + chunks panel rendered.
    * waitFor('[data-e2e=layers-bar]')
    * waitFor('[data-e2e=chunks-panel]')
    * waitFor('[data-e2e=chunks-panel-list]')
    * assert karate.sizeOf(locateAll('[data-e2e=chunks-panel-list] li')) > 0

    # 6. Cleanup via API.
    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
