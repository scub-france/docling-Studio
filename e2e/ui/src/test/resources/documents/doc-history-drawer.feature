@ui @regression
Feature: UI — History drawer lists analyses and switches the active one (#267)

  # Two analyses are created over the same document; the drawer should
  # surface both and "Set as current" should activate the older one
  # without leaving the workspace.

  Background:
    * url baseUrl

  Scenario: Two analyses → drawer lists both → set the older as current
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    # Analysis #1
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

    # Analysis #2 — bigger max_tokens so we can tell them apart.
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

    # UI — open the workspace, click History.
    * driver uiBaseUrl + '/docs/' + docId
    * waitFor('[data-e2e=parse-tab]')
    * click('[data-e2e=history-btn]')
    * waitFor('[data-e2e=history-drawer]')
    * waitFor('[data-e2e=history-list]')

    # The newer analysis is the default active one.
    * waitFor('[data-e2e=history-item-' + analysisNewId + '].active')

    # Switch to the older analysis.
    * click('[data-e2e=history-set-current-' + analysisOldId + ']')
    * retry().until(!exists('[data-e2e=history-drawer]'))

    # Re-open History → the older one is now active.
    * click('[data-e2e=history-btn]')
    * waitFor('[data-e2e=history-item-' + analysisOldId + '].active')

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
