# Rapport d'audit : Performance & Ressources

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code
**Baseline** : `release-0.7.3-reaudit/12-performance.md` (67/100, GO CONDITIONNEL, 0 CRIT, 2 MAJ, 6 MIN, 7 INFO) et `release-0.7.3/12-performance.md` (52/100)
**Delta examiné** : `git diff 1de1929..eade7fa`. Fichiers de la fiche touchés : `services/analysis_edit_service.py` (nouveau), `infra/docling_editor.py`, `infra/docling_projector.py`, `infra/docling_merger.py` (nouveaux), `persistence/analysis_edit_repo.py`, `persistence/document_analysis_repo.py` (nouveaux), `services/chunk_service.py`, `services/version_service.py`, `services/export_service.py`, `persistence/database.py`, `frontend/src/features/analysis-editor/` (nouveau), `features/document/{api,store}.ts`, `features/document/ui/BboxCanvas.vue`. Non touchés : `infra/page_raster.py`, `services/document_service.py`, `services/source_service.py`, `services/citation_service.py`, `services/parse_loader.py`, templates nginx, `frontend/public/`.

Méthode : lecture statique uniquement. **Aucune exécution** (ni pytest, ni l'app, ni script
de mesure : consigne, machine occupée). L'ordre de grandeur du coût de projection
(~1,4 s CPU pour un document de 28 pages) est **repris de la revue antérieure de la PR
#319/#388, non re-mesuré ici**. Les autres coûts sont qualifiés PLAUSIBLE.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 7 / 13 |
| Score | 52 / 100 |
| Écarts CRITICAL | 1 |
| Écarts MAJOR | 2 |
| Écarts MINOR | 7 |
| Écarts INFO | 7 |

### Détail par item

| # | Item | Poids | Re-audit 0.7.3 | 0.7.4 (`eade7fa`) |
|---|------|-------|----------------|-------------------|
| 12.1.1 | Pas de requête N+1 | 2 | Non | Non (réduit : ~3N → ~N connexions) |
| 12.1.2 | Fichiers uploadés temporaires supprimés | 2 | Oui | Oui |
| 12.1.3 | `MAX_CONCURRENT_ANALYSES` configurée et respectée | 2 | Oui | Oui |
| 12.1.4 | Opérations longues hors event loop | 3 | Oui | **Non — régression (éditeur)** |
| 12.1.5 | Pas de fichier entier en mémoire sans nécessité | 2 | Non | Non |
| 12.2.1 | Watchers Vue avec cleanup | 2 | Oui | Oui |
| 12.2.2 | Event listeners supprimés au démontage | 2 | Oui | Oui |
| 12.2.3 | Annulation ou debounce des requêtes | 1 | Oui | Oui |
| 12.2.4 | Pas de re-render excessif | 1 | Oui | Oui |
| 12.2.5 | Assets lourds optimisés | 1 | Non | Non |
| 12.3.1 | Cache nginx pour les fichiers statiques | 1 | Non | Non |
| 12.3.2 | Réponses API de taille raisonnable | 1 | Non | Non (aggravé par l'éditeur) |
| 12.3.3 | Health check léger | 1 | Oui | Oui |

Poids total = 21. Non conformes : 12.1.1 (2) + 12.1.4 (3) + 12.1.5 (2) + 12.2.5 (1) +
12.3.1 (1) + 12.3.2 (1) = 10. Poids conformes = 11. `11 / 21 * 100 = 52,4` → **52 / 100**.

Delta vs re-audit 0.7.3 : **67 → 52** (−3 points de poids, 12.1.4). C'est le score du
premier passage 0.7.3, pour la même raison (travail Docling sur l'event loop), sur un
autre chemin.

---

## Écarts constatés

### [CRIT] Rejeu et projection de l'éditeur exécutés de façon synchrone sur l'event loop, sur des chemins de navigation courants (item 12.1.4)

- **Localisation** :
  - travail CPU : `document-parser/services/analysis_edit_service.py:298-311` (`_project` :
    `self._editor.apply(...)` puis `self._projector.project(...)`, appels **synchrones**
    dans des coroutines) ; `:94-98` (chemin « cache » : `project_serialized`, synchrone
    aussi) ; aucun `asyncio.to_thread` dans le fichier.
  - ce que coûte un appel : `infra/docling_editor.py:44` (`model_validate_json` du
    document complet), `:53-61` (`validate_tree`, `validate_document`, puis aller-retour
    `model_dump_json` + `model_validate_json` + `validate_tree`) ;
    `infra/docling_projector.py:42-62` (parcours, résolution des parents/enfants,
    pages, arbre), `:64` (`model_copy(deep=True)`), `:72-76` (`model_dump_json`,
    `export_to_markdown`, `export_to_html`, `json.dumps` ×2) ; `:91` (revalidation complète
    dans `project_serialized`). Puis `api/analysis_edits.py:60` (`json.loads` du modèle) et
    sérialisation de la réponse.
  - points d'entrée (tous `async`) : `load_editor` `:75-103`, `preview` `:120-133`,
    `save` `:135-207` (`_project` l.172), `set_command_active` `:209-246` (→ `save`),
    `rebuild` `:248-269` (l.253), `active_result` `:105-111` (→ `load_editor`).
  - appelants hors de l'éditeur : export md/json par défaut
    `services/export_service.py:78-79,96-97,121-125` et export `edited`
    `:127-131` ; rechunk `services/chunk_service.py:376-381` ; arbre sans `analysisId`
    `:712-716`.
  - déclencheurs côté front : **chaque ouverture du workspace d'un document**
    (`frontend/src/features/document/store.ts:25-34`, appelé l.162, 191 et 215 : appel
    `/analysis-editor` dès que le flag est actif et que l'analyse a un JSON Docling) ;
    ouverture de l'éditeur (`features/analysis-editor/store.ts:82`) ; **chaque
    modification** en cours d'édition (aperçu après 400 ms d'inactivité, l.106-108 → l.214) ;
    chaque sauvegarde, qui enchaîne **deux** projections (save l.240, puis rechargement
    l.248).
- **Constat** : pour un document de 28 pages, la revue antérieure a mesuré ~1,4 s de CPU
  pour charger l'éditeur. Pendant ce temps, l'event loop est occupé : **toutes** les
  requêtes du processus sont gelées (polling des analyses, previews de pages, `/mcp`,
  `/api/health`, progression des conversions). Le coût croît avec la taille du document,
  avec le nombre de commandes rejouées, et il n'y a pas de borne sur ces commandes (voir
  audit 08, [MIN] « routes de l'éditeur non bornées »).
  Le cache mono-slot ajouté (`analysis_edit_service.py:73,81-85,101-102`) ne couvre que
  le cas « analyse **non éditée**, même analyse que la requête précédente » : il est
  vidé dès qu'on ouvre un autre document, et il ne sert jamais une analyse éditée. Pour
  une analyse éditée, le cache persistant (`edited_analysis_cache`) évite le rejeu des
  commandes, mais `project_serialized` (`docling_projector.py:83-98`) revalide le document
  et refait toute la projection (copie profonde et deux exports compris) : le gain est
  partiel.
  Le reste du code fait l'inverse pour le même type de travail : conversion
  (`infra/local_converter.py:201,204`), chunking (`infra/local_chunker.py:106`) et import
  Docling (`services/analysis_service.py:180`, correctif #audit-12 de 0.7.3).
- **Classement** : poids 3, donc CRIT selon la fiche. Les audits 0.5.0, 0.6.1 et 0.7.3 ont
  ramené cet item à MAJ pour un **chemin unique, déclenché manuellement** (l'import). Ces
  conditions ne sont pas réunies ici : le chemin est emprunté à chaque ouverture de
  workspace et à chaque frappe (aperçu) pendant l'édition, et les routes d'export et de
  rechunk par défaut en héritent. Je n'applique donc pas la contextualisation. Le verdict
  de l'audit ne dépend pas de ce choix : avec un MAJ, le score serait le même (52 < 60,
  NO-GO).
- **Règle violée** : 12.1.4 (poids 3).
- **Remédiation** (effort S) : dans `AnalysisEditService`, exécuter `_project` et
  `project_serialized` via `await asyncio.to_thread(...)` (l'éditeur et le projecteur
  sont sans état, `infra/docling_editor.py:33`, `infra/docling_projector.py:31`), ainsi que
  `json.loads(editor_model_json)` côté API ou dans le même thread. Ajouter un test du même
  type que `tests/test_analysis_service.py` (#audit-12) : le projecteur ne doit voir
  aucune boucle en cours. En complément (M) : un sémaphore d'éditeur pour éviter N
  projections parallèles en mémoire, et un cache LRU de quelques entrées au lieu du slot
  unique.

### [MAJ] Fichier PDF entier relu en mémoire pour chaque page rendue — inchangé (item 12.1.5)

- **Localisation** : `document-parser/infra/page_raster.py:26-28` (`read_bytes` puis
  `convert_from_bytes`) ; `document-parser/api/documents.py:189-194` +
  `services/document_service.py:160-162` (`/preview`) ; `api/documents.py:217-220` +
  `services/document_service.py:171-176` (`/pages`, `pdfium.PdfDocument(file_content)`).
- **Constat** : fichiers inchangés depuis 0.7.3, analyse reprise. Tout le PDF (jusqu'à
  50 Mo) est lu puis réécrit dans un fichier temporaire par `pdf2image` pour rendre une
  page. L'éditeur s'appuie sur ces rendus (`AnalysisEditor.vue:303`,
  `PagePreviewWithOverlay`), donc chaque page affichée dans l'éditeur paie ce coût.
- **Règle violée** : 12.1.5 (poids 2).
- **Remédiation** : `convert_from_path(storage_path, first_page=page, last_page=page, dpi=dpi)`
  et `pdfium.PdfDocument(path)` sous le verrou pdfium. Effort S.

### [MAJ] Boucles d'écriture une-requête-par-chunk — réduit mais toujours présent (item 12.1.1)

- **Localisation** : `document-parser/services/chunk_service.py:397-398`
  (`rechunk_document`), `:357-358` (`merge_chunks`), `:752-758` (`_shift_sequences`) ;
  `document-parser/services/version_service.py:185-186` (`restore`) ; une connexion et un
  `commit` par appel : `persistence/chunk_repo.py:104-111`,
  `persistence/database.py:367-373`.
- **Constat** : la suppression du journal `chunk_edits` (#388) a retiré l'`insert` d'audit
  qui accompagnait chaque chunk : un rechunk ou une restauration de N chunks passe de ~3N
  à ~N connexions et transactions (les insertions passent par `insert_many`). Il reste un
  `soft_delete` unitaire par chunk existant, et un `update` par chunk décalé.
  Le code neuf est sain sur ce point : les commandes d'édition sont insérées dans une seule
  transaction (`persistence/analysis_edit_repo.py:149-203`) et un chargement d'éditeur fait
  un nombre **constant** de requêtes (~8), indépendant de la taille du document.
- **Règle violée** : 12.1.1 (poids 2).
- **Remédiation** : `soft_delete_for_document(document_id, at)` en un seul `UPDATE` ;
  `_shift_sequences` en un `UPDATE chunks SET sequence = sequence + 1 WHERE document_id = ?
  AND sequence >= ? AND deleted_at IS NULL`. Effort S.

### [MIN] Réponses de l'éditeur volumineuses et redondantes ; double chargement au workspace (item 12.3.2)

- **Localisation** : `document-parser/api/schemas.py:199-207` (`AnalysisEditorResponse` :
  `model` avec le texte de chaque élément, `tree` dont chaque `label` est encore le texte
  de l'élément `infra/docling_projector.py:213`, `result` avec `contentMarkdown`,
  `contentHtml` et `pagesJson` qui contient encore le texte, `api/analysis_edits.py:30-47`) ;
  renvoyée par **chaque** aperçu (`features/analysis-editor/store.ts:214`). Workspace :
  `frontend/src/features/document/store.ts:26-28` charge l'analyse de base complète puis la
  réponse complète de l'éditeur, pour n'en garder que trois champs (l.29-34).
  Écarts déjà ouverts : `frontend/src/features/analysis/store.ts:54`
  (`api.fetchAnalyses()`), `frontend/src/pages/DocsLibraryPage.vue:345`.
- **Constat** : le texte du document part ~5 fois par réponse (modèle, arbre, pages,
  Markdown, HTML) ; le workspace télécharge deux fois le résultat. Ordre de grandeur
  PLAUSIBLE : quelques Mo par aperçu pour un document de plusieurs centaines de pages.
- **Règle violée** : 12.3.2 (poids 1).
- **Remédiation** : un endpoint léger « résultat actif » (Markdown, HTML, pages) pour le
  workspace ; dans l'aperçu, ne renvoyer que ce qui change (ou omettre `contentHtml`, que
  le front n'affiche pas) ; `tree` en ids + type, le libellé étant lu dans `model`. Effort M.

### [MIN] `show_sources` recharge la même parse pour chaque citation — inchangé

- **Localisation** : `services/source_service.py:102` → `services/citation_service.py:99` →
  `services/parse_loader.py:78,83`.
- **Remédiation** : charger la parse une fois par appel.

### [MIN] Logo PNG 1024×1024 (~858 Kio) servi en favicon — inchangé (item 12.2.5)

- **Localisation** : `frontend/public/logo.png` (878 643 octets), `frontend/index.html:7`.
- **Règle violée** : 12.2.5 (poids 1).
- **Remédiation** : `favicon.svg`, logo compressé (< ~100 Kio). Effort S.

### [MIN] Nginx sans cache pour les fichiers statiques — inchangé (item 12.3.1)

- **Localisation** : `nginx.conf.template:13-15`, `frontend/nginx.conf.template:13-15`.
- **Règle violée** : 12.3.1 (poids 1).
- **Remédiation** : `expires 1y` + `Cache-Control "public, immutable"` sur `/assets/`,
  `no-cache` sur `index.html`. Effort S.

### [MIN] pdfium appelé hors du verrou partagé avec Docling (hors checklist, PLAUSIBLE) — inchangé

- **Localisation** : `services/document_service.py:176` ; `services/analysis_service.py:59-68`
  (`_count_pdf_pages`, appelé sur la loop l.449).
- **Remédiation** : même verrou que `infra/page_text.py` ; `_count_pdf_pages` en thread.

### [MIN] Suivi à 3 s sans borne de durée (hors checklist) — inchangé

- **Localisation** : `frontend/src/features/analysis/store.ts` (`followActive`).
- **Remédiation** : réconciliation au boot des analyses `PENDING`/`RUNNING` ; plafond de
  durée.

### [MIN] Coûts quadratiques dans le rejeu des commandes (hors checklist, nouveau)

- **Localisation** : `document-parser/infra/docling_editor.py:157-163` (`_delete_elements` :
  `_is_descendant` pour chaque paire d'ids, O(k²·profondeur)) ; `:89-99`
  (`_in_document_order` réénumère tout le document à chaque `mergeText`, donc
  O(fusions × éléments) au rejeu) ; `infra/docling_projector.py:115-119` (chaque enfant
  résolu deux fois).
- **Constat** : négligeable pour un usage normal ; devient significatif avec de longues
  sélections ou des centaines de fusions rejouées, sur l'event loop tant que le CRIT n'est
  pas corrigé. N'affecte pas le score.
- **Remédiation** : index de position et ensemble d'ancêtres calculés une fois par rejeu.

### [INFO] Reliquat CPU sur l'event loop (mis à jour)

- **Localisation** : `services/analysis_edit_service.py:82,148,175,353` (`sha256` du
  document complet, plusieurs fois par requête) ; `services/chunk_service.py:425`
  (idem au rechunk) ; `services/analysis_service.py:467` (`pages_json`) ;
  `infra/neo4j/tree_writer.py` (prétraitement, si Neo4j est branché, appelé aussi par
  `save` l.196-206).
- **Constat** : linéaire, rapide (hash en C). À regrouper dans le thread de projection
  quand le CRIT sera corrigé.

### [INFO] Projections parallèles non bornées

- **Localisation** : `services/analysis_edit_service.py` (aucun sémaphore) ;
  `services/analysis_service.py:424` (le sémaphore ne couvre que les conversions).
- **Constat** : aujourd'hui sérialisées de fait par la loop bloquée ; une fois en thread,
  plusieurs aperçus ou ouvertures de workspace tourneront en parallèle, chacun avec deux
  copies du document plus les exports. Prévoir un sémaphore (cf. remédiation du CRIT).

### [INFO] Minuteur d'aperçu non annulé au démontage de l'éditeur

- **Localisation** : `frontend/src/features/analysis-editor/store.ts:33,108` (store Pinia
  global) ; `ui/AnalysisEditor.vue:481-485` (`onBeforeUnmount` n'appelle pas
  `clearTimeout` sur ce minuteur ni `abort`).
- **Constat** : si l'on quitte l'éditeur moins de 400 ms après une frappe, un aperçu part
  quand même (une projection serveur inutile). Pas de fuite durable (le minuteur est
  unique). 12.2.2 reste conforme : les listeners `window` sont bien retirés (l.477-478 /
  482-483).

### [INFO] Cache mono-slot partagé entre documents

- **Localisation** : `services/analysis_edit_service.py:73,81-85,101-102`.
- **Constat** : un seul tuple pour tout le processus ; deux onglets sur deux documents se
  l'arrachent. Le cache garde aussi en RAM un `ProjectedAnalysis` complet (JSON, Markdown,
  HTML, pages, modèle) : borné à un document, acceptable.

### [INFO] Polling des résumés, `/summaries`, budgets MCP, fusion des lots — inchangés

- **Localisation** : `frontend/src/features/analysis/store.ts`,
  `persistence/analysis_repo.py`, `services/navigation_config.py:36-54`,
  `services/analysis_service.py` (fusion des lots) ; voir le re-audit 0.7.3.

### [INFO] Observations reportées de 0.7.0 — inchangées

- Connexion neuve par appel, pas de WAL (`persistence/database.py:367-373`) ; upload en
  mémoire borné (`api/documents.py:76-87`).

### [INFO] Cleanup front : bonnes pratiques sur le code neuf

- `features/document/ui/BboxCanvas.vue:254-275` : `ResizeObserver` déconnecté via
  `onCleanup` et au démontage, `cancelAnimationFrame` ; `AnalysisEditor.vue:476-485`
  (listeners `keydown` / `beforeunload` retirés, minuteur de notice annulé) ;
  aperçu annulable (`AbortController`, `store.ts:206-223`) et différé de 400 ms. Ce sont
  les preuves de conformité de 12.2.1 à 12.2.3.

---

## Statut des écarts du re-audit 0.7.3

| Écart 0.7.3 | Statut à `eade7fa` |
|---|---|
| [MAJ] PDF entier relu par page rendue (12.1.5) | **Toujours ouvert**, fichiers inchangés |
| [MAJ] Boucles une-requête-par-chunk (12.1.1) | **Toujours ouvert**, réduit (~3N → ~N) par la suppression de `chunk_edits` |
| [MIN] N+1 `show_sources` | Inchangé |
| [MIN] Bibliothèque sur la liste complète (12.3.2) | Inchangé ; 12.3.2 aggravé par l'éditeur |
| [MIN] Logo / favicon (12.2.5) | Inchangé |
| [MIN] Pas de cache nginx (12.3.1) | Inchangé |
| [MIN] pdfium hors verrou | Inchangé |
| [MIN] Suivi à 3 s sans borne | Inchangé |
| [INFO] Reliquat CPU, imports parallèles, polling, `/summaries`, MCP, lots, reports 0.7.0 | Inchangés ou mis à jour |
| — | **Nouveau [CRIT]** 12.1.4 : projection de l'éditeur sur l'event loop |
| — | **Nouveaux [MIN]** : réponses de l'éditeur redondantes (12.3.2), coûts quadratiques du rejeu |

---

## Points positifs

- **Persistance de l'éditeur bien conçue côté I/O** : append des commandes et mise à jour
  du cache dans **une** transaction ; nombre de requêtes constant par chargement.
- **Cache persistant du résultat édité** : le rejeu complet des commandes n'a lieu qu'au
  premier calcul ou au `rebuild`.
- **Front de l'éditeur sobre** : aperçu différé de 400 ms et annulable, regroupement des
  frappes (`commands.ts:31-52`), arbre replié au-delà de 1 000 éléments
  (`AnalysisEditor.vue:487-497`), listeners et observers nettoyés.
- **Suppression du journal `chunk_edits`** : divise par trois les écritures d'un rechunk
  ou d'une restauration.
- Acquis de 0.7.3 conservés : import et conversion en thread, sémaphore
  (`services/analysis_service.py:100,424`), health check `SELECT 1` (`main.py:136`),
  suppression des fichiers temporaires (`services/document_service.py:96`).

---

## Verdict partiel : NO-GO

Score **52/100** (< 60) et **1 CRIT** non résolu : NO-GO par les deux règles du master.
2 MAJ (≤ 3).

Plan de remédiation, par gain :
1. [CRIT 12.1.4] `asyncio.to_thread` autour de `_project` et `project_serialized` dans
   `AnalysisEditService`, plus un test « pas de loop dans le projecteur » (S) → +3 ⇒
   **67, GO CONDITIONNEL**.
2. [MAJ 12.1.1] `soft_delete` groupé et `_shift_sequences` en un `UPDATE` (S) → +2 ⇒ 76.
3. [MAJ 12.1.5] rendus de page depuis le chemin du fichier (S) → +2 ⇒ **86, GO**.
4. [MIN] Endpoint « résultat actif » léger pour le workspace, aperçu allégé (M) → +1.
