@ui @critical
Feature: API — Doc chunk endpoint returns the canonical chunkset (#256, no 404)

  # Regression coverage for the #256 bug where /api/documents/{id}/chunks
  # returned 404 because the endpoint was not implemented backend-side.
  #
  # The doc-workspace chunk *view* was removed in 0.7.0 ("simplified document
  # workflow" — chunking/ingestion controls dropped from the workspace, which
  # is now preview-only, see CHANGELOG). This feature therefore covers the
  # chunk API contract end-to-end: upload -> analysis -> explicit rechunk ->
  # GET chunks (no 404, correct DocChunkResponse fields). The removed UI flow
  # (view-switcher / chunk-tab / layers-bar / chunks-panel) is dropped.
  #
  # The other specs that drove the removed workspace views (Ingest, Chunk,
  # Strategy popover, History drawer) were deleted in 0.7.4: those views no
  # longer exist, and `?mode=chunk` / `?mode=ingest` now resolve to the
  # default mode (shared/routing/modes.ts).
  #
  # Refreshed for #266: analysis and chunk are independent — running an
  # analysis no longer auto-promotes a canonical chunkset, so we POST
  # /api/documents/{id}/rechunk explicitly after the analysis completes.

  Background:
    * url baseUrl

  Scenario: Rechunk populates the canonical chunkset and GET chunks returns it (no 404)
    # 1. Setup via API: upload + run an analysis.
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    Given url baseUrl
    And path '/api/analyses'
    And request { documentId: '#(docId)', chunkingOptions: { chunkerType: 'hybrid', maxTokens: 256, mergePeers: true, repeatTableHeader: true } }
    When method POST
    Then status 200
    * def analysisId = response.id

    # Poll until the analysis is COMPLETED.
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

    # 4. Cleanup via API.
    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
