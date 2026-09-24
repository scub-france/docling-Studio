# MCP document server

Docling Studio exposes its parsed documents to AI agents (Claude Code, Claude
Desktop, any [MCP](https://modelcontextprotocol.io) client). An agent can:

- find a document and read its map before any text;
- read one section under a token budget;
- cite what it read with anchors the server can verify.

For a question that needs several passages, a recorded **investigation** does
two things. The server keeps the plan and judges every ref the agent tries.
Afterwards, a navigation tree shows where the answer came from.

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
| `MCP_STUDIO_BASE_URL` | empty (`http://localhost:3000` in compose) | Where citation deep links point. Empty: no deep links. |
| `MCP_MAX_READ_TOKENS` | `4000` | Ceiling on one read. A client may ask for less, never more. |
| `MCP_APPS_ENABLED` | `true` | Publishes the two MCP Apps viewers. They degrade to text on hosts without UI support. |
| `MCP_INVESTIGATION_ENABLED` | `true` | Publishes the investigation tools, the `investigate` prompt and its viewer. |
| `MCP_MAX_ATTEMPTS_PER_STEP` | `3` | Refs one step may try before it closes as `unanswered` (`1..10`). |
| `MCP_MAX_STEPS_PER_INVESTIGATION` | `12` | Ceiling on a plan (`1..50`). |
| `MCP_CACHE_TTL_SECONDS` | `600` | Freshness hint (SEP-2549) for the tool list, prompt list and viewers. `0` disables it. |

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

Claude Desktop, in `claude_desktop_config.json`:

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
| `show_citation` | `uri` | The passage highlighted on its page (MCP Apps). |
| `open_investigation` … `get_investigation` | see [Investigations](#investigations) | |
| `show_investigation` | `investigation_id` | The investigation as a card (MCP Apps). |

Every result also carries a `next_step`: what to do with it, when it applies.

Two prompts, which the user invokes as slash commands:

- **`cite_answer`** (`document`, `question`, `evidence`): read only what the
  question needs, verify every quote, and say so when the document does not
  answer. `evidence=images` adds a `show_citation` for each quote.
- **`investigate`** (`document`, `question`): the investigation protocol.

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
| `verified` | The quote is there. `citation` carries the precise anchor to cite (an element inside a section, or a span). |
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

`bbox` comes with `coord_origin`. With `BOTTOMLEFT`, which docling emits for
PDF-native parses, `top` is the larger number.

## Investigations

1. `open_investigation(document_id, question)` pins the parse and returns the
   outline.
2. `plan_steps` records the steps (`{question, why}`), once.
3. `record_attempt(investigation_id, step_id, thought, uri, quote?)` tries an
   anchor for a step. The server decides the outcome:

   | Outcome | Meaning |
   |---------|---------|
   | `kept` | The ref held up. Cite `kept_uri`. |
   | `quote_drift` | The quote is not at the anchor. `actual_quote` holds what is. |
   | `unknown_ref` | No such element in the pinned parse. This includes an anchor from another parse of the same document. |
   | `empty_element` | The element resolves but has no text. |
   | `bad_anchor` | Not a well-formed anchor. |
   | `foreign_document` | The anchor points into another document. |

4. `abandon_step` drops a step that will not be worked, with the reason.
5. `close_investigation(investigation_id, answer)` publishes the answer.
6. `get_investigation` reads the record back, to resume or to review.
   `show_investigation` shows it as a card.

**Verdicts.** A kept ref settles a step only with a quote: without one, it is
citable but unverified. Each rejection spends one attempt. When the attempts
run out, the step closes as **`unanswered`**. That is a finding the answer
must state, not an error.

**Closing** is refused in three cases:

- a planned step is still pending;
- the answer cites an anchor the investigation did not keep;
- the answer cites nothing although a step was answered.

Concurrent writes resolve safely: a kept attempt wins over a last rejection,
and only one close lands.

**What the record holds:**

- `reasoning[]`: the steps and attempts in order. `thought` is what the
  model said and is never checked; `outcome` is the server's verdict.
- `map[]`: the same record placed on the outline, in document order. Each
  section is marked `kept`, `rejected`, `visited` or `path`. This is the
  navigation tree.

**One parse, pinned.** Every ref is read against the `version_id` fixed at
open. A newer parse flags the investigation `stale`, and it carries on. A
deleted parse leaves the record readable, without a map.

## MCP Apps

On hosts that support MCP Apps (SEP-1865), `show_citation` and
`show_investigation` render inline cards:

- the citation card shows the passage highlighted on its page, and can open
  the page full screen;
- the investigation card shows the tree, the timeline, and a page thumbnail
  per kept ref.

Page images travel only between the card and the server, through two
app-only tools (`get_citation_image`, `get_investigation_page`). They never
enter the model's context.

- **Rendered by** Claude Desktop, claude.ai, VS Code Copilot, Goose, Cursor,
  ChatGPT and others.
- **Not rendered by** Claude Code, which gets the same record as text.
- **Deep links.** With `MCP_STUDIO_BASE_URL` set, each citation carries a
  `deep_link` to `/analyses/{version_id}?ref=…&page=N`. It opens Studio on
  the pinned parse, at the page, with the element highlighted.

## Security

- **Document text is data.** Every excerpt is wrapped in `<document-content>`
  delimiters, and a closing delimiter inside the text is neutralised. The
  same applies to titles, quotes, and every string the journal replays. The
  server instructions tell the agent never to follow instructions found
  inside them.
- **No authentication.** Anyone who can reach `/mcp` can read every document
  and every investigation. An `investigation_id` is a uuid4: it cannot be
  guessed, but nothing checks who holds it. Keep the server on localhost. On
  a Hugging Face Space, leave `MCP_ENABLED=false`.
- **Writes stop at the journal.** No tool uploads, edits or re-analyses.
- **Identifiers only.** Tools take identifiers, never file paths or free-form
  queries against OpenSearch or Neo4j.
- **Bounded output.** Server-side ceilings apply to reads, outline size and
  result counts, and a client can only lower them.
- **Bounded input.** A quote longer than one read is refused before any
  matching. Questions, `why` and `thought` are capped at 2 000 characters,
  answers at 20 000.
- **Nothing internal leaks.** A crash reaches the client as a generic error;
  the details stay in the server log.

## Limits

- No search tools, no `docling://` resources, no authentication.
- Investigations have no retention policy. Deleting a document deletes its
  investigations; nothing else expires them.
