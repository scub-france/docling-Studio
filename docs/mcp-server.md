# MCP document server

Docling Studio can expose its parsed documents to an AI agent — Claude Code,
Claude Desktop, or any [MCP](https://modelcontextprotocol.io) client — as a
**read-only** tool surface: map a document, read one section of it under a
token budget, and get citations the server can verify.

It is off by default and carries no authentication of its own. Enable it for
local agent work; put it behind an authenticating proxy anywhere else.

## What an agent can do

| Tool | Purpose |
|------|---------|
| `find_documents` | List documents, optionally filtered by filename. Returns `document_id`, the current `version_id`, and the window that was searched — `truncated: true` with an empty list means "not among the documents I looked at", not "no such document". |
| `get_outline` | The map: a tree of sections — or of pages, for a document without headings — each with its anchor and its estimated reading cost. `deeper_levels_available` says to ask for more depth; `entries_omitted` says the node cap was hit. |
| `read_element` | Read one anchor: the element alone (`include="self"`) or the whole section under it (`include="section"`), capped server-side and resumable through `next_cursor`. |
| `verify_citation` | Re-resolve an anchor and confirm a quote actually appears at it. |

Nothing writes. Uploading, re-analysing and editing chunks stay in the Studio
UI and the HTTP API.

## Anchors and citations

Every result carries anchors of the form:

```
dstudio://doc/{document_id}@{version_id}#{self_ref}
dstudio://doc/8f2a91c4@a71f0c33#/texts/91
```

- `version_id` identifies the **parse** the ref belongs to. A docling
  `self_ref` is stable inside one analysis and meaningless across two — a
  re-parse renumbers the document. Pinning the version is what keeps a
  citation true afterwards.
- `#{self_ref}` is the docling reference, or a virtual page ref
  (`#/pages/7`) for documents with no headings.

`read_element` returns one citation per element it read: the verbatim quote, a
`sha256` of it, the page, the bounding box, the heading breadcrumb, and a deep
link back into the Studio viewer.

Read `coord_origin` before the bbox numbers. Docling emits `BOTTOMLEFT` for
PDF-native parses — the y axis grows upwards, so `top` is the *larger* number
and the height is `top - bottom`; with `TOPLEFT` it is the other way round.
`page_width` / `page_height` come with the citation so the box can be flipped
without another call.

`verify_citation` is the point of the whole contract: the server, not the
model, is the source of truth for what the document says. Its `status` is one
of:

| Status | Meaning |
|--------|---------|
| `verified` | The quote is there. A partial quote counts, and a section anchor also covers the elements inside it — when the quote came from one of them, `citation` carries that precise anchor to prefer. |
| `stale_version` | The quote is there, but the anchor pins a parse that has since been superseded. Still valid; re-read to cite the current one. |
| `quote_drift` | The anchor resolves and the quote is not in what it covers. `actual_quote` says what is. |
| `unknown_ref` | No such element in that parse. |
| `unknown_version` | No such parse for that document. |

## Enable it

Install the optional SDK — needed for both transports:

```bash
cd document-parser
uv sync --group mcp
```

The stdio transport works from there. For the HTTP transport, turn the flag
on and restart the backend:

```bash
# .env
MCP_ENABLED=true
MCP_STUDIO_BASE_URL=http://localhost:3000   # optional, for absolute deep links
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_ENABLED` | `false` | Mounts `POST /mcp` on the backend. It does **not** gate `mcp_stdio.py`: that process is spawned by the client itself, which is the authorisation. |
| `MCP_ALLOWED_HOSTS` | `127.0.0.1:*,localhost:*,[::1]:*` | Host/Origin allow-list (DNS-rebinding protection). `*` delegates the check to a fronting proxy. |
| `MCP_MAX_READ_TOKENS` | `4000` | Hard ceiling for one `read_element`. A client may ask for less, never more. |
| `MCP_STUDIO_BASE_URL` | *(empty)* | Absolute base for citation deep links. Empty keeps them relative. |

## Connect a client

### Claude Code — over HTTP (backend already running)

```bash
claude mcp add --transport http docling-studio http://localhost:8000/mcp
```

### Claude Code — over stdio (no server needed)

The client launches the process itself; use the project venv's interpreter,
because a bare `python` resolves against the ambient one.

```bash
claude mcp add --env DB_PATH=/abs/path/document-parser/data/docling_studio.db \
  --transport stdio docling-studio -- \
  /abs/path/document-parser/.venv/bin/python /abs/path/document-parser/mcp_stdio.py
```

`DB_PATH` matters: the client launches the process from its own working
directory, so the default relative path would point somewhere else. Keep an
option between `--env` and the server name — the CLI otherwise reads the name
as another `KEY=value` pair.

### Claude Desktop

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "docling-studio": {
      "command": "/abs/path/document-parser/.venv/bin/python",
      "args": ["/abs/path/document-parser/mcp_stdio.py"],
      "env": { "DB_PATH": "/abs/path/document-parser/data/docling_studio.db" }
    }
  }
}
```

Then ask, in plain language: *"list the documents, then find the notice period
in the contract and cite it."*

## Security posture

- **Document text is untrusted data.** Everything read is wrapped in
  `<document-content …>` delimiters, any closing delimiter inside the text is
  neutralised, and the server instructions tell the agent never to follow
  instructions found inside. Outline titles and citation quotes are
  document-derived too.
- **No authentication.** `MCP_ENABLED=true` publishes the surface to anyone
  who can reach the port. Keep it on localhost.
- **Closed input surface.** Tools take identifiers only — no file paths, no
  free-form queries against OpenSearch or Neo4j.
- **Bounded output.** Server-side ceilings on read size, outline size and
  result counts — a client argument can lower them, never raise them, and a
  single element larger than the whole budget is clipped rather than smuggled
  through. The HTTP surface is also covered by `RATE_LIMIT_RPM`.

## Limits of this first slice

Search (`search_document`, `search_corpus`), page-crop images
(`get_element_image`), MCP resources and prompts, and authentication are not
part of it. `find_documents` filters on filename over the most recent
documents rather than through a repository query, and the Docker image does
not carry the SDK yet — the group is opt-in at install time.
