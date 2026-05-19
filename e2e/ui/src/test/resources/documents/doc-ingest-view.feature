@ui @regression
Feature: UI — Ingest view shell + history-driven design (#225, redesigned #283)

  # The third tab in the workspace switcher (Parse | Chunk | Ingest)
  # surfaces a primary "Launch ingest" CTA + the document's push
  # history. Per-store state lives inside the launch modal — the
  # tab itself shows only the timeline.
  #
  # On a fresh document we expect either:
  #   - no-stores empty state (no stores configured in the test env), or
  #   - no-history empty state (stores exist but no pushes yet).
  # Both states are valid Karate-side; we just assert the tab renders
  # and the CTA + at least one empty-state surface is visible.

  Background:
    * url baseUrl

  Scenario: Ingest tab renders the CTA + history shell
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    # Doc + at least one completed analysis so the workspace has data.
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

    # Open the workspace on the Ingest mode.
    * driver uiBaseUrl + '/docs/' + docId + '?mode=ingest'
    * waitFor('[data-e2e=view-switcher]')
    * waitFor('[data-e2e=ingest-tab]')
    * waitFor('[data-e2e=ingest-launch-cta]')

    # Exactly one of the three states is visible: error / no-stores /
    # no-history / history. We assert at least one of the safe ones.
    * def hasHistory = exists('[data-e2e=ingest-history]')
    * def hasNoStores = exists('[data-e2e=ingest-no-stores]')
    * def hasNoHistory = exists('[data-e2e=ingest-no-history]')
    * assert hasHistory || hasNoStores || hasNoHistory

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }

  Scenario: Launch CTA opens the modal (when stores are available)
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    * driver uiBaseUrl + '/docs/' + docId + '?mode=ingest'
    * waitFor('[data-e2e=ingest-tab]')
    * waitFor('[data-e2e=ingest-launch-cta]')

    # Only attempt the modal flow if the CTA is enabled (stores exist).
    * def ctaDisabled = script('[data-e2e=ingest-launch-cta]', "el => el.disabled")
    * if (!ctaDisabled) karate.call('classpath:documents/_open-launch-modal.feature', { docId: docId })

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }

  Scenario: ?mode=compare deep link aliases to ?mode=ingest
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    * driver uiBaseUrl + '/docs/' + docId + '?mode=compare'
    * waitFor('[data-e2e=ingest-tab]')

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
