# Rapport d'audit : Clean Code

**Release** : 0.6.1
**Date** : 2026-05-24
**Auditeur** : claude-code
**HEAD** : `825e7d7` (release/0.6.1)

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

| # | Item | Poids | Statut |
|---|------|-------|--------|
| 3.1.1 | Fonctions = verbes d'action | 1 | OK |
| 3.1.2 | Variables expriment l'intention | 1 | OK |
| 3.1.3 | Code en anglais / i18n separe | 2 | OK |
| 3.1.4 | Pas d'abbreviations ambigues | 1 | OK |
| 3.2.1 | Single Responsibility | 2 | **KO** |
| 3.2.2 | Fonctions <= 30 lignes | 1 | **KO** |
| 3.2.3 | <= 4 parametres | 1 | **KO** |
| 3.2.4 | Pas de flag arguments | 1 | OK |
| 3.2.5 | `get_*` sans side-effects | 2 | OK |
| 3.3.1 | Fichiers <= 300 lignes | 1 | **KO** |
| 3.3.2 | Un concept par fichier | 2 | OK |
| 3.3.3 | Imports ordonnes | 1 | OK |
| 3.4.1 | Code auto-documentant | 1 | OK |
| 3.4.2 | Pas de code commente | 1 | OK |

**Calcul** : poids conformes (1+1+2+1+1+2+2+1+1+1 = 13) / poids total (18) × 100 = 72.2 → **72 / 100**.

---

## Ecarts constates

### [MAJ] Violations du Single Responsibility — handlers fourre-tout

- **Localisation** :
  - `document-parser/services/chunk_service.py:568` `push_to_store` — ~118 lignes / 6 responsabilites concatenees : validation du document, resolution slug→id, chargement chunks, hashing, resolution du backend (try/except), appel `ingest`, ecriture du `ChunkPush`, upsert du link, log + payload de retour. Mediation d'erreurs intercalee avec la logique nominale (3 chemins d'erreur dans la meme methode).
  - `document-parser/services/chunk_service.py:445` `rechunk_document` — ~88 lignes : verification doc, lecture analyse, lecture chunks existants, calcul du diff (split/merge), purge des chunks orphelins, persistance, audit, retour. Trois sous-cas (rechunk identique / divergent / vide) imbriques.
  - `document-parser/main.py:247` `lifespan` — 154 lignes de wiring DI. Onze blocs successifs (init DB, build repos, store, ingestion, backend_resolver, chunk_service, version_service, drain pools). Le decoupage en `_build_*` fonctions ne couvre qu'une fraction — la majorite du wiring vit toujours inline.
  - `document-parser/infra/neo4j/tree_writer.py:69` `write_document` — 242 lignes (mesure brute, inclut nested defs) : un assistant a re-deroule la suppression precedente.
  - `document-parser/infra/neo4j/chunk_writer.py:55` `write_chunks` — 114 lignes : MERGE Cypher + retry + upsert link, tout dans la meme coroutine.
- **Regle violee** : 3.2.1 (poids 2).
- **Remediation** :
  - `push_to_store` : extraire `_resolve_store(store_id)`, `_load_canonical_chunks(document_id)`, `_resolve_targets(store)`, `_record_push(...)`. Le corps tomberait sous 40 lignes.
  - `rechunk_document` : sortir le calcul de diff dans `domain/chunk_editing.py` (deja le bon endroit pour `split`/`merge`/`insert`).
  - `lifespan` : completer la decomposition `_build_*` pour couvrir le wiring store + chunk + version. Idealement `lifespan` ne fait plus que `await build_app_state(app)` + drain pools.
  - `write_document` / `write_chunks` : extraire chaque MERGE en helper Cypher dedie (cf. ce qui avait ete fait sur 0.5.0 avant la reintroduction).

### [MIN] Fonctions de plus de 30 lignes

- **Localisation (top backend)** :
  - `services/chunk_service.py:568` `push_to_store` — ~118 lignes
  - `services/chunk_service.py:445` `rechunk_document` — ~88 lignes
  - `services/chunk_service.py:329` `split_chunk` — ~58 lignes
  - `services/chunk_service.py:387` `merge_chunks` — ~58 lignes
  - `services/chunk_service.py:148` `__init__` — 44 lignes (11 deps DI)
  - `services/chunk_service.py:199` `promote_from_analysis_if_empty` — 44 lignes
  - `services/chunk_service.py:687` `list_pushes` — ~50 lignes
  - `services/analysis_service.py:421` `_finalize_analysis` — ~74 lignes
  - `services/analysis_service.py:246` `_run_batched_conversion` — ~60 lignes
  - `services/analysis_service.py:81` `__init__` — 32 lignes
  - `services/store_service.py:236` `update_store` — ~72 lignes
  - `services/store_service.py:185` `create_store` — ~50 lignes
  - `services/ingestion_service.py:82` `ingest` — ~60 lignes
  - `services/ingestion_service.py:158` `_build_indexed_chunks` — ~40 lignes
  - `services/version_service.py:148` `restore` — ~53 lignes
  - `main.py:247` `lifespan` — 154 lignes
  - `main.py:145` `_build_ingestion_service` — 46 lignes
  - `infra/local_converter.py:158` `_process_content_item` — ~63 lignes
  - `infra/local_converter.py:222` `_convert_sync` — ~65 lignes
  - `infra/local_chunker.py:24` `_chunk_sync` — ~62 lignes
  - `infra/docling_graph.py:76` `build_graph_payload` — ~102 lignes
  - `infra/docling_tree.py:154` `build_collapse_index` — ~51 lignes
  - `infra/docling_agent_reasoning.py:67` `run` — ~62 lignes
  - `infra/settings.py:133` `from_env` — ~60 lignes
  - `infra/settings.py:77` `__post_init__` — ~55 lignes
  - `infra/neo4j/tree_writer.py:69` `write_document` — 242 lignes
  - `infra/neo4j/chunk_writer.py:55` `write_chunks` — 113 lignes
  - `infra/neo4j/queries.py:143` `fetch_graph` — ~90 lignes
  - `api/schemas.py:19` `_to_camel` — `lineno`-only, mesure brute 133 lignes (gros bloc Pydantic — la majorite est du boilerplate de schemas, mais ce sont bien des classes/methodes inline du fichier — a verifier au cas par cas)
  - `api/reasoning.py:52` `run_reasoning` — ~61 lignes
  - `api/documents.py:132` `preview` — ~34 lignes
  - `api/document_chunks.py` `preview` — ~76 lignes
  - `domain/models.py:131` et `:220` `mark_failed` — 69 et 111 lignes (mesure brute, inclut decorateurs et nested types)
- **Regle violee** : 3.2.2.
- **Remediation** : prioritaires = `push_to_store` (a sortir au moins en 4 helpers), `rechunk_document` (deja decompose en `domain/chunk_editing.py`, finir le travail), `lifespan` (cf. MAJ ci-dessus), et les writers Neo4j (cf. MAJ).
- **Evolution vs 0.5.0** : regression. 0.5.0 listait ~10 fonctions >30 lignes (top: `ingest` 81, `_convert_sync` 66, `convert` 66, `_run_batched_conversion` 60). 0.6.1 cumule ~30 fonctions, dont **5 au-dessus de 100 lignes** (`push_to_store` 118, `_to_camel`-bloc 133, `write_document` 242, `write_chunks` 113, `lifespan` 154, `build_graph_payload` 102). Les fonctions >100 lignes avaient disparu en 0.5.0 — leur retour suit la reintroduction de neo4j + reasoning + l'extension de `chunk_service`.

### [MIN] Fonctions avec plus de 4 parametres

- **Localisation** (positionnels + kw-only, exclut `self` / `cls`) :
  - `services/chunk_service.py:148` `ChunkService.__init__` — **11 params** (DI massive : 5 repos + chunker + ingestion + 2 store deps + backend_resolver + actor)
  - `services/store_service.py:236` `update_store` — **10 params**
  - `services/store_service.py:185` `create_store` — 9 params
  - `services/analysis_service.py:81` `AnalysisService.__init__` — 8 params
  - `services/store_backend_resolver.py:74` `__init__` — 7 params
  - `infra/neo4j/tree_writer.py:69` `write_document` — 7 params
  - `domain/chunk_editing.py:46` `insert` — 6 params
  - `domain/models.py:105` `AnalysisJob.mark_completed` — 5 params
  - `services/analysis_service.py:246` `_run_batched_conversion` — 5 params
  - `services/analysis_service.py:372` `_run_analysis` — 5 params
  - `services/analysis_service.py:518` `_run_analysis_inner` — 5 params
  - `services/chunk_service.py:737` `_upsert_link_ingested` — 5 params
  - `services/chunk_service.py:933` `_build_item_subtree` — 5 params
  - `services/ingestion_service.py:82` `ingest` — 5 params
  - `services/ingestion_service.py:158` `_build_indexed_chunks` — 5 params
  - `infra/opensearch_store.py:76` `OpenSearchStore.__init__` — 5 params
  - `infra/opensearch_pool.py:43` `get` — 5 params
- **Regle violee** : 3.2.3.
- **Remediation** :
  - `ChunkService.__init__` (11 params) et `update_store` (10) : grouper les deps connexes en dataclasses (`ChunkServiceDeps`, `StoreMutationRequest`).
  - `create_store` / `update_store` : un `StoreFormPayload` (nom, slug, kind, embedder, config, is_default, connection_*) clarifie l'API et evite la divergence entre POST et PATCH.
  - `_upsert_link_ingested` et `mark_completed` : passer un `IngestedLinkRow` / `CompletionPayload` dataclass.
- **Evolution vs 0.5.0** : regression. 0.5.0 listait 5 occurrences (top `AnalysisService.__init__` 8 params). 0.6.1 en compte 17, dont 3 avec >=9 params (`ChunkService.__init__` 11, `update_store` 10, `create_store` 9). Tous les nouveaux services arrives en 0.6.x (chunk + store CRUD + backend_resolver + version) sont entres avec des DI larges qu'aucune dataclass n'a regroupees.

### [MIN] Fichiers source de plus de 300 lignes

- **Localisation (frontend, productif, hors tests / i18n)** :
  - `frontend/src/pages/StudioPage.vue` — **1450** (etait 1422 en 0.5.0 — **+28**, regression — chantier toujours pas attaque)
  - `frontend/src/pages/DocsLibraryPage.vue` — 849 (nouveau)
  - `frontend/src/features/chunking/ui/ChunkPanel.vue` — 801 (inchange)
  - `frontend/src/features/analysis/ui/GraphView.vue` — 695 (reintroduit ; etait supprime en 0.5.0)
  - `frontend/src/features/analysis/ui/ResultTabs.vue` — 690 (inchange)
  - `frontend/src/features/chunks/ui/ChunksEditor.vue` — 622 (nouveau)
  - `frontend/src/features/store/ui/StoreForm.vue` — 520 (nouveau)
  - `frontend/src/pages/DocIngestTab.vue` — 518 (nouveau)
  - `frontend/src/pages/StoreDetailPage.vue` — 512 (nouveau)
  - `frontend/src/features/reasoning/ui/ReasoningPanel.vue` — 485 (reintroduit)
  - `frontend/src/pages/DocParseTab.vue` — 456 (nouveau)
  - `frontend/src/features/analysis/ui/StructureViewer.vue` — 447
  - `frontend/src/pages/StoresListPage.vue` — 415 (nouveau)
  - `frontend/src/pages/DocumentsPage.vue` — 412
  - `frontend/src/features/analysis/ui/NodeDetailsPanel.vue` — 409 (nouveau, lie a GraphView)
  - **+ 13 autres fichiers entre 300 et 400 lignes** (au total **28 fichiers productifs > 300 lignes**, vs 9 en 0.5.0)
- **Localisation (frontend, traductions / generes — informatif)** :
  - `frontend/src/shared/i18n.ts` — **1287** (etait 364 en 0.5.0 — **+253 %**, mais reste excludable car c'est de la traduction)
- **Localisation (backend, productif)** :
  - `document-parser/services/chunk_service.py` — **1003** (n'existait pas comme tel en 0.5.0 — c'est le service ajoute en 0.6.x pour le chunk CRUD)
  - `document-parser/services/analysis_service.py` — 552 (etait 409 — **+35 %**)
  - `document-parser/api/schemas.py` — 493 (etait <300 en 0.5.0 — montee suite a #279 connection fields, #267 versions, #283 push history)
  - `document-parser/main.py` — 471 (etait <300)
  - `document-parser/services/store_service.py` — 389 (nouveau)
  - `document-parser/domain/ports.py` — 339
  - `document-parser/domain/models.py` — 331
  - `document-parser/infra/neo4j/tree_writer.py` — 310 (reintroduit)
- **Regle violee** : 3.3.1.
- **Remediation** :
  - **Backend prioritaire** : decomposer `chunk_service.py` (1003 lignes) en `chunk_crud_service.py` + `chunk_push_service.py` + `chunk_diff_service.py` + `chunk_tree_builder.py` (les helpers `_build_tree_nodes`, `_build_item_subtree`, `_make_node`, `_display_label`, `_truncate` aux lignes 874-1003 forment deja un module autonome).
  - **Backend** : extraire le wiring DI de `main.py` vers `services/bootstrap.py` (cf. fiche audit Hexagonal Architecture).
  - **Frontend prioritaire** : `StudioPage.vue` (1450) — *deuxieme audit consecutif ou cette dette n'est pas attaquee*. Decouper en `<UploadSection>`, `<AnalysisSection>`, `<ResultsSection>` est le minimum. Objectif <400 lignes.
  - **Frontend** : `DocsLibraryPage.vue` (849), `ChunkPanel.vue` (801), `GraphView.vue` (695), `ResultTabs.vue` (690), `ChunksEditor.vue` (622) — chacun extrait par panneau / onglet, objectif <400 lignes.
- **Evolution vs 0.5.0** : **regression massive**.
  - Backend : 8 fichiers >300 lignes (vs 1 en 0.5.0). Trois facteurs : reintroduction du module `infra/neo4j/` (310 lignes pour `tree_writer.py` seule), arrivee du `chunk_service` (1003), grossissement de `analysis_service` (+35 %) et `main.py` (passage de <300 a 471).
  - Frontend : 28 fichiers >300 lignes (vs 9 en 0.5.0). Reintroduction de `GraphView.vue` (695), `ReasoningPanel.vue` (485) et al. (+8 fichiers reasoning/graph reintroduits), plus la nouvelle famille de pages 0.6.x : `DocsLibraryPage`, `DocIngestTab`, `DocParseTab`, `DocChunkTab`, `DocWorkspacePage`, `StoreDetailPage`, `StoresListPage`, `StoreCreatePage`, `StoreEditPage`, `StoreQueryPage`, `IngestLaunchDialog`. La discipline "<300 lignes par fichier" a saute en bloc avec l'arrivee des features 0.6.x.

---

## Points positifs

- **Zero TODO / FIXME / HACK / XXX** dans `document-parser/` et `frontend/src/` (grep multi-mot : aucun hit). Discipline maintenue depuis 0.4.0.
- **Zero code commente** laisse en place — grep `^[[:space:]]*#[[:space:]]*(def |return |import |class )` (Python) et `^[[:space:]]*//[[:space:]]*(function |const |let |return )` (TS/Vue) : aucun hit hors tests.
- **Zero `console.log` / `debugger`** dans `frontend/src/` hors tests.
- **Imports propres** : `ruff check document-parser/ --select I` passe sans erreur (rule `I` = isort, first-party `api|domain|persistence|services`).
- **Nommage explicite** : `_run_batched_conversion`, `_build_indexed_chunks`, `_resolve_targets`, `_upsert_link_ingested`, `promote_from_analysis_if_empty`, `find_latest_for_document`, `mark_link_failed` — tous porteurs d'intention. Pas d'abreviation cryptique (`dto`, `bbox`, `id`, `url`, `uri` restent acceptables).
- **`get_*` sans side-effect** verifie sur `get_by_slug`, `get_tree`, `get_pool`, `get_reasoning_graph` — lecture pure.
- **Aucun flag argument** identifie. Les options voyagent toujours par dataclasses (`ConversionOptions`, `ChunkingOptions`, `IngestionConfig`, `StoreBackendResolver`).
- **Code i18n separe** : `frontend/src/shared/i18n.ts` reste l'unique source FR/EN, jamais de chaine FR en dur dans un composant.
- **Une seule responsabilite par fichier** (3.3.2 OK malgre la taille) : `chunk_service.py` est gros mais tout son contenu concerne le chunk CRUD ; `main.py` est gros mais c'est exclusivement du bootstrap DI ; `neo4j/tree_writer.py` ne fait que de l'ecriture Neo4j. Pas de fichier fourre-tout.
- **Validation pipeline respectee** : `ruff check .` et `ruff format --check .` passent sur le backend (cf. `document-parser/CLAUDE.md`).

---

## Verdict partiel : GO CONDITIONNEL

Score **72 / 100**, 0 CRITICAL, **1 MAJOR**, 3 MINOR.

**Evolution vs 0.5.0** : **-6 points** (78 → 72). La regression est entierement portee par la reintroduction des modules `infra/neo4j/`, `features/reasoning/` et `features/analysis/ui/GraphView.vue` (qui avaient ete sortis en 0.5.0), combinee a la nouvelle dette frontend des pages 0.6.x (`DocsLibraryPage`, `DocIngestTab`, `DocParseTab`, `Store*Page`, `IngestLaunchDialog`...) et au nouveau service backend `chunk_service.py` (1003 lignes, methodes jusqu'a 118 lignes). Le MAJ Single Responsibility (`push_to_store`, `rechunk_document`, `lifespan`, `write_document`) est nouveau — 0.5.0 etait clean sur ce point.

**Conditions de remontee a GO (>=80)** :
1. Decomposer `services/chunk_service.py` (1003 lignes) en au moins 3 fichiers + ramener `push_to_store` sous 40 lignes par extraction de 3-4 helpers prives. Eteint a la fois le MAJ et les MIN 3.2.2 / 3.3.1 sur le backend.
2. Decomposer **au moins un** des trois plus gros fichiers Vue (`StudioPage.vue` 1450, `DocsLibraryPage.vue` 849, `ChunkPanel.vue` 801). `StudioPage.vue` est cible depuis 0.5.0 — second audit consecutif sans action.
3. Acter un plan de remediation explicite dans le changelog 0.6.1 si les points 1 et 2 ne sont pas tenus avant le merge dans `main`.

**Note** : aucun CRIT — la release n'est pas bloquee, mais la trajectoire est negative. Si 0.7.0 introduit autant de nouvelles pages sans hygiene de decomposition, le score passera sous 60 (NO-GO).
