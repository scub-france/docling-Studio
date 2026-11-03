@critical @ui
Feature: UI — Delete a document

  Background:
    * url baseUrl

  Scenario: Upload a document, then delete it via UI
    # Setup via API — upload a doc
    * def result = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = result.docId

    # Open Studio page
    * driver uiBaseUrl + '/studio'
    * waitFor('[data-e2e=doc-item]')

    # Count docs before deletion
    * def countBefore = karate.sizeOf(locateAll('[data-e2e=doc-item]'))

    # Select the first doc, hover to reveal delete, click it
    * click('[data-e2e=doc-item]')
    * waitFor('[data-e2e=doc-item].selected')
    * mouse('[data-e2e=doc-item].selected').go()
    * waitFor('[data-e2e=doc-delete]')
    * click('[data-e2e=doc-delete]')

    # Wait for the doc count to decrease (UI confirmation). waitUntil, not
    # script(): script() runs once and never waits (e2e/CONVENTIONS.md).
    * retry(10, 500).waitUntil("document.querySelectorAll('[data-e2e=doc-item]').length < " + countBefore)

    # Cleanup — ensure our uploaded doc is gone regardless
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }
