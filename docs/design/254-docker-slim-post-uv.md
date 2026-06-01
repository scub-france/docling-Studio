# Design: Docker image slim post-uv (sortir reasoning, multi-stage, dockerignore)

<!--
Design doc template for Docling Studio.

One design doc per tracked issue. File path convention:
  docs/design/<issue-number>-<kebab-slug>.md

Status lifecycle: Draft → In review → Accepted → Implemented (or Superseded).
Bump the Status line as the doc progresses; do not delete sections on the way.
-->

- **Issue:** #254
- **Title on issue:** [ENHANCEMENT] Optim taille image latest-local (sortir reasoning, multi-stage, dockerignore)
- **Author:** Pier-Jean Malandrino
- **Date:** 2026-05-29
- **Status:** Draft
- **Target milestone:** 0.6.2 — uv + Docker slim
- **Impacted layers:** infra/CI (Dockerfile, pyproject groups, compose) · docs (README, this doc)
- **Audit dimensions likely touched:** CI/Build · Performance · Decoupling · Documentation
- **ADR spawned?:** no  *(no load-bearing library/boundary change — Docker layout choice is locally scoped)*

> **Lineage** — a first attempt was made on `release/0.6.1` (commits `975f405` + `392d316`, design doc `docs/design/254-optim-taille-image-latest-local.md`). It was never merged. This doc supersedes it and adapts the plan to the post-uv codebase (PR #289), where `requirements*.txt` no longer exist.

---

## 1. Problem

L'image `latest-local` empile aujourd'hui beaucoup de surface : `torch` + `torchvision` (CPU, ~800 Mo–1.2 Go), `docling>=2.80`, et — par effet de bord — `docling-agent` + `mellea` qui sont déclarés dans `[project.dependencies]` du `document-parser/pyproject.toml` et donc tirés **aussi** par la cible `remote` (qui devrait être lightweight).

Le `Dockerfile` post-uv améliore le caching (les `COPY pyproject.toml uv.lock` arrivent avant `uv sync`), mais souffre encore de plusieurs problèmes qui pénalisent la taille et le temps de rebuild :

- `COPY . .` se fait toujours dans la stage `base`, donc toute modification de code Python invalide le layer de la stage `base` et force le re-build des couches d'OS et torch de la stage `local`.
- Pas de stage builder isolée → caches uv + outils de compilation éventuels restent dans l'image finale.
- `.dockerignore` minimal — pas d'exclusion de `tests/`, `data/`, `uploads/`, `docs/`, etc.
- Reasoning (R&D, gated par `REASONING_ENABLED`) embarqué inconditionnellement dans toutes les images via `[project.dependencies]`.

## 2. Goals

- [ ] Baseline mesurée et notée dans le design doc (`docker images` + `docker history` du top-3 layers, post-uv).
- [ ] `docling-agent` + `mellea` retirés de `[project.dependencies]`, déplacés dans un nouveau `[dependency-groups] reasoning` du `document-parser/pyproject.toml`.
- [ ] `Dockerfile` multi-stage (`builder` + cible finale) avec `COPY . .` repoussé après les `uv sync`.
- [ ] Build-arg `WITH_REASONING=false` (défaut) supporté dans la cible `local` (déclenche `uv sync --group reasoning` quand `true`).
- [ ] `.dockerignore` étendu (`tests/`, `data/`, `uploads/`, `docs/`, `*.iml`, `package-lock.json`, `node_modules/`, `tools/migrate_06.py`).
- [ ] Évaluation de `torchvision` documentée (gardé ou retiré, justifié — vérifier ce que docling ≥2.80 utilise réellement).
- [ ] Volume HF cache documenté dans `docker-compose.yml` et `docker-compose.dev.yml`.
- [ ] Smoke test : conversion locale OK sans reasoning ; reasoning OK avec `WITH_REASONING=true` + `REASONING_ENABLED=true` + Ollama joignable.
- [ ] `uv run pytest tests/ -v` passe dans le container final.
- [ ] Réduction taille ≥ 30 % vs baseline (chiffrée dans la PR).

## 3. Non-goals

- **Pas de réécriture du `LocalConverter`** ni de suppression du `threading.Lock` global → suivi perf séparé (issue dédiée à ouvrir si besoin).
- **Pas de bake-in des modèles Docling** dans l'image par défaut — le compromis taille est trop défavorable (+1.3 GB). Le cache HF reste mountable via volume ; un build-arg `BAKE_MODELS=true` opt-in peut être proposé en option.
- **Pas d'optim de l'image `embedding-service`** — autre image, autre périmètre.
- **Pas de tuning HF Space deploy** — HF Space déploie `latest-remote`, pas `latest-local`.
- **Pas de changement du moteur OCR** livré par Docling.
- **Pas de modification de l'API publique** ni du schéma SQLite — change additif/build-only.
- **Pas de retour aux `requirements*.txt`** — uv (PR #289) est la nouvelle baseline.

## 4. Context & constraints

### Existing code surface

- `document-parser/Dockerfile` — multi-target file (`base` → `remote` / `local`), post-uv.
- `document-parser/pyproject.toml` — déclare `[project.dependencies]` (commun aux 2 cibles), `[dependency-groups.dev]` (pytest, ruff, etc.) et `[dependency-groups.local]` (docling).
- `document-parser/uv.lock` — lock unique committé, géré par `uv sync --frozen`.
- `document-parser/.dockerignore` — minimal exclusion list.
- `Dockerfile` (racine) — image single-container frontend+backend, miroir de `document-parser/Dockerfile`.
- `docker-compose.yml` / `docker-compose.dev.yml` — référencent `target: ${CONVERSION_MODE:-local}`.
- `document-parser/infra/docling_agent_reasoning.py` — garde déjà avec `deps_present()`, donc retirer les deps de l'image standard dégrade gracieusement.

No domain / API / persistence / services code is touched. No SQLite migration. No frontend change. No e2e change.

### Hexagonal Architecture constraints

None crossed. The change lives entirely in `infra/CI` (Docker + pyproject groups). Domain/API/services/persistence are untouched and the `LocalConverter` / `ReasoningRunner` ports keep their existing shapes — only the deployment artefact changes shape, not the code.

### Deployment modes

- `latest-local` (in-process Docling) — affected: standard variant ships without reasoning ; opt-in `WITH_REASONING=true` build pour les opérateurs R&D.
- `latest-remote` (delegates to Docling Serve) — affected: also slimmed (hérite des deps reasoning via `[project.dependencies]` aujourd'hui ; après le change, plus).
- HF Space — uses `latest-remote`, donc bénéficie du gain sans action HF-spécifique.
- Frontend feature flags (`chunking`, `disclaimer`, `reasoningAvailable`) inchangés ; `reasoningAvailable` continue à refléter `deps_present()` côté backend.

### Hard constraints

- **No SQLite or API contract change** — additive build-only.
- **No Pydantic DTO change.**
- **Backwards-compatible runtime behaviour** — le même toggle `CONVERSION_ENGINE` pilote les mêmes code paths ; les deps reasoning manquantes étaient déjà gérées par `deps_present()`.
- **CI / GHCR push pipeline must keep working** — `latest-local` et `latest-remote` continuent à être buildés, mêmes target names.
- **Performance budget** — réduction ≥ 30 % vs baseline post-uv (à mesurer).

## 5. Proposed design

### 5.1 Domain

Untouched.

### 5.2 Persistence

Untouched.

### 5.3 Infra adapters

Untouched at the Python level. Les adaptateurs `LocalConverter`, `ServeConverter`, et `DoclingAgentReasoningRunner` gardent leurs contrats actuels. Le seul change infra est au niveau **deployment** :

- `document-parser/pyproject.toml` :
  - `docling-agent==0.1.0` et `mellea==0.4.2` quittent `[project.dependencies]` pour rejoindre un nouveau `[dependency-groups] reasoning`.
  - `[dependency-groups.local]` reste inchangé (contient `docling`).
- `document-parser/Dockerfile` réécrit en multi-stage avec une stage `builder` isolée :

```
                 python:3.12-slim
                 │
   ┌─────────────┴─────────────┐
   ▼                           ▼
builder-remote            builder-local
   │ uv sync --frozen          │ apt: build deps (si besoin)
   │   --no-dev                │ uv sync --frozen --no-dev --group local
   │                           │ + index pytorch CPU pour torch/torchvision
   │                           │ si WITH_REASONING: uv sync --frozen --group reasoning
   │  (/usr/local site-pkgs)   │  (/usr/local site-pkgs)
   └────────────┬──────────────┘
                ▼
           runtime-base   (poppler + appuser, no uv, no source, no caches)
                │
   ┌────────────┴────────────┐
   ▼                         ▼
remote (final)           local (final)
COPY site-packages       apt: libgl1 + libglib2.0-0
COPY .                   COPY site-packages
                         COPY .
```

- Source (`COPY . /app`) est désormais copiée uniquement dans les stages **finales** — un edit code-only réutilise toutes les couches uv.
- Le cache uv (`/root/.cache/uv`) reste dans la stage builder et n'atteint jamais l'image runtime.
- Un build-arg `WITH_REASONING=false` (défaut) gate l'install des deps reasoning dans le builder-local.

Build-arg `BAKE_MODELS=true` **par défaut** dans la stage local : `docling-tools models download --output-dir /home/appuser/.cache/docling/models` pré-télécharge les checkpoints (layout heron, tableformer, CodeFormulaV2, DocumentFigureClassifier, RapidOCR — ~1.3 GB) à la build. Le tradeoff : +1.3 GB sur l'image standard contre **first-convert instantané** au lieu de 2-5 min de spinner silencieux côté user. Opt-out via `--build-arg BAKE_MODELS=false` pour les déploiements size-conscious (l'opérateur monte alors `/home/appuser/.cache/docling` comme volume pour persister les downloads).

### 5.4 Services

Untouched.

### 5.5 API

Untouched.

### 5.6 Frontend — feature module

Untouched.

### 5.7 Cross-cutting (feature flags, i18n, shared types)

- `/api/health` — no schema change. `reasoningAvailable` continue à refléter `infra/docling_agent_reasoning.deps_present()`, donc rapporte `false` sur l'image standard `latest-local` et `true` sur une image buildée avec `WITH_REASONING=true`.
- `i18n` — no string change.
- `shared/types.ts` — no type change.

## 6. Alternatives considered

### Alternative A — Dedicated `local-reasoning` Dockerfile target (3ème stage)

- **Summary:** ajouter un 3ème final target `FROM local AS local-reasoning` qui lance `uv sync --group reasoning`. CI publie `latest-local` et `latest-local-reasoning` séparément.
- **Why not:** double la surface CI pour peu de bénéfice, et la duplication d'intention (build-arg vs target) brouille les opérateurs. Un seul `--build-arg WITH_REASONING=true` suffit — les opérateurs tagueront l'image résultante comme `local-reasoning` s'ils ont besoin de la distinction.

### Alternative B — Garder reasoning dans `[project.dependencies]`, ne rien faire

- **Summary:** garder `docling-agent` + `mellea` dans les deps de base, accepter l'image lourde comme coût de "tout fonctionne out of the box".
- **Why not:** l'image `latest-remote` (qui délègue à Docling Serve et ne raisonne jamais localement) porterait toujours les ~1 GB de CUDA + LLM SDK weights inutilement. Ça disqualifie le do-nothing.

### Alternative C — Bake les modèles Docling dans une image séparée + sidecar volume

- **Summary:** build une mini "models-only" image, mount comme volume read-only sur le container backend.
- **Why not:** ajoute une moving piece de déploiement (multi-image orchestration) pour une propriété — cold start instantané — qu'un simple `BAKE_MODELS=true` build-arg donnerait, au prix de +1.3 GB que l'opérateur peut opt-out.

## 7. API & data contract

### Endpoints

No change. `/api/health` garde la même shape ; `reasoningAvailable` continue à dériver des import-checks runtime.

### Persistence schema

No change.

### Env vars / config

No new runtime env vars. Build-args sur la cible `local` du Dockerfile :

| Name | Default | Allowed | Notes |
|------|---------|---------|-------|
| `WITH_REASONING` | `false` | `true` / `false` | Déclenche `uv sync --frozen --group reasoning` dans le builder-local. Opt in pour produire une image `local-reasoning`. Off garde l'image standard slim. |
| `BAKE_MODELS` | `true` | `true` / `false` | Pré-fetch les checkpoints Docling (`docling-tools models download`) dans `/home/appuser/.cache/docling/models` à la build (~+1.3 GB). Default `true` pour un first-convert instantané. Opt-out pour les déploiements size-conscious — monter alors le dir comme volume pour persister entre restarts. |

Compose forwards `WITH_REASONING` depuis l'env host (`WITH_REASONING=true docker compose up --build`).

### Breaking changes

**Additive only at the deployment level. Une seule attente opérationnelle change** — intentionnelle :

1. Toute personne run l'image standard `latest-local` avec `REASONING_ENABLED=true` verra `reasoningAvailable=false` depuis l'API, et l'entrée Reasoning de la sidebar va se cacher. Pour restorer : rebuild avec `--build-arg WITH_REASONING=true`.

## 8. Risks

| Risk | Audit dimension | Likelihood | Impact | How we notice | Mitigation / rollback |
|------|-----------------|------------|--------|---------------|------------------------|
| Une dep transitive future re-pull une torch CUDA et regonfle l'image | Performance · CI/Build | Medium | High | CI image-size step régresse ; `docker history` montre des layers `nvidia-*` | Pin `torch` à un build `+cpu` dans `[dependency-groups.local]` ; ajouter un check CI qui fail si des packages `nvidia-*` apparaissent dans le venv |
| Opérateurs qui dépendent du reasoning R&D hit `reasoningAvailable=false` après upgrade | Documentation · Decoupling | Medium | Medium | User report ou 503 depuis `/api/reasoning` (déjà gated) | README + design doc appellent explicitement le path `WITH_REASONING=true` ; le `deps_present()` existant dégrade déjà gracieusement (pas de crash) |
| `COPY --from=builder` multi-stage augmente le temps de build initial sur cache froid | CI/Build | Low | Low | CI build duration | Cold builds séquentiels by design ; warm builds dramatiquement plus rapides (couches uv réutilisées sur chaque edit Python) — net positif |
| Le `[dependency-groups] reasoning` non synchronisé via `uv sync --frozen --group reasoning` peut sauter sans erreur si mal câblé dans le Dockerfile | CI/Build | Medium | Medium | Smoke test reasoning échoue silencieusement (404 sur `/api/reasoning`) | Tester `WITH_REASONING=true` au moins en local avant merge ; smoke automatisé en suivi CI |

## 9. Testing strategy

### Backend — pytest

No new tests added. Le change est build-only et la suite pytest existante est le filet de régression (services, persistence, API contract — aucun touché).

Validation pipeline à exécuter sur la branche :

```
ruff check .          → All checks passed
ruff format --check . → OK
uv run pytest tests/  → all green
```

### Frontend — Vitest

Untouched. Not run.

### E2E — Karate UI

Not in scope. Le change n'affecte aucun comportement user-facing.

### Manual QA

1. `docker compose up --build` → backend container démarre, `/api/health` retourne 200, `reasoningAvailable=false`.
2. Upload un petit PDF et lance une analyse → conversion complète (premier run = download des modèles depuis HF si `BAKE_MODELS` n'est pas activé).
3. Rebuild avec `WITH_REASONING=true docker compose up --build` et `REASONING_ENABLED=true`, avec Ollama joignable → `reasoningAvailable=true`, `POST /api/documents/:id/reasoning` works.

### Performance / load — image size measurements

Mesures arm64 (référence taguées dans le daemon Docker local : `docling-studio-backend:baseline-*` et `:after-*` reprises du 0.6.1 design doc, et `docling-doc-parser:slim-*` produites par cette branche).

| Variant                                                                   | Pre-#254 baseline | 0.6.1 best | **Cette branche** | Δ vs baseline |
|---------------------------------------------------------------------------|------------------:|-----------:|------------------:|--------------:|
| `latest-remote`                                                           | 5.85 GB           | 585 MB     | **537 MB**        | **−91 %**     |
| `latest-local` (`BAKE_MODELS=true`, default)                              | n/a               | 3.19 GB    | **3.1 GB**        | **−49 %**     |
| `latest-local` (`BAKE_MODELS=false`, slim)                                | 6.09 GB           | 1.89 GB    | **1.72 GB**       | **−72 %**     |
| `latest-local` (`BAKE_MODELS=false`, `WITH_REASONING=true`)               | n/a               | n/a        | **1.92 GB**       | n/a           |

Reasoning stack mesuré : `+200 MB` (docling-agent + mellea + ollama client + deps transitives). Plus modeste que prévu — la séparation reste pertinente pour la propreté de surface (HF Space remote n'embarque pas de LLM SDK code R&D) mais n'est pas le levier taille principal. Le gros gain vient de torch+cpu et du `.dockerignore` durci.

Build durations cold cache (apple silicon, M-series) : `remote` ≈ 30 s, `local` slim ≈ 1 min, `local` baked ≈ 1 min 40 s (HF download ~40 s pour ~1.3 GB sur lien rapide).

## 10. Rollout & observability

### Release branch

Targets `release/0.6.2`. La branche feature est `feature/254-docker-slim-post-uv`, branchée depuis `chore/python-uv-setup` (PR #289) pour intégrer uv avant de slimmer.

### Feature flag / staged rollout

Pas de runtime feature flag. Le change est caché derrière un **build-time** flag :

- `WITH_REASONING=true` (opt-in) — produit une variante `local-reasoning`.

Optionnel :

- `BAKE_MODELS=true` (opt-in) — produit l'image avec checkpoints baked.

Les opérateurs roll out en re-pullant `latest-local` depuis GHCR ; pas de env flip nécessaire.

HF Space deployments sont non-affectés par les build-args `local` (HF Space utilise `latest-remote`).

### Observability

- Pas de nouveaux logs, metrics, ou error modes.
- Image size devient un signal CI : un follow-up devrait ajouter une step qui print la taille de l'image publiée dans le summary du workflow, pour qu'une future régression (e.g. une nouvelle dep re-pullant CUDA) soit visible en PR review.

### Rollback plan

Pure-revert. Re-deployer le tag précédent (`v0.6.1` une fois publié) restaure l'image antérieure. Pas de data migration ni env flip.

## 11. Open questions

- Faut-il activer `BAKE_MODELS=true` par défaut (instant cold start mais +1.3 GB) ou laisser le download au premier run (image plus légère mais latence first-conversion) ? → décision à prendre en cours d'implémentation, après mesure du gain net.
- Pin `torch` à un build CPU explicite (`torch==X.Y.Z+cpu`) dans `[dependency-groups.local]` plutôt que de passer par `--index-url` dans le Dockerfile ? Plus déclaratif mais oblige à pinner précisément la version.
- Drop `docling-core[chunking]` extra de `[project.dependencies]` pour pousser `latest-remote` encore plus bas ? Demande de vérifier que le path `infra/local_chunker.py` est strictement local-only.

## 12. References

- **Issue:** https://github.com/scub-france/Docling-Studio/issues/254
- **Predecessor design doc (0.6.1, non-mergé):** historique git sur `release/0.6.1`, commits `975f405` + `392d316`, fichier `docs/design/254-optim-taille-image-latest-local.md`.
- **Upstream uv migration PR:** #289
- **ADRs:** none planned
- **Project docs:**
  - Architecture: `docs/architecture.md`
  - Coding standards: `docs/architecture/coding-standards.md`
  - Audit master: `docs/audit/master.md`
- **External:**
  - Upstream `_rag_loop` public-API replacement: https://github.com/docling-project/docling-agent/issues/26
  - Docling models tooling: `docling-tools models download` (CLI shipped by `docling`)
  - uv dependency groups: https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups
