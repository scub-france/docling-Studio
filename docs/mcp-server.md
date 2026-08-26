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

Every result also carries a `next_step`: what to do with what was just
returned, delivered at the moment it applies rather than as a rule stated once
at connection time. A truncated read hands back its own cursor; a verification
says whether the quote is publishable.

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
| `MCP_CACHE_TTL_SECONDS` | `600` | Freshness hint for the tool list, the prompt list and the viewer (SEP-2549). `0` disables it. |
| `MCP_APPS_ENABLED` | `true` | Ships the `show_citation` MCP App. Degrades to text on hosts without UI support. |
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
in the contract and cite it."* On Claude Desktop, add *"and show me where"* to
get the passage rendered on its page.

## Procedures the user invokes

Two MCP **prompts** — slash commands in clients that surface them. They exist
because a thorough protocol is worth several extra tool calls when someone
asks for a sourced answer, and wasteful when they ask a passing question. A
tool description is read on every call; a prompt is chosen.

| Prompt | Arguments | What it makes the agent do |
|--------|-----------|----------------------------|
| `cite_answer` | `document`, `question`, `evidence` (`text` \| `images`) | Map before reading, read only what the question needs, resume a truncated read with its cursor, cite with the *element's* uri, verify every quote before publishing — and say so plainly when the document does not answer. `evidence=images` adds a `show_citation` for each verified quote. |
| `extract_table` | `uri` | Read the table alone, return it exactly as rendered — no re-aligning, re-ordering, or rounding — with the citation needed to check it. |

Neither reimplements anything: a prompt returns text the model then executes
with the same tools, which is what keeps the procedure from drifting away
from what the server actually does.

Clients list prompts once per session, so a newly added one needs a reconnect
to appear.

## Seeing a citation, not just reading it

The server also ships one **MCP App** (SEP-1865, extension
`io.modelcontextprotocol/ui`): a `show_citation` tool bound to a predeclared
`ui://docling-studio/citation.html` template. A host that supports it renders
the cited passage **as an image of the page region it was lifted from**, next
to its verbatim text — `verify_citation` says a quote is real, this shows it.

| Tool | Purpose |
|------|---------|
| `show_citation` | Takes a citation uri and returns the passage with a raster crop of its page region. Falls back to the citation as text on hosts that cannot render it. |

**Which clients render it**

- **Claude Desktop / claude.ai / mobile — yes.** A local stdio server works: Claude asks
  permission the first time ("Always allow") and renders the app inline. No
  directory listing or review needed for your own connector.
- **Claude Code — no.** It is absent from the
  [client matrix](https://modelcontextprotocol.io/extensions/client-matrix) and
  its docs and changelog never mention MCP Apps. `show_citation` still works
  there — it just answers as text.
- Others rendering today: VS Code Copilot, Goose, Postman, MCPJam, Cursor,
  ChatGPT, LibreChat, Smithery.

Degradation is a spec requirement and it is what makes this free to ship: a
host that never advertises the extension never fetches the template, and the
image is never rendered at all — so the bytes cost nothing on a client that
could not have shown them.

Turn it off with `MCP_APPS_ENABLED=false`; the four text tools are unaffected.

**How the image is kept small.** The crop is embedded as a `data:` URI (the
default MCP Apps CSP allows `img-src data:` and nothing else, so the view
loads from the network never — which also means it works over stdio, with no
backend running). It is rendered at 150 dpi and halved until it fits
`image_max_bytes` (45 KB by default): a paragraph lands around 35-50 KB.

*Known limitation:* the crop travels in the tool result, so on a rendering
host the model sees the base64 too. The documented upgrade is an app-only tool
(`visibility: ["app"]`) that the view calls for its own image — worth doing if
payloads grow, unnecessary at one crop per call.

## What a client may cache

The protocol's caching seam is `_meta` freshness hints (SEP-2549) on the
methods it declares cacheable: `tools/list`, `prompts/list`, `resources/list`,
`resources/templates/list`, `resources/read` and `server/discover`. The server
stamps all of them with `MCP_CACHE_TTL_SECONDS` and `cacheScope: public` —
they are deploy-scoped and identical for every caller.

Note what is *not* on that list: **`tools/call`**. The protocol offers caching
exactly where this server's cost is not. A hint amortises the ~4 000 tokens of
connecting; it does nothing for the cost of reading, which is where the tokens
actually go. Any deduplication of repeated reads has to happen in the client or
a proxy.

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

Search (`search_document`, `search_corpus`), `docling://` resources, and
authentication are not part of it. `find_documents` filters on filename over the most recent
documents rather than through a repository query, and the Docker image does
not carry the SDK yet — the group is opt-in at install time.
