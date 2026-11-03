@ui
Feature: UI — Reasoning feature flag

  # Reasoning (Ask) no longer has a sidebar entry or a page of its own (#303):
  # it is a tab of the Parse view, on /analyses/:id, shown only when the
  # `reasoning` flag is on, i.e. ASK_MODE=visible and `reasoningAvailable` on
  # /api/health (REASONING_ENABLED=true with docling-agent installed).
  #
  # These scenarios run against the default CI backend, where both are off.
  # On a backend with reasoning wired, the @reasoning-off scenario stops at
  # its first check, the /api/health precondition, before any UI step.

  @reasoning-off
  Scenario: Parse view has no Ask tab while the runner isn't wired
    Given url baseUrl
    And path '/api/health'
    When method GET
    Then status 200
    * match response.reasoningAvailable == false

    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId
    * def analysis = call read('classpath:common/helpers/analyze.feature') { docId: '#(docId)' }
    * match analysis.response.status == 'COMPLETED'

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitFor('[data-e2e=parse-tab]')
    * waitFor('[data-e2e=element-properties]')
    # Without the flag the right panel is Properties alone: no Properties/Ask tabs.
    * match karate.sizeOf(locateAll('[data-e2e=ask-tab]')) == 0
    * match karate.sizeOf(locateAll('[data-e2e=props-tab]')) == 0

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }

  Scenario: Retired /reasoning deep links land on the documents
    # Shared links to the old standalone page must not 404 (app/router/routes.ts).
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    * driver uiBaseUrl + '/reasoning'
    * waitUntil("location.pathname == '/docs'")

    * driver uiBaseUrl + '/reasoning/' + docId
    * waitUntil("location.pathname == '/docs/" + docId + "'")
    * waitFor('[data-e2e=document-viewer]')

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }

  # ASK_MODE is unset on the CI backend, so Ask is hidden: Settings must not
  # offer the Reasoning section, where Ask would otherwise be turned on.
  @ask-hidden
  Scenario: Settings has no Reasoning section while ASK_MODE hides Ask
    * driver uiBaseUrl + '/settings'
    * waitFor('[data-e2e=settings-panel]')
    * match karate.sizeOf(locateAll('[data-e2e=reasoning-config-section]')) == 0
