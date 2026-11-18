# PDF loading performance

## Baseline

Measured in the deployment on a 411-page PDF (November 2026):

| Request | Observed time | Response size |
| --- | ---: | ---: |
| Analysis detail | 1.26 s | 1.6 MB |
| Editor load, first request | 18.2 s | 6.2 MB |
| Editor load, repeat request | 10.1 s | 6.2 MB |
| Page 1 preview, repeat request | 2.0 s | 0.93 MB |

The repeat editor request spent about 4.3 s before its response started and
5.7 s transferring its body. Its JSON included about 2.9 MB of editor model,
0.95 MB of tree, and 2.0 MB of analysis result. The browser parsed it in 23 ms.
The analysis view mounted about 27,600 DOM nodes, including 3,550 tree items,
and requested nine page images on opening. These are observations from one PDF,
not a complete performance distribution.

## Phase 1: reuse and transfer less

- Compress JSON responses at nginx. PDF page images are already compressed and
  should not be passed through gzip.
- Cache rendered page previews in the backend with a fixed memory budget. Key
  by source path, file size, modification time, page, and DPI. Let the browser
  cache successful previews under each document's stable ID.
- Narrow the stacked preview's preload window so opening an analysis does not
  start as many raster requests at once.

This phase leaves the API shape and editing behavior unchanged. It improves
repeat page visits and JSON transfer, but does not remove the server's editor
projection work on a cold load.

## Phase 2: page-scoped analysis data

Add a lightweight analysis manifest with page dimensions and document metadata.
Move bounding boxes and page elements to a page endpoint. Fetch the current
page and a small adjacent window; retain page dimensions for the whole PDF so
scroll positions and direct page navigation remain stable. Keep full Markdown
and HTML behind their own requests, made only when those tabs open.

The frontend currently expects the full `pagesJson` string and scans it for
focused references. A page-scoped API needs a compact reference-to-page index
or a lookup endpoint so deep links and selection across pages still work.

## Phase 3: editor model and tree

Return a compact editor manifest first: analysis ID, revision, page index, and
selection metadata. Fetch editable element details by page. Load tree branches
on demand or virtualize visible rows; document sections are not bounded by PDF
pages, so the tree should not be paginated strictly by page number.

Edit commands still use stable logical element IDs and are validated against
the complete canonical document on the server. Preview and save responses
should identify changed pages and elements so the client does not download the
full model after every edit. This requires revision-aware invalidation when a
cross-page merge, delete, or reorder changes reading order or tree structure.

## Verification

Compare initial display time, first page image time, repeated page time, editor
load time, transferred bytes, and mounted tree rows for the same 411-page PDF.
Check direct navigation to a distant page and element, cross-page edits, and
returning to a previously viewed page.

## Scrolling follow-up

After phase 1 deployed, cold pages still arrived slowly during continuous
scrolling. In the 411-page analysis at a 1440px desktop viewport, page 30 took
1.72 s and page 31 took 1.41 s to reach the browser; a cached repeat of page 30
took 7 ms. Most of the cold request time was image transfer. The 25% observer
margin mounted only the current and next page, leaving too little time before
the reader reached the next cold page.

The scrolling follow-up keeps image mounting to the current page, one previous
page and two upcoming pages, regardless of page-card geometry. The browser
starts those mounted image requests immediately. The frontend requests lossless
WebP previews while the backend retains PNG for existing clients. On four local
150 DPI pages, lossless WebP was 69–119 KB versus 331–472 KB for PNG, with
similar encode time. Lossless encoding preserves text edges; deployed transfer
times should be checked after rollout.

The next viewer revision prioritizes the current page: it mounts a cold
foreground image first and requests the two upcoming pages after that image
loads. Previously requested nearby pages stay mounted while they finish, and
the document switch clears the request state. This addresses the observed
4.6–6.8 s time to first byte when three cold page renders began together.
