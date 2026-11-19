@ui @regression
Feature: UI — Old workspace mode links open the document viewer (#264, #225)

  # 0.7.0 removed the Chunk and Ingest views from /docs/:id. Parse is the only
  # workspace mode left (frontend/src/shared/routing/modes.ts): every older
  # ?mode= value is an alias of parse, and the router guard rewrites the query
  # to ?mode=parse, so a saved bookmark still opens the document.
  #
  # This feature replaces doc-chunk-view, doc-ingest-view and
  # doc-strategy-popover, which drove the removed views (view-switcher,
  # chunk-tab, strategy popover, ingest CTA). Chunking stays covered by
  # doc-tab-chunk-mode.feature (API) and analyses/rechunk.feature (UI).

  Background:
    * url baseUrl

  Scenario Outline: ?mode=<mode> opens the document viewer in Parse mode
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'small.pdf' }
    * def docId = upload.docId

    * driver uiBaseUrl + '/docs/' + docId + '?mode=<mode>'
    * waitFor('[data-e2e=document-viewer] [data-e2e=preview-with-overlay]')
    * waitFor('[data-e2e=preview-page-1]')
    * waitUntil("new URLSearchParams(location.search).get('mode') === 'parse'")

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'small.pdf' }

    Examples:
      | mode    |
      | chunk   |
      | ingest  |
      | compare |
      | chunks  |
      | linked  |
      | inspect |
