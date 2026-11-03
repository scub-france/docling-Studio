# Glossary

The words the code, the API, the MCP server and the UI use for the same
things. When two names exist for one thing, the table says which one new code
uses, and why the other one is still around.

## The document and its parse

| Term | Meaning | In the code |
|------|---------|-------------|
| **Document** | A PDF a user uploaded: the file, its metadata, and its lifecycle state (Uploaded, Parsed, Chunked…). | `Document`, `DocumentLifecycleState`, `/api/documents` |
| **Analysis** | One Docling run on a document. It goes from `PENDING` to `COMPLETED` or `FAILED`, and keeps the result: Markdown, HTML, pages, and the Docling document as JSON. A document can have several. | `AnalysisJob`, `AnalysisStatus`, `/api/analyses` |
| **Parse** | The result of a completed analysis, read as a tree: the Docling document and the index built from it. The navigation code and the MCP server say parse; the UI and the API say analysis. Same object, same id. | `ParseLoader`, `LoadedParse`, `DocumentIndex` |
| **Document version** | A frozen pair recorded for a document: the analysis it pointed at, and a snapshot of its chunks. A completed analysis or a chunk generation records one; restoring it writes the chunks back. | `DocumentVersion`, `VersionService`, `/api/documents/{id}/versions` |

!!! warning "`version_id` names a parse, not a document version"
    In anchors and in the MCP tools, `version_id` is the id of the parse, so of
    an `AnalysisJob`. It is not a `DocumentVersion` id, which only the
    versions API takes (`/versions/{document_version_id}/restore`).

    The name is part of the MCP contract: tool arguments (`get_outline`,
    `read_element`), result fields (`find_documents`, every citation), the
    `<document-content version_id=…>` envelope and the anchor grammar the
    server teaches agents. Renaming it would break every connected agent, so
    it stays until that contract is versioned. Inside the backend it is kept
    too: the parse loader, the citation services and the MCP tool handlers
    all pass it along under that name.

    The versioning side uses another name for its own id:
    `VersionService.restore` and the restore route take a
    `document_version_id`. The URL did not change, only the name of its path
    variable.

## Chunks

| Term | Meaning | In the code |
|------|---------|-------------|
| **Chunk** | A piece of a document's text, cut by a chunker, with its headings, page and boxes. Chunks can be edited, split, merged and deleted. | `Chunk`, `ChunkEdit` |
| **Chunkset** | All the live chunks of one document, in order. A document version stores a snapshot of it. | `chunk_editing`, `chunkset_hash` |

Chunks feed ingestion into vector stores (deprecated, removed in 0.8.0). The
MCP server does not use them: it reads the parse.

## Reading with an agent (Chunkless RAG)

| Term | Meaning | In the code |
|------|---------|-------------|
| **Anchor** | The address of one element of one parse: `dstudio://doc/{document_id}@{version_id}#{ref}`. The `ref` is a Docling ref (`#/texts/91`), a virtual page (`#/pages/7`) or a span (`#/texts/91..#/texts/94`). Only the server builds anchors. | `DocumentAnchor`, `domain/anchors.py`, `domain/spans.py` |
| **Round** | One step of the agent's loop: pick one section, say why, read it, say what it found. Reading on with a `cursor` stays in the same round. `max_rounds` caps them. | `SourceRound`, `SourceTotals.rounds`, `MCP_MAX_ROUNDS` |
| **Quote** | The words an agent claims a passage says. The server checks it: at least 10 characters, found at the anchor once formatting is ignored. | `domain/citation_match.py`, `CitationService.verify_citation` |
| **Citation** | An anchor with its verbatim text, the hash of that text, its page, box and Studio link. What an agent cites. | `Citation`, `CitationCheck`, `CitationStatus` |
| **Source** | A place in the document an answer came from: a section read in a round, or a passage cited. `show_sources` draws them on the document's map. | `SourceMap`, `SourceStatus`, `domain/source_map.py` |

Three older names for the same ideas remain where changing them would break
something:

- The sources card's contract calls a round a **hop**: `hops`, `hop_id`
  (`h1`, `h2`…), `hop_ids`. The domain says round; the MCP adapter maps one to
  the other (`mcp_adapter/sources_wire.py`).
- Studio's own Ask feature runs the same loop through docling-agent, which
  calls a round an **iteration** (`ReasoningIteration`,
  `REASONING_MAX_ITERATIONS`). Both caps default to 5.
- In Ask, a **citation** is only a Docling ref, with no quote and no check
  (`ReasoningStep.citations`). The MCP server's citation is the full value
  object above.

## In the UI

- **History** (`/history`) lists analyses. It is not the list of document
  versions.
- **OCR** is the Docling option that reads the text of scanned pages and
  images. It does not name an analysis.
