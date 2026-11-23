# Rapport d'audit : Performance & Ressources

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a744f48`, arbre de travail
**Nature** : Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5`
(`release-0.7.4-validation/12-performance.md` : 95/100, 12/13, 0 CRIT, 0 MAJ, 4 MIN, 15 INFO)

Aucune mesure : coûts estimés à la lecture.

Méthode : lecture de l'arbre de travail, `git log` / `git diff efc0bc5..a744f48`, lecture
(sans import) de FastAPI 0.136.1, pydantic 2.13.4, aiosqlite 0.22.1 et docling-core 2.87.1
installés dans `document-parser/.venv`. Rien n'a été lancé : ni pytest, ni ruff, ni outillage
node, ni Docker, ni uvicorn ; aucun chronométrage. Les suites ont été lancées par le mainteneur sur
ce commit (backend ruff propre, 1773 passés / 15 ignorés ; frontend 604 tests) ; je ne les ai pas
relancées. Les chiffres « mesuré » viennent de rapports antérieurs, cités ; tous les autres sont
des **estimations** d'ordre de grandeur. Document de référence : 300 pages, 15 000 à 20 000
éléments, réponse de l'éditeur de 13,8 Mo (mesuré au re-audit).

Arbre de travail : `document-parser/api/schemas.py` et `tests/test_schemas.py` sont modifiés et
non commités (les modèles de payload stockés redeviennent des classes écrites à la main au lieu
d'être générés par `create_model`). Sans effet sur la performance : même union de 7 modèles,
construite une fois à l'import.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 12 / 13 |
| Score | 95 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 0 |
| Écarts MINOR | 3 |
| Écarts INFO | 16 |

### Détail par item

| # | Item | Poids | Conforme | Justification (arbre à `a744f48`) |
|---|------|-------|----------|---------------|
| 12.1.1 | Pas de requête N+1 | 2 | Oui | Résolveur toujours groupé (`services/current_analysis.py:40-66`). `show_sources` résout les parses courantes une fois par appel (`services/source_service.py:102-103,173-186`) puis passe le résultat à chaque vérification (`services/citation_service.py:94-106,209-216`) : de ~300 à ~105 requêtes pour 50 citations. Restent 2 requêtes par citation (document et appartenance de la version), bornées à 50 : INFO. Sauvegarde de l'éditeur en un `executemany` (`persistence/analysis_edit_repo.py:189-195`). |
| 12.1.2 | Fichiers temporaires supprimés | 2 | Oui | Inchangé (`services/document_service.py:108-110`). |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` respectée | 2 | Oui | Inchangé (`infra/settings.py:24`, `bootstrap/factories.py:208`). |
| 12.1.4 | Opérations longues hors event loop | 3 | Oui | La réponse typée des quatre routes de l'éditeur est construite dans `asyncio.to_thread` (`api/analysis_edits.py:59-77`) : décodage JSON du modèle, `model_validate`, arbre et résultat hors de la loop. Reste sur la loop la sérialisation finale par FastAPI (INFO). Conversion, projection, rejeu, rendu, comptage : inchangés, en thread. |
| 12.1.5 | Pas de fichier entier en mémoire | 2 | Oui | Inchangé (`infra/pdf_inspector.py`, `infra/body_limit.py`). |
| 12.2.1 | Watchers avec cleanup | 2 | Oui | Aucun nouveau `watch` ; composants morts supprimés (`StructureViewer.vue`, `PagePreview.vue`, `DocChunkTab.vue`…), donc moins de watchers montables. |
| 12.2.2 | Listeners retirés au démontage | 2 | Oui | Inchangé (`AnalysisEditor.vue`). |
| 12.2.3 | Annulation / debounce | 1 | Oui | `previewScheduler.ts:37-43` remet le minuteur à `null` quand il se déclenche : même délai, même annulation. |
| 12.2.4 | Pas de re-render excessif | 1 | Oui | `saveError` séparé d'`error` (`features/analysis-editor/store.ts:44`) : un refus de sauvegarde ne vide plus l'éditeur, pas de rechargement en plus. |
| 12.2.5 | Assets lourds optimisés | 1 | Oui | `frontend/public` inchangé. |
| 12.3.1 | Cache nginx des statiques | 1 | Oui | Templates inchangés. |
| 12.3.2 | Réponses API de taille raisonnable | 1 | **Non** | Non traité par le cycle. Réponse de l'éditeur toujours complète (`api/schemas.py:288-297`), toujours chargée par le workspace pour n'en garder que `result` après un `GET /api/analyses/{id}` complet (`features/document/store.ts:41-51`). Seule réduction : plus aucun chargement quand le document n'a pas d'analyse courante (`store.ts:170-176,204-208`), cas rare. |
| 12.3.3 | Health check léger | 1 | Oui | Inchangé (`SELECT 1`). |

Poids total = 21. Non conforme : 12.3.2 (1). Poids conformes = 20.
`20 / 21 * 100 = 95,2` → **95 / 100**.

---

## Écarts constatés

### [MIN] Réponses de l'éditeur volumineuses ; double chargement au workspace — inchangé (item 12.3.2)

- **Localisation** : `document-parser/api/schemas.py:288-297` ; `frontend/src/features/document/store.ts:41-51,162-181,195-212`.
- **Constat** : 13,8 Mo à 300 pages (mesuré au re-audit). L'ouverture du workspace fait toujours
  deux requêtes lourdes en série (`GET /api/analyses/{id}`, puis `GET /analysis-editor` dont seul
  `result` est lu). Le cycle supprime seulement le chargement de repli quand le document n'a pas
  d'analyse courante.
- **Règle violée** : 12.3.2 (poids 1).
- **Remédiation** : vue légère du résultat courant (`?view=result` ou route dédiée) pour le
  workspace ; `fetchAnalysis` complet seulement si l'éditeur est désactivé. Effort M.

### [MIN] Suivi des analyses à 3 s sans plafond de durée — inchangé (hors checklist)

- **Localisation** : `frontend/src/features/analysis/store.ts:171-182`.
- **Constat** : inchangé ; chaque tick lit jusqu'à 200 lignes de résumés (voir INFO sur les pages
  de débordement).
- **Remédiation** : plafond de durée, comme le polling unitaire. Effort S.

### [MIN] Suppression et fusion en masse : la part du projet est linéaire, celle de Docling reste quadratique — requalifié (hors checklist, non introduit par le cycle)

- **Localisation** : `document-parser/infra/docling_editor.py:150-174` (`_delete_elements`),
  `:235-264` (`_gather_merge_run`), `:343-368` ; docling-core 2.87.1
  `docling_core/types/doc/document.py:1011` (`if ref in refs`), `:1062` (`delta = sum(...)`),
  `:1076` (`ref_item not in refs_to_be_deleted`), `:1200,1204` (`_move_subtree`) ; rejeu à chaque
  aperçu `services/analysis_edit_service.py:126-139,316-326`.
- **Constat** :
  - Code du projet, corrigé : dédoublonnage et recherche des racines par ensemble d'identités, une
    remontée d'ancêtres par élément, O(k × profondeur) ; fusion avec une seule table
    `cref → position` par parent, O(1) par élément. Plus de `list(parent.children).index` dans la
    fusion ; `_is_descendant` est O(profondeur) et n'est appelé qu'une fois par déplacement. J'ai
    relu la règle de décalage de la fusion : elle donne le même point d'insertion que l'ancien
    calcul (un élément du parent n'est avant la fin du bloc que s'il y est déjà ou s'il précédait
    la cible). Restent O(n) par commande, normaux : `list(parent.children).index` dans les deux
    formes de déplacement (`:307,311,335-337`), le parcours de `logical_objects` à chaque
    changement de niveau vers -1/0 (`:206-208`), le tri de la fusion sur tout le document
    (`:106-107`).
  - Docling, inchangé et non compté par la validation : `delete_items` parcourt tout le document
    et teste `ref in refs` sur une **liste** de `RefItem` pydantic (égalité Python, ~1 µs), puis
    reconstruit les références de chaque nœud en testant de nouveau `not in refs_to_be_deleted`
    et en sommant le dictionnaire des suppressions pour chaque référence. Coût O(N × k) pour k
    racines supprimées dans un document de N éléments. Le document produit par Docling est
    presque plat (les titres ne contiennent pas leurs paragraphes), donc les racines sont
    presque tous les éléments sélectionnés. Estimations à 300 pages (N = 20 000) : k = 1 000 →
    20 à 45 s ; tout le document → 10 à 20 min, le même ordre que l'estimation de la validation
    pour l'ancien code du projet. Une fusion de m paragraphes ajoute m `_move_subtree`, chacun un
    `list.remove` par égalité sur les enfants du parent (O(s)), puis le même `delete_items` sur
    m - 1 éléments : m = 1 000 dans un corps de 15 000 enfants → 25 à 50 s (**estimé**).
    Chaque `deleteElement` unitaire coûte aussi un parcours complet (0,05 à 0,2 s à 300 pages,
    **estimé**), multiplié par le nombre de suppressions du flux.
  - Le flux sauvegardé est rejoué en entier à chaque aperçu (pause de 400 ms), à chaque
    sauvegarde et reconstruction ; seul le chargement passe par le cache. Après une suppression
    sauvegardée de 1 000 éléments sur un document de 300 pages, chaque aperçu occuperait donc un
    thread du pool par défaut 20 à 45 s en tenant le GIL. L'annulation côté navigateur
    n'interrompt pas le thread serveur.
  - Le test de 3 000 éléments (`tests/test_analysis_editing.py:260-283`) range 9 textes sous
    chacun des 300 titres : 300 racines seulement, il ne couvre pas le cas plat.
- **Remédiation** : (1) aperçu incrémental : partir du `document_json` du cache sauvegardé et
  n'appliquer que les commandes en attente quand elles ne contiennent pas de `setCommandActive` ;
  (2) contourner `delete_items` pour les suppressions groupées : appeler `_delete_items` avec une
  liste dont `__contains__` teste un ensemble de `cref` (le projet utilise déjà une primitive
  privée de Docling, avec contrôle de signature, `:343-357`), ou proposer le correctif en amont
  (ensemble de `cref`, décalages par recherche dichotomique) ; (3) test du cas plat. Effort M.

### [INFO] Sérialisation finale de la réponse de l'éditeur sur la loop — reste de l'ancien MIN

- **Localisation** : `document-parser/api/analysis_edits.py:59-77` ; FastAPI 0.136.1
  `fastapi/routing.py:687-712`, `fastapi/_compat/v2.py:173-183`.
- **Constat** : le `to_thread` reçoit l'instantané par référence ; le saut de thread ne copie
  rien. Dans le thread : `json.loads` du modèle, `model_validate`, arbre, résultat. FastAPI
  valide ensuite l'instance renvoyée par `validate_python` (renvoyée telle quelle, pydantic ne
  revalide pas une instance) puis la sérialise en Rust (`serialize_json`) **sur la loop** : 13,8
  Mo à 300 pages, de l'ordre de 20 à 60 ms par réponse (**estimé**, contre 115 ms mesurés au
  re-audit pour l'ancien chemin, qui décodait aussi le JSON sur la loop, et 175 à 265 ms estimés
  à `efc0bc5`). Le modèle de l'éditeur est décodé deux fois quand il vient du cache (dans
  `project_serialized`, `infra/docling_projector.py:87`, puis dans `read_editor_model`), en
  thread. Pool : par défaut `min(32, 16 + 4) = 20` threads sur cette machine ; le saut ajoute
  100 à 250 ms (**estimé**) par réponse, après la projection. Sans risque de famine en usage
  normal ; le seul scénario de famine identifié vient des rejeux Docling (MIN ci-dessus).
- **Suggestion** : `AnalysisEditorModelResponse.model_validate_json(editor_model_json)` (analyse
  en Rust, sans dict Python intermédiaire) ; à terme, construire les octets de la réponse dans le
  thread et renvoyer un `Response` brut.

### [INFO] `show_sources` : 2 requêtes par citation — réduit (ancien MIN)

- **Localisation** : `document-parser/services/source_service.py:102-103,173-186` ;
  `services/citation_service.py:110` → `services/parse_loader.py:79-90`.
- **Constat** : la parse courante n'est plus résolue par citation. Chaque vérification lit encore
  le document et l'appartenance de la version épinglée (2 requêtes, une connexion chacune), alors
  que toutes les citations d'une carte épinglent le même document et la même version
  (`_require_single_pin`). Pour 50 citations : ~105 requêtes au lieu de ~300, soit environ 0,1 s
  de moins (**estimé**).
- **Suggestion** : mémoriser `(document, version)` le temps de l'appel.

### [INFO] Verrou pdfium partagé avec Docling — inchangé

- **Localisation** : `document-parser/infra/pdf_inspector.py:27-42`.

### [INFO] `index.html` sans en-tête de cache explicite — inchangé

- **Localisation** : `nginx.conf.template:19-21`, `frontend/nginx.conf.template:19-21`.

### [INFO] Logo surdimensionné ; `favicon.svg` non référencé — inchangé

- **Localisation** : `frontend/public/logo.png`, `frontend/index.html:7`.

### [INFO] Reliquat de CPU sur l'event loop hors éditeur — réduit

- **Localisation** : `services/analysis_edit_service.py:78,229,358-366` ;
  `services/document_tree_service.py` (`json.loads` + `build_tree_nodes`) ;
  `persistence/analysis_edit_repo.py:163-188`.
- **Constat** : `_has_stale_chunks` ne hache plus que si une source de chunks est enregistrée
  (`:362-364`) ; c'est le cas habituel après un chunking, le hachage (2,6 ms à 300 pages, mesuré
  au re-audit) reste donc fréquent. L'arbre reste construit sur la loop (67 ms mesurés au
  re-audit). Le calcul des empreintes et la sérialisation des commandes de la sauvegarde
  tournent sur la loop pendant que le verrou d'écriture est tenu (quelques µs par commande).
- **Suggestion** : `build_tree_nodes` en `to_thread`.

### [INFO] Projections parallèles non bornées, pool partagé, GIL — inchangé, occupation un peu plus longue

- **Localisation** : `services/analysis_edit_service.py:316-326`, `api/analysis_edits.py:62`.
- **Constat** : pas de sémaphore sur les projections ; chaque réponse de l'éditeur prend
  maintenant un second passage dans le pool. Voir le scénario de famine du MIN Docling.

### [INFO] Cache mono-slot `_unedited_projection` — inchangé

- **Localisation** : `services/analysis_edit_service.py:69,78-81,96-97`.

### [INFO] Cache de previews sans coalescence — inchangé

- **Localisation** : `services/preview_service.py:91-96`.

### [INFO] PDF.js : un document par visionneuse — inchangé

- **Localisation** : `frontend/src/features/document/ui/usePdfDocument.ts`.

### [INFO] Réactivité profonde sur les réponses de l'éditeur — inchangé

- **Localisation** : `frontend/src/features/analysis-editor/store.ts` (`preview`, `saved`).

### [INFO] SQLite : connexion par appel, pas de WAL ; transactions — réduit pour la sauvegarde, nouvelle transaction de suppression

- **Localisation** : `persistence/database.py:358-373` ; `persistence/analysis_edit_repo.py:148-198` ;
  `persistence/analysis_repo.py:206-237,249-269` ; `persistence/chunk_repo.py:151-170`.
- **Constat** :
  - Toujours une connexion aiosqlite par appel, pas de `journal_mode=WAL`, pas de
    `busy_timeout` explicite (5 s implicites de `sqlite3.connect`).
  - Sauvegarde de l'éditeur : `BEGIN IMMEDIATE`, lecture de la dernière commande, empreintes en
    Python, **un** `executemany`, upsert du cache. Pour 10 000 commandes, le verrou passe de 0,5 à
    1 s à environ 0,1 à 0,3 s plus l'upsert de quelques Mo (**estimé**).
  - Suppression d'une analyse : une connexion, `BEGIN IMMEDIATE` (verrou `RESERVED` : les
    lecteurs passent, les autres écrivains attendent), lecture de `document_id` par clé, lecture
    de l'état, `DELETE`, puis seulement si l'analyse était active, la requête « dernière analyse
    restante » et l'écriture de la sélection (le trigger vérifie par l'index unique
    `(document_id, id)`, sans lire la ligne). Le `DELETE` libère les chaînes de débordement de la
    ligne et du cache d'édition en cascade : il lit chaque page de la chaîne pour trouver la
    suivante (quelques Mo). La requête de resélection passe par `idx_analysis_jobs_doc_status`,
    mais lit `completed_at`, placé après les colonnes lourdes : elle parcourt la chaîne de
    débordement de chaque analyse terminée restante du document. Verrou tenu estimé : 10 à 50 ms
    cache chaud, 0,1 à 0,5 s cache froid avec plusieurs analyses de 300 pages (**estimé**), puis
    `EXCLUSIVE` bref au commit. Un écrivain concurrent (progression, re-chunk) attend dans les 5 s ;
    un re-chunk de 30 000 chunks (1 à 3 s estimés à la validation) peut faire attendre la
    suppression, sans dépasser le délai. Pas de montée lecture → écriture : pas de
    `SQLITE_BUSY` immédiat. La clé étrangère `ON DELETE SET NULL` sur
    `document_analysis_state.active_analysis_id` n'a pas d'index : un parcours de la table d'état
    (une ligne par document) à chaque suppression, négligeable.
  - Re-chunk et restauration : `adopt_selection` / `write_selection` / `write_chunk_source`
    ajoutent une ou deux instructions dans la même transaction, négligeable.
- **Suggestion** : WAL et `busy_timeout` explicite dans `get_db` ; index partiel
  `analysis_jobs(document_id, completed_at) WHERE status = 'COMPLETED' AND document_json IS NOT NULL`
  : la resélection et le repli du résolveur n'ont alors plus à lire la table.

### [INFO] Les requêtes « résumé » parcourent le contenu lourd — inchangé

- **Localisation** : `persistence/database.py:63-79` ; `persistence/analysis_repo.py`.
- **Constat** : inchangé ; la resélection à la suppression s'y ajoute (voir INFO SQLite).

### [INFO] `nest_by_heading` : constante plus élevée — inchangé

- **Localisation** : `document-parser/domain/heading_tree.py:51-91`.

### [INFO] Historique : union de payloads sans discriminant — inchangé

- **Localisation** : `document-parser/api/schemas.py` (arbre de travail : 7 classes écrites à la
  main, union simple), `api/analysis_edits.py:80-91`.
- **Constat** : même coût qu'à la validation, que les modèles soient générés (`a744f48`) ou écrits
  à la main (arbre de travail).

### [INFO] Middlewares — inchangé

- **Localisation** : `infra/host_guard.py:78-89`, `infra/body_limit.py`, `main.py:92-118`.
- **Constat** : contrôle d'hôte réduit à une regex sur le nom, en ASGI pur, seulement sur
  `/api/` : de l'ordre de la µs.

---

## Delta vs validation

| Écart de la validation (`efc0bc5`) | Statut à `a744f48` | Preuve |
|---|---|---|
| [MIN] 12.3.2 réponses de l'éditeur, double chargement | **Inchangé** (non ciblé ; repli supprimé sans analyse courante) | `features/document/store.ts:41-51,170-176` |
| [MIN] Réponse typée de l'éditeur sur la loop | **Résolu** ; reste la sérialisation Rust sur la loop (20 à 60 ms estimés), en INFO | `api/analysis_edits.py:59-77` |
| [MIN] `show_sources` par citation | **Réduit** (~300 → ~105 requêtes pour 50 citations), passe en INFO | `services/source_service.py:102-103,173-186` |
| [MIN] `followActive` sans borne | **Inchangé** | `features/analysis/store.ts:171-182` |
| [INFO] SHA-256 de plus dans `_has_stale_chunks` | **Résolu** (hachage seulement avec une source enregistrée) | `services/analysis_edit_service.py:358-366` |
| [INFO] Arbre construit sur la loop | **Inchangé** | `services/document_tree_service.py` |
| [INFO] Fenêtre d'écriture de `replace_for_document`, pas de WAL, pas de `busy_timeout` | **Inchangé** ; nouvelle transaction de suppression analysée, courte | `persistence/analysis_repo.py:206-237` |
| [INFO] Suppression / fusion en masse quadratiques | **Réduit** dans le code du projet (linéaire) ; **requalifié en MIN** : le terme dominant est dans `delete_items` / `_move_subtree` de Docling, O(N × k), non compté jusqu'ici | `infra/docling_editor.py:150-174,235-264` ; docling-core `document.py:1011,1062,1076,1200` |
| [INFO] Un `execute` par commande à la sauvegarde | **Résolu** (`executemany`) | `persistence/analysis_edit_repo.py:189-195` |
| [INFO] Colonnes de résumé après les colonnes lourdes | **Inchangé** ; une requête de plus y passe (resélection) | `persistence/database.py:63-79` |
| [INFO] pdfium, `index.html`, logo, projections non bornées, cache mono-slot, previews, PDF.js, réactivité profonde, `nest_by_heading`, union de l'historique, middlewares | Inchangés | — |

Score : **95 → 95** (20/21). CRIT 0, MAJ 0 inchangés. MIN 4 → 3 (−1 réponse typée résolue,
−1 `show_sources` passé en INFO, +1 suppression/fusion Docling requalifiée). INFO 15 → 16 (+1
sérialisation résiduelle, +1 `show_sources`, −1 quadratique passé en MIN ; le SHA-256 en trop et
l'`execute` par commande, résolus, étaient des points à l'intérieur d'INFO existantes).

---

## Effets du troisième cycle

### Requêtes SQL par requête HTTP (estimé à la lecture)

Une requête = un appel de dépôt, donc une connexion aiosqlite. `[repli]` = seulement pour un
document sans ligne d'état ; `[cmd]`, `[cache]` = seulement avec un flux d'édition ; `[compte]` =
seulement sans source de chunks enregistrée ; `[miss]` = index de navigation absent du cache LRU.

| Route | Validation (`efc0bc5`) | Final (`a744f48`) | Commentaire |
|---|---|---|---|
| `GET /api/documents/{id}` | 3-5 | 3-5 | document, liens, [stores], états, [repli] ; la dépendance ne fait que lire l'état de l'app |
| `GET /analysis-editor?analysisId=` | 4-7 | 4-7 | document, analyse (ligne lourde), flux, [cmd], [cache], état, [compte] |
| `GET /analysis-editor` sans id | 5-9 | 5-9 | + états, [repli] |
| `POST /analysis-edits/preview` | 5-8 | 5-8 | pas de lecture du cache : rejeu complet (voir MIN Docling) |
| `POST /analysis-edits` (sans id) | 8-13 + 1 transaction | 8-13 + 1 transaction | la transaction fait 4 instructions au lieu de 3 + une par commande |
| `GET /tree` sans id | 7-11 | 7-11 | appel direct à `DocumentTreeService`, même chemin |
| Ask | 2-3 | 2-3 | `load_current_original` = ancien `load_current_analysis` |
| Export md/json sans id | 2-3 (lu à la validation) | 7-11 | correction de lecture : l'éditeur est branché sur l'export depuis `efc0bc5` (`bootstrap/builder.py`), le chemin était déjà celui du résultat édité ; pas de changement réel |
| MCP `find_documents` | 2-4 | 2-4 | ≤ 50 ids, `IN` borné |
| MCP `verify_citation` | 4-6 | 4-6 (+1 [miss]) | document, appartenance de la version, états, [repli], parses |
| MCP `show_sources`, 50 citations | ~300 | ~105 | 2-3 une fois, puis 2 par citation, puis ~4 pour la carte |
| `DELETE /api/analyses/{id}` | 1 connexion, 1 instruction | 1 connexion, 4 instructions (+2 si l'analyse était active) | `BEGIN IMMEDIATE`, SELECT, état, DELETE, [resélection, sélection], COMMIT |
| Re-chunk du document | ~10-14 | ~10-14 | le document est lu 3 fois, comme avant |

### Event loop, threads et verrous

- **Loop** : plus de construction pydantic de la réponse de l'éditeur ; restent la sérialisation
  Rust (20 à 60 ms estimés à 300 pages), l'arbre des chunks, les hachages de résultat. L'export
  PDF appelle `resolve` puis `has_file` sur la loop (2 à 5 appels `stat` / `realpath`, quelques
  dizaines de µs). `can_be_current_of`, `has_docling_document` : comparaisons de champs, aucun
  accès disque. Les routes qui appellent directement `ChunkPushService`, `DocumentTreeService` et
  le résolveur n'ajoutent ni requête ni saut de thread.
- **Pool** : 20 threads par défaut ici. Un passage de plus par réponse de l'éditeur, court. Le
  risque réel reste le rejeu Docling d'un gros flux à chaque aperçu, non annulable.
- **SQLite** : sauvegarde de l'éditeur plus courte ; suppression d'analyse en une transaction
  courte qui commence par prendre le verrou d'écriture. Rien de nouveau ne bloque les lecteurs
  avant le commit.
- **Frontend** : composants morts retirés ; le store document ne charge plus d'analyse de repli ;
  rien de nouveau sur les watchers, listeners ou re-rendus.

### Complexité

- `_delete_elements` : O(k × profondeur) dans le projet, au lieu de O(k² × profondeur).
- `_gather_merge_run` : O(s) une fois pour la table de positions, puis O(1) par élément dans le
  projet ; chaque `_move_subtree` de Docling reste O(s).
- `delete_items` de Docling : O(N × k) égalités pydantic, plus O(N × k) additions pour les
  décalages. Terme dominant pour toute suppression ou fusion de plus de quelques centaines
  d'éléments, payé à chaque rejeu.

### Ce qu'une mesure seule peut trancher

Le temps réel de `delete_items` de Docling sur un document plat de 300 pages pour k = 1 000 et
k = N ; le temps d'un aperçu après une telle suppression sauvegardée ; la part de la
sérialisation Rust de 13,8 Mo restée sur la loop ; le temps du `DELETE` d'une analyse de 300 pages
avec son cache, et celui de la resélection, cache OS chaud et froid ; le coût d'une connexion
aiosqlite par appel ; l'occupation réelle du pool pendant une frappe soutenue dans l'éditeur.

---

## Points positifs

- La réponse de l'éditeur ne bloque plus la loop pendant sa construction ; le saut de thread ne
  copie rien.
- Plus aucun algorithme quadratique dans le code du projet pour la suppression et la fusion.
- `show_sources` divise ses requêtes par trois environ.
- Sauvegarde de l'éditeur en un `executemany` sous `BEGIN IMMEDIATE`.
- Suppression d'une analyse et resélection atomiques, en une connexion, verrou pris d'entrée.
- Hachage paresseux dans `_has_stale_chunks`.

---

## Verdict partiel : GO

Score **95/100** (≥ 80), 0 CRIT, 0 MAJ, 3 MIN. Les deux régressions ciblées sont traitées
(réponse typée hors de la loop, `show_sources`). Rien de ce que le cycle a introduit ne coûte
davantage. Reste, non introduit par le cycle mais désormais chiffré : le coût de
`delete_items` de Docling, rejoué à chaque aperçu (correctif M : aperçu incrémental depuis le
cache, contournement de la recherche linéaire de Docling, test du cas plat). À traiter ensuite :
12.3.2 (M), `followActive` (S), WAL + `busy_timeout` + index partiel (S).
