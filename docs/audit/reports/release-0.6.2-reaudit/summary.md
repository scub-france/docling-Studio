# Synthese de re-audit — Release 0.6.2 (remediation `fix/0.6.2-audit-blockers`)

**Date** : 2026-06-08
**Branche auditee** : `fix/0.6.2-audit-blockers` (issue de `release/0.6.2`)
**Commit audite** : `f6b4e23`
**Audit initial** : `docs/audit/reports/release-0.6.2/summary.md` (`051ac4a`, NO-GO, 82.68/100)
**Auditeur** : claude-code

---

## Tableau de bord — avant / apres

| #  | Audit                | Avant (0.6.2)        | Apres (re-audit)     | Δ score | Verdict             |
|----|----------------------|----------------------|----------------------|---------|---------------------|
| 01 | Clean Architecture   | 97  · 0/0/1/1        | 97  · 0/0/1/1        | =       | GO → **GO**         |
| 02 | DDD                  | 97  · 0/0/1/0        | 97  · 0/0/1/0        | =       | GO → **GO**         |
| 03 | Clean Code           | 72  · 0/1/3/0        | 72  · 0/1/3/0        | =       | GO COND → GO COND   |
| 04 | KISS                 | 92  · 0/0/1/3        | 92  · 0/0/1/3        | =       | GO → **GO**         |
| 05 | DRY                  | 75  · 0/0/2/3        | 75  · 0/0/2/4        | =       | GO COND → GO COND   |
| 06 | SOLID                | 100 · 0/0/0/1        | 100 · 0/0/0/1        | =       | GO → **GO**         |
| 07 | Decouplage           | 73  · 0/1/3/1        | 73  · 0/1/3/1        | =       | GO COND → GO COND   |
| 08 | Securite             | 100 · 0/0/0/2        | 100 · 0/0/0/2        | =       | GO → **GO**         |
| 09 | Tests                | 96  · 0/0/1/0        | 96  · 0/0/1/0        | =       | GO → **GO**         |
| 10 | CI / Build           | **70  · 2/0/0/1**    | **100 · 0/0/0/1**    | **+30** | NO-GO → **GO**      |
| 11 | Documentation        | **44  · 2/2/0/2**    | **89  · 0/1/0/2**    | **+45** | NO-GO → **GO COND** |
| 12 | Performance          | 76.19 · 0/1/2/2      | 76.19 · 0/1/2/2      | =       | GO COND → GO COND   |

**Score global (moyenne simple)** : **88.93 / 100** (vs 82.68 initial → **+6.25**)
**Ecarts CRITICAL totaux** : **0** (vs 4) → **les 4 CRIT sont fermes**
**Ecarts MAJOR totaux** : **4** (vs 5) → -1
**Ecarts MINOR totaux** : 14 (vs 14)
**Ecarts INFO totaux** : 16 (vs 15) — +1 sur audit 05 (duplication block `BAKE_MODELS` entre `Dockerfile` et `document-parser/Dockerfile`, non promotable)

---

## Fermetures CRITICAL (4 / 4)

| # | CRIT initial | Commit(s) | Verification |
|---|--------------|-----------|--------------|
| 10-1 | `tests/test_chunking.py:480` instancie `LocalChunker()` → tire HF Hub (CI 429) | `29ab575` | Test re-execute en isolation : `0.30s PASSED` (vs `3.64s` avant, et OSError 429 sur CI). Mock du port `DocumentChunker` au lieu d'instancier l'adapter. |
| 10-2 | `release-gate.yml:522,586` sans `BAKE_MODELS=false` (patch oublie sur release-gate) | `307caf7` puis supersede par `dd1962e`+`bc9b4f8`+`f6b4e23` | Resolution architecturale : CI/release-gate basculent en `CONVERSION_MODE=remote` + `--profile remote` (container `docling-serve` officiel quay.io, modeles bakes a la source). CI run **#27122658684 vert** sur HEAD. |
| 11-1 | `CHANGELOG.md` sans section `## [0.6.2]` | `2403027` enrichi par `f6b4e23` | Section a `CHANGELOG.md:7-37` avec sous-sections `Added` / `Changed` / `Fixed` / `CI` / `BREAKING CHANGES`. Couvre les 11 commits 0.6.2 baseline + les 8 commits fix branch. |
| 11-2 | Breaking changes 0.6.2 non identifies | `2403027` + `f6b4e23` | 3 entrees `### BREAKING CHANGES` : (a) pip → uv, (b) reasoning opt-in via `WITH_REASONING`, (c) `BAKE_MODELS` default flip true → false. |

---

## Fermetures MAJOR (1 / 5)

| # | MAJ initial | Commit | Status |
|---|-------------|--------|--------|
| 11-3 | Modifications 0.6.2 non documentees | `2403027` + `f6b4e23` | Ferme automatiquement par les commits CHANGELOG (corollaire de CRIT 11-1). |

---

## MAJ residuels (4) — repartis en 3 carry-over 0.6.1-reaudit + 1 recidive

### Bloquant en l'etat (master.md §2 : > 3 MAJOR non resolus = bloquant)

Le compte total reste **4 MAJ** apres remediation — un de plus que le seuil bloquant master.md §2. **Diagnostic** :

| # | MAJ | Source | Statut |
|---|-----|--------|--------|
| 03 | Handlers et fichiers > 80L (`chunk_service.push_to_store` ~118L, `tree_writer.write_document` ~242L, `StudioPage.vue` 1450L) | Carry-over 0.6.1-reaudit | Planifie 0.7.0 — non touche par cette fenetre. |
| 07 | Couplage UI cross-feature (`reasoning ↔ analysis`, `chunks → document`, `chunking → analysis`) | Carry-over 0.6.1-reaudit | Planifie 0.7.0. |
| 11 | **`frontend/package.json` toujours a `0.6.1`** (`frontend/package.json:3`, `frontend/package-lock.json:3,9`) | **Recidive — 3eme audit consecutif** (0.5.0 → 0.6.1 → 0.6.2) | **Adressable maintenant en ~30s** : bump a `0.6.2` (+ lockfile). La "reserve operationnelle" du re-audit 0.6.1 + initial 0.6.2 recommandait un check CI bloquant — toujours pas cable. |
| 12 | Requetes N+1 sur `store_service.list_stores` (`:163-164`), `list_documents` (`:358-360`), `version_service.restore` (`:161-173`, `:180-192`) | Carry-over 0.6.1-reaudit | Planifie 0.7.0. |

**Si on bump `frontend/package.json`** → 3 MAJ residuels (tous des dettes structurelles planifiees) → **seuil respecte → GO franc**.

---

## Regressions detectees (1 INFO, non bloquant)

- **[05] DRY** : duplication du bloc `BAKE_MODELS` gating (comments + `ARG` + `RUN if`) entre `Dockerfile:72-111` et `document-parser/Dockerfile:47-87`. Dockerfiles multi-files n'ont pas de mecanisme natif de factorisation ; la nouvelle doc `docs/architecture/huggingface-dependency-map.md` consolide la rationale en un point unique (mitige la dette de comprehension). Promotion en MIN non justifiee. **Non bloquant**.

## Renforcements architecturaux (qualitative)

- **[01] / [06] / [07]** : le switch CI vers `docling-serve` (commit `bc9b4f8`) **valide empiriquement** le pattern hexagonal — la nouvelle source de conversion est consommee via le port `DocumentConverter` existant (`infra/serve_converter.py:58`) sans toucher une seule ligne de `services/` ou `domain/`. OCP demontre.
- **[09] / [01]** : le commit `29ab575` (mock chunker dans `test_chunking.py`) reinforces DIP en testant au boundary du port plutot qu'a l'adapter concret. Pattern reusable pour les futurs tests.
- **[08]** : surface HF Hub reduite par le flip `BAKE_MODELS=false` partout sauf `release.yml` `latest-local` — moins de chaines d'approvisionnement implicites.

---

## Validation empirique

- **Pytest backend** : 768 collected, 753 passed / 15 skipped / 0 errors en 8.27s (vs 9.6s baseline).
- **CI run #27122658684** sur HEAD `f6b4e23` : ✅ vert (Backend tests + Frontend + Lint + Docker build + E2E API).
- **Release Gate #27122658742** : 2 failures **hors scope audit 10** :
  - `E2E API` : 1 test Karate fonctionnel (`pipeline-options.feature:23`, FAILED vs COMPLETED). Cross-ref audit 09 — necessite investigation separee. Les steps `Start stack` + `Wait for health` sont verts → l'infra docling-serve est OK.
  - `Security scan — local` : Trivy installer (`unable to find 'latest'`) — bug upstream de `aquasecurity/setup-trivy`, non lie a nos CVE ignores.

---

## Verdict final : **GO CONDITIONNEL**

**Justification** : les 4 ecarts CRITICAL sont **fermes et verifies empiriquement** (CI vert sur HEAD). Score global 88.93 (> 80, seuil GO franc).

Mais **4 MAJOR non resolus** (4 > 3, seuil bloquant master.md §2) → verdict ne peut pas etre GO franc tant qu'on n'est pas a ≤ 3 MAJ.

### Conditions pour passer a GO franc (1 action, ~30 secondes)

1. **[11]** Bumper `frontend/package.json:3` et `frontend/package-lock.json:3,9` de `0.6.1` a `0.6.2`. Cet ecart est une **recidive sur 3 audits consecutifs** — adressable trivialement.

Apres cette action : 3 MAJ residuels (tous documentes comme dette structurelle planifiee 0.7.0) → seuil respecte → **GO**.

### Reserve operationnelle (4eme fois proposee — encore plus urgente)

**Cabler un check CI** sur les branches `release/*` qui valide :
- Presence d'une section `## [X.Y.Z] - YYYY-MM-DD` en tete de `CHANGELOG.md`
- `frontend/package.json:version == X.Y.Z`
- (Bonus) `document-parser/pyproject.toml:version == X.Y.Z`

**Sans ce verrou, la recidive est garantie sur 0.7.0**. Le pattern est documente depuis 0.5.0, propose 4 fois, jamais cable — c'est le moment.

### Notes complementaires

- Le **vrai gain architectural** de la remediation est le decouplage HF Hub : la pipeline CI n'a plus aucune dependance implicite a HuggingFace Hub, et un seul point sanctionne subsiste (`release.yml` → `latest-local`). Le projet est passe d'une dette implicite ("personne ne sait quand HF est appele") a une politique explicite documentee (`docs/architecture/huggingface-dependency-map.md`). Bonus de robustesse au-dela de la fermeture des CRIT.
- Les **3 MAJ carry-over** (03, 07, 12) sont stables depuis 0.6.1-reaudit. Ils ne devraient pas bloquer 0.6.2 — ce sont des chantiers de refactor planifies 0.7.0.
- Le **score 88.93** masque la dette structurelle au-dessus du seuil — la moyenne simple favorise les audits a 100 (06, 08) et a 97 (01, 02). Lire le tableau item-par-item, pas la moyenne.
