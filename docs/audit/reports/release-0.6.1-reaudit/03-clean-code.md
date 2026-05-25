# Rapport d'audit : Clean Code (re-audit)

**Release** : 0.6.1 (branche `fix/0.6.1-audit-blockers`)
**Date** : 2026-05-25
**Auditeur** : claude-code
**HEAD** : `f9e5619` (refactor(hex-arch): route graph + tree access through ports)
**Baseline** : `825e7d7` (release/0.6.1) — rapport `release-0.6.1/03-clean-code.md`

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

| # | Item | Poids | Statut | Delta vs 0.6.1 |
|---|------|-------|--------|----------------|
| 3.1.1 | Fonctions = verbes d'action | 1 | OK | = |
| 3.1.2 | Variables expriment l'intention | 1 | OK | = |
| 3.1.3 | Code en anglais / i18n separe | 2 | OK | = |
| 3.1.4 | Pas d'abbreviations ambigues | 1 | OK | = |
| 3.2.1 | Single Responsibility | 2 | **KO** | = |
| 3.2.2 | Fonctions <= 30 lignes | 1 | **KO** | = |
| 3.2.3 | <= 4 parametres | 1 | **KO** | = (legere regression locale) |
| 3.2.4 | Pas de flag arguments | 1 | OK | = |
| 3.2.5 | `get_*` sans side-effects | 2 | OK | = |
| 3.3.1 | Fichiers <= 300 lignes | 1 | **KO** | = (counts quasi-stables) |
| 3.3.2 | Un concept par fichier | 2 | OK | = (renforce par nouveaux fichiers) |
| 3.3.3 | Imports ordonnes | 1 | OK | = |
| 3.4.1 | Code auto-documentant | 1 | OK | = |
| 3.4.2 | Pas de code commente | 1 | OK | = |

**Calcul** : poids conformes (1+1+2+1+1+2+2+1+1+1 = 13) / poids total (18) × 100 = 72.2 → **72 / 100**.

---

## Contexte de la re-audit

Le scope de remediation 0.6.1 n'a **pas** cible les ecarts Clean Code (SRP / taille fonction / file size). Les commits ont adresse les CRIT/MAJ des audits 01, 02, 08, 09, 11, 12. Cette re-audit mesure donc :

1. l'impact collateral du commit `f9e5619` (#audit-01) qui introduit `services/graph_service.py` (132L) + `infra/neo4j/graph_adapter.py` (75L) + un `tree_reader` parametre supplementaire sur `ChunkService.__init__` ;
2. le statut des 4 fonctions deja flaggees (`push_to_store`, `rechunk_document`, `lifespan`, `write_document`).

Les deltas mesures sont **neutres a legerement negatifs sur les compteurs locaux**, mais aucun nouvel item de checklist ne bascule (les seuils restent depasses des le 1er fichier).

---

## Ecarts constates

### [MAJ] Violations du Single Responsibility — handlers fourre-tout (inchange)

- **Localisation** :
  - `document-parser/services/chunk_service.py:574` `push_to_store` — **~120 lignes** (574-693, etait ~118). Le wiring `tree_reader` n'a pas touche cette methode mais 2 lignes supplementaires (logging du payload du backend resolver) sont entrees via merge. Les 6 responsabilites du baseline restent intactes.
  - `document-parser/services/chunk_service.py:451` `rechunk_document` — **~90 lignes** (451-540, etait ~88). Idem, +2 lignes marginales, structure inchangee.
  - `document-parser/main.py:247` `lifespan` — **~142 lignes** (247-389). Le commit `f9e5619` a refactor le wiring graph : il remplace l'init Neo4j inline par 11 nouvelles lignes (`if app.state.neo4j is not None: ... graph_writer = Neo4jGraphWriter(...)` + injection dans `_build_analysis_service` + `_build_ingestion_service` + `StoreBackendResolver` + construction de `GraphService`). **Net -12 lignes** vs baseline (154 → 142) grace au remplacement de plusieurs blocs d'imports inline par des passages parametres. La methode reste hors-seuil (>>30 lignes) et le decoupage `_build_*` n'a pas progresse vers le `await build_app_state(app)` cible.
  - `document-parser/infra/neo4j/tree_writer.py:69` `write_document` — **242 lignes** (inchange, brut). Aucun travail sur ce fichier dans le scope 0.6.1-audit-blockers.
  - `document-parser/infra/neo4j/chunk_writer.py:55` `write_chunks` — **~114 lignes** (inchange).
- **Regle violee** : 3.2.1 (poids 2).
- **Remediation** : identique au baseline — `push_to_store` en 4 helpers, `rechunk_document` deja partiellement decompose dans `domain/chunk_editing.py`, `lifespan` reductible a `await build_app_state(app)`, writers Neo4j a re-deserrer en helpers Cypher. **Aucun de ces chantiers n'a ete entame.**
- **Note positive** : le **nouveau code introduit par `f9e5619` ne contribue PAS au MAJ** — `GraphService.fetch_document_graph` (`services/graph_service.py:90`, 17 lignes) et `project_reasoning_graph` (`:109`, 24 lignes) sont sous 30 lignes, mono-responsabilite, exceptions typees. Les adaptateurs `Neo4jGraphReader` / `Neo4jGraphWriter` (`infra/neo4j/graph_adapter.py`) sont des shims de 2-5 lignes/methode.

### [MIN] Fonctions de plus de 30 lignes (quasi-inchange)

- **Top backend (deltas marques)** :
  - `services/chunk_service.py:149` `ChunkService.__init__` — **49 lignes** (etait 44) — +5 lignes du commentaire + assignation du `tree_reader` (#audit-01) + un commentaire elargi sur `_stores` et `_backend_resolver`.
  - `services/chunk_service.py:574` `push_to_store` — ~120 lignes (etait ~118).
  - `services/chunk_service.py:451` `rechunk_document` — ~90 lignes (etait ~88).
  - `main.py:247` `lifespan` — ~142 lignes (etait 154, **-12**).
  - Toutes les autres entrees du top baseline (`split_chunk`, `merge_chunks`, `_finalize_analysis`, `update_store`, `write_document` 242, `write_chunks` 113, `fetch_graph` 90, etc.) restent au meme rang, non touchees par le scope 0.6.1-audit-blockers.
- **Nouvelles fonctions introduites** (toutes <30 lignes, conformes) :
  - `services/graph_service.py:90` `fetch_document_graph` — 17 lignes
  - `services/graph_service.py:109` `project_reasoning_graph` — 24 lignes
  - `services/graph_service.py:77` `GraphService.__init__` — 13 lignes (4 params)
  - `infra/neo4j/graph_adapter.py` — toutes les methodes <10 lignes
- **Regle violee** : 3.2.2.
- **Evolution vs 0.6.1** : neutre. Le total de fonctions >30 lignes reste autour de 30 ; le nouveau code n'ajoute rien a la liste mais ne resout aucune entree existante.

### [MIN] Fonctions avec plus de 4 parametres (1 legere regression locale)

- **Localisation (deltas marques)** :
  - `services/chunk_service.py:149` `ChunkService.__init__` — **12 params** (etait 11) : ajout du `tree_reader: DocumentTreeReader` introduit par #audit-01. Conforme au plan port-injection, mais aggrave un compteur deja hors-seuil — **non bloquant** car l'item bascule des le 1er depassement.
  - Toutes les autres entrees du top baseline (`update_store` 10, `create_store` 9, `AnalysisService.__init__` 8, `StoreBackendResolver.__init__` 7, `tree_writer.write_document` 7, ...) sont inchangees.
- **Nouveaux callsites introduits — tous conformes** :
  - `services/graph_service.py:77` `GraphService.__init__` — 4 params (`analysis_repo`, `graph_reader`, `graph_projector`, `config`) — conforme.
  - `infra/neo4j/graph_adapter.py:30, :46` `__init__` (1 param) ; `fetch` (3 params) ; `write_document_tree` (3 params kw-only) ; `write_chunks` (2 params kw-only) ; `ping` (0 param) — tous conformes.
- **Regle violee** : 3.2.3.
- **Remediation** : `ChunkService.__init__` devient prioritaire — 12 params sur un constructeur de service crie pour une `ChunkServiceDeps` dataclass. Le mouvement port-injection (#audit-01) a augmente la pression et legitime de plus en plus un regroupement.

### [MIN] Fichiers source de plus de 300 lignes (compteurs quasi-stables)

- **Backend (8 fichiers >300 lignes, identique au baseline en nombre)** :
  - `services/chunk_service.py` — **1014** (etait 1003, **+11** : tree_reader + commentaires longs)
  - `services/analysis_service.py` — **553** (etait 552, +1)
  - `main.py` — **504** (etait 471, **+33** : +51/-18 net pour le wiring graph/tree port + import factory `Neo4jGraphWriter` injecte dans `StoreBackendResolver`)
  - `api/schemas.py` — 493 (inchange)
  - `domain/ports.py` — **442** (etait 339, **+103** : nouveaux ports `GraphReader`, `GraphWriter`, `DocumentGraphProjector`, `DocumentTreeReader` + docstrings) — file size monte mais le concept "ports & adapters" reste un seul concept (3.3.2 OK).
  - `services/store_service.py` — 391 (etait 389, +2)
  - `domain/models.py` — 331 (inchange)
  - `infra/neo4j/tree_writer.py` — 310 (inchange)
- **Nouveaux fichiers introduits sous le seuil** :
  - `services/graph_service.py` — **132 lignes** (sous 300, conforme).
  - `infra/neo4j/graph_adapter.py` — **75 lignes** (sous 300, conforme).
- **Frontend** : **33 fichiers >300 lignes** (etait 28, +5 — purement structurel, aucun chantier 0.6.1-audit-blockers n'a touche au frontend). `StudioPage.vue` reste a **1450 lignes** (chantier toujours non attaque — *troisieme audit consecutif*).
- **Regle violee** : 3.3.1.
- **Evolution vs 0.6.1** : neutre cote backend (8 fichiers, le nouveau `domain/ports.py` rejoint la liste mais `tree_writer.py` aurait pu en sortir s'il avait ete decompose — il ne l'a pas ete) ; **legere regression cote frontend** (+5 fichiers >300L, mais sans rapport avec le scope re-auditee).

---

## Points positifs

- **Aucune regression conceptuelle.** Le commit `f9e5619` introduit du code conforme : `GraphService` et les adapters `Neo4j*` respectent 3.2.1 (SRP), 3.2.2 (<30L), 3.2.3 (<=4 params), 3.3.1 (<300L). Ils valident le pattern attendu par les remediations futures.
- **`lifespan` regresse de -12 lignes** apres le refactor port — premiere baisse mesuree sur ce point depuis 0.4.0. Reste hors-seuil mais la trajectoire s'inverse.
- **Concept par fichier renforce (3.3.2)** : les nouveaux fichiers (`graph_service.py`, `graph_adapter.py`) sont mono-concept. `domain/ports.py` grossit de +103 lignes mais reste un agregat coherent de ports abstraits.
- **Zero TODO / FIXME / dead code / `console.log` / `debugger`** — discipline maintenue.
- **Ruff** : `ruff check .` + `ruff format --check .` passent sur la branche (validation pipeline du backend).
- **Nommage des nouvelles classes explicite** : `GraphStoreNotConfiguredError`, `GraphNotFoundError`, `GraphTooLargeError`, `Neo4jGraphReader`, `Neo4jGraphWriter`, `DoclingGraphProjector`, `DoclingTreeReader` — porteur d'intention, pas d'abbreviation.

---

## Verdict partiel : GO CONDITIONNEL (inchange)

Score **72 / 100**, 0 CRITICAL, **1 MAJOR**, 3 MINOR. **Identique au baseline 0.6.1 (72/0/1/3/0)**.

**Delta vs 0.6.1** : **0 point**. Aucun item ne bascule. La remediation 0.6.1-audit-blockers ne ciblait pas l'audit Clean Code — le score est mecaniquement stable. Le commit `f9e5619` apporte du code conforme (qui ne pese pas sur le score, mais qui ne le degrade pas non plus) et fait baisser `lifespan` de 12 lignes (premier signal positif depuis 3 cycles). Le compteur `ChunkService.__init__` monte a 12 params (etait 11) mais l'item 3.2.3 etait deja KO.

**Conditions de remontee a GO (>=80) — inchangees** :
1. Decomposer `services/chunk_service.py` (1014 lignes) en au moins 3 fichiers + ramener `push_to_store` sous 40 lignes par extraction de 3-4 helpers prives. Eteint le MAJ + 2 MIN.
2. Decomposer `StudioPage.vue` (1450L) — *troisieme audit consecutif sans action*.
3. Regrouper les deps de `ChunkService.__init__` (12 params) dans une dataclass `ChunkServiceDeps` — le mouvement port-injection rend ce regroupement encore plus pertinent.

**Note** : aucun CRIT — la release n'est pas bloquee. Mais l'audit Clean Code n'a recu **aucune attention** dans le scope 0.6.1-audit-blockers ; le plan de remediation doit etre acte explicitement pour 0.7.0 sous peine de passer sous 60 (NO-GO) si une nouvelle vague de pages frontend arrive sans hygiene.
