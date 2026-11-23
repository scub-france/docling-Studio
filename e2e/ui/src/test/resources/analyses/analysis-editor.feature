@ui
Feature: UI - Edit and persist Docling analysis changes

  # Needs ANALYSIS_EDITOR_ENABLED (on by default, docker-compose.yml) and the
  # editor-*.pdf fixtures from e2e/generate-test-data.py. Tree rows are
  # addressed by the slug of their text (EditableStructureNode.vue), so
  # "Editor alpha paragraph marker." is ...-editor-alpha-paragraph-marker.
  # Assertions avoid translated labels: the UI may be in French or English.

  Background:
    * url baseUrl

  @critical
  Scenario: Open the editor, save a text edit, and find it after a reload
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'editor-text.pdf' }
    * def docId = upload.docId
    * def analysis = call read('classpath:common/helpers/analyze.feature') { docId: '#(docId)' }
    * match analysis.response.status == 'COMPLETED'
    * def replacement = 'Editor alpha critical marker.'

    # The editor opens on the analysis and shows its tree.
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]')
    * waitFor('[data-e2e=analysis-editor-text]')

    # Edit and save.
    * clear('[data-e2e=analysis-editor-text]')
    * input('[data-e2e=analysis-editor-text]', replacement)
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * waitForEnabled('[data-e2e=analysis-editor-save]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')

    # Reload the page: the edit must come back from the server.
    * refresh()
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-tree-item-editor-alpha-critical-marker]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-critical-marker]')
    * waitFor('[data-e2e=analysis-editor-text]')
    * match value('[data-e2e=analysis-editor-text]') == replacement
    * match optional('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]').present == false

    # The saved stream holds exactly this one command.
    Given url baseUrl
    And path '/api/documents', docId, 'analysis-editor'
    And param analysisId = analysis.jobId
    When method GET
    Then status 200
    And match response.appliedThroughSequence == 1
    And match response.model.elements[*].text contains replacement

    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }

  Scenario: Replace, merge, delete, and discard text edits
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'editor-text.pdf' }
    * def docId = upload.docId
    * def analysis = call read('classpath:common/helpers/analyze.feature') { docId: '#(docId)' }
    * match analysis.response.status == 'COMPLETED'
    * def replacement = 'Editor alpha revised marker.'

    # Replace text and verify it survives save, browser reload, and stream history.
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]')
    * waitFor('[data-e2e=analysis-editor-text]')
    * clear('[data-e2e=analysis-editor-text]')
    * input('[data-e2e=analysis-editor-text]', replacement)
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * waitForEnabled('[data-e2e=analysis-editor-undo]')
    * click('[data-e2e=analysis-editor-undo]')
    * waitUntil("document.querySelector('[data-e2e=analysis-editor-markdown]').textContent.includes('Editor alpha paragraph marker.') && !document.querySelector('[data-e2e=analysis-editor-markdown]').textContent.includes('Editor alpha revised marker.')")
    * waitForEnabled('[data-e2e=analysis-editor-redo]')
    * click('[data-e2e=analysis-editor-redo]')
    * waitUntil("document.querySelector('[data-e2e=analysis-editor-markdown]').textContent.includes('Editor alpha revised marker.')")
    * waitForEnabled('[data-e2e=analysis-editor-save]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-tree-item-editor-alpha-revised-marker]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-revised-marker]')
    * waitFor('[data-e2e=analysis-editor-text]')
    * match value('[data-e2e=analysis-editor-text]') == replacement
    # The history lists the saved command; its label is translated, so look
    # for the revert button of sequence 1 instead of the command name.
    * click('[data-e2e=analysis-editor-history]')
    * waitFor('[data-e2e=analysis-edit-history]')
    * waitFor('[data-e2e=analysis-editor-history-toggle-1]')

    # Merge two paragraphs of the same type (#395: merge is only enabled for
    # same-type text) and verify the durable result after reload.
    * click('[data-e2e=analysis-editor-item-editor-alpha-revised-marker] [data-e2e=analysis-editor-merge-select]')
    * click('[data-e2e=analysis-editor-item-editor-bravo-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    * match text('[data-e2e=analysis-editor-selection-count]') contains '2'
    * waitForEnabled('[data-e2e=analysis-editor-merge]')
    * click('[data-e2e=analysis-editor-merge]')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * waitForEnabled('[data-e2e=analysis-editor-save]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-markdown-tab]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * match text('[data-e2e=analysis-editor-markdown]') contains 'Editor alpha revised marker. Editor bravo paragraph marker.'

    # Discard is local: the saved Charlie text remains unchanged.
    * click('[data-e2e=analysis-editor-tree-item-editor-charlie-paragraph-marker]')
    * waitFor('[data-e2e=analysis-editor-text]')
    * clear('[data-e2e=analysis-editor-text]')
    * input('[data-e2e=analysis-editor-text]', 'Editor text should be discarded.')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-discard]')
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * match text('[data-e2e=analysis-editor-markdown]') contains 'Editor charlie paragraph marker.'
    * match text('[data-e2e=analysis-editor-markdown]') !contains 'Editor text should be discarded.'

    # Persist a selected-range deletion. The range delete asks no
    # confirmation (store.queueDeleteElements), so no dialog is expected.
    * click('[data-e2e=analysis-editor-item-editor-charlie-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    * click('[data-e2e=analysis-editor-item-editor-delta-paragraph-marker] [data-e2e=analysis-editor-merge-select]')
    * match text('[data-e2e=analysis-editor-selection-count]') contains '2'
    * waitFor('[data-e2e=analysis-editor-delete-range]')
    * click('[data-e2e=analysis-editor-delete-range]')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * waitForEnabled('[data-e2e=analysis-editor-save]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')
    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-markdown-tab]')
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
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-tree-item-structure-one-alpha-paragraph-marker]')
    * click('[data-e2e=analysis-editor-tree-item-structure-one-alpha-paragraph-marker]')
    * waitFor('[data-e2e=analysis-editor-choose-move]')
    * click('[data-e2e=analysis-editor-choose-move]')
    # The section's own drop targets come before those of its children.
    * waitFor('[data-e2e=analysis-editor-item-structure-section-two] [data-e2e=analysis-editor-move-inside]')
    * click('[data-e2e=analysis-editor-item-structure-section-two] [data-e2e=analysis-editor-move-inside]')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * click('[data-e2e=analysis-editor-tree-item-structure-section-two]')
    * waitFor('[data-e2e=analysis-editor-heading-level]')
    * select('[data-e2e=analysis-editor-heading-level]', '2')
    * waitForEnabled('[data-e2e=analysis-editor-save]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-markdown-tab]')
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
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-paragraph-marker]')
    * waitFor('[data-e2e=analysis-editor-text]')
    * clear('[data-e2e=analysis-editor-text]')
    * input('[data-e2e=analysis-editor-text]', replacement)
    * waitFor('[data-e2e=analysis-editor-unsaved]')

    # Session storage keeps the command draft across a refresh; the native
    # beforeunload prompt is accepted as part of this recovery scenario.
    * driver.reload()
    * dialog(true)
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-recovered]')
    * click('[data-e2e=analysis-editor-restore-draft]')
    * waitFor('[data-e2e=analysis-editor-unsaved]')
    * waitForEnabled('[data-e2e=analysis-editor-save]')
    * click('[data-e2e=analysis-editor-save]')
    * waitFor('[data-e2e=analysis-editor-saved]')

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-tree-item-editor-alpha-recovered-marker]')
    * click('[data-e2e=analysis-editor-tree-item-editor-alpha-recovered-marker]')
    * waitFor('[data-e2e=analysis-editor-text]')
    * match value('[data-e2e=analysis-editor-text]') == replacement

    # Another session advances the stream while this tab has an unsaved edit.
    # The now-stale draft must not be offered or applied after refresh
    # (the stored draft's expectedAppliedThroughSequence no longer matches).
    * click('[data-e2e=analysis-editor-tree-item-editor-charlie-paragraph-marker]')
    * waitFor('[data-e2e=analysis-editor-text]')
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
    * waitForEnabled('[data-e2e=analysis-edit-toggle]')
    * click('[data-e2e=analysis-edit-toggle]')
    * waitFor('[data-e2e=analysis-editor-markdown-tab]')
    * match optional('[data-e2e=analysis-editor-recovered]').present == false
    * click('[data-e2e=analysis-editor-markdown-tab]')
    * waitFor('[data-e2e=analysis-editor-markdown]')
    * match text('[data-e2e=analysis-editor-markdown]') contains 'Editor external session change.'
    * match text('[data-e2e=analysis-editor-markdown]') !contains 'Editor stale draft must be rejected.'
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }
