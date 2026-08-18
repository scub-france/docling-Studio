# Design: Admin panel — runtime configuration for reasoning mode

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

- **Issue:** #317
- **Title on issue:** [FEATURE] Admin panel — runtime configuration for reasoning mode
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-08-04
- **Status:** Accepted
- **Target milestone:** 0.7.0 — UI Redesign Maquette
- **Impacted layers:** backend: domain · api · services · persistence · infra · frontend: `features/admin-config` (new) · `features/feature-flags` · `features/settings` · `shared/i18n`
- **Audit dimensions likely touched:** Hexagonal Architecture · DDD · Security · Decoupling · Tests · Documentation
- **ADR spawned?:** no — the env-as-bootstrap / SQLite-as-override precedence is scoped to the `reasoning` namespace; promote it to an ADR when a second consumer adopts `app_settings`

---

## 1. Problem

Reasoning (#303) is configured entirely through environment variables read once at
boot: `REASONING_ENABLED`, `OLLAMA_HOST`, `REASONING_MODEL_ID`, `LLM_PROVIDER_TYPE`
(`document-parser/infra/settings.py`). `Settings` is a `frozen=True` dataclass
instantiated as a module-level singleton, and `app.state.reasoning_runner` is built at
import time by `_build_reasoning_runner()` in `main.py`.

Consequence: switching model or Ollama host means editing a `.env` and restarting the
backend. That is the main friction on the Ask panel today — trying `mistral-small3.2`
when `gpt-oss:20b` fails to produce a parseable answer (the 502 path the API itself
suggests) is an ops round-trip, not a UI action. `max_iterations` is not configurable at
all: the adapter takes `DoclingRAGAgent`'s default of 5.

Meanwhile the admin surface `/settings` (`SettingsPage.vue` → `SettingsPanel.vue`) is
purely client-side — theme, language, version, about link. There is no server write path
of any kind, and `/api/health` exposes a single boolean `reasoningAvailable`: not the
host, not the model, not the reason for an unavailability. When docling-agent is missing
or too old the runner is disabled at boot with a server-side log warning, invisible from
the UI, which simply hides the Ask tab (cf. d4d6851, dbb0a11). This issue introduces
that write path, with reasoning as its first consumer.

## 2. Goals

- [ ] An operator can enable/disable reasoning and change the Ollama URL, default model
      and `max_iterations` from `/settings`, with the change taking effect **without a
      backend restart** (runner + service rebuilt in place, `/api/health` follows).
- [ ] The configuration is **persisted in SQLite** and survives a restart; env vars act
      as bootstrap defaults, each field reports its source (`env` / `db`), and a
      "reset to environment" action drops the overrides.
- [ ] A **test-connection** action probes the given host and returns reachability plus
      the models actually installed, which drives the model field as a select; an
      unreachable host is a normal 200 with `reachable: false`, never a 500.
- [ ] The panel surfaces **read-only diagnostics** — docling-agent version + resolved
      import path, provider type, effective availability — so the boot failures behind
      d4d6851 / dbb0a11 are diagnosable from the UI.
- [ ] `max_iterations` is actually threaded into `DoclingRAGAgent` by the adapter, so
      the new knob has an effect.
- [ ] Writes are refused with 403 when `DEPLOYMENT_MODE=huggingface`; the panel stays
      readable in every deployment mode.

## 3. Non-goals

- **Authentication / RBAC.** The app has no auth today; the config endpoints inherit
  that posture. The accepted risk and its mitigation (HF read-only mode, rate limiter)
  are in §8. Auth is a milestone-level decision, not a per-endpoint one.
- **Runtime config for the other domains** (Docling Serve URL, Neo4j, OpenSearch,
  surface feature flags). This issue lays the `app_settings` groundwork; other
  namespaces follow only if the pattern holds. Tracked informally; no issue yet.
- **Providers other than Ollama.** `LLM_PROVIDER_TYPE` stays read-only in the panel —
  docling-agent is hardwired to Ollama via mellea
  (docling-project/docling-agent#26). The field is displayed as a diagnostic.
- **Per-request model override in the Ask composer.** The API already accepts
  `modelId`; the composer field shipped with #303. Whether it stays is a separate UX
  decision — this issue only sets the *default* model.
- **Karate UI e2e for the panel.** `data-e2e` selectors are laid down here (§5.6);
  the feature file is a follow-up once the panel's UX stabilizes (§9).

## 4. Context & constraints

### Existing code surface

- Backend:
  - `document-parser/infra/settings.py` — frozen env-based `Settings` singleton.
  - `document-parser/main.py` — `_build_reasoning_runner()` at module scope;
    `ReasoningService` built in `lifespan`; `/api/health` reads
    `app.state.reasoning_runner`.
  - `document-parser/infra/docling_agent_reasoning.py` — `DoclingAgentReasoningRunner`
    (constructs `DoclingRAGAgent(tools=[], backend=…)`, no `max_iterations`),
    `deps_present()`, `deps_provenance()`.
  - `document-parser/infra/llm/ollama_provider.py` — `OllamaProvider` (host + default
    model + sync `health_check` on `/api/tags`).
  - `document-parser/domain/ports.py` — `LLMProvider`, `ReasoningRunner` ports.
  - `document-parser/persistence/database.py` — authoritative `_SCHEMA`, no migration
    machinery since #279.
- Frontend:
  - `frontend/src/features/settings/ui/SettingsPanel.vue` — client-side only panel.
  - `frontend/src/features/feature-flags/store.ts` — `/api/health` snapshot; `load()`
    is memoized and has no forced-refresh path.
  - `frontend/src/pages/DocParseTab.vue` — gates the Ask tab on the `reasoning` flag.

### Hexagonal constraints

- `services/` may not import `infra/` (enforced by `tests/test_architecture.py`).
  Everything infra-flavored reaching `AppConfigService` is **constructor-injected by
  `main.py`**: env defaults as a domain VO, the Ollama probe behind a new domain port,
  the runner rebuild as a callback, diagnostics as a callback. Same pattern as
  `StoreBackendResolver.graph_writer_factory` (#audit-01).
- `api/` may not import `infra/` or `persistence/` — the router only talks to
  `AppConfigService` via `app.state` (`api/deps.py` accessor).
- New port surface: `AppSettingsRepository` (persistence) and `LLMHostProbe` (infra)
  in `domain/ports.py`.

### Deployment modes

- `latest-local` / `latest-remote`: full read-write panel.
- HF Space (`DEPLOYMENT_MODE=huggingface`): the panel renders read-only; `PUT`,
  `DELETE` and `POST …/test` return 403. The probe is included in the refusal —
  on a public Space it would let anonymous visitors aim server-side HTTP requests at
  arbitrary hosts (SSRF-as-a-service), see §8.
- Reasoning itself remains opt-in at the image level (`WITH_REASONING` build-arg,
  #254): on an image without the deps, enabling via UI persists the intent but the
  runner stays down with diagnostics explaining why. That is the designed behavior,
  not an error (the save is valid; availability is a separate observable).

### Hard constraints

- SQLite schema is authoritative (`init_db` runs `_SCHEMA` directly, no migration
  pass) — a new table is additive and safe on existing 0.6.x files.
- API contract stays camelCase Pydantic; additive only (no existing route changes —
  `/api/health` keeps its shape, its `reasoningAvailable` just starts tracking the
  runtime rebuild).
- Backend files ≤ 300 lines, functions ≤ 30 lines; frontend TS strict.

## 5. Proposed design

### 5.1 Domain

New module `domain/app_config.py` (keeps `value_objects.py` under the size cap):

```python
ConfigSource = Literal["env", "db"]

MAX_ITERATIONS_MIN = 1
MAX_ITERATIONS_MAX = 20

@dataclass(frozen=True)
class ReasoningConfig:
    enabled: bool
    ollama_host: str
    model_id: str
    max_iterations: int

@dataclass(frozen=True)
class ReasoningDiagnostics:
    deps_present: bool
    provenance: str          # "docling-agent 0.6.0 from /path" | "not importable"
    available: bool          # runner wired and reporting is_available

@dataclass(frozen=True)
class ReasoningConfigView:
    config: ReasoningConfig
    sources: dict[str, ConfigSource]   # keyed by ReasoningConfig field name
    provider_type: str                 # read-only diagnostic ("ollama")
    read_only: bool                    # deployment_mode == "huggingface"
    diagnostics: ReasoningDiagnostics

@dataclass(frozen=True)
class LLMHostProbeResult:
    reachable: bool
    models: list[str]
    error: str | None

def validate_reasoning_config(config: ReasoningConfig) -> list[str]: ...
```

`validate_reasoning_config` is a pure function returning human-readable errors:
well-formed `http(s)://` host (parseable, has a netloc), non-empty `model_id`
(≤ 200 chars), `max_iterations` within `[1, 20]`. Validation lives outside
`__post_init__` on purpose: reads must stay tolerant (a corrupt DB row falls back to
the env value instead of failing boot), only **writes** are strict.

New ports in `domain/ports.py`:

```python
class AppSettingsRepository(Protocol):
    async def get_namespace(self, namespace: str) -> dict[str, str]: ...
    async def set_many(self, namespace: str, values: dict[str, str]) -> None: ...
    async def delete_namespace(self, namespace: str) -> int: ...

@runtime_checkable
class LLMHostProbe(Protocol):
    async def probe(self, host: str) -> LLMHostProbeResult: ...
```

### 5.2 Persistence

New table in `database.py::_SCHEMA` (additive — `CREATE TABLE IF NOT EXISTS`, no
backfill; existing 0.6.x SQLite files gain it on next boot):

```sql
CREATE TABLE IF NOT EXISTS app_settings (
    namespace   TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (namespace, key)
);
```

`persistence/app_settings_repo.py::SqliteAppSettingsRepository` implements the port:
`get_namespace` (SELECT → dict), `set_many` (INSERT … ON CONFLICT DO UPDATE, one
transaction), `delete_namespace` (DELETE, returns rowcount). Values are stored as
TEXT; the service owns (de)serialization (`"true"/"false"`, stringified int).

### 5.3 Infra adapters

- `infra/llm/ollama_probe.py::OllamaProbe` implements `LLMHostProbe`: async httpx
  `GET {host}/api/tags`, 3 s timeout, maps `models[].name` (sorted) into
  `LLMHostProbeResult`. Any transport/HTTP/parse error → `reachable=False` with the
  error message; **never raises**.
- `infra/docling_agent_reasoning.py`: `DoclingAgentReasoningRunner(provider,
  max_iterations=5)`; `run()` passes `max_iterations=self._max_iterations` to
  `DoclingRAGAgent` (kwarg verified on the pinned 0.6.0 surface).
- `infra/settings.py`: new `reasoning_max_iterations: int = 5` ←
  `REASONING_MAX_ITERATIONS`, bounds-checked in `__post_init__` against the domain
  constants (infra → domain import is legal).

### 5.4 Services

New `services/app_config_service.py::AppConfigService`. Constructor (all injected by
`main.py`, zero infra imports):

```python
AppConfigService(
    repo: AppSettingsRepository,
    env_defaults: ReasoningConfig,            # from Settings
    provider_type: str,                       # settings.llm_provider_type
    read_only: bool,                          # deployment_mode == "huggingface"
    probe: LLMHostProbe,
    apply_config: Callable[[ReasoningConfig], None],       # main.py closure
    diagnostics_provider: Callable[[], ReasoningDiagnostics],  # main.py closure
)
```

Typed errors mirror `ReasoningServiceError`: `AppConfigError(http_status)`,
`AppConfigValidationError(400)`, `AppConfigReadOnlyError(403)`.

Use cases:

- `get_reasoning() -> ReasoningConfigView` — resolve effective config = persisted
  rows over `env_defaults`, tolerant parse (unparseable row → env value, source
  stays `env`), attach sources / provider type / read-only / diagnostics.
- `update_reasoning(config: ReasoningConfig) -> ReasoningConfigView` — refuse when
  `read_only`; run `validate_reasoning_config` (raise 400 with joined errors);
  persist all four keys under namespace `reasoning`; call `apply_config(effective)`;
  return the fresh view. Full-state PUT by design: the panel submits the whole form,
  so after a save every field reads `source: db` (see §6 Alternative B).
- `reset_reasoning() -> ReasoningConfigView` — refuse when `read_only`;
  `delete_namespace("reasoning")`; `apply_config(env_defaults)`; return view.
- `test_connection(host: str) -> LLMHostProbeResult` — refuse when `read_only`
  (SSRF posture, §8); validate the URL shape (400); delegate to the probe.
- `apply_effective() -> None` — resolve and `apply_config(...)`; called once by
  `lifespan` so persisted overrides take effect at boot.

Rebuild concurrency: `apply_config` swaps `app.state.reasoning_runner` and
`app.state.reasoning_service` by rebinding the attributes (single assignment,
event-loop thread). In-flight Ask runs hold a reference to the old
runner/service and complete on the old config; new requests resolve the new
one via `request.app.state`. No locking needed — no shared mutable state
inside the runner beyond the provider it was constructed with. Writes are
admin-frequency, not a hot path (`MAX_CONCURRENT_ANALYSES` untouched).

### 5.5 API

New router `api/config.py`, prefix `/api/config`, tag `config` — DDD-granular
(#269): each route is one domain operation on the runtime-config aggregate;
no screen-shaped bundling. Not excluded from the rate limiter.

| Route | Op | Errors |
|---|---|---|
| `GET /api/config/reasoning` | read effective config + sources + diagnostics | — |
| `PUT /api/config/reasoning` | replace the override set, hot-rebuild | 400 invalid · 403 read-only |
| `DELETE /api/config/reasoning` | drop overrides (reset to environment), hot-rebuild | 403 read-only |
| `POST /api/config/reasoning/test` | probe an Ollama host | 400 bad URL · 403 read-only |

`DELETE` models "reset to env" as removing the override resource — `GET` afterwards
returns the env-sourced view. The router maps `AppConfigError.http_status` exactly
like `api/reasoning.py` maps `ReasoningServiceError`.

`main.py` wiring (in `lifespan`, after `init_db` + repos):

```
_apply_reasoning_config(cfg):                 # closure over app + analysis_repo
    runner = _build_reasoning_runner(cfg)     # refactored to take ReasoningConfig
    app.state.reasoning_runner = runner
    app.state.reasoning_service = ReasoningService(runner, analysis_repo, cfg.model_id)

_reasoning_diagnostics():                     # closure over app
    ReasoningDiagnostics(deps_present(), deps_provenance(), runner.is_available…)

app.state.app_config_service = AppConfigService(…)
await app.state.app_config_service.apply_effective()   # DB overrides live from boot
```

The module-scope `app.state.reasoning_runner = _build_reasoning_runner(env_config)`
stays as the pre-lifespan default (tests importing `app` without lifespan keep the
env behavior); `lifespan` immediately replaces it with the DB-aware build.
`/api/health` is untouched code-wise — it already reads
`app.state.reasoning_runner`, which now tracks every rebuild.

### 5.6 Frontend — feature module

New `frontend/src/features/admin-config/`:

- `types.ts` — `ReasoningConfigView` (flat camelCase mirror of the wire DTO),
  `ReasoningProbeResult`, `ConfigSource`.
- `api.ts` — `getReasoningConfig()`, `putReasoningConfig(body)`,
  `resetReasoningConfig()`, `testReasoningConnection(host)` via `apiFetch`.
- `store.ts` — Pinia `admin-config` store: server `view`, editable `form`
  (enabled/ollamaHost/modelId/maxIterations), `dirty` computed, async states
  (`loading/saving/testing`), `testResult`, errors. Actions `load`, `save`, `reset`,
  `testConnection`. After a successful `save`/`reset`: `useFeatureFlagStore().reload()`
  so the sidebar + Ask tab follow the toggle without a page reload.
- `ui/ReasoningConfigSection.vue` — rendered by `SettingsPanel.vue` under a
  "Reasoning" heading: enable toggle, host input, model field (free text; becomes a
  select of installed models after a successful test — current value kept as an
  option if absent), bounded number input, Test/Save/Reset buttons, per-field `db`
  source badge, diagnostics block, read-only banner on HF.

`data-e2e` selectors (for the follow-up Karate feature): `reasoning-config-section`,
`reasoning-config-enabled`, `reasoning-config-host`, `reasoning-config-model`,
`reasoning-config-max-iterations`, `reasoning-config-test`, `reasoning-config-save`,
`reasoning-config-reset`, `reasoning-config-diagnostics`.

`features/feature-flags/store.ts` gains `reload()`: await any in-flight `load`,
drop the memo, re-fetch `/api/health`.

### 5.7 Cross-cutting (feature flags, i18n, shared types)

- The `reasoning` feature flag keeps its single source of truth
  (`/api/health.reasoningAvailable`); this design only makes the value dynamic and
  adds the `reload()` refresh path after a save.
- i18n: `settings.reasoning.*` keys, FR + EN, in `shared/i18n.ts`.
- No `shared/types.ts` change — the view types stay feature-local.

Save sequence:

```
SettingsPanel ── save ──▶ PUT /api/config/reasoning
   api/config.py ──▶ AppConfigService.update_reasoning
        validate → repo.set_many("reasoning", …) → apply_config(effective)
                                                        │ rebuild runner + service
                                                        ▼ app.state.* swapped
   ◀── 200 ReasoningConfigResponse (sources: db, fresh diagnostics)
store ──▶ featureFlags.reload() ──▶ GET /api/health (reasoningAvailable follows)
```

## 6. Alternatives considered

### Alternative A — mutable `Settings` singleton (reload env + patch in place)

- **Summary:** drop `frozen=True`, add a write path that mutates the module-level
  `settings` and rebuilds dependents; persist by rewriting `.env`.
- **Why not:** every layer reads `settings` at construction time — mutating the
  singleton gives no rebuild signal, and file-writing `.env` from a container is
  hostile to Docker/HF deployments (read-only mounts, no audit trail). The frozen
  singleton as *bootstrap defaults* + explicit override store keeps the boot
  contract intact and the write path observable.

### Alternative B — per-field PATCH with sparse overrides

- **Summary:** `PATCH` semantics where only fields explicitly touched become `db`
  overrides, leaving the rest env-tracking (an env change surfaces on restart for
  non-overridden fields).
- **Why not (now):** the panel submits the whole form anyway, so sparse tracking
  buys accuracy only for operators mixing `.env` edits with UI edits — at the cost
  of a merge matrix in the service, an ambiguous UI ("why is this field still
  env?"), and a harder reset story. Full-state PUT + explicit reset is the KISS cut;
  sources still honestly report the env → db transition. Revisit if a second
  namespace needs sparse semantics.

### Alternative C — do nothing (keep env-only config)

- **Summary:** accept the restart round-trip; document the vars better.
- **Why not:** the friction is precisely what #317 is filed against — model
  experiments on the Ask panel are an ops loop today, and boot failures
  (d4d6851, dbb0a11) stay invisible in the UI. The panel is also the groundwork
  for future runtime config consumers.

## 7. API & data contract

### Endpoints

| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
| GET | `/api/config/reasoning` | — | `ReasoningConfigResponse` | additive |
| PUT | `/api/config/reasoning` | `ReasoningConfigUpdateRequest` | `ReasoningConfigResponse` · 400 · 403 | additive |
| DELETE | `/api/config/reasoning` | — | `ReasoningConfigResponse` · 403 | additive |
| POST | `/api/config/reasoning/test` | `ReasoningProbeRequest` | `ReasoningProbeResponse` · 400 · 403 | additive |

`ReasoningConfigResponse` (camelCase `_CamelModel`):

```json
{
  "enabled": true,
  "ollamaHost": "http://localhost:11434",
  "modelId": "gpt-oss:20b",
  "maxIterations": 5,
  "sources": { "enabled": "env", "ollamaHost": "db", "modelId": "db", "maxIterations": "env" },
  "providerType": "ollama",
  "readOnly": false,
  "diagnostics": {
    "depsPresent": true,
    "provenance": "docling-agent 0.6.0 from /app/.venv/…/docling_agent/__init__.py",
    "available": true
  }
}
```

`ReasoningConfigUpdateRequest`: `{ "enabled": bool, "ollamaHost": str, "modelId":
str, "maxIterations": int }` — all four required (full-state PUT, §6-B).
`ReasoningProbeRequest`: `{ "host": str }`.
`ReasoningProbeResponse`: `{ "reachable": bool, "models": [str], "error": str|null }` —
an unreachable host is a **200** with `reachable: false`; only a malformed URL 400s.
Errors use the standard FastAPI `{ "detail": "…" }` shape.

`/api/health` — no schema change; `reasoningAvailable` now reflects runtime rebuilds.

### Persistence schema

```sql
-- Namespaced key/value override store; reasoning is the first namespace.
-- TEXT values, service-owned encoding. PK (namespace, key) → upsert-friendly.
CREATE TABLE IF NOT EXISTS app_settings (
    namespace   TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (namespace, key)
);
```

### Env vars / config

| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
| `REASONING_ENABLED` | `false` | bool-ish | now a **bootstrap default**, overridable at runtime |
| `OLLAMA_HOST` | `http://localhost:11434` | http(s) URL | bootstrap default |
| `REASONING_MODEL_ID` | `gpt-oss:20b` | non-empty | bootstrap default |
| `REASONING_MAX_ITERATIONS` | `5` | 1–20 | **new**; bootstrap default for the RAG loop bound |
| `LLM_PROVIDER_TYPE` | `ollama` | `ollama` | unchanged; read-only diagnostic in the panel |

### Breaking changes

None — additive only. New table, new routes, new optional env var; every existing
contract (health shape, reasoning route, DTOs) is untouched.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Unauthenticated config writes (no RBAC exists app-wide) let anyone on the network flip reasoning or point it at another host | Security | Medium | Medium | config-change log lines (host/model/enabled at INFO) | Accepted for self-hosted (same trust as every existing mutating route); HF Spaces hard-refuse writes (403); revisit with app-wide auth |
| Test-connection is server-side HTTP to a user-supplied URL (SSRF) | Security | Medium | Medium on public deploys | 403s in HF logs | Probe refused in HF mode; scheme restricted to http/https; 3 s timeout; response never echoes bodies, only model names |
| Hot rebuild races an in-flight Ask run | Decoupling | Low | Low | none needed | Rebind-only swap on `app.state`; in-flight runs keep the old runner reference and finish on the old config |
| Corrupt/hand-edited `app_settings` row breaks boot | Clean Code | Low | High if strict | WARN log on tolerant fallback | Reads are tolerant (bad value → env default, source `env`); only writes validate strictly |
| Enabling via UI on an image without reasoning deps looks like a no-op | Documentation | Medium | Low | diagnostics block shows `depsPresent: false` + provenance | The view pairs every toggle with availability diagnostics; README documents `WITH_REASONING` interplay |
| `max_iterations` silently ignored if the pinned agent changes its kwarg | Tests | Low | Medium | adapter unit test asserts the kwarg lands on `DoclingRAGAgent` | Pin already exact (0.6.0); test fails on surface drift |

Rollback: revert the commits — the `app_settings` table is inert for older code
(nothing reads it), so no data cleanup is required; env vars resume as the sole
config source.

## 9. Testing strategy

### Backend — pytest (`document-parser/tests/`)

- `test_app_settings_repo.py` — temp-SQLite repo: empty namespace, upsert
  (`set_many` twice), namespace isolation, `delete_namespace` count.
- `test_app_config_service.py` — fake repo/probe/callbacks: env-only view (all
  sources `env`), db-over-env precedence, tolerant parse of corrupt rows,
  validation 400s (bad host, empty model, out-of-bounds iterations), read-only
  403s on update/reset/test, `apply_config` invoked with the effective config on
  update/reset/apply_effective, probe delegation + URL-shape refusal.
- `test_config_api.py` — router + real service on a `FastAPI()` app (pattern of
  `test_reasoning_api.py`): camelCase wire shape, PUT happy path rebuilds, PUT 400 /
  403, DELETE resets sources to env, POST test 200-unreachable and 400-bad-URL.
- `test_docling_agent_reasoning.py` — extend: `max_iterations` reaches the
  `DoclingRAGAgent` constructor.
- `test_settings.py` — extend: `REASONING_MAX_ITERATIONS` parsing + bounds.
- `test_architecture.py` — no new assertions needed; it sweeps the new modules
  automatically (service must stay infra-free).

### Frontend — Vitest (`frontend/src/**/*.test.ts`)

- `features/admin-config/store.test.ts` — mocked `api.ts` + Pinia: load populates
  view+form, dirty tracking, save PUTs the form and calls
  `featureFlags.reload()`, reset action, testConnection populates models /
  unreachable path, error surfacing.
- `features/feature-flags/store.test.ts` — extend: `reload()` re-fetches and
  updates `reasoningAvailable`.
- Repo convention is logic/store tests (no `@vue/test-utils` mount tests); the
  component stays thin over the store.

### E2E — Karate UI (`e2e/`)

Out of scope for this PR (§3); `data-e2e` selectors are in place. Follow-up
feature: enable toggle → sidebar Ask tab appears without reload (`retry()` on the
flag-driven element, setup/teardown via `PUT`/`DELETE /api/config/reasoning`).

### Manual QA

1. Boot with `REASONING_ENABLED=false` → `/settings` shows the section disabled,
   sources all `env`.
2. Enable + save (Ollama up) → Ask tab appears without backend restart;
   `/api/health` shows `reasoningAvailable: true`.
3. Test connection against a live Ollama → model list populates the select; against
   a dead port → red state, no 500.
4. Restart the backend → saved config still effective (sources `db`).
5. Reset to environment → env values return, sources `env`.
6. `DEPLOYMENT_MODE=huggingface` → panel read-only, PUT refused 403.

### Performance / load

Not applicable — admin-frequency writes; the probe is bounded by a 3 s timeout and
excluded from the hot path.

## 10. Rollout & observability

### Release branch

Ships on `feature/303-reasoning-trace-v2-parse-view` together with the #303 line
(explicit exception to the one-branch-per-issue rule, requested by the author —
the runtime-config panel is the direct unblocke­r for #303 model iteration).
Target release: 0.7.0.

### Feature flag / staged rollout

No new flag: the panel section renders whenever the backend serves
`GET /api/config/reasoning` (same-repo deploys ship front+back together). The
existing `reasoning` feature flag continues to gate the Ask surface; HF Spaces get
the read-only degradation via `readOnly` in the DTO (server-enforced 403 behind it).

### Observability

- INFO log on every applied config (`enabled/host/model/max_iterations` — no
  secrets in this namespace).
- Existing boot-provenance WARN (d4d6851) unchanged; the same string is now also
  surfaced in `diagnostics.provenance`.
- Probe failures log at DEBUG (they are user-visible in the response already).

### Rollback plan

- Code revert is sufficient; the `app_settings` table is ignored by prior versions
  (additive, no FK).
- Operational kill-switch without redeploy: `DELETE /api/config/reasoning` (reset)
  or the panel toggle; env vars remain authoritative after a reset.
- No migration to reverse.

## 11. Open questions

- ~~Should the probe be allowed in HF mode?~~ Resolved: no — SSRF posture (§8).
- ~~PATCH vs PUT?~~ Resolved: full-state PUT (§6-B).
- ~~Does `DoclingRAGAgent` 0.6.0 accept `max_iterations`?~~ Verified on the pinned
  package: `DoclingRAGAgent(*, tools, backend=None, max_iterations=5, …)`.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/317
- **Related PRs / commits:** #303 line (`9e0c049`…`5511fd7`); boot-detection fixes
  `d4d6851`, `dbb0a11`; `WITH_REASONING` image split (#254, `d1ed61e`)
- **ADRs:** none planned (see header)
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide / template: `docs/architecture/adr-guide.md`, `docs/architecture/adr-template.md`
  - Audit master: `docs/audit/master.md`
  - E2E conventions: `e2e/CONVENTIONS.md`
- **External:**
  - docling-agent provider abstraction: https://github.com/docling-project/docling-agent/issues/26
  - `run_with_trace` upstream PR: https://github.com/docling-project/docling-agent/pull/39
  - Ollama tags endpoint (model listing): https://github.com/ollama/ollama/blob/main/docs/api.md#list-local-models
