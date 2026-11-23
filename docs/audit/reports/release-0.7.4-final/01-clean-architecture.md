# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.4
**Date** : 2026-11-20
**Auditeur** : claude-code
**Branche / commit** : `fix/0.7.4-editor-followups` @ `707a486`

Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5` (`docs/audit/reports/release-0.7.4-validation/01-clean-architecture.md`, 91/100, 0 CRIT / 1 MAJ / 1 MIN). Premier passage de ce contrôle à `a744f48` (91), repris à `707a486` après trois commits (`062bf70`, `414fdb7`, `707a486`) : voir « Contrôle à a744f48 ».

Suites lancées par le mainteneur sur `707a486` (non relancées ici) : ruff propre, 1789 passés / 15 ignorés.

Fiche : `docs/audit/audits/01-clean-architecture.md`, cible `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).
Méthode : lecture de l'arbre de travail, `git diff efc0bc5 707a486` et `git diff a744f48 707a486 -- document-parser`, greps de la fiche, comparaison de `tests/test_architecture.py` avec `git show efc0bc5:…`. Un script AST en lecture seule (aucun import du code audité) : graphe des imports runtime (hors `TYPE_CHECKING`, imports dans les fonctions compris), sens des couches, imports de pairs dans `services/`, cycles. Constructions de `bootstrap/builder.py` comparées à la main aux `__init__` des services touchés. Les messages de commit n'ont servi qu'à savoir où regarder.

Même lecture que la base : un item n'est conforme que si toutes les occurrences ont disparu, y compris celles qu'un cycle a créées.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 97 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 13 |

### Détail item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 1.1.1 | `domain/` sans FastAPI, aiosqlite ni lib infra | 3 | Oui | Grep de la fiche vide. `domain/quote_location.py` et les nouvelles fonctions de `domain/models.py` n'importent que `domain.*` et la stdlib. |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | Prédicats `AnalysisJob.can_be_current`/`can_be_current_of`/`has_docling_document` et règles de sélection (`domain/models.py:129`, `:164`, `:184`) : purs. `locate_quote` et `pick_within_budget` : calcul sur `DocumentIndex`. |
| 1.1.3 | Toute interaction externe passe par un protocole | 3 | Oui | `ChunkRepository.replace_and_select` / `replace_keeping_selection` (`domain/ports.py:296`, `:320`) ↔ `persistence/chunk_repo.py:136`, `:155` ; `CurrentAnalysisReader.load_current_original` ↔ `services/current_analysis.py:69` ; `ActiveAnalysisResultReader.load_current_edited` ↔ `services/analysis_edit_service.py:100`. Aucun appelant des méthodes retirées ou renommées (`replace_for_document`, `keep_selection`, `select_after_deleting`, `save_state`, `load_active_result`, `load_current_analysis`, `find_latest_for_document`, `LLMProvider.health_check`). |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | Aucun import. |
| 1.2.1 | `services/` sans `fastapi`/`starlette` | 3 | Oui | Grep vide. |
| 1.2.2 | Services → dépôts, jamais de SQL | 3 | Oui | Aucun SQL ni `aiosqlite` dans `services/`. |
| 1.2.3 | Règles métier dans `domain/` | 2 | Oui | Les trois familles de la base et l'occurrence ouverte à `a744f48` sont soldées : chaque décision sur la sélection est une fonction du domaine, les services l'appellent, la persistance ne garde que le SQL et la transaction. Détail ci-dessous. |
| 1.2.4 | Dépendances injectées, pas de concrétions | 2 | Oui | `ChunkService` reçoit `analysis_state_repo` (port) en plus (`services/chunk_service.py:56-64`, câblé `bootstrap/builder.py:149-155`) ; aucun service pair importé (`:20-26`) ; `ChunkPushService`/`DocumentTreeService` construits à la racine (`bootstrap/builder.py:204`, `:213`). |
| 1.3.1 | Routes sans `persistence/` | 3 | Oui | Grep vide ; aucun import runtime `api → infra/persistence`. |
| 1.3.2 | camelCase confiné à `api/schemas.py` | 1 | **Non** | Inchangé depuis `a744f48`. Voir [MIN]. |
| 1.3.3 | Endpoints qui délèguent toute la logique | 2 | Oui | Routes de chunks, arbre, diff, push : une méthode d'un service. `get_document` (`api/documents.py:94-107`) : deux lectures, un 404, un mappage ([INFO] n°2). Garde d'export inchangée et acceptée (`api/documents.py:130-136`). |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | Oui | Adaptateurs inchangés dans leur contrat ; `infra/host_guard.py` (nouveau `log_host_check`) reste un middleware, même lecture que la base ([INFO] n°3). |
| 1.4.2 | Config issue de `infra/settings.py` | 2 | Oui | Aucune nouvelle lecture d'environnement. |

Calcul : poids conformes = 3+3+3+2 + 3+3+2+2 + 3+2 + 3+2 = **31 / 32**. Non conforme : 1.3.2 (1). `31 / 32 × 100 = 96,9`, soit **97**.

Score alternatif : garde d'export refusée (1.3.3 non conforme) : 29/32 = **91**.

### 1.2.3 : ce que j'ai vérifié

**Familles de la base (soldées depuis `a744f48`, toujours vraies) :**
- localisation de citation : `domain/quote_location.py:22` (`locate_quote`), `:50`, `:81` ; le service n'appelle que `locate_quote` (`services/citation_service.py:135`) ;
- lecture budgétée : `pick_within_budget` est maintenant dans `domain/element_reader.py:59`, appelée par `services/navigation_service.py:151` ;
- « seule une analyse terminée peut être courante » : prédicats `domain/models.py:221-232`, utilisés par `persistence/analysis_repo.py:177`, `services/version_service.py:173`, `services/analysis_edit_service.py:280`, `services/current_analysis.py:75`, `services/document_tree_service.py:57`, `services/export_service.py:134`.

**Sélection de l'analyse active, les trois écrivains :**

| Écriture | Décision (domaine) | Service | Persistance |
|----------|--------------------|---------|-------------|
| Suppression | `DocumentAnalysisState.resolve_selection_after_deleting` (`domain/models.py:129`) | — | `persistence/analysis_repo.py:206-237` : verrou, lecture d'état, `DELETE`, appel du domaine, écriture |
| Restauration | `resolve_selection_after_restore` (`domain/models.py:164`) | `services/version_service.py:184-192` lit l'état et le repli, appelle la règle | `replace_and_select` (`persistence/chunk_repo.py:136`) : upsert de la valeur reçue |
| Régénération | `resolve_selection_after_rechunk` (`domain/models.py:184`) | `services/chunk_service.py:224-235` lit l'état, appelle la règle | `replace_keeping_selection` (`persistence/chunk_repo.py:155`) : `ON CONFLICT DO NOTHING` (`persistence/document_analysis_repo.py:27`, `:90`) |

Ce qui tient : les trois décisions sont écrites et documentées dans le domaine, à côté de `resolve_current_analysis_id`, et les services les appellent. Le drapeau `keep_selection` a disparu au profit de deux méthodes de port nommées ; le choix entre `write_selection` et `adopt_selection` est une fonction passée en interne (`persistence/chunk_repo.py:177`, `:206`), pas un paramètre que l'appelant règle.

Trois nuances, sans effet sur la note :
- **régénération** : quand une ligne d'état existe, la valeur que rend le domaine (`state.active_analysis_id`) est ignorée par le `DO NOTHING` ; c'est le SQL qui garantit « la sélection ne bouge pas » contre une sélection faite après la lecture. La règle est donc dite deux fois, une fois en Python, une fois en SQL atomique. La docstring du domaine (`domain/models.py:190-195`) et celle du port (`domain/ports.py:320-343`) l'écrivent ; c'est la seule façon d'avoir la règle et l'atomicité sans verrou, je l'accepte ;
- **restauration** : le service ne lit le repli que si la règle peut le choisir (`services/version_service.py:186-188`), ce qui recopie deux conditions du domaine ; c'est une optimisation de lecture, comme la condition recopiée dans la suppression (`persistence/analysis_repo.py:229`) ;
- **suppression** : le critère « dernière analyse terminée avec document Docling » est en SQL (`persistence/analysis_repo.py:249-268`), déclaré comme forme SQL de `has_docling_document` ; c'est une sélection de requête. `BEGIN IMMEDIATE` (`:218`) est de la gestion de transaction, avec un précédent (`persistence/analysis_edit_repo.py:150`).

**Graphe des modules du domaine** : plus de cycle. `domain/navigation.py` n'importe plus que la stdlib (et `collections.abc` sous `TYPE_CHECKING`) ; `pick_within_budget` est dans `domain/element_reader.py`, qui dépendait déjà de `navigation`. Le script ne trouve plus aucun import dans une fonction dans `domain/`.

---

## Ecarts constates

### [MIN] camelCase hors `api/schemas.py`

- **Localisation** : `services/chunk_push_service.py:91-105`, `:156`, `:284-291`, `:340-343` ; `services/analysis_service.py:48-51` ; `services/version_service.py:51-60` ; `services/analysis_edit_service.py:199` (`targetSequence`) ; `infra/docling_projector.py:56`, `:222-231` ; types de commande (`domain/analysis_editing.py:286`, `infra/docling_editor.py:124-139`, valeurs persistées).
- **Constat** : réduit depuis la base (plus de dict de payload écrits dans `api/analysis_edits.py`), inchangé depuis `a744f48`. Le JSON des chunks et des versions reste produit en camelCase par les services.
- **Regle violee** : item 1.3.2 (poids 1).
- **Remediation** : documenter `chunks_json`, `chunks_snapshot` et le payload de commande v1 comme formats durables (et les exclure de l'item), puis faire rendre des dataclasses aux services de chunks et mapper dans `api/schemas.py`. Effort S.

### [INFO] n°1 — Réduit : le format persisté des commandes vient des modèles de requête HTTP

- **Localisation** : `api/analysis_edits.py:94-103` (`command.model_dump(by_alias=True, exclude={"type"})`) ; modèles de requête `api/schemas.py:180-215` ; modèles de payload stocké `api/schemas.py:324-370`.
- **Constat** : `062bf70` a remplacé les modèles de payload générés par `create_model` par des classes écrites à la main, gardées en phase par `tests/test_schemas.py`. La lecture du format stocké est donc explicite. L'écriture reste un `model_dump` du modèle de requête : ce qui entre dans le flux d'édition (et dans son hachage) suit toujours le DTO HTTP.
- **Remediation** : une dataclass par commande dans `domain/analysis_editing.py` avec sa forme v1, l'API ne faisant que mapper ; ou un test qui fige le JSON stocké de chaque type.

### [INFO] n°2 — `get_document` lit un service et un port secondaire

- **Localisation** : `api/documents.py:94-107` ; `api/deps.py:42-45` ; slot `AppState.current_analysis` (`api/state.py:59`).
- **Constat** : deux lectures indépendantes, un 404 entre les deux, un mappage : pas d'orchestration. La route dépend de `CurrentAnalysisReader`, un port de `domain/ports.py` pensé pour les services ; l'implémentation est un service, le sens des couches tient.
- **Remediation** : facultative, `DocumentService.find_details(doc_id)`.

### [INFO] n°3 — Middlewares HTTP dans `infra/`

- **Localisation** : `infra/host_guard.py:21-22`, `:105` ; `infra/body_limit.py:13-14`, `:20` ; `infra/rate_limiter.py` ; `main.py:39-41`.
- **Constat et remédiation** : inchangés (déplacer dans `api/middleware/` ou acter dans la fiche).

### [INFO] n°4 — `stat` sur la boucle d'événements

- **Localisation** : `services/preview_service.py:89`, `:106` ; `services/export_service.py:96-97` ; `services/document_service.py:169`.
- **Constat** : inchangé ; négligeable sur disque local.

### [INFO] n°5 — Contrôles « analyse terminée » de l'ancienne API de chunks

- **Localisation** : `services/analysis_service.py:218`, `:242`, `:264`.
- **Constat** : antérieurs à la base, non comptés par elle ; règle voisine (« on ne retouche que les résultats d'une analyse terminée ») répétée trois fois. Je garde la lecture de la base.
- **Remediation** : un prédicat `AnalysisJob.has_results()` si cette API survit à 0.7.4.

### [INFO] Reportés de la base, inchangés (8)

1. `PdfiumInspector` compte les pages d'un upload avec poppler (`infra/pdf_inspector.py:16`, `:53`) ;
2. `VectorStore.get_chunks` : `limit: int = 1000` (`domain/ports.py:581`) contre `int | None = None` (`infra/opensearch_store.py:173`) ;
3. `DocumentMerger` (`domain/ports.py:102`) et `DoclingDocumentMerger` (`infra/docling_merger.py:12`) jamais câblés ;
4. `persistence` importe `infra` (`persistence/store_repo.py` → `infra.secrets`, seul écart de couche du graphe, entrée legacy du test) ;
5. le domaine lit le schéma JSON Docling (`domain/element_reader.py`) ;
6. configuration hors `settings` : `persistence/database.py:22` (`DB_PATH`), `:342` (`DEFAULT_EMBEDDER`), `infra/preview_cache.py:16` ;
7. contrôle service → service limité à cinq modules (`tests/test_architecture.py:119-125`) ;
8. frontend `shared` → `features` : `frontend/src/shared/ui/AppSidebar.vue:55-56` (hors barème).

---

## Contrôle à a744f48

Premier passage de ce contrôle, le 2026-11-19, sur `a744f48` : **91/100, 11/13, 0 CRIT / 1 MAJ / 1 MIN / 14 INFO, GO**.
- Le MAJ de la base était soldé sur toutes ses occurrences (localisation de citation, lecture budgétée, prédicat « analyse terminée »).
- Mais `73ceaf3` avait gelé `DocumentAnalysisState` et retiré ses transitions (`restore`, `record_chunk_source`, `select`). La sélection posée par une restauration était décidée dans `services/version_service.py:182-186`, et « une régénération ne change pas la sélection » n'existait plus que sous la forme d'un drapeau `keep_selection=True` et d'un `ON CONFLICT DO NOTHING`. J'avais compté une nouvelle occurrence 1.2.3 (MAJ), régression du cycle.
- Deux INFO nouveaux : cycle d'imports dans le domaine (`domain/navigation.py:395`, import dans `pick_within_budget`) et payloads stockés générés par `create_model` à partir des modèles de requête.

Ce qu'il en est à `707a486` :

| Constat à `a744f48` | Statut à `707a486` | Preuve |
|----------------------|--------------------|--------|
| [MAJ] 1.2.3 — sélection de restauration décidée dans le service | **Résolu** | `resolve_selection_after_restore` (`domain/models.py:164`), appelée par `services/version_service.py:189` |
| [MAJ] 1.2.3 — règle de régénération réduite à un drapeau | **Résolu** | `resolve_selection_after_rechunk` (`domain/models.py:184`), appelée par `services/chunk_service.py:235` ; drapeau remplacé par `replace_keeping_selection` (`domain/ports.py:320`) |
| [INFO] cycle `navigation` ↔ `element_reader` | **Résolu** | `pick_within_budget` dans `domain/element_reader.py:59` ; aucun import dans une fonction dans `domain/` |
| [INFO] format persisté dérivé des DTO | **Réduit** | modèles de payload écrits à la main (`api/schemas.py:324-370`) ; écriture toujours par `model_dump` (`api/analysis_edits.py:100`) |
| [MIN] 1.3.2 | Inchangé | — |
| Autres INFO | Inchangés | — |

**Régressions cherchées dans les trois commits, aucune trouvée** :
- graphe des imports runtime : aucun nouvel écart de couche ; seul écart, `persistence.store_repo → infra.secrets`, déjà en base ; `services/chunk_service.py` importe `domain.exceptions` (domaine), pas de pair ;
- `tests/test_architecture.py` : aucune modification depuis `efc0bc5` (diff vide sur `efc0bc5..707a486`), ni resserré ni élargi ;
- constructions : `ChunkService(analysis_state_repo=…)` câblé (`bootstrap/builder.py:153`) et seul site de construction hors tests ; ports et adaptateurs de `ChunkRepository` alignés (mêmes paramètres) ;
- comportement nouveau : une régénération dont l'analyse est supprimée entre-temps répond 409 (`services/chunk_service.py:237-240`, `ChunkConflictError.http_status = 409`, `services/chunk_errors.py:34-35`) ; l'erreur du dépôt est traduite dans le service, la route n'en sait rien.

---

## Delta vs validation

**Score : 91 → 97 (Δ +6).** 11/13 → 12/13 items conformes. Le MAJ 1.2.3 est soldé, y compris l'occurrence que ce cycle avait ouverte. Reste le MIN 1.3.2.

| Écart de la validation (`efc0bc5`) | Statut à `707a486` | Preuve |
|-------------------------------------|--------------------|--------|
| [MAJ] 1.2.3 — `_locate_quote`, `_locate_across`, `_trim_left` | **Résolu** | `domain/quote_location.py:22`, `:50`, `:81` ; `services/citation_service.py:135` |
| [MAJ] 1.2.3 — `_pick` | **Résolu** | `domain/element_reader.py:59` ; `services/navigation_service.py:151` |
| [MAJ] 1.2.3 — « seule une analyse terminée est courante » dans cinq fichiers | **Résolu** | `domain/models.py:221-232` et ses six sites d'appel |
| [MIN] 1.3.2 camelCase hors schémas | **Réduit** | Plus de dict de payload dans `api/analysis_edits.py` ; services de chunks, versions et projecteur inchangés |
| [INFO] `ChunkService` construit ses pairs | **Résolu** | `services/chunk_service.py:20-26`, `:56-64` ; `bootstrap/builder.py:204`, `:213` |
| [INFO] Export PDF sans `resolve` | **Résolu** | `services/export_service.py:96-97` |
| [INFO] `AppState` garde trois dépôts inutilisés | **Résolu** | `api/state.py:50-89` : plus aucun dépôt |
| [INFO] Port inutilisé `find_latest_for_document` | **Résolu** | Retiré du port et de l'adaptateur |
| [INFO] `get_document` assemble deux lectures | Modifié | Service + port : `api/documents.py:94-107` |
| [INFO] Middlewares HTTP, `stat` sur la boucle | Inchangés | [INFO] n°3, n°4 |
| [INFO] poppler, `get_chunks`, `DocumentMerger`, `persistence → infra`, schéma Docling, config, pairs, frontend | Inchangés | Voir « Reportés » |

---

## Points positifs

- **Les règles de sélection de l'analyse active sont toutes dans le domaine**, à côté de la règle de lecture : suppression, restauration, régénération, chacune une fonction documentée, avec ses tests (`tests/test_current_analysis.py`).
- **Les deux algorithmes de l'agent sont dans le domaine** (`domain/quote_location.py`, `domain/element_reader.py`), et le module de valeurs `domain/navigation.py` redevient une feuille.
- **Des méthodes de port nommées plutôt qu'un drapeau** : `replace_and_select` et `replace_keeping_selection` disent ce que fait l'écriture.
- **Plus de façade de chunks** : trois services étroits, construits à la racine de composition.
- **Ports nettoyés** : méthodes mortes retirées des protocoles et des adaptateurs sans appelant laissé derrière.

---

## Verdict partiel : GO

97/100, 0 CRITICAL, 0 MAJOR, 1 MINOR. En lecture stricte sur la garde d'export, 91. Reste le camelCase des services de chunks et de versions (MIN) et des INFO sans risque.

Réserve : je n'ai rien exécuté. Les résultats de suites cités sont ceux du mainteneur. Je n'ai pas vérifié le SQL lui-même (triggers de `document_analysis_state`, `BEGIN IMMEDIATE` sur la connexion aiosqlite), ni le démarrage de FastAPI/MCP.
