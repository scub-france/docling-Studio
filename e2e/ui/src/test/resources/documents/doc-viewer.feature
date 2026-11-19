@ui @regression
Feature: UI — Doc workspace: the document shows in the analysis viewer (#352)

  # /docs/:id used to show one page image at a time with its own ‹ › bar.
  # It now uses the Parse view's viewer, sized from GET /api/documents/:id/pages,
  # so it works before any analysis.

  Background:
    * url baseUrl

  Scenario: Multi-page document → viewer on page 1 → next page → page 2
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'medium.pdf' }
    * def docId = upload.docId

    # The page sizes come from the PDF itself, no analysis needed.
    Given url baseUrl
    And path '/api/documents', docId, 'pages'
    When method GET
    Then status 200
    And assert karate.sizeOf(response) > 1

    * driver uiBaseUrl + '/docs/' + docId
    * waitFor('[data-e2e=document-viewer] [data-e2e=preview-with-overlay]')
    * waitFor('[data-e2e=preview-page-1]')
    * waitUntil("document.querySelector('[data-e2e=page-input]').value === '1'")

    * click('[data-e2e=page-next]')
    * waitUntil("document.querySelector('[data-e2e=page-input]').value === '2'")

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'medium.pdf' }

  Scenario: PDF.js draws page 1 itself, without the server image fallback
    # The containers above also show when PDF.js fails and the viewer falls
    # back to the server-rendered <img> (PagePreviewWithOverlay.vue). This
    # scenario tells the two apart:
    #   - [data-e2e=bbox-canvas] appears once the page is ready, on either path;
    #   - the fallback is an <img> in the page card, PDF.js draws into a
    #     <canvas> outside the bbox overlay;
    #   - that canvas must hold dark pixels, the text of the generated page.
    # No data-e2e tells the PDF.js canvas from the fallback image yet, so the
    # selectors below use element types under data-e2e containers. Switch to
    # [data-e2e=pdf-page-canvas] and [data-e2e=preview-fallback-image] once
    # the frontend adds them (PdfPageCanvas.vue, PagePreviewWithOverlay.vue).
    * def upload = call read('classpath:common/helpers/upload.feature') { file: 'medium.pdf' }
    * def docId = upload.docId

    * driver uiBaseUrl + '/docs/' + docId
    * waitFor('[data-e2e=preview-page-1] [data-e2e=bbox-canvas]')
    * match optional('[data-e2e=preview-page-1] img').present == false
    * waitUntil("(function(){ var c = document.querySelector('[data-e2e=preview-page-1] canvas:not([data-e2e=bbox-canvas] canvas)'); if (!c || !c.width || !c.height) return false; var d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; for (var i = 0; i < d.length; i += 4) { if (d[i + 3] > 0 && d[i] < 128 && d[i + 1] < 128 && d[i + 2] < 128) return true; } return false; })()")
    * match optional('[data-e2e=preview-page-1] img').present == false

    * call read('classpath:common/helpers/cleanup-by-name.feature') { filename: 'medium.pdf' }
