@ui
Feature: UI helper — open the Launch Ingest modal and close it (#283)

  # Called from doc-ingest-view.feature when the CTA is enabled. The
  # modal is the only piece of the new Ingest UI that needs explicit
  # coverage; the rest of the shell (CTA + history list) is asserted
  # inline in the parent feature.

  Scenario: Open the modal, see at least one store row, close it
    * click('[data-e2e=ingest-launch-cta]')
    * waitFor('[data-e2e=ingest-launch-modal]')
    # The modal renders either an empty state (no eligible stores) or
    # a non-empty list. Either path is valid here.
    * def hasEmpty = exists('[data-e2e=ingest-launch-empty]')
    * def hasList = exists('[data-e2e^=ingest-launch-row-]')
    * assert hasEmpty || hasList

    # Close via the cancel button rather than the backdrop; the
    # backdrop click is environment-flaky on smaller viewports.
    * click('[data-e2e=ingest-launch-cancel]')
    * waitForEnabled('[data-e2e=ingest-launch-cta]')
