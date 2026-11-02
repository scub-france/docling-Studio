@ui
Feature: UI — Reasoning feature flag

  # The Reasoning sidebar entry must be hidden when the backend is not wired
  # to expose the live runner. This test runs against the default CI backend
  # (REASONING_ENABLED unset → false), so `reasoningAvailable` from
  # /api/health is false and the sidebar entry must not render.
  #
  # When REASONING_ENABLED=true on the backend with docling-agent installed,
  # this scenario will fail — flip the assertion or drop the @reasoning-off
  # tag in CI accordingly.

  @reasoning-off
  Scenario: Sidebar does not show Reasoning when the runner isn't wired
    * driver uiBaseUrl
    * waitFor('[data-e2e=sidebar]')

    # The other nav items must still render
    * waitFor('[data-e2e=nav-studio]')
    * waitFor('[data-e2e=nav-documents]')

    # nav-reasoning must NOT be present (v-if="reasoningEnabled" gates it on
    # `reasoningAvailable` in the health response)
    * match karate.sizeOf(locateAll('[data-e2e=nav-reasoning]')) == 0

  @reasoning-off
  Scenario: /reasoning route is reachable but flag-driven UI gates the entry point
    * driver uiBaseUrl + '/reasoning'

    # The route is registered in the SPA router so a deep-link doesn't 404,
    # but the sidebar nav-reasoning entry stays hidden — users can't reach
    # the page through normal navigation when the runner is disabled.
    * waitFor('[data-e2e=sidebar]')
    * match karate.sizeOf(locateAll('[data-e2e=nav-reasoning]')) == 0

  # ASK_MODE is unset on the CI backend, so Ask is hidden: Settings must not
  # offer the Reasoning section, where Ask would otherwise be turned on.
  @ask-hidden
  Scenario: Settings has no Reasoning section while ASK_MODE hides Ask
    * driver uiBaseUrl + '/settings'
    * waitFor('[data-e2e=settings-panel]')
    * match karate.sizeOf(locateAll('[data-e2e=reasoning-config-section]')) == 0
