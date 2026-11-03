@ui
Feature: UI — Full happy path via browser

  Background:
    * url baseUrl

  Scenario: Complete workflow — upload, analyze, verify results, rechunk, delete — all via UI
    # Step 1: Open Studio page
    * driver uiBaseUrl + '/studio'
    * waitFor('[data-e2e=upload-zone]')

    # Step 2: Upload a PDF via UI
    * def filePath = karate.toAbsolutePath('classpath:common/data/generated/medium.pdf')
    * driver.inputFile('input[type=file]', filePath)

    # Step 3: Verify document appears in doc list
    * waitFor('[data-e2e=doc-item]')
    * match text('[data-e2e=doc-name]') contains 'medium.pdf'

    # Step 4: Select the document
    * click('[data-e2e=doc-item]')
    * waitFor('[data-e2e=doc-item].selected')

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

    # Step 10: Delete the document via UI
    * click('[data-e2e~=configure-btn]')
    * waitFor('[data-e2e=doc-item]')

    # Hover and delete
    * mouse('[data-e2e=doc-item]').go()
    * waitFor('[data-e2e=doc-delete]')
    * click('[data-e2e=doc-delete]')

    # Verify document is gone from the list
    * retry(10, 500).waitUntil("!document.querySelector('[data-e2e=doc-item]') || !document.querySelector('[data-e2e=doc-name]').textContent.includes('medium.pdf')")
