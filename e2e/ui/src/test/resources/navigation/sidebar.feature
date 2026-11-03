@ui
Feature: UI — Sidebar navigation

  # The sidebar has five entries (shared/ui/AppSidebar.vue): Home, Documents,
  # Analyses, Runs, Settings. Each one is `nav-<key>`, and the entry of the
  # current section carries the `active` class.

  Scenario: Navigate through all sidebar links
    * driver uiBaseUrl
    * waitFor('[data-e2e=sidebar]')
    * match karate.sizeOf(locateAll('[data-e2e^=nav-]')) == 5

    * click('[data-e2e=nav-docs]')
    * waitUntil("location.pathname == '/docs'")
    * waitUntil("document.querySelector('[data-e2e=nav-docs]').classList.contains('active')")

    * click('[data-e2e=nav-analyses]')
    * waitUntil("location.pathname == '/analyses'")
    * waitUntil("document.querySelector('[data-e2e=nav-analyses]').classList.contains('active')")

    * click('[data-e2e=nav-runs]')
    * waitUntil("location.pathname == '/runs'")
    * waitUntil("document.querySelector('[data-e2e=nav-runs]').classList.contains('active')")

    * click('[data-e2e=nav-settings]')
    * waitUntil("location.pathname == '/settings'")
    * waitUntil("document.querySelector('[data-e2e=nav-settings]').classList.contains('active')")

    * click('[data-e2e=nav-home]')
    * waitUntil("location.pathname == '/'")

  Scenario: Toggle sidebar collapse and expand
    * driver uiBaseUrl
    * waitFor('[data-e2e=sidebar]')

    # Sidebar should start with .open class
    * match attribute('[data-e2e=sidebar]', 'class') contains 'open'

    # Click burger menu to collapse
    * click('[data-e2e=burger-btn]')
    * waitUntil("!document.querySelector('[data-e2e=sidebar]').classList.contains('open')")

    # Toggle back to expand
    * click('[data-e2e=burger-btn]')
    * waitUntil("document.querySelector('[data-e2e=sidebar]').classList.contains('open')")
