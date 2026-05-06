# Design: Optim taille image latest-local (sortir reasoning, multi-stage, dockerignore)

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

- **Issue:** #254
- **Title on issue:** [ENHANCEMENT] Optim taille image latest-local (sortir reasoning, multi-stage, dockerignore)
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-05-06
- **Status:** Draft
- **Target milestone:** 0.6.0 — Doc-centric ingest
- **Impacted layers:** <backend: domain | api | services | persistence | infra> · <frontend: features/<name> | shared | app> · <e2e> · <infra/CI>
- **Audit dimensions likely touched:** <pick from: Hexagonal Architecture · DDD · Clean Code · KISS · DRY · SOLID · Decoupling · Security · Tests · CI/Build · Documentation · Performance>
- **ADR spawned?:** <no>  *(write an ADR when choosing a library, moving a boundary, or deciding **not** to do something — see `docs/architecture/adr-guide.md`)*

---

## 1. Problem

L'image `latest-local` empile aujourd'hui beaucoup de surface : `torch` + `torchvision` (CPU, ~800 Mo–1.2 Go), `docling>=2.80`, et — par effet de bord — `docling-agent` + `mellea` qui sont déclarés dans `requirements.txt` et donc tirés **aussi** par la cible `remote` (qui devrait être lightweight).

Le `Dockerfile` actuel souffre par ailleurs de plusieurs problèmes de build qui pénalisent la taille et le temps de rebuild : `COPY . .` se fait dans la stage `base`, donc toute modification de code Python invalide les layers `pip install` de la stage `local` (rebuild complet de torch à chaque commit) ; pas de stage builder isolée → pip + caches restent dans l'image finale ; `.dockerignore` minimal — pas d'exclusion de `tests/`, `data/`, `uploads/`, `docs/`, etc. ; reasoning (R&D, gated par `REASONING_ENABLED`) embarqué inconditionnellement dans toutes les images.

## 2. Goals

<!--
Concrete, verifiable outcomes. Convert the issue's acceptance criteria into
checkboxes here; the design is "done" when all are satisfied. Keep the list
small — five or fewer goals is a good smell.
-->

- [ ] Baseline mesurée et notée dans le design doc (`docker images` + `docker history` du top-3 layers).
- [ ] `docling-agent` + `mellea` retirés de `document-parser/requirements.txt`, déplacés dans `document-parser/requirements-reasoning.txt`.
- [ ] `Dockerfile` multi-stage (`builder` + cible finale) avec `COPY . .` repoussé après les `pip install`.
- [ ] Build-arg `WITH_REASONING=false` (défaut) supporté dans la cible `local`.
- [ ] `.dockerignore` étendu (`tests/`, `data/`, `uploads/`, `docs/`, `*.iml`, `package-lock.json`, `node_modules/`, `tools/migrate_06.py`).
- [ ] Évaluation de `torchvision` documentée (gardé ou retiré, justifié).
- [ ] Volume HF cache documenté dans `docker-compose.yml` et `docker-compose.dev.yml`.
- [ ] Smoke test : conversion locale OK sans reasoning ; reasoning OK avec `WITH_REASONING=true` + `REASONING_ENABLED=true` + Ollama joignable.
- [ ] `pytest tests/ -v` passe dans le container final.
- [ ] Réduction taille ≥ 30 % vs baseline (chiffrée dans la PR).

## 3. Non-goals

<!--
What this design explicitly does NOT try to solve — and, for each, where it
*should* be solved (follow-up issue, next milestone, different audit area).
This is the section that saves the review: naming the off-ramps up front
prevents scope creep. If you leave this empty, reviewers will fill it in
for you, badly.
-->

- **Pas de réécriture du `LocalConverter`** ni de suppression du `threading.Lock` global → suivi perf séparé (issue dédiée à ouvrir si besoin).
- **Pas de bake-in des modèles Docling** dans l'image — le compromis taille est trop défavorable. Le cache HF reste mountable via volume ; un `tools/prefetch_models.py` opt-in pourra arriver dans un autre issue.
- **Pas d'optim de l'image `embedding-service`** — autre image, autre périmètre.
- **Pas de tuning HF Space deploy** — HF Space déploie `latest-remote`, pas `latest-local`.
- **Pas de changement du moteur OCR** livré par Docling.
- **Pas de modification de l'API publique** ni du schéma SQLite — change additif/build-only.

## 4. Context & constraints

<!--
The surrounding reality the design has to live in.

### Existing code surface
List the modules / files / stores this change touches. Prefer concrete paths
over prose:
  - Backend: document-parser/<layer>/<file>.py
  - Frontend: frontend/src/features/<name>/{store,api,ui}.ts|.vue
  - Persistence: document-parser/persistence/<repo>.py + schema in database.py
  - E2E: e2e/<feature>.feature

### Hexagonal Architecture constraints (backend)
The domain layer has zero imports from api / persistence / infra, and
defines ports (abstract protocols) that `infra/` adapters implement.
Persistence imports only from domain. API never imports persistence
directly — it goes through services. Call out any change that crosses
these lines or adds / moves a port.

### Deployment modes
Docling Studio ships two images (`latest-local`, `latest-remote`) driven by
`CONVERSION_ENGINE` — and a HF Space deployment on top of `latest-remote`.
State which modes this design supports, which it does not, and how the
frontend's feature flags (`chunking`, `disclaimer`) are affected.

### Hard constraints
Compatibility (SQLite schema, API contract, Pydantic DTOs), deadlines
(milestone due date), deployment target (Docker Compose, HF Space),
performance budget (matters for Performance audit), license / privacy
(matters for Security audit).
-->

## 5. Proposed design

<!--
The recommended approach, in enough detail that a competent engineer
outside the immediate context can implement it. Describe contracts, not
code — the PR is where code lives.

Structure this section by layer. Skip a layer if it is genuinely untouched;
do not pad.

### 5.1 Domain
New or changed dataclasses / value objects / ports in `document-parser/domain/`.
No HTTP or DB concerns here. If you are adding a port (`Protocol`), give its
full signature.

### 5.2 Persistence
Schema changes (table, columns, indexes), migration plan, aiosqlite query
shape. Note whether existing rows need a backfill.

### 5.3 Infra adapters
New or changed adapters in `document-parser/infra/` (converter, chunker,
rate limiter, settings). For new env vars, give name / default / allowed
values.

### 5.4 Services
Use-case orchestration in `document-parser/services/`. Services do NOT
implement — they delegate. Describe the call sequence, error handling,
and concurrency (how does this interact with `MAX_CONCURRENT_ANALYSES`?).

### 5.5 API
Endpoint additions / changes in `document-parser/api/`. For each:
  - Method + path
  - Request DTO (Pydantic, camelCase via alias_generator)
  - Response DTO (camelCase; remember `pages_json` stays snake_case)
  - Error responses (status codes, shape)
  - Whether it is excluded from the rate limiter (like `/api/health`)

### 5.6 Frontend — feature module
Which `frontend/src/features/<name>/` folder, which Pinia store actions,
which API client calls in `api.ts`, which Vue components in `ui/`. Name
new `data-e2e` attributes here (Karate needs them).

### 5.7 Cross-cutting
Feature flags (how the backend advertises capability via `/api/health` and
how the frontend reacts), i18n strings (`shared/i18n.ts`), shared types
(`shared/types.ts`).

Prefer mermaid / ASCII for sequence and data flow. Interfaces are more
valuable than pseudocode.
-->

### 5.1 Domain

### 5.2 Persistence

### 5.3 Infra adapters

### 5.4 Services

### 5.5 API

### 5.6 Frontend — feature module

### 5.7 Cross-cutting (feature flags, i18n, shared types)

## 6. Alternatives considered

<!--
At least two genuine alternatives, each with a one-paragraph description
and the reason it was rejected. "Do nothing" is often a legitimate
alternative — name it if it is. Reviewers use this section to sanity-check
that the recommended design was a choice and not the first thing that
came to mind.

If one of the alternatives represents a significant architectural fork
(e.g. introducing a new service, replacing a library), spawn an ADR under
`docs/architecture/adrs/` and link it in §12 — the design doc captures the
local decision, the ADR captures the cross-cutting one.
-->

### Alternative A — <name>

- **Summary:**
- **Why not:**

### Alternative B — <name>

- **Summary:**
- **Why not:**

## 7. API & data contract

<!--
Make the wire contract explicit — this is what the frontend, e2e tests,
and any external consumer will code against.

### Endpoints
| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
|        |      |         |          |           |

Remember:
  - API serialization is camelCase (Pydantic `alias_generator`).
  - Backend internals stay snake_case.
  - `pages_json` is the documented exception — it carries raw
    `dataclasses.asdict()` output (snake_case).
  - Health endpoint (`/api/health`) may need new fields if this design adds
    a feature flag.

### Persistence schema
```sql
-- ALTER TABLE / CREATE TABLE statements, with reasoning
```

### Env vars / config
| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
|      |         |         |       |

### Breaking changes
Enumerate anything a consumer must change. If there are none, say so
explicitly — "additive only" is a useful commitment.
-->

## 8. Risks & mitigations

<!--
One row per non-trivial risk. Map each to an audit dimension so the
release-gate audit has a clear hook:

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|-----------|--------|---------------|------------------------|
|      | Security        |           |        |               |                        |
|      | Performance     |           |        |               |                        |
|      | Decoupling      |           |        |               |                        |

Common families to scan for:
  - **Hexagonal Architecture:** cross-layer imports, leaking HTTP into domain, adapter bypassing its port
  - **Security:** rate limiter bypass, path traversal on uploads, SSRF via
    the remote converter, unauthenticated data exposure
  - **Performance:** synchronous work on the FastAPI event loop,
    unbounded queries, new work inside `MAX_CONCURRENT_ANALYSES` budget
  - **Tests:** coverage gap on a critical path
  - **Documentation:** missing README / env var / i18n entry

A design with "no risks identified" is a design that has not been read
carefully.
-->

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
|      |                 |            |        |               |                        |

## 9. Testing strategy

<!--
How this design will be verified. Be specific — name files / suites.

### Backend — pytest (`document-parser/tests/`)
  - Unit: per-layer (`tests/domain/`, `tests/persistence/`, `tests/services/`)
  - Integration: services wired with real aiosqlite + real adapters
  - Architecture tests (if applicable): enforce import boundaries

### Frontend — Vitest (`frontend/src/**/*.test.ts`)
  - Stores: actions / getters / mocked API
  - Pure helpers (e.g. `bboxScaling.ts`-style modules): deterministic
  - Components only when behavior is non-trivial; do not test markup

### E2E — Karate UI (`e2e/`)
  - Use `data-e2e` selectors — never CSS classes (see e2e/CONVENTIONS.md)
  - `retry()` / `waitFor()` — never `Thread.sleep()` / `delay()`
  - Setup via API, verify via UI, cleanup via API
  - Tag appropriately: `@critical` / `@ui` / `@smoke` / `@regression` / `@e2e`
  - **Never Playwright** — Karate is the tool here.

### Manual QA
Steps the reviewer can run locally (`docker-compose.dev.yml` up, scenario
to reproduce). Keep it short — if the manual list is long, automate more.

### Performance / load
Required when the design claims a latency / throughput / memory property,
or touches the conversion hot path.
-->

## 10. Rollout & observability

<!--
How this change gets to production safely.

### Release branch
Which `release/X.Y.Z` is the target? Any coordination with a parallel
release (e.g. R&D branch)?

### Feature flag / staged rollout
Does the change hide behind a flag surfaced via `/api/health`? If so, what
flips the flag, and what is the default? HF Space deployments often need
`deploymentMode === 'huggingface'` gating.

### Observability
  - Logs to add / extend (structured, low-cardinality keys)
  - Metrics / counters (if added — call out any new Prometheus names)
  - New error modes to watch for in `analysis_jobs.status = FAILED`

### Rollback plan
The revert that is safe to apply at any time:
  - Which migration is reversible? Which is not?
  - Which env var flip disables the feature without a redeploy?
  - Any data cleanup needed after rollback?

Link to the existing release / ops playbooks:
  - Deployment: `docs/release/*` (also surfaced via `/release:deploy`)
  - Rollback: also surfaced via `/release:rollback`
  - Incident: `docs/operations/*` (also surfaced via `/ops:incident`)
-->

## 11. Open questions

<!--
Things the author explicitly does not know yet, phrased as questions the
reviewer can answer or redirect. Empty is allowed once the design is
Accepted — during Draft / In review, this section is where the honest
uncertainty lives. Resolve or delete each entry before shipping.
-->

- ...
- ...

## 12. References

<!--
Links to everything a future reader would want.
-->

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/254
- **Related PRs / commits:**
- **ADRs:** <ADR-NNN or "none planned">
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide / template: `docs/architecture/adr-guide.md`, `docs/architecture/adr-template.md`
  - Audit master: `docs/audit/master.md`
  - E2E conventions: `e2e/CONVENTIONS.md`
- **External:** <specs, upstream issues, dashboards, third-party docs>
