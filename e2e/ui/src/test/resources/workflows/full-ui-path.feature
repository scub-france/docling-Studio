@ui
Feature: UI — Full happy path via browser

  Background:
    * url baseUrl

  Scenario: Complete workflow — upload, analyze, verify results, rechunk, delete — all via UI
    # The steps target the uploaded document (the selected row, and the id the
    # upload created), never the first row: documents left in the base by an
    # earlier run must not decide the outcome.
    * def before = call read('classpath:common/helpers/document-ids.feature') { filename: 'medium.pdf' }

    # Step 1: Open Studio page
    * driver uiBaseUrl + '/studio'
    * waitFor('[data-e2e=upload-zone]')

    # Step 2: Upload a PDF via UI
    * driver.inputFile('input[type=file]', 'classpath:common/data/generated/medium.pdf')

    # Step 3: The upload lists the document and selects it
    * waitFor('[data-e2e=doc-item].selected')
    * match text('[data-e2e=doc-item].selected [data-e2e=doc-name]') == 'medium.pdf'

    # Step 4: The upload created exactly one document
    * def after = call read('classpath:common/helpers/document-ids.feature') { filename: 'medium.pdf' }
    * def created = karate.filter(after.ids, function(id){ return before.ids.indexOf(id) == -1 })
    * match karate.sizeOf(created) == 1
    * def docId = created[0]

    # Step 5: Verify Configure mode is active
    * waitFor('[data-e2e~=configure-btn].active')

    # Step 6: Run the analysis
    * click('[data-e2e=run-btn]')

    # Step 7: Wait for analysis to complete
    * call read('classpath:common/helpers/ui-wait-analysis.feature')

    # Step 8: Verify results — tabs and content
    * waitFor('[data-e2e=result-tabs]')
    * match karate.sizeOf(locateAll('[data-e2e=tab-btn]')) == 3

    # Check Elements tab has content
    * def tabs = locateAll('[data-e2e=tab-btn]')
    * tabs[0].click()
    * waitFor('[data-e2e=elements-list]')
    * assert karate.sizeOf(locateAll('[data-e2e=element-card]')) > 0

    # Check Markdown tab has content
    * tabs[1].click()
    * waitFor('[data-e2e=raw-markdown]')
    * match text('[data-e2e=raw-content]') != ''

    # Step 9: Switch to Préparer mode and rechunk
    * waitFor('[data-e2e~=prepare-btn]')
    * click('[data-e2e~=prepare-btn]')
    * waitFor('[data-e2e=chunk-panel]')

    # Expand config if needed
    * def chevronOpen = optional('[data-e2e=config-chevron].open')
    * if (!chevronOpen.present) click('[data-e2e=config-toggle]')
    * waitFor('[data-e2e=config-body]')

    # Set max tokens and run chunking
    * clear('[data-e2e=config-input]')
    * input('[data-e2e=config-input]', '512')
    * click('[data-e2e=chunk-btn]')

    # Wait for chunks
    * retry(30, 1000).waitFor('[data-e2e=chunk-card]')
    * waitFor('[data-e2e=chunk-results]')
    * assert karate.sizeOf(locateAll('[data-e2e=chunk-card]')) > 0

    # Step 10: Delete the uploaded document via UI
    * click('[data-e2e~=configure-btn]')
    * waitFor('[data-e2e=doc-item].selected')
    * def rowsBefore = karate.sizeOf(locateAll('[data-e2e=doc-item]'))

    # Hover its row and delete it
    * mouse('[data-e2e=doc-item].selected').go()
    * click('[data-e2e=doc-item].selected [data-e2e=doc-delete]')

    # Its row leaves the list, and the API no longer knows the document
    * retry(10, 500).waitUntil("document.querySelectorAll('[data-e2e=doc-item]').length == " + (rowsBefore - 1))
    Given path '/api/documents', docId
    When method GET
    Then status 404
