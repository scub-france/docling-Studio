# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `a744f48`, arbre de travail (`experiments/mcp-bench/` non suivi, hors périmètre)
**Nature** : Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5` (score 67)

Code non exécuté : aucune suite, aucun linter, aucun type-check lancé pour ce contrôle (poste utilisé).
Les messages de commit du cycle disent les suites passées « on a calm machine » ; ce n'est pas vérifié ici.

Périmètre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/` pour les constats) et `frontend/src/`.
Delta examiné : `git log efc0bc5..a744f48` (9 commits, dont 6 de code : `60234e4`, `da6603d`, `73ceaf3`, `894bba4`, `914246e`, `a744f48`).
Méthode : lecture de l'arbre de travail, `rg`, `git diff` / `git show` en lecture seule, recherche
d'appelants de production pour chaque symbole suspect. Même lecture des items qu'à la validation.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 8 |
| Score | 58 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 4 |
| Ecarts INFO | 11 |

Poids total : 12. Poids conformes : 7 (4.1, 4.3, 4.4, 4.6, 4.8). Non conformes : 4.2 (2), 4.5 (1), 4.7 (2).
`score = 7 / 12 × 100 = 58,3` → **58**. Validation : 67.

Le score tient à un seul jugement : 4.7 (méta-programmation des modèles de payload). Si l'on juge
cette génération nécessaire, 4.7 reste conforme et le score est **75**. Je ne la juge pas nécessaire
(voir l'écart MAJ 4.7).

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Grep fiche : `AppStateBuilder` seul (`bootstrap/builder.py:84`). Le suivi des parties modifiées de `DocumentAnalysisState` a disparu (agrégat figé, écritures explicites) |
| 4.2 | Résout le problème actuel, pas hypothétique | 2 | **Non** | Plomberie de l'éditeur, carte de citation et cache d'aperçu non touchés, laissés à la décision du mainteneur (plan, section 2). Le code mort a beaucoup baissé mais il en reste : un composant, un chemin de store inatteignable, un port, une méthode de port, un client sans appelant |
| 4.3 | Pas de wrapper sans valeur ajoutée | 1 | Oui (limite) | Des six relais, il en reste un : `ParseLoader.find_current_parse_ids` (`services/parse_loader.py:72-76`), gardé pour ne pas ajouter une dépendance à trois services qui ont déjà `ParseLoader`. Aucun relais ajouté par le cycle |
| 4.4 | Outils standard avant solutions maison | 1 | Oui (limite) | Le contrôle `Host` reste maison, mais la raison de ne pas prendre `TrustedHostMiddleware` est maintenant écrite (`infra/host_guard.py:67-70`) |
| 4.5 | Configuration simple | 1 | **Non** | Config MCP en couches inchangée ; `API_ALLOWED_HOSTS` garde la grammaire `name:port` / `name:*` / `*` (ports ignorés) ; `MAX_IMPORT_SIZE_MB` reste un réglage ; `OPENSEARCH_DEFAULT_LIMIT` ne borne qu'une méthode sans appelant |
| 4.6 | Pas d'indirection inutile | 2 | Oui | Le saut route → `ChunkService` → `ChunkPushService` / `DocumentTreeService` a disparu ; la route document lit l'analyse courante sans passer par `DocumentService` |
| 4.7 | Pas de méta-programmation / magie | 2 | **Non** | Nouveau : six classes de réponse créées à l'import par `create_model` à partir de l'introspection des annotations des modèles de requête (`api/schemas.py:317-359`). Nécessité non avérée |
| 4.8 | Structures de données les plus simples | 1 | Oui (limite) | `AnalysisDetailPage` télécharge toujours 200 résumés pour en trouver un (`pages/AnalysisDetailPage.vue`), hors diff ; même lecture qu'à la validation |

### Métriques de périmètre

| Mesure | efc0bc5 | a744f48 |
|--------|---------|---------|
| Fichiers `.py` de production | 146 | 145 (−2 supprimés, +1 `domain/quote_location.py`) |
| Lignes Python de production (`git diff --shortstat`, hors `tests/`) | — | +807 / −1 085 (net **−278**) |
| Lignes front de production (hors `*.test.ts`) | — | +59 / −1 840 (net **−1 781**) |
| Lignes de tests backend / front | — | +1 035 / −710 ; +127 / −521 |
| `Protocol` dans `domain/ports.py` | 32 (826 l.) | 32 (846 l.) |
| Variables d'env lues par `infra/settings.py` (même comptage aux deux commits) | 44 | 44 |
| Relais purs ajoutés par la seconde passe | 6 | 1 |
| Composants front sans importeur | 7 fichiers + `HistoryDrawer.vue` | `HistoryDrawer.vue` (263 l.) |
| Paramètres du constructeur de `ChunkService` | 13 | 4 |
| `infra/host_guard.py` | 113 l. | 89 l. |

---

## Ecarts constatés

### [MAJ] Plomberie de l'éditeur pour des besoins non exprimés — porte l'item 4.2 (reconduit, inchangé)

- **Localisation** : `document-parser/persistence/database.py:258` (`edited_analysis_cache`) ; `document-parser/services/analysis_edit_service.py:212` (`rebuild`), `:235` (`engine_version` écrit, jamais comparé), `:287` (`_project_cache`) ; `document-parser/api/analysis_edits.py:195-202` (route `rebuild`) ; `document-parser/api/schemas.py:301-302` (`warnings`, `reference_changes`) ; `frontend/src/features/analysis-editor/api.ts:71` (`rebuildAnalysisEdits`, plus aucun appelant, même en test) ; `frontend/src/features/analysis-editor/types.ts:15` (`beforeElementId`), `:55-56`
- **Constat** : non touché, volontairement : le plan du troisième cycle le range dans les « décisions laissées au mainteneur » parce qu'il vient de la PR #319 d'un contributeur et que le CHANGELOG annonce la route `rebuild`. Noté tel quel. La carte de citation (`mcp_adapter/citation_app.html`, 1 256 l., `MCP_CITATION_CARD=false`) et le cache d'aperçu (`infra/preview_cache.py:16-20`) sont eux aussi inchangés.
- **Règle violée** : item 4.2 (poids 2).
- **Remédiation** : retirer la route et le client `rebuild`, `warnings` / `referenceChanges`, `beforeElementId` ; comparer ou retirer `engine_version`. Effort M. Avec la carte de citation, le cache d'aperçu et le code mort restant (MIN ci-dessous), 4.2 repasse conforme.

### [MAJ] Modèles de payload générés par introspection des annotations (nouveau)

- **Localisation** : `document-parser/api/schemas.py:317-321` (commentaire), `:323-332` (`_strip_bounds`), `:335-336` (`_StoredPayload`), `:339-346` (`_stored_payload_model`), `:356-359` (`_EDIT_REQUESTS`, union construite par `reduce(operator.or_, …)`), utilisée comme annotation `:367`
- **Constat** : `914246e` remplace sept modèles plats (une soixantaine de lignes, un champ par ligne) par une génération à l'import :
  - `_strip_bounds` réécrit récursivement des types (`Annotated`, `Literal`, `Union`/`UnionType`, reconstruction d'un générique par `get_origin(...)[...]`) pour quatre formes de champ réelles (`str`, `int`, `list[ElementId]`, `ElementId | None`, un `Literal | None`) ;
  - `create_model` fabrique les classes ; leur nom vient d'un `str.replace` sur le nom de la classe de requête : renommer une requête renomme en silence un schéma OpenAPI ;
  - `get_args(get_args(AnalysisEditCommandRequest)[0])` déballe l'union discriminée pour en retrouver les membres ;
  - le type `EditCommandPayloadResponse` est une variable calculée à l'exécution : un type-checker ne le lit pas (`fields: Any` est là pour le faire taire) ;
  - le bon membre est choisi par la forme du dict, et cela tient à trois règles implicites tenues ensemble : chaque clé toujours écrite, `extra="forbid"`, et tous les champs rendus obligatoires (le défaut `separator=" "` disparaît). Or `command_type` est sur la même entrée et pourrait servir de discriminant.

  La raison donnée pour retirer les bornes (« a row written before the bounds still reads back ») ne couvre aucun cas réel : l'éditeur et les bornes sont tous deux dans `[Unreleased]` (`CHANGELOG.md:11`, `:29`), aucune base publiée ne contient de ligne antérieure aux bornes. Le gain réel est une seule définition des champs (DRY, audit 05) ; des formes sans magie le donnent aussi. La fiche range explicitement la création dynamique de classes dans 4.7 (sa commande vise `type(…, …, …)`) : `create_model` en est l'équivalent Pydantic.
- **Règle violée** : item 4.7 (poids 2) — méta-programmation sans nécessité avérée.
- **Remédiation** : au choix, (a) revenir aux sept classes écrites à la main, avec un test qui compare leurs champs à ceux des requêtes (le risque de dérive est couvert sans magie) ; (b) `payload: dict[str, Any]` documenté par `command_type` ; (c) une union discriminée sur `command_type` au niveau de l'entrée. Effort S. Ferme l'écart et rend 9 points de poids sur 12 (score 75).

### [MIN] Configuration : couches MCP inchangées, grammaire `Host` gardée, deux réglages superflus (reconduit, légèrement réduit)

- **Localisation** : `document-parser/domain/mcp_config.py:41-45`, `:107-113` et `document-parser/infra/settings.py:90-128`, `:259-300` (inchangés) ; `document-parser/infra/host_guard.py:34` (motif qui accepte encore `:port` et `:*`), `:37-42` (`port_wildcard`), `:45-61` (`is_host_check_on`, `describe_host_check`, deux façons d'éteindre : vide ou `*`) ; `document-parser/infra/settings.py:110-112` (commentaire qui documente la grammaire), `:285-287` ; `document-parser/infra/settings.py:31`, `:231` et `document-parser/main.py:95-101` (`MAX_IMPORT_SIZE_MB`) ; `document-parser/infra/settings.py:71`, `:252` (`OPENSEARCH_DEFAULT_LIMIT`)
- **Constat** :
  - le contrôle `Host` ne compare plus que le nom (fait), mais le code garde toute la grammaire d'avant pour l'ignorer aussitôt, alors que `docs/configuration.md:127-144` ne documente plus que des noms. `*` reste une seconde façon d'éteindre le contrôle.
  - `MAX_IMPORT_SIZE_MB` reste un réglage alors que l'image passe `/api` par nginx limité à `200M`.
  - `OPENSEARCH_DEFAULT_LIMIT` est documenté, validé, lu, transmis à l'adaptateur, et ne borne que `VectorStore.get_chunks`, qu'aucun code de production n'appelle. Le garder « parce qu'un réglage documenté en dépend » est un argument circulaire.
- **Règle violée** : item 4.5 (poids 1).
- **Remédiation** : `API_ALLOWED_HOSTS` = liste de noms (motif sans port, sans `*`) ; `MAX_IMPORT_SIZE_MB` → constante dans `main.py` ; retirer `get_chunks` et `OPENSEARCH_DEFAULT_LIMIT` ensemble (entrée CHANGELOG « Removed »). MCP comme à la validation.

### [MIN] Code mort restant (reconduit, fortement réduit)

- **Localisation** :
  - front, chemin « workspace » du store de document, inatteignable : `frontend/src/features/document/ui/HistoryDrawer.vue` (263 l., aucun importeur, absent de `features/document/index.ts`) ; `frontend/src/features/document/store.ts:18-30` (`pickWorkspaceVersion`), `:34-35`, `:67-73` (`workspaceVersions`, `workspaceCurrentVersionId`, `workspaceCurrentVersion`, `workspaceLatestAnalysis`, lus nulle part hors du store), `:155-235` (`loadWorkspace`, `refreshWorkspace`, `reloadWorkspaceVersions`, `setWorkspaceVersion`) ; `frontend/src/features/document/api.ts:95`, `:100` ;
  - `loadWorkspace` a deux appels, `frontend/src/pages/DocParseTab.vue:374-379` et `:414-419`, tous deux dans la branche « pas de prop `analysis` ». Le seul parent de `DocParseTab` est `pages/AnalysisDetailPage.vue:55-61`, rendu sous `v-else` de `!analysis` (`:4-5`) et qui passe toujours `:analysis`. Ces branches ne sont jamais prises : aucun écran n'atteint ce chemin. `refreshWorkspace`, `reloadWorkspaceVersions`, `setWorkspaceVersion` n'ont aucun appelant hors `store.test.ts` ;
  - e2e : `e2e/ui/src/test/resources/documents/doc-history-drawer.feature:47-60` (tag `@regression`, pas `@ignore`) clique `[data-e2e=history-btn]`, que rien dans `frontend/src` ne rend : le scénario échouerait à cette étape s'il était lancé ;
  - back : `document-parser/domain/ports.py:101-104` (`DocumentMerger`) et `document-parser/infra/docling_merger.py` (40 l.), arrivés avec l'éditeur (`051ec3f`), sans usage de production, testés seulement (`tests/test_docling_merger.py`) — non relevé à la validation ; `document-parser/domain/ports.py:553` et `document-parser/infra/opensearch_store.py:168` (`get_chunks`, tests seulement) ; `document-parser/domain/models.py:314` (`DocumentStoreLink.mark_stale`, aucun appelant, même en test) ; `frontend/src/features/analysis-editor/api.ts:71` (déjà compté au MAJ).
- **Constat** : `60234e4` a supprimé les sept fichiers listés (2 189 lignes) et `914246e` tout le code mort backend listé, sauf `get_chunks`. `HistoryDrawer.vue` et le chemin workspace ont été laissés en signalant au mainteneur « code mort ou fonctionnalité perdue », ce qui est honnête. Mais `da6603d` a ensuite modifié `loadWorkspace` (+38/−35 lignes de store, +82 lignes de test) tout en écrivant dans son message « No screen reaches that path today » : c'est le même schéma qu'au cycle précédent avec `StructureViewer.vue`, du travail fait sur du code que rien n'affiche.
- **Règle violée** : item 4.2 (déjà compté).
- **Remédiation** : trancher la question « code mort ou fonctionnalité perdue ». Si c'est du code mort : supprimer `HistoryDrawer.vue`, le chemin workspace du store, les deux branches de `DocParseTab.vue`, les deux fonctions d'API, la spec e2e et leurs tests (environ 450 lignes de production). Si c'est une fonctionnalité perdue : remonter un bouton History et la spec redevient valide. Supprimer `DocumentMerger`, `DoclingDocumentMerger`, `mark_stale`.

### [MIN] Repli serveur des aperçus équipé comme un chemin principal (reconduit, inchangé)

- **Localisation** : `document-parser/infra/preview_cache.py:16`, `:20` (LRU 64 Mo, `Lock`)
- **Constat** : hors diff, laissé à la décision du mainteneur avec le reste de 4.2.
- **Règle violée** : item 4.2 (déjà compté).
- **Remédiation** : inchangée.

### [MIN] Carte de citation désactivée par défaut et maintenue (reconduit, inchangé)

- **Localisation** : `document-parser/infra/settings.py:128`, `:290` (`MCP_CITATION_CARD=false`), `document-parser/mcp_adapter/citation_app.html` (1 256 l.), `document-parser/mcp_adapter/apps.py:124`
- **Règle violée** : item 4.2 (déjà compté).
- **Remédiation** : inchangée (retirer ou activer).

---

### [INFO] Un relais gardé, avec une raison recevable (4.3 à la limite)

- **Localisation** : `document-parser/services/parse_loader.py:72-76` ; appelants `services/navigation_service.py:85`, `services/citation_service.py:214`, `services/source_service.py:186`
- **Constat** : relais pur vers `CurrentAnalysisReader`. Le retirer ferait ajouter `current_analysis` au constructeur de trois services qui reçoivent déjà `ParseLoader`. Le coût du relais (cinq lignes) est plus bas que celui de trois injections : je le laisse en INFO.

### [INFO] Le port et l'attribut gardent le mot « active »

- **Localisation** : `document-parser/domain/ports.py:447` (`ActiveAnalysisResultReader`), `services/chunk_service.py:56`, `services/document_tree_service.py:37`, `services/export_service.py:47`, `bootstrap/builder.py:152`, `:193`, `:216` (`active_result_service`)
- **Constat** : les méthodes s'appellent maintenant `load_current_original` / `load_current_edited` et la dépendance est obligatoire (les trois replis `None` ont disparu). Le nom du port et de l'attribut dit encore « active ».
- **Remédiation** : `EditedResultReader` / `edited_results`, au prochain passage.

### [INFO] Un drapeau booléen choisit entre deux écritures

- **Localisation** : `document-parser/persistence/chunk_repo.py:140`, `:159-163` ; `domain/ports.py:303` ; seul `services/chunk_service.py:229` passe `keep_selection=True`
- **Constat** : les écritures explicites remplacent bien le suivi des champs modifiés. Reste un paramètre booléen qui bascule entre `adopt_selection` et `write_selection`. Deux appelants, acceptable.

### [INFO] Arithmétique d'index dans la fusion en temps linéaire

- **Localisation** : `document-parser/infra/docling_editor.py:245-264`
- **Constat** : passer de quadratique à linéaire est justifié (audit 12) et le commit dit avoir comparé 3 000 commandes aléatoires à l'ancien code. Le calcul de `insertion_index` demande un commentaire de cinq lignes ; c'est le prix de la performance, pas de la sur-ingénierie.

### [INFO] Import local pour casser un cycle

- **Localisation** : `document-parser/domain/navigation.py:395` (`from domain.element_reader import resolve` dans `pick_within_budget`)
- **Constat** : code déplacé du service vers le domaine (bonne direction), mais le déplacement crée un cycle d'import contourné par un import dans la fonction.

### [INFO] Contrôle `Host` maison, désormais justifié (4.4)

- **Localisation** : `document-parser/infra/host_guard.py:64-89`
- **Constat** : la docstring dit pourquoi ce n'est pas `TrustedHostMiddleware` (portée `/api` seule, 421 comme `/mcp`). Le cœur du contrôle tient en douze lignes ; le reste est la grammaire comptée en 4.5.

### [INFO] Coût du câblage après retrait de la façade

- **Localisation** : `document-parser/api/state.py:59`, `:71-72` ; `document-parser/api/deps.py:42-46`, `:91-102` ; `document-parser/bootstrap/builder.py:149-154`, `:203-217`
- **Constat** : trois emplacements `AppState` et trois accesseurs `deps` ajoutés (environ 25 lignes, sur le modèle de tous les autres), contre trois emplacements morts retirés, `build_chunk_service` retiré, et un constructeur passé de 13 à 4 paramètres. Bilan net favorable : ce n'est pas un coût à corriger.

### [INFO] Reste de l'abstraction LLM

- **Localisation** : `document-parser/domain/ports.py:639-655` (`LLMProvider`, une implémentation, un consommateur, tous deux dans `infra/`) ; `provider_type` en lecture seule (`domain/app_config.py`, `services/app_config_service.py`, `api/schemas.py`, `bootstrap/factories.py`, `infra/settings.py`)
- **Constat** : `health_check` retiré. Reste un port qu'aucune règle de couche n'exige et `provider_type` à retirer avec la variable dépréciée.

### [INFO] Résidus reconduits, inchangés

- `PdfInspector` construit par deux chemins (`bootstrap/builder.py:185`, `bootstrap/factories.py:307-310`) et `pdf_inspector: PdfInspector | None` pour les tests (`services/analysis_service.py:95`).
- `--warning-muted` figé en RGB (4 occurrences dans `frontend/src`) à côté de `color-mix(…)`.
- Alias de `frontend/src/features/history/api.ts:2-5`.
- `AnalysisDetailPage` (4.8) : 200 résumés pour en trouver un, requêtes en séquence.
- Event-sourcing avec chaîne de hash, introspection d'une API privée Docling, pont MCP Apps en deux copies, `_neutralise_all` en double (`mcp_adapter/wire.py:72`, `wire_mapping.py:42`).

### [INFO] Deux composants d'aperçu : décision écrite

- **Localisation** : `frontend/src/features/document/ui/PageRaster.vue:29-32`
- **Constat** : la raison de ne pas adosser `PdfPagePreview` à `PageRaster` est maintenant écrite (chargement PDF propre, hauteur naturelle, remontage par page). Recevable ; clos côté KISS.

### [INFO] CI : liste de tests codée en dur (hors fiche, reconduit)

- **Localisation** : `.github/workflows/ci.yml:91-97`
- **Remédiation** : un marqueur pytest (`-m docling`).

---

## Delta vs validation

Score : **67 → 58 (−9)**. Items conformes : 5/8 → 5/8, mais pas les mêmes : 4.3 redevient conforme
(façade retirée), 4.7 bascule en non conforme (méta-programmation des payloads). 4.2 et 4.5 restent
non conformes. CRIT 0 → 0, MAJ 1 → 2, MIN 5 → 4.

| Écart de la validation (efc0bc5) | Statut à a744f48 | Détail |
|----------------------------------|------------------|--------|
| [MAJ] Plomberie de l'éditeur (4.2) | **Inchangé** (décision du mainteneur) | `rebuildAnalysisEdits` a même perdu son seul usage (le test) |
| [MIN] Six relais purs (4.3) | **Résolu** (un relais gardé en INFO) | Façade `ChunkService` retirée, `DocumentService.find_current_analysis_id` retiré, `ParseLoader.find_current_parse_ids` gardé |
| [MIN] Configuration (4.5) | **Légèrement réduit** | `Host` comparé par nom seul ; grammaire et `*` gardés ; `MAX_IMPORT_SIZE_MB` gardé ; `OPENSEARCH_DEFAULT_LIMIT` ne sert qu'à du code mort |
| [MIN] Code mort | **Fortement réduit** | 7 fichiers front et tout le code mort back listé supprimés, sauf `get_chunks` ; reste le chemin workspace, `HistoryDrawer.vue`, une spec e2e obsolète, `DocumentMerger` (non relevé à la validation), `mark_stale` |
| [MIN] Repli d'aperçu (4.2) | Inchangé | |
| [MIN] Carte de citation (4.2) | Inchangé | |
| [INFO] Reste LLM | **Réduit** | `health_check` retiré ; `provider_type` reste |
| [INFO] Suivi des parties modifiées de `DocumentAnalysisState` | **Résolu** | Agrégat figé (`domain/models.py:97-141`), trois écritures explicites (`persistence/document_analysis_repo.py:72-119`) ; reste un drapeau `keep_selection` (INFO) |
| [INFO] Deux noms et trois replis `None` | **Résolu** | `load_current_original` / `load_current_edited`, dépendance obligatoire, branches `else` supprimées ; le nom du port dit encore « active » (INFO) |
| [INFO] Sept modèles de payload recopiés | **Remplacé par pire** | Génération dynamique : MAJ 4.7 |
| [INFO] Contrôle `Host` maison (4.4) | **Résolu** | Raison écrite ; 113 → 89 lignes |
| [INFO] Deux composants d'aperçu | **Résolu** (justifié) | Raison écrite dans `PageRaster.vue` |
| [INFO] Commentaires qui justifient la structure | **Résolu** pour l'essentiel | Commentaire faux de `api/state.py` parti avec les emplacements ; relais « See … » partis |
| [INFO] `PdfInspector`, teinte, alias, 4.8, autres | Inchangés | |
| [INFO] CI liste codée en dur | Inchangé | |

Nouveaux écarts : 1 MAJ (payloads générés, 4.7) ; INFO : relais gardé, nom « active », drapeau
`keep_selection`, arithmétique de fusion, import local, coût du câblage.

### Les huit structures « plus complexes que nécessaire » de la validation

Dans l'ordre de valeur de la validation (suppressions d'abord) :

| # | Structure (validation) | Statut | Où |
|---|------------------------|--------|-----|
| 1 | Façade `ChunkService` (4 relais, 13 paramètres) | **Corrigé** | `services/chunk_service.py:52-65` (4 paramètres) ; routes `api/document_chunks.py:177`, `:195`, `:210`, `:226` sur `DocumentTreeServiceDep` / `ChunkPushServiceDep` ; câblage `bootstrap/builder.py:149-154`, `:203-217` |
| 2 | Relais `DocumentService` / `ParseLoader` vers le résolveur | **Réduit** | `DocumentService` : retiré, la route lit `CurrentAnalysisDep` (`api/documents.py:94-106`) ; `ParseLoader` : gardé (`services/parse_loader.py:72-76`) |
| 3 | `load_current_analysis` / `load_active_result` et replis `None` | **Corrigé** | `services/current_analysis.py:69`, `services/analysis_edit_service.py:100` ; plus aucun `is not None` sur le lecteur |
| 4 | `DocumentAnalysisState` avec suivi des parties modifiées | **Corrigé** | `domain/models.py:97-141`, `persistence/document_analysis_repo.py:72-119` ; `save_state`, `mark_saved`, `DocumentAnalysisSelection` supprimés |
| 5 | `chunk_editing.insert` / `update` / `delete` (tests seulement) | **Corrigé** | `domain/chunk_editing.py` ne garde que `split`, `merge`, `check_merge_count` |
| 6 | Sept modèles de payload recopiés | **Pire** | `api/schemas.py:317-359` : moins de lignes dupliquées, mais génération dynamique (MAJ 4.7) |
| 7 | `infra/host_guard.py` + `API_ALLOWED_HOSTS` | **Réduit** | 113 → 89 lignes, nom seul, réponse JSON ; grammaire `:port` / `:*` / `*` gardée (`infra/host_guard.py:34`, `:45-61`) |
| 8 | `infra/body_limit.py` + `MAX_IMPORT_SIZE_MB` | **Inchangé** | `infra/settings.py:31`, `:231`, `main.py:95-101` ; la nouvelle branche 400 (`infra/body_limit.py:43-45`) est une correction, pas de la complexité |

### Liste de code mort de la validation, point par point

| Élément | Statut |
|---------|--------|
| `pages/DocChunkTab.vue`, `pages/IngestLaunchDialog.vue`, `pages/DocIngestTab.logic.ts` (+ test), `features/analysis/ui/AnalysisPanel.vue`, `features/document/ui/PagePreview.vue`, `features/analysis/ui/InspectResultTabs.vue`, `features/analysis/ui/StructureViewer.vue` | **Supprimés** (`60234e4`), barrels nettoyés |
| `api/state.py` : `analysis_repo`, `store_repo`, `document_store_link_repo` et le fixture autouse | **Supprimés** |
| `ChunkRepository.soft_delete_for_document` | **Supprimé** |
| `DocumentAnalysisStateRepository.save_state` | **Supprimé** |
| `DocumentAnalysisSelection`, propriété `selection` | **Supprimés** |
| `chunk_editing.insert` / `update` / `delete` | **Supprimés** |
| `StoreRepository.get_default`, `DocumentVersionRepository.find_latest_for_document` | **Supprimés** |
| `VectorStore.get_chunks` | **Gardé** (`domain/ports.py:553`, `infra/opensearch_store.py:168`), raison circulaire |
| `domain/hashing.py`, `domain/lifecycle_aggregation.py` | **Supprimés** |
| `LLMProvider.health_check` | **Supprimé** |
| `rebuildAnalysisEdits` | Gardé avec la plomberie de l'éditeur (MAJ 4.2) |

---

## Le troisième cycle a-t-il simplifié ?

**Oui, nettement, sauf sur un point.** C'est le premier cycle de remédiation qui fait maigrir le code :
−278 lignes Python et −1 781 lignes front de production nettes, deux modules Python de moins, un
constructeur de 13 paramètres ramené à 4, une couche de relais en moins sur le chemin des chunks, un
mécanisme de suivi de modifications remplacé par trois écritures explicites, trois branches jamais
prises supprimées, deux noms pour une même chose ramenés à un par contenu. Retirer la façade n'a pas
alourdi le câblage : trois emplacements et trois accesseurs sur le modèle existant, contre trois
emplacements morts et une fabrique en moins.

Le point qui va dans l'autre sens est la génération des modèles de payload. Elle remplace une
duplication plate et lisible (rangée INFO à la validation) par une réécriture récursive de types,
`create_model`, des noms de classe obtenus par `str.replace` et une union que seule la forme du dict
départage. Elle protège contre des lignes « écrites avant les bornes » qui ne peuvent exister dans
aucune base publiée. C'est de l'astuce, pas de la simplicité : un DRY gagné au prix de 4.7.

Restent deux choses que ce cycle n'avait pas le mandat de trancher : la plomberie de l'éditeur (avec
la carte de citation et le cache d'aperçu) et la question « code mort ou fonctionnalité perdue » du
chemin workspace. Sur ce second point, le cycle a encore modifié du code qu'il savait inatteignable.

Le score baisse (67 → 58) alors que le code est plus simple : la baisse vient en entier de 4.7, un
item de poids 2 basculé par 40 lignes. Retirer ces 40 lignes au profit de sept classes écrites à la
main ramène le score à 75 sans rien changer d'autre.

| Structure du cycle | Commit | Verdict | Raison | Forme minimale |
|--------------------|--------|---------|--------|----------------|
| Retrait de la façade `ChunkService` | `914246e` | **Plus simple** | Un saut et quatre relais de moins ; câblage à plat | — |
| `AppState` : 3 emplacements ajoutés, 3 retirés ; 3 accesseurs `deps` | `914246e` | Neutre | Même motif que les quinze autres | — |
| Contrôle `Host` à nom seul, réponse JSON | `914246e`, `a744f48` | **Plus simple**, pas minimal | Comparaison juste ; grammaire d'avant gardée pour être ignorée | Motif `nom` seul, une liste, une ligne de log |
| Modèles de payload générés | `914246e` | **Plus complexe que nécessaire** | Méta-programmation pour un cas qui n'existe pas | Sept classes à la main + test de concordance, ou `dict` |
| Réponses de l'éditeur dans un thread | `914246e` | Neutre | Un `asyncio.to_thread` | — |
| Suppression et fusion en temps linéaire | `914246e` | Neutre (justifié) | Ensembles d'identité ; fusion à l'index subtil mais commenté et comparé | — |
| Retrait du code mort backend | `914246e` | **Plus simple** | Deux modules, cinq méthodes de port, un promoteur, trois emplacements | Finir avec `get_chunks`, `DocumentMerger`, `mark_stale` |
| `DocumentAnalysisState` figé, écritures explicites | `73ceaf3` | **Plus simple** | Plus de drapeaux ni de `mark_saved` ; une affectation directe lève | — |
| Noms `load_current_original` / `load_current_edited`, lecteur obligatoire | `73ceaf3` | **Plus simple** | Un nom par contenu ; trois `else` morts supprimés | Renommer aussi le port |
| Prédicat `can_be_current_of`, `domain/quote_location.py`, `pick_within_budget` | `73ceaf3` | Neutre | Règles déplacées dans le domaine (code déplacé, pas ajouté) ; un import local | — |
| Resélection à la suppression de l'analyse active, `adopt_selection` | `73ceaf3` | Neutre | Comportement corrigé ; une fonction d'écriture de plus, un drapeau | — |
| Bandeau d'enregistrement refusé | `da6603d` | Neutre | Correction d'interface, quelques lignes | — |
| `loadWorkspace` sans analyse de repli | `da6603d` | **Travail sur code mort** | Chemin qu'aucun écran n'atteint, dit par le commit lui-même | Supprimer ou rebrancher |
| Retrait de sept composants front | `60234e4` | **Plus simple** | 2 189 lignes, preuve fichier par fichier | Finir avec `HistoryDrawer.vue` |

---

## Points positifs

- **Premier cycle qui retire plus qu'il n'ajoute** : environ −2 060 lignes de production nettes, sans changer le document OpenAPI (d'après `914246e`).
- **Chemin des chunks à plat** : chaque route appelle le service qui fait le travail (`api/document_chunks.py`).
- **Agrégat d'état figé** : une écriture oubliée ne peut plus se perdre en silence (`domain/models.py:97`).
- **Un nom par contenu** pour l'analyse courante, lecteur obligatoire, plus de branches mortes.
- **Code mort traité avec preuve** et, pour le cas douteux, laissé et signalé plutôt que supprimé à l'aveugle.
- **Décisions documentées** là où l'audit demandait une trace (`host_guard.py:67-70`, `PageRaster.vue:29-32`).

---

## Non vérifié

- Comportement réel : rien n'a été exécuté pour ce contrôle. En particulier, que l'union générée accepte chaque entrée d'historique stockée et que l'OpenAPI soit bien identique octet pour octet (affirmé par `914246e`).
- Que les branches `else` de `DocParseTab.vue:374-379` / `:414-419` ne soient prises par aucun autre parent hors dépôt ; dans le dépôt, `AnalysisDetailPage.vue` est le seul.
- Que la spec `doc-history-drawer.feature` soit effectivement sélectionnée par un run Karate (elle n'est pas `@ignore`) ; aucune spec UI n'a été lancée.
- Usages hors dépôt (scripts, forks) de `DocumentMerger`, `get_chunks`, `mark_stale`.
- Raison exacte du maintien de `ParseLoader.find_current_parse_ids` : aucune trace écrite trouvée dans le code ou le commit ; la raison retenue ici (trois injections évitées) est déduite.

---

## Verdict partiel : NO-GO

Aucun écart CRITICAL. Deux écarts MAJOR, sous le seuil bloquant de la règle MAJ (> 3), mais le score,
58 / 100, est sous le seuil de 60 du barème : **NO-GO** au sens strict de `master.md` section 3.

Le verdict tient à un seul écart, cher en points et bon marché à fermer : remplacer la génération des
modèles de payload (`api/schemas.py:317-359`) par sept classes écrites à la main, ou un `dict`, ramène
4.7 en conforme et le score à **75 (GO CONDITIONNEL)**, effort S. La plomberie de l'éditeur reste
alors le seul MAJ, à la décision du mainteneur. Le code, lui, est plus simple qu'à la validation.
