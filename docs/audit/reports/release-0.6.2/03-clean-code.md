# Rapport d'audit : Clean Code

**Release** : 0.6.2 (branche `release/0.6.2`)
**Date** : 2026-06-05
**Auditeur** : claude-code
**HEAD** : `051ac4a` (ci(#254): skip Docling model bake in E2E to avoid HF rate limit)
**Baseline** : `f9e5619` — rapport `release-0.6.1-reaudit/03-clean-code.md` (72/100, GO CONDITIONNEL)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 10 / 14 (somme des poids conformes 13 / 18) |
| Score | **72 / 100** |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 3 |
| Ecarts INFO | 0 |

### Detail

| # | Item | Poids | Statut | Delta vs 0.6.1-reaudit |
|---|------|-------|--------|------------------------|
| 3.1.1 | Fonctions = verbes d'action | 1 | OK | = |
| 3.1.2 | Variables expriment l'intention | 1 | OK | = |
| 3.1.3 | Code en anglais / i18n separe | 2 | OK | = |
| 3.1.4 | Pas d'abbreviations ambigues | 1 | OK | = |
| 3.2.1 | Single Responsibility | 2 | **KO** | = |
| 3.2.2 | Fonctions <= 30 lignes | 1 | **KO** | = |
| 3.2.3 | <= 4 parametres | 1 | **KO** | = |
| 3.2.4 | Pas de flag arguments | 1 | OK | = |
| 3.2.5 | `get_*` sans side-effects | 2 | OK | = |
| 3.3.1 | Fichiers <= 300 lignes | 1 | **KO** | = |
| 3.3.2 | Un concept par fichier | 2 | OK | = |
| 3.3.3 | Imports ordonnes | 1 | OK | = |
| 3.4.1 | Code auto-documentant | 1 | OK | = |
| 3.4.2 | Pas de code commente | 1 | OK | = |

**Calcul** : poids conformes (1+1+2+1+1+2+2+1+1+1 = 13) / poids total (18) × 100 = 72.2 → **72 / 100**.

---

## Contexte du re-audit 0.6.2

Le HEAD `051ac4a` est identique a la baseline 0.6.1-reaudit (`f9e5619`) sur tous les fichiers flagges en Clean Code : `git log f9e5619..HEAD -- document-parser/services/chunk_service.py document-parser/main.py document-parser/infra/neo4j/tree_writer.py frontend/src/pages/StudioPage.vue` renvoie zero commit. La fenetre 0.6.2 a entierement ete consacree au workstream **#254 (docker-slim)** + un commit `audit-02` qui touche uniquement la wire-vocabulary (`job → push`) sans impact size.

Conclusion structurelle :
- Le bilan Clean Code de 0.6.2 herite mot pour mot du re-audit 0.6.1.
- **Aucune des 3 conditions de remontee a GO** (decomposer `chunk_service.py`, `StudioPage.vue`, regrouper `ChunkService.__init__` en dataclass) n'a ete travaillee.
- Aucun nouvel ecart n'apparait — la trajectoire reste plate, ni progression ni regression.

---

## Ecarts constates

### [MAJ] Violations du Single Responsibility — handlers fourre-tout (inchange)

- **Localisation** (lignes verifiees au HEAD `051ac4a`) :
  - `document-parser/services/chunk_service.py:574` `push_to_store` — **119 lignes** (574-692). Six responsabilites empilees : resolution du slug du store, snapshot des chunks, calcul du hash de chunkset, recuperation du backend resolver, persistance de la `chunk_pushes` row, upsert du `document_store_links` + marquage failure path. Aucun helper extrait.
  - `document-parser/services/chunk_service.py:451` `rechunk_document` — **89 lignes** (451-539). Inchange depuis 0.6.1.
  - `document-parser/main.py:247` `lifespan` — **187 lignes** (247-433, body principal 247→376 jusqu'au `yield`, cleanup 377→423). Wiring graph/tree port d'`#audit-01` (#0.6.1) plus le bloc `app.state.graph_writer` (247:261-275) + injection `Neo4jGraphWriter` dans `StoreBackendResolver` + 3 helpers `_build_*` toujours non encapsules dans un seul `await build_app_state(app)`. Note : la mesure 0.6.1-reaudit annoncait 142L en s'arretant au `yield` ; la mesure complete (corps + cleanup) sort a 187L.
  - `document-parser/infra/neo4j/tree_writer.py:69` `write_document` — **242 lignes** (69-310). Aucun changement depuis 0.6.0 — *quatrieme audit consecutif sans action*.
  - `document-parser/infra/neo4j/chunk_writer.py:55` `write_chunks` — ~113 lignes (inchange).
- **Regle violee** : 3.2.1 (poids 2).
- **Remediation** : identique au baseline — `push_to_store` en 4 helpers (`_resolve_store_id`, `_snapshot_chunks`, `_persist_push_row`, `_upsert_link_state`), `lifespan` reductible a `await build_app_state(app)` apres extraction des 4 sub-helpers deja partiels (`_build_analysis_service`, `_build_ingestion_service`, `_build_document_service`, `_build_reasoning_runner`), writers Neo4j a re-deserrer en helpers Cypher.

### [MIN] Fonctions de plus de 30 lignes (inchange)

- **Top backend (inchange depuis 0.6.1-reaudit)** :
  - `services/chunk_service.py:149` `ChunkService.__init__` — **49 lignes** (149-197).
  - `services/chunk_service.py:574` `push_to_store` — 119 lignes.
  - `services/chunk_service.py:451` `rechunk_document` — 89 lignes.
  - `services/chunk_service.py:335` `split_chunk` — 58 lignes (335-392).
  - `services/chunk_service.py:393` `merge_chunks` — 58 lignes (393-450).
  - `services/chunk_service.py:693` `list_pushes` — 50 lignes (693-742).
  - `services/chunk_service.py:205` `promote_from_analysis_if_empty` — 44 lignes (205-248).
  - `services/chunk_service.py:285` `update_chunk` — 31 lignes (285-315).
  - `main.py:247` `lifespan` — 187 lignes.
  - `main.py:145` `_build_ingestion_service` — 46 lignes (145-190).
  - `main.py:434` `_build_reasoning_runner` — 34 lignes (434-467).
  - `infra/neo4j/tree_writer.py:69` `write_document` — 242 lignes.
- **Regle violee** : 3.2.2 (poids 1).
- **Evolution** : zero changement structurel ; le compteur global reste autour de 30 fonctions >30L.

### [MIN] Fonctions avec plus de 4 parametres (inchange)

- **Localisation** :
  - `document-parser/services/chunk_service.py:149` `ChunkService.__init__` — **12 parametres** (`chunk_repo`, `chunk_edit_repo`, `chunk_push_repo`, `document_repo`, `analysis_repo`, `tree_reader`, `chunker`, `ingestion_service`, `store_repo`, `link_repo`, `backend_resolver`, `actor`). Verifie au HEAD `051ac4a`.
  - `document-parser/services/store_service.py` — `update_store` 10 params, `create_store` ~9 params (inchange).
  - `document-parser/services/analysis_service.py` — `__init__` 8 params (inchange).
  - `document-parser/services/store_backend_resolver.py` — `__init__` 7 params (inchange).
  - `document-parser/infra/neo4j/tree_writer.py:69` `write_document` — 7 params (inchange).
- **Regle violee** : 3.2.3 (poids 1).
- **Remediation** : `ChunkService.__init__` reste le candidat prioritaire pour une dataclass `ChunkServiceDeps` regroupant les 6 repos + le `tree_reader` + le `backend_resolver`.

### [MIN] Fichiers source de plus de 300 lignes (inchange)

- **Backend (8 fichiers >300L, identique au baseline)** :
  - `services/chunk_service.py` — 1014L
  - `services/analysis_service.py` — 553L
  - `main.py` — 504L
  - `api/schemas.py` — 493L
  - `domain/ports.py` — 442L
  - `services/store_service.py` — 391L
  - `domain/models.py` — 331L
  - `infra/neo4j/tree_writer.py` — 310L
- **Frontend (34 fichiers >300L au total, 31 hors tests)** :
  - `frontend/src/pages/StudioPage.vue` — **1450L** (inchange — *quatrieme audit consecutif sans action*).
  - `frontend/src/shared/i18n.ts` — 1287L (catalogue i18n, mono-concept par construction, 3.3.2 OK).
  - `frontend/src/pages/DocsLibraryPage.vue` — 849L.
  - `frontend/src/features/chunking/ui/ChunkPanel.vue` — 801L.
  - `frontend/src/features/analysis/ui/GraphView.vue` — 695L.
  - `frontend/src/features/analysis/ui/ResultTabs.vue` — 690L.
  - `frontend/src/features/chunks/ui/ChunksEditor.vue` — 622L.
  - 25 autres composants entre 300 et 520L.
- **Regle violee** : 3.3.1 (poids 1).
- **Evolution vs 0.6.1-reaudit** : neutre. Backend 8/8, frontend 34 (vs 33) — l'incrementation marginale du frontend vient d'un fichier `i18n.ts` qui passe le seuil dans un fichier de test (`features/document/store.test.ts` 355L), sans impact sur le concept "source code".

---

## Points positifs

- **Zero code commente, zero TODO/FIXME/XXX, zero `console.log`, zero `debugger`** sur tout le scope `document-parser/` + `frontend/src/`. Discipline maintenue depuis 0.5.x.
- **Imports ordonnes** : `ruff check .` (rule `I` isort) passe au vert sur la branche.
- **Nommage** : tous les verbes d'action utilises (`create_*`, `update_*`, `fetch_*`, `push_to_store`, `rechunk_document`, `record_on_rechunk`...). Seul `l, t, r, b` dans `infra/serve_converter.py:288-291` sont monolettres et le cas est *legitime* — ce sont les kwargs natifs du payload Docling Serve pour bbox (left/top/right/bottom), convention etablie au sens de la fiche 3.1.4.
- **Auto-documentation `pourquoi`** : les commentaires verifies dans `chunk_service.py:169-196` (constructeur), `tree_writer.py:237`, `settings.py:43`, `value_objects.py:206`, `store_service.py:299`, `store_backend_resolver.py:95` expliquent tous l'intention/le contrat et non le mecanisme. Conforme 3.4.1.
- **Code en anglais homogene** — toutes les chaines visibles transitent par `frontend/src/shared/i18n.ts` (1287L de catalogue centralise), conformement a 3.1.3.
- **Concept par fichier (3.3.2)** : meme les fichiers >300L sont mono-concept. `chunk_service.py` reste un service unique (a decomposer pour la taille, mais pas pour la coherence), `tree_writer.py` est un adaptateur unique, `i18n.ts` est un catalogue unique.
- **Ruff pipeline** : `ruff check .` + `ruff format --check .` passent.

---

## Verdict partiel : GO CONDITIONNEL (inchange)

Score **72 / 100**, 0 CRITICAL, **1 MAJOR**, 3 MINOR. **Strictement identique a 0.6.1-reaudit (72/0/1/3/0)**.

**Delta vs 0.6.1-reaudit** : **0 point**. Aucun item ne bascule. Le scope 0.6.2 n'a jamais ete cense traiter Clean Code (focus #254 docker-slim + #225 push semantics + #279 store backends) — la stabilite mecanique est attendue, mais le compteur de cycles sans action sur le chantier prioritaire est desormais a **quatre** pour `StudioPage.vue` et `tree_writer.write_document`.

**Conditions de remontee a GO (>=80) — inchangees, plus pressantes** :
1. Decomposer `services/chunk_service.py` (1014L) en au moins 3 fichiers + ramener `push_to_store` sous 40 lignes par extraction de 3-4 helpers prives. Eteint le MAJ + 2 MIN.
2. Decomposer `StudioPage.vue` (1450L) — *quatrieme audit consecutif sans action*.
3. Regrouper les deps de `ChunkService.__init__` (12 params) dans une dataclass `ChunkServiceDeps`.

**Note** : aucun CRIT — la release n'est pas bloquee. La trajectoire reste constante depuis 0.6.0 ; sans inflexion sur 0.7.0 le score risque la bascule sous 60 (NO-GO) si la vague de nouvelles pages workspace deja amorcee par `1f75551` arrive sans hygiene de taille.
