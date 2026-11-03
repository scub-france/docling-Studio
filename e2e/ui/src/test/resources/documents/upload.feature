@ui
Feature: UI — Upload a PDF and verify preview

  # The upload selects the new document, so every check targets the selected
  # row and the id the upload created, never the first row of the list: a
  # document left in the base by an earlier run must not decide the outcome.

  Background:
    * url baseUrl

  Scenario: Upload a single-page PDF via UI and verify it appears with preview
    * def before = call read('classpath:common/helpers/document-ids.feature') { filename: 'small.pdf' }

    # Open Studio page
    * driver uiBaseUrl + '/studio'
    * waitFor('[data-e2e=upload-zone]')

    # Upload via hidden file input
    * driver.inputFile('input[type=file]', 'classpath:common/data/generated/small.pdf')

    # The uploaded document is listed and selected
    * waitFor('[data-e2e=doc-item].selected')
    * match text('[data-e2e=doc-item].selected [data-e2e=doc-name]') == 'small.pdf'

    # The upload created exactly one document
    * def after = call read('classpath:common/helpers/document-ids.feature') { filename: 'small.pdf' }
    * def created = karate.filter(after.ids, function(id){ return before.ids.indexOf(id) == -1 })
    * match karate.sizeOf(created) == 1

    # Verify PDF preview loads
    * waitFor('[data-e2e=pdf-image]')

    # Cleanup via API
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(created[0])' }

  Scenario: Upload a multi-page PDF and verify page navigation
    * def before = call read('classpath:common/helpers/document-ids.feature') { filename: 'medium.pdf' }

    # Open Studio page
    * driver uiBaseUrl + '/studio'
    * waitFor('[data-e2e=upload-zone]')

    * driver.inputFile('input[type=file]', 'classpath:common/data/generated/medium.pdf')

    # Verify the uploaded document is listed and selected, and its preview loads
    * waitFor('[data-e2e=doc-item].selected')
    * match text('[data-e2e=doc-item].selected [data-e2e=doc-name]') == 'medium.pdf'
    * waitFor('[data-e2e=pdf-image]')

    # The upload created exactly one document
    * def after = call read('classpath:common/helpers/document-ids.feature') { filename: 'medium.pdf' }
    * def created = karate.filter(after.ids, function(id){ return before.ids.indexOf(id) == -1 })
    * match karate.sizeOf(created) == 1

    # Cleanup
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(created[0])' }
