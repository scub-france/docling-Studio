@ui
Feature: UI - Edit and persist Docling analysis changes

  Background:
    * url baseUrl

  Scenario: Replace, merge, delete, and discard text edits
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'editor-text.pdf' }
    * def docId = upload.docId
    * def analysis = call read('classpath:common/helpers/analyze.feature') { docId: '#(docId)' }
    * match analysis.response.status == 'COMPLETED'
    * def replacement = 'Editor alpha revised marker.'

    # Replace text and verify it survives save, browser reload, and stream history.
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-editor=analysis-editor]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]')
    * clear('[data-e2e=analysis-editor-text]')
    * input('[data-e2e=analysis-editor-text]', replacement)
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * click('[data-e2e=analysis-editor-undo]')
    * retry(30, 500).script("document.querySelector('[data-e2e=analysis-editor-markdown]').textContent.includes('Editor alpha paragraph marker.') && !document.querySelector('[data-e2e=analysis-editor-markdown]').textContent.includes('Editor alpha revised marker.')")
    * click('[data-e2e=analysis-editor-redo]')
    * retry(30, 500).script("document.querySelector('[data-e2e=analysis-editor-markdown]').textContent.includes('Editor alpha revised marker.')")
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * click('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-revised-marker]')
    * match value('[data-e2e=analysis-editor-text]') == replacement
    * click('[data-e2e=analysis-editor-history]')
    * match text('[data-e2e=analysis-edit-history]') contains 'replaceText'

    # Merge two paragraph elements and verify the durable result after reload.
    * click('[data-e2e=analysis-editor-item-editor-alpha-revised-marker] [data-e2e=analysis-editor-merge-select]')
    * click('[data-e2e=analysis-editor-item-editor-bravo-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    * match text('[data-e2e=analysis-editor-selection-count]') contains '2'
    * click('[data-e2e=analysis-editor-merge]')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * click('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * match text('[data-e2e=analysis-editor-markdown]') contains 'Editor alpha revised marker. Editor bravo paragraph marker.'

    # Discard is local: the saved Charlie text remains unchanged.
    * click('[data-e2e=analysis-editor-tree-item-editor-charlie-paragraph-marker]')
    * clear('[data-e2e=analysis-editor-text]')
    * input('[data-e2e=analysis-editor-text]', 'Editor text should be discarded.')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-discard]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * match text('[data-e2e=analysis-editor-markdown]') contains 'Editor charlie paragraph marker.'
    * match text('[data-e2e=analysis-editor-markdown]') !contains 'Editor text should be discarded.'

    # Confirm and persist a selected-range deletion.
    * click('[data-e2e=analysis-editor-item-editor-charlie-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    * click('[data-e2e=analysis-editor-item-editor-delta-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    * match text('[data-e2e=analysis-editor-selection-count]') contains '2'
    * dialog(true)
    * click('[data-e2e=analysis-editor-delete-range]')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * click('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * match text('[data-e2e=analysis-editor-markdown]') !contains 'Editor charlie paragraph marker.'
    * match text('[data-e2e=analysis-editor-markdown]') !contains 'Editor delta paragraph marker.'
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }

  Scenario: Move a paragraph into a section and persist its reading order
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'editor-structure.pdf' }
    * def docId = upload.docId
    * def analysis = call read('classpath:common/helpers/analyze.feature') { docId: '#(docId)' }
    * match analysis.response.status == 'COMPLETED'

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-editor=analysis-editor]')
    * click('[data-e2e=analysis-editor-tree-item-structure-one-alpha-paragraph-marker]')
    * click('[data-e2e=analysis-editor-choose-move]')
    * click('[data-e2e=analysis-editor-item-structure-section-two] [data-e2e=analysis-editor-move-inside]')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-tree-item-structure-section-two]')
    * select('[data-e2e=analysis-editor-heading-level]', '2')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * click('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * def savedMarkdown = text('[data-e2e=analysis-editor-markdown]')
    * assert savedMarkdown.contains('### Structure section two')
    * assert savedMarkdown.indexOf('### Structure section two') < savedMarkdown.indexOf('Structure one alpha paragraph marker.')
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }

  Scenario: Recover a pending text edit after refreshing the browser
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'editor-text.pdf' }
    * def docId = upload.docId
    * def analysis = call read('classpath:common/helpers/analyze.feature') { docId: '#(docId)' }
    * match analysis.response.status == 'COMPLETED'
    * def replacement = 'Editor alpha recovered marker.'

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-editor=analysis-editor]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]')
    * clear('[data-e2e=analysis-editor-text]')
    * input('[data-e2e=analysis-editor-text]', replacement)
    * waitFor('[data-e2e=analysis-editor-unsaved]')

    # Session storage keeps the command draft across a refresh; the native
    # beforeunload prompt is accepted as part of this recovery scenario.
    * driver.reload()
    * dialog(true)
    * waitFor('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-recovered]')
    * click('[data-e2e=analysis-editor-restore-draft]')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * click('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-recovered-marker]')
    * match value('[data-e2e=analysis-editor-text]') == replacement

    # Another session advances the stream while this tab has an unsaved edit.
    # The now-stale draft must not be offered or applied after refresh.
    * click('[data-e2e=analysis-editor-tree-item-editor-charlie-paragraph-marker]')
    * clear('[data-e2e=analysis-editor-text]')
    * input('[data-e2e=analysis-editor-text]', 'Editor stale draft must be rejected.')
    * waitFor('[data-e2e=analysis-editor-unsaved]')

    Given url baseUrl
    And path '/api/documents', docId, 'analysis-editor'
    And param analysisId = analysis.jobId
    When method GET
    Then status 200
    * def externalTarget = response.model.elements.find(function(e) { return e.text == 'Editor charlie paragraph marker.' })
    * match externalTarget == '#present'

    Given url baseUrl
    And path '/api/documents', docId, 'analysis-edits'
    And param analysisId = analysis.jobId
    And request { expectedAppliedThroughSequence: 1, commands: [{ type: 'replaceText', elementId: '#(externalTarget.id)', text: 'Editor external session change.' }] }
    When method POST
    Then status 200

    * driver.reload()
    * dialog(true)
    * waitFor('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-editor=analysis-editor]')
    * assert !exists('[data-e2e=analysis-editor-recovered]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * match text('[data-e2e=analysis-editor-markdown]') contains 'Editor external session change.'
    * match text('[data-e2e=analysis-editor-markdown]') !contains 'Editor stale draft must be rejected.'
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }
