@ui
Feature: UI — Settings sections fold and unfold

  # Every section starts open but the MCP environment table. What the viewer
  # folds is kept in the browser, so the scenario clears it at the end: the
  # other Settings scenarios click inside sections that must be open.

  Scenario: Fold every section, find the fold after a reload, unfold them all
    * driver uiBaseUrl + '/settings'
    * waitFor('[data-e2e=settings-group-mcp-advanced-toggle]')
    * match attribute('[data-e2e=settings-group-general-toggle]', 'aria-expanded') == 'true'
    * match attribute('[data-e2e=settings-group-mcp-advanced-toggle]', 'aria-expanded') == 'false'

    # Fold everything.
    * click('[data-e2e=settings-toggle-all]')
    * waitUntil("document.querySelector('[data-e2e=settings-group-general-toggle]').getAttribute('aria-expanded') == 'false'")
    * match attribute('[data-e2e=settings-group-mcp-toggle]', 'aria-expanded') == 'false'
    * match attribute('[data-e2e=settings-group-mcp-budgets-toggle]', 'aria-expanded') == 'false'

    # The fold survives a reload.
    * refresh()
    * waitFor('[data-e2e=settings-group-mcp-advanced-toggle]')
    * match attribute('[data-e2e=settings-group-general-toggle]', 'aria-expanded') == 'false'

    # One section opens on its own.
    * click('[data-e2e=settings-group-general-toggle]')
    * waitUntil("document.querySelector('[data-e2e=settings-group-general-toggle]').getAttribute('aria-expanded') == 'true'")
    * match attribute('[data-e2e=settings-group-mcp-toggle]', 'aria-expanded') == 'false'

    # Fold all, then unfold all: every section opens, the environment table too.
    * click('[data-e2e=settings-toggle-all]')
    * click('[data-e2e=settings-toggle-all]')
    * waitUntil("document.querySelector('[data-e2e=settings-group-mcp-advanced-toggle]').getAttribute('aria-expanded') == 'true'")
    * match attribute('[data-e2e=settings-group-mcp-budgets-toggle]', 'aria-expanded') == 'true'

    # Leave the defaults for the next scenario.
    * script("localStorage.removeItem('docling-settings-collapsed')")
