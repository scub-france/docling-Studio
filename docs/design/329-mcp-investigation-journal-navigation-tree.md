# Design: MCP investigation journal — recorded reasoning chain and the navigation tree it leaves behind

<!--
Design doc template for Docling Studio.

One design doc per tracked issue. File path convention:
  docs/design/<issue-number>-<kebab-slug>.md

Status lifecycle: Draft → In review → Accepted → Implemented (or Superseded).
Bump the Status line as the doc progresses; do not delete sections on the way.

This template is tailored to the project's architecture and conventions:
  - Backend Hexagonal Architecture / ports & adapters
    (domain → api/services/persistence/infra)
    see docs/architecture.md
  - Backend coding standards (FastAPI + Pydantic camelCase, aiosqlite,
    Python snake_case internal, max 300 lines/file, 30 lines/function)
    see docs/architecture/coding-standards.md
  - Frontend feature-based organization (Vue 3 + Pinia, one store per
    feature, Composition API, TypeScript strict, data-e2e selectors)
  - E2E with Karate UI (NOT Playwright) — see e2e/CONVENTIONS.md
  - Audit dimensions used at release gate — see docs/audit/master.md
  - ADR process for load-bearing decisions — see docs/architecture/adr-guide.md

The `/conception` command pre-fills the header block and §1 / §2 / §12 from
the linked issue. Everything else is on the author.
-->

- **Issue:** #329
- **Title on issue:** [FEATURE] MCP investigation journal — recorded reasoning chain and the navigation tree it leaves behind
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-08-30
- **Status:** Draft
- **Target milestone:** 0.8.0 — Production ready
- **Impacted layers:** backend: domain · services · persistence · infra (settings) · mcp_adapter — no api, no frontend, no e2e
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Clean Code · Security · Tests · Performance · Documentation
- **ADR spawned?:** proposed — ADR: *Docling Studio hosts no agent for the MCP surface; the server keeps investigation state and adjudicates refs, the client model does the reasoning*  *(write an ADR when choosing a library, moving a boundary, or deciding **not** to do something — see `docs/architecture/adr-guide.md`)*

---

## 1. Problem

The MCP surface (#327) hands an agent four read-only tools and a protocol
prompt. What it does not hand it is a memory. Each tool call is independent,
the server keeps no state between them, and `cite_answer` prescribes an order
without anything holding the agent to it — no attempt count, no record of what
was tried, no artefact once the answer is written.

Two things follow, and both matter. **The model grades its own retrieval:** it
decides alone whether the ref it landed on answers the question it was chasing.
A ref that does not is a wrong answer to the user, when it should have been a
second attempt — yet the server can settle it objectively, since an anchor
either resolves or it does not, a read either returns content or it does not,
and a quote either verifies or it does not. That judgement is being left to the
party least able to make it. **The exploration is thrown away:** how the
question was decomposed, which passages were opened and discarded, which one
finally carried the claim — precisely what a reader needs in order to trust the
answer — dies with the conversation.

Today `Ledger` counts tokens served and is the only server-side state in the
whole surface, deliberately so. After an answer is published nothing remains:
no sub-questions, no dead ends, no map of where in the document the answer came
from beyond the citations that made it into the prose.

## 2. Goals

- [ ] `investigations` + node tables in `persistence/database.py`, idempotent
      `CREATE TABLE IF NOT EXISTS` like every other table — no migration
      framework introduced
- [ ] `InvestigationRepository` port in `domain/ports.py`; `mcp_adapter/`
      never touches SQLite, enforced by `tests/test_architecture.py`
- [ ] Five tools (`open_investigation`, `plan_steps`, `record_attempt`,
      `close_investigation`, `get_investigation`) with the same wire
      conventions as #327 — frozen dataclasses in `wire.py`, a `next_step` on
      every result, ledger-recorded
- [ ] Server-side adjudication of an attempt: anchor resolution, then quote
      verification through the existing `verify_citation` path
- [ ] Bounded retries per step (`MCP_MAX_ATTEMPTS_PER_STEP`, default 3), a
      step closing as `unanswered` when exhausted
- [ ] `close_investigation` rejects an answer citing an anchor never kept
- [ ] `version_id` pinned at open; a superseded parse marks the investigation
      `stale` without interrupting it
- [ ] `domain/investigation_map.py` — the outline projection, pure, tested
      without DB or MCP, including the headless case where outline nodes are
      virtual pages
- [ ] `investigate` prompt; `cite_answer` stays for the single-step question
- [ ] `MCP_INVESTIGATION_ENABLED` (default `true`) — five extra tool
      descriptions are read on every call, including in conversations that
      never investigate
- [ ] Token budget respected on every path that returns document text, as on
      the existing tools
- [ ] `docs/mcp-server.md` extended: the protocol, the adjudication rules, the
      declarative nature of `thought`, and the fact that nothing authenticates
      the bearer of an `investigation_id`

## 3. Non-goals

- **No server-side reasoning loop.** Studio does not call an LLM for this
  feature. The decomposition, the choice of what to read next and the wording
  of the answer stay in the client model. `ReasoningRunner` / docling-agent
  (#303, #317) is a different surface with a different owner and is untouched
  here. *If a Studio-initiated investigation is ever wanted, it is a new issue
  and it reuses these tables — that is why the journal is persisted rather
  than returned.*
- **No HTTP API.** No `api/` route, no Pydantic DTO, no camelCase contract.
  Reading an investigation from the browser belongs to **#330**, which owns
  the endpoints and the Parse-view rendering.
- **No frontend, no e2e.** Same reason. Karate coverage lands with #330.
- **No authentication.** Unchanged posture from #327: this surface has none,
  and `docs/mcp-server.md` already says to keep it on localhost or behind an
  authenticating proxy. An `investigation_id` is a uuid4, not a credential —
  see §8.
- **No retention policy / GC.** Investigations accumulate. Bounded per
  investigation (steps, attempts) but not globally — see §11.
- **No cross-document investigation.** One investigation, one document, one
  parse. Corpus-wide work was already out of scope in #327 and stays out.
- **No mutation of the document.** The surface remains read-only in the sense
  that matters: nothing here alters a document, an analysis or a chunk. The
  journal writes only its own tables.

## 4. Context & constraints

### Existing code surface

This issue extends the **unmerged** `feature/mcp-document-server` branch — not
`release/0.7.2`. Every path below is from that branch.

| Area | Files |
|---|---|
| Touched, existing | `document-parser/domain/ports.py` · `document-parser/persistence/database.py` · `document-parser/infra/settings.py` · `document-parser/services/navigation_errors.py` · `document-parser/bootstrap/factories.py` · `document-parser/bootstrap/mcp_mount.py` · `document-parser/api/state.py` · `document-parser/mcp_adapter/{server,wire,wire_mapping,prompts}.py` · `document-parser/tests/test_architecture.py` · `.env.example` · `docs/mcp-server.md` |
| New, backend | `domain/investigation.py` · `domain/investigation_map.py` · `persistence/investigation_repo.py` · `services/investigation_service.py` · `mcp_adapter/investigation_tools.py` |
| New, tests | `tests/test_investigation_domain.py` · `tests/test_investigation_map.py` · `tests/test_investigation_service.py` · `tests/test_investigation_repo.py` · `tests/test_mcp_investigation.py` |
| Reused as-is | `domain/anchors.py` (`DocumentAnchor`, `normalise_quote`) · `domain/navigation.py` (`CitationStatus`, `DocumentOutline`, `OutlineNode`) · `services/{navigation,citation,parse_loader}.py` · `mcp_adapter/ledger.py` · `tests/navigation_fixtures.py` |

### Hexagonal Architecture constraints (backend)

The dependency direction is unchanged and the new pieces slot into the
existing lanes:

```
mcp_adapter/investigation_tools.py        driving adapter — mapping only
        │  (calls)
services/investigation_service.py         use-case orchestration
        │  (depends on)                          │ (injects)
domain/ports.InvestigationRepository      NavigationService · CitationService
        │  (implemented by)
persistence/investigation_repo.py         aiosqlite adapter
```

Three rules bite here:

1. **`mcp_adapter` may not import `persistence`, `api` or `infra`** — asserted
   by `TestMcpAdapterLayerIsolation` with an ast scan (the pytestarch rules
   above it do not resolve targets across the hyphenated project root, as that
   test's docstring explains). The tools reach `InvestigationService` and stop.
2. **Ports live only in `domain/ports.py`** — `TestPortConvention` fails any
   `Protocol` defined elsewhere. `InvestigationRepository` goes there, beside
   `AppSettingsRepository`.
3. **`domain/` imports nothing from the other layers** — so
   `investigation_map.py` takes a `DocumentOutline` and an `Investigation` as
   arguments and returns a value object. It never loads anything.

`InvestigationService` receives `NavigationService` and `CitationService` as
constructor collaborators. That is established practice on this branch —
`NavigationService(parses=…, citations=CitationService)` already does exactly
this, and `test_they_do_not_import_a_peer_service` explicitly allows
`citation_service` in its peer list. §9 covers the small change that test
needs.

### Deployment modes

Orthogonal to `CONVERSION_ENGINE`: the journal reads a parse that already
exists, so `latest-local` and `latest-remote` behave identically. The optional
`mcp` dependency group gates the whole package (`deps_present()`), unchanged.

**HF Space: `MCP_ENABLED` must stay false.** The Space is public and this
surface is unauthenticated; that is already true of #327 and this issue widens
what an anonymous caller could read (other people's investigations, including
their questions). Documented, not enforced in code — consistent with the
existing posture.

No `/api/health` feature flag: there is no frontend consumer in this lot. The
flag that would advertise it arrives with #330.

### Hard constraints

- **SQLite, additive only.** New tables, no `ALTER` on existing ones, no
  backfill. The schema in `database.py` is authoritative and re-run at every
  boot (`init_db`), so `CREATE TABLE IF NOT EXISTS` is the whole migration.
- **Enum-shaped TEXT columns carry a `CHECK`** mirroring the domain enum —
  house convention, stated at the top of `_SCHEMA`.
- **300 lines/file, 30 lines/function.** Five tools plus their wire types will
  not fit in `server.py` (283 lines) or `wire.py` (241 lines); the tools get
  their own module and the mapping extends `wire_mapping.py`.
- **MCP wire is snake_case**, not camelCase — the consumer is a model reading
  a JSON schema, not the Vue app (`wire.py` header). This is the one place the
  project's camelCase DTO rule does not apply.
- **`stateless_http=True`** on the HTTP transport: no MCP session to key state
  on. The `investigation_id` is what replaces it, and it must therefore be
  passed explicitly on every call.
- **Optional dependency.** Nothing in `domain/`, `services/` or `persistence/`
  may import the `mcp` SDK; a backend installed without `--group mcp` boots
  with the tables present and the surface unmounted.

## 5. Proposed design

### 5.1 Domain

**`domain/investigation.py`** — value objects and the state machine. Pure
dataclasses, frozen, snake_case, no I/O.

```python
class InvestigationState(StrEnum):    # open | closed | abandoned
class StepState(StrEnum):             # pending | answered | unanswered
class AttemptOutcome(StrEnum):
    KEPT = "kept"
    BAD_ANCHOR = "bad_anchor"           # not a dstudio:// uri
    FOREIGN_DOCUMENT = "foreign_document"# resolves, but not this investigation's doc
    UNKNOWN_REF = "unknown_ref"         # no such element in this parse
    EMPTY_ELEMENT = "empty_element"     # resolves, carries no text
    QUOTE_DRIFT = "quote_drift"         # anchor is fine, the quote is not there

@dataclass(frozen=True)
class Attempt:
    id: str
    step_id: str
    ordinal: int          # 1-based, within the step
    thought: str          # what the model was thinking — declarative, unchecked
    uri: str
    quote: str | None
    outcome: AttemptOutcome | None   # None while in flight
    detail: str                       # human-readable why
    kept_uri: str | None              # the anchor to cite: may be widened
    actual_quote: str | None          # on QUOTE_DRIFT
    created_at: datetime

@dataclass(frozen=True)
class Step:
    id: str
    ordinal: int
    question: str
    why: str
    state: StepState
    attempts: list[Attempt]

@dataclass(frozen=True)
class Investigation:
    id: str
    document_id: str
    version_id: str      # pinned at open — one parse per investigation
    question: str
    state: InvestigationState
    stale: bool          # the pinned parse has been superseded
    answer: str | None
    steps: list[Step]
    created_at: datetime
    closed_at: datetime | None
```

Pure predicates live with the data — `attempts_left(step, cap)`,
`is_exhausted(step, cap)`, `kept_uris(investigation)`, `next_pending(inv)`.
They are what the service asks instead of re-deriving state from row counts.

**`domain/investigation_map.py`** — the navigation tree, as a pure projection.

```python
def build_navigation_map(
    outline: DocumentOutline,
    investigation: Investigation,
) -> NavigationMap: ...
```

The algorithm, deliberately boring:

1. Index the outline's nodes by `ref`, remembering each node's ancestors
   (`build_outline` already returns a nested `OutlineNode` tree).
2. For every attempt, resolve its `kept_uri`/`uri` to the outline node that
   *contains* it. An attempt cites an element (`#/texts/91`); the outline
   holds sections (or virtual pages, `#/pages/7`, when the document has no
   headings). Containment is resolved through the section the element belongs
   to, which `parse_index` already knows — passed in as a `ref → section_ref`
   mapping so the projection stays free of services.
3. Mark each hit node `kept` / `rejected` / `visited` — `kept` wins over
   `rejected` when both apply, because a section that eventually answered is
   not a dead end.
4. Keep every ancestor of a marked node so the result is a connected tree,
   marked `path` (touched only as a route).
5. Emit in document order, carrying the `step_id`s that reached each node.

A span anchor (`#/texts/91..#/texts/94`) maps to the node containing its first
member — the same rule `CitationImageService` already applies for a crop that
straddles two pages.

**`domain/ports.py`** — one new port, beside `AppSettingsRepository`:

```python
class InvestigationRepository(Protocol):
    async def create(self, investigation: Investigation) -> None: ...
    async def find_by_id(self, investigation_id: str) -> Investigation | None: ...
    async def find_for_document(self, document_id: str, *, limit: int = 20) -> list[Investigation]: ...
    async def add_steps(self, investigation_id: str, steps: list[Step]) -> None: ...
    async def record_attempt(self, attempt: Attempt) -> None: ...
    async def settle_attempt(self, attempt: Attempt) -> None: ...
    async def set_step_state(self, step_id: str, state: StepState) -> None: ...
    async def close(self, investigation_id: str, *, answer: str, at: datetime) -> None: ...
    async def mark_stale(self, investigation_id: str) -> None: ...
    async def count_open_for_document(self, document_id: str) -> int: ...
```

`find_by_id` returns the whole aggregate, steps and attempts included — a
tree is read as a tree, and three round trips to render one card is the shape
this port exists to avoid.

### 5.2 Persistence

Three tables, not two. The issue's acceptance criterion says
`investigations` + `investigation_nodes`; a single node table would need every
step column nullable for attempt rows and vice versa, which forfeits the
`CHECK`-per-enum convention that the rest of this schema is built on. **The
issue text should be amended to match this section.**

```sql
-- Investigations (#329) — one agent's recorded exploration of one parse of
-- one document. `version_id` is an analysis id, pinned at open: a docling
-- self_ref is meaningless across two parses, so an investigation that
-- followed a re-parse would be citing different text than it read.
-- `stale` records that the pinned parse has been superseded; the
-- investigation continues on it rather than being interrupted.
CREATE TABLE IF NOT EXISTS investigations (
    id           TEXT PRIMARY KEY,
    document_id  TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_id   TEXT NOT NULL,
    question     TEXT NOT NULL,
    state        TEXT NOT NULL DEFAULT 'open'
                 CHECK (state IN ('open','closed','abandoned')),
    stale        INTEGER NOT NULL DEFAULT 0 CHECK (stale IN (0,1)),
    answer       TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    closed_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_investigations_doc_created
    ON investigations(document_id, created_at DESC);

-- One sub-question of the decomposition. `ordinal` is the plan order, which
-- is also the order the timeline renders.
CREATE TABLE IF NOT EXISTS investigation_steps (
    id               TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    ordinal          INTEGER NOT NULL,
    question         TEXT NOT NULL,
    why              TEXT NOT NULL DEFAULT '',
    state            TEXT NOT NULL DEFAULT 'pending'
                     CHECK (state IN ('pending','answered','unanswered')),
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (investigation_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_investigation_steps_inv
    ON investigation_steps(investigation_id, ordinal);

-- One ref tried against one step, with the verdict the SERVER reached.
-- `thought` is what the model said it was thinking: recorded, never checked.
-- `outcome` NULL means the row was written before adjudication finished —
-- the thought is persisted first on purpose, so a crash mid-verdict loses
-- the verdict and not the reasoning.
CREATE TABLE IF NOT EXISTS investigation_attempts (
    id           TEXT PRIMARY KEY,
    step_id      TEXT NOT NULL REFERENCES investigation_steps(id) ON DELETE CASCADE,
    ordinal      INTEGER NOT NULL,
    thought      TEXT NOT NULL DEFAULT '',
    uri          TEXT NOT NULL,
    quote        TEXT,
    outcome      TEXT CHECK (outcome IN
                 ('kept','bad_anchor','foreign_document','unknown_ref',
                  'empty_element','quote_drift')),
    detail       TEXT NOT NULL DEFAULT '',
    kept_uri     TEXT,
    actual_quote TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (step_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_investigation_attempts_step
    ON investigation_attempts(step_id, ordinal);
```

No backfill: the tables are new. `ON DELETE CASCADE` from `documents` means
deleting a document takes its investigations with it, which is the only
cleanup path this lot ships (§11).

`persistence/investigation_repo.py` follows `SqliteAppSettingsRepository`
exactly — `async with get_connection() as db`, explicit `commit()`, rows to
domain objects in the adapter. `find_by_id` is three `SELECT`s in one
connection assembled into the aggregate, not a join with manual de-duplication.

The attempt cap is enforced inside a single transaction. `record_attempt`
opens `BEGIN IMMEDIATE`, counts the step's existing attempts, refuses past the
cap, inserts, and commits — so two workers racing on the same step under
`stateless_http` cannot both slip past the ceiling (§8).

### 5.3 Infra adapters

No new adapter. `infra/settings.py` gains three fields beside the existing
`mcp_*` block, read in `from_env` and validated in `__post_init__`:

| Field | Env | Default | Validation |
|---|---|---|---|
| `mcp_investigation_enabled` | `MCP_INVESTIGATION_ENABLED` | `true` | — |
| `mcp_max_attempts_per_step` | `MCP_MAX_ATTEMPTS_PER_STEP` | `3` | `1..10` |
| `mcp_max_steps_per_investigation` | `MCP_MAX_STEPS_PER_INVESTIGATION` | `12` | `1..50` |

The two caps are ceilings in the same sense as `mcp_max_read_tokens`: a client
may plan fewer steps, never more.

### 5.4 Services

**`services/investigation_service.py`** — the use cases, no implementation.
Constructed with `navigation: NavigationService`, `citations: CitationService`,
`investigations: InvestigationRepository`, `config: InvestigationConfig`
(the two caps; kept beside `NavigationConfig` in `services/navigation_config.py`
so the budgets stay in one module, as that file's docstring requires).

New errors extend the existing family in `services/navigation_errors.py`, so
`_ToolErrors` in the adapter keeps catching one base class:

| Error | HTTP hint | Raised when |
|---|---|---|
| `InvestigationNotFoundError` | 404 | unknown id |
| `InvestigationClosedError` | 409 | writing to a closed investigation |
| `StepNotFoundError` | 404 | step id not in this investigation |
| `StepSettledError` | 409 | the step is already answered or exhausted |
| `UnbackedAnswerError` | 400 | the answer cites an anchor never kept |

**`open_investigation(document, question)`**

1. `navigation.find_documents(query=document, limit=…)`; zero matches →
   `DocumentNotFoundError`, more than one → `InvalidArgumentError` naming the
   candidates (the model asks the user, it does not pick).
2. `navigation.get_outline(document_id)` — resolves and pins `version_id`,
   and the outline is returned to the caller. One round trip instead of two,
   and *map before text* becomes structural rather than advisory.
3. Refuse if the document has too many open investigations (§8, growth).
4. Persist the `Investigation` (state `open`, no steps).
5. Return id + outline + `next_step`: *decompose, then call `plan_steps`*.

**`plan_steps(investigation_id, steps)`**

Validates state `open`, non-empty questions, and `len(steps) <= cap`. Persists
in order. Returns the first pending step and the per-step attempt budget.
Callable once — a second call on a planned investigation is
`InvestigationClosedError`'s sibling case, rejected rather than appended to,
because a plan that grows while it is being executed is not a plan.

**`record_attempt(investigation_id, step_id, thought, uri, quote=None)`** —
the core. Order matters:

1. Load the investigation; reject unless `open`. Load the step; reject unless
   `pending`.
2. **Persist the attempt first**, `outcome = NULL`. The thought is recorded
   before anything can fail: historisation must not be contingent on the
   verdict.
3. Adjudicate, first failure wins:
   - `DocumentAnchor.parse(uri)` raises → `BAD_ANCHOR`.
   - `anchor.document_id != investigation.document_id` → `FOREIGN_DOCUMENT`.
   - `navigation.read_element(…, include="self", version_id=pinned)`:
     `RefNotFoundError` → `UNKNOWN_REF`; empty text → `EMPTY_ELEMENT`.
   - With a quote: `citations.verify_citation(uri, quote)` —
     `verified` → `KEPT`; `stale_version` → `KEPT` **and** `mark_stale`;
     `quote_drift` → `QUOTE_DRIFT` carrying `actual_quote`;
     `unknown_ref` / `unknown_version` → `UNKNOWN_REF`.
     When the check hands back a more precise or widened anchor
     (`CitationCheck.citation`), **that** uri is stored as `kept_uri` — the
     span-widening of #327 flows straight through.
   - Without a quote: `KEPT` on resolution alone — *I read this and it bears
     on the step*.
4. `settle_attempt` writes the outcome.
5. Step bookkeeping: `KEPT` → `answered`; otherwise, if the cap is now spent →
   `unanswered`; else it stays `pending`.
6. Compose `next_step` from the outcome and the remaining budget.

**What it does not return: the element's text.** The agent already read it
through `read_element`; sending it back would charge twice for the same
tokens, which is the mistake `perf(mcp): stop paying to send the same text
four times` already corrected once on this surface. The result carries the
verdict, the `kept_uri`, and `actual_quote` on drift — the last already
clipped by `CitationService`.

**`close_investigation(investigation_id, answer)`**

1. Reject unless `open`.
2. Extract every `dstudio://` anchor in `answer` with the `anchors.py` grammar.
3. Every one must be in `kept_uris(investigation)` → else `UnbackedAnswerError`
   listing the offenders. This is `verify_citation` applied to the answer as a
   whole.
4. An answer citing nothing is accepted **only** when no step was answered —
   the honest "the document does not say" case. Otherwise it is rejected: an
   investigation that found evidence and then wrote an unsourced answer is the
   exact failure the protocol exists to prevent.
5. Persist answer, `state = closed`, `closed_at`.

**`get_investigation(investigation_id)`**

Loads the aggregate, loads the outline for the pinned version, and calls
`build_navigation_map`. Returns both views. Works on an open investigation too
— that is the resume path after a context compaction.

Concurrency: this touches no analysis worker and is outside
`MAX_CONCURRENT_ANALYSES`. The work per call is a few SQLite statements plus
one element read, which hits the `ParseLoader` index cache (a parse is
immutable for a given analysis id, so the cache cannot go stale).

### 5.5 API

**None.** No route, no DTO, no `/api/health` field. #330 owns the HTTP
surface, and adding an unused endpoint here would be a contract nobody
consumes, frozen before its consumer exists.

### 5.6 Frontend — feature module

**None.** See §3 and #330.

### 5.7 Cross-cutting

- **MCP tools** live in `mcp_adapter/investigation_tools.py`
  (`register_investigation_tools(server, tools, ledger, config)`), called from
  `build_mcp_server` only when `MCP_INVESTIGATION_ENABLED` is set. `server.py`
  stays under its line budget and the flag has one obvious seam.
- **Wire types** extend `wire.py`; mapping extends `wire_mapping.py`. Every
  document-derived string — a step question echoed back, a `thought`, an
  `actual_quote`, an outline title in the map — goes through `neutralise()`
  on the way out. This is not ceremony: an investigation is *stored* and
  *re-served*, so a delimiter forged in a PDF and copied into a thought would
  otherwise be replayed to a later reader (§8).
- **`DocumentTools`** gains a fourth field, `investigations`. That dataclass
  exists precisely so a new use case does not change every signature between
  the composition root and the tools.
- **`bootstrap/factories.py`** — `build_document_tools` constructs the service
  with the new repository; `main.py` passes the repo in as it does for the
  others.
- **`INSTRUCTIONS`** in `server.py` gains one short paragraph, and only when
  the flag is on: point at the `investigate` prompt rather than describe the
  protocol, so the always-on cost stays a sentence.
- **`prompts.py`** — the `investigate` prompt: resolve, plan, one attempt per
  step with a thought, respect the verdict, stop at the cap, close with an
  answer that cites only kept anchors. Declarative, like the other two.
- **i18n:** none (no UI).
- **`.env.example` + `docs/mcp-server.md`:** the three variables, the
  adjudication table, and two honesty notes — a `thought` is unchecked, and an
  `investigation_id` is not a credential.

## 6. Alternatives considered

### Alternative A — a server-side agent loop (docling-agent)

- **Summary:** Studio runs the investigation itself with the reasoning stack
  already merged for #303/#317 — one MCP tool, `investigate(question)`,
  returning the finished trace. Deterministic, identical for every client,
  and immediately reusable by the Studio UI.
- **Why not:** it forces an LLM into the Studio deployment for a feature whose
  whole point is to serve clients that already have one, and it duplicates a
  loop the calling model runs better — with the user's context, their
  follow-up questions and their model choice. It also mis-locates the
  reasoning: the chain we want recorded is the *client agent's*, and a
  server-side loop would record a different agent's instead. Kept as the
  explicit fork in the proposed ADR; if a Studio-initiated investigation is
  ever wanted it writes to these same tables, which is why they are persisted.

### Alternative B — a stateless protocol, scratchpad in the prompt

- **Summary:** extend `cite_answer` to tell the model to keep its own plan and
  attempt log in the conversation, and hand the whole thing back at the end
  through one `record_investigation(payload)` call.
- **Why not:** nothing adjudicates. The retry cap becomes a suggestion, the
  verdicts are the model's own opinion of its own retrieval — the exact defect
  in §1 — and the record dies with the context window it lives in, which is
  precisely when a long investigation needs it most. It is also strictly more
  expensive: the log is re-sent on every turn.

### Alternative C — an in-memory journal, like `Ledger`

- **Summary:** keep the tree in a per-server dict. No schema, no repository,
  no port. The closest thing to code that already exists on this branch.
- **Why not:** `Ledger`'s own docstring names the flaw — over `stateless_http`
  there is no session to key on, so every client of a backend would share one
  journal, and the tally is honest about that because it is only a tally. An
  investigation is not: mixing two users' explorations, or losing one to a
  reload, is a correctness bug rather than an imprecise number. And #330 needs
  to read these from a different process entirely.

## 7. API & data contract

### Endpoints

| Method | Path | Request | Response | Breaking? |
|---|---|---|---|---|
| — | — | — | — | — |

No HTTP surface in this lot (§5.5). `/api/health` is unchanged.

### MCP tool contract

Registered only when `MCP_INVESTIGATION_ENABLED`. Read-only annotations do
**not** apply: these tools write, so they carry `read_only_hint=False`,
`idempotent_hint=False` — the first non-read-only tools on this surface, and
worth stating plainly since #327's server docstring says nothing here writes.
That sentence needs amending: nothing here writes *to a document*.

| Tool | Arguments | Returns |
|---|---|---|
| `open_investigation` | `document`, `question` | `InvestigationOpened`: `investigation_id`, `document_id`, `version_id`, `outline` (an `OutlineResult`), `max_steps`, `max_attempts_per_step`, `next_step` |
| `plan_steps` | `investigation_id`, `steps[] {question, why}` | `PlanAccepted`: `steps[] {step_id, ordinal, question}`, `first_step_id`, `attempts_per_step`, `next_step` |
| `record_attempt` | `investigation_id`, `step_id`, `thought`, `uri`, `quote?` | `AttemptSettled`: `outcome`, `detail`, `kept_uri?`, `actual_quote?`, `attempts_left`, `step_state`, `next_step_id?`, `next_step` |
| `close_investigation` | `investigation_id`, `answer` | `InvestigationClosed`: `investigation_id`, `steps_answered`, `steps_unanswered`, `citations[] (uri)`, `stale`, `next_step` |
| `get_investigation` | `investigation_id` | `InvestigationView`: `question`, `document_id`, `version_id`, `state`, `stale`, `reasoning[]`, `map[]`, `next_step` |

`reasoning[]` mirrors the aggregate — steps in ordinal order, each with its
attempts, each attempt with `thought`, `uri`, `outcome`, `detail`.

`map[]` is the navigation tree: `{ref, uri, title, kind, level, page,
status, step_ids[]}` in document order, where `status` is
`kept | rejected | visited | path`.

Every result carries `next_step`, ledger-recorded like the existing four.

### Persistence schema

See §5.2 for the DDL and the reasoning behind three tables rather than one.

### Env vars / config

| Name | Default | Allowed | Notes |
|---|---|---|---|
| `MCP_INVESTIGATION_ENABLED` | `true` | bool | Registers the five tools. Off leaves #327's surface untouched and the tables unused. |
| `MCP_MAX_ATTEMPTS_PER_STEP` | `3` | `1..10` | Server-side ceiling; a step that spends it closes `unanswered`. |
| `MCP_MAX_STEPS_PER_INVESTIGATION` | `12` | `1..50` | Ceiling on a plan. |

### Breaking changes

**Additive only.** New tables, new optional env vars, new tools behind a flag.
The four existing tools, their wire types and the two existing prompts are
untouched. One documentation correction: `mcp_adapter/server.py`'s "Read-only
by design. Nothing in this package writes" now means *nothing writes to a
document* — the journal writes its own tables.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|---|---|---|---|---|---|
| An `investigation_id` is not a credential: anyone who can reach `/mcp` can read any investigation, including its question | Security | High where exposed | Medium — discloses what someone asked of a document | Only by inspection | Unchanged posture: localhost or authenticating proxy, stated in `docs/mcp-server.md`; ids are uuid4 so they are not enumerable; **HF Space keeps `MCP_ENABLED=false`** |
| Stored prompt injection: a delimiter or instruction lifted from a PDF into a `thought`, replayed later by `get_investigation` to another agent | Security | Medium | High — the replay looks like server text, not document text | A crafted fixture in the test suite | `neutralise()` on **every** stored string on the way out, and the `<document-content>` wrapper on anything document-derived — the rule #327 applies to titles and quotes, extended to journal fields |
| Two workers race the attempt cap under `stateless_http`, so a step gets more than its budget | Clean Code / correctness | Low | Low — an extra retry | A concurrency test with two overlapping calls | Count-and-insert inside one `BEGIN IMMEDIATE` transaction in the repository (§5.2) |
| Unbounded growth: an agent opens investigations in a loop, or a long-lived Studio accumulates them forever | Performance | Medium | Medium — DB size, slow `find_for_document` | DB file size; index on `(document_id, created_at DESC)` keeps reads fast | Caps on steps and attempts; a per-document ceiling on *open* investigations refused at `open_investigation`; `ON DELETE CASCADE` from `documents`. **No global retention in this lot** — §11 |
| Five extra tool descriptions on every call, in conversations that never investigate | Performance | Certain | Low but constant | Token accounting against a baseline session | `MCP_INVESTIGATION_ENABLED`; `INSTRUCTIONS` gains one sentence pointing at the prompt, not the protocol |
| `record_attempt` re-reads an element the agent just read | Performance | Certain | Low | — | `ParseLoader`'s index cache; a parse is immutable per analysis id, so the read is memory-bound. The text is **not** returned (§5.4) |
| A `thought` is unchecked, but the artefact looks certified | Documentation | Medium | High — false confidence in a replayed trace | Review of `docs/mcp-server.md` and #330's rendering | Say it explicitly in the docs, in the tool description, and again in the `get_investigation` result; only anchors and quotes are verified |
| `InvestigationService` takes two peer services, and the peer-import guard is a shared allow-list that would have to be widened for all four modules | Hexagonal Architecture | Medium | Medium — a guard that stops biting | The test itself | Split `test_they_do_not_import_a_peer_service` into a per-module allow-list (§9) — strictly stronger than today |
| `domain/investigation_map.py` reaching for a service to resolve element→section containment | Hexagonal Architecture | Medium | Medium | `TestDomainLayerIsolation` | The mapping is passed in as an argument; the projection loads nothing |
| Five tools + wire types overflow the 300-line files | Clean Code | High | Low | ruff / review | Tools in their own module from the start (§5.7) |

## 9. Testing strategy

### Backend — pytest (`document-parser/tests/`, flat, no layer subdirs)

- **`test_investigation_domain.py`** — the state machine, pure: attempt
  accounting, `is_exhausted`, `kept_uris`, `next_pending`, the transitions a
  step may and may not make.
- **`test_investigation_map.py`** — the projection, pure: element→section
  containment, `kept` beating `rejected` on the same node, ancestors kept as
  `path`, document order, a span anchor mapping to its first member, and the
  **headless document** case where outline nodes are virtual `#/pages/N`.
  Built on `tests/navigation_fixtures.py`.
- **`test_investigation_service.py`** — the adjudication matrix, one case per
  `AttemptOutcome`, times quote / no-quote: `verified`, `stale_version` (kept
  **and** investigation marked stale), `quote_drift` with `actual_quote`,
  `unknown_ref`, `unknown_version`, foreign document, malformed anchor, empty
  element. Plus: the widened-span `kept_uri`; the cap spending out to
  `unanswered`; `close_investigation` rejecting an unbacked answer, accepting
  a no-citation answer when every step is unanswered, and rejecting it when
  one is answered; writes to a closed investigation; `plan_steps` twice.
- **`test_investigation_repo.py`** — round-trip of the aggregate, ordinal
  uniqueness, cascade on document delete, and the attempt-cap race (two
  overlapping `record_attempt` calls, one must lose).
- **`test_mcp_investigation.py`** — adapter mapping only: wire shapes, error
  translation to `ToolError`, `neutralise()` applied to every echoed string,
  ledger recording, and `next_step` present on every result.
- **`test_mcp_mount.py`** (extend) — flag off ⇒ the five tools are absent and
  the original four are unchanged.
- **`test_architecture.py`** (extend) — `investigation_service` added to
  `TestDocumentAgentServicesAreFrameworkFree.MODULES`, and
  `test_they_do_not_import_a_peer_service` refactored from one shared
  allow-list to a per-module mapping (`navigation_service` may import
  `citation_service`; `investigation_service` may import both) so widening it
  for the new module does not loosen it for the existing four.

### Frontend — Vitest

None. #330.

### E2E — Karate UI

None in this lot; there is no UI to drive. #330 carries the Karate coverage.
(For the record, and because it is the standing rule: Karate UI, never
Playwright.)

### Manual QA

1. `cd document-parser && uv sync --group mcp`
2. Connect Claude Desktop over stdio per `docs/mcp-server.md` (absolute
   `DB_PATH`, the venv interpreter).
3. Run the `investigate` prompt against a parsed contract with a question that
   genuinely needs two or three steps.
4. Check: a deliberately wrong ref comes back as a retry rather than an
   answer; a fabricated quote comes back `quote_drift`; a step that cannot be
   answered closes as `unanswered` and the final answer says so; the answer
   cannot be closed while citing an anchor never kept.
5. `get_investigation` returns a `map[]` whose order matches the document.

### Performance / load

No latency or throughput claim is made. Worth one measurement rather than a
suite: the token cost of a three-step investigation against the same question
answered through `cite_answer`, so the price of the protocol is a number in
the PR rather than a feeling.

## 10. Rollout & observability

### Release branch

**Branch from `feature/mcp-document-server`, not from `release/0.7.2`.** #329
extends an unmerged branch; branching from the release would mean
re-implementing #327's anchors, services and wire conventions. This is a
deliberate, stated exception to the usual "branch from the release" rule, and
it ends when the MCP branch merges. If #327 merges to `release/0.7.2` first,
rebase onto the release and the exception disappears.

### Feature flag / staged rollout

Two gates, already layered: the surface itself (`MCP_ENABLED` for HTTP, or the
client spawning `mcp_stdio.py`), then `MCP_INVESTIGATION_ENABLED` for these
five tools. Default `true` — inside a surface that is off by default. No
`/api/health` advertisement until #330 needs one.

### Observability

- `INFO` on open and close: investigation id, document id, step count, and
  answered/unanswered tallies. Low cardinality, no question text — that is
  user content and does not belong in logs.
- `WARNING` when a step exhausts its budget: the signal that either the
  document does not answer or the cap is too tight, which is exactly what an
  operator would tune.
- No new Prometheus names. `analysis_jobs.status` is untouched — this feature
  runs no jobs.

### Rollback plan

`MCP_INVESTIGATION_ENABLED=false` and restart: the tools disappear, #327's
surface is byte-identical to before, and the tables sit unused. Nothing to
migrate back — the schema change is additive and `CREATE TABLE IF NOT EXISTS`
is a no-op on rollback. Data cleanup, if wanted, is three `DROP TABLE`s; not
required, since nothing else reads them.

Existing playbooks apply unchanged: `docs/release/*` (`/release:deploy`),
`/release:rollback`, `docs/operations/*` (`/ops:incident`).

## 11. Open questions

- **Retention.** Investigations accumulate with no TTL and no GC beyond the
  document cascade. Is a retention policy wanted before 0.8.0 ships, or is a
  follow-up issue after we see real volume the right call?
- **Does `investigate` supersede `cite_answer`?** Both stay in this design —
  one for the single-step question, one for the decomposed one. If the model
  reliably picks the wrong one, the answer is probably to fold `cite_answer`
  into `investigate` with a one-step plan.
- **Should `close_investigation` accept `evidence="images"`**, closing with a
  `show_citation` per kept anchor the way `cite_answer` does?
- **Is a per-investigation attempt ceiling needed** on top of the per-step
  one, to bound a pathological plan of 12 steps × 3 attempts?
- **Is `stale` the right terminal marker for a re-parse mid-investigation**,
  or should the server offer to open a successor investigation seeded with
  the same plan against the new parse?
- **Should `record_attempt` accept several uris at once** for a step whose
  answer is spread over non-contiguous elements? Today that is several
  attempts, all `kept`, which reads fine in the tree — but it spends the
  retry budget on successes, which is arguably wrong.

## 12. References

<!--
Links to everything a future reader would want.
-->

- **Issue:** https://github.com/scub-france/docling-Studio/issues/329
- **Related PRs / commits:** parent surface #327 (`feature/mcp-document-server`, 12 commits) · consumer #330 (Studio Parse-view rendering) · #303 reasoning trace v2 (`ReasoningStepKind`, the timeline #330 projects onto)
- **ADRs:** proposed — *Studio hosts no agent for the MCP surface* (see header)
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide / template: `docs/architecture/adr-guide.md`, `docs/architecture/adr-template.md`
  - Audit master: `docs/audit/master.md`
  - E2E conventions: `e2e/CONVENTIONS.md`
  - MCP surface: `docs/mcp-server.md`
  - Reasoning trace v2: `docs/design/303-reasoning-trace-v2-parse-view.md`
- **External:** MCP specification (https://modelcontextprotocol.io) · SEP-1865 (MCP Apps) · SEP-2549 (cache hints)
