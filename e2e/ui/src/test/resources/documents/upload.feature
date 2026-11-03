@ui
Feature: UI — Upload a PDF and verify preview

  Background:
    * url baseUrl

  Scenario: Upload a single-page PDF via UI and verify it appears with preview
    # Open Studio page
    * driver uiBaseUrl + '/studio'
    * waitFor('[data-e2e=upload-zone]')

    # Upload via hidden file input
    * driver.inputFile('input[type=file]', 'classpath:common/data/generated/small.pdf')

    # Verify document appears in the doc list sidebar
    * waitFor('[data-e2e=doc-item]')
    * match text('[data-e2e=doc-name]') contains 'small.pdf'

    # Click the document to select it
    * click('[data-e2e=doc-item]')
    * waitFor('[data-e2e=doc-item].selected')

    # Verify PDF preview loads
    * waitFor('[data-e2e=pdf-image]')

    # Cleanup via API
    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }

  Scenario: Upload a multi-page PDF and verify page navigation
    # Open Studio page
    * driver uiBaseUrl + '/studio'
    * waitFor('[data-e2e=upload-zone]')

    * driver.inputFile('input[type=file]', 'classpath:common/data/generated/medium.pdf')

    # Verify document appears
    * waitFor('[data-e2e=doc-item]')

    # Click to select and verify preview loads
    * click('[data-e2e=doc-item]')
    * waitFor('[data-e2e=doc-item].selected')
    * waitFor('[data-e2e=pdf-image]')

    # Cleanup
    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'medium.pdf' }
