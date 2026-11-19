# Rapport d'audit : Hexagonal Architecture (ports & adapters)

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Branche / commit** : `fix/0.7.4-editor-followups` @ `efc0bc5`

Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`docs/audit/reports/release-0.7.4-control/01-clean-architecture.md`, `a12b744`, 78/100, 0 CRIT / 3 MAJ / 1 MIN).

Code non exécuté : aucune suite n'a tourné sur ce commit.

Fiche : `docs/audit/audits/01-clean-architecture.md`, cible `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/`).
Méthode : lecture de l'arbre de travail, greps de la fiche, `git diff a12b744 efc0bc5 -- document-parser`, comparaison de `tests/test_architecture.py` avec `git show a12b744:…`. Cinq scripts d'analyse en lecture seule (AST, aucun import du code audité) :
- chaque appel de constructeur et de fabrique dans `bootstrap/`, `main.py`, `mcp_stdio.py`, `services/`, `api/`, `infra/`, `persistence/`, `mcp_adapter/` (et `tests/`) comparé au `__init__` ou à la signature visée ;
- chaque `from <module local> import X` vérifié contre les noms définis par le module cible ; chaque nom lu dans une fonction vérifié (local, englobant, module, builtin), avec un signal dédié pour un nom importé seulement sous `TYPE_CHECKING` mais lu à l'exécution ;
- graphe des imports runtime (hors `TYPE_CHECKING`) : cycles, sens des couches, imports de pairs dans `services/` ;
- chaque protocole de `domain/ports.py` comparé à ses implémentations (noms, paramètres, défauts, async) ;
- chaque appel `self._x.m(...)` d'un service dont l'attribut est typé sur un port ou un service : méthode existante, `await` présent si et seulement si la méthode est async ; idem pour chaque appel `service.m(...)` des routes typées `deps.*Dep`.

Même lecture que la base : un item n'est conforme que si toutes les occurrences listées ont disparu.

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
| 1.1.1 | `domain/` sans FastAPI, aiosqlite ni lib infra | 3 | Oui | Grep de la fiche vide (pydantic et starlette compris). Nouveaux modules `domain/document_tree.py`, `domain/heading_tree.py` : stdlib et `domain` seulement. |
| 1.1.2 | Modèles, VO et ports sans I/O | 3 | Oui | Aucun `open(`, `os`, client HTTP ou SQL. `ProjectedAnalysis.read_editor_model` (`domain/analysis_editing.py:106`) ne fait que `json.loads` d'une chaîne. `pathlib.Path` a disparu de `domain/ports.py`. |
| 1.1.3 | Toute interaction externe passe par un protocole | 3 | Oui | Nouveaux ports `DocumentFileStore` (`domain/ports.py:146`), `DocumentAnalysisStateRepository` (`:197`), `CurrentAnalysisReader` (`:213`) ; `ChunkRepository.replace_for_document` (`:293`). Le disque des documents ne passe plus que par `DocumentFileStore`. |
| 1.1.4 | Pas de Pydantic dans domain | 2 | Oui | Aucun import. `DocumentAnalysisState`, `NestStep`, `HeadingNesting` sont des dataclasses. |
| 1.2.1 | `services/` sans `fastapi`/`starlette` | 3 | Oui | Grep vide. |
| 1.2.2 | Services → dépôts, jamais de SQL | 3 | Oui | Aucun `SELECT`/`INSERT`/`execute(`/`aiosqlite` dans `services/` (les deux `get_connection_password` de `services/store_backend_resolver.py:130`, `:145` sont des méthodes de port). |
| 1.2.3 | Règles métier dans `domain/` | 2 | **Non** | Fortement réduit : hachage et séquence du flux d'édition, split/merge, règles d'édition sur valeurs simples et marche des titres sont dans le domaine. Restent la localisation de citation et la lecture budgétée dans les services, et la règle « seule une analyse terminée est courante / active » répétée dans cinq fichiers. Voir [MAJ]. |
| 1.2.4 | Dépendances injectées, pas de concrétions | 2 | Oui | Plus aucun accès disque dans `services/` (scanner AST `tests/test_architecture.py:237-302` et mon grep concordent), `DocumentFileLocator` supprimé, aucun import runtime de `infra`/`persistence`. La construction de `ChunkPushService`/`DocumentTreeService` par `ChunkService` est un couplage entre pairs du même anneau, pas une concrétion d'adaptateur : [INFO] n°1, avec le score alternatif. |
| 1.3.1 | Routes sans `persistence/` | 3 | Oui | Grep vide ; aucun import runtime `api → infra` non plus. |
| 1.3.2 | camelCase confiné à `api/schemas.py` | 1 | **Non** | Réduit côté API (arbre et modèle d'éditeur typés), inchangé ailleurs. Voir [MIN]. |
| 1.3.3 | Endpoints qui délèguent toute la logique | 2 | Oui | Le `json.loads` a quitté la route : `read_editor_model()` + `AnalysisEditorModelResponse.model_validate` (`api/analysis_edits.py:62`), simple mappage typé. La garde du drapeau d'export (`api/documents.py:130-136`) est acceptée comme exposition HTTP, justification ci-dessous. Score si on la refuse : 84. |
| 1.4.1 | Chaque adaptateur `infra/` implémente un port | 3 | Oui | `LocalDocumentFileStore` (`infra/document_file_store.py:18`) ↔ `DocumentFileStore` : six méthodes, signatures identiques. `PdfiumInspector` suit le renommage `read_page_sizes`/`count_pages` (`infra/pdf_inspector.py:27`, `:44`). `SqliteDocumentAnalysisRepository` ↔ `DocumentAnalysisStateRepository`, `SqliteChunkRepository.replace_for_document` ↔ port : identiques. Les deux middlewares ASGI ne sont pas des adaptateurs de port (même lecture que `infra/rate_limiter.py` en base) : [INFO] n°2. |
| 1.4.2 | Config issue de `infra/settings.py` | 2 | Oui | `MAX_IMPORT_SIZE_MB` et `API_ALLOWED_HOSTS` lus dans `infra/settings.py:230`, `:284` et validés (`:154`). Aucune nouvelle lecture d'environnement ailleurs. |

Calcul : poids conformes = 3+3+3+2 + 3+3 + 2 + 3 + 2 + 3+2 = **29 / 32**. Non conformes : 1.2.3 (2), 1.3.2 (1). `29 / 32 × 100 = 90,6`, soit **91**.

Scores alternatifs, pour lecture stricte :
- garde d'export refusée (1.3.3 non conforme) : 27/32 = **84** ;
- construction des services pairs comptée dans 1.2.4 : 27/32 = **84** ;
- les deux : 25/32 = **78**.

### Garde du drapeau d'export : acceptée

La justification écrite (`api/documents.py:130-134`) tient pour trois raisons vérifiées dans le code :
1. Le drapeau est un champ de `AppState` (`AppState(analysis_editor_enabled=…)`, `bootstrap/builder.py:96`), le conteneur de la couche HTTP. Toutes les routes de l'éditeur le lisent par `deps.ensure_analysis_editor_enabled`. Le passer à `ExportService` ferait connaître au service un interrupteur d'interface et ajouterait un argument booléen de contrôle.
2. L'effet est HTTP : un 404 qui cache une fonctionnalité désactivée. `ExportService` reste correct sans lui (`export_edited` lit le résultat édité par le port `ActiveAnalysisResultReader`).
3. Le placement dans le corps et non en dépendance est une vraie contrainte de FastAPI : une dépendance lèverait son 404 avant la validation de `format` (422).
Le reste de la route ne fait que choisir entre deux méthodes du service selon un paramètre de requête et mapper le résultat. Je l'accepte comme exposition HTTP. Ce que la base demandait (« acter que la garde relève de `deps` ») est fait dans le commentaire ; il reste à l'écrire dans la fiche si l'équipe veut que la règle survive à l'auditeur.

---

## Ecarts constates

### [MAJ] Règles métier hors domaine : deux familles restent

- **Localisation** :
  - Localisation d'une citation : `services/citation_service.py:201` (`_locate_quote`), `:230` (`_locate_across`, fenêtre glissante bornée), `:261` (`_trim_left`). Fonctions statiques pures sur `DocumentIndex`, sans aucune dépendance du service.
  - Lecture budgétée : `services/navigation_service.py:234` (`_pick` : prise en ordre de lecture, coupe au mot, curseur `ref@offset`). N'utilise de `self` que rien d'autre que ses arguments.
  - « Seule une analyse terminée est courante / sélectionnable » : `persistence/analysis_repo.py:185-186` (`ValueError` dans le dépôt), `services/version_service.py:165-172`, `services/analysis_edit_service.py:277`, `services/current_analysis.py:76`, `services/document_tree_service.py:62`. `DocumentAnalysisState.select` (`domain/models.py:136`) accepte n'importe quel identifiant.
- **Constat** : la remédiation `d3059c6` a sorti tout le reste de la liste de base, vérifié dans le code :
  - chaîne de hachage et séquence : `hash_command` `domain/analysis_editing.py:152`, `hash_command_stream` `:168`, `check_expected_sequence` `:215`, utilisés par le service (`services/analysis_edit_service.py:89`, `:155`, `:183`) et par le dépôt (`persistence/analysis_edit_repo.py:158`, `:166`) : plus de copie ;
  - split/merge : `ChunkService` appelle `chunk_editing.split`/`check_merge_count`/`merge` (`services/chunk_service.py:242`, `:264`, `:275`) ;
  - règles d'édition sur valeurs simples : `domain/analysis_editing.py:232-272`, appelées par l'adaptateur Docling ;
  - marche des titres : `domain/heading_tree.py:51`, partagée par `domain/parse_index.py:151`, `domain/outline_builder.py:96`, `:162`, `domain/document_tree.py:62` et `infra/docling_projector.py:199`.
  La racine protégée reste dans `infra/docling_editor.py:136`, `:163`, `:241`, `:294`, `:317`, mais c'est désormais une décision écrite (`domain/analysis_editing.py:224-225` : les règles qui exigent le document vivant restent dans l'adaptateur) et elle tient : tester « est-ce `document.body` » exige l'objet Docling. Je ne la compte plus.
  Ce qui reste n'est pas de la tuyauterie : ce sont des algorithmes qui décident ce qu'une citation prouve et ce qu'un agent lit, et un invariant d'agrégat dispersé dans un dépôt et quatre services.
- **Regle violee** : item 1.2.3 (poids 2).
- **Remediation** (effort S à M) :
  1. Déplacer `_locate_quote`/`_locate_across`/`_trim_left` dans un module `domain/citation_locate.py` (fonction `locate_quote(index, ref, element, claimed)`) et `_pick` dans `domain/navigation.py` (`pick_within_budget(index, refs, budget, start)`). Copier-coller sans changement de logique, le service appelle la fonction. C'est le moins cher.
  2. Un prédicat `AnalysisJob.can_be_current(document_id)` (ou `is_selectable`) dans `domain/models.py`, utilisé par les cinq sites ; `DocumentAnalysisState.select` peut prendre le job et le vérifier.
  Le point 1 seul ne fait pas passer l'item ; il faut les deux.

### [MIN] camelCase hors `api/schemas.py`

- **Localisation** : `api/analysis_edits.py:87-108` (payloads de commande `elementId`, `beforeElementId`…) ; `services/chunk_push_service.py:91-105`, `:159`, `:287-294`, `:343-346` (déplacés de `chunk_service`) ; `services/chunk_service.py:76`, `:92-95` ; `services/analysis_service.py:48-51` ; `services/version_service.py:51-56` ; `services/analysis_edit_service.py:195-196` ; `domain/analysis_editing.py:287` (`targetSequence`) ; `infra/docling_projector.py:56`, `:221-231`.
- **Constat** : progrès côté API, `_serialize_tree` a disparu au profit de `EditorTreeNodeResponse` (`api/analysis_edits.py:49-55`) et le modèle d'éditeur est typé (`api/schemas.py:228-264`, `extra="forbid"`). Le reste a été déplacé, pas converti. Les payloads de commande et le JSON de chunks sont des formats persistés (v1), ce qui explique une partie du camelCase hors schémas ; la base le savait déjà.
- **Regle violee** : item 1.3.2 (poids 1).
- **Remediation** : inchangée. Documenter le payload de commande v1 et `chunks_json` comme formats durables (et les exclure de l'item dans la fiche), puis faire produire des dataclasses aux services de chunks et mapper dans `api/schemas.py`. Effort S.

### [INFO] n°1 — Nouveau : `ChunkService` construit lui-même ses deux services pairs

- **Localisation** : `services/chunk_service.py:41-42` (imports runtime de `ChunkPushService` et `DocumentTreeService`), `:133-149` (construction dans `__init__`) ; contrôle des pairs limité à cinq modules (`tests/test_architecture.py:119-125`).
- **Constat** : le découpage `8a60cee` est sain (chaque sous-service reçoit des ports), mais la façade instancie ses collaborateurs au lieu de les recevoir. Aucun test ne peut substituer `ChunkPushService`, et le test d'architecture ne voit pas ces imports de pairs. Ce n'est pas une concrétion d'adaptateur (l'objet de 1.2.4 dans cette fiche), d'où l'INFO ; le sujet relève de 06 (DIP) et 07 (découplage). Si on le compte dans 1.2.4 : 84.
- **Remediation** : construire `ChunkPushService` et `DocumentTreeService` dans `bootstrap/factories.py:build_chunk_service` et les injecter (`push=`, `tree=`) ; étendre le contrôle des pairs à tout `services/` avec une liste blanche (`*_errors`, `*_config`, `errors`).

### [INFO] n°2 — Nouveau : deux middlewares HTTP de plus dans `infra/`

- **Localisation** : `infra/host_guard.py:90` (`ApiHostGuardMiddleware`, starlette `Headers`, `PlainTextResponse`), `infra/body_limit.py:20` (`BodySizeLimitMiddleware`, `JSONResponse`), câblés en `main.py:95-119` ; précédent `infra/rate_limiter.py`.
- **Constat** : ce sont des adaptateurs entrants (côté HTTP), pas des adaptateurs sortants derrière un port. Dans cet hexagone, la couche qui connaît HTTP est `api/`. Le sens des dépendances reste correct (personne n'importe ces modules hors `main.py`), et la base n'a pas compté `rate_limiter.py` dans 1.4.1 ; je garde la même lecture. Le placement est défendable (« tout ce qui n'est pas le métier »), mais il brouille la règle de 1.4.1 que la fiche pose.
- **Remediation** : déplacer les trois middlewares dans `api/middleware/` (les fonctions pures `is_allowed_host`/`split_host` peuvent rester où elles sont ou y aller aussi) ; ou acter dans la fiche que `infra/` héberge aussi les middlewares ASGI.

### [INFO] n°3 — Nouveau : `get_document` assemble deux lectures du service

- **Localisation** : `api/documents.py:97-105` (`find_with_store_links` puis `find_current_analysis_id`).
- **Constat** : deux appels indépendants mappés dans une réponse. Pas de logique, mais c'est le même genre de jointure que la base a fait sortir de la route pour les store-links.
- **Remediation** : un `DocumentService.find_details(doc_id)` qui rend le document, ses liens et l'id courant.

### [INFO] n°4 — Nouveau : l'export PDF ne résout pas le chemin, la preview si

- **Localisation** : `services/export_service.py:98-101` (`has_file(doc.storage_path)` puis `file_path=doc.storage_path`) ; `services/preview_service.py:89`, `:106` (`self._files.resolve(...)`).
- **Constat** : comportement antérieur (`Path(doc.storage_path).is_file()` en base), mais le port expose maintenant `resolve` pour le cas « chemin Docker lu sur l'hôte ». Dans ce cas la preview fonctionne et l'export PDF répond 404.
- **Remediation** : `path = self._file_store.resolve(doc.storage_path)` puis `has_file(path)` et `file_path=path`.

### [INFO] n°5 — Nouveau : appels disque bloquants restés sur la boucle d'événements

- **Localisation** : `services/preview_service.py:89`, `:106` (`resolve`), `services/document_service.py:176` (`delete`), `services/export_service.py:98` (`has_file`).
- **Constat** : le port le dit (« callers decide which calls leave the event loop », `domain/ports.py:149-150`) et les appels lourds (`save`, `read_fingerprint`, rendu, inspection) passent par `asyncio.to_thread`. Ceux-ci sont des `stat` : négligeables sur disque local, pas sur un volume réseau.
- **Remediation** : `asyncio.to_thread` aussi pour ces trois-là si les uploads vivent sur un volume distant.

### [INFO] Reportés de la base

- Résolus :
  - docstring périmée du test d'architecture : corrigée (`tests/test_architecture.py:112-116`) ;
  - erreurs d'adaptateur non traduites par la preview : `_translate_pdf_read_errors` (`services/preview_service.py:121-140`), la route n'a plus qu'un `except ServiceError` (`api/documents.py:169-172`, `:184-187`) ;
  - MCP sur la dernière parse brute : `ParseLoader` passe par `CurrentAnalysisReader` (`services/parse_loader.py:72-76`), `find_latest_parsed_ids` n'est plus qu'un repli du résolveur (`services/current_analysis.py:46`).
- Réduit : `AppState` garde trois dépôts que l'API ne lit plus (`api/state.py:61-66`) ; le commentaire est désormais vrai (« for the tests »), les champs restent.
- Inchangés (9) :
  1. `PdfiumInspector` compte les pages d'un upload avec poppler (`infra/pdf_inspector.py:52-62`) ;
  2. méthode de port inutilisée `DocumentVersionRepository.find_latest_for_document` (`domain/ports.py:355`) ;
  3. `VectorStore.get_chunks` : `limit: int = 1000` (`domain/ports.py:527`) contre `int | None = None` (`infra/opensearch_store.py:168`) ;
  4. `DocumentMerger` jamais câblé (`domain/ports.py:101`, `infra/docling_merger.py:12`) ;
  5. `persistence` importe `infra` (`persistence/store_repo.py:24`, seule entrée legacy du test, `tests/test_architecture.py:67`) ;
  6. le domaine lit le schéma JSON Docling (`domain/element_reader.py`) ;
  7. configuration hors `settings` : `persistence/database.py:22` (`DB_PATH`), `:342` (`DEFAULT_EMBEDDER`), `infra/preview_cache.py` ;
  8. contrôle service → service limité à cinq modules (`tests/test_architecture.py:119-125`), aggravé d'un cran par l'INFO n°1 ;
  9. frontend `shared` → `features` : `frontend/src/shared/ui/AppSidebar.vue:55-56` (hors barème).

---

## Delta vs contrôle

**Score : 78 → 91 (Δ +13).** 9/13 → 11/13 items conformes. Deux MAJ soldés (1.2.4, 1.3.3), un MAJ fortement réduit (1.2.3), le MIN réduit.

| Écart du contrôle (a12b744) | Statut à `efc0bc5` | Preuve |
|-----------------------------|--------------------|--------|
| [MAJ] 1.2.3 Règles métier hors domaine | **Réduit** | Résolus : hachage/séquence (`domain/analysis_editing.py:152`, `:168`, `:215` ; `persistence/analysis_edit_repo.py:158`, `:166`), split/merge (`services/chunk_service.py:242`, `:275`), racine protégée actée (`domain/analysis_editing.py:224`). Restent `services/citation_service.py:201`, `services/navigation_service.py:234`, l'invariant « analyse terminée » (`persistence/analysis_repo.py:185` et quatre services). |
| [MAJ] 1.2.4 Services couplés au disque, `DocumentFileLocator` | **Résolu** | `os`/`open`/`Path` absents de `services/` ; `infra/document_file_store.py:18` ; `services/document_service.py:104`, `:113`, `:176`, `:187` ; `services/preview_service.py:89-90` ; `services/export_service.py:98` ; garde-fou `tests/test_architecture.py:280`. `DocumentFileLocator`/`resolve_storage_path` : aucune occurrence. |
| [MAJ] 1.3.3 Routes qui travaillent (`json.loads`, garde d'export) | **Résolu** (garde acceptée) | `api/analysis_edits.py:62` (plus de `json.loads`, mappage typé) ; garde `api/documents.py:130-136` acceptée comme exposition HTTP. Lecture stricte : réduit, score 84. |
| [MIN] 1.3.2 camelCase hors schémas | **Réduit** | Arbre et modèle d'éditeur typés (`api/analysis_edits.py:49-62`, `api/schemas.py:233-284`) ; payloads et services de chunks inchangés. |
| [INFO] docstring du test, erreurs de preview, MCP sur la parse brute | **Résolus** | Voir « Reportés ». |
| [INFO] `AppState` orphelins | Réduit | Commentaire corrigé, champs présents. |
| [INFO] `PdfiumInspector`/poppler, port inutilisé, `get_chunks`, `DocumentMerger`, `persistence → infra`, schéma Docling, config, peers partiels, frontend | Inchangés | Voir « Reportés ». |

**Régressions de couche cherchées, aucune trouvée** :
- graphe des imports runtime : aucun `domain → hors domaine`, `services → infra/persistence/api/bootstrap/mcp_adapter`, `api → persistence/infra`, `infra → services/api/persistence` ;
- `tests/test_architecture.py` : diff contre `a12b744` uniquement additif (règle « services sans système de fichiers » et son test de détection, `:231-302`), aucune liste élargie, `_LEGACY_LAYER_IMPORTS` identique ;
- aucun port revenu à une concrétion : tous les paramètres des nouveaux services sont typés sur des ports (`services/current_analysis.py:28-29`, `services/chunk_push_service.py:44-50`, `services/document_tree_service.py:36-41`) ; `infra` ne connaît aucun service ;
- `CurrentAnalysisResolver` implémente un port dans `services/` : c'est le même patron que `AnalysisEditService` pour `ActiveAnalysisResultReader` (orchestration de dépôts, aucune I/O), pas la dérive de `DocumentFileLocator` ;
- nouveaux cas non comptés : [INFO] n°1 (pairs construits par `ChunkService`) et n°2 (middlewares HTTP dans `infra/`).

---

## Relecture avant première exécution

Périmètre : fichiers backend touchés par `ac7ac17`, `d3059c6`, `4939413`, `8a60cee`, `efc0bc5` dans ma zone (`domain/`, `services/`, `infra/`, `persistence/`, `api/`, `bootstrap/`, `main.py`, `mcp_stdio.py`, `mcp_adapter/sources_*`).

**Aucun défaut d'import ou d'exécution trouvé à la lecture.** Ce que j'ai vérifié, et comment :

| Contrôle | Résultat |
|----------|----------|
| Constructions dans `bootstrap/builder.py`, `bootstrap/factories.py`, `mcp_stdio.py`, `main.py` contre chaque `__init__` (script AST) | Toutes conformes : `AnalysisEditService` (`builder.py:135-144`), `VersionService` (`:158-164`), `PreviewService` (`:191-197`), `ExportService` (`:200-206`), `StoreService`, `CurrentAnalysisResolver` (`:125-128`, `mcp_stdio.py:68-71`), `DocumentService` (`factories.py:230-242`), `ParseLoader` (`:275-281`), `LocalDocumentFileStore` (`:224`), `ReasoningService`, `AppConfigService`. `build_chunk_service(**repos)` vérifié à la main : les onze clés de `builder.py:145-157` sont des paramètres de `ChunkService.__init__` (`services/chunk_service.py:107-122`). Constructions internes `ChunkPushService`/`DocumentTreeService` (`services/chunk_service.py:133-149`) conformes. Les tests construisent aussi les classes avec les bons arguments (hors `**kwargs`). |
| Noms importés depuis un module local | Tous définis (seul signal : `PreviewImageKey`, alias `type` PEP 695 en `domain/ports.py:186`, faux positif de mon script ; il existait déjà en base). |
| Noms lus dans les fonctions, noms `TYPE_CHECKING` lus à l'exécution | Aucun nom indéfini ; aucun nom `TYPE_CHECKING` utilisé hors annotation. Cas sensibles vérifiés à la main : `DocumentAnalysisState` importé au runtime là où il est construit (`persistence/analysis_repo.py`, `services/chunk_service.py:28`, `services/version_service.py`) ; `deque[Message]` dans `infra/body_limit.py:44` est une annotation de variable locale, jamais évaluée ; `TypeAdapter(SourcesCard)` (`mcp_adapter/sources_view.py:31`) : tous les champs de `SourcesCard` sont des builtins ou des classes du même module (`mcp_adapter/sources_card.py:24-134`), donc résolubles. |
| Méthodes de port appelées / définies par l'adaptateur | Aucun écart nouveau. Renommages `page_sizes → read_page_sizes`, `page_count → count_pages` propagés partout (`infra/pdf_inspector.py:27`, `:44` ; `services/preview_service.py:107` ; `services/analysis_service.py:456` ; `api/documents.py:185`). Méthodes supprimées (`find_latest_completed*`, `get_selection`, `get_chunk_source`, `LLMProvider.type`, `DocumentFileLocator`) : aucun appelant restant. Nouvelles (`find_parsed_ids`, `find_summaries_by_document`, `replace_for_document`, `find_state(s)`, `save_state`) : définies avec la même signature (`persistence/analysis_repo.py:83`, `:151` ; `persistence/chunk_repo.py:139` ; `persistence/document_analysis_repo.py:81`, `:90`, `:101`). Seul écart : `VectorStore.get_chunks`, antérieur. |
| `await` manquant ou en trop | 225 appels par attribut typé vérifiés : aucun. Les deux signaux (`self._converter.convert` sans `await` direct, `services/analysis_service.py:334`, `:481`) sont passés à `asyncio.wait_for` : correct. Méthodes de port synchrones (`DocumentFileStore`, `PdfInspector`, `PageRasterizer`) appelées sans `await` ou via `asyncio.to_thread`. Appels duck-typés vérifiés : `record_on_rechunk(document_id, analysis_id, source_result_hash)` (`services/chunk_service.py:363` ↔ `services/version_service.py:126`), `load_active_result` (`services/document_tree_service.py:66` ↔ `services/analysis_edit_service.py:100`). |
| Routes → méthodes de service | Toutes les méthodes appelées par `api/*.py` via `deps.*Dep` existent sur la classe (dont les délégations de `ChunkService` vers ses sous-services) ; aucun `await` incohérent. |
| Imports circulaires | Aucun nouveau. Deux cycles connus et sans effet : `bootstrap ↔ bootstrap.builder` (le paquet importe `builder` en premier, qui importe `bootstrap.factories` alors que `bootstrap` est déjà dans `sys.modules`) et `infra.neo4j` (antérieur). `persistence.chunk_repo`/`analysis_repo → persistence.document_analysis_repo` : sans retour. |
| Contrat du modèle d'éditeur | `AnalysisEditorModelResponse`/`EditorElementResponse` (`extra="forbid"`, `api/schemas.py:228-264`) contre le dict produit par `infra/docling_projector.py:55-57`, `:221-231` : mêmes douze clés (alias camelCase, `populate_by_name=True`), `supported_operations` limité aux valeurs de `CommandType` (`infra/docling_projector.py:143-153` ⊂ `domain/analysis_editing.py:18-26`). Le cache relit le modèle via `project_serialized`, qui le recalcule : pas de vieux JSON validé tel quel. |
| Middlewares | Ordre conforme au commentaire (`main.py:92-119` : `add_middleware` empile, le dernier ajouté est le plus externe : Host → rate limit → CORS → limite d'import). `logger` défini avant usage (`main.py:49`, `:119`). Réglages présents et validés (`infra/settings.py:31`, `:111`, `:154`). |
| Version de Python | `def nest_by_heading[T]` (`domain/heading_tree.py:51`) exige 3.12 : `requires-python >= 3.12`, images `python:3.12-slim`, `.venv` en 3.12.2. |

Points de comportement (pas des plantages) relevés en lisant, déjà en INFO : export PDF sans `resolve` (n°4), `stat` sur la boucle (n°5).

**Ce que la lecture ne couvre pas** : les noms lus au niveau module ou dans un corps de classe (décorateurs, valeurs par défaut), les appels dont le receveur n'est pas typé (paramètres sans annotation de `bootstrap/builder.py:242`, `:285`), le comportement de pydantic/FastAPI/MCP au démarrage (génération du schéma OpenAPI des nouveaux modèles, enregistrement des outils), le SQL lui-même (colonnes de `document_analysis_state`, migrations) et tout ce qui dépend de Docling, pdfium ou poppler. Seule une exécution de la suite et un démarrage de l'application le diront.

---

## Points positifs

- **Le disque est derrière un port, et un test le garde** : `DocumentFileStore` à six méthodes étroites, un adaptateur (`infra/document_file_store.py`), et un scanner AST qui refuse `os`, `shutil`, `glob`, `tempfile`, `pathlib.Path` et `open()` dans tout `services/`, avec son propre test de détection pour ne pas passer au vert à vide (`tests/test_architecture.py:285-302`).
- **Une seule règle pour « l'analyse courante »** : `resolve_current_analysis_id` dans le domaine (`domain/models.py:193`), un port de lecture, un résolveur ; route, export, éditeur, arbre, Ask et MCP (y compris `mcp_stdio.py`) lisent la même.
- **Un agrégat `DocumentAnalysisState` avec écriture des seules parties modifiées** et une fonction d'écriture partagée qui rejoint la transaction de l'appelant (`persistence/document_analysis_repo.py:50`) : la restauration de version et la régénération des chunks sont atomiques (`persistence/chunk_repo.py:139-166`).
- **Le flux d'édition n'a plus qu'une définition** du hachage et de la séquence, utilisée par le service et par le dépôt.
- **Une marche des titres pour cinq consommateurs** (`domain/heading_tree.py`), dont le projecteur Docling qui avait sa propre pile.
- **Routes de preview réduites au mappage** : la traduction des erreurs d'adaptateur est dans le service, avec des messages qui ne fuient pas le chemin serveur (`services/preview_service.py:116-117`).

---

## Verdict partiel : GO

91/100, 0 CRITICAL, 1 MAJOR, 1 MINOR. Même en lecture stricte (garde d'export refusée, ou pairs comptés dans 1.2.4), le score reste à 84, au-dessus du seuil GO. Le MAJ restant ne bloque pas ; sa correction la moins chère est un déplacement sans changement de logique (`_locate_quote`, `_pick` vers `domain/`) plus un prédicat d'agrégat pour « analyse terminée ».

Réserve : ce verdict porte sur l'architecture lue, pas sur un code qui a tourné. Aucun défaut d'import ou d'exécution n'apparaît à la lecture, mais la suite complète et un démarrage restent à faire avant de s'y fier.
