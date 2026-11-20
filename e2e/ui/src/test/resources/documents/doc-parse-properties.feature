@ui @regression
Feature: UI — Parse view Properties panel (#265)

  # Selecting a node in the Structure tree fills the right-side
  # Properties panel.

  Background:
    * url baseUrl

  Scenario: Select a node → Properties populated
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

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
