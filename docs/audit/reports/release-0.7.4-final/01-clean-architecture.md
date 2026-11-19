# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Branche / commit** : `fix/0.7.4-editor-followups` @ `a744f48`

Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5` (`docs/audit/reports/release-0.7.4-validation/01-clean-architecture.md`, 91/100, 0 CRIT / 1 MAJ / 1 MIN).

Suites lancées par le mainteneur sur ce commit (non relancées ici) : ruff propre, 1773 passés / 15 ignorés ; frontend eslint, prettier, vue-tsc propres, 604 tests, build OK.

Fiche : `docs/audit/audits/01-clean-architecture.md`, cible `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).
Méthode : lecture de l'arbre de travail, `git diff efc0bc5 a744f48 -- document-parser`, greps de la fiche, comparaison de `tests/test_architecture.py` avec `git show efc0bc5:…`. Un script AST en lecture seule (aucun import du code audité) : graphe des imports runtime (hors `TYPE_CHECKING`, imports dans les fonctions compris), sens des couches, imports de pairs dans `services/`, cycles. Constructions de `bootstrap/builder.py` comparées à la main aux `__init__` des services touchés. Les messages de commit n'ont servi qu'à savoir où regarder.

Même lecture que la base : un item n'est conforme que si toutes les occurrences ont disparu, y compris celles que le cycle a créées.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 11 / 13 |
| Score | 91 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 14 |

### Détail item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 1.1.1 | `domain/` sans FastAPI, aiosqlite ni lib infra | 3 | Oui | Grep de la fiche vide. `domain/quote_location.py` n'importe que `domain.*`. |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | Nouveaux prédicats `AnalysisJob.can_be_current`/`can_be_current_of`/`has_docling_document` (`domain/models.py:184-195`) et `select_after_deleting` (`:129`) : purs. `locate_quote` et `pick_within_budget` : calcul sur `DocumentIndex`. |
| 1.1.3 | Toute interaction externe passe par un protocole | 3 | Oui | Ports ajustés et cohérents avec leurs implémentations : `ChunkRepository.replace_for_document` (`domain/ports.py:295`) ↔ `persistence/chunk_repo.py:132` ; `CurrentAnalysisReader.load_current_original` ↔ `services/current_analysis.py:69` ; `ActiveAnalysisResultReader.load_current_edited` ↔ `services/analysis_edit_service.py:100`. Aucun appelant des méthodes retirées (`save_state`, `load_active_result`, `load_current_analysis`, `soft_delete_for_document`, `get_default`, `find_latest_for_document`, `LLMProvider.health_check`). |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | Aucun import. `DocumentAnalysisState` reste une dataclass (désormais gelée). |
| 1.2.1 | `services/` sans `fastapi`/`starlette` | 3 | Oui | Grep vide. |
| 1.2.2 | Services → dépôts, jamais de SQL | 3 | Oui | Aucun SQL ni `aiosqlite` dans `services/`. Le SQL de la resélection est dans `persistence/analysis_repo.py`. |
| 1.2.3 | Règles métier dans `domain/` | 2 | **Non** | Les trois familles de la base sont soldées (voir Delta). Mais le cycle a sorti du domaine les règles d'écriture de l'agrégat `DocumentAnalysisState` (`restore`, `record_chunk_source`, `select`) : la sélection posée par une restauration est décidée dans `services/version_service.py:182-186`. Voir [MAJ]. |
| 1.2.4 | Dépendances injectées, pas de concrétions | 2 | Oui | `ChunkService` n'importe plus aucun service pair (`services/chunk_service.py:20-25`) ; `ChunkPushService` et `DocumentTreeService` sont construits dans `bootstrap/builder.py:203-217` avec des ports. Aucun import runtime `services → infra/persistence`. |
| 1.3.1 | Routes sans `persistence/` | 3 | Oui | Grep vide ; aucun import runtime `api → infra/persistence`. |
| 1.3.2 | camelCase confiné à `api/schemas.py` | 1 | **Non** | Réduit : les dict littéraux de `api/analysis_edits.py` ont disparu. Reste le JSON camelCase des services de chunks, de versions et du projecteur. Voir [MIN]. |
| 1.3.3 | Endpoints qui délèguent toute la logique | 2 | Oui | Chaque route de `api/document_chunks.py` appelle une seule méthode d'un seul service. `get_document` (`api/documents.py:94-107`) fait deux lectures (service + résolveur) séparées par un 404 : pas d'orchestration, voir [INFO] n°3. Garde d'export inchangée (`api/documents.py:130-136`), toujours acceptée pour les raisons de la base. |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | Oui | `OllamaProvider` suit le port allégé (`infra/llm/ollama_provider.py`, plus de `health_check`, la sonde est `infra/llm/ollama_probe.py`). Middlewares ASGI : même lecture que la base, [INFO] n°4. |
| 1.4.2 | Config issue de `infra/settings.py` | 2 | Oui | Aucune nouvelle lecture d'environnement (`infra/settings.py:110-111` : commentaire seulement). Les lectures hors `settings` restent celles de la base ([INFO] reporté n°6). |

Calcul : poids conformes = 3+3+3+2 + 3+3 + 2 + 3 + 2 + 3+2 = **29 / 32**. Non conformes : 1.2.3 (2), 1.3.2 (1). `29 / 32 × 100 = 90,6`, soit **91**.

Scores alternatifs :
- restauration acceptée comme orchestration (1.2.3 conforme) : 31/32 = **97** ;
- garde d'export refusée (1.3.3 non conforme) : 27/32 = **84**.

### 1.2.3 : ce que j'ai vérifié

**Soldé, dans le code et pas seulement dans les messages :**
- localisation de citation : `locate_quote` (`domain/quote_location.py:22`), `_locate_across` (`:50`), `_trim_left` (`:81`) ; le service n'appelle plus que `locate_quote` (`services/citation_service.py:31`, `:135`). Aucune copie restée dans le service ;
- lecture budgétée : `pick_within_budget` (`domain/navigation.py:382`), appelée par `services/navigation_service.py:147` ; `_pick` n'existe plus ;
- « seule une analyse terminée peut être courante » : un prédicat (`domain/models.py:184`, `:188`, `:192`) utilisé par les sites que la base listait : `persistence/analysis_repo.py:177`, `services/version_service.py:172`, `services/analysis_edit_service.py:280`, `services/current_analysis.py:75`, `services/document_tree_service.py:57`, et en plus `services/export_service.py:134`. Plus aucun `status == COMPLETED` sur ce sujet dans `services/`, `persistence/`, `api/`.

**Resélection après suppression** (`persistence/analysis_repo.py:206-237`) : la décision est dans le domaine (`DocumentAnalysisState.select_after_deleting`, `domain/models.py:129`), le dépôt ne fait que le SQL. Deux nuances, sans effet sur la note :
- le dépôt recopie la condition du domaine (`state.active_analysis_id == job_id`, `:229`) pour éviter une requête inutile ; c'est une optimisation, la décision reste celle du domaine ;
- le critère « dernière analyse terminée avec document Docling » est écrit en SQL (`_find_latest_parsed_ids`, `:249-268`), déclaré comme forme SQL de `has_docling_document`. C'est une sélection de requête, partagée avec la règle de repli : acceptable.

`BEGIN IMMEDIATE` dans le dépôt (`:218`) : c'est de la gestion de transaction, donc de la persistance, avec un précédent (`persistence/analysis_edit_repo.py:150`). Pas un écart.

**Graphe des modules du domaine** : un cycle est apparu, `domain.navigation → domain.element_reader → domain.navigation` (plus `domain.parse_index`), cassé par un import dans la fonction (`domain/navigation.py:395`). Il n'existait pas à `efc0bc5` (`navigation` n'importait que la stdlib et des modules sous `TYPE_CHECKING`). Il ne casse rien à l'exécution, mais il contredit l'en-tête du module (« Everything here is pure data… the projections… live in `domain.element_reader` »). [INFO] n°1.

---

## Ecarts constates

### [MAJ] Les règles d'écriture de l'agrégat d'analyse ont quitté le domaine

- **Localisation** :
  - `services/version_service.py:182-186` : la restauration décide elle-même de la sélection (« une version sans analyse, sur un document sans ligne d'état, garde l'analyse de repli »), avec une lecture du dépôt d'état et du résolveur ;
  - `services/version_service.py:189-193` : le passage version → (sélection, source des chunks), qui était `DocumentAnalysisState.restore` (`efc0bc5:document-parser/domain/models.py:158`) ;
  - `services/chunk_service.py:223-230` et `persistence/chunk_repo.py:160-163`, `persistence/document_analysis_repo.py:90-103` : « une régénération ne change jamais la sélection, mais une ligne qu'elle crée reprend l'analyse courante » n'est plus écrit que par un drapeau `keep_selection=True` et un `ON CONFLICT DO NOTHING`.
- **Constat** : à `efc0bc5`, l'agrégat portait ses transitions (`select`, `clear_selection`, `record_chunk_source`, `restore`) et le dépôt écrivait les parties modifiées. `73ceaf3` l'a gelé (`domain/models.py:97-141`) : il ne sait plus que lire (`are_chunks_stale`) et calculer la sélection après suppression. Le choix de dépôt se défend (chaque écrivain écrit sa partie, pas de lecture-modification-écriture), mais les décisions sur l'état sont maintenant dans un service et dans le mode d'écriture SQL choisi par l'appelant. La nouvelle règle de repli à la restauration a été écrite dans le service, alors que la même règle côté lecture (`resolve_current_analysis_id`, `domain/models.py:144`) est dans le domaine. C'est petit (quatre lignes), mais c'est une régression sur l'item que la base suivait, introduite par ce cycle.
- **Regle violee** : item 1.2.3 (poids 2).
- **Remediation** (effort XS) : une fonction de domaine, à côté de `resolve_current_analysis_id`, par exemple `selection_after_restore(state: DocumentAnalysisState | None, version: DocumentVersion, fallback_id: str | None) -> str | None` (l'analyse de la version si elle existe, sinon le repli si aucune ligne n'existe, sinon None), appelée par `VersionService.restore`. Écrire aussi dans la docstring de `DocumentAnalysisState` que la régénération ne change pas la sélection, et le tester au niveau du domaine plutôt que par le seul drapeau du dépôt.

### [MIN] camelCase hors `api/schemas.py`

- **Localisation** : `services/chunk_push_service.py:91-105`, `:156`, `:284-291`, `:340-343` ; `services/analysis_service.py:48-51` ; `services/version_service.py:51-60` ; `services/analysis_edit_service.py:199` (`targetSequence`) ; `infra/docling_projector.py:56`, `:222-231` ; types de commande (`domain/analysis_editing.py:286`, `infra/docling_editor.py:124-139`, valeurs persistées).
- **Constat** : réduit. Les payloads de commande ne sont plus des dict écrits à la main dans la route : ils sont dérivés des modèles de requête (`api/analysis_edits.py:94-103`, `api/schemas.py:300-357`). Le JSON des chunks et des versions reste produit en camelCase par les services.
- **Regle violee** : item 1.3.2 (poids 1).
- **Remediation** : inchangée. Documenter `chunks_json`, `chunks_snapshot` et le payload de commande v1 comme formats durables (et les exclure de l'item), puis faire rendre des dataclasses aux services de chunks et mapper dans `api/schemas.py`. Effort S.

### [INFO] n°1 — Nouveau : cycle d'imports dans le domaine

- **Localisation** : `domain/navigation.py:395` (`from domain.element_reader import resolve` dans `pick_within_budget`) ; `domain/element_reader.py:13` importe `domain.navigation`.
- **Constat** : `navigation` est le module de valeurs pures dont dépendent `element_reader`, `parse_index`, `outline_builder`, `source_map`. Y poser un algorithme qui a besoin de `element_reader` crée le premier cycle du domaine. Le cycle `services`/`infra` du graphe ne change pas ailleurs.
- **Remediation** : déplacer `pick_within_budget` dans `domain/element_reader.py` (il en dépend déjà) ou dans un module `domain/budgeted_read.py`, comme `quote_location.py`. Copier-coller.

### [INFO] n°2 — Nouveau : le format persisté des commandes dépend des DTO HTTP

- **Localisation** : `api/analysis_edits.py:94-103` (`command.model_dump(by_alias=True, exclude={"type"})`) ; `api/schemas.py:180-215` (modèles de requête), `:300-357` (modèles de payload stocké dérivés).
- **Constat** : le payload devient une ligne du flux d'édition et entre dans le hachage (`domain/analysis_editing.py`). Il est désormais défini par les modèles Pydantic de la couche HTTP : renommer ou ajouter un champ d'API change le format stocké et les hachages. Avant, la route l'écrivait à la main, déjà dans `api/` ; le couplage est plus serré, pas nouveau de couche.
- **Remediation** : une dataclass par commande dans `domain/analysis_editing.py` avec sa forme v1, l'API ne faisant que mapper ; ou acter que les modèles de requête sont la définition du format v1 et les geler (test de non-régression sur le JSON stocké).

### [INFO] n°3 — Modifié : `get_document` lit un service et un port secondaire

- **Localisation** : `api/documents.py:94-107` (`service.find_with_store_links`, puis `current.find_current_analysis_id`) ; `api/deps.py:42-45`, slot `AppState.current_analysis` (`api/state.py:59`).
- **Constat** : deux lectures indépendantes, un 404 entre les deux, un mappage. Pas d'orchestration. Mais la route dépend maintenant de `CurrentAnalysisReader`, un port de `domain/ports.py` pensé pour les services ; l'implémentation est un service (`CurrentAnalysisResolver`), donc le sens des couches tient.
- **Remediation** : rien d'obligatoire. Si l'équipe veut que l'API n'atteigne que des services : `DocumentService.find_details(doc_id)` (proposé en base).

### [INFO] n°4 — Reporté : middlewares HTTP dans `infra/`

- **Localisation** : `infra/host_guard.py:21-22`, `:64` (réécrit, toujours starlette, répond désormais en JSON) ; `infra/body_limit.py:13-14`, `:20` ; `infra/rate_limiter.py` ; câblés dans `main.py:39-41`.
- **Constat et remédiation** : inchangés (déplacer dans `api/middleware/` ou acter dans la fiche).

### [INFO] n°5 — Reporté : `stat` sur la boucle d'événements

- **Localisation** : `services/preview_service.py:89`, `:106` ; `services/export_service.py:96-97` ; `services/document_service.py:169`.
- **Constat** : inchangé ; l'export appelle désormais `resolve` puis `has_file`, deux appels synchrones au lieu d'un.

### [INFO] n°6 — Non relevé en base : contrôles « analyse terminée » de l'ancienne API de chunks

- **Localisation** : `services/analysis_service.py:218`, `:242`, `:264` (`job.status != AnalysisStatus.COMPLETED`).
- **Constat** : présents à `efc0bc5` (`:233`, `:257`, `:279`) et non comptés par la base. Ce n'est pas la règle « courante », mais « on ne retouche que les résultats d'une analyse terminée », répétée trois fois dans un service sur l'API historique des chunks par analyse. Je garde la lecture de la base (non compté).
- **Remediation** : un prédicat `AnalysisJob.has_results()` ou un garde unique, si cette API survit à 0.7.4.

### [INFO] Reportés de la base, inchangés (8)

1. `PdfiumInspector` compte les pages d'un upload avec poppler (`infra/pdf_inspector.py:16`, `:53`) ;
2. `VectorStore.get_chunks` : `limit: int = 1000` (`domain/ports.py:558`) contre `int | None = None` (`infra/opensearch_store.py:173`) ;
3. `DocumentMerger` (`domain/ports.py:102`) et `DoclingDocumentMerger` (`infra/docling_merger.py:12`) jamais câblés ;
4. `persistence` importe `infra` (`persistence/store_repo.py` → `infra.secrets`, seul écart de couche du graphe, entrée legacy du test) ;
5. le domaine lit le schéma JSON Docling (`domain/element_reader.py`) ;
6. configuration hors `settings` : `persistence/database.py:22` (`DB_PATH`), `:342` (`DEFAULT_EMBEDDER`), `infra/preview_cache.py:16` ;
7. contrôle service → service limité à cinq modules (`tests/test_architecture.py:119-125`) ; moins grave qu'en base puisque `ChunkService` n'importe plus de pair, mais rien n'empêche qu'il revienne ;
8. frontend `shared` → `features` : `frontend/src/shared/ui/AppSidebar.vue:55-56` (hors barème).

---

## Delta vs validation

**Score : 91 → 91 (Δ 0).** 11/13 → 11/13 items conformes. Le MAJ de la base est soldé sur toutes ses occurrences, mais le cycle en a ouvert un nouveau, petit, sur le même item. Si l'on accepte la décision de restauration comme orchestration : 97.

| Écart de la validation (`efc0bc5`) | Statut à `a744f48` | Preuve |
|-------------------------------------|--------------------|--------|
| [MAJ] 1.2.3 — `_locate_quote`, `_locate_across`, `_trim_left` | **Résolu** | `domain/quote_location.py:22`, `:50`, `:81` ; `services/citation_service.py:135` |
| [MAJ] 1.2.3 — `_pick` | **Résolu** | `domain/navigation.py:382` ; `services/navigation_service.py:147` |
| [MAJ] 1.2.3 — « seule une analyse terminée est courante » dans cinq fichiers | **Résolu** | `domain/models.py:184-195` ; sites `persistence/analysis_repo.py:177`, `services/version_service.py:172`, `services/analysis_edit_service.py:280`, `services/current_analysis.py:75`, `services/document_tree_service.py:57`, `services/export_service.py:134` |
| [MAJ] 1.2.3 dans son ensemble | **Pire sur un autre point** | Nouvelle occurrence : transitions de `DocumentAnalysisState` sorties du domaine, `services/version_service.py:182-186` |
| [MIN] 1.3.2 camelCase hors schémas | **Réduit** | Plus de dict de payload dans `api/analysis_edits.py` ; services de chunks, versions et projecteur inchangés |
| [INFO] `ChunkService` construit ses pairs | **Résolu** | `services/chunk_service.py:20-25`, `:52-58` ; `bootstrap/builder.py:203-217` |
| [INFO] Middlewares HTTP dans `infra/` | Inchangé | `infra/host_guard.py:64`, `infra/body_limit.py:20` |
| [INFO] `get_document` assemble deux lectures | Modifié | Deux collaborateurs au lieu d'un service : `api/documents.py:94-107` |
| [INFO] Export PDF sans `resolve` | **Résolu** | `services/export_service.py:96-97` |
| [INFO] `stat` sur la boucle | Inchangé | Voir [INFO] n°5 |
| [INFO] `AppState` garde trois dépôts inutilisés | **Résolu** | `api/state.py:50-89` : plus aucun dépôt |
| [INFO] Port inutilisé `find_latest_for_document` | **Résolu** | Retiré de `domain/ports.py` et de `persistence/document_version_repo.py` |
| [INFO] poppler, `get_chunks`, `DocumentMerger`, `persistence → infra`, schéma Docling, config, pairs, frontend | Inchangés | Voir « Reportés » |

**Régressions introduites par le cycle** :
- 1.2.3 : règles d'écriture de l'agrégat sorties du domaine ([MAJ]) ;
- cycle d'imports nouveau dans le domaine (`domain/navigation.py:395`, [INFO] n°1) ;
- format persisté des commandes défini par les DTO HTTP ([INFO] n°2).

**Régressions cherchées, non trouvées** :
- graphe des imports runtime : aucun `domain → hors domaine`, `services → infra/persistence/api/bootstrap/mcp_adapter`, `api → persistence/infra`, `infra → services/api/persistence` ; seul écart de couche : `persistence.store_repo → infra.secrets`, déjà en base ;
- imports de pairs dans `services/` : uniquement des modules d'erreurs ou de configuration (`*_errors`, `errors`, `config_overrides`, `navigation_config`) ;
- `tests/test_architecture.py` : **identique** à `efc0bc5` (diff vide). Ni resserré ni élargi ; `_LEGACY_LAYER_IMPORTS` et la liste des cinq modules inchangés ;
- constructions : `ChunkService`, `ChunkPushService`, `DocumentTreeService`, `VersionService`, `AnalysisEditService`, `ExportService` dans `bootstrap/builder.py:128-217` correspondent à leurs `__init__` ; `build_document_service` et `DocumentService` ont perdu `current_analysis` des deux côtés ; `build_chunk_service` supprimé sans appelant restant ;
- routes : chaque route de chunks, arbre, diff et push appelle une méthode d'un service ; la route de l'éditeur ne fait que du mappage (le passage en `asyncio.to_thread`, `api/analysis_edits.py:59-62`, est un choix d'exécution, pas de la logique).

---

## Points positifs

- **Les deux algorithmes de l'agent sont dans le domaine**, testés seuls (`tests/test_quote_location.py`) : ce qu'une citation prouve et ce qu'un agent lit ne dépendent plus d'un service.
- **Un prédicat pour « analyse courante possible »** et un pour « analyse avec document Docling », utilisés partout, y compris par l'export qui avait sa propre condition.
- **La suppression de l'analyse active est atomique** : verrou d'écriture pris d'abord, décision du domaine, SQL seulement dans le dépôt, même transaction (`persistence/analysis_repo.py:215-237`).
- **Plus de façade de chunks** : trois services étroits, construits à la racine de composition, chacun reçu par les routes qui en ont besoin.
- **Ports nettoyés** : six méthodes mortes retirées des protocoles et des adaptateurs sans appelant laissé derrière.

---

## Verdict partiel : GO

91/100, 0 CRITICAL, 1 MAJOR, 1 MINOR. Le MAJ restant est petit et local (une décision de quatre lignes dans `VersionService.restore`, à rendre au domaine à côté de `resolve_current_analysis_id`). En lecture stricte sur la garde d'export, le score reste à 84, au-dessus du seuil GO.

Réserve : je n'ai rien exécuté. Les résultats de suites cités sont ceux du mainteneur. Je n'ai pas vérifié le SQL lui-même (triggers de `document_analysis_state`, comportement de `BEGIN IMMEDIATE` avec la connexion aiosqlite), le démarrage de FastAPI/MCP, ni le schéma OpenAPI des modèles de payload générés par `create_model`.
