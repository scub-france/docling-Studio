# Rapport d'audit : Performance & Ressources

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `efc0bc5`, lu dans l'arbre de travail.
**Nature** : Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18 (`release-0.7.4-control/12-performance.md`, `a12b744` : 95/100, 12/13 items, 0 CRIT, 0 MAJ, 3 MIN, 11 INFO).

Code non exécuté, aucune mesure : coûts estimés à la lecture.

Méthode : lecture du code à `efc0bc5`, `git diff a12b744 efc0bc5` sur les fichiers touchés,
lecture de FastAPI 0.136.1, pydantic 2.13.4 et aiosqlite 0.22.1 installés dans
`document-parser/.venv` (lecture seule, rien importé). Aucune application lancée, aucun test,
aucun chronométrage. Les chiffres « mesuré » cités viennent des rapports précédents ; tous les
autres sont des **estimations** (ordre de grandeur), document de référence : 300 pages,
environ 15 000 à 20 000 éléments, `document_json` de quelques Mo.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 95 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 4 |
| Écarts INFO | 15 |

### Détail par item

| # | Item | Poids | Conforme | Justification (arbre à `efc0bc5`) |
|---|------|-------|----------|---------------|
| 12.1.1 | Pas de requête N+1 | 2 | Oui | Le résolveur d'analyse courante est groupé : `IN (...)` sur les états puis, seulement pour les documents sans ligne d'état, sur les analyses (`services/current_analysis.py:35-53`, `persistence/document_analysis_repo.py:90-99`, `persistence/analysis_repo.py:118-139,151-162`). Le listage MCP lui passe au plus 50 ids (`services/navigation_service.py:82`, `navigation_config.py:34`), loin des 999 / 32 766 variables de SQLite. Remplacement des chunks en un `executemany` (`persistence/chunk_repo.py:160-161`). `show_sources` reste en MIN, un peu aggravé (voir écart). |
| 12.1.2 | Fichiers temporaires supprimés | 2 | Oui | Refus au comptage de pages → `discard` en thread (`services/document_service.py:113`). |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` respectée | 2 | Oui | `bootstrap/factories.py:209` → sémaphore `services/analysis_service.py:102`, pris à `:434`. |
| 12.1.4 | Opérations longues hors event loop | 3 | Oui | Conversion (`infra/local_converter.py:201,204`), projection et rejeu (`services/analysis_edit_service.py:291,318`), tailles de page et rendu (`services/preview_service.py:107,112`), empreinte du fichier (`:90`), écriture + comptage d'upload en un seul `to_thread` (`services/document_service.py:108-110`), comptage pour le batching (`services/analysis_service.py:456`). La validation typée de la réponse de l'éditeur ajoute du CPU sur la loop : écart MIN séparé, pas une opération longue au sens de l'item. |
| 12.1.5 | Pas de fichier entier en mémoire | 2 | Oui | PDF ouvert par chemin (`infra/pdf_inspector.py:31,46`, `infra/page_raster.py`). Le middleware de taille ne garde en mémoire que ce que Starlette aurait lu de toute façon, et seulement sur `/api/analyses/import` (`infra/body_limit.py:36-63`, `main.py:95-101`). |
| 12.2.1 | Watchers avec cleanup | 2 | Oui | Aucun nouveau `watch` ni observer ; `BboxCanvas.vue:296-310` inchangé sur ce point. |
| 12.2.2 | Listeners retirés au démontage | 2 | Oui | `AnalysisEditor.vue:420-424` (clavier, `beforeunload`, `cancelPreview`). |
| 12.2.3 | Annulation / debounce | 1 | Oui | Planificateur extrait (`features/analysis-editor/previewScheduler.ts:23-57`) : même délai de 400 ms, un seul minuteur, `AbortController` remplacé à chaque requête, `cancel()` vide le minuteur, annule et oublie le contrôleur, si bien qu'une réponse tardive est ignorée (`store.ts:209-228`). Équivalent à l'ancien code. |
| 12.2.4 | Pas de re-render excessif | 1 | Oui | L'historique et les bandeaux sont devenus des composants enfants (`AnalysisEditHistoryPanel.vue`, `EditorBanners.vue`) : une frappe dans le panneau d'édition ne re-rend plus la liste de l'historique (amélioration). |
| 12.2.5 | Assets lourds optimisés | 1 | Oui | `frontend/public` inchangé depuis le contrôle. |
| 12.3.1 | Cache nginx des statiques | 1 | Oui | Templates nginx inchangés depuis le contrôle. |
| 12.3.2 | Réponses API de taille raisonnable | 1 | **Non** | Réponse de l'éditeur toujours complète (modèle + arbre + résultat, `api/schemas.py:281-291`), toujours chargée par le workspace pour n'en lire que `result` (`features/document/store.ts:41-51`, `api.ts:20-28`). Partiellement réduit : le comptage d'analyses de la bibliothèque passe par les résumés (`pages/DocsLibraryPage.vue:345`). |
| 12.3.3 | Health check léger | 1 | Oui | `SELECT 1` (`main.py:148-155`). |

Poids total = 21. Non conforme : 12.3.2 (1). Poids conformes = 20.
`20 / 21 * 100 = 95,2` → **95 / 100**.

---

## Écarts constatés

### [MIN] Validation typée de la réponse de l'éditeur sur l'event loop (nouveau, régression estimée)

- **Localisation** : `document-parser/api/analysis_edits.py:58-70` (`AnalysisEditorModelResponse.model_validate(...)` à `:62`, `_to_tree_node_response` récursif à `:49-55`) ; modèles `api/schemas.py:228-291` ; appelé par `GET /analysis-editor`, `POST /analysis-edits/preview`, `PATCH /analysis-edits/history/{n}` et `POST /analysis-edits/rebuild`.
- **Constat** : avant `efc0bc5`, la route faisait `json.loads` du modèle et renvoyait un `dict` (`model: dict`, `tree: list[dict]`). Elle construit désormais un objet pydantic par élément, par provenance et par nœud d'arbre, sur l'event loop. FastAPI 0.136.1 ne revalide pas l'instance renvoyée (`fastapi/_compat/v2.py:173-185`, `revalidate_instances` par défaut à `never`) et sérialise en Rust par `dump_json` (`fastapi/routing.py:687-712`) : le surcoût est donc la construction des objets, pas la sérialisation. Estimation : 2 à 5 µs par élément (12 champs, provenance en sous-modèle, tuple de 4 flottants, liste de `Literal`) et 2 à 3 µs par nœud (constructeur pydantic appelé depuis Python), soit **+60 à +150 ms par réponse à 300 pages**, qui s'ajoutent aux 115 ms mesurées au re-audit pour l'ancien chemin. Chaque pause de frappe dans l'éditeur (aperçu à 400 ms) et chaque ouverture ou rechargement du workspace (qui appelle cette route) bloque donc la loop de l'ordre de 0,2 s au lieu de 0,1 s (**estimé**). `extra="forbid"` coûte peu ; c'est le nombre d'objets qui compte.
- **Règle violée** : hors checklist (rattaché à 12.1.4, sans faire tomber l'item : il vise les opérations longues).
- **Remédiation** : garder le contrat dans les tests seulement, et à l'exécution insérer `editor_model_json` tel quel dans la réponse (le JSON est déjà produit par le projecteur) ; à défaut, `model_construct` sans validation, ou construire la réponse dans le `to_thread` de la projection. L'arbre peut aussi être sérialisé une fois dans le thread. Effort S.

### [MIN] Réponses de l'éditeur volumineuses ; double chargement au workspace — réduit en partie (item 12.3.2)

- **Localisation** : `document-parser/api/schemas.py:281-291` ; `frontend/src/features/document/store.ts:41-51,155-181,195-215` ; `frontend/src/pages/DocsLibraryPage.vue:345` → `features/analysis/api.ts:64-68` → `api/analyses.py:107-123`.
- **Constat** : la taille ne change pas (13,76 Mo à 300 pages, mesuré au re-audit sur un code équivalent). L'ouverture du workspace fait toujours 4 requêtes, dont 2 lourdes et en série (`GET /api/analyses/{id}` complet, puis `GET /analysis-editor` complet pour n'en garder que `result`). `reloadWorkspaceVersions` ajoute un `GET /api/documents/{id}` (3 → 4 requêtes) ; il part en parallèle des versions et ne coûte que 3 à 5 requêtes SQL légères. Réduction réelle : la boîte de suppression de la bibliothèque compte les analyses par `/summaries?documentId=` au lieu de télécharger toutes les analyses avec leur contenu.
- **Règle violée** : 12.3.2 (poids 1).
- **Remédiation** : endpoint « résultat actif » léger (ou `?view=result`) pour le workspace ; ne charger `fetchAnalysis` complet que si l'éditeur est désactivé ; compteur d'analyses en `COUNT(*)`. Effort M.

### [MIN] `show_sources` refait la résolution pour chaque citation — aggravé (hors checklist)

- **Localisation** : `document-parser/services/source_service.py:102` → `:185` (`verify_citation` par citation) → `services/citation_service.py:138,196-199` → `services/current_analysis.py:58-68`.
- **Constat** : la recherche d'une parse plus récente passait par une requête (`find_latest_parsed_ids`) ; elle passe maintenant par le résolveur : états, éventuel repli, puis `find_parsed_ids`, soit 2 à 3 requêtes. Une vérification de citation passe de 3-4 à 4-6 requêtes, chacune sur sa propre connexion ; avec le plafond de 50 ancres (`navigation_config.py:60`), un `show_sources` passe d'environ 200 à environ 300 requêtes, soit de l'ordre de 0,1 à 0,3 s de plus (**estimé**, 0,5 à 1 ms par connexion aiosqlite : thread, ouverture, `PRAGMA`, requête, fermeture).
- **Remédiation** : résoudre la parse courante une fois par appel (un seul `find_current_parse_ids` pour le document épinglé) et la passer aux vérifications ; ouvrir le PDF une fois pour toutes les pages lues. Effort S.

### [MIN] Suivi des analyses à 3 s sans plafond de durée — inchangé (hors checklist)

- **Localisation** : `frontend/src/features/analysis/store.ts:171-182` (`followActive`).
- **Constat** : inchangé. Voir aussi l'INFO sur les pages de débordement : chaque tick lit jusqu'à 200 lignes d'`analysis_jobs`.
- **Remédiation** : plafond de durée, comme le polling unitaire. Effort S.

### [INFO] Verrou pdfium partagé avec Docling — réduit

- **Localisation** : `document-parser/infra/pdf_inspector.py:27-42`.
- **Constat** : `read_page_sizes` lit les tailles par `pdf.get_page_size(index)` sans charger les pages (`8436e27`) : le maintien du verrou à 300 pages passe de 106 ms à 2,6 ms (chiffres **mesurés** au contrôle sur un document synthétique). Le reste de l'INFO du contrôle (attentes bornées derrière un appel Docling, thread Docling abandonné tenant le verrou) est inchangé.

### [INFO] `index.html` sans en-tête de cache explicite — inchangé

- **Localisation** : `nginx.conf.template:19-21`, `frontend/nginx.conf.template:19-21`.

### [INFO] Logo encore surdimensionné ; `favicon.svg` non référencé — inchangé

- **Localisation** : `frontend/public/logo.png`, `frontend/index.html:7`.

### [INFO] Reliquat de CPU sur l'event loop hors éditeur — légèrement aggravé

- **Localisation** : arbre `services/document_tree_service.py:73-78` (`json.loads` + `build_tree_nodes` sur la loop, 67 ms mesurés au re-audit) ; empreintes `services/analysis_edit_service.py:78,226,365,381`, `services/chunk_service.py:345` ; paramètres d'insertion des chunks `persistence/chunk_repo.py:161` ; restauration `services/version_service.py:174-177`.
- **Constat** : l'arbre passe par `nest_by_heading` (voir INFO dédiée), quelques ms à quelques dizaines de ms de plus à 300 pages (**estimé**). `_has_stale_chunks` calcule maintenant le SHA-256 du résultat même quand aucune source de chunks n'est enregistrée (`:365`, l'ancien code ne le faisait que s'il y en avait une) : un hachage inutile de plus par chargement, aperçu ou sauvegarde, 2,6 ms à 300 pages (mesuré au re-audit). La construction des paramètres de chunks (`json.dumps` par chunk) reste sur la loop, comme avant.
- **Suggestion** : `hash_result` paresseux (seulement si `chunks_source_analysis_id` existe) ; `build_tree_nodes` en `to_thread`.

### [INFO] Projections parallèles non bornées, pool de threads partagé, GIL — inchangé

- **Localisation** : `services/analysis_edit_service.py` (pas de sémaphore) ; exécuteur par défaut.

### [INFO] Cache mono-slot `_unedited_projection` partagé entre documents — inchangé

- **Localisation** : `services/analysis_edit_service.py:69,79,97`.

### [INFO] Cache de previews sans coalescence des requêtes — inchangé

- **Localisation** : `services/preview_service.py:91-96`.

### [INFO] PDF.js : un document par visionneuse — inchangé

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.ts`.

### [INFO] Coûts quadratiques du rejeu — confirmés et chiffrés ; borne de requête sans effet sur le pire cas

- **Localisation** : `document-parser/infra/docling_editor.py:150-173` (`_delete_elements`), `:233-253` (`_gather_merge_run`), `:349-355` (`_is_descendant`) ; borne `api/schemas.py:162,200-202` (`MAX_ELEMENT_IDS = 100_000`).
- **Constat** : code inchangé depuis le contrôle. Confirmé :
  - Dédoublonnage `any(existing is item for existing in items)` (`:159-162`) : O(k²) sur les k éléments distincts. 100 000 fois le même id ne coûte rien (la liste reste à 1 élément) ; le pire cas est k = nombre d'éléments du document. Recherche des racines (`:165-171`) : O(k² × profondeur), chaque pas de `_is_descendant` résolvant une référence Docling (~1 µs). Pour k = 1 000 : ~10⁶ paires, 1 à 3 s ; k = 5 000 : ~25 à 75 s ; k = 20 000 (tout un document de 300 pages) : de l'ordre de 10 à 20 minutes (**estimé**).
  - `_gather_merge_run` : `list(parent.children).index(...)` deux fois par élément fusionné (`:243,249`), comparaison d'égalité pydantic sur `RefItem` (~1 µs) ; fusionner 1 000 paragraphes du corps (15 000 enfants) : ~10 à 30 s, plus le coût de `_move_subtree` de Docling par élément (**estimé**).
  - Tout cela tourne en thread (pas sur la loop), mais garde le GIL, occupe un thread du pool partagé sans annulation possible, et se rejoue à chaque aperçu, chargement sans cache, sauvegarde et reconstruction. La borne de 100 000 ids ne protège pas : le nombre d'ids distincts valides est borné par la taille du document.
- **Suggestion** : `seen = set(map(id, …))` pour le dédoublonnage ; racines par un ensemble d'ids et une remontée unique par élément (O(k × profondeur)) ; positions des enfants via un dict `ref → index` calculé une fois par parent. Effort S.

### [INFO] Réactivité profonde sur les réponses de l'éditeur — inchangé

- **Localisation** : `frontend/src/features/analysis-editor/store.ts:32` (`preview`), `saved` idem.

### [INFO] SQLite : connexion par appel, pas de WAL, transactions de remplacement (en partie nouveau)

- **Localisation** : `document-parser/persistence/database.py:358-373` ; `persistence/chunk_repo.py:139-169` ; `persistence/analysis_edit_repo.py:148-198`.
- **Constat** :
  - Toujours une connexion aiosqlite (donc un thread) par appel de dépôt, pas de `PRAGMA journal_mode=WAL`, pas de `busy_timeout` explicite : le délai d'attente est celui de `sqlite3.connect`, 5 s par défaut, transmis par `aiosqlite.connect` (lecture de la signature, non exécuté). La seconde remédiation ajoute 1 à 2 connexions par résolution d'analyse courante (tableau plus bas).
  - `replace_for_document` : soft-delete, `executemany` des nouveaux chunks et écriture de l'état dans une transaction implicite (`BEGIN` différé ouvert par l'`UPDATE`, donc verrou `RESERVED` pris dès la première instruction, pas de montée lecture → écriture). Plus d'une instruction par chunk : un seul `executemany`. Pour 3 000 chunks d'environ 3 Ko, ~9 Mo de pages neuves plus les pages des anciennes lignes réécrites dépassent le cache de 2 Mo par défaut : SQLite déverse sur le fichier et prend le verrou `EXCLUSIVE` avant le commit, ce qui bloque aussi les lecteurs jusqu'à la fin. Durée estimée : 0,1 à 0,5 s sur SSD, 1 à 3 s pour ~30 000 chunks (**estimé**). Lecteurs et écrivains concurrents (polling, progression d'une analyse) attendent via le délai de 5 s ; au-delà : `database is locked`. Avant, deux transactions séparées de taille voisine : durée totale comparable, mais une seule fenêtre exclusive plus longue maintenant.
  - Les chunks soft-supprimés s'accumulent : chaque re-chunk fait parcourir à l'`UPDATE` toutes les lignes du document, mortes comprises (`idx_chunks_doc`), comme avant.
  - Sauvegarde de l'éditeur : `BEGIN IMMEDIATE`, puis un `await db.execute` par commande (`:163-190`), soit un aller-retour vers le thread aiosqlite par commande, verrou d'écriture tenu entre deux. Avec la nouvelle borne `MAX_EDIT_COMMANDS = 10_000`, 0,5 à 1 s de verrou au pire, plus l'upsert du cache (plusieurs Mo à 300 pages) (**estimé**). Structure inchangée depuis le contrôle.
- **Suggestion** : `PRAGMA journal_mode=WAL` à l'initialisation (les lecteurs ne sont plus bloqués par un écrivain) et `PRAGMA busy_timeout` explicite dans `get_db` ; `executemany` pour les commandes de l'éditeur ; purge périodique des chunks soft-supprimés anciens. Effort S.

### [INFO] Les requêtes « résumé » parcourent quand même le contenu lourd (nouveau)

- **Localisation** : schéma `document-parser/persistence/database.py:63-79` ; `persistence/analysis_repo.py:42-47,73-96,118-139`.
- **Constat** : dans `analysis_jobs`, les colonnes lues par les résumés (`progress_*`, `error_message`, `started_at`, `completed_at`, `created_at`) sont placées **après** `content_markdown`, `content_html`, `pages_json`, `document_json` et `chunks_json`. SQLite stocke une ligne dans l'ordre des colonnes ; pour lire une colonne située après plusieurs Mo de texte, il suit la chaîne des pages de débordement, page par page. Les résumés n'envoient donc pas le contenu à Python, mais en relisent les pages : de l'ordre de la taille de la ligne par analyse terminée (quelques Mo à 300 pages) (**estimé**, non vérifiable sans mesure ; rapide si les pages sont dans le cache de l'OS, coûteux sinon). Concerné : `find_all_summaries` (jusqu'à 200 lignes, appelé toutes les 3 s par `followActive`, préexistant), `find_summaries_by_document` (nouveau, sans plafond, seulement à l'ouverture de la boîte de suppression : rare), et le repli `find_latest_parsed_ids` (tri sur `completed_at`, mais seulement pour un document sans ligne d'état, donc en pratique sans analyse terminée : négligeable). Index : `WHERE document_id = ?` utilise `idx_analysis_jobs_doc_status` ; le tri sur `created_at` se fait en mémoire sur les quelques lignes d'un document, sans problème.
- **Suggestion** : index couvrant pour les résumés, par exemple `analysis_jobs(created_at, id, document_id, status, progress_current, progress_total, error_message, started_at, completed_at)` et son pendant préfixé par `document_id` : SQLite répond alors depuis l'index sans toucher la table. À terme, sortir le contenu dans une table d'artefacts (#279). Pour le compteur de la bibliothèque, un `COUNT(*)` suffit.

### [INFO] `nest_by_heading` : même complexité, constante plus élevée (nouveau)

- **Localisation** : `document-parser/domain/heading_tree.py:51-91` ; appelants `domain/parse_index.py:151` (index MCP, en thread et mis en cache LRU), `domain/document_tree.py:62` (arbre des chunks, sur la loop), `domain/outline_builder.py:96,162` (titres seulement, sur la loop), `infra/docling_projector.py:199` (projection de l'éditeur, en thread, à chaque aperçu).
- **Constat** : pas de O(n²). Par élément : un `NestStep` figé (6 champs posés par `object.__setattr__`), un tuple d'ancêtres de taille ≤ profondeur (niveaux 0 à 6, donc ≤ 7) et un tuple des titres fermés ; les fermetures sont amorties en O(n) sur tout le parcours. C'est O(n × profondeur) en mémoire, comme l'ancien `heading_path` de l'index qui faisait déjà une liste par élément. Surcoût estimé : ~1 µs par élément, soit 15 à 25 ms par appel pour 15 000 à 20 000 éléments (**estimé**). Le plan MCP parcourt deux fois les titres (`:96` et `:162` via `_count_children`) : quelques centaines d'éléments, négligeable.
- **Suggestion** : aucune urgence ; si la projection devient le goulot, un tuple simple ou `__slots__` au lieu d'une dataclass figée divise ce coût.

### [INFO] Historique : union de payloads sans discriminant (nouveau)

- **Localisation** : `document-parser/api/schemas.py:364-383`, `api/analysis_edits.py:73-84`.
- **Constat** : `payload: EditCommandPayloadResponse` est une union de 7 modèles sans discriminant ; pydantic 2.13 en mode « smart » essaie chaque membre pour chaque entrée (une fois à la construction ; FastAPI ne revalide pas l'instance). Membres petits : quelques µs par entrée, quelques ms pour un historique de 1 000 entrées. Un `deleteElements` de 100 000 ids fait valider la liste deux fois (`MergeText` puis `DeleteElements`), ~2 à 4 ms (**estimé**). Négligeable.
- **Suggestion** : `Discriminator` callable sur `command_type`, si l'historique grossit.

### [INFO] Middlewares et bornes de requête (nouveau)

- **Localisation** : `document-parser/infra/host_guard.py:103-113`, `infra/body_limit.py:35-63`, `main.py:92-119`.
- **Constat** : les deux middlewares sont en ASGI pur. Le contrôle d'hôte n'est installé que si `API_ALLOWED_HOSTS` est renseigné, et coûte alors une construction de `Headers` et quelques comparaisons de chaînes par requête `/api` : de l'ordre de la µs. La limite de taille ne s'applique qu'à `/api/analyses/import` (comparaison de chemin pour les autres) ; elle compte les morceaux au fil de l'eau, refuse sur `Content-Length` sans rien lire, et rejoue les messages sans copie supplémentaire. Le JSON importé (jusqu'à 200 Mo) reste décodé par FastAPI sur la loop avant la route (1 à 2 s à 200 Mo, **estimé**), comme avant mais désormais borné. Les bornes de l'éditeur (`MAX_ELEMENT_IDS`, `MAX_ELEMENT_TEXT_LENGTH`, `MAX_EDIT_COMMANDS`) s'appliquent après décodage complet du corps : la taille effective reste plafonnée par `client_max_body_size` de nginx.

---

## Delta vs contrôle

| Écart du contrôle (`a12b744`) | Statut à `efc0bc5` | Preuve |
|---|---|---|
| [MIN] 12.3.2 réponses de l'éditeur, double chargement | **Réduit** en partie (comptage de la bibliothèque) ; double chargement inchangé ; +1 requête légère au rechargement des versions ; coût CPU par réponse en hausse (nouvel écart) | `DocsLibraryPage.vue:345`, `features/document/store.ts:195-215` |
| [MIN] `followActive` sans borne | **Inchangé** | `features/analysis/store.ts:171-182` |
| [MIN] `show_sources` par citation | **Aggravé** (+1 à 2 requêtes par citation) | `services/citation_service.py:196-199` |
| [INFO] verrou pdfium, `page_sizes` 106 ms | **Résolu** pour `page_sizes` (2,6 ms, `8436e27`) ; reste de l'INFO inchangé | `infra/pdf_inspector.py:36-39` |
| [INFO] `index.html` sans cache | Inchangé | — |
| [INFO] logo, `favicon.svg` | Inchangé | — |
| [INFO] CPU sur la loop | **Légèrement aggravé** (hachage non paresseux, `NestStep` dans l'arbre) ; la part éditeur passe en MIN | `services/analysis_edit_service.py:365` |
| [INFO] projections non bornées | Inchangé | — |
| [INFO] cache mono-slot | Inchangé | — |
| [INFO] previews sans coalescence | Inchangé | — |
| [INFO] PDF.js par visionneuse | Inchangé | — |
| [INFO] quadratiques du rejeu | Inchangé (confirmé, chiffré) ; borne de 100 000 ids sans effet sur le pire cas | `infra/docling_editor.py:159-171,243,249` |
| [INFO] réactivité profonde | Inchangé | — |
| [INFO] connexion par appel, pas de WAL | Inchangé ; plus de connexions par requête ; analyse des transactions ajoutée | `persistence/database.py:358-364` |

Score : **95 → 95** (inchangé, 20/21). CRIT 0, MAJ 0 inchangés. MIN 3 → 4 (+1 : validation typée de l'éditeur). INFO 11 → 15 (+4 : pages de débordement des résumés, `nest_by_heading`, union de l'historique, middlewares ; une INFO réduite).

---

## Effets de la seconde remédiation

### Requêtes SQL par requête HTTP (estimé à la lecture)

Une « requête » = un appel de dépôt, donc une connexion aiosqlite (thread, ouverture, `PRAGMA foreign_keys`, requête, fermeture : ~0,5 à 1 ms estimé). Les crochets indiquent les requêtes conditionnelles : `[repli]` = `find_latest_parsed_ids`, seulement pour un document sans ligne d'état ; `[cmd]`, `[cache]` = seulement si un flux d'édition existe ; `[compte]` = seulement si les chunks n'ont pas de source enregistrée.

| Route | Avant (`a12b744`) | Après (`efc0bc5`) | Commentaire |
|---|---|---|---|
| `GET /api/documents/{id}` | 2-3 (document, liens, [stores]) | 3-5 (+ états, [repli]) | `api/documents.py:104` résout l'analyse courante une fois |
| `GET /analysis-editor?analysisId=` (workspace, éditeur) | 4-7 | 4-7 | document, analyse (ligne lourde), flux, [cmd], [cache], état, [compte] — identique |
| `GET /analysis-editor` sans `analysisId` | 5-8 | 5-9 | sélection → états + [repli] |
| `POST /analysis-edits/preview` | 5-7 | 5-8 | idem |
| `POST /analysis-edits` (sauvegarde, sans id) | 8-11 + 1 transaction | 8-13 + 1 transaction | le résolveur est appelé deux fois (`_load_base_analysis` puis `activate`, `analysis_edit_service.py:163,271`), comme l'ancienne sélection ; l'état est relu une troisième fois dans `_has_stale_chunks` |
| Re-chunk du document | ~10-13 dont 3 écritures | ~10-14 dont 1 transaction | document lu 3 fois, état lu 2 fois (`chunk_service.py:304-348`) ; écritures regroupées |
| `GET /tree` sans id | 7-10 | 7-11 | passe par `load_active_result` |
| Ask | 1 (dernière analyse complète, lourde) | 2-3 (états, [repli], analyse par clé) | moins d'E/S si le document a plusieurs analyses : l'ancienne requête triait sur `completed_at` à travers les lignes lourdes |
| Export md/json | 1 | 2-3 | idem Ask |
| MCP `find_documents` | 2 | 2-4 (documents, états, [repli], parses) | ≤ 50 ids, `IN` borné |
| MCP plan / lecture sans version | 2-3 | 3-5 | + états, + `find_parsed_ids` |
| MCP `verify_citation` | 3-4 | 4-6 | voir MIN `show_sources` |
| MCP `show_sources`, 50 citations | ~200 | ~300 | idem |

Résolutions multiples dans une même requête : la sauvegarde résout deux fois quand aucun `analysisId` n'est passé ; `load_active_result` lit le document deux fois (lui-même puis `load_editor`), comme avant. `GET /api/documents/{id}` ne résout qu'une fois. Côté navigateur : ouverture du workspace 4 requêtes HTTP (inchangé, dont 2 lourdes en série) ; rechargement des versions 3 → 4 (le `GET` document part en parallèle des versions).

### Verrous et threads

- **Fichiers** (`ac7ac17`) : en thread — écriture et comptage d'upload (un seul saut), `discard`, `read_fingerprint`, rendu, tailles de page. Sur la loop — `resolve` (1 à 2 `stat`), `has_file` à l'export (1 `stat`), `delete` à la suppression (`realpath` ×2, `exists`, `unlink`) : déjà sur la loop avant, quelques dizaines de µs sur disque local. Le gestionnaire de contexte de `PreviewService` n'englobe que des `await` vers des threads ; il ne retient rien et ne coûte rien hors exception.
- **SQLite** : voir l'INFO dédiée. Pas de montée de verrou lecture → écriture dans les transactions nouvelles (`replace_for_document` commence par une écriture ; la sauvegarde de l'éditeur fait `BEGIN IMMEDIATE`), donc pas de `SQLITE_BUSY` immédiat par interblocage. Fenêtre exclusive plus longue au re-chunk et à la restauration, attentes absorbées par le délai implicite de 5 s.
- **pdfium** : maintien de `page_sizes` divisé par ~40 (`8436e27`). Rien de neuf sous le verrou.
- **Pool de threads** : les rejeux quadratiques (INFO) restent le seul moyen identifié d'occuper un thread pendant des minutes.

### Complexité

- `nest_by_heading` : O(n × profondeur), profondeur ≤ 7 ; même ordre que les boucles qu'il remplace, constante plus élevée (INFO).
- `hash_command_stream` : une fois par chargement (à partir des empreintes stockées, sans resérialiser), une fois par sauvegarde et par reconstruction ; `serialize_command_payload` deux fois par commande en attente à la sauvegarde (empreinte du flux, puis écriture par le dépôt) et une fois de plus dans `hash_command` : quelques µs par commande.
- `index_items_by_ref` (`domain/parse_index.py`) est partagé entre l'index et l'arbre : même coût qu'avant.
- `_build_cache` : simple déplacement en fonction de module, même travail.
- Frontend : `createCssTokenReader` fait un `getComputedStyle` par tracé, et `StructureViewer` l'appelle désormais à chaque tracé (avant : couleurs en dur) ; les tracés sont déclenchés par le changement de page, les filtres et le redimensionnement, pas par la souris : coût de l'ordre de la µs (**estimé**). `PageRaster` remonté par `key` quand le PDF échoue : un remontage par page de la fenêtre de rendu, une fois, comme l'ancien `v-if`. Le planificateur d'aperçu est équivalent. L'historique en composant enfant évite de re-rendre la liste à chaque frappe ; `[...history].reverse()` et un `Intl.DateTimeFormat` par entrée restent dans le gabarit, comme avant. Aucune nouvelle source de re-rendu complet de l'éditeur par frappe.

### Ce qu'une mesure seule peut trancher

Coût réel de la validation pydantic du modèle de l'éditeur à 300 pages ; temps de lecture des pages de débordement par les résumés (cache OS chaud ou froid) ; durée de la fenêtre exclusive au re-chunk et à la restauration, et attente réelle d'un lecteur concurrent ; coût d'une connexion aiosqlite par appel ; surcoût de `NestStep` ; durée des rejeux quadratiques sur un vrai document ; coût de `getComputedStyle` dans le navigateur.

---

## Points positifs

- Résolution de l'analyse courante groupée, avec des listes d'ids bornées (≤ 50) : pas de N+1 au listage MCP.
- Remplacement des chunks et écriture de l'état en une seule transaction, en `executemany`, qui commence par une écriture : atomicité gagnée sans interblocage.
- `page_sizes` ne charge plus les pages : 40 fois moins de temps sous le verrou pdfium.
- Middlewares en ASGI pur, sans enveloppe de réponse : les exports en flux passent intacts ; la limite de taille ne touche qu'un chemin.
- Comptage de la bibliothèque par les résumés au lieu de toutes les analyses avec leur contenu.
- Extraction de l'historique et des bandeaux en composants : moins de re-rendu dans l'éditeur.
- Ask et l'export lisent l'analyse par sa clé au lieu de trier les lignes lourdes.

---

## Verdict partiel : GO

Score **95/100** (≥ 80), 0 CRIT, 0 MAJ, 4 MIN. Une régression estimée, non bloquante :
la validation typée de la réponse de l'éditeur sur l'event loop (correctif S : insérer le
JSON déjà produit). À traiter au prochain cycle : 12.3.2 (M), `show_sources` (S),
`followActive` (S), WAL + `busy_timeout` (S), index couvrant des résumés (S), algorithmes
du multi-delete et de la fusion (S).
