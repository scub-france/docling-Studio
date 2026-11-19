# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `efc0bc5`, arbre de travail (`experiments/mcp-bench/` non suivi, hors périmètre)
**Nature** : Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`a12b744`, score 75)

Code non exécuté : aucune suite n'a tourné sur ce commit

Périmètre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/` pour les constats) et `frontend/src/`.
Delta examiné : `git log a12b744..efc0bc5` (22 commits, dont les 15 de `b5f8c7f..efc0bc5`).
Méthode : lecture de l'arbre de travail, `rg`, `git diff` / `git show` en lecture seule, recherche
d'appelants pour chaque structure ajoutée. Aucun outil du projet lancé. Les messages de commit de
la seconde remédiation disent tous « Not run ».

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 8 |
| Score | 67 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 5 |
| Ecarts INFO | 14 |

Poids total : 12. Poids conformes : 8 (4.1, 4.4, 4.6, 4.7, 4.8). Non conformes : 4.2 (2), 4.3 (1), 4.5 (1).
`score = 8 / 12 × 100 = 66,7` → **67**. Contrôle : 75.

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Grep fiche : `AppStateBuilder` seul (`bootstrap/builder.py:80`). Le suivi des parties modifiées de `DocumentAnalysisState` est plus lourd que nécessaire mais reste deux booléens (INFO) |
| 4.2 | Résout le problème actuel, pas hypothétique | 2 | **Non** | Le MAJ LLM est résolu. L'item reste non conforme selon la lecture du contrôle : plomberie de l'éditeur, carte de citation et cache du repli d'aperçu sont inchangés ; la passe ajoute du code mort maintenu |
| 4.3 | Pas de wrapper sans valeur ajoutée | 1 | **Non** | Six relais purs ajoutés : 4 dans `ChunkService` (`services/chunk_service.py:378-397`), `DocumentService.find_current_analysis_id` (`services/document_service.py:162-164`), `ParseLoader.find_current_parse_ids` (`services/parse_loader.py:72-76`) |
| 4.4 | Outils standard avant solutions maison | 1 | Oui (limite) | `infra/host_guard.py` réécrit un contrôle de `Host` que Starlette fournit (`TrustedHostMiddleware`) ; la portée `/api` seule et l'alignement sur `/mcp` en donnent une raison. INFO |
| 4.5 | Configuration simple | 1 | **Non** | Config MCP en couches inchangée ; deux réglages ajoutés, dont une grammaire `name:port` / `name:*` / `*` pour `API_ALLOWED_HOSTS` et `MAX_IMPORT_SIZE_MB` qui double la limite nginx |
| 4.6 | Pas d'indirection inutile | 2 | Oui | Route `/preview` réduite à une branche `ServiceError` (`api/documents.py:160-177`). Le saut `ChunkService` → `ChunkPushService` est compté en 4.3 |
| 4.7 | Pas de méta-programmation / magie | 2 | Oui | Grep fiche : rien hors `setattr` trivial (`main.py:55`) |
| 4.8 | Structures de données les plus simples | 1 | Oui (limite) | `AnalysisDetailPage` télécharge toujours 200 résumés pour en trouver un (`pages/AnalysisDetailPage.vue:123`) ; même lecture qu'au contrôle |

### Métriques de périmètre

| Mesure | a12b744 | efc0bc5 |
|--------|---------|---------|
| Fichiers `.py` de production | 135 | 146 (+11) |
| Lignes Python de production (`git diff --shortstat`, hors `tests/`) | — | +3 023 / −1 778 (net +1 245) |
| Lignes de tests backend | — | +2 438 / −332 |
| Lignes front de production (hors `*.test.ts`) | — | +957 / −543 (net +414) |
| `Protocol` dans `domain/ports.py` | 32 | 32 (3 retirés, 3 ajoutés) ; 766 → 826 lignes |
| Variables d'env lues par `infra/settings.py` | 44 | 46 |
| Méthodes de port sans appelant de production | 5 (préexistantes) | 7 (+ `ChunkRepository.soft_delete_for_document`, `DocumentAnalysisStateRepository.save_state`) |
| Relais purs ajoutés | — | 6 |
| Composants front sans importeur | — | 7 fichiers, 1 721 lignes (+ 468 l. de test) |

---

## Ecarts constatés

### [MAJ] Plomberie de l'éditeur pour des besoins non exprimés — porte désormais l'item 4.2

- **Localisation** : `document-parser/persistence/database.py:258` (`edited_analysis_cache`), `document-parser/services/analysis_edit_service.py:209` (`rebuild`), `:232` (`engine_version` écrit, jamais comparé), `:284` (`_project_cache`) ; `document-parser/api/analysis_edits.py:200` (route `rebuild`) ; `document-parser/api/schemas.py:290-291` (`warnings`, `reference_changes`) ; `frontend/src/features/analysis-editor/api.ts:71` (`rebuildAnalysisEdits`, aucun appelant hors test) ; `frontend/src/features/analysis-editor/types.ts:15` (`beforeElementId`), `:55-56` (`warnings`, `referenceChanges`, lus nulle part)
- **Constat** : le MAJ du contrôle (abstraction LLM-provider) est résolu (voir Delta). Le contrôle avait posé que 4.2 ne repasse conforme qu'en traitant ensemble ce MAJ, la plomberie de l'éditeur, la carte de citation et le cache du repli d'aperçu. Les trois derniers sont inchangés. Un item de poids 2 non conforme est un écart MAJ : il est porté par le plus lourd des résidus, la plomberie de l'éditeur (une table, une route, une méthode de service, un client, quatre champs que personne ne lit). `efc0bc5` a même typé `warnings` et `reference_changes` dans les nouveaux schémas au lieu de les retirer.
- **Règle violée** : item 4.2 (poids 2).
- **Remédiation** : retirer la route et le client `rebuild`, `warnings`/`referenceChanges`, `beforeElementId` ; documenter ou retirer `engine_version`. Effort M. Avec la carte de citation et le cache d'aperçu, 4.2 repasse conforme.

---

### [MIN] Six relais purs ajoutés par la remédiation (nouveau)

- **Localisation** : `document-parser/services/chunk_service.py:378-397` (`diff_against_store`, `push_to_store`, `list_pushes`, `get_tree`, docstring « See … ») et `:107-149` (constructeur à 13 paramètres dont 5 ne servent qu'à construire `ChunkPushService`, `:133-148`) ; `document-parser/services/document_service.py:162-164` ; `document-parser/services/parse_loader.py:72-76`
- **Constat** : `8a60cee` découpe `chunk_service.py` (905 → 426 lignes) mais garde `ChunkService` comme façade : il construit lui-même ses deux collaborateurs et leur transmet quatre appels sans rien ajouter, pour ne pas toucher aux routes ni au câblage. Le chemin `push` passe désormais par route → `ChunkService` → `ChunkPushService` → dépôts. `4939413` ajoute deux autres relais du même type vers `CurrentAnalysisResolver`.
- **Règle violée** : item 4.3 (poids 1).
- **Remédiation** : construire `ChunkPushService` et `DocumentTreeService` dans `bootstrap/builder.py`, les exposer par `deps`, faire appeler les quatre routes de `api/document_chunks.py:173-234` directement ; le constructeur de `ChunkService` perd 5 paramètres. Injecter le résolveur là où `api/documents.py:104` et `NavigationService` en ont besoin. Effort S.

### [MIN] Configuration : couches MCP inchangées, deux réglages de plus (reconduit, aggravé)

- **Localisation** : `document-parser/infra/settings.py:90-122`, `:259-300`, `document-parser/domain/mcp_config.py:44`, `:107-113` (inchangés) ; nouveau : `document-parser/infra/settings.py:111` et `:284` (`API_ALLOWED_HOSTS`), `document-parser/infra/host_guard.py:38-87` ; `document-parser/infra/settings.py:31`, `:154`, `:230` (`MAX_IMPORT_SIZE_MB`), `document-parser/main.py:92-101` ; `Dockerfile:61` et `nginx.conf.template:42` (`NGINX_MAX_BODY_SIZE=200M`)
- **Constat** : la config MCP garde trois représentations pour quatre réglages. La passe ajoute :
  - `API_ALLOWED_HOSTS` avec trois formes de motif (`name:port`, `name:*`, `*`) et une exception (`name:*` accepte aussi `name` sans port). Contre le rebinding DNS seul le nom compte. `*` équivaut à la variable vide (deux façons d'éteindre). Le réglage local recommandé (`docs/configuration.md:139`) liste les trois noms de loopback, déjà toujours acceptés (`host_guard.py:60`) : on les écrit seulement pour allumer le contrôle.
  - `MAX_IMPORT_SIZE_MB=200` alors que l'image publiée passe tout `/api` par nginx limité à `200M` et que uvicorn n'écoute que sur `127.0.0.1` (`Dockerfile:65`). Le middleware sert hors nginx (dev) ; le réglage ne sert à rien de plus qu'une constante.
- **Règle violée** : item 4.5 (poids 1).
- **Remédiation** : MCP comme au contrôle (une seule source des bornes, `_env_bool`). `API_ALLOWED_HOSTS` = liste de noms, sans port ni `*`. `MAX_IMPORT_SIZE_MB` → constante de 200 Mo dans `main.py`.

### [MIN] Code mort laissé en place, en partie remanié (nouveau)

- **Localisation** :
  - front, aucun importeur (`rg` sur `frontend/src`, `e2e/`, routes, barrels ; pas d'`import.meta.glob` ni de `defineAsyncComponent`) : `frontend/src/pages/DocChunkTab.vue` (241 l.), `frontend/src/pages/IngestLaunchDialog.vue` (399 l.), `frontend/src/pages/DocIngestTab.logic.ts` (192 l. + test de 468 l.), `frontend/src/features/analysis/ui/AnalysisPanel.vue` (185 l., exporté par `features/analysis/index.ts:6` sans importeur), `frontend/src/features/document/ui/PagePreview.vue` (114 l., seul importeur `AnalysisPanel`), `frontend/src/features/analysis/ui/InspectResultTabs.vue` (125 l.), `frontend/src/features/analysis/ui/StructureViewer.vue` (465 l., seul importeur `InspectResultTabs`) ;
  - back : `document-parser/api/state.py:61-66` (`analysis_repo`, `store_repo`, `document_store_link_repo` : aucune lecture ; le commentaire « they stay for the tests » est faux, seul un fixture autouse les remplit, `tests/test_api_endpoints.py:58-66`) ; `document-parser/domain/ports.py:291` + `persistence/chunk_repo.py:126` (`soft_delete_for_document`, sans appelant depuis `replace_for_document`) ; `document-parser/domain/ports.py:208` (`save_state`, appelé par les tests seulement) ; `document-parser/domain/models.py:90-93` et `:122-126` (`DocumentAnalysisSelection` et la propriété `selection`, tests seulement) ; `document-parser/domain/chunk_editing.py:48-116` (`insert`, `update`, `delete`, tests seulement, le service a ses propres versions).
- **Constat** : `453a1b9` a remanié `StructureViewer.vue` (+29 lignes, lecteur de jetons) alors que plus rien ne l'affiche. `d3059c6` a réécrit `chunk_editing.py` en gardant trois fonctions que seul le test appelle. `4939413` a laissé `soft_delete_for_document` orphelin et ajouté `save_state` et `selection` pour les seuls tests.
- **Règle violée** : item 4.2 (déjà compté).
- **Remédiation** : supprimer ces fichiers, slots, méthodes et le fixture. Environ 1 900 lignes front et 120 lignes back de moins. Effort S.

### [MIN] Repli serveur des aperçus équipé comme un chemin principal (reconduit, inchangé)

- **Localisation** : `document-parser/infra/preview_cache.py:16`, `:20` (LRU 64 Mo, `Lock`)
- **Constat** : fichier hors diff. Le `Lock` protège toujours des appels faits depuis la boucle d'événements seulement.
- **Règle violée** : item 4.2 (déjà compté).
- **Remédiation** : inchangée.

### [MIN] Carte de citation désactivée par défaut et maintenue (reconduit, inchangé)

- **Localisation** : `document-parser/infra/settings.py` (`MCP_CITATION_CARD=false`), `document-parser/mcp_adapter/citation_app.html` (1 256 l., hors diff), `document-parser/mcp_adapter/apps.py:124`
- **Règle violée** : item 4.2 (déjà compté).
- **Remédiation** : inchangée (retirer ou activer).

---

### [INFO] Reste de l'abstraction LLM après résolution du MAJ

- **Localisation** : `document-parser/domain/ports.py:613-635` (`LLMProvider`, une implémentation `infra/llm/ollama_provider.py`, un consommateur `infra/docling_agent_reasoning.py:134`, tous deux dans `infra/`) ; `:631` (`health_check`, aucun appelant) ; `document-parser/bootstrap/factories.py:103-110` ; `document-parser/infra/settings.py:54-58`, `:245` ; `document-parser/domain/app_config.py:63`, `document-parser/services/app_config_service.py:73`, `:81`, `:186`, `document-parser/api/schemas.py:940`, `:955`, `frontend/src/features/admin-config/types.ts:19`, `frontend/src/features/admin-config/ui/ReasoningConfigSection.vue:153`
- **Constat** : l'enum, la propriété `type` et le garde du runner ont disparu ; un seul contrôle reste dans la fabrique. C'est la forme minimale proposée au contrôle. Restent : un port qu'aucune règle de couche n'exige (adaptateur → adaptateur), une méthode `health_check` jamais appelée, et une valeur dépréciée qui traverse six couches pour un affichage en lecture seule.
- **Remédiation** : retirer `health_check` du port ; au retrait de la variable, retirer `provider_type` de la vue, du schéma et du panneau.

### [INFO] `DocumentAnalysisState` : suivi des parties modifiées là où deux écritures explicites suffiraient

- **Localisation** : `document-parser/domain/models.py:103-190` (deux drapeaux `:119-120`, `mark_saved` `:187`), `document-parser/persistence/document_analysis_repo.py:50-75` (écrivain à quatre branches), appelants `persistence/analysis_repo.py:186-195`, `persistence/chunk_repo.py:145-166`, `services/version_service.py:182-183`, `services/chunk_service.py:346-347`
- **Constat** : le problème est réel (une regénération de chunks ne doit pas écraser une sélection faite entre-temps). Mais les trois écrivains savent chacun ce qu'ils changent : `complete_and_select` construit un état vide pour lever un drapeau, la regénération ne touche que la source, la restauration les deux. Le mécanisme ajoute deux drapeaux, un `mark_saved` à ne pas oublier après chaque commit, et une méthode de port (`save_state`) sans appelant.
- **Remédiation** : deux fonctions d'écriture (`write_selection`, `write_chunk_source`) appelées par la transaction concernée ; l'agrégat garde ses méthodes et sa règle `are_chunks_stale`, sans drapeaux.

### [INFO] Deux noms pour « l'analyse courante » et un repli `None` répété trois fois

- **Localisation** : `document-parser/services/current_analysis.py:70` (`load_current_analysis`, résultat d'origine) ; `document-parser/domain/ports.py:426-437` (`load_active_result`, résultat édité) ; repli identique dans `services/document_tree_service.py:64-70`, `services/chunk_service.py:309-318`, `services/export_service.py:125-133`
- **Constat** : les deux lectures sont légitimes (avec ou sans éditions), mais « current » et « active » désignent la même analyse. Chaque service teste `active_result_service is not None` alors que `bootstrap/builder.py:156` et `:202-203` l'injectent toujours : la branche `else` n'est jamais prise en production.
- **Remédiation** : rendre `active_result_service` obligatoire et supprimer les trois branches `else` ; à terme une seule lecture `load_current(document_id, with_edits=...)`.

### [INFO] Sept modèles de payload de réponse qui recopient six modèles de requête

- **Localisation** : `document-parser/api/schemas.py:313-372` (7 classes + union), à comparer à `:169-205` (6 classes de requête aux mêmes champs) ; `:380`
- **Constat** : `efc0bc5` remplace `payload: dict` par une union non discriminée de 7 modèles en `extra="forbid"`. Les champs recopient ceux des requêtes ; la sélection du bon membre repose sur le refus des clés inconnues. Les modèles typés de l'arbre et du modèle éditeur (`:228-286`) sont, eux, justifiés : ils remplacent un `dict` par un contrat que le front attend.
- **Remédiation** : réutiliser les classes de requête (une base sans `type`, ou `command_type` comme discriminant au niveau de l'entrée), ou garder `dict` pour le payload.

### [INFO] Contrôle `Host` écrit à la main (4.4 à la limite)

- **Localisation** : `document-parser/infra/host_guard.py` (113 l. : analyse IPv6 `:38-51`, trois formes de motif `:62-67`, fonction de log `:77-87`), `document-parser/main.py:115-119`
- **Constat** : Starlette, déjà utilisé, fournit `TrustedHostMiddleware`. Il s'applique à toute l'application et répond 400 ; le choix d'un middleware `/api` seul, en 421 comme `/mcp`, se défend, mais aucune trace ne montre que l'outil standard ait été évalué.
- **Remédiation** : un contrôle par nom seul (une vingtaine de lignes), ou `TrustedHostMiddleware` si la double vérification de `/mcp` est acceptée.

### [INFO] Deux composants pour rendre une page d'aperçu

- **Localisation** : `frontend/src/features/document/ui/PageRaster.vue` (nouveau, `18cdf1b`) et `frontend/src/features/document/ui/PdfPagePreview.vue` (utilisé par `pages/StudioPage.vue:258`)
- **Constat** : le commit s'intitule « render a preview page through one component » et dit lui-même ne pas avoir réutilisé `PdfPagePreview`. Les deux font canvas PDF.js puis PNG de repli.
- **Remédiation** : faire reposer `PdfPagePreview` sur `PageRaster`.

### [INFO] Commentaires qui grossissent pour justifier la structure

- **Localisation** : `document-parser/api/state.py:61-63` (justification fausse), `document-parser/services/chunk_service.py:378-397` (« See … » sur chaque relais), `document-parser/main.py:92-94`, `:115-116` (ordre des middlewares), `document-parser/api/documents.py:130-135` (six lignes pour placer un garde), `document-parser/infra/host_guard.py:1-15`
- **Constat** : plusieurs commentaires expliquent pourquoi une structure existe plutôt que ce que fait le code ; un est faux.
- **Remédiation** : supprimer avec les structures concernées ; corriger `api/state.py`.

### [INFO] Résidus reconduits, inchangés

- `PdfInspector` construit par deux chemins (`bootstrap/builder.py:195`, `bootstrap/factories.py:318-321`) et `pdf_inspector: PdfInspector | None` pour les tests (`services/analysis_service.py:95`).
- `--warning-muted` figé en RGB (`frontend/src/app/App.vue:99`, 3 usages) à côté de `color-mix(… var(--warning) 10% …)` (2 usages, dont le nouveau `EditorBanners.vue:85`).
- Alias de `frontend/src/features/history/api.ts:2-5`.
- `AnalysisDetailPage` (4.8) : 200 résumés pour en trouver un, `JSON.stringify` des pages, requêtes en séquence (`pages/AnalysisDetailPage.vue:107-152`). `efc0bc5` ajoute un filtre `documentId` mais la page ne s'en sert pas ; `DocsLibraryPage.vue` télécharge la liste des résumés d'un document pour en lire `.length`.
- Event-sourcing avec chaîne de hash, introspection d'une API privée Docling, allers-retours JSON du projecteur, pont MCP Apps en deux copies, `_neutralise_all` en double (`mcp_adapter/wire.py:72`, `wire_mapping.py:42`), port moteur `project_serialized`.
- Méthodes de port préexistantes sans appelant : `StoreRepository.get_default` (`domain/ports.py:246`), `DocumentVersionRepository.find_latest_for_document` (`:355`), `get_chunks` (`:527`) ; fonctions `domain/hashing.py:43` (`hash_chunkset`) et `domain/lifecycle_aggregation.py:35` (`aggregate_lifecycle`) sans appelant de production.

### [INFO] CI : liste de tests codée en dur

- **Localisation** : `.github/workflows/ci.yml` (job `backend-docling`, 4 chemins de tests listés)
- **Constat** : hors périmètre de la fiche. La passe retire un job mort (`audit-checks`, script absent du dépôt), ce qui simplifie. Le nouveau job liste ses fichiers à la main : un test Docling ajouté ailleurs sera ignoré.
- **Remédiation** : un marqueur pytest (`-m docling`).

---

## Delta vs contrôle

Score : **75 → 67 (−8)**. Items conformes : 6/8 → 5/8. 4.3 bascule en non conforme (relais ajoutés).
4.2 reste non conforme mais change de porteur. 4.5 reste non conforme et s'alourdit. 4.4 et 4.8 restent à la limite.

| Écart du contrôle (a12b744) | Statut à efc0bc5 | Détail |
|-----------------------------|------------------|--------|
| [MAJ] Abstraction LLM-provider (4.2) | **Résolu** (résidu INFO) | Enum, propriété `type` et garde du runner retirés ; un seul contrôle (`bootstrap/factories.py:103`) ; variable dépréciée ; `health_check` sans appelant et `providerType` en lecture seule restent |
| [MIN] Repli d'aperçu équipé comme principal (4.2) | Inchangé | |
| [MIN] Plomberie de l'éditeur (4.2) | **Inchangé, promu MAJ** | Porte l'item 4.2 une fois le MAJ LLM résolu ; `warnings`/`reference_changes` typés au lieu d'être retirés |
| [MIN] Configuration MCP en couches (4.5) | **Aggravé** | +`API_ALLOWED_HOSTS` (grammaire à trois formes), +`MAX_IMPORT_SIZE_MB` |
| [MIN] Carte de citation désactivée (4.2) | Inchangé | |
| [INFO] Ports non imposés `DocumentFileLocator`, `ActiveAnalysisResultReader` | **Partiellement résolu** | `DocumentFileLocator` remplacé par `DocumentFileStore` (imposé par une règle) ; `ActiveAnalysisResultReader` reste, avec trois replis `None` |
| [INFO] Câblage `PdfInspector`, `None` pour les tests | Inchangé | |
| [INFO] Échelle d'exceptions de `/preview` | **Résolu** | Une branche `ServiceError` (`api/documents.py:169-172`) |
| [INFO] Teinte warning en deux mécanismes | Inchangé (3 contre 2) | |
| [INFO] Alias `history/api.ts` | Inchangé | |
| [INFO] Ouverture d'analyse en deux temps (4.8) | Inchangé | |
| [INFO] Replis jamais pris | Inchangé | |
| [INFO] Autres reconduits | Inchangés | |

Nouveaux écarts : 2 MIN (relais purs, code mort), 6 INFO (`DocumentAnalysisState`, deux noms et
replis, payloads recopiés, contrôle `Host` maison, deux composants d'aperçu, commentaires) et un
INFO CI.

---

## La seconde remédiation a-t-elle simplifié ?

En partie. Elle supprime de vraies duplications (marche des titres écrite quatre fois, hash
calculé deux fois, règle de l'analyse courante divergente selon le lecteur, écritures d'état en
trois ou quatre commits) et retire l'abstraction LLM. Mais elle grossit plus qu'elle ne
simplifie : +1 245 lignes Python et +414 lignes front de production nettes, 11 fichiers Python de
plus, six relais purs, un mécanisme de suivi de modifications, sept modèles recopiés, deux
réglages. Elle a aussi remanié du code que rien n'affiche au lieu de le supprimer.

| Structure | Commit | Verdict | Raison | Forme minimale |
|-----------|--------|---------|--------|----------------|
| Retrait de `LLMProviderType`, de `type` et du garde du runner | `efc0bc5` | **Plus simple** | Un contrôle au lieu de trois, plus d'enum à un membre | Retirer aussi `health_check` du port et, avec la variable, `providerType` de l'API et du panneau |
| `infra/host_guard.py` + `API_ALLOWED_HOSTS` | `efc0bc5` | **Plus complexe que nécessaire** | Le besoin (rebinding DNS) est réel ; la grammaire `name:port` / `name:*` / `*`, l'analyse IPv6 et la fonction de log ne le servent pas | Liste de noms, contrôle par nom seul, ~20 lignes, ou `TrustedHostMiddleware` |
| `infra/body_limit.py` + `MAX_IMPORT_SIZE_MB` | `efc0bc5` | **Légèrement plus complexe** | Le middleware est la bonne place (le corps est lu avant la route) ; le réglage double les `200M` de nginx de l'image | Garder le middleware, constante de 200 Mo |
| Bornes des requêtes de l'éditeur | `efc0bc5` | Neutre | Cinq constantes `Field(max_length=…)`, rien de plus | — |
| Modèles typés du modèle et de l'arbre éditeur | `efc0bc5` | Neutre | Remplacent `dict` par le contrat que le front lit | — |
| Sept modèles de payload de réponse | `efc0bc5` | **Plus complexe que nécessaire** | Recopient les six modèles de requête ; union non discriminée | Réutiliser les modèles de requête ou garder `dict` |
| Port `DocumentFileStore` (6 méthodes) + règle d'architecture | `ac7ac17` | Neutre | Imposé par la règle ajoutée dans le même commit ; les 6 méthodes ont un appelant ; remplace `DocumentFileLocator` | — |
| `domain/heading_tree.py` (`nest_by_heading`) | `d3059c6` | **Plus simple** | Quatre copies → une ; cinq appelants ; `may_open` sert à un seul, acceptable | — |
| Règles dans `domain/analysis_editing.py`, `domain/chunk_editing.py` | `d3059c6` | **Plus simple** | Hash et règles écrits une fois ; résidu : `insert`/`update`/`delete` pour les tests seulement | Supprimer ces trois fonctions |
| `CurrentAnalysisResolver` + port `CurrentAnalysisReader` | `4939413` | **Plus simple** sur la règle | Une règle au lieu de lecteurs divergents ; port à une implémentation mais sept consommateurs | Sans les deux relais `DocumentService` / `ParseLoader` |
| `DocumentAnalysisState` avec suivi des parties modifiées | `4939413` | **Plus complexe que nécessaire** (à la marge) | Chaque écrivain sait ce qu'il change ; drapeaux, `mark_saved`, `save_state` sans appelant, `selection` pour les tests | Deux fonctions d'écriture explicites dans la transaction |
| `ChunkRepository.replace_for_document` | `4939413` | **Plus simple** | Une transaction au lieu de trois ou quatre commits | Supprimer `soft_delete_for_document` devenu orphelin |
| `load_current_analysis` / `load_active_result` | `4939413` | **Plus complexe que nécessaire** | Deux noms pour la même analyse ; repli `None` copié trois fois, jamais pris | `active_result_service` obligatoire, branches `else` supprimées |
| `ChunkService` façade de `ChunkPushService` et `DocumentTreeService` | `8a60cee` | **Plus complexe que nécessaire** | Quatre relais, collaborateurs construits en interne, constructeur toujours à 13 paramètres | Routes branchées sur les deux services via `deps` ; câblage dans `builder.py` |
| `sources_view.py` en trois modules | `8a60cee` | Neutre | Code déplacé, pas ajouté (369 → 97 + 248 + 47) | — |
| `PageRaster.vue` | `18cdf1b` | **Plus simple** pour `PagePreviewWithOverlay` | Un jeu de gestionnaires au lieu de deux | Y adosser aussi `PdfPagePreview` |
| `pendingDraft.ts`, `commandStacks.ts`, `mergeSelection.ts`, `previewScheduler.ts` | `e03ac99` | Neutre | Fonctions pures testées ; `PreviewScheduler` (6 méthodes, un client) et un module de 20 lignes sont un peu cérémonieux | — |
| `AnalysisEditHistoryPanel.vue`, `EditorBanners.vue`, `editorButton.css` | `81e11f3` | Neutre | 805 → 620 lignes, styles partagés par import | — |
| `shared/cssTokens.ts` + découpage de `BboxCanvas` | `453a1b9` | Neutre | Un lecteur de jetons de 15 lignes ; mais un des trois appelants (`StructureViewer.vue`) est mort | Supprimer `StructureViewer.vue` |
| CI (`backend-docling`, UI sur `release/**`, image locale, retrait de `audit-checks`) | `23e4c81` | Neutre | Retire un job mort ; ajoute une liste de tests codée en dur | Marqueur pytest |

---

## Points positifs

- **Abstraction LLM réduite** à un port sans dispatch, un seul contrôle de la variable dépréciée, documentée (`CHANGELOG.md:48`, `docs/configuration.md:49`).
- **Une seule marche des titres** pour l'index, le plan, l'arbre des chunks et l'arbre de l'éditeur (`domain/heading_tree.py:51-91`).
- **Une seule règle d'analyse courante** pour l'éditeur, les chunks, l'export, Ask et MCP (`domain/models.py`, `services/current_analysis.py`).
- **Écritures atomiques** : chunks et état du document dans une transaction (`persistence/chunk_repo.py:145-166`).
- **Route `/preview` réduite** à une branche `ServiceError`.
- **Services sans accès direct au système de fichiers** par un port dont chaque méthode sert.

---

## Non vérifié

- Comportement réel : le code n'a pas été exécuté (aucune suite, aucun type-check sur `efc0bc5`). En particulier, que l'union non discriminée de payloads en `extra="forbid"` sérialise bien chaque entrée d'historique.
- Usages hors dépôt (scripts, notebooks, forks) des fichiers et méthodes déclarés morts.
- Fréquence réelle du repli serveur des aperçus.
- Raison du choix d'un contrôle `Host` maison plutôt que `TrustedHostMiddleware` : aucune trace écrite.

---

## Verdict partiel : GO CONDITIONNEL

Aucun écart CRITICAL. Un écart MAJOR (plomberie de l'éditeur, qui porte 4.2 depuis que le MAJ
LLM est résolu), sous le seuil bloquant (> 3). Score 67 / 100, en baisse de 8 points : la seconde
remédiation a résolu le MAJ visé mais a ajouté des relais purs (4.3) et des réglages (4.5).
Le gain le plus rapide est une suppression : code mort front et back, relais de `ChunkService`,
replis `None`. Avec la carte de citation, le cache d'aperçu et la plomberie de l'éditeur, 4.2 et
4.3 repassent conformes (score 92).
