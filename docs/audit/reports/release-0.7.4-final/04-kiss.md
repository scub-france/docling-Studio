# Rapport d'audit : KISS (Keep It Simple, Stupid)

**Release** : 0.7.4
**Date** : 2026-11-20
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups`, commit `707a486`, arbre de travail (`experiments/mcp-bench/` non suivi, hors périmètre)
**Nature** : Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5` (score 67). Premier passage de ce contrôle à `a744f48` (score 58), repris à `707a486`.

Code non exécuté par l'auditeur. Le mainteneur indique, sur `707a486` : ruff propre, 1 789 tests passés, 15 sautés ; non vérifié ici.

Périmètre : `document-parser/` (hors `.venv/`, `__pycache__/`, `tests/` pour les constats) et `frontend/src/`.
Delta examiné : `git log efc0bc5..707a486` (14 commits), dont `a744f48..707a486` : `ef37b6f`, `cce3d24`, `062bf70`, `414fdb7`, `707a486`.
Méthode : lecture de l'arbre de travail, `rg`, `git diff` / `git show` en lecture seule, recherche
d'appelants de production pour chaque symbole suspect. Même lecture des items qu'à la validation.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 8 |
| Score | 75 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 4 |
| Ecarts INFO | 11 |

Poids total : 12. Poids conformes : 9 (4.1, 4.3, 4.4, 4.6, 4.7, 4.8). Non conformes : 4.2 (2), 4.5 (1).
`score = 9 / 12 × 100 = 75`. Validation : 67. Premier passage à `a744f48` : 58.

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 4.1 | Pas de design pattern complexe superflu | 2 | Oui | Grep fiche : `AppStateBuilder` seul (`bootstrap/builder.py:84`). Plus de drapeaux de modification dans `DocumentAnalysisState`. Le `_replace` à fonction d'écriture passée en paramètre (`persistence/chunk_repo.py:177-206`) reste privé, deux appelants (INFO) |
| 4.2 | Résout le problème actuel, pas hypothétique | 2 | **Non** | Plomberie de l'éditeur, carte de citation et cache d'aperçu non touchés (décision du mainteneur). Code mort restant : chemin workspace du store, `HistoryDrawer.vue`, sa spec e2e, `DocumentMerger`, `get_chunks`, `mark_stale` |
| 4.3 | Pas de wrapper sans valeur ajoutée | 1 | Oui (limite) | Un relais reste, `ParseLoader.find_current_parse_ids` (`services/parse_loader.py:72-79`), avec sa raison écrite dans la docstring. Les deux méthodes publiques de `SqliteChunkRepository` au-dessus de `_replace` ne sont pas des relais purs : chacune choisit l'écriture de la sélection |
| 4.4 | Outils standard avant solutions maison | 1 | Oui (limite) | Contrôle `Host` maison, raison écrite (`infra/host_guard.py`, docstring de `ApiHostGuardMiddleware`) |
| 4.5 | Configuration simple | 1 | **Non** | Inchangé sur le fond : config MCP en couches, grammaire `name:port` / `name:*` / `*` gardée, `MAX_IMPORT_SIZE_MB` réglage, `OPENSEARCH_DEFAULT_LIMIT` pour du code mort. Le contrôle `Host` grossit (89 → 130 lignes) pour journaliser ce qu'il ignore |
| 4.6 | Pas d'indirection inutile | 2 | Oui (limite) | Chemin des chunks à plat. Mais la règle de rechunk est calculée deux fois : une lecture d'état dans le service, puis la même règle appliquée par l'écriture (INFO) |
| 4.7 | Pas de méta-programmation / magie | 2 | **Oui** | Grep fiche (`__metaclass__`, `type(…, …, …)`, `__init_subclass__`, `__class_getitem__`) plus `create_model` : rien en production. Les sept modèles de payload sont écrits à la main (`api/schemas.py:320-371`) |
| 4.8 | Structures de données les plus simples | 1 | Oui (limite) | `AnalysisDetailPage` télécharge toujours 200 résumés pour en trouver un ; hors diff |

### Métriques de périmètre

| Mesure | efc0bc5 | a744f48 | 707a486 |
|--------|---------|---------|---------|
| Lignes Python de production, net depuis le commit précédent (hors `tests/`) | — | −278 | +182 (+322 / −140) |
| Lignes front de production, net | — | −1 781 | +12 (attributs `data-e2e`, commentaires) |
| Paramètres du constructeur de `ChunkService` | 13 | 4 | 5 |
| `infra/host_guard.py` | 113 l. | 89 l. | 130 l. |
| Relais purs | 6 | 1 | 1 (justifié par écrit) |
| Création dynamique de classes en production | 0 | 1 (`create_model`) | 0 |

---

## Ecarts constatés

### [MAJ] Plomberie de l'éditeur pour des besoins non exprimés — porte l'item 4.2 (reconduit, inchangé)

- **Localisation** : `document-parser/persistence/database.py:258` (`edited_analysis_cache`) ; `document-parser/services/analysis_edit_service.py:212` (`rebuild`), `:235` (`engine_version` écrit, jamais comparé), `:287` (`_project_cache`) ; `document-parser/api/analysis_edits.py:195-202` (route `rebuild`) ; `document-parser/api/schemas.py` (`warnings`, `reference_changes` de `AnalysisEditorResponse`) ; `frontend/src/features/analysis-editor/api.ts:71` (`rebuildAnalysisEdits`, aucun appelant, même en test) ; `frontend/src/features/analysis-editor/types.ts:15`, `:55-56`
- **Constat** : non touché, volontairement : le plan du troisième cycle le laisse au mainteneur (PR #319 d'un contributeur, route `rebuild` annoncée au CHANGELOG). La carte de citation (`mcp_adapter/citation_app.html`, 1 256 l., `MCP_CITATION_CARD=false`) et le cache d'aperçu (`infra/preview_cache.py:16-20`) sont eux aussi inchangés.
- **Règle violée** : item 4.2 (poids 2).
- **Remédiation** : retirer la route et le client `rebuild`, `warnings` / `referenceChanges`, `beforeElementId` ; comparer ou retirer `engine_version`. Avec la carte de citation, le cache d'aperçu et le code mort ci-dessous, 4.2 repasse conforme (score 92).

### [MIN] Configuration : couches MCP, grammaire `Host`, deux réglages superflus (reconduit, légèrement alourdi)

- **Localisation** : `document-parser/domain/mcp_config.py`, `document-parser/infra/settings.py:90-128`, `:259-300` (inchangés) ; `document-parser/infra/host_guard.py:34` (motif qui accepte `:port` et `:*`), `:37-55` (`parse_host_name`, `parse_allowed_host_name`, `_match_host`), `:57-60` (`*` éteint le contrôle, comme la variable vide), `:63-74` (`split_allowed_hosts`), `:77-102` (`describe_host_check`, `log_host_check`) ; `document-parser/infra/settings.py:31`, `:231`, `document-parser/main.py:95-101` (`MAX_IMPORT_SIZE_MB`) ; `document-parser/infra/settings.py:71`, `:252` (`OPENSEARCH_DEFAULT_LIMIT`)
- **Constat** : `707a486` remplace le drapeau `port_wildcard` par deux fonctions d'analyse et `062bf70` ajoute un avertissement au démarrage pour les entrées ignorées. L'avertissement a une vraie valeur (une entrée mal écrite refusait en silence le nom qu'elle voulait autoriser). Mais la cause reste : la grammaire `:port` / `:*` / `*` est gardée pour être aussitôt ignorée, et elle demande maintenant deux fonctions d'analyse au lieu d'une. Avec une liste de noms seuls, une seule fonction d'analyse et un seul cas « off » suffiraient. Le reste est inchangé.
- **Règle violée** : item 4.5 (poids 1).
- **Remédiation** : `API_ALLOWED_HOSTS` = liste de noms (motif sans port ni `*`, un seul `parse_host_name`) ; garder l'avertissement ; `MAX_IMPORT_SIZE_MB` → constante ; retirer `get_chunks` et `OPENSEARCH_DEFAULT_LIMIT` ensemble.

### [MIN] Code mort restant (reconduit, inchangé depuis a744f48)

- **Localisation** :
  - front, chemin workspace inatteignable : `frontend/src/features/document/ui/HistoryDrawer.vue` (263 l., aucun importeur) ; `frontend/src/features/document/store.ts` (`pickWorkspaceVersion`, `workspaceVersions`, `workspaceCurrentVersionId`, `workspaceCurrentVersion`, `workspaceLatestAnalysis`, `loadWorkspace`, `refreshWorkspace`, `reloadWorkspaceVersions`, `setWorkspaceVersion`) ; `frontend/src/features/document/api.ts:95`, `:100`. Les deux appels de `loadWorkspace` sont dans la branche « pas de prop `analysis` » de `pages/DocParseTab.vue`, que son seul parent (`pages/AnalysisDetailPage.vue:55-61`, sous `v-else` de `!analysis`) ne prend jamais ;
  - e2e : `e2e/ui/src/test/resources/documents/doc-history-drawer.feature` (`@regression`) clique `[data-e2e=history-btn]`, que rien ne rend. `cce3d24` a réparé deux autres specs, pas celle-ci ;
  - back : `document-parser/domain/ports.py:101-104` (`DocumentMerger`) et `document-parser/infra/docling_merger.py` (tests seulement) ; `document-parser/domain/ports.py:553`, `document-parser/infra/opensearch_store.py:168` (`get_chunks`, tests seulement) ; `document-parser/domain/models.py:314` (`DocumentStoreLink.mark_stale`, aucun appelant).
- **Règle violée** : item 4.2 (déjà compté).
- **Remédiation** : trancher « code mort ou fonctionnalité perdue » pour le chemin workspace (supprimer, environ 450 lignes, ou rebrancher un bouton History) ; supprimer `DocumentMerger`, `DoclingDocumentMerger`, `mark_stale`.

### [MIN] Repli serveur des aperçus équipé comme un chemin principal (reconduit, inchangé)

- **Localisation** : `document-parser/infra/preview_cache.py:16`, `:20`
- **Règle violée** : item 4.2 (déjà compté).

### [MIN] Carte de citation désactivée par défaut et maintenue (reconduit, inchangé)

- **Localisation** : `document-parser/infra/settings.py:128`, `:290`, `document-parser/mcp_adapter/citation_app.html`, `document-parser/mcp_adapter/apps.py:124`
- **Règle violée** : item 4.2 (déjà compté).

---

### [INFO] Règle de rechunk calculée deux fois (nouveau, `062bf70`)

- **Localisation** : `document-parser/services/chunk_service.py:59`, `:64` (dépendance ajoutée), `:224` (lecture d'état), `:235` (`resolve_selection_after_rechunk`) ; `document-parser/domain/models.py:184-198` ; `document-parser/persistence/chunk_repo.py:155-174` (`replace_keeping_selection` → `adopt_selection`)
- **Constat** : `adopt_selection` fait `INSERT … ON CONFLICT DO NOTHING` et ne fait rien pour `None` : l'écriture applique déjà la règle (une ligne existante garde sa sélection, une ligne créée prend l'analyse chunkée). Le service lit l'état, calcule la même règle et passe le résultat à cette écriture, qui l'ignore dès qu'une ligne existe. Résultat identique à passer `source_analysis_id` directement, comme à `a744f48` : une requête de plus par rechunk et un paramètre de constructeur de plus (4 → 5) pour rien. La docstring de la fonction le dit elle-même (« Persistence applies this rule in the write itself »). L'ajout du `try/except AnalysisNotSelectableError` (`:237`), lui, est une correction réelle (409 au lieu de 500).
- **Remédiation** : retirer la lecture d'état et la dépendance de `ChunkService`, passer `source_analysis_id` ; garder la règle documentée sur `replace_keeping_selection` (ou la fonction de domaine, testée, appelée par le dépôt).

### [INFO] Deux méthodes de port au lieu d'un drapeau (nouveau, `707a486`)

- **Localisation** : `document-parser/domain/ports.py` (`replace_and_select`, `replace_keeping_selection`) ; `document-parser/persistence/chunk_repo.py:136-206`
- **Constat** : les appels se lisent mieux (`replace_and_select` pour une restauration, `replace_keeping_selection` pour un rechunk) qu'avec `keep_selection=True`. Le prix : deux signatures de six paramètres recopiées au port et à l'adaptateur, et un `_replace` qui reçoit une fonction d'écriture (`Callable[[aiosqlite.Connection, str, str | None], Awaitable[None]]`). Bilan à peu près neutre ; pas de complexité à corriger.

### [INFO] Fonctions de règle de sélection dans le domaine (nouveau, `062bf70`)

- **Localisation** : `document-parser/domain/models.py:164-181` (`resolve_selection_after_restore`), `:184-198` ; appelant `services/version_service.py:184-191`
- **Constat** : pour la restauration, la règle sort du service vers une fonction pure de dix lignes, testée : neutre, bonne direction. Pour le rechunk, voir l'INFO « calculée deux fois ».

### [INFO] Un relais gardé, raison maintenant écrite (4.3 à la limite)

- **Localisation** : `document-parser/services/parse_loader.py:72-79`
- **Constat** : la docstring dit pourquoi : les trois appelants tiennent déjà le chargeur. Recevable.

### [INFO] Le port et l'attribut gardent le mot « active »

- **Localisation** : `document-parser/domain/ports.py` (`ActiveAnalysisResultReader`), `services/chunk_service.py:57`, `services/document_tree_service.py:37`, `services/export_service.py:47` (`active_result_service`)
- **Remédiation** : `EditedResultReader` / `edited_results`.

### [INFO] Commentaire de justification périmé sur les payloads

- **Localisation** : `document-parser/api/schemas.py:313-318`
- **Constat** : le commentaire garde « without the bounds, so a row written before the bounds still reads back ». Avec des classes écrites à la main sans bornes, la phrase n'a plus d'objet, et aucune ligne antérieure aux bornes n'existe dans une base publiée (éditeur et bornes en `[Unreleased]`). L'union non discriminée reste départagée par la forme du dict (`extra="forbid"` + champs obligatoires), ce que le commentaire dit ; acceptable pour sept classes explicites.

### [INFO] Arithmétique d'index dans la fusion en temps linéaire

- **Localisation** : `document-parser/infra/docling_editor.py` (`_merge_text`, calcul de `insertion_index`)
- **Constat** : prix de la performance (audit 12), commenté et comparé à l'ancien code. Pas de sur-ingénierie.

### [INFO] Coût du câblage après retrait de la façade

- **Localisation** : `document-parser/api/state.py:59`, `:71-72` ; `document-parser/api/deps.py:42-46`, `:91-102`
- **Constat** : trois emplacements et trois accesseurs sur le modèle existant, contre trois emplacements morts et une fabrique retirés. Bilan net favorable.

### [INFO] Reste de l'abstraction LLM

- **Localisation** : `document-parser/domain/ports.py` (`LLMProvider`), `provider_type` en lecture seule à travers six couches
- **Remédiation** : retirer `provider_type` avec la variable dépréciée.

### [INFO] Résidus reconduits, inchangés

- `PdfInspector` construit par deux chemins et `pdf_inspector: PdfInspector | None` pour les tests (`services/analysis_service.py:95`).
- `--warning-muted` figé en RGB à côté de `color-mix(…)`.
- Alias de `frontend/src/features/history/api.ts:2-5`.
- `AnalysisDetailPage` (4.8) : 200 résumés pour en trouver un.
- Event-sourcing avec chaîne de hash, introspection d'une API privée Docling, pont MCP Apps en deux copies, `_neutralise_all` en double (`mcp_adapter/wire.py:72`, `wire_mapping.py:42`).

### [INFO] CI : liste de tests codée en dur (hors fiche, reconduit)

- **Localisation** : `.github/workflows/ci.yml:91-97`
- **Remédiation** : un marqueur pytest (`-m docling`).

Résolus depuis `a744f48` et retirés de la liste : import local dans `domain/navigation.py` (`pick_within_budget` est dans `domain/element_reader.py:59`), drapeau `keep_selection` (remplacé, voir INFO), drapeau `port_wildcard` (remplacé par deux fonctions, compté en 4.5).

---

## Contrôle à a744f48

Premier passage de ce contrôle, le 2026-11-19 : **58 / 100, 5/8 items, 0 CRIT, 2 MAJ, 4 MIN, 11 INFO,
NO-GO** (sous le seuil de 60). 4.3 était revenu conforme (façade `ChunkService` retirée) ; 4.7 avait
basculé.

Le second MAJ portait sur 4.7 : `914246e` avait remplacé sept modèles de payload plats par une
génération à l'import (`_strip_bounds` qui réécrivait récursivement des types, `create_model`, noms de
classe par `str.replace`, union calculée à l'exécution par `reduce(operator.or_, …)` et illisible
pour un type-checker). La justification, relire des lignes écrites avant les bornes, ne couvrait
aucune base publiée. Remédiation proposée : sept classes écrites à la main et un test de concordance.

**Ce qu'il est devenu** : fermé par `062bf70`. Sept classes explicites (`api/schemas.py:320-371`), une
union écrite à la main (`:362-371`), `create_model`, `_strip_bounds`, `reduce` et les imports de
`typing` d'introspection ont disparu. La dérive entre requête et payload est couverte par
`tests/test_schemas.py:186-196` (le test compare les champs ; il lit les annotations, mais dans un
test, pas en production). Le grep de la fiche ne trouve plus rien. 4.7 est conforme, le score passe
à 75, comme le rapport l'annonçait.

Le reste du passage à `a744f48` tient toujours : MAJ 4.2 inchangé, MIN 4.5, code mort, aperçu et
carte de citation inchangés.

---

## Delta vs validation

Score : **67 → 75 (+8)**. Items conformes : 5/8 → 6/8. 4.3 redevient conforme (façade retirée) ;
4.7 reste conforme (après un aller-retour pendant le cycle). 4.2 et 4.5 restent non conformes.
CRIT 0 → 0, MAJ 1 → 1, MIN 5 → 4.

| Écart de la validation (efc0bc5) | Statut à 707a486 | Détail |
|----------------------------------|------------------|--------|
| [MAJ] Plomberie de l'éditeur (4.2) | **Inchangé** (décision du mainteneur) | |
| [MIN] Six relais purs (4.3) | **Résolu** | Un relais gardé, raison écrite |
| [MIN] Configuration (4.5) | **Inchangé sur le fond** | Nom seul comparé ; grammaire, `*`, `MAX_IMPORT_SIZE_MB`, `OPENSEARCH_DEFAULT_LIMIT` gardés ; garde `Host` 113 → 130 lignes |
| [MIN] Code mort | **Fortement réduit** | 7 fichiers front, tout le code mort back listé sauf `get_chunks` ; restent chemin workspace, `HistoryDrawer.vue`, spec e2e, `DocumentMerger`, `mark_stale` |
| [MIN] Repli d'aperçu, carte de citation (4.2) | Inchangés | |
| [INFO] Suivi des parties modifiées de `DocumentAnalysisState` | **Résolu** | |
| [INFO] Deux noms et trois replis `None` | **Résolu** | Le nom du port dit encore « active » |
| [INFO] Sept modèles de payload recopiés | **Résolu** | Classes explicites + test de concordance |
| [INFO] Contrôle `Host` maison (4.4) | **Résolu** | Raison écrite |
| [INFO] Deux composants d'aperçu | **Résolu** (justifié) | |
| [INFO] Reste LLM | **Réduit** | `health_check` retiré |
| [INFO] Autres reconduits | Inchangés | |

### Les huit structures « plus complexes que nécessaire » de la validation

| # | Structure | Statut à 707a486 | Où |
|---|-----------|------------------|-----|
| 1 | Façade `ChunkService` | **Corrigé** (4 → 5 paramètres depuis `062bf70`, voir INFO) | `services/chunk_service.py:52-70` ; routes `api/document_chunks.py:177`, `:195`, `:210`, `:226` |
| 2 | Relais `DocumentService` / `ParseLoader` | **Réduit** | `DocumentService` retiré ; `ParseLoader` gardé avec sa raison (`services/parse_loader.py:72-79`) |
| 3 | current/active et replis `None` | **Corrigé** | Nom du port résiduel (INFO) |
| 4 | Suivi des parties modifiées | **Corrigé** | `domain/models.py:97-141`, `persistence/document_analysis_repo.py` |
| 5 | `chunk_editing.insert` / `update` / `delete` | **Corrigé** | Supprimés |
| 6 | Sept modèles de payload | **Corrigé** (après un passage par pire à `a744f48`) | `api/schemas.py:320-371` |
| 7 | `host_guard.py` + `API_ALLOWED_HOSTS` | **Réduit puis regonflé** | Comparaison par nom ; 130 lignes, deux fonctions d'analyse, grammaire gardée |
| 8 | `body_limit.py` + `MAX_IMPORT_SIZE_MB` | **Inchangé** | `infra/settings.py:31`, `:231`, `main.py:95-101` |

---

## Le troisième cycle a-t-il simplifié ?

**Oui.** Sur l'ensemble du cycle (`efc0bc5..707a486`), le code de production perd environ 100 lignes
Python nettes et 1 770 lignes front ; la façade, les drapeaux de modification, les replis morts et
les deux noms pour une même chose ont disparu ; la génération de modèles a été retirée aussitôt
relevée.

Les deux derniers commits ajoutent un peu de poids pour peu de valeur, sans faire tomber d'item :
- la lecture d'état ajoutée à `ChunkService` recalcule une règle que l'écriture applique déjà
  (une requête et une dépendance pour un résultat identique) ;
- le contrôle `Host` passe de 89 à 130 lignes : l'avertissement est utile, mais il soigne un
  symptôme de la grammaire `:port` / `:*` / `*` que le code garde pour l'ignorer ;
- les deux méthodes de port au lieu d'un drapeau, et les deux fonctions d'analyse au lieu d'un
  drapeau, sont neutres : plus de lignes, des appels plus clairs.

| Changement depuis a744f48 | Commit | Verdict | Raison |
|---------------------------|--------|---------|--------|
| Payloads écrits à la main + test de concordance | `062bf70` | **Plus simple** | Plus de méta-programmation ; sept classes plates |
| `resolve_selection_after_restore` | `062bf70` | Neutre | Règle déplacée du service vers une fonction pure |
| `resolve_selection_after_rechunk` + lecture d'état dans `ChunkService` | `062bf70` | **Plus complexe que nécessaire** (à la marge) | Calcul redondant avec `adopt_selection` |
| `pick_within_budget` dans `element_reader.py` | `062bf70` | **Plus simple** | Plus d'import local |
| `split_allowed_hosts`, `log_host_check` | `062bf70` | Légèrement plus lourd | Avertissement utile ; grammaire toujours là |
| Raison écrite pour `ParseLoader.find_current_parse_ids` | `062bf70` | Plus clair | |
| `replace_and_select` / `replace_keeping_selection` sur `_replace` | `707a486` | Neutre | Lisibilité contre deux signatures recopiées |
| `parse_host_name` / `parse_allowed_host_name` | `707a486` | Neutre | Un drapeau remplacé par deux fonctions de cinq lignes |

---

## Points positifs

- **Méta-programmation retirée** dès qu'elle a été relevée, avec un test qui garde requêtes et payloads alignés.
- **Chemin des chunks à plat**, chaque route appelle le service qui fait le travail.
- **Agrégat d'état figé**, écritures nommées par ce qu'elles font.
- **Code mort traité avec preuve**, et le cas douteux signalé plutôt que supprimé à l'aveugle.
- **Décisions écrites** là où l'audit demandait une trace (`Host`, aperçu, relais `ParseLoader`).

---

## Non vérifié

- Comportement réel : rien n'a été exécuté par l'auditeur ; les résultats de suites cités sont ceux du mainteneur.
- Que l'union non discriminée de payloads accepte chaque entrée d'historique réellement stockée.
- Qu'aucun parent hors dépôt ne monte `DocParseTab` sans `analysis` ; que la spec `doc-history-drawer.feature` soit sélectionnée par un run Karate.
- Usages hors dépôt de `DocumentMerger`, `get_chunks`, `mark_stale`.

---

## Verdict partiel : GO CONDITIONNEL

Aucun écart CRITICAL. Un écart MAJOR (plomberie de l'éditeur, 4.2), laissé à la décision du
mainteneur, sous le seuil bloquant. Score 75 / 100, en hausse de 8 points sur la validation et de 17
sur le premier passage de ce contrôle. Pour aller plus loin : trancher la plomberie de l'éditeur, la
carte de citation, le cache d'aperçu et le chemin workspace (4.2 conforme, score 92), puis réduire
`API_ALLOWED_HOSTS` à une liste de noms et `MAX_IMPORT_SIZE_MB` à une constante (4.5 conforme, 100).
