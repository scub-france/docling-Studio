# MCP document server

Docling Studio exposes its parsed documents to AI agents (Claude Code, Claude
Desktop, any [MCP](https://modelcontextprotocol.io) client) for **Chunkless
RAG**: no chunks, no embeddings, no vector store. An agent can:

- find a document and read its map before any text;
- read only the sections the question needs, under a token budget;
- cite what it read with anchors the server verifies.

Two cards then show the result: the passage on its page, and where the whole
answer came from, with the share of the document that was read.

It is off by default and has **no authentication**. Enable it for local
agent work, and put it behind an authenticating proxy anywhere else.

## Enable it

The MCP SDK ships with the backend. `MCP_ENABLED` is the only switch, and it
gates the HTTP transport only. The stdio process is spawned by the client
itself, and that spawn is the authorisation.

| Run | Enable | Endpoint |
|-----|--------|----------|
| From source | `MCP_ENABLED=true` in `.env`, restart the backend | `http://localhost:8000/mcp` (or `:3000/mcp` through the Vite dev server) |
| Docker Compose | `MCP_ENABLED=true docker compose up` | `http://localhost:3000/mcp`, through nginx |
| stdio | nothing to enable | `mcp_stdio.py`, spawned by the client |

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_ENABLED` | `false` | Mounts `POST /mcp` on the backend. |
| `MCP_ALLOWED_HOSTS` | `127.0.0.1:*,localhost:*,[::1]:*` | Host allow-list (DNS-rebinding protection). Empty means the default; `*` delegates the check to a fronting proxy. |
| `MCP_STUDIO_BASE_URL` | empty (`http://localhost:3000` in compose) | Where citation deep links point. Empty: no deep links. Live in Settings. |
| `MCP_MAX_READ_TOKENS` | `4000` | Ceiling on one read. A client may ask for less, never more. Live in Settings. |
| `MCP_MAX_ROUNDS` | `5` | Round cap of the loop (1–20), stated by the `chunkless_rag` prompt and counted by the sources card. Live in Settings. |
| `MCP_APPS_ENABLED` | `true` | Publishes the MCP Apps sources card, `show_sources`. It degrades to text on hosts without UI support. |
| `MCP_CITATION_CARD` | `false` | Also publishes the citation card, `show_citation`. Off by default: a model offered it called it on its own before every sources card, which already shows each cited passage on its page. |

## Configure from Studio

**Settings → MCP server** shows the HTTP transport and edits three budgets
with no restart.

- **Status**: whether `/mcp` is mounted, the URL a client should use, and a
  warning when the browser's host is not in `MCP_ALLOWED_HOSTS` (a client on
  that URL would get a 421).
- **Connect a client**: the Claude Desktop config (through `mcp-remote`) and
  the Claude Code command, ready to copy.
- **Published by the server**: the tools, cards and prompts the running server
  publishes, read from the server itself.
- **Live settings**: `MCP_MAX_ROUNDS`, `MCP_MAX_READ_TOKENS` and
  `MCP_STUDIO_BASE_URL`. The environment gives the defaults; a saved value is
  stored in Studio's database, marked `db`, and used from the next tool call.
  *Reset to environment* drops the saved values. The stdio server reads them
  at its next launch.
- **Restart-only settings**: `MCP_ENABLED`, `MCP_ALLOWED_HOSTS`,
  `MCP_APPS_ENABLED` and `MCP_CITATION_CARD`, shown with their values.

Two limits:

- The round cap also appears in the server instructions, which a client reads
  once, when it connects. Over HTTP they keep the boot-time value: restart the
  backend, then the client, to align them.
- The restart-only settings stay in the environment on purpose. The admin API
  has no authentication, and `MCP_ALLOWED_HOSTS` is the DNS-rebinding guard,
  so neither the switch nor the guard can be changed from it. The two card
  flags change the tool list, which Claude Desktop rereads only on a full
  restart: change the variable, restart the backend, then quit Claude Desktop
  with Cmd+Q (closing the window is not enough) and relaunch it.

On a Hugging Face Space (`DEPLOYMENT_MODE=huggingface`) the section is
read-only.

The routes behind it: `GET/PUT/DELETE /api/config/mcp` for the budgets,
`GET /api/mcp/server` for the running server.

## Connect a client

Claude Code, over HTTP:

```bash
claude mcp add --transport http docling-studio http://localhost:3000/mcp
```

Claude Code, over stdio. Use the project venv's interpreter: a bare `python`
lacks the project's dependencies.

```bash
claude mcp add docling-studio -- \
  /abs/path/document-parser/.venv/bin/python /abs/path/document-parser/mcp_stdio.py
```

`mcp_stdio.py` reads Studio's database: `DB_PATH`, resolved against
`document-parser/` whatever the client's working directory. If the file is
missing it exits with a message rather than serving an empty database.

Claude Desktop, over HTTP, through `mcp-remote` (Settings → MCP server gives
this block with the right URL):

```json
{
  "mcpServers": {
    "docling-studio": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:3000/mcp", "--allow-http", "--transport", "http-only"]
    }
  }
}
```

Claude Desktop, over stdio, in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "docling-studio": {
      "command": "/abs/path/document-parser/.venv/bin/python",
      "args": ["/abs/path/document-parser/mcp_stdio.py"]
    }
  }
}
```

## Tools

| Tool | Takes | Returns |
|------|-------|---------|
| `find_documents` | `query?` (filename substring), `limit?` | `document_id` and current `version_id` per document; `null` means not parsed yet. |
| `get_outline` | `document_id`, `version_id?`, `depth?` | The map: sections, or pages when the document has no headings. Each entry has a `ref` and `est_tokens`. |
| `read_element` | `document_id`, `ref`, `version_id?`, `include?`, `max_tokens?`, `cursor?` | The text in `content`, one anchor per element in `citations[]`, and `span_uri` covering them all. |
| `verify_citation` | `uri`, `quote` | Whether the quote is at the anchor, server-side. |
| `show_citation` | `uri` | One passage highlighted on its page, when the reader asks to see it. Only with `MCP_CITATION_CARD=true`. Not part of the loop. |
| `show_sources` | `question`, `read`, `cited` | Where the answer came from, as one card. See [Sources](#sources). |

Every result also carries a `next_step`: what to do with it, when it applies.
The text copy of each result is compact JSON, the same as its structured
content.

One prompt, which the user invokes as a slash command:

- **`chunkless_rag`** (`document`, `question`): read the map, then run at most
  **5 rounds**. Each round picks one section, says why, reads it, and says what
  it found; the loop stops as soon as the answer is there. A `cursor`
  continuation is the same round. Then it verifies every quote and ends with
  `show_sources`, the one card of the answer. It says what is missing when 5
  rounds did not answer.

The rounds are docling-agent's loop, run by the client model, with the same
cap as Studio's own Ask (`REASONING_MAX_ITERATIONS`, 5). The server cannot
enforce the cap, since it is stateless and the client drives the loop; the
sources card counts the rounds against it and says so when it was passed.

**Reading under a budget.** `est_tokens` is what a read will cost: the text
plus about 60 tokens per element for its anchor. The map and the read count
it the same way. A read stops at the budget (1 200 tokens by default) and
returns `truncated` with a `next_cursor`. An element longer than the whole
budget is cut at a word boundary, and the cursor (`ref@offset`) resumes inside
it.

**Text before the first heading**, such as a contract's parties, gets an
outline node of its own (`kind: "preamble"`). A document with fewer than two
headings is mapped by pages instead.

## Anchors

```
dstudio://doc/{document_id}@{version_id}#{ref}
dstudio://doc/8f2a91c4@a71f0c33#/texts/91
```

- `version_id` pins the **parse**. A docling ref means nothing across two
  parses, because a re-parse renumbers the document.
- `ref` is one of:
  - a docling ref (`#/texts/91`);
  - a virtual page (`#/pages/7`);
  - a **span** covering a run of elements (`#/texts/91..#/texts/94`).
- Anchors come from the server. An agent passes them back unchanged and never
  builds one.

**Spans.** `read_element` returns `span_uri` for a quote that runs across
elements. `verify_citation` also finds a quote across consecutive elements on
its own, and answers with the smallest span that contains it.

**`verify_citation`** is the point of the contract: the server, not the model,
says what the document says. Its `status` is one of:

| Status | Meaning |
|--------|---------|
| `verified` | The quote is there. `citation` carries the precise anchor to cite (an element inside a section, or a span), its page and its `deep_link`. |
| `stale_version` | The quote is there, but a newer parse exists. |
| `quote_drift` | The quote is not at the anchor. `actual_quote` holds what is. |
| `unknown_ref` / `unknown_version` | No such element, or no such parse. |

A quote must be at least 10 characters long, and no longer than one read.
Matching ignores the formatting a model changes when it copies text:

- Unicode compatibility forms (NFKC);
- typographic quotes, apostrophes and dashes;
- soft hyphens;
- table pipes;
- whitespace.

## Sources

`show_sources(question, read, cited)` ends an answer by showing where it came
from. It is stateless: the agent passes back the anchors it already holds.

- `read`: one entry per round, in order: the `uri` its `read_element`
  returned, a one-line `why`, and what it `found`.
- `cited`: each quote it verified, as `{uri, quote}`. The server checks every
  quote again, as `verify_citation` does, so the card says *vérifiée* on the
  server's word. A bare anchor is still accepted and shows as cited, not
  verified.

The server resolves them against the one parse they all pin, then returns:

- **the rounds**: one per section read, numbered against the cap (`2/5`),
  with its `why`, what it `found`, its page, its cost and the passages cited
  from it. Each round carries `regions`: where its section sits, one block
  per column run on each page, as fractions of the page;
- **the passages**: each quote cited, with the server's status for it
  (`verified`, `quote_drift`, …, or none when no quote came), its round and
  its blocks on the page;
- **the map**: the same reads placed on the outline, in document order. Each
  section is marked `cited`, `read`, or `path` (an ancestor);
- **the segments**: every section of the document, each with the tokens of
  its own text and whether it was read, so the card can draw the whole
  document as a bar;
- **the ratio**: "2 of 5 rounds · read 2 of 25 sections — ~531 of 29,745
  tokens (1.8 %)". A section counts whole, once, even when a read stopped at
  its budget, so the figure errs against the agent. Past the cap it reads "6
  rounds, over the 5-round cap".

An anchor that does not parse, or names an element the parse does not hold,
is listed in `unknown` rather than dropped. Anchors into more than one
document or parse are refused.

On a host without MCP Apps, the result reads as a short text tree with a
Studio link per section.

## MCP Apps

On hosts that support MCP Apps (SEP-1865), `show_sources` renders an inline
card, and so does `show_citation` when `MCP_CITATION_CARD=true`. An answer
ends on one card, the sources card.

- the **citation card**, off by default, says one thing: *texte exact du
  document*. It shows the passage boxed on its page, then the passage itself,
  large; a long one folds to seven lines. No ids or hashes;
- the **sources card** has two tabs, in Studio's look:
  - **Sources**: the real page, with every round's section boxed in orange
    and numbered in the margin, and every quoted passage boxed in green.
    Beside it, the rounds against the cap; the one selected opens on its
    *pourquoi*, its *trouvé* and its quote, marked *vérifiée par le serveur*
    or *introuvable*. A click on a round turns to its page; the arrows leaf
    through the document; *Agrandir* opens the page fullscreen, boxes
    included.
  - **Détails**: the share of the document read, the rounds, the tokens
    read and the quotes verified; the whole document as a bar, one segment
    per section, with the sections read lit; and a table of the rounds with
    their pages and cost.

Both cards are light only, so they read the same off a projector whatever
the host's theme. Their labels are in French.

Page images travel only between the card and the server, through two
app-only tools (`get_citation_image`, `get_source_page`). They never enter the
model's context.

- **Rendered by** Claude Desktop, claude.ai, VS Code Copilot, Goose, Cursor,
  ChatGPT and others.
- **Not rendered by** Claude Code, which gets the same record as text.
- **Rehearse on the host you demo on.** A host fetches a card's template once
  and caches it; the template uri carries a hash of its content, so a
  redeployed card is a new resource, but a host update can still change how a
  card is framed.
- **Deep links.** With `MCP_STUDIO_BASE_URL` set, each citation carries a
  `deep_link` to `/analyses/{version_id}?ref=…&page=N`. It opens Studio on
  the pinned parse, at the page, with the element highlighted.

## Security

- **Document text is data.** Every excerpt is wrapped in `<document-content>`
  delimiters, and a closing delimiter inside the text is neutralised. The
  same applies to titles, quotes, and every string a card replays. The server
  instructions tell the agent never to follow instructions found inside them.
- **No authentication.** Anyone who can reach `/mcp` can read every document.
  Keep the server on localhost. On a Hugging Face Space, leave
  `MCP_ENABLED=false`.
- **Read-only.** No tool uploads, edits, re-analyses or stores anything.
- **Identifiers only.** Tools take identifiers, never file paths or free-form
  queries against OpenSearch or Neo4j.
- **Bounded output.** Server-side ceilings apply to reads, outline size and
  result counts, and a client can only lower them.
- **Bounded input.** A quote longer than one read is refused before any
  matching. `show_sources` takes at most 50 anchors, and its question, each
  `why` and each `found` are capped at 2 000 characters.
- **Nothing internal leaks.** A crash reaches the client as a generic error;
  the details stay in the server log.

## Limits

- No search inside a document, no multi-document questions, no `docling://`
  resources, no authentication.
