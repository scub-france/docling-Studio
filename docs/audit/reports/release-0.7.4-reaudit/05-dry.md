# Rapport d'audit : DRY (Don't Repeat Yourself) — re-audit

**Release** : 0.7.4 (re-audit apres remediation)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` @ `a4d9679` (code audite ; HEAD `4c59df0` n'ajoute que deux rapports de re-audit, aucun fichier de code)

Baseline : `reports/release-0.7.4/05-dry.md` (67/100, 3 MAJ, 16 MIN, 6 INFO, code `1de1929`,
rapport commite en `e6047c2`). Perimetre identique : `document-parser/` (hors `.venv/`,
`__pycache__/`, `tests/`) et `frontend/src/` (hors `*.test.*`).

> **Score 67 → 100 en lecture 0.7.4 ; 83 en lecture stricte de 5.3.** Les trois MAJ sont
> traites. `_parse_iso` x7 est remplace par un seul module (`persistence/timestamps.py`), et la
> divergence UTC a disparu. Le contrat d'erreur repose sur une seule base `ServiceError` et un
> seul handler : il reste 0 des 6 bases et des 16 mappings. Les 74 sites de couleurs
> inventories en 0.7.4 sont soldes (73, plus 1 exception assumee). Deux MIN sont corriges
> (journal `ChunkEdit`, regles split/merge) et deux passent en INFO (serialisation de chunk,
> labels Docling).
>
> Deux reliquats sont releves en MIN. (1) Le contrat d'erreur est contourne par 4 erreurs de
> service hors `ServiceError` : 3 ont ete **creees par la remediation** (`e68ee5a`). (2) 15
> couleurs de meme nature que le MAJ sont restees hors de l'inventaire 0.7.4 : 13 tokens jamais
> definis et 2 rouges bruts. En lecture 0.7.4, ou le basculement de 5.3 etait lie aux 74 sites,
> 5.3 est conforme. En lecture stricte, ou tout token non defini tient 5.3, l'item reste non
> conforme (83). Aucune regression n'est introduite par la remediation au-dela de ces deux points.

Methode :
- Chaque ecart du rapport 0.7.4 a ete re-verifie dans le code a `a4d9679`, et non dans les
  messages de commit.
- Les compteurs 0.7.4 ont ete recalcules par `git grep` sur `e6047c2` (code identique a `1de1929`)
  et sur HEAD. Les commandes de la fiche 05 ont ete rejouees.
- Detecteur de fenetres glissantes (4 et 6 lignes normalisees, hors blancs, commentaires et
  imports) lance sur les deux arbres. L'arbre `e6047c2` a ete extrait par `git archive` dans le
  scratchpad. Les seules fenetres nouvelles a HEAD sont triviales : injection de constructeur
  (`document_tree_service.py:29` / `parse_loader.py:46`), signatures (`store_service.py:205` /
  `:259`) et passage de parametres (`api/stores.py:96` / `:124`).
- Script hors depot listant les custom properties CSS referencees mais jamais definies (`App.vue`
  et SFC).
- OpenAPI de l'application reelle (`main.app.openapi()`) inspectee pour les schemas ajoutes par la
  remediation. Le detail est dans le re-audit 07.
- Tests cibles : `test_timestamps.py`, `test_api_errors.py`, `test_chunk_serialization.py`,
  `test_chunk_editing.py`, `test_architecture.py`, `test_graph_api.py`, `test_api_stores.py` :
  **151 passed**.
- Suites completes non relancees. Resultats du coordinateur sur HEAD :
  - backend : `ruff check` et `ruff format --check` OK, pytest 1673 passed / 19 skipped ;
  - frontend : eslint, prettier, vue-tsc OK, vitest 522 passed, vite build OK.
- Le rendu visuel n'a pas ete verifie (application non lancee). Les effets visuels decrits plus
  bas sont deduits des regles CSS.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 7 |
| Score | 100 / 100 (83 en lecture stricte de 5.3) |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 (1 en lecture stricte de 5.3) |
| Ecarts MINOR | 14 |
| Ecarts INFO | 8 |

| # | Item | Poids | 0.7.4 (`1de1929`) | Re-audit (`a4d9679`) | Justification |
|---|------|-------|-------------------|----------------------|---------------|
| 5.1 | Aucun bloc identique/quasi-identique 3+ fois sans factorisation | 2 | Non | **Oui** | Les deux MAJ qui le tenaient sont corriges (`_parse_iso`, contrat d'erreur). Restent des MIN d'ampleur limitee, toleres comme en 0.7.4 (reliquat du contrat d'erreur, pont MCP, import x3, `formatDate` x3, squelette Pinia, etc.) |
| 5.2 | Types partages centralises (`shared/types.ts` / `domain/models.py`) | 2 | Oui | **Oui** | Aucun nom de type exporte en double dans `frontend/src`. Les nouveaux types TS (`StoreConfig`, `GraphNode`, `GraphProvenance`) restent locaux a leur feature |
| 5.3 | Pas de magic numbers/strings eparpilles — constantes nommees et centralisees | 2 | Non | **Oui** (lecture 0.7.4) / Non (lecture stricte) | Inventaire 0.7.4 solde : 74 → 1, exception assumee. Reliquat hors inventaire de meme nature (13 tokens non definis, 2 rouges bruts) releve en MIN, cf. « Lecture des items » |
| 5.4 | Logique reactive partagee dans `shared/composables/` | 1 | Oui | **Oui** | Inchange |
| 5.5 | Appels API sans duplication de config HTTP — `shared/api/http.ts` | 2 | Oui | **Oui** | 11 `features/*/api.ts` + `graphApi.ts` passent par `apiFetch`. Seul `fetch()` brut : `DownloadDropdown.vue:133` (INFO) |
| 5.6 | Schemas Pydantic transforment le domain, ne le redefinissent pas | 2 | Oui | **Oui** | `StoreConfigResponse` / `GraphNode` typent des payloads `dict` du domaine (`api/graph.py:95-104`), ils ne redeclarent pas un modele. `AnalysisSummaryResponse` reste un MIN |
| 5.7 | Regles de validation a un seul endroit | 1 | Oui | **Oui** | Nouvelles bornes `READ_TOKENS_MIN/MAX` definies dans le domaine (`domain/mcp_config.py:34-35`), importees par `infra/settings.py:13-14`, miroir front aligne (`features/mcp-config/types.ts:61-62`). Garde SSRF unique injectee (`bootstrap/builder.py:163`) |

Poids total : 12. **Lecture 0.7.4 : 12 / 12 = 100.** Lecture stricte : 5.3 non conforme,
10 / 12 = 83,3, soit **83**. Delta : +33 (ou +16).

### Lecture des items

- **5.1** : meme lecture qu'en 0.7.4. Un item bascule quand plus aucun ecart MAJ ne le tient ;
  les MIN d'ampleur limitee sont toleres.
  - Le MAJ « contrat d'erreur » etait defini par 6 bases et 16 mappings : il en reste 0.
  - Le reliquat ne fait pas basculer l'item. Il comprend 4 classes hors contrat, 5 `ValueError`
    mappes et une garde recopiee 5 fois (blocs de 2 a 3 lignes).
- **5.3** : le rapport 0.7.4 donnait un inventaire dit « exhaustif » de 74 sites dans 5
  categories, et liait le basculement de 5.3 a leur traitement (« +17 une fois les 74 sites
  traites ou supprimes »). Cet inventaire est solde.
  - Ce re-audit trouve 15 sites de meme nature que l'inventaire n'avait pas vus. Il y a 13
    references a des tokens jamais definis (`--bg-tertiary`, `--bg-secondary`, …) : la
    categorie (a)/(c) de 0.7.4 sous d'autres noms. Il y a aussi 2 `#ef4444`, soit
    `--error` en clair (categorie (b), que 0.7.4 ne cherchait qu'en `#dc2626`).
  - **Lecture 0.7.4** (inventaire et convention « MIN d'ampleur limitee ») : 10 des 15 sites sont
    dans un composant de la route legacy `/studio`, et l'effet visuel est limite. Le reliquat est
    MIN et 5.3 est conforme. **Score retenu : 100.**
  - **Lecture stricte** : tout token non defini tient 5.3 non conforme, comme `--color-*` en
    0.7.0. Le MAJ couleurs est alors partiellement corrige et reste [MAJ] a perimetre reduit.
    Score : 83.

### Compteurs de duplication

| Compteur | 0.7.4 (`1de1929`) | Re-audit (`a4d9679`) |
|----------|-------------------|----------------------|
| Definitions `_parse_iso` / `_parse_dt` dans `persistence/` (+ parse inline) | 7 (+1) | **0** (helper unique `persistence/timestamps.py:15`) |
| Repli `or datetime.now(UTC)` sur une date lue en base | 5 | **0** (`parse_required_iso` leve `ValueError`, `timestamps.py:29-38`) |
| References `var(--color-*)` | 33 | **0** |
| Litteraux `#d1d5db` / `#6b7280` / `#dc2626` (casse exacte, `App.vue` inclus) | 7 / 12 / 11 | **0 / 0 / 2** (`App.vue:131` token clair `--error` ; `GraphView.vue:576` garde volontairement) |
| `var(--danger, …)` | 3 | **0** |
| Replis en dur `var(--<token defini>, #hex)` | 24 | **0** |
| References a des tokens jamais definis, hors `--color-*`/`--danger` (nouveau compteur) | 13 | 13 |
| `var(--on-accent)` / `white`·`#fff` en texte sur fond plein | — / 27 | 7 / 19 |
| Bases `XServiceError` avec `__init__(message, *, http_status=None)` recopie | 6 | **0** (base unique `services/errors.py:14`) |
| `HTTPException(status_code=<err>.http_status, …)` dans `api/` (inline + `_raise_for`) | 14 + 2 | **0 + 0** |
| Erreurs de service hors `ServiceError` mappees a la main dans `api/` (nouveau compteur) | 1 | 4 (+3 creees par `e68ee5a`) |
| `except ValueError` → `HTTPException` dans `api/` (hors parse d'enum) | 7 | 5 |
| Formes de « document introuvable » | 6 | 4 |
| SFC redefinissant `@keyframes spin` | 17 | 16 |
| Parse booleen `.lower() in ("1","true","yes","on")` dans `infra/settings.py` | 8 | 8 |
| Ensemble `{"page_header","page_footer"}` redeclare | 3 | 2 |
| Constructions `ChunkEdit(` dans `services/` | 10 | **0** (fabrique unique `domain/chunk_editing.py:210-219`) |
| Serialiseurs Chunk → dict camelCase | 4 | 2 |
| `function formatDate` locales dans `frontend/src` | 4 | 3 |
| `str(<datetime>)` dans `api/` | 13 | 13 |
| `(e as Error).message` dans `frontend/src` | 41 | 39 |

---

## Etat des ecarts 0.7.4

| Ecart 0.7.4 | Niveau | Statut re-audit | Preuve (`a4d9679`) |
|-------------|--------|-----------------|--------------------|
| `_parse_iso` / `_parse_dt` x7 + divergence UTC `analysis_repo` | MAJ | **Corrige** | `persistence/timestamps.py:15-38`, importe par les 7 repositories ; plus aucune definition locale |
| Couleurs UI en dur, tokens `--color-*` / `--danger` | MAJ | **Corrige sur l'inventaire 0.7.4** (73/74, 1 exception assumee) ; reliquat hors inventaire → nouveau MIN | 0 `--color-*`, 0 `--danger`, 0 repli `#hex` ; `--on-accent` `App.vue:89`, `:121` |
| Contrat d'erreur service → HTTP (6 bases, 16 mappings) | MAJ | **Corrige** ; reliquat → nouveau MIN | `services/errors.py:14-26`, `api/errors.py:24-30`, `main.py:90` |
| Pont JSON-RPC MCP Apps x2 | MIN | Inchange | voir MIN |
| Import d'analyse x3 | MIN | Inchange | voir MIN |
| Defauts / bornes / parse env MCP-Ask | MIN | Inchange (bornes `READ_TOKENS` ajoutees sans duplication) | voir MIN |
| Labels Docling | MIN | **Partiellement corrige → INFO** (2 copies) | voir INFO |
| `.field-*` formulaires de store | MIN | Inchange (perimetre deprecie) | voir MIN |
| Bornes de chunking / defauts DTO | MIN | Inchange | voir MIN |
| Primitives UI (spinner, boutons, switch, icone) | MIN | Inchange (17 → 16 `@keyframes spin`, `DocChunkTab` supprime) | voir MIN |
| Palette graphe Neo4j x3 | MIN | Inchange | voir MIN |
| `api/analyses.py` chunks x3 / resume | MIN | Inchange | voir MIN |
| `_utcnow` / `_new_id` x4, deux formats d'id | MIN | Inchange (une copie deplacee dans le nouveau `chunk_push_service.py`) | voir MIN |
| Serialisation Chunk ↔ dict x4 | MIN | **Partiellement corrige → INFO** (4 → 2) | voir INFO |
| Journal `ChunkEdit` x10 + remplacement de chunkset divergent | MIN | **Corrige** | `EditJournal` `domain/chunk_editing.py:159-219` ; `replace_chunkset` unique `persistence/chunk_repo.py:80` |
| Regles split / merge en double (domaine mort) | MIN | **Corrige** | `services/chunk_service.py:183` (`chunk_editing.split`), `:212` (`chunk_editing.merge`) |
| `formatDate` x4 | MIN | **Partiellement corrige** (4 → 3) | voir MIN |
| Squelette d'action Pinia | MIN | Inchange | voir MIN |
| `str(datetime)` x13 / deux formats sur le fil | MIN | Inchange | voir MIN |
| `fetch()` brut `DownloadDropdown` | INFO | Inchange | `DownloadDropdown.vue:133` |
| Constantes de troncature | INFO | Inchange | — |
| Config MCP vs Ask | INFO | Inchange | — |
| DTO MCP miroirs | INFO | Inchange (deplaces dans `mcp_adapter/sources_wire.py`) | — |
| Extraction pages Serve | INFO | Inchange | — |
| Redondances front sous le seuil | INFO | Inchange | — |

---

## Ecarts corriges (preuves)

### [MAJ → corrige] Helper de parsing ISO-datetime x7, divergence UTC

- `persistence/timestamps.py:15-26` (`parse_iso`). Une valeur naive est lue comme UTC (`:24-25`) ;
  un autre decalage est converti en UTC (`:26`). La divergence d'`analysis_repo` disparait :
  `analysis_repo.py:24-26` passe par le meme helper.
- `persistence/timestamps.py:29-38` (`parse_required_iso`) : une colonne `NOT NULL` vide leve
  `ValueError` au lieu de prendre « maintenant », ce qui supprime les 5 replis
  `or datetime.now(UTC)`.
- Consommateurs : `analysis_repo.py:7`, `document_repo.py:10` (le parse inline 0.7.4 devient
  `:30`), `chunk_repo.py:13`, `chunk_edit_repo.py:11`, `document_store_link_repo.py:8`,
  `document_version_repo.py:10`, `store_repo.py:26`.
- `git grep fromisoformat persistence/` ne trouve que `timestamps.py:23`. Tests :
  `tests/test_timestamps.py` (dans les 151 passes).

### [MAJ → corrige] Couleurs UI : inventaire 0.7.4 (74 sites)

- Les categories (a) `--color-*` (33), (c) `--danger` (3) et (d) replis en dur (24) sont toutes a
  0 dans `frontend/src`.
- (b) `#dc2626` / `#6b7280` brut : 14 sites sont partis avec le composant mort
  `IngestLaunchDialog.vue`, supprime. Les autres utilisent `var(--error)`. Un site est garde :
  `features/analysis/ui/GraphView.vue:575-577` (`.legend-chunk`). C'est la pastille de legende
  de la palette du graphe : elle doit egaler la couleur de noeud Cytoscape `Chunk: '#DC2626'`
  (`GraphView.vue:146`, `:310`) et non le rouge d'erreur. L'exception est coherente et
  rattachee au MIN « palette Neo4j ».
- (e) `--on-accent` est defini dans les deux themes (`app/App.vue:89`, `:121`) et consomme par
  `McpConfigSection.vue:663`, `:1041`, `:1047`, `ComingSoonShell.vue:99`, `StoreForm.vue:441`,
  `DocsNewPage.vue:379`, `DocsLibraryPage.vue:664`.
- Reliquat hors inventaire : voir le premier MIN ci-dessous.

### [MAJ → corrige] Contrat d'erreur service → HTTP

- Base unique : `services/errors.py:14-26` (`ServiceError`, `http_status` de classe, surcharge par
  instance `:23-26`).
- Les 7 familles en derivent : `store_service.py:40`, `graph_service.py:27`,
  `chunk_errors.py:27` (`ChunkServiceError` a quitte `chunk_service.py`), `version_service.py:55`,
  `reasoning_service.py:28`, `navigation_errors.py:18`, `config_overrides.py:27`.
- Handler unique : `api/errors.py:24-30`, enregistre en `main.py:90`. `api/reasoning.py:35-39`
  relance les `ServiceError` avant son catch-all.
- Resultats :
  - `git grep "http_status" api/` ne trouve que le handler ;
  - plus de `_raise_for` ;
  - plus de choix de statut sur le prefixe du message (`api/analyses.py:139-145`) ;
  - une seule `DocumentNotFoundError` (`navigation_errors.py:24`), levee par
    `chunk_errors.py:64`, `analysis_service.py:137`, `:165` et `parse_loader.py:80`.
- Le filtre MCP reste borne a la famille navigation (`mcp_adapter/tool_errors.py:46`).
- Tests : `tests/test_api_errors.py` (7 tests). Reliquat : voir le deuxieme MIN ci-dessous.

### [MIN → corrige] Journal `ChunkEdit` x10 et remplacement de chunkset

- `EditJournal` (`domain/chunk_editing.py:159-219`) est la seule fabrique de lignes
  `chunk_edits` : `git grep "ChunkEdit("` hors tests ne trouve que `chunk_editing.py:211` et le
  mapper `persistence/chunk_edit_repo.py:20`.
- `replace_chunkset` est unique (port `domain/ports.py:204`, adaptateur
  `persistence/chunk_repo.py:80`). Il est appele par l'analyse initiale
  (`chunk_service.py:113-115`), le rechunk (`:248-255`) et le restore (`version_service.py:158-170`).
- Le restore sans instantane devient un choix nomme et commente : `without_snapshot`
  (`chunk_editing.py:205-208`), `version_service.py:156-157`.

### [MIN → corrige] Regles split / merge en double

- `ChunkService` appelle le domaine : `sequence_after` (`chunk_service.py:134`), `split` (`:183`),
  `merge` (`:212`), `chunkset_from_results` (`:245`).
- Les refus du domaine sont traduits par `refusals_as_service_errors` (`chunk_errors.py:51-57`).
  Une seule implementation des regles subsiste.

---

## Ecarts constates

### [MIN] Couleurs : reliquat hors inventaire 0.7.4 — 13 tokens jamais definis, rouges bruts, `--on-accent` adopte a moitie (nouveau, preexistant)

**Statut : nouveau dans ce rapport.** L'ecart est preexistant : les 13 references sont
identiques a `e6047c2`. Il est de meme nature que le MAJ couleurs 0.7.4 ; c'est un MAJ en lecture
stricte, cf. « Lecture des items ».

- **Localisation** :
  - **(a) tokens references, definis nulle part — 13 sites, 8 noms** :
    - sans repli (la propriete devient invalide : fond transparent, ombre absente) :
      - `frontend/src/features/chunking/ui/ChunkPanel.vue:407` et `:512` (`--bg-secondary`) ;
      - `ChunkPanel.vue:438`, `:548`, `:612`, `:676`, `:737` (`--bg-tertiary`) ;
      - `frontend/src/pages/StudioPage.vue:1264` (`--bg-primary`) ;
      - `frontend/src/features/document/ui/DocumentActionsMenu.vue:133` (`--shadow-lg`) ;
    - avec repli :
      - `ChunkPanel.vue:563` (`--accent-bg`, repli indigo `rgba(99, 102, 241, 0.1)` alors que
        l'accent est orange) ;
      - `frontend/src/features/chunks/ui/ChunkItem.vue:211` (`--border-hover`, repli
        `--border`) ;
      - `frontend/src/features/document/ui/DocTreeNode.vue:131` (`--warning-muted`) ;
      - `frontend/src/features/chunks/ui/StaleStoresStrip.vue:118` (`--warning-bg`) : ligne
        voisine des `:119-120` corrigees par la remediation ;
  - **(b) rouge d'erreur en clair `#ef4444`** (`--error` du theme sombre) : `ChunkPanel.vue:620`,
    `:727` ;
  - **(c) surfaces codees en dur qui ne suivent pas le theme** :
    - `frontend/src/pages/DocsLibraryPage.vue:416-418` (`.flash--warning`, ambre clair dans les
      deux themes) ;
    - `frontend/src/features/store/ui/StoreForm.vue:426-427` (perimetre deprecie) ;
    - `frontend/src/features/chunks/ui/StrategyPopover.vue:361-362` (`#b91c1c`) ;
    - `ChunkPanel.vue:523`, `:527`, `:571` (`#f59e0b`) ;
    - `frontend/src/shared/ui/StatusBadge.vue:58` (`#818cf8`) ;
  - **(d) `--on-accent` adopte a 7 sites ; 19 `white` / `#fff` restent pour du texte ou un spinner
    sur fond plein**, par exemple :
    - `frontend/src/features/reasoning/ui/Composer.vue:122` (`#fff` sur `var(--accent)`) ;
    - `ElementProperties.vue:430`, `ChunksEditor.vue:370`, `:596`, `AnalysisPanel.vue:120` ;
    - `GraphView.vue:635`, `StudioPage.vue:864`, `DocumentsPage.vue:292`, `ChunkPanel.vue:481`,
      `:667`.
- **Constat** :
  - L'inventaire 0.7.4 ne cherchait que le namespace `--color-*`, `--danger`,
    `#dc2626` / `#6b7280` / `#d1d5db` en casse exacte, et les replis. Les noms ci-dessus lui ont
    echappe.
  - 10 des 15 sites (a) + (b) sont dans `ChunkPanel.vue`, consomme par la page legacy `/studio`
    (`app/router/routes.ts:24-27`). Les 4 sites du workspace documentaire courant ont un repli,
    sauf `--shadow-lg` (menu d'actions sans ombre).
  - (d) n'a pas d'effet visuel aujourd'hui, car `--on-accent` vaut `#ffffff` dans les deux themes.
    Mais le token cree pour ce role n'est pas la source unique.
  - Le CHANGELOG `[Unreleased]` › Fixed (« Every hard-coded colour now uses the theme's tokens »)
    est donc inexact. Ce point est signale pour l'audit 11.
- **Regle violee** : item 5.3 (poids 2). C'est un MIN en lecture 0.7.4, un MAJ en lecture stricte.
- **Remediation** :
  - `--bg-secondary` → `--bg-surface` ;
  - `--bg-tertiary` → `--bg-elevated` ;
  - `--bg-primary` → `--bg` ;
  - `--accent-bg` → `--accent-muted` ;
  - `--border-hover` → `--border-light` ;
  - definir `--warning-muted` et `--shadow-lg` dans `App.vue` (clair et sombre), ou les remplacer ;
  - `#ef4444` → `var(--error)` ;
  - tokeniser `.flash--warning` ;
  - `white` / `#fff` sur accent → `var(--on-accent)` ;
  - ajouter un garde (test vitest ou script lint, ~10 lignes) qui echoue sur toute
    `var(--x)` non definie dans `App.vue`, pour que le compteur ne remonte pas.
- **Effort** : S (15 sites (a) + (b), 19 sites (d) mecaniques). **Risque** : visuel faible ; une
  verification clair + sombre de `/studio` et du menu d'actions documentaire est requise.

### [MIN] Contrat d'erreur unique contourne : 4 erreurs de service hors `ServiceError`, `ValueError` mappe a la main, « introuvable » en 4 formes (nouveau ; en partie introduit par la remediation)

**Statut : nouveau dans ce rapport.** C'est le reliquat du MAJ corrige. Trois des quatre classes
ont ete **creees par la remediation** : `e68ee5a` (#audit-06, PDF derriere des ports), 8 commits
avant l'introduction de `ServiceError` par `cb1e3b9`, qui ne les a pas rattachees.

- **Localisation** :
  - **erreurs typees hors contrat, mappees une a une** :
    - `services/document_service.py:40` (`PageOutOfRangeError(Exception)`), `:47`
      (`PageNotFoundError`), `:54` (`DocumentFileError`) → `api/documents.py:157-170`
      (400 / 404 / 422) et `:186-192` ;
    - `services/export_service.py:113` (`ExportNotFoundError(Exception)`, preexistante) →
      `api/documents.py:130-133` (404).
    - Les trois clauses `:132-133`, `:159-160`, `:161-162` sont exactement
      `raise HTTPException(status_code=N, detail=str(exc)) from exc`, le motif que le handler
      factorise.
  - **blocs `FileNotFoundError` → 404 / `OSError` → 422** toujours recopies entre `/preview`
    (`api/documents.py:163-167`) et `/pages` (`:188-192`) ;
  - **`ValueError` → 400 au cas par cas** (7 en 0.7.4) : `api/analyses.py:141-145`, `:206-207`,
    `:230-231`, `:253-254`, `api/documents.py:87-88`.
    - `services/analysis_service.py:214`, `:238`, `:260` levent `ValueError("Analysis not found")`,
      repondu 400.
    - La meme absence repond 404 sur `GET /api/analyses/{id}` (`api/analyses.py:195`) et dans
      `services/document_tree_service.py:50` (`ChunkNotFoundError`).
  - **« document introuvable » en 4 formes** (6 en 0.7.4) :
    1. `DocumentNotFoundError` (`services/navigation_errors.py:24`) ;
    2. `VersionServiceError(…, http_status=404)` (`services/version_service.py:182-185`) ;
    3. `ExportNotFoundError("Document not found")` (`services/export_service.py:61`) ;
    4. `HTTPException(404, "Document not found")` apres un `None` / `False` du service
       (`api/documents.py:105`, `:115`, `:172`, `:194`).
  - **garde « charger le document ou 404 »** :
    - un helper partage, `require_document` (`services/chunk_errors.py:60-65`, 8 appels) ;
    - 5 copies en ligne : `analysis_service.py:135-137`, `:163-165`, `parse_loader.py:78-80`,
      `export_service.py:59-61`, `version_service.py:182-185`.
- **Constat** : le mecanisme est en place et teste. Mais un nouveau service peut encore lever une
  `Exception` maison, et le routeur la retraduit a la main : c'est arrive dans la remediation
  elle-meme. `VersionService` garde sa garde privee alors que `require_document` existe a cote.
- **Regle violee** : item 5.1. Non bloquant : 4 classes et des blocs de 2 a 3 lignes.
- **Remediation** :
  - faire deriver `PageOutOfRangeError` (400), `PageNotFoundError` (404) et `ExportNotFoundError`
    (404) de `ServiceError`, et supprimer leurs `except` ;
  - `DocumentFileError` : `ServiceError` 422 si le libelle peut venir du service ;
  - remonter `require_document` dans `services/errors.py` ou `navigation_errors.py`, et l'utiliser
    dans `version_service`, `analysis_service`, `parse_loader` ;
  - une `AnalysisNotFoundError(ServiceError)` 404 pour `analysis_service` : 3 routes legacy passent
    alors de 400 a 404, a acter.
- **Effort** : S. **Risque** : faible ; codes inchanges sauf le 400 → 404 optionnel. Couvert par
  `tests/test_api_errors.py` et les tests d'API documents.

### [MIN] Pont JSON-RPC MCP Apps recopie dans les deux cartes HTML

**Statut : inchange.**

- **Localisation** :
  - `document-parser/mcp_adapter/citation_app.html` : `post` `:690`, `call` `:701`, `settle`
    `:713`, `PROTOCOL_VERSION` `:732`, `handshake` `:737`, `applyHostContext` `:768`,
    `applyContainerDimensions` `:787`, `reportSize` `:1082`, `extract` `:1122`, ecouteur
    `message` `:1140` ;
  - `document-parser/mcp_adapter/sources_app.html` : `:991`, `:1007`, `:1019`, `:1035`, `:1040`,
    `:1068`, `:1078`, `:1096`, `:1132`, `:1150`.
- **Constat** : memes fonctions dans les deux pages. Les modifications de la remediation
  (libelles FR de `citation_app.html`) n'y touchent pas.
- **Regle violee** : item 5.1 (2 copies, ampleur notable).
- **Remediation** : inchangee. Extraire `mcp_adapter/app_bridge.js`, inline au chargement
  (`apps.py`, `sources_view.py`).

### [MIN] Import d'une analyse Docling recopie dans trois composants

**Statut : inchange.**

- **Localisation** : `frontend/src/features/analysis/ui/AnalysisImportButton.vue:40-57`,
  `frontend/src/features/document/ui/DocumentActionsMenu.vue:74-91`,
  `frontend/src/features/document/ui/DocumentUpload.vue:105-123`
- **Remediation** : composable `useAnalysisImport()` exporte par le barrel `@/features/analysis`.

### [MIN] Defauts, bornes et parsing d'env des budgets MCP / Ask non centralises

**Statut : inchange.** Les nouvelles bornes `READ_TOKENS_MIN/MAX` sont, elles, centralisees
(`domain/mcp_config.py:34-35`, importees par `infra/settings.py:13-14`).

- **Localisation** :
  - plafonds 5 :
    - `services/navigation_config.py:25` (`MAX_ROUNDS = 5`) ;
    - `infra/settings.py:70` (`reasoning_max_iterations = 5`) et `:121` (`mcp_max_rounds = 5`) ;
  - lecture 4000 : `services/navigation_config.py:32`, `infra/settings.py:118` ;
  - bornes 1/20 : `domain/mcp_config.py:29-30` vs `domain/app_config.py:22-23` ;
  - clamp de largeur : `mcp_adapter/apps.py:206`, `mcp_adapter/sources_view.py:90` ;
  - parse booleen en ligne x8 : `infra/settings.py:271`, `:286`, `:288`, `:291`, `:293`, `:300`,
    `:310`, `:312`, alors que `services/config_overrides.py:55` (`_TRUE_VALUES`) existe.
- **Remediation** : inchangee (`DEFAULT_MAX_ROUNDS`, `_env_bool`).

### [MIN] Bloc de style `.field-*` duplique dans les formulaires de store (perimetre deprecie)

**Statut : inchange.** Les valeurs ont change avec les tokens, mais le bloc reste copie.

- **Localisation** : `frontend/src/features/store/ui/Neo4jConfigForm.vue:83-109`,
  `OpenSearchConfigForm.vue:66-92`, `StoreForm.vue:375-408`
- **Remediation** : aucune ; suppression avec l'ingestion en 0.8.0.

### [MIN] Bornes de chunking et defauts d'options dupliques entre DTO Pydantic et value objects

**Statut : inchange.**

- **Localisation** :
  - DTO : `api/schemas.py:187` (`PipelineOptionsRequest`, defaut `table_mode` `:197`, validation
    `:227-228`) et `:239` (`ChunkingOptionsRequest`, `64`/`8192` `:265-266`) ;
  - value objects : `domain/value_objects.py:104`, `:129` ;
  - autres sites :
    - `infra/settings.py:30`, `:191`, `:253` ;
    - `services/analysis_service.py:63` ;
    - `infra/local_converter.py:54` ;
    - `frontend/src/features/chunks/ui/StrategyPopover.vue:52-53`,
      `frontend/src/features/chunking/ui/ChunkPanel.vue:38-39`.
- **Remediation** : inchangee (`TableMode(StrEnum)`, bornes exposees).

### [MIN] Primitives UI recopiees composant par composant

**Statut : inchange.** 16 `@keyframes spin` (17 en 0.7.4 : `DocChunkTab.vue` est supprime).

- **Localisation** :
  - `.spinner-sm` : `features/ingestion/ui/IngestPanel.vue:332`, `features/chunking/ui/ChunkPanel.vue`,
    `pages/StudioPage.vue` ;
  - icone document : `DocWorkspaceHeader.vue:4`, `DocumentList.vue:12`, `StudioPage.vue:142`,
    `DocsLibraryPage.vue:108` ;
  - boutons primaires et interrupteurs : localisations 0.7.4 inchangees.
- **Remediation** : inchangee (`AppSpinner`, `AppButton` sur `--on-accent`, `AppSwitch`).

### [MIN] Palette de la vue graphe Neo4j recopiee trois fois (perimetre deprecie)

**Statut : inchange**, avec l'exception `.legend-chunk` assumee par la remediation.

- **Localisation** :
  - `frontend/src/features/analysis/ui/GraphView.vue:134-147` (et `.legend-*` `:556-577`) ;
  - `frontend/src/features/analysis/ui/NodeDetailsPanel.vue:113-132` ;
  - `frontend/src/features/analysis/legendFilters.ts:34`.
- **Remediation** : suppression avec l'ingestion en 0.8.0.

### [MIN] `api/analyses.py` : mapping de chunks x3 et resume d'analyse redeclare

**Statut : inchange.**

- **Localisation** :
  - mapping de chunks : `document-parser/api/analyses.py:208-217`, `:232-243`, `:255-266` ;
  - resume : `_to_response` `:85-102` vs `list_analysis_summaries` `:173-187` ;
  - schemas : `api/schemas.py:154` vs `:172`.
- **Remediation** : inchangee (`AnalysisResponse(AnalysisSummaryResponse)`, `_chunk_from_dict`).

### [MIN] Helpers `_utcnow` / `_new_id` recopies x4, avec deux formats d'identifiant

**Statut : inchange** en nombre. Une copie a ete deplacee dans un fichier cree par la
remediation.

- **Localisation** :
  - `document-parser/domain/models.py:29-34` ;
  - `domain/chunk_editing.py:154-155` (`_new_edit_id`, desormais `str(uuid4())`) ;
  - `services/chunk_service.py:54-55` (`_utcnow`) ;
  - `services/chunk_push_service.py:40-45` (**nouvelle copie**, fichier cree en `e95c75d`) ;
  - `services/version_service.py:41-46`.
- **Constat** : `_utcnow` x4 et `_new_id` x4. Le format hex ne subsiste que dans
  `version_service.py:42`. Il sert aux ids des chunks restaures (`:192`) et aux lignes de journal
  du restore (`:158`), commente comme voulu (`:156-157`). Les autres chunks recoivent l'id de
  36 caracteres du `default_factory`.
- **Remediation** : inchangee. `new_id()` / `utcnow()` publics dans `domain/models.py` ;
  conserver le hex du restore seulement s'il est un contrat.

### [MIN] Formatage de date local x3 malgre `shared/format.ts`

**Statut : partiellement corrige** (4 → 3). `AnalysisDetailPage.vue:13`, `:41` utilise
`formatAbsolute` (`30d8ecb`).

- **Localisation** : `frontend/src/pages/AnalysisLibraryPage.vue:158-162` (copie de
  `formatAbsolute` sans son `try/catch`), `frontend/src/features/history/ui/HistoryList.vue:71-74`,
  `frontend/src/pages/DocumentsPage.vue:179-182` (`toLocaleString()`). Helper :
  `frontend/src/shared/format.ts:26-37`.
- **Constat** : une meme date s'affiche toujours en deux formats selon la page.
- **Remediation** : 3 imports de `formatAbsolute`.

### [MIN] Squelette d'action asynchrone recopie dans les stores Pinia

**Statut : inchange** (`(e as Error).message` : 41 → 39, par suppression de composants).

- **Localisation** : `frontend/src/features/chunks/store.ts:51-63` et `:65-77` (`updateText` /
  `updateTitle`, toujours identiques au champ pres). `catch` : 10 / 8 / 9 / 3 / 2 dans les stores
  `chunks` / `document` / `analysis` / `chunking` / `history`.
- **Remediation** : inchangee (`runAction` / `errorMessage` dans `shared/`).

### [MIN] Datetime → texte ecrit en ligne x13 dans `api/`, deux formats sur le fil

**Statut : inchange.** La remediation a unifie la **lecture** des dates
(`persistence/timestamps.py`), pas leur ecriture sur le fil.

- **Localisation** :
  - `str(<datetime>)` dans `api/` :
    - `document-parser/api/analyses.py:99-101`, `:182-184` ;
    - `api/documents.py:43`, `:45`, `:55` ;
    - `api/document_chunks.py:55-56` ;
    - `api/document_versions.py:34` ;
    - `api/stores.py:49` ;
  - `str(<datetime>)` ailleurs :
    - `services/store_service.py:418`, `:434` ;
    - `domain/chunk_serialization.py:54-55` (deplace depuis `version_service`) ;
  - `.isoformat()` : `services/chunk_push_service.py:338` (deplace depuis `chunk_service`),
    `services/navigation_service.py:95`.
- **Constat** : `pushedAt` de `/chunks/pushes` (`T`) et `pushedAt` des liens de
  `GET /api/documents/{id}` (espace) ont toujours deux formats.
- **Remediation** : `to_iso()` a cote de `parse_iso`, ou un type `AwareDatetime` serialise par
  Pydantic.

### [INFO] Serialisation Chunk → dict : deux copies du « coeur » camelCase (MIN 0.7.4 partiellement corrige)

- **Localisation** : `document-parser/domain/chunk_serialization.py:85-93` (`_core`, sur `Chunk`)
  vs `document-parser/services/analysis_service.py:43-52` (`_chunk_to_dict`, sur `ChunkResult`).
  Lecteur unique : `chunk_from_dict` (`chunk_serialization.py:59-82`), utilise par
  `chunk_service.py:105` et `version_service.py:192`.
- **Constat** :
  - Le passage de 4 a 2 copies est obtenu. Les divergences 0.7.4 (`self_ref`, `tokenCount`
    `0` / `null`) deviennent des formats documentes (`chunk_serialization.py:1-22`).
  - La docstring du module dit que l'analyse ecrit le meme coeur dans `chunks_json`, mais elle le
    fait par sa propre copie.
  - Sous le seuil 3+.
- **Remediation** : servir `ChunkResult` par `_core`, les attributs etant les memes, ou ajouter
  `chunk_result_to_dict` au module.

### [INFO] Labels Docling : deux copies de l'ensemble « furniture » (MIN 0.7.4 partiellement corrige)

- **Localisation** : `document-parser/domain/page_regions.py:42` (`_FURNITURE`) vs
  `document-parser/domain/navigation.py:365` (`_EMPTY_LABELS`). Litteral residuel :
  `domain/doc_tree.py:138`.
- **Constat** :
  - La copie de `source_service` a disparu.
  - L'arbre documentaire passe par `label_of` / `is_heading` (`domain/doc_tree.py:68`, `:100`).
  - Plus de litteral `{"title", "section_header"}` hors `HEADING_LABELS` (`navigation.py:361`).
- **Remediation** : `FURNITURE_LABELS` unique a cote de `label_of` (`domain/parse_index.py:247`).

### [INFO] Reconduits sans changement

| Constat | Localisation verifiee | Statut |
|---------|-----------------------|--------|
| `fetch()` brut hors client HTTP | `frontend/src/features/document/ui/DownloadDropdown.vue:133` | Inchange |
| Constantes de troncature | `infra/neo4j/queries.py:104`, `:128` ; `infra/docling_agent_reasoning.py:183`, `:199`, `:213` | Inchange |
| Config MCP vs Ask : paires paralleles | `domain/mcp_config.py:94` vs `domain/app_config.py:77` ; stores `mcp-config` / `admin-config` | Inchange |
| DTO du fil MCP en miroir du domaine (accepte) | `mcp_adapter/sources_wire.py:25-108` (extrait de `sources_view.py` par la remediation) vs `domain/source_map.py`, `domain/source_bar.py` | Inchange |
| Deux extractions DoclingDocument → pages | `infra/docling_pages.py:48` vs `infra/serve_converter.py:269` (`_LABEL_MAP` `:52`) | Inchange |
| Redondances front sous le seuil | `features/reasoning/api.ts:26` vs `shared/api/http.ts:9` ; `features/document/store.ts:75` vs `pages/DocsNewPage.vue:164` ; clic exterieur `DocumentActionsMenu` / `DownloadDropdown` | Inchange |

---

## Regressions et nouveaux ecarts introduits par la remediation

| Constat | Gravite | Localisation |
|---------|---------|--------------|
| Trois erreurs de service creees hors du contrat `ServiceError`, mappees a la main | MIN (dans le reliquat du contrat d'erreur) | `services/document_service.py:40`, `:47`, `:54` ; `api/documents.py:157-170`, `:186-192` |
| Nouvelle copie de `_utcnow` / `_new_id` | MIN (dans l'ecart `_utcnow` existant) | `services/chunk_push_service.py:40-45` |
| Constante front miroir d'un defaut de persistence (`SUMMARIES_PAGE = 200`) | INFO, traite dans le re-audit 07 (couplage) | `frontend/src/pages/DocsLibraryPage.logic.ts:17` vs `persistence/analysis_repo.py:70` |

Les fenetres dupliquees nouvelles a HEAD sont triviales (signatures, injection, passage de
parametres). `services/chunk_push_service.py`, `document_tree_service.py`, `chunk_errors.py`,
`domain/doc_tree.py`, `domain/citation_match.py`, `domain/read_budget.py` et
`mcp_adapter/sources_*.py` ne recopient pas de logique existante.

---

## Ce qui reste pour 100 (lecture stricte) et quick wins

| Action | Item | Effort | Gain |
|--------|------|--------|------|
| 13 tokens non definis + 2 `#ef4444` (MIN couleurs, partie (a) + (b)) | 5.3 | S | 83 → 100 en lecture stricte (0 en lecture 0.7.4) |
| Rattacher `PageOutOfRange`/`PageNotFound`/`ExportNotFound` a `ServiceError`, `require_document` partout | 5.1 | S | 0 (consolide 5.1) |
| `formatDate` x3 → `formatAbsolute` | 5.1 | XS | 0 (leve un MIN) |
| `--on-accent` sur les 19 `white` / `#fff` + garde « token non defini » | 5.3 | S | 0 (empeche la rechute) |

---

## Points positifs

- **Un seul contrat d'erreur, teste.** `ServiceError` porte le statut et un handler le traduit.
  Les routeurs ont perdu 14 `try/except` et 2 helpers, et un changement de libelle ne change
  plus un code HTTP.
- **Lecture des dates en un seul endroit.** La conversion UTC est explicite et une date
  obligatoire vide est signalee au lieu d'etre inventee (`persistence/timestamps.py`).
- **Ecriture des chunks factorisee de bout en bout** :
  - serialisation et formats documentes dans `domain/chunk_serialization.py` ;
  - journal construit par `EditJournal` ;
  - remplacement de chunkset par un seul `replace_chunkset` transactionnel ;
  - regles split / merge servies par le domaine.
- **Couleurs du theme** : les 33 references fantomes `--color-*` et les 24 replis divergents ont
  disparu ; `--on-accent` est defini dans les deux themes.
- **Bornes de validation importees du domaine** par la configuration (`infra/settings.py:9-14`)
  au lieu d'etre recopiees.
- **Aucune duplication significative introduite** par ~100 commits de refactoring, verifie par
  detecteur sur les deux arbres.

---

## Verdict partiel : GO

Score **100 / 100** en lecture 0.7.4, **0 CRITICAL**, **0 MAJOR**, 14 MIN, 8 INFO. Les trois MAJ
de 0.7.4 sont corriges, deux MIN corriges et deux requalifies en INFO. En lecture stricte de 5.3,
ou les 15 couleurs hors inventaire tiennent l'item, le score est **83 / 100** avec 1 MAJ : GO,
au-dessus de 80. Les deux reliquats (couleurs, contrat d'erreur) se traitent en effort S et
rendent la note insensible a la lecture. La remediation n'introduit aucune regression DRY au-dela
des trois erreurs de service creees hors contrat.
