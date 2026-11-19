# Rapport d'audit : DDD (Domain-Driven Design)

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `efc0bc5` (arbre de travail)

Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`docs/audit/reports/release-0.7.4-control/02-ddd.md` sur `a12b744` : 83/100, 13/17, 0 CRIT / 2 MAJ / 12 MIN / 11 INFO, GO).

Code non exécuté : aucune suite n'a tourné sur ce commit.

Référence : fiche `docs/audit/audits/02-ddd.md`, barème `docs/audit/master.md` §2, §3, §5.
Méthode : lecture statique de l'arbre de travail, `rg`/`grep`, `git show` / `git diff a12b744 efc0bc5`. Ni application, ni tests, ni lint, ni build lancés. Commits lus en priorité : `4939413` (analyse courante, agrégat `DocumentAnalysisState`), `d3059c6` (règles d'édition, de chunks et de titres dans `domain/`), `8a60cee` (`domain/document_tree.py`), `efc0bc5` (`LLMProviderType` supprimé). Même grille de lecture que le contrôle, pour que les scores se comparent.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 14 / 17 |
| Score | 89 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 13 |
| Écarts INFO | 12 |

Score = (32 / 36) × 100 = 88,9 → **89**. Items non conformes : 2.3.1 (poids 2), 2.2.4 (1), 2.3.3 (1).

**Lecture appliquée pour 2.3.1** (stricte, celle du contrôle) : l'item reste non conforme. « Quelle analyse » est unifié côté backend, mais le vocabulaire ne l'est pas : « active » et « courante » désignent tantôt la même analyse, tantôt deux contenus différents (texte édité ou d'origine), le front garde un repli à part, et l'homonymie « version » n'a pas bougé. **Lecture alternative** (le seul critère est « une seule règle pour choisir l'analyse », le reste en [MIN]) : 2.3.1 conforme, 34/36 → **94**.

Comme dans les audits précédents, plusieurs [MIN] et [INFO] sont des dégradations relevées sur des items conformes ; seuls 2.2.4 et 2.3.3 sont des items de poids 1 non conformes.

### Métriques de périmètre (`a12b744` → `efc0bc5`)

| Mesure | a12b744 | efc0bc5 |
|--------|---------|---------|
| Modules `document-parser/domain/*.py` | 27 | 29 (+`heading_tree.py`, +`document_tree.py`) |
| Dataclasses `frozen=True` dans `domain/` | 64 | 68 |
| Dataclasses mutables (`@dataclass` nu) dans `domain/` | 7 | 8 (+`DocumentAnalysisState`) |
| `Protocol` dans `domain/ports.py` | 32 | 32 (+`DocumentAnalysisStateRepository`, +`CurrentAnalysisReader` ; les deux anciens ports de la ligne d'état fusionnés) |
| Imports `docling` dans `domain/` + `services/` | 0 | 0 |
| `domain/models.py` | 314 l. | 436 l. |
| `job` hors `AnalysisJob` dans `api/` + `services/` | 147 | 149 |
| Classes `*Manager/Handler/Processor/Helper/Util` | 0 | 0 |
| Lecteurs qui choisissent eux-mêmes « la dernière analyse » (backend) | 7 | 0 |

---

## Évaluation item par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 2.1.1 | Contextes métier identifiés et isolés | 3 | OUI | Inchangés. L'arbre de document a son module de domaine (`domain/document_tree.py`), la poussée vers les stores son service (`services/chunk_push_service.py`). |
| 2.1.2 | Pas de god object partagé | 3 | OUI (INFO) | `models.py` passe de 314 à 436 lignes : l'agrégat d'état et la règle de l'analyse courante y entrent, dans le contexte « analyse ». À surveiller ([INFO]). |
| 2.1.3 | Frontières explicites (DTOs, contrats) | 2 | OUI (MIN) | Nouveaux ports typés (`domain/ports.py:197-230`). Restent `EditorSnapshot.job` forgée et des contrats en tuples ([MIN]). |
| 2.1.4 | Le frontend respecte les mêmes contextes | 2 | OUI (MIN) | La feature `document` appelle toujours `GET /analysis-editor` en direct (`frontend/src/features/document/api.ts:20-29`) ([MIN]). |
| 2.2.1 | Entités = identité + cycle de vie | 2 | OUI (MIN) | `EditorSnapshot` fabrique toujours un `AnalysisJob` `working:{doc}:{base}` (`services/analysis_edit_service.py:341`) ([MIN]). |
| 2.2.2 | Value objects immutables | 2 | OUI (MIN) | +4 dataclasses gelées. `SourceHop` toujours muté (`domain/source_map.py:203`) ([MIN]). |
| 2.2.3 | Pas de persistence dans les VO | 3 | OUI | L'agrégat n'a ni `save` ni SQL ; `mark_saved` remet seulement ses drapeaux à zéro. |
| 2.2.4 | Entités porteuses de comportement | 1 | **NON** | Réduit : la chaîne de hachage n'a plus qu'une définition (`domain/analysis_editing.py:152`, `:168`), utilisée par le service et le dépôt (`persistence/analysis_edit_repo.py:166`). Mais `EditStream` (`domain/analysis_editing.py:58-62`) reste un sac de quatre champs. Voir [MIN]. |
| 2.3.1 | Vocabulaire cohérent domain / services / API / frontend | 2 | **NON** | Une seule règle pour « quelle analyse » (`domain/models.py:193-209`), lue par tous les lecteurs backend. Restent : « active » / « courante » pour deux contenus, repli propre au front, « version » homonyme, docs MCP et docstrings d'API en retard. Voir [MAJ]. |
| 2.3.2 | Noms du domaine, pas génériques | 1 | OUI | `CurrentAnalysisResolver`, `DocumentAnalysisState`, `nest_by_heading`, `build_tree_nodes` : noms métier. 0 classe générique. |
| 2.3.3 | Statuts métier explicites | 1 | **NON** | Inchangé : `STATUS_PATH/READ/CITED` (`domain/source_map.py:44-46`), `STATUS_UNREAD` (`domain/source_bar.py:20`), `operation: str` (`services/analysis_edit_service.py:314`), `EditorElement.type: str` (`domain/analysis_editing.py:76`). |
| 2.4.1 | Chaque agrégat a une racine claire | 2 | OUI | L'état du document a maintenant sa racine : `DocumentAnalysisState` (`domain/models.py:102`). |
| 2.4.2 | Invariants protégés dans le domaine | 3 | OUI (MIN) | Les règles d'édition sur valeurs simples, de split/merge et de fraîcheur des chunks sont dans le domaine (`domain/chunk_editing.py`, `domain/analysis_editing.py`, `DocumentAnalysisState.are_chunks_stale` `domain/models.py:173`). « Analyse active terminée et du document » reste écrit hors domaine, à cinq endroits ([MIN]). |
| 2.4.3 | Modifications via la racine | 2 | **OUI** (MIN) | Bascule. Toute écriture de `document_analysis_state` passe par une méthode de l'agrégat (`select`, `clear_selection`, `record_chunk_source`, `clear_chunk_source`, `restore`) et par un seul module SQL (`persistence/document_analysis_repo.py:18-75`) ; `restore` et `rechunk` écrivent chunks et état dans une transaction (`persistence/chunk_repo.py:139-167`). Réserves : champs publics, écriture « à l'aveugle » dans `complete_and_select`, `save_state` sans appelant en production ([MIN]). |
| 2.5.1 | Repositories manipulent des entités | 2 | OUI (MIN) | Le dépôt d'état rend l'agrégat. `AnalysisJob` partiellement hydratée reconduite (`persistence/analysis_repo.py:13-31`) ([MIN]). |
| 2.5.2 | Anti-corruption HTTP (Pydantic → domaine) | 2 | OUI | Schémas de l'éditeur typés et fermés aux clés inconnues (`efc0bc5`) ; erreurs traduites en un point (`api/errors.py`). |
| 2.5.3 | Infra ne leake pas ses types vers services | 3 | OUI (MIN) | 0 import Docling dans `services/`. Le schéma JSON Docling lu dans le domaine s'étend (`domain/document_tree.py:77-139`) ([MIN]). |

---

## Écarts constatés

### [MAJ] « L'analyse courante » : une règle pour le choix, pas encore un vocabulaire (réduit)

- **Localisation** :
  - règle unique, conforme : `document-parser/domain/models.py:193-209` (`resolve_current_analysis_id`), `document-parser/services/current_analysis.py:35-78`, lue par l'éditeur (`services/analysis_edit_service.py:103`, `:163`, `:271`), l'arbre (`services/document_tree_service.py:70`), l'export (`services/export_service.py:133`), le rechunk (`services/chunk_service.py:317`), Ask (`services/reasoning_service.py:103`), MCP (`services/parse_loader.py:98`, `services/navigation_service.py:88`, `services/citation_service.py:198`) et la route document (`api/documents.py:104`) ;
  - **même mot, deux contenus** : `CurrentAnalysisReader.load_current_analysis` = texte d'origine (`domain/ports.py:228-230`) ; `ActiveAnalysisResultReader.load_active_result` = texte édité (`domain/ports.py:426-438`, `services/analysis_edit_service.py:100-105`) ; la doc utilisateur dit l'inverse en mots : « Ask reads the document's active analysis […] the original result » (`docs/user-guide.md:104`) ; `_resolve_original_analysis` rend le résultat édité quand l'éditeur est branché (`services/export_service.py:126-133`) ;
  - **repli propre au front** : `frontend/src/features/document/store.ts:16-24` (`pickWorkspaceVersion` → `versions[0]`), `:172`, `:206` (`doc.currentAnalysisId ?? version.analysisId`) ; homonyme `analysisStore.currentAnalysis` = l'analyse ouverte dans Studio (`frontend/src/features/analysis/store.ts:32`) ;
  - **docs et docstrings en retard** : `docs/mcp-server.md:154` (« `null` means not parsed yet ») ; `document-parser/api/document_chunks.py:163`, `:178` (« latest analysis », publié dans l'OpenAPI) ; `frontend/src/features/document/ui/DownloadDropdown.vue:63` (« instead of the latest one ») ; `docs/mcp-server.md` ne dit pas que MCP lit le texte d'origine ;
  - **homonymie « version »** inchangée : `version_id` = id d'analyse (`document-parser/services/parse_loader.py:46`, `domain/anchors.py`) vs `DocumentVersion` (`domain/models.py:416`).
- **Constat** : le cœur du MAJ du contrôle est traité. Sept lecteurs choisissaient eux-mêmes « la dernière analyse terminée » ; il n'y en a plus aucun, `find_latest_completed` et `find_latest_completed_by_document` sont supprimés, le seul repli (`find_latest_parsed_ids`) n'est appelé que par le résolveur. Le front lit la sélection du backend. Après une restauration, Studio, l'export, le chunking, Ask et MCP lisent la même analyse.
  Reste que « active » et « courante » désignent la même analyse dans le code et la doc, mais que les deux ports s'en servent pour distinguer le texte édité du texte d'origine. Un lecteur ne peut pas savoir, au nom, ce qu'il obtient. Le front ajoute un quatrième cas : sans analyse courante, il ouvre quand même l'analyse de la version la plus récente, que le backend déclare non courante (et qui peut avoir été supprimée).
- **Règle violée** : 2.3.1 (poids 2).
- **Remédiation (la moins chère)** : (1) renommer pour que le contenu soit dans le nom : `load_current_analysis` → `load_current_original`, `load_active_result` → `load_current_edited` (ports, service, trois appelants) et `_resolve_original_analysis` → `_resolve_default_analysis` ; (2) une phrase dans `docs/mcp-server.md` : MCP lit l'analyse courante du document, texte d'origine, `version_id = null` aussi quand l'analyse active a été supprimée ou n'a pas de parse ; (3) corriger les deux docstrings de `api/document_chunks.py` ; (4) dans `pickWorkspaceVersion`, ne plus charger d'analyse quand `currentAnalysisId` est `null`. Effort S. Le glossaire et l'homonymie « version » (contrat MCP public) peuvent attendre 0.8.0.

### [MIN] L'agrégat `DocumentAnalysisState` : bonne racine, encore ouvert (nouveau, item conforme)

- **Localisation** : `document-parser/domain/models.py:102-190` ; `document-parser/persistence/document_analysis_repo.py:50-106` ; `document-parser/persistence/analysis_repo.py:179-195` ; `document-parser/persistence/chunk_repo.py:139-167` ; `document-parser/domain/ports.py:208`.
- **Constat** :
  - *Invariants* : les méthodes portent le métier (`restore(version)`, `are_chunks_stale`) et la paire « source des chunks » ne se pose qu'à deux valeurs. Mais les quatre champs sont publics et mutables : `state.active_analysis_id = x` ne lève pas le drapeau et la modification est perdue sans erreur. `select(analysis_id)` prend un id nu et ne vérifie rien ; « terminée et du document » reste garanti par le trigger SQL et par les services. C'est plus qu'un enregistrement à setters, moins qu'une racine qui se défend.
  - *« Écrire seulement ce qui a changé »* : le mécanisme est sain pour ce qu'il vise. Sélection et source des chunks sont deux groupes de colonnes indépendants ; une analyse qui se termine pendant un rechunk garde sa sélection, le rechunk garde sa source (test `tests/test_document_analysis_repo.py:120-145`). Il ne protège pas deux écritures du même groupe (dernier qui écrit gagne, ce qui est le bon choix ici). Défaut : l'upsert de la source crée une ligne à sélection `NULL` quand le document n'en a pas, ce qui change le sens de l'état (voir la relecture, D1).
  - *Porte d'entrée* : `save_state` n'a aucun appelant en production ; les deux écritures réelles passent par le dépôt d'`AnalysisJob` et par le dépôt de chunks, qui appellent la fonction de module `write_document_analysis_state` sur leur connexion. Le SQL n'existe qu'une fois, ce qui était le but ; mais l'agrégat est écrit par deux dépôts qui ne sont pas le sien. `complete_and_select` crée un état vierge sans le charger : correct seulement grâce aux drapeaux.
  - *Les deux anciennes vues* : `DocumentAnalysisSelection` (`domain/models.py:89-92`) n'est plus lue qu'au travers de la propriété `selection`, que seuls les tests appellent. `DocumentChunkSource` sert à deux endroits (`services/version_service.py:111`, `services/analysis_edit_service.py:361`).
- **Règle violée** : 2.4.3 — conforme ; réserve.
- **Remédiation** : supprimer `DocumentAnalysisSelection` et la propriété `selection` ; remplacer les deux champs de source par un champ `chunk_source: DocumentChunkSource | None` (la paire devient un VO, l'invariant « les deux ou aucun » tient par construction) ; champs privés ou `__setattr__` gardé ; `select(analysis: AnalysisJob)` qui refuse une analyse étrangère ou non terminée. Effort S.

### [MIN] `EditStream` reste anémique (réduit, item non conforme)

- **Localisation** : `document-parser/domain/analysis_editing.py:58-62` ; règles en fonctions libres `domain/analysis_editing.py:152-180` ; séquence `services/analysis_edit_service.py:154-155`, `:183`.
- **Constat** : la double chaîne de hachage du contrôle est résolue (`d3059c6`) : une seule `hash_command`, une seule `hash_command_stream`, les mêmes octets. Mais l'entité n'a toujours aucune méthode ; séquence attendue et chaîne vivent à côté d'elle.
- **Règle violée** : 2.2.4 (poids 1).
- **Remédiation** : `EditStream.append(commands, expected_sequence)` et `EditStream.accepts_base(hash)`.

### [MIN] Statuts et genres du contexte navigation en chaînes nues (inchangé, item non conforme)

- **Localisation** : `document-parser/domain/source_map.py:44-48` ; `document-parser/domain/source_bar.py:20-22` ; `document-parser/services/analysis_edit_service.py:314` ; `document-parser/domain/analysis_editing.py:76`, `:89`.
- **Règle violée** : 2.3.3 (poids 1).
- **Remédiation** : `SourceStatus`, `OutlineNodeKind` ; `Literal["preview", "save", "replay"]`.

### [MIN] « Historique » nomme trois concepts (inchangé)

- **Localisation** : `frontend/src/features/history/api.ts:3-4` ; `document-parser/domain/analysis_editing.py` (`EditHistoryEntry`) ; `frontend/src/pages/DocIngestTab.logic.ts` (`toHistoryEntry`).
- **Règle violée** : 2.3.1 — dégradation.

### [MIN] Invariant de sélection hors du domaine (réduit)

- **Localisation** : « analyse active terminée et du document » : `document-parser/persistence/database.py:96-114` (trigger, appartenance seulement), `document-parser/persistence/analysis_repo.py:185-186`, `document-parser/services/version_service.py:163-172`, `document-parser/services/analysis_edit_service.py:266-278`, `document-parser/services/current_analysis.py:76`.
- **Constat** : les règles d'édition sur valeurs simples ont quitté l'adaptateur Docling pour le domaine (`d3059c6`), split/merge aussi. La règle de sélection, elle, est toujours écrite cinq fois, et `DocumentAnalysisState.select` ne la porte pas.
- **Règle violée** : 2.4.2 — conforme ; dégradation.
- **Remédiation** : celle du MIN sur l'agrégat (`select(analysis)` validant).

### [MIN] `EditorSnapshot` fabrique un `AnalysisJob` à identité forgée (inchangé)

- **Localisation** : `document-parser/services/analysis_edit_service.py:341` ; `document-parser/domain/analysis_editing.py:126-132` ; `document-parser/domain/ports.py:426-433`.
- **Règle violée** : 2.2.1 — conforme ; dégradation.

### [MIN] La feature `document` rappelle l'endpoint de l'éditeur (inchangé)

- **Localisation** : `frontend/src/features/document/api.ts:20-29`, `frontend/src/features/document/store.ts:44`.
- **Règle violée** : 2.1.4 — conforme ; dégradation.

### [MIN] « Document introuvable » : six classes (inchangé, une déplacée)

- **Localisation** : `document-parser/services/chunk_errors.py:30`, `document-parser/services/navigation_errors.py:21`, `document-parser/services/preview_service.py:27`, `document-parser/services/analysis_service.py:59`, `document-parser/services/export_service.py:162`, `document-parser/domain/analysis_editing.py:199`.
- **Constat** : la classe de `chunk_service.py` a déménagé dans `chunk_errors.py` (`8a60cee`) ; le nombre ne change pas.
- **Règle violée** : 2.3.1 / 2.1.3 — dégradation.

### [MIN] Le schéma JSON Docling est lu dans le domaine (aggravé)

- **Localisation** : `document-parser/domain/document_tree.py:20`, `:77-139` (`body`, `children`, `self_ref`, `form_area`, `key_value_area`) ; `document-parser/domain/parse_index.py` ; `document-parser/domain/element_reader.py`.
- **Constat** : la projection d'arbre a quitté le service pour le domaine (`8a60cee`), avec sa lecture directe du JSON Docling et une sortie `list[dict]`. Le port `DocumentTreeReader` n'en couvre qu'une partie. La garde d'architecture n'interdit toujours pas Docling au domaine.
- **Règle violée** : 2.5.3 — conforme ; dégradation.

### [MIN] Règles cœur du contexte citation dans les services (inchangé)

- **Localisation** : `document-parser/services/citation_service.py`, `document-parser/services/navigation_service.py`.

### [MIN] Un value object est muté après construction (inchangé)

- **Localisation** : `document-parser/domain/source_map.py:203`.

### [MIN] `AnalysisJob` partiellement hydratée (inchangé)

- **Localisation** : `document-parser/persistence/analysis_repo.py:13-31`, `:42-47`.

### [MIN] Contrats inter-couches en tuples (inchangé)

- **Localisation** : `document-parser/services/document_service.py:136-138` ; `document-parser/services/source_service.py`.

### [INFO] Dépôt sans document : la source des chunks crée une ligne à sélection vide (nouveau)

- **Localisation** : `document-parser/persistence/document_analysis_repo.py:29-34`. Détail en relecture, D1.

### [INFO] Une erreur d'intégrité de l'état remonte en 500 (nouveau)

- **Localisation** : `document-parser/services/version_service.py:155-158`, `document-parser/persistence/database.py:96-114`. Détail en relecture, D3.

### [INFO] Repli du résolveur et rattrapage 0.7.3 ne choisissent pas tout à fait pareil (nouveau)

- **Localisation** : `document-parser/persistence/analysis_repo.py:129-136` (exige un parse, ordre `completed_at` seul) vs `document-parser/persistence/database.py:300-311` (préfère un parse, accepte sans, départage par `created_at`).
- **Constat** : sans conséquence tant que le rattrapage tourne à chaque démarrage (il le fait, `database.py:282`) : un document sans ligne n'a alors aucune analyse terminée. À aligner pour qu'il n'y ait qu'une définition du repli.

### [INFO] `models.py` grossit (élargi)

- **Localisation** : `document-parser/domain/models.py` (314 → 436 l.).

### [INFO] `hash_result` vit dans le module de l'éditeur (réduit)

- **Localisation** : `document-parser/domain/analysis_editing.py:134`.
- **Constat** : la règle de fraîcheur a rejoint l'agrégat (`DocumentAnalysisState.are_chunks_stale`) : la moitié du point est résolue. Le hash reste importé du module d'édition par le contexte chunks.

### [INFO] Inchangés

`PreviewImageKey` technique dans `domain/ports.py:186` ; statut HTTP porté par les erreurs de service (`services/errors.py:11-19`) ; ports « service vers service » (`DocumentFileLocator`) ; immutabilité superficielle des VO de l'éditeur ; `GraphPayload` mutable (`domain/value_objects.py:257`) ; import Docling absent du modèle ; garde d'architecture sans Docling pour le domaine (`tests/test_architecture.py:183`) ; enum du domaine publiée dans le contrat MCP.

---

## Points positifs

- Une règle, un résolveur, un port : plus aucun lecteur ne choisit « la dernière analyse » de son côté. Le repli n'a plus qu'un appelant (`services/current_analysis.py:46`), et le port le dit (`domain/ports.py:381-383`).
- La distinction « ligne absente » / « sélection NULL » est écrite dans le domaine et documentée (`domain/models.py:197-206`), et les `UPDATE` de remise à zéro ne créent pas de ligne (`persistence/document_analysis_repo.py:23-27`).
- `restore` et `rechunk` sont atomiques : chunks et état dans une seule transaction (`persistence/chunk_repo.py:156-166`). Le défaut « chunks restaurés avec l'ancienne sélection » du contrôle n'existe plus.
- Le SQL de l'état n'existe qu'une fois ; les placeholders correspondent aux paramètres sur toutes les requêtes relues.
- Chaîne de hachage, règles de split/merge, règles d'édition sur valeurs et imbrication par titres sont énoncées une seule fois, dans le domaine.
- `LLMProviderType`, enum à un seul membre, a disparu (`efc0bc5`).
- Choix produit et effets utilisateur écrits dans le message de commit, le CHANGELOG et `docs/user-guide.md:104`.

---

## Delta vs contrôle

**Score** : 83 → **89** (+6). Items conformes : 13/17 → 14/17. Écarts : 0 CRIT / 2 MAJ / 12 MIN / 11 INFO → **0 CRIT / 1 MAJ / 13 MIN / 12 INFO**. 2.4.3 bascule en conforme ; 2.3.1 reste non conforme sous la lecture stricte (94 sous la lecture alternative).

| Écart du contrôle | Statut sur efc0bc5 | Preuve |
|-------------------|--------------------|--------|
| [MAJ] 2.3.1 Trois définitions de l'analyse courante | **Réduit** : une règle backend ; restent synonymes à deux contenus, repli front, docs, « version » | `domain/models.py:193`, `services/current_analysis.py:35` ; `domain/ports.py:228`, `:432` ; `document/store.ts:23`, `:172` |
| [MAJ] 2.4.3 État document sans racine | **Résolu** (reste un [MIN] de conception) | `domain/models.py:102-190`, `persistence/document_analysis_repo.py:50`, `persistence/chunk_repo.py:139` |
| [MIN] 2.2.4 `EditStream` anémique, chaîne en double | **Réduit** : chaîne unique ; entité toujours vide | `domain/analysis_editing.py:152`, `persistence/analysis_edit_repo.py:166` ; `:58-62` |
| [MIN] 2.3.3 Statuts en chaînes nues | **Inchangé** | `domain/source_map.py:44-46` |
| [MIN] « Historique » ×3 | **Inchangé** | `frontend/src/features/history/api.ts:3-4` |
| [MIN] Invariants hors domaine | **Réduit** : règles d'édition et de chunks dans le domaine ; sélection ×5 | `domain/chunk_editing.py` ; `services/version_service.py:163` |
| [MIN] `EditorSnapshot` forgée | **Inchangé** | `services/analysis_edit_service.py:341` |
| [MIN] Front `document` → éditeur | **Inchangé** | `frontend/src/features/document/api.ts:20-29` |
| [MIN] « Document introuvable » ×6 | **Inchangé** (une classe déplacée) | `services/chunk_errors.py:30` |
| [MIN] Schéma Docling dans le domaine | **Aggravé** | `domain/document_tree.py:77-139` |
| [MIN] Règles de citation dans les services | **Inchangé** | — |
| [MIN] `SourceHop` muté | **Inchangé** | `domain/source_map.py:203` |
| [MIN] `AnalysisJob` partiellement hydratée | **Inchangé** | `persistence/analysis_repo.py:13-31` |
| [MIN] Contrats en tuples | **Inchangé** | `services/document_service.py:136-138` |
| [INFO] `hash_result` / fraîcheur dans le service | **Réduit** : fraîcheur dans l'agrégat | `domain/models.py:173` |
| [INFO] ×10 autres | Inchangés ; `models.py` élargi | |

**Les cinq régressions attribuées à la première remédiation** :

| Régression | Statut | Preuve |
|------------|--------|--------|
| 1. `ImportDocumentNotFoundError`, sixième classe | **Inchangé** | `services/analysis_service.py:59` |
| 2. Alias `fetchHistory` / `deleteHistoryEntry` | **Inchangé** | `frontend/src/features/history/api.ts:3-4` |
| 3. `EditorSnapshot` forgée publiée par un port | **Inchangé** | `domain/analysis_editing.py:126`, `domain/ports.py:433` |
| 4. Deux `_hash_command` homonymes | **Résolu** | une seule `hash_command`, `domain/analysis_editing.py:152` |
| 5. `find_with_store_links` renvoie un tuple | **Inchangé** | `services/document_service.py:136-138` |

**Nouveaux écarts** : [MIN] agrégat ouvert ; [INFO] ligne créée par la source des chunks ; [INFO] intégrité en 500 ; [INFO] repli vs rattrapage. Aucun ne fait basculer un item.

**Décompte des définitions de « l'analyse courante »** (choix de l'analyse) :

| Où | Définition | Compte |
|----|-----------|--------|
| Backend (10 lecteurs + route document) | `resolve_current_analysis_id` : sélection, ou dernière analyse avec parse si aucune ligne | **1** |
| Front, workspace | la même via `currentAnalysisId`, **plus** un repli sur `versions[0]` quand elle est `null` | 1 + 1 cas limite |
| Front, Studio | `analysisStore.currentAnalysis` = analyse ouverte (homonyme, autre concept) | homonyme |
| `docs/user-guide.md:104` | « la plus récente, jusqu'à une restauration » : conforme à la règle | 1 (cohérente) |
| `docs/analysis-editor.md:65`, `:82` | « active analysis » : conforme | 1 (cohérente) |
| `docs/mcp-server.md:154`, `:216` | « current » non défini, `null` = « pas encore parsé » : incomplet | 1 (incomplète) |

Contenu lu (avec ou sans éditions) : **2 réponses** selon le lecteur — édité pour Studio, l'arbre, l'export par défaut et le rechunk ; d'origine pour Ask et MCP.

---

## Relecture avant première exécution

Fichiers relus ligne à ligne : `domain/models.py`, `domain/ports.py`, `persistence/document_analysis_repo.py`, `persistence/analysis_repo.py`, `persistence/chunk_repo.py`, `services/current_analysis.py`, `services/version_service.py`, `services/chunk_service.py`, `services/reasoning_service.py`, `services/parse_loader.py`, confrontés au schéma de `persistence/database.py` et au câblage (`bootstrap/builder.py`, `bootstrap/factories.py`, `mcp_stdio.py`).

**Rien de bloquant trouvé.** Vérifié sans écart :

- Tables et colonnes : `document_analysis_state(document_id, active_analysis_id, chunks_source_analysis_id, chunks_source_result_hash)` correspond au SQL et à `_row_to_state` (ordre positionnel correct). `ON CONFLICT(document_id)` s'appuie sur la clé primaire.
- Placeholders / paramètres : sélection 2/2, remise à zéro 1/1, source 3/3, remise à zéro source 1/1, soft-delete 3/3, insertion de chunk 12/12, `IN (...)` construits sur la liste passée.
- Transactions : `complete_and_select` et `replace_for_document` font toutes leurs écritures sur une connexion, `commit` en dernier ; une exception ferme la connexion sans commit, donc annule. Pas d'usage de connexion après fermeture ; `mark_saved` est appelé après le `with`, hors connexion, ce qui est voulu.
- Triggers : l'upsert de sélection déclenche `validate_update` (colonne `active_analysis_id` dans le `SET`) ; l'upsert de source insère `active_analysis_id` NULL, le trigger d'insertion ne se déclenche pas.
- Drapeaux de l'agrégat : `field(init=False)` après des champs à défaut est valide ; aucune méthode ne perd une mise à jour ; deux vues chargées du même état ne s'écrasent pas (sélection d'un côté, source de l'autre).
- Câblage : signatures des constructeurs (`AnalysisEditService`, `ChunkService`, `ExportService`, `DocumentService`, `DocumentTreeService`, `ReasoningService`, `ParseLoader`) cohérentes avec `builder.py`, `factories.py` et `mcp_stdio.py`. Aucune référence restante aux méthodes supprimées, ni dans le code ni dans les tests.

**Résolveur, scénario par scénario** :

| Scénario | Résultat | Correct ? |
|----------|----------|-----------|
| Une analyse terminée | ligne posée par `complete_and_select` → cette analyse | oui |
| Deux terminées, la plus ancienne restaurée | ligne → l'ancienne, pour l'éditeur, l'export, le rechunk, Ask et MCP | oui |
| Une plus récente en cours | la ligne ne bouge pas tant qu'elle n'est pas terminée ; à la fin, `complete_and_select` la sélectionne et remplace la restauration | oui (documenté : « la plus récente, jusqu'à une restauration ») |
| Analyse importée | `import_docling_document` → `_finalize_analysis` → `complete_and_select` : sélectionnée | oui |
| Aucune analyse | pas de ligne, repli vide → `None` | oui |
| Ligne à sélection NULL | `None`, sans repli, pour tous | conforme à la règle ; voir l'avis sur le choix produit |
| Pas de ligne, analyse terminée avec parse | repli sur la plus récente avec parse | oui, mais voir D1 |
| Analyse active sans parse | éditeur/arbre/rechunk : 409 ; Ask : 404 ; MCP : `version_id = null` même s'il existe un parse plus ancien | conforme au choix annoncé |

**Défauts probables** :

**D1 — Le premier rechunk d'un document sans ligne d'état lui retire son analyse courante.** PLAUSIBLE, portée faible.
- `document-parser/persistence/document_analysis_repo.py:29-34`, appelé depuis `document-parser/services/chunk_service.py:346-349` (et `services/version_service.py:182-186`).
- Scénario : un document n'a pas de ligne d'état (cas que le résolveur prévoit, `domain/models.py:200-203`) ; le résolveur rend la dernière analyse avec parse ; le rechunk enregistre sa source par upsert, qui insère une ligne avec `active_analysis_id = NULL`. Dès l'appel suivant, la règle lit « sélection NULL = pas d'analyse courante » : éditeur, Ask, MCP et workspace perdent l'analyse que le rechunk vient d'utiliser. Même effet pour `restore` d'une version qui porte une source de chunks. Aujourd'hui difficile à atteindre, car le rattrapage au démarrage crée une ligne pour tout document qui a une analyse terminée et `complete_and_select` en crée une à chaque fin d'analyse ; mais c'est exactement le cas que le repli existe pour couvrir.
- Correction : dans `rechunk_document`, quand `find_state` rend `None`, partir de `DocumentAnalysisState(document_id)` puis `state.select(source_analysis_id)` avant `record_chunk_source` (la ligne créée porte l'analyse que le repli désignait). Mieux, une fabrique unique `DocumentAnalysisState.load_or_adopt(state, fallback_id)` utilisée par le rechunk et la restauration.

**D2 — Restaurer une version sans analyse sur un document sans ligne : le résultat dépend de la présence d'une source de chunks.** PLAUSIBLE, portée très faible.
- `document-parser/domain/models.py:158-171`, `document-parser/persistence/document_analysis_repo.py:59-75`.
- Scénario : `clear_selection` émet un `UPDATE` sans effet (pas de ligne) ; si la version n'a pas de source, rien n'est créé et le repli continue de s'appliquer ; si elle en a une, l'upsert crée une ligne NULL et le document n'a plus d'analyse courante. Deux issues pour la même intention « pas d'analyse ».
- Correction : la même que D1 ; ou faire créer la ligne par `clear_selection` quand il n'y en a pas (`INSERT … ON CONFLICT DO UPDATE SET active_analysis_id = NULL`), si « restaurer une version sans analyse » doit vraiment vouloir dire « aucune analyse courante ».

**D3 — Une analyse supprimée entre la vérification et l'écriture de `restore` répond 500, pas 409.** PROBABLE sur ce chemin, rare.
- `document-parser/services/version_service.py:163-186` ; trigger `document-parser/persistence/database.py:96-114`.
- Scénario : la docstring l'annonce (« fails the state trigger and rolls back »). Le rollback a bien lieu, mais l'`IntegrityError` d'aiosqlite n'est pas une `ServiceError` : la route renvoie 500 au lieu du 409 que le même cas reçoit quand il est détecté avant.
- Correction : dans `replace_for_document` (ou `restore`), attraper `sqlite3.IntegrityError` et lever `VersionServiceError("Version analysis is no longer available", http_status=409)`, via une erreur de domaine si l'on veut garder la persistance sans dépendance aux services.

**D4 — Le workspace ouvre une analyse que le backend déclare non courante, ou supprimée.** PROBABLE, comportement (pas un crash serveur).
- `frontend/src/features/document/store.ts:16-24`, `:170-174`, `:203-207`.
- Scénario : l'utilisateur supprime l'analyse active ; la clé étrangère passe la sélection à NULL ; `currentAnalysisId` vaut `null` ; le front prend `versions[0].analysisId`, qui est souvent l'analyse supprimée (les versions gardent leur pointeur), et `fetchAnalysis` échoue → « Failed to load workspace ». Si l'analyse existe encore, le Parse affiche une analyse qu'Ask et MCP refusent de lire.
- Correction : quand `currentAnalysisId` est `null`, épingler la version la plus récente pour l'historique mais ne charger aucune analyse, et afficher « Aucune analyse active ». Côté backend, voir l'avis ci-dessous sur la suppression.

**D5 — Une version à moitié renseignée ferait échouer `restore` en 500.** IMPROBABLE.
- `document-parser/domain/models.py:164-171` ; CHECK `document-parser/persistence/database.py:93`.
- Scénario : sur une base montée depuis 0.7.3, `document_versions` n'a pas le CHECK ; une ligne avec `chunks_source_analysis_id` mais sans hash passerait `None` à `record_chunk_source` (le type l'interdit, rien ne le vérifie) et le CHECK de `document_analysis_state` refuserait l'écriture. Le seul écrivain des versions pose les deux colonnes ensemble, d'où IMPROBABLE.
- Correction : dans `restore`, ne prendre la source que si les deux colonnes sont présentes (sinon `clear_chunk_source`).

Non vérifié (lecture seule) : l'exécution réelle de ces chemins, le comportement de l'upsert et des triggers sur la version de SQLite embarquée, et la suite `tests/test_current_analysis.py` (222 lignes) qui couvre la règle mais n'a pas tourné.

---

## Verdict partiel : GO

Score 89 ≥ 80, 0 CRIT, 1 MAJ (seuil bloquant : > 3). La seconde remédiation fait ce qu'elle annonçait sur ce périmètre : une seule règle pour l'analyse courante, lue par tous les lecteurs backend, et un agrégat qui porte l'état du document avec des écritures atomiques. Le MAJ restant tient au vocabulaire, pas au comportement, et se corrige à l'effort S (renommage de deux méthodes de port, une phrase de doc MCP, deux docstrings, le repli du front). Aucun défaut bloquant à la relecture ; D3 et D4 méritent d'être corrigés avant la sortie, D1 et D2 avant 0.8.0. Ce verdict suppose que les suites passent : rien n'a tourné sur `efc0bc5`.
