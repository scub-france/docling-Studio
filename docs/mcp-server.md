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
| `read_element` | Read one entry, by `ref` + `document_id` (from an outline) or by the `uri` of a citation you hold. The element alone (`include="self"`) or the whole section under it (`include="section"`), capped server-side and resumable through `next_cursor`. `citations[]` gives one anchor per element; `span_uri` gives the one covering all of them. |
| `verify_citation` | Re-resolve an anchor and confirm a quote actually appears at it — including a quote that runs across several elements, which comes back as a span anchor. |
| `open_investigation` + five more | For a question that needs several passages: the server keeps the plan, grades every ref you try, bounds the retries, refuses to close over a step nobody worked, and leaves a navigation tree behind. See [Investigating](#investigating-a-question-that-needs-several-passages). |

**Nothing writes to a document.** Uploading, re-analysing and editing chunks
stay in the Studio UI and the HTTP API. The investigation journal writes, but
only to its own three tables: no document, no analysis and no chunk is touched
by anything on this surface.

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
- `#{self_ref}` is the docling reference, a virtual page ref (`#/pages/7`)
  for documents with no headings, or a **span** — `#/texts/91..#/texts/94` —
  covering everything between two elements in reading order.

`read_element` returns one **pointer** per element it read — the anchor, the
page, and a few words of preview so you can tell which passage is which. Not
the verbatim: the text is already in `content`, and sending it again doubled
every read. The full citation — quote, `sha256`, bounding box, heading
breadcrumb, deep link — comes from `verify_citation` or `show_citation`, for
the one anchor that turns out to matter.

### Citing more than one element

A docling `self_ref` names one block; a quote rarely respects that boundary.
A sentence finishes in the next paragraph, a clause is split across two list
items, a figure's number lives in the caption below it. Cited one block at a
time, such a passage is either truncated to whichever half fits a ref, or
fails verification because it is in neither.

A span is the inclusive range between two refs. It resolves like any other
anchor — text, page, provenance, crop, deep link — so reading, verifying and
showing all work on it unchanged. Two ways to get one, both server-issued
(the "never assemble an anchor" rule is unchanged):

- `read_element` returns **`span_uri`**: the anchor covering exactly what that
  read returned. It is absent when the read returned a single element, and
  when the range between the first and the last would have covered text the
  read did not return — a citation quietly including unread text would be
  worse than none.
- `verify_citation` **widens** on its own. A quote found in no single element
  is looked for across consecutive ones, and the `citation` it answers with is
  the smallest span that actually contains it. So an agent that quotes what it
  read gets back the anchor for the whole passage, without ever building one.

A span's box is the union of its members' boxes **on the page it opens on**:
a rectangle spanning two pages is not a rectangle, so the crop shows the first
page and the rest is reachable through the outline.

Every path that hands out document text obeys the same ceiling. A budget that
governed reads but not verification would not be a budget: a 300-row table
came back at 19 795 tokens through `verify_citation` before it did.

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
| `verified` | The quote is there. A partial quote counts, and a section anchor also covers the elements inside it — when the quote came from one of them, `citation` carries that precise anchor to prefer. A quote running across several elements counts too: `citation` is then the span anchor covering exactly them. |
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
| `MCP_INLINE_CITATION_IMAGE` | `false` | Put the raster back in the tool result (~21 000 tokens a call). Only for a host where the app-only fetch fails. |
| `MCP_APPS_ENABLED` | `true` | Ships the `show_citation` MCP App. Degrades to text on hosts without UI support. |
| `MCP_STUDIO_BASE_URL` | *(empty)* | Absolute base for citation deep links. Empty keeps them relative. |
| `MCP_INVESTIGATION_ENABLED` | `true` | Publishes the six journal tools, the `investigate` prompt and the investigation viewer. Off leaves the read surface byte-identical — worth knowing that five tool descriptions are read on every call, including in conversations that never investigate. |
| `MCP_MAX_ATTEMPTS_PER_STEP` | `3` | Refs one step may be tried against before it closes as `unanswered`. `1..10`. |
| `MCP_MAX_STEPS_PER_INVESTIGATION` | `12` | Ceiling on a plan. `1..50`. |

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
| `investigate` | `document`, `question` | The decomposed question: open an investigation, plan the steps, try one ref per step and read the server's verdict, close with an answer that cites only what was kept. Use `cite_answer` when one passage settles it; this when it does not. |

Neither reimplements anything: a prompt returns text the model then executes
with the same tools, which is what keeps the procedure from drifting away
from what the server actually does.

Clients list prompts once per session, so a newly added one needs a reconnect
to appear.

## Investigating: a question that needs several passages

`cite_answer` is a protocol with no memory. Each call stands alone, so nothing
counts how many refs a step has already cost, nothing decides whether the ref
an agent landed on actually answered the sub-question it was chasing, and
nothing survives the conversation. Two consequences, and the journal exists
for both.

**The model was grading its own retrieval.** Whether the anchor resolves,
whether the element carries text, whether the quote is really there — none of
those is an opinion, and all three were being settled by the party with an
interest in the answer being yes. Now the agent proposes and the server
decides. `record_attempt` returns one of:

| Outcome | Meaning |
|---------|---------|
| `kept` | The ref held up. `kept_uri` is the anchor to cite — it differs from the one you sent when verification widened a quote across element boundaries, or found the precise element inside a section. |
| `quote_drift` | The anchor is right and the quote is not in it. `actual_quote` says what is. |
| `unknown_ref` | No such element in that parse. |
| `empty_element` | It resolves and carries no text — a group, a page break. |
| `bad_anchor` | Not a well-formed `dstudio://` anchor. You built one. |
| `foreign_document` | It resolves, to another document than the one under investigation. |

A rejection costs one attempt out of `MCP_MAX_ATTEMPTS_PER_STEP`. When they
run out the step closes as `unanswered` — **that is a result, not a failure**.
The document not answering is a finding, and the answer has to say so.

**A quote is what settles a step.** A ref recorded without one comes back
`kept` — it resolves, and it is citable — but nothing about the passage was
checked, so the step stays open. Letting a bare ref close a step made
`answered` mean *the agent stopped here*, which is the model's own account of
its retrieval wearing the server's word.

**No step is skipped silently.** `close_investigation` refuses while any
planned step is still pending. A step you decide not to work — the map does
not cover it, an earlier step already settled it — is `abandon_step`, with the
reason. It leaves no attempt behind, and that absence is what tells a later
reader the step was *dropped* rather than *exhausted*: two honest outcomes,
two different findings. This rule exists because a real run planned two steps,
worked one, and published an answer asserting it had checked four sections for
the second. The record showed it had checked none.

**The exploration was thrown away.** Now every step carries its question and
its *why*, and every attempt carries the `thought` that chose the ref. Those
are recorded verbatim and **never checked** — nothing can check them. What is
checked is the anchor and the quote. Do not read a stored trace as a certified
one: `outcome` is the server's word, `thought` is the model's.

`close_investigation` applies the same rule to the answer as a whole. Every
`dstudio://` anchor in it must be one the investigation kept, and an answer
that cites nothing is accepted only when no step was answered — the honest
"the document does not say" case. An investigation that found evidence and
then wrote an unsourced paragraph is refused.

### The navigation tree

`get_investigation` returns the record twice over. `reasoning[]` is the plan
and every attempt in the order they happened. `map[]` is the same record
projected onto the document outline, **in document order**: the sections the
investigation touched, each marked `kept`, `rejected`, `visited` (tried,
verdict pending) or `path` (on the route to a marked descendant). That is the
navigation tree — where the answer came from, laid out the way the document
is.

An attempt cites an element; the outline holds sections, or virtual pages for
a document with no headings. Each attempt is attributed to the nearest section
the outline actually published, so a subsection elided by `depth` hands its
hits to its visible ancestor rather than disappearing.

It is also the resume path: `get_investigation` on an open investigation gives
an agent back everything it needs after losing its context.

### Seeing the trace, not only reading it

On a host that supports MCP Apps, `show_investigation` renders the record as a
card: the navigation tree on the left, the timeline on the right, and the two
linked — clicking a step lights the sections it reached, clicking a section
lights the steps that reached it. Each step draws its attempt budget as marks
filled left to right, so *three marks and none of them kept* reads at a glance
as a step the document did not answer; a step that was abandoned draws no
marks at all and says so.

It is the view an investigation should end on, and the `investigate` prompt
says so in as many words. Left to itself a model reaches for `show_citation`,
whose own description asks to be preferred whenever someone wants to *see* a
passage — which is most of the time. A citation card shows one passage that
held up. It cannot show the steps, the refs that did not hold up, or the parts
the document did not answer, which is everything the protocol just produced.

Two things the card does deliberately. A **thought is set in italic and its
verdict in a chip beside it**, because one is testimony and the other is
evidence, and a trace that presented them alike would be claiming something it
cannot. And the caveat is printed **on the card**, not only here: a stored
trace looks certified, and half of it is not.

It makes no call of its own beyond the handshake — everything it renders
arrives in the tool result, which is why it also works over stdio with no
backend running. It returns the same record as `get_investigation`, so call
one or the other, not both. `MCP_APPS_ENABLED=false` withholds it, and the
journal's five text tools are unaffected.

### One parse, pinned

`version_id` is fixed when the investigation opens and every ref is read
against it. A docling `self_ref` is meaningless across two parses, so an
investigation that followed a re-parse would be citing text it never read. If
the parse is superseded mid-investigation the record is flagged `stale` and
carries on against the version it started with — the quotes are still real, a
re-read would cite the current parse.

## Seeing a citation, not just reading it

The server ships two **MCP Apps** (SEP-1865, extension
`io.modelcontextprotocol/ui`), each a tool bound to a predeclared `ui://`
template. `show_citation` renders the cited passage **as an image of the page
region it was lifted from**, next to its verbatim text — `verify_citation`
says a quote is real, this shows it. `show_investigation` renders a whole
recorded investigation: the steps, every ref tried with the server's verdict
on it, and the navigation tree those verdicts draw on the document.

| Tool | Purpose |
|------|---------|
| `show_citation` | Takes a citation uri and returns the passage with a raster crop of its page region. Falls back to the citation as text on hosts that cannot render it. |
| `show_investigation` | Takes an `investigation_id` and returns the record as a card: the plan, each attempt with its verdict, and the navigation tree. Falls back to exactly what `get_investigation` returns. |

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

**Opening the page.** The rail answers *where on the page*; at 128 px it
cannot answer *what is around it*, which is the other half of showing a reader
where a quote comes from. Clicking the page (or focusing it and pressing
Enter) asks the host for the whole frame with `ui/request-display-mode` and
fetches the same raster at a readable width. Escape, the close button or the
scrim dismisses it, and the view goes back to `inline`.

Fullscreen is requested, never assumed: granting it is the host's call, and a
host that refuses still gets the overlay filling the inline frame. The
thumbnail already on screen stands in, upscaled, until the readable render
lands — it is the same page with the marker already in the right place. The
page raster has its own byte ceiling (`image_page_max_bytes`, 400 KB) separate
from the crop's 45 KB: it never travels in a tool result, so it is bounded by
what a host will hold in an iframe rather than by what a model can afford.
Both paths run the same dpi ladder, and the marker is projected at the dpi the
ladder settled on rather than the one it was asked for.

**The handshake, and why the thumbnail depends on it**

The view opens with `ui/initialize` and sends `ui/notifications/initialized`
only once the host has answered. Both matter, and for different reasons: the
notification is what allows the host to push the tool result at all, and the
*request* is what registers the view as a negotiated app — without it a host
is entitled to refuse the `tools/call` the view makes for its own page
thumbnail, which is how the rail ends up a grey rectangle that never fills in.
It now says why instead of staying blank.

The host's answer also carries `hostContext`, and the card uses two fields of
it: `theme`, because a sandboxed iframe cannot read the host's theme class and
has to be told; and `containerDimensions`, which says whether the frame's width
is fixed (fill it) or capped (grow up to it). Applying neither is how a card
ends up laid out at a width the host then cuts off. Its own breakpoints are
container queries against the card, not media queries against the window — in a
400 px frame a viewport query answers a question about the frame.

The card's own rows cannot size the card. `.body` is a grid, and its column is
floored at `minmax(0, 1fr)` rather than left implicit: an `auto` track is
`minmax(min-content, max-content)`, and an `auto` minimum has no floor — its
base size is the largest min-content contribution among the rows, and it is
allowed to exceed the grid's own content box. The anchor is `white-space:
nowrap`, so its min-content is the whole unbroken `dstudio://` URI — 722 px.
Every row of the body was laid out at that width inside a 700 px card and
clipped by `.card`'s `overflow: hidden`: every line, at the same place,
mid-word.

When the frame is fixed and the card still does not fit, the card scales.
`.card` is an `overflow: hidden` box, so content its grid cannot fit is cut off
*inside* it — mid-word, with no scrollbar, and invisible to any check on the
document's width, because the document never overflowed. `scrollWidth` reports
clipped content all the same, so the shortfall is measured and applied as
`zoom` (which takes part in layout, unlike `transform: scale()`, so the height
reported back is the height the card now occupies), bounded at 80%. The two
numbers behind that decision sit in the origin label's tooltip: `frame 921 ·
content 984` means the content was too wide; a frame larger than the content,
with no zoom applied, means the frame was — which is the one thing a
screenshot cannot tell apart.

Turn it off with `MCP_APPS_ENABLED=false`; the four text tools are unaffected.

**The image never reaches the model.** The view fetches it itself, through
`get_citation_image` — an app-only tool (`visibility: ["app"]`), which a
conforming host keeps out of the agent's tool list. That rule is the host's to
enforce: the SDK advertises every registered tool in `tools/list` and adds no
filter of its own, so on a host that ignores `visibility` a model could reach
it. What it would get is the picture it already has the text for — wasteful,
read-only, no new data. Sending the raster in the tool result cost
**21 432 tokens a call**, twice over, for a picture no reader can read;
fetching it costs zero. `kind="page"` returns a thumbnail of the whole page with
the passage's box in that image's own pixels, so the view draws a marker
without converting anything — the crop answers *what*, the thumbnail answers
*where on the page*.

Rasters are WebP, which is about half of PNG on a rendered paragraph and a
fifth of it on a scaled page — a 320 px page is ~25 KB, which would have been
~7 400 tokens through a tool result and twice that on a host that forwards
both representations of it. The crop is embedded as a `data:` URI — the
default MCP Apps CSP allows `img-src data:` and nothing else, so the view
never loads from the network, which is also why it works over stdio with no
backend running. It is rendered at 150 dpi and halved until it fits
`image_max_bytes`.

If a host cannot make the app-only fetch work, `MCP_INLINE_CITATION_IMAGE=true`
restores the old behaviour — at the old price. The view degrades on its own
either way: a failed or unanswered fetch leaves the citation intact and says
what is missing.

**Neither path consults the client's negotiated capabilities**, and that is
deliberate. `client_supports_apps()` reports what the *connection* advertised
at `initialize`, which is the same answer for a call made by the model and one
made by the view — so it can never mean "only the view may call this". It also
cannot answer yes over HTTP at all: the transport is mounted `stateless_http`,
and on the 2025-era protocol path the SDK serves each request from a fresh
connection with `client_capabilities=None`. Gating on it refused the view its
own image and left the `MCP_INLINE_CITATION_IMAGE` escape hatch dead in exactly
the case it was written for. Over stdio the same code negotiates normally; the
asymmetry was invisible until the view tried to call back.

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
  who can reach the port. Keep it on localhost. **An `investigation_id` is not
  a credential** — it is a uuid4, so it is not enumerable, but nothing checks
  who is holding one. Anyone who can reach `/mcp` can read any investigation,
  including the question someone asked. On a Hugging Face Space, keep
  `MCP_ENABLED=false`.
- **A recorded `thought` is declarative.** It is what the model said it was
  thinking, replayed later to whoever reads the investigation. Every string
  the journal hands back is run through the same delimiter defusing as
  document text, because a thought written after reading a PDF can carry
  whatever that PDF suggested.
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
not carry the SDK yet — the group is opt-in at install time. Investigations
accumulate with no retention policy: they are bounded per investigation
(steps, attempts) and per document (open count), and a deleted document takes
its investigations with it, but nothing expires them on its own.
