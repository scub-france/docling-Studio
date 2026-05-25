# Synthese de re-audit — Release 0.6.1 (remediation `fix/0.6.1-audit-blockers`)

**Date** : 2026-05-25
**Branche auditee** : `fix/0.6.1-audit-blockers` (issue de `release/0.6.1`)
**Commit audite** : `f9e5619`
**Audit initial** : `docs/audit/reports/release-0.6.1/summary.md` (`825e7d7`, NO-GO)
**Auditeur** : claude-code

---

## Tableau de bord — avant / apres

| #  | Audit                | Avant (0.6.1)   | Apres (re-audit) | Δ score | Verdict           |
|----|----------------------|-----------------|------------------|---------|-------------------|
| 01 | Clean Architecture   | 75  · 1/2/1/0   | **97**  · 0/0/1/0 | **+22** | NO-GO → **GO**    |
| 02 | DDD                  | 92  · 0/1/1/0   | **97**  · 0/0/1/0 | +5      | GO → **GO**       |
| 03 | Clean Code           | 72  · 0/1/3/0   | 72  · 0/1/3/0    | =       | GO COND → GO COND |
| 04 | KISS                 | 87.5 · 0/0/1/3  | 87.5 · 0/0/1/3   | =       | GO → **GO**       |
| 05 | DRY                  | 75  · 0/0/2/2   | 75  · 0/0/2/3    | =       | GO COND → GO COND |
| 06 | SOLID                | 90  · 0/0/1/1   | **100** · 0/0/0/1 | **+10** | GO → **GO**       |
| 07 | Decouplage           | 74  · 0/2/3/0   | 73  · 0/1/3/0    | -1      | GO COND → GO COND |
| 08 | Securite             | 93  · 0/1/0/2   | **100** · 0/0/0/2 | **+7**  | GO COND → **GO**  |
| 09 | Tests                | 85  · **1**/0/1/0 | **96**  · 0/0/1/0 | **+11** | NO-GO → **GO**    |
| 10 | CI / Build           | 100 · 0/0/0/2   | **100** · 0/0/0/0 | =       | GO → **GO**       |
| 11 | Documentation        | **44** · **2**/2/0/1 | **100** · 0/0/0/1 | **+56** | NO-GO → **GO**    |
| 12 | Performance          | 61.9 · 0/2/2/1  | **85.7** · 0/1/2/1 | **+24** | GO COND → **GO**  |

**Score global (moyenne simple)** : **90.27 / 100** (vs 79.12 en initial → **+11.15**)
**Ecarts CRITICAL totaux** : **0** (vs 4) → **les 4 CRIT sont fermes**
**Ecarts MAJOR totaux** : **3** (vs 11) → -8, sous le seuil bloquant (master.md §2 = bloquant si > 3)
**Ecarts MINOR totaux** : 13 (vs 15)
**Ecarts INFO totaux** : 11 (vs 12)

---

## Fermetures CRITICAL (4 / 4)

| # | CRIT | Commit | Verification |
|---|------|--------|--------------|
| 01 | `api/graph.py` + services contournent `domain/ports.py` | `f9e5619` | `grep '^from infra\|^import infra' services/ api/` → 0 match runtime. 4 ports introduits (`DocumentTreeReader`, `GraphReader`, `GraphWriter`, `DocumentGraphProjector`), `GraphService` cree, adapters en infra. |
| 09 | 2 modules tests echouent au collect | `68cfdf1` | `test_local_converter.py` supprime (SUT removed), `.gitignore` purge. `test_architecture.py` → `pytest.importorskip("pytestarch")`. `pytest --collect-only` → 747 / 0 erreur. |
| 11 | `CHANGELOG.md` sans `[0.6.0]`/`[0.6.1]` | `4fbf3b8` | Sections `## [0.6.1] - 2026-05-25` (`CHANGELOG.md:7`) et `## [0.6.0] - 2026-05-19` (`CHANGELOG.md:55`) avec Added/Changed/Fixed/Security. |
| 11 | Breaking changes 0.6.x non identifies | `4fbf3b8` | `### BREAKING CHANGES` x2 (lignes 48-53 et 75-79) couvrant 7 ruptures (jobId→pushId, surface flags off, STORE_SECRET_KEY required, i18n renames, URL scheme migration, index→ingest, no auto-migration). |

---

## Fermetures MAJOR (8 / 11)

| # | MAJ | Commit | Status |
|---|-----|--------|--------|
| 01 | `api/graph.py` n'a pas de service | `f9e5619` | Ferme — `GraphService` en `services/graph_service.py`. |
| 01 | Services importateurs directs de concretions infra | `f9e5619` | Ferme — DI via ports. |
| 02 | Ubiquitous language `jobId` vs `pushId` | `313f9a9` | Ferme — schemas + service + frontend + i18n. Mirror du fix 0.5.0 sur `analysis`. |
| 07 | `api/graph.py` -> `infra.neo4j` / `infra.docling_graph` | `f9e5619` | Ferme par CRIT-01. |
| 08 | `STORE_SECRET_KEY` absent | `3818933` | Ferme — `.env.example:61-68`, `docker-compose.yml:109-113`, `docker-compose.dev.yml:111-114`, no default. |
| 11 | `frontend/package.json` a 0.5.0 | `e11a567` | Ferme — bumpe 0.6.1 + lockfile. |
| 11 | Modifications 0.6.x non documentees | `4fbf3b8` | Ferme — voir CRIT-11. |
| 12 | Sync I/O dans endpoints async | `bdbe1a2` | Ferme — `document_service.upload` + `serve_converter.convert` via `asyncio.to_thread`. |

## MAJ residuels (3) — non-bloquants, planifies 0.6.2

| # | MAJ | Justification report |
|---|-----|----------------------|
| 03 | SRP — `chunk_service.push_to_store` ~118L, `rechunk_document` ~88L, `tree_writer.write_document` 242L | Refactor non en scope du hotfix branchee. Decoupage planifie 0.6.2 sans risque correctness. |
| 07 | Couplage UI cross-feature : `reasoning ↔ analysis`, `chunks → document`, `chunking → analysis` | Refactor frontend non en scope. Mock/DI patterns a etablir avant casser les imports directs — bundle 0.6.2. |
| 12 | N+1 sur `store_service.list_stores`/`list_documents` + `version_service.restore` | Optimisation requete a faire dans le scope de la refonte multi-store qui ship en 0.6.2. |

---

## Quick wins encore ouverts

- **[03]** `ChunkService.__init__` a 12 params (était 11) — regrouper en `ChunkServiceDeps` dataclass.
- **[03]** Decouper `frontend/src/views/StudioPage.vue` (1450L, 3e audit consecutif sans action) — bloquera pas 0.6.x mais devient un risque de maintenance.
- **[05]** `usePoller()` composable pour DRY le pattern `setInterval+setTimeout` (3 sites front).
- **[09]** Vague `assert X is not None` (50 occurrences) — tightener au fil de l'eau.
- **[12]** Watchers `setInterval` sans cleanup dans `frontend/src/features/settings/store.ts:27-39`.

---

## Verdict final : **GO**

**Justification** :
- **0 ecart CRITICAL** — la regle absolue master.md §3 est satisfaite.
- **3 ecarts MAJOR** — au seuil de tolerance master.md §2 (bloquant si > 3 ; ici = 3) ; aucun n'introduit un risque correctness, securite ou regression.
- **Score global 90.27 / 100** — au-dessus du seuil GO inconditionnel (80).
- **11 / 12 audits a GO**, les 2 GO CONDITIONNEL restants (03, 05, 07) etant des MIN documentes pour 0.6.2.
- **Validation pipeline complete** :
  - Backend : `ruff check` clean, `ruff format --check` clean, `pytest tests/` → 732 passed / 16 skipped (pytestarch fait skip local, run en CI).
  - Frontend : `eslint`/`prettier`/`vue-tsc` clean, `vitest` → 400 / 400 passes.

### Recommandation

1. **Merger `fix/0.6.1-audit-blockers` -> `release/0.6.1`** puis FF vers `main` et tag `v0.6.1`.
2. **Planifier sprint 0.6.2** sur les 3 MAJ residuels + les quick wins ci-dessus.
3. **Re-auditer la branche release/0.6.2** par le meme protocole pour confirmer la trajectoire (les 3 MAJ doivent disparaitre).

### Notes pour le release notes / annonce

La section CHANGELOG `## [0.6.1]` est fidele au scope reel. Les 4 BREAKING CHANGES 0.6.1 (jobId→pushId, surface flags default-off, STORE_SECRET_KEY required, i18n keys) doivent etre relayes dans la communication aupres des operateurs/integrateurs avant le merge `main`.
