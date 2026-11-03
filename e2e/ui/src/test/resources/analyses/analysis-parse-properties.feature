@ui @regression
Feature: UI — Parse view: selecting a structure node fills the Properties panel (#265)

  # The Parse view only exists on the saved analysis page (/analyses/:id): the
  # document workspace (/docs/:id) shows the document without it. Selecting a
  # node in the Structure tree fills the right-side Properties panel. The page
  # shows a saved analysis read-only, so the inline "Edit chunk" action of
  # #265 is not offered there.

  Background:
    * url baseUrl

  Scenario: Select a node → Properties populated, no inline chunk edit
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId
    * def analysis = call read('classpath:common/helpers/analyze.feature') { docId: '#(docId)' }
    * match analysis.response.status == 'COMPLETED'

    * driver uiBaseUrl + '/analyses/' + analysis.jobId
    * waitFor('[data-e2e=parse-tab]')
    * waitFor('[data-e2e=element-properties]')

    # Empty state visible before any selection.
    * waitFor('[data-e2e=element-properties-empty]')

    # Click the first tree node: Properties fills in, the empty state goes.
    * waitFor('[data-e2e=tree-node-row]')
    * click('[data-e2e=tree-node-row]')
    * waitUntil("!document.querySelector('[data-e2e=element-properties-empty]')")
    * waitFor('[data-e2e=properties-extracted-text]')

    # Read-only: a saved analysis never offers the inline chunk editor.
    * match karate.sizeOf(locateAll('[data-e2e=properties-edit-btn]')) == 0

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }
