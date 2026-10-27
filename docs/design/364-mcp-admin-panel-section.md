# Design: MCP — an admin panel section: connect a client, tune the read budgets live

- **Issue:** #364
- **Title on issue:** [FEATURE] MCP — an admin panel section: connect a client, tune the read budgets live
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-10-27
- **Status:** In review
- **Target milestone:** 0.8.0 — Production ready
- **Impacted layers:** backend: domain | api | services | infra (settings) | bootstrap · frontend: features/mcp-config, features/settings · e2e
- **Audit dimensions likely touched:** Hexagonal Architecture · DRY · Security · Tests · Documentation
- **ADR spawned?:** no

---

## 1. Problem

Every MCP setting is an env var read once at startup (`infra/settings.py`), and the round cap is a constant (`MAX_ROUNDS`). Changing a budget means restarting the backend; changing the tool list also means quitting Claude Desktop entirely. Connecting a client means knowing the `mcp-remote` incantation by heart.

6 env vars + 1 constant, all read at startup. No way to see from Studio whether MCP is on, which URL to use, or which tools a client gets. The reasoning section (#317) already shows the pattern: `app_settings` overrides over env, a source per value, a reset to env.

## 2. Goals

- [ ] Routes: `GET/PUT/DELETE /api/config/mcp` (runtime config, per-field `env`/`db` source) and `GET /api/mcp/server` (running server: enabled, path, allowed hosts, apps, citation card, tools with visibility, prompts). No screen-shaped route: the client config is built in the Pinia store.
- [ ] A PUT applies on the next MCP tool call, over HTTP, with no restart; an in-flight call finishes on the previous config; the parse index cache survives.
- [ ] `chunkless_rag` and `show_sources` use the effective round cap.
- [ ] `mcp_stdio.py` applies the overrides at launch.
- [ ] 400 on out-of-bounds or malformed values; 403 on PUT/DELETE when `DEPLOYMENT_MODE=huggingface`; reset drops every `mcp` override.
- [ ] The four restart-only settings are read-only, with their env var and the procedure (restart the backend, then quit Claude Desktop with Cmd+Q and relaunch).
- [ ] A warning when the browser's host is not in `MCP_ALLOWED_HOSTS`.
- [ ] The published tools come from the built server, not from the flags.
- [ ] Tests: service precedence, validation and hot apply; API 200/400/403; prompt renders the live cap; store test; one Karate UI scenario (change the read ceiling, check the source badge, reset).
- [ ] `docs/mcp-server.md` updated. ruff, pytest, frontend lint and tests green.

## 3. Non-goals

- **Authentication** on `/mcp` or `/api/config/*`. A separate issue; until then the admin API is as open as the rest of `/api`.
- **Toggling `MCP_ENABLED` or `MCP_ALLOWED_HOSTS` at runtime.** The admin API has no authentication outside Hugging Face, and the allow-list is the DNS-rebinding guard: `/api` has no Host check, so a rebinding page could write `*` through the very surface the list does not cover. Opening an unauthenticated read-everything endpoint stays an operator decision taken in the environment.
- **A dynamic tool list** (`MCP_APPS_ENABLED`, `MCP_CITATION_CARD`). The server is built at import, before the database is open, and the stateless HTTP transport cannot send `tools/list_changed`; Claude Desktop rereads its tools only on a full restart. Shown read-only with the procedure. A "pending until next start" override can follow if asked.
- **A live round cap in the server instructions.** The instructions are a string fixed when the server is built and read by the client once, at `initialize`. Over HTTP they keep the env cap until the backend and the client restart. Dropping the number from the instructions changes the model's behaviour and is left for after BDX I/O.
- **A stdio config block** in the panel: it would publish absolute server paths over an unauthenticated API. The docs carry it.

## 4. Context & constraints

### Existing code surface
- Backend: `infra/settings.py` (MCP vars), `services/navigation_config.py` (`MAX_ROUNDS`, `NavigationConfig`), `bootstrap/factories.py::build_document_tools`, `bootstrap/builder.py` (`_wire_reasoning` pattern), `bootstrap/mcp_mount.py` (mount at import), `mcp_adapter/server.py` + `prompts.py` (cap in text), `mcp_stdio.py`, `services/app_config_service.py` (#317 precedence), `persistence/app_settings_repo.py` (namespaced KV, no schema change), `api/config.py`, `api/schemas.py`, `api/state.py`, `api/deps.py`, `main.py`.
- Frontend: `features/settings/ui/SettingsPanel.vue`, `features/admin-config/*` (pattern), `shared/i18n.ts`.
- E2E: `e2e/ui/src/test/resources/navigation/`.

### Hexagonal Architecture constraints (backend)
The MCP tools already resolve `container.document_tools` on every call (`mcp_mount._tools_from`), so a hot apply is a rebuild of `DocumentTools` plus one atomic `AppState` rebind — the same move as #317's runner rebuild. The SDK stays in `mcp_adapter/` and `bootstrap/`: the service sees the running server only through an injected status callable returning a domain value object.

### Deployment modes
All three. On the HF Space (`DEPLOYMENT_MODE=huggingface`) writes are refused (403) and the section is read-only, like Reasoning; `MCP_ENABLED` stays false there. The stdio entry point reads the same database, so panel values reach it on the next client launch.

### Hard constraints
- Depends on PR #328 (`feature/mcp-document-server`, not yet in `release/0.7.3`): this branch is stacked on it.
- BDX I/O demo on 2026-10-29: nothing here merges before it.
- Additive API; no SQLite schema change (`app_settings` is namespaced).

## 5. Proposed design

### 5.1 Domain
New `domain/mcp_config.py`:
- `McpRuntimeConfig(max_rounds: int, max_read_tokens: int, studio_base_url: str)` — the live knobs.
- `McpRuntimeConfigView(config, sources: dict[str, ConfigSource], read_only: bool)`.
- `McpToolInfo(name, visibility: tuple[str, ...], card: bool)` and `McpServerStatus(enabled, path, allowed_hosts, apps_enabled, citation_card, tools, prompts)` — what is running.
- Bounds: rounds 1–20, read ceiling 100–32 000 tokens, base URL empty or http(s), ≤ 500 chars.
- `validate_mcp_config(config) -> list[str]` (write path only; reads are tolerant).

### 5.2 Persistence
None. Namespace `mcp` in `app_settings`, keys `max_rounds`, `max_read_tokens`, `studio_base_url`.

### 5.3 Infra adapters
`Settings.mcp_max_rounds` / `MCP_MAX_ROUNDS` (default 5, bounds 1–20 checked at boot). The constant `MAX_ROUNDS` stays as the default.

### 5.4 Services
- `services/config_overrides.py`: the tolerant `pick` + parsers, moved out of `app_config_service.py` so both config services share them.
- `services/mcp_config_service.py::McpConfigService` (`get_config`, `update_config`, `reset_config`, `apply_effective`, `server_status`) with injected `repo`, `env_defaults`, `read_only`, `apply_config`, `status_provider`. Same precedence as #317: db over env, per-field source, unparseable row → env.
- `load_effective_mcp_config(repo, env)`: the resolution alone, for `mcp_stdio.py`.
- `NavigationConfig.from_runtime(config)` maps the knobs onto the budgets; `DocumentTools` carries the `config` it was built with.

Hot apply (`bootstrap/builder.py::_wire_mcp`):

```
PUT /api/config/mcp → McpConfigService.update_config
  → validate_mcp_config → repo.set_many("mcp", …)
  → apply_config(cfg) → build_document_tools(parses, cfg)   # same ParseLoader: cache kept
  → builder._update(document_tools=…)                        # one atomic rebind
next tool call → _tools_from(app) → container.document_tools  # new budgets
```

An in-flight call holds the previous `DocumentTools` and finishes on it.

### 5.5 API
`api/config.py`: `GET/PUT/DELETE /api/config/mcp`. New `api/mcp.py`: `GET /api/mcp/server`. Errors: 400 invalid, 403 read-only (the service's `http_status` hint, as in #317).

### 5.6 Frontend — feature module
New `features/mcp-config/` (one store per feature): `types.ts`, `api.ts`, `client.ts` (pure: client URL, Claude Desktop JSON, Claude Code command, host allow-list match), `store.ts` (loads both GETs, form, save, reset), `ui/McpConfigSection.vue`, mounted in `SettingsPanel.vue` under Reasoning.

`data-e2e`: `mcp-config-section`, `mcp-config-status`, `mcp-config-url`, `mcp-config-host-warning`, `mcp-config-desktop-json`, `mcp-config-copy-desktop`, `mcp-config-code-cmd`, `mcp-config-tools`, `mcp-config-max-rounds`, `mcp-config-max-read-tokens`, `mcp-config-base-url`, `mcp-config-source-max-read-tokens`, `mcp-config-save`, `mcp-config-reset`, `mcp-config-readonly`, `mcp-config-restart-only`.

### 5.7 Cross-cutting (feature flags, i18n, shared types)
No new health flag: the section reads `GET /api/mcp/server`. i18n keys under `settings.mcp.*` (fr + en).

## 6. Alternatives considered

### Alternative A — Extend `AppConfigService` with an MCP namespace

- **Summary:** add `get_mcp`/`update_mcp`/`reset_mcp` to the #317 service.
- **Why not:** its constructor is reasoning-shaped (env defaults, Ollama probe, runner rebuild, diagnostics). Two aggregates in one service grows every collaborator list; the shared part (precedence) is extracted instead.

### Alternative B — Make every MCP setting editable, rebuilding the server

- **Summary:** rebuild the `MCPServer` on change and swap the route, including `MCP_ENABLED` and the tool flags.
- **Why not:** the session manager must be entered by the parent lifespan, the clients would still need a restart to see the tool list, and the security switches would become writable from an unauthenticated API.

### Alternative C — Do nothing

- **Summary:** keep env vars and the docs.
- **Why not:** every budget tweak costs a restart, and connecting a client stays a docs lookup.

## 7. API & data contract

### Endpoints
| Method | Path | Request | Response | Breaking? |
|--------|------|---------|----------|-----------|
| GET | `/api/config/mcp` | — | `McpConfigResponse` | no (new) |
| PUT | `/api/config/mcp` | `{maxRounds, maxReadTokens, studioBaseUrl}` | `McpConfigResponse` | no (new) |
| DELETE | `/api/config/mcp` | — | `McpConfigResponse` | no (new) |
| GET | `/api/mcp/server` | — | `McpServerResponse` | no (new) |

`McpConfigResponse`: `{maxRounds, maxReadTokens, studioBaseUrl, sources: {maxRounds, maxReadTokens, studioBaseUrl}, readOnly}`.

`McpServerResponse`: `{enabled, path, allowedHosts, appsEnabled, citationCard, tools: [{name, visibility, card}], prompts}`.

### Persistence schema
No change.

### Env vars / config
| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
| `MCP_MAX_ROUNDS` | `5` | 1–20 | New. Bootstrap default; the panel overrides it. |
| `MCP_MAX_READ_TOKENS` | `4000` | ≥ 1 (panel: 100–32 000) | Now overridable. |
| `MCP_STUDIO_BASE_URL` | empty | empty or http(s) URL | Now overridable. |

### Breaking changes
None for API consumers. Internal: `build_document_tools` takes a `ParseLoader` and an `McpRuntimeConfig`; `mount_mcp_server` returns the server with its session.

## 8. Risks & mitigations

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| The model reads the boot cap in the instructions while the prompt and card show the panel's | Clean Code | Medium | Low | Card shows more rounds than its cap | Stated in the UI next to the field and in the docs; instructions change deferred (§3) |
| Anyone reaching the port rewrites the deep-link base to a third-party site | Security | Low | Medium | `db` source badge on the field | http(s) validation, source shown; same exposure as the rest of `/api`; reset to env |
| A panel value shown as active while it is not | Clean Code | Low | High on stage | — | Live and restart-only settings are split; restart-only ones are never editable |
| Hot rebuild drops the parse cache | Performance | Low | Low | Re-index latency after a save | The `ParseLoader` is built once and reused across rebuilds |
| The service or API leaks the SDK | Hexagonal Architecture | Low | Medium | Architecture tests | The SDK→domain mapping lives in `bootstrap/mcp_mount.py` |

## 9. Testing strategy

### Backend — pytest (`document-parser/tests/`)
- `test_mcp_config_service.py`: precedence, tolerant reads, validation, read-only, hot apply, reset, stdio resolution.
- `test_mcp_config_api.py`: 200/400/403 on `/api/config/mcp`, `GET /api/mcp/server`.
- `test_mcp_mount.py`: describe the mounted server (tools from the built server, visibility, disabled case).
- `test_mcp_prompts.py`: the prompt renders the live cap.
- `test_settings.py`: `MCP_MAX_ROUNDS` bounds.
- Existing `test_app_config_service.py` guards the extracted helper.

### Frontend — Vitest
- `features/mcp-config/client.test.ts`: URL, Desktop JSON, Claude Code command, host match.
- `features/mcp-config/store.test.ts`: load, dirty, save, reset, errors.

### E2E — Karate UI (`e2e/`)
- `navigation/mcp-config.feature` (`@ui`): open Settings, change the read ceiling, check the `db` badge, reset, check it is gone.

### Manual QA
`MCP_ENABLED=true`, connect Claude Desktop with the copied JSON, lower the read ceiling, ask a question: the next `read_element` is truncated at the new ceiling without a restart.

## 10. Rollout & observability

### Release branch
Stacked on `feature/mcp-document-server` (#328, base `release/0.7.3`); rebased once #328 merges. Not before BDX I/O (2026-10-29).

### Feature flag / staged rollout
None. With no override row, behaviour is exactly today's.

### Observability
One INFO line per apply: `MCP config applied: max_rounds=… max_read_tokens=… base_url=…`; one per reset with the number of rows dropped.

### Rollback plan
`DELETE /api/config/mcp` (or the panel's reset) returns to env. Reverting the code leaves harmless `mcp` rows in `app_settings`.

## 11. Open questions

- Drop the round number from the server instructions so the cap is fully live? (after BDX I/O, tested on Claude Desktop)
- Offer a "pending until next start" override for the two tool-list flags?

## 12. References

- **Issue:** https://github.com/scub-france/docling-Studio/issues/364
- **Related PRs / commits:** #328 (MCP server), #363, #317 (runtime reasoning config)
- **ADRs:** none planned
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - ADR guide / template: `docs/architecture/adr-guide.md`, `docs/architecture/adr-template.md`
  - Audit master: `docs/audit/master.md`
  - E2E conventions: `e2e/CONVENTIONS.md`
- **External:** MCP Apps (SEP-1865), `mcp-remote`
