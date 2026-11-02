@ui @regression
Feature: UI — MCP section of the settings panel (#364)

  # Runs against the default CI backend: MCP_ENABLED unset, so /mcp is
  # mounted (MCP is on by default), and DEPLOYMENT_MODE self-hosted. The live
  # budgets are editable whether or not the HTTP transport is mounted (they
  # also reach the stdio server). Overrides, the on/off switch included, are
  # cleared through the API before each scenario, so no row survives the run.

  Background:
    Given url baseUrl
    And path '/api/config/mcp'
    When method DELETE
    Then status 200

  Scenario: Change the read ceiling, see its source, reset to the environment
    * driver uiBaseUrl + '/settings'
    * waitFor('[data-e2e=mcp-config-section]')
    * waitFor('[data-e2e=mcp-config-status]')
    * waitFor('[data-e2e=mcp-config-restart-only]')
    * match karate.sizeOf(locateAll('[data-e2e=mcp-config-source-max-read-tokens]')) == 0

    # Save a new ceiling: that field, and only that one, reports a db override.
    * clear('[data-e2e=mcp-config-max-read-tokens]')
    * input('[data-e2e=mcp-config-max-read-tokens]', '1500')
    * click('[data-e2e=mcp-config-save]')
    * waitFor('[data-e2e=mcp-config-source-max-read-tokens]')
    * match karate.sizeOf(locateAll('[data-e2e=mcp-config-source-max-rounds]')) == 0
    * match karate.sizeOf(locateAll('[data-e2e=mcp-config-source-base-url]')) == 0

    # The backend serves it from now on.
    Given url baseUrl
    And path '/api/config/mcp'
    When method GET
    Then status 200
    And match response.maxReadTokens == 1500
    And match response.sources == { maxRounds: 'env', maxReadTokens: 'db', studioBaseUrl: 'env', enabled: 'env' }

    # Reset: the badge goes, the environment value comes back.
    * click('[data-e2e=mcp-config-reset]')
    * retry().until(!exists('[data-e2e=mcp-config-source-max-read-tokens]'))

    Given url baseUrl
    And path '/api/config/mcp'
    When method GET
    Then status 200
    And match response.sources.maxReadTokens == 'env'

  Scenario: An out-of-bounds value is refused and nothing is stored
    * driver uiBaseUrl + '/settings'
    * waitFor('[data-e2e=mcp-config-max-rounds]')
    * clear('[data-e2e=mcp-config-max-rounds]')
    * input('[data-e2e=mcp-config-max-rounds]', '0')
    * click('[data-e2e=mcp-config-save]')
    * waitFor('[data-e2e=mcp-config-save-error]')
    * match text('[data-e2e=mcp-config-save-error]') contains 'max_rounds'

    Given url baseUrl
    And path '/api/config/mcp'
    When method GET
    Then status 200
    And match response.sources.maxRounds == 'env'

  Scenario: Turn the server off and back on, with no restart
    * driver uiBaseUrl + '/settings'
    * waitFor('[data-e2e=mcp-config-switch]')
    * match karate.sizeOf(locateAll('[data-e2e=mcp-config-source-enabled]')) == 0

    # Off: the switch is stored, and /mcp answers 503 before reaching the server.
    * match attribute('[data-e2e=mcp-config-switch]', 'aria-checked') == 'true'
    * click('[data-e2e=mcp-config-switch]')
    * waitFor('[data-e2e=mcp-config-source-enabled]')

    Given url baseUrl
    And path '/mcp'
    And header Accept = 'application/json, text/event-stream'
    And request { jsonrpc: '2.0', id: 1, method: 'ping' }
    When method POST
    Then status 503
    And match response.error.message contains 'turned off'

    # Back on: the override goes, the environment value comes back.
    * click('[data-e2e=mcp-config-switch]')
    * retry().until(!exists('[data-e2e=mcp-config-source-enabled]'))

    Given url baseUrl
    And path '/api/config/mcp'
    When method GET
    Then status 200
    And match response.enabled == true
    And match response.sources.enabled == 'env'
