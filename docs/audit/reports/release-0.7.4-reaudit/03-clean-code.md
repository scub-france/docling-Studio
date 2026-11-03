# Rapport d'audit : Clean Code — re-audit

**Release** : 0.7.4 (re-audit après remédiation, avant gel)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` @ `a4d9679`
**Baseline** : `docs/audit/reports/release-0.7.4/03-clean-code.md` (code `1de1929`, identique à `e6047c2` pour `document-parser/` et `frontend/src/`), score **39**, NO-GO.

---

## Score de compliance

| Metrique | 0.7.4 | Re-audit |
|----------|-------|----------|
| Items conformes | 6 / 14 | **8 / 14** |
| Score | 39 / 100 | **56 / 100** |
| Ecarts CRITICAL | 0 | 0 |
| Ecarts MAJOR | 3 | **2** |
| Ecarts MINOR | 5 | **4** |
| Ecarts INFO | 8 | 9 |

**Detail du calcul** : poids conformes = 10 (3.1.2=1, 3.1.4=1, 3.2.4=1, 3.2.5=2, 3.3.2=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur 18, soit `10 / 18 * 100 = 55,6`, arrondi à **56**.

**Lecture des items : identique au rapport 0.7.4.**
- 3.2.4 reste lu au sens strict, étendu au TS/Vue et au JS des cartes MCP. Il est conforme sous les deux lectures (0.7.3 et 0.7.4) : le score ne dépend plus de ce choix.
- 3.1.1 et 3.1.3 restent non conformes : la convention de nommage et la langue des cartes sont des décisions laissées au mainteneur (brief), non prises à ce jour. La fiche `docs/audit/audits/03-clean-code.md` est inchangée depuis `e6047c2`.

**D'où viennent les +17 points** : 3.2.4 (+1, les 3 flag arguments sont supprimés) et 3.3.2 (+2, `chunk_service.py` et `sources_view.py` sont scindés). Aucun item ne passe de conforme à non conforme.

**Périmètre.**
- `document-parser/`, hors `.venv/`, `__pycache__/` et `tests/` : 136 fichiers `.py` (20 778 lignes), plus `mcp_adapter/citation_app.html` (1 194 l.) et `sources_app.html` (1 195 l.), audités comme du code source.
- `frontend/src/`, hors `*.test.*` : 145 fichiers `.vue`/`.ts` (25 181 lignes).

**Méthode : les scripts de mesure du 1er audit, relancés tels quels.**
- Fonctions Python par AST (corps sans signature ni docstring, paramètres hors `self`/`cls`) ; fonctions TS/Vue/JS des cartes avec le parseur TypeScript du projet ; littéraux `true`/`false` aux sites d'appel ; heuristique verbe/nom ; découpage script/template/style des `.vue` ; extraction des littéraux français des cartes.
- **Contrôle de comparabilité** : relancés sur l'arbre `e6047c2` (extrait par `git archive`), ils redonnent exactement les chiffres du rapport 0.7.4 : 45 fonctions Python > 30 lignes (83 avec signature et docstring), 29 signatures > 4 paramètres, 12 fonctions front + 3 internes aux stores, 9 fonctions JS des cartes, les 7 appels `fitToFrame`/`draw` à littéral booléen, 96/199 noms non verbaux.
- Ajouts de ce re-audit : inventaire des paramètres typés `boolean` en TS/JS (le 1er audit avait trouvé `updateRenderWindow` sans littéral) ; **atteignabilité** des modules front depuis `frontend/src/app/main.ts` (imports statiques et dynamiques, alias `@/`).
- Imports : `ruff check --select I` (ruff 0.16.4, configuration du projet) → « All checks passed! ». Gates du coordinateur sur HEAD : `ruff check` et `ruff format --check` OK, pytest 1673 passed / 19 skipped, eslint, prettier, vue-tsc, vitest (522 passed) OK.
- Analyse statique ; aucune suite n'a été relancée ici. Le JS des cartes n'est toujours exécuté par aucun test : le comportement inchangé des refactorings JS n'est attesté que par le message de commit `d094673` (rendu Chromium dans un hôte simulé), **non vérifié par moi**.

---

## Metriques

| Mesure | 0.7.4 (`e6047c2`) | Re-audit (`a4d9679`) | Commentaire |
|--------|-------------------|----------------------|-------------|
| Fichiers `.py` source (hors tests) | 119 (19 773 l.) | 136 (20 778 l.) | +17 modules extraits ou créés par la remédiation |
| Fichiers `.vue`/`.ts` source (hors tests) | 150 (26 386 l.) | 145 (25 181 l.) | −4 composants orphelins, −`DocIngestTab.logic.ts`, `i18n.ts` −69 l. |
| `.py` > 300 lignes | 14 (+2 HTML) | **14 (+2 HTML)** | 2 sorties, 2 entrées (voir liste) |
| `.vue`/`.ts` > 300 lignes | 26 | **25** | `IngestLaunchDialog.vue` supprimé |
| Fonctions Python > 30 lignes de corps | 45 | **33** | 78 si l'on compte signature et docstring (83 avant) |
| Fonctions TS/Vue > 30 lignes (hors stores Pinia setup) | 12 (+3) | **12 (+3)** | identiques |
| Fonctions JS des cartes > 30 lignes | 9 | **9** | identiques, lignes décalées |
| Fonctions Python > 4 paramètres | 29 | **32** | +5 introduites, −2 supprimées ; 0 côté front et JS |
| Flag arguments (TS / JS) | 3 | **0** | les 2 seuls littéraux restants sont `Array.indexOf(true)` |
| Flag arguments Python (booléen positionnel) | 0 | 0 | 2 nouveaux booléens keyword-only de donnée/configuration (INFO) |
| Imbrication max (Python / TS / JS) | 7 / 4 / 4 | 7 / 4 / 4 | `local_chunker.py:24`, inchangé |
| Code commenté laissé en place | 0 | 0 | aucune ligne ajoutée par la remédiation |
| Texte UI français hors `i18n.ts` (cartes) | ≈ 80 l., ≈ 100 fragments, + 3 textes anglais | **≈ 86 l., ≈ 106 fragments, 0 texte anglais en dur** | +6 fragments : les chaînes anglaises traduites |
| Noms non verbaux (heuristique, Python) | 96/199 (48 %) modules ajoutés depuis v0.7.2 ; 196/729 global | 112/248 (45 %) ; 224/803 (28 %) | modules créés par la remédiation : 21/54 (39 %) |
| Noms non verbaux (JS des cartes) | 49-50/96 | 51/101 | |
| Composants `.vue` sans importeur hors tests | 4 annoncés (1 034 l.) | **4 (1 588 l.)**, mais pas les mêmes | voir INFO code mort |
| Modules front non atteignables depuis `app/main.ts` | non mesuré (19 modules, 4 174 l. recomptés sur `e6047c2`) | **15 modules, 2 968 l.** | voir INFO code mort |

### Fichiers > 300 lignes (liste exhaustive)

**Python (14)** :

| Fichier | 0.7.4 | Re-audit | Note |
|---------|------:|---------:|------|
| `api/schemas.py` | 849 | 892 | |
| `domain/ports.py` | 542 | 727 | +185 : chaque méthode de dépôt appelée par les services est déclarée (`39dcda5`) |
| `services/analysis_service.py` | 589 | 619 | |
| `services/store_service.py` | 395 | 459 | déprécié ; +64 (politique de connexion SSRF / lecture seule) |
| `domain/navigation.py` | 385 | 431 | statuts, types et modes typés (`44d0e2f`) |
| `infra/serve_converter.py` | 402 | 402 | |
| `bootstrap/factories.py` | 354 | 368 | |
| `domain/source_map.py` | 354 | 364 | |
| `services/chunk_push_service.py` | — | **339** | **nouveau** (extrait de `chunk_service.py`), déprécié |
| `domain/models.py` | 331 | 331 | |
| `infra/settings.py` | 280 | **320** | **franchit le seuil** (`MAX_IMPORT_TABLE_CELLS`, bornes de `MCP_MAX_READ_TOKENS`) |
| `services/chunk_service.py` | 1 019 | **311** | −708 ; encore 11 lignes au-dessus du seuil |
| `infra/neo4j/tree_writer.py` | 310 | 310 | déprécié |
| `infra/docling_tree.py` | 307 | 307 | |

Sortis de la liste : `services/citation_service.py` (307 → 238) et `mcp_adapter/sources_view.py` (369 → 105). Hors `.py` : `sources_app.html` (1 195) et `citation_app.html` (1 194).

**Front (25)**, avec le détail script / template / style des `.vue` :

| Fichier | Lignes | Script / template / style | Note |
|---------|-------:|---------------------------|------|
| `shared/i18n.ts` | 1405 | — | données (1 474 → 1 405) |
| `pages/StudioPage.vue` | 1450 | 175 / 505 / 762 | |
| `features/mcp-config/ui/McpConfigSection.vue` | 1110 | 170 / 355 / 577 | |
| `features/chunking/ui/ChunkPanel.vue` | 801 | 111 / 221 / 461 | |
| `pages/DocParseTab.vue` | 794 | **318** / 160 / 308 | |
| `features/document/ui/PagePreviewWithOverlay.vue` | 724 | **404** / 121 / 191 | +4 (flag argument retiré) |
| `pages/DocsLibraryPage.vue` | 710 | 166 / 201 / 335 | +9 |
| `features/analysis/ui/ResultTabs.vue` | 679 | 133 / 187 / 351 | |
| `features/analysis/ui/GraphView.vue` | 657 | **437** / 59 / 153 | déprécié |
| `features/chunks/ui/ChunksEditor.vue` | 622 | 168 / 124 / 322 | **non atteignable** |
| `features/store/ui/StoreForm.vue` | 522 | 171 / 190 / 153 | déprécié, **non atteignable** |
| `features/document/ui/ElementProperties.vue` | 456 | 98 / 126 / 224 | |
| `features/analysis/ui/StructureViewer.vue` | 438 | 242 / 58 / 130 | |
| `pages/DocumentsPage.vue` | 436 | 92 / 120 / 216 | |
| `features/analysis/ui/NodeDetailsPanel.vue` | 409 | 113 / 84 / 204 | vue graphe, dépréciée |
| `pages/DocsNewPage.vue` | 391 | 97 / 78 / 208 | |
| `features/chunks/ui/ChunkItem.vue` | 387 | 82 / 107 / 190 | **non atteignable** |
| `features/admin-config/ui/ReasoningConfigSection.vue` | 386 | 20 / 157 / 201 | |
| `features/chunks/ui/StrategyPopover.vue` | 369 | 77 / 111 / 173 | **non atteignable** |
| `pages/AnalysisLibraryPage.vue` | 365 | 62 / 103 / 192 | |
| `features/ingestion/ui/IngestPanel.vue` | 346 | 16 / 106 / 216 | déprécié |
| `features/analysis/ui/BboxOverlay.vue` | 312 | 177 / 33 / 94 | |
| `shared/ui/AppSidebar.vue` | 304 | 128 / 46 / 122 | |
| `app/App.vue` | 304 | 26 / 42 / 228 | +3 |
| `features/chunks/ui/ChunksPanel.vue` | 301 | 88 / 75 / 130 | **non atteignable** |

---

## Checklist

| # | Item | Poids | 0.7.4 | Re-audit | Statut |
|---|------|-------|-------|----------|--------|
| 3.1.1 | Fonctions nommées avec des verbes d'action | 1 | ❌ | ❌ | inchangé (décision mainteneur non prise) |
| 3.1.2 | Variables qui expriment l'intention | 1 | ✅ | ✅ | inchangé |
| 3.1.3 | Tout le code en anglais — traductions dans `shared/i18n.ts` | 2 | ❌ | ❌ | partiellement corrigé (textes anglais traduits ; français hors i18n = choix assumé) |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | ✅ | ✅ | inchangé |
| 3.2.1 | Chaque fonction fait une seule chose | 2 | ❌ | ❌ | partiellement corrigé (3 cas sur 5 ; restent 2 fonctions dépréciées) |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | ❌ | ❌ | partiellement corrigé (66 → 54) |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | ❌ | ❌ | inchangé, légèrement aggravé (29 → 32) |
| 3.2.4 | Pas de flag arguments | 1 | ❌ | ✅ | **corrigé** |
| 3.2.5 | Un `get_*` ne modifie pas d'état | 2 | ✅ | ✅ | inchangé |
| 3.3.1 | Aucun fichier source > 300 lignes | 1 | ❌ | ❌ | inchangé (42 → 41) |
| 3.3.2 | Un seul concept par fichier | 2 | ❌ | ✅ | **corrigé** |
| 3.3.3 | Imports ordonnés | 1 | ✅ | ✅ | inchangé |
| 3.4.1 | Commentaires = « pourquoi » | 1 | ✅ | ✅ | inchangé |
| 3.4.2 | Pas de code commenté laissé en place | 1 | ✅ | ✅ | inchangé |

---

## Ecarts constates

### [MAJ] Cartes MCP : libellés UI en français codés en dur, hors i18n — statut : **partiellement corrigé** (textes anglais traduits ; le reste relève de la décision produit)

- **Corrigé (commit `1b9b59f`)** : la carte de citation n'affiche plus aucun texte anglais en dur.
  - `document-parser/mcp_adapter/citation_app.html:680` : « Presse-papiers bloqué — sélectionnez le texte ci-dessus » (était « Clipboard blocked — select the text below », qui désignait en outre le mauvais endroit) ;
  - `:706` : « l’hôte n’a pas répondu » ;
  - `:825` et `:957` : « le serveur a refusé » ;
  - `:718`, et `sources_app.html:1024` : « l’appel a échoué » (était « call failed », non relevé en 0.7.4).

  La phrase composée `citation_app.html:832` (« Aperçu de la page indisponible — ${error.message}. ») ne mélange plus de libellé anglais codé en dur. Elle peut encore afficher un message d'erreur **renvoyé par le serveur**, qui est en anglais (`ToolError(str(exc))`, `mcp_adapter/sources_view.py:93` et `mcp_adapter/apps.py`) : c'est une donnée, pas un libellé de la carte.
  - Un balayage des littéraux du JS des deux cartes ne trouve plus aucun texte anglais visible.
- **Inchangé (choix produit assumé)** : les cartes affichent ≈ 86 lignes, ≈ 106 fragments de texte français codés en dur, sans mécanisme de traduction.
  - `citation_app.html:395` (« En attente d'une citation… »), `:426` (table `KIND_LABELS`), `:606-615` (« Texte exact du document », « Lire la suite », « Copier la citation », « Ouvrir dans Docling Studio ») ;
  - `sources_app.html:317`, `:397` (« vérifiée »…), `:490` (onglets), `:742` (« une ${noun} par tour »), `:1005` (`TIMEOUT_MESSAGE`) ;
  - formatage figé en français : `sources_app.html:336` (`num`), `:343-346` (`fr()`, `"fr-FR"`), `:359` (`plural()`) ;
  - `lang="fr"` sur les deux pages (`:2`).
  - Le repli texte serveur reste en anglais, désormais dans `mcp_adapter/sources_text.py:16-47` (destiné au modèle, pas à l'utilisateur).
  - Côté Studio, aucune chaîne française hors `i18n.ts` en dehors de l'autonyme « Français » (convention UX).
- **Regle violee** : item 3.1.3 (poids 2).
- **Ampleur restante** : identique à l'évaluation 0.7.4, à +6 fragments près. Option B (table `MESSAGES = { en, fr }`, `en` par défaut, locale lue depuis l'hôte) : ≈ 75-85 messages, une dizaine de phrases à accords à paramétrer, `Intl.NumberFormat`, `lang` dynamique, ≈ 5 assertions de test à réécrire ; effort M (≈ 1 à 1,5 j avec recette manuelle). L'item ne deviendra conforme qu'avec une décision du mainteneur.

### [MAJ] Fonctions d'orchestration multi-responsabilités — statut : **partiellement corrigé** (3 sur 5 ; restent les 2 fonctions Neo4j dépréciées)

- **Corrigé** :
  - **`push_to_store`** : sorti de `ChunkService` vers `document-parser/services/chunk_push_service.py:114`. 24 lignes de corps, une étape nommée par préoccupation : `_require_ingestion` (`:159`), `_resolve_store` (`:168`), `_chunks_to_push` (`:184`), `_resolve_backends` (`:193`), `_ingest` (`:214`), `_record_push` (`:230`). L'ordre « tout vérifier, puis ingérer, puis enregistrer » est documenté (`:129-132`). L'historique (`list_pushes`, `:249`) délègue la jointure à `_stores_of` (`:275`) et `_history_entry` (`:327`).
  - **`build_index`** : `document-parser/domain/parse_index.py:80`, 29 lignes, compose `_items_by_ref` (`:113`), `_heading_paths` (`:126`), `_page_sizes` (`:160`) et `_provenance` (`:185`). C'est exactement l'extraction proposée en 0.7.4.
  - **`_finalize_analysis`** : `document-parser/services/analysis_service.py:466`, 8 lignes, enchaîne `_chunk_result` (`:488`), `_completed_job` (`:503`), `_record_version` (`:525`), `update_status`, puis `_apply_analysis_effects` (`:544`). **L'ordre version → COMPLETED est conservé** (`:483-484`) et documenté (`:474-477`).
- **Inchangé** (`git diff e6047c2..HEAD -- document-parser/infra/neo4j/` est vide) :
  - `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l. de corps, 7 paramètres) : projection de l'arbre Docling puis une dizaine d'étapes Cypher dans une même transaction (effacement, nœud document, éléments par label, provenances, `HAS_ROOT`, ordre de lecture…) ;
  - `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.).

  Les deux relèvent du périmètre ingestion / vue graphe Neo4j, déprécié et retiré en 0.8.0 (`CHANGELOG.md:81`).
- **Pas de nouveau cas** dans le code de la remédiation : les fonctions qui orchestrent (`ChunkService.rechunk_document`, `chunk_service.py:230`, 27 l. ; `ChunkPushService.push_to_store`) délèguent chaque étape à une fonction nommée.
- **Regle violee** : item 3.2.1 (poids 2) — tout ou rien : 2 fonctions suffisent à le garder non conforme.
- **Ampleur restante** : 2 fonctions, toutes deux dépréciées. Soit les découper (effort L : 342 lignes de Cypher, et les 15 tests Neo4j sont ignorés sans serveur), soit **anticiper le retrait de l'ingestion**, qui les supprime avec `tree_writer.py` et `queries.py`.

### [MIN] Convention de nommage : environ la moitié des fonctions MCP/navigation portent un nom, pas un verbe — statut : **inchangé** (décision mainteneur non prise)

- **Localisation** : tous les cas 0.7.4 sont présents, aux lignes près. Exemples : `domain/source_map.py:246` (`_totals`), `:302` (`_rounds`, ex-`_hops`) ; `services/source_service.py:224` (`_marks`), `:234` (`_anchor`), `:258` (`_resolvable`) ; `mcp_adapter/wire_mapping.py` ; `mcp_adapter/sources_mapping.py:30` (`sources_card`), `:105` (`_passage`), `:131` (`_node`) ; `mcp_adapter/sources_text.py:43` (`_said`) ; JS `sources_app.html` (`head`, `sources`, `details`, `coverage`…).
- **Constat**
  - Même heuristique : 112 noms non verbaux sur 248 fonctions (45 %) dans les modules ajoutés depuis v0.7.2 ; 224 sur 803 (28 %) sur tout le backend ; 51 sur 101 dans le JS des cartes.
  - Le code de la remédiation suit la même convention « nom = valeur renvoyée » : 21 noms non verbaux sur 54 fonctions dans les 17 modules créés (`chunk_push_service.py:184` `_chunks_to_push`, `:275` `_stores_of`, `:327` `_history_entry` ; `infra/pdf_inspector.py:25` `page_count`…). C'est cohérent avec l'existant, non conforme à la lecture stricte.
  - **Le coût concret relevé en 0.7.4 est toujours là** : `_anchor(uri, unknown)` (`services/source_service.py:234`) et `_resolvable(parse, anchors, unknown)` (`:258`) ajoutent à la liste `unknown` reçue en argument, sans que leur nom le dise. Appels en `:95`, `:96` et `:107`.
- **Regle violee** : item 3.1.1 (poids 1).
- **Ampleur restante** : (a) décision de gouvernance dans la fiche 3.1.1 (« nom = valeur renvoyée » admis pour les fonctions pures) **plus** 2 renommages (`_anchor` → `_parse_or_report`, `_resolvable` → `_partition_known` ; 3 appels, 0 référence de test), effort S ; ou (b) lecture stricte : ≈ 224 fonctions Python et ≈ 51 fonctions JS à renommer, effort M.

### [MIN] Fonctions au-delà de 30 lignes — statut : **partiellement corrigé** (66 → 54 ; 12 fonctions Python en moins)

- **Localisation** : liste exhaustive. **Python (33)**, lignes de corps entre parenthèses :
  - **Dépréciées (7)** : `infra/neo4j/tree_writer.py:69` (227), `infra/neo4j/queries.py:137` (115), `infra/neo4j/chunk_writer.py:55` (107), `services/store_service.py:248` (60) et `:195` (39), `domain/vector_schema.py:121` (50), `bootstrap/factories.py:330` (34).
  - **Code mort** : 0 (3 en 0.7.4).
  - **Code vivant (26)** :

    | Module | Fonctions > 30 lignes (ligne, lignes de corps) |
    |--------|------------------------------------------------|
    | `bootstrap/builder.py` | `:102` (`build`, **92**, était 69), `:212` (32) |
    | `mcp_adapter/server.py` | `:98` (87) |
    | `infra/docling_agent_reasoning.py` | `:144` (86) |
    | `mcp_adapter/apps.py` | `:146` (80) |
    | `infra/settings.py` | `:237` (78), `:136` (74, était 69) |
    | `infra/local_chunker.py` | `:24` (60) |
    | `services/citation_service.py` | `:104` (`verify_citation_in`, 53 ; était `verify_citation`, 62) |
    | `mcp_adapter/sources_mapping.py` | `:30` (`sources_card`, 52, déplacée de `sources_view.py`) |
    | `infra/docling_pages.py` | `:68` (48) |
    | `services/analysis_service.py` | `:277` (46) |
    | `domain/outline_builder.py` | `:75` (43) |
    | `services/source_service.py` | `:85` (42, était 40) |
    | `services/export_service.py` | `:47` (41) |
    | `services/version_service.py` | `:131` (40, était 48) |
    | `services/navigation_service.py` | `:128` (38, était 34) |
    | `mcp_adapter/sources_view.py` | `:48` (38) |
    | `domain/doc_tree.py` | `:27` (`build_doc_tree`, 38, déplacée de `chunk_service._build_tree_nodes`) |
    | `main.py` | `:132` (37) |
    | `infra/serve_converter.py` | `:141` (34), `:339` (32) |
    | `domain/source_map.py` | `:188` (33), `:302` (`_rounds`, 32, ex-`_hops`) |
    | `bootstrap/mcp_mount.py` | `:84` (33, était 37) |
    | `domain/trace_builder.py` | `:40` (31) |

  - **Sorties de la liste (12)** : `push_to_store` (103) et `list_pushes` (32), désormais ≤ 30 dans `ChunkPushService` ; `chunk_editing.split` (36 → 6), `chunk_editing.merge` (33 → 23), `promote_from_analysis_if_empty` (35 → 27) ; `rechunk_document` (79 → 27), `build_index` (79 → 29), `_finalize_analysis` (67 → 8), `split_chunk` (56 → 27), `merge_chunks` (56 → 19), `ChunkService.__init__` (33 → 10), `DocumentService.upload` (35 → 29).
  - **Front (12, inchangé)** : `GraphView.vue:193` (`renderGraph`, 216, déprécié), `BboxCanvas.vue:62` (75), `StructureViewer.vue:146` (66), `BboxOverlay.vue:85` (61) et `:152` (35), `sectionParenting.ts:31` (58), `usePagination.ts:19` (53), `PagePreviewWithOverlay.vue:331` (`setupObserver`, **55**, était 53 : le retrait du flag argument a mis le `if/else` dans l'observateur) et `:429` (46), `DownloadDropdown.vue:130` (49), `accordion.ts:58` (40), `router/index.ts:39` (32). S'y ajoutent 3 fonctions internes à des stores : `feature-flags/store.ts:154` (35), `reasoning/store.ts:77` (33), `analysis/store.ts:114` (32).
  - **JS des cartes (9, inchangé)** : `citation_app.html:460` (`renderMarkdown`, 77), `:808` (`hydrateLocator`, 68), `:565` (`render`, 66), `:1140` (écouteur `message`, 45) ; `sources_app.html:717` (`details`, 45), `:516` (`strip`, 38), `:810` (`roundsTable`, 37), `:1150` (écouteur `message`, 35), `:765` (`coverage`, 32).
- **Constat** : aucune fonction > 30 lignes n'est créée de toutes pièces par la remédiation ; les 4 « nouvelles » entrées sont des fonctions déplacées ou renommées, à taille égale ou réduite. **Une régression** : `bootstrap/builder.py:102` passe de 69 à 92 lignes, parce qu'il câble maintenant `ChunkPushService` en ligne (`:127-135`, sans fabrique, contrairement à `build_chunk_service` et `build_document_tree_service`), `set_connection_policy` (`:162-165`) et `build_document_service` avec 5 arguments.
- **Regle violee** : item 3.2.2 (poids 1).
- **Ampleur restante** : 54 fonctions (33 Python, 12 front, 9 JS), plus 3 internes aux stores. Le retrait de l'ingestion en supprime 8 (7 Python et `renderGraph`). Effort L.

### [MIN] Fonctions à plus de 4 paramètres — statut : **inchangé, légèrement aggravé** (29 → 32)

- **Localisation** : liste exhaustive, nombre de paramètres hors `self` entre parenthèses.
  - **Dépréciées (9)** : `services/store_service.py:248` (10) et `:195` (9) ; `services/store_backend_resolver.py:80` (8) ; `infra/neo4j/tree_writer.py:69` (7) ; **`services/chunk_push_service.py:60` (7, nouveau)** ; `infra/opensearch_pool.py:43` (5) ; `infra/opensearch_store.py:76` (5) ; `services/ingestion_service.py:85` (5) et `:161` (5).
  - **Code mort** : 0 (`domain/chunk_editing.py:46`, `insert`, supprimée).
  - **Constructeurs DI (6)** : `services/analysis_service.py:71` (**10**, était 9) ; **`services/document_service.py:86` (8, était 3)** ; `services/chunk_service.py:61` (6, était 12) ; `services/app_config_service.py:72` (6, était 7) ; `services/mcp_config_service.py:112` (6) ; `services/source_service.py:70` (5).
  - **Autres (17)** :
    - `mcp_adapter/server.py:98` (5, était 6) et `:169` (`read_element`, 6, miroir du schéma publié) ;
    - `domain/doc_tree.py:85` (6) et `:118` (5), déplacées de `chunk_service.py:942` et `:975` ;
    - `services/citation_image_service.py:133` (6) et `:81` (5) ;
    - `services/navigation_service.py:128` (6) ;
    - `domain/models.py:105` (`mark_completed`, 5) ;
    - `domain/source_map.py:246` (5) ;
    - `infra/serve_converter.py:141` (5) ;
    - `services/analysis_service.py:277`, `:403` et `:585` (5 chacune) ;
    - `services/config_overrides.py:81` (5) ;
    - **nouveaux** : `bootstrap/factories.py:220` (`build_document_service`, 5, était 2), `domain/ports.py:204` et `persistence/chunk_repo.py:80` (`replace_chunkset`, 5 chacune, port et adaptateur ; 4 paramètres keyword-only).
- **Constat** : la remédiation en introduit 5 (`ChunkPushService.__init__`, `DocumentService.__init__`, `build_document_service`, `replace_chunkset` ×2), en alourdit une (`AnalysisService.__init__`), en supprime 2 (`chunk_editing.insert`, `_upsert_link_ingested` qui prend désormais un `ChunkPush`) et en allège 3 qui restent au-dessus du seuil. Les nouveaux cas sont des constructeurs DI et une écriture atomique dont les paramètres sont nommés ; aucun n'est positionnel au-delà de 3. Côté front et JS des cartes : aucune.
- **Regle violee** : item 3.2.3 (poids 1).
- **Ampleur restante** : 32 signatures, dont 9 dépréciées (supprimées avec l'ingestion), 6 constructeurs DI (objet de dépendances), 17 autres (dont `replace_chunkset` : un value object `ChunksetReplacement` ; `read_element` : un `ReadRequest`). Effort L.

### [MIN] Fichiers sources au-delà de 300 lignes — statut : **inchangé** (42 → 41)

- **Localisation** : liste exhaustive dans « Fichiers > 300 lignes » : 14 `.py`, 2 `.html`, 25 `.vue`/`.ts`, soit **41 fichiers**, dont `shared/i18n.ts`.
- **Constat**
  - `chunk_service.py` passe de 1 019 à 311 lignes et reste 11 lignes au-dessus du seuil. `citation_service.py` et `sources_view.py` passent sous le seuil ; `IngestLaunchDialog.vue` est supprimé.
  - **Entrées** : `services/chunk_push_service.py` (339, nouveau fichier de la remédiation, périmètre déprécié) et `infra/settings.py` (280 → 320). Plusieurs fichiers déjà au-dessus grossissent : `domain/ports.py` +185, `services/store_service.py` +64, `domain/navigation.py` +46, `api/schemas.py` +43, `services/analysis_service.py` +30.
  - 11 des 41 fichiers sont dépréciés ou non atteignables : `store_service.py`, `tree_writer.py`, `chunk_push_service.py`, `GraphView.vue`, `NodeDetailsPanel.vue`, `StoreForm.vue`, `IngestPanel.vue` (dépréciés) ; `ChunksEditor.vue`, `ChunkItem.vue`, `StrategyPopover.vue`, `ChunksPanel.vue` (non atteignables depuis `app/main.ts`, voir INFO code mort).
  - `GraphView.vue` (437), `PagePreviewWithOverlay.vue` (404) et `DocParseTab.vue` (318) dépassent toujours 300 lignes de script seul.
- **Regle violee** : item 3.3.1 (poids 1).
- **Ampleur restante** : 41 fichiers. Supprimer les 4 composants non atteignables (−1 679 l.) et retirer 11 lignes à `chunk_service.py` (par exemple `promote_from_analysis_if_empty`, 33 l., sans appelant de production) ramène à 36. Le retrait de l'ingestion en retire 7 de plus. Le reste (dont `i18n.ts`, `StudioPage.vue`, `McpConfigSection.vue`, `ports.py`, `schemas.py`) demande des découpages : effort L.

### [INFO] Constantes magiques, dont des doublons de constantes nommées — statut : **inchangé** (lignes décalées)

- `services/navigation_service.py:197` (`[:96]`, alors que `_MAX_TITLE_LEN = 96` et `truncate_title` existent dans `domain/parse_index.py`) et `:114` (`min(depth, 6)`) ;
- `mcp_adapter/apps.py:206` et `mcp_adapter/sources_view.py:90` (`max(120, min(max_width, 1600))` en double) ;
- `domain/outline_builder.py:44` (`max_nodes=200`) ; `services/citation_image_service.py:71` (`24`, `72.0`) ; `services/analysis_service.py:77` (`conversion_timeout = 600`) ;
- `frontend/src/features/mcp-config/ui/McpConfigSection.vue:517` (`1500`) ; `timeoutMs = 8000` dans `citation_app.html:701` et `sources_app.html:1007`.

### [INFO] Code mort — statut : **partiellement corrigé**, constat élargi (modules front non atteignables)

- **Corrigé** :
  - les 4 composants orphelins relevés en 0.7.4 sont supprimés, avec `DocIngestTab.logic.ts` et 67 lignes de traductions orphelines (commit `2deb5f4`, −1 761 l. tests compris) ;
  - `domain/chunk_editing.py` n'est plus mort : ses règles sont celles du service (`services/chunk_service.py:29-30`, `services/version_service.py:24`, `services/chunk_errors.py:16`) ;
  - `shared/format.ts:26` (`formatAbsolute`) est utilisé (`pages/AnalysisDetailPage.vue:13`).
- **Toujours présent** : `domain/lifecycle_aggregation.py:35` (`aggregate_lifecycle`, tests seuls) ; `_chunk_promoter` posé (`services/analysis_service.py:105`, `:118`, via `bootstrap/builder.py:146`) mais jamais lu ; `services/chunk_service.py:88` (`promote_from_analysis_if_empty`, tests seuls) ; `features/chunks/api.ts:82` (`fetchChunkPushes`).
- **Non relevé en 0.7.4, préexistant** : la recherche « 0 importeur hors tests » donne aujourd'hui encore 4 composants, mais pas les mêmes :
  - `features/chunks/ui/ChunksEditor.vue` (622 l.), `features/chunks/ui/StaleStoresStrip.vue` (143 l.) et `features/store/ui/StoreForm.vue` (522 l.) n'avaient déjà **aucun importeur** sur `e6047c2` ; le 1er audit ne les a pas vus. `ChunksEditor` est gardé volontairement selon `docs/design/264-linked-view-preview-chunks-layers.md:109`, `:392`.
  - **`features/chunks/ui/ChunksPanel.vue` (301 l.) devient orphelin** avec la suppression de `DocChunkTab.vue`, son seul importeur. Il n'était déjà atteignable que par ce composant mort.
- **Atteignabilité depuis `frontend/src/app/main.ts`** (nouvelle mesure) : **15 modules, 2 968 lignes** ne sont atteignables par aucun import (19 modules, 4 174 lignes sur `e6047c2`) :
  - `features/chunks/` : `ChunksEditor.vue`, `ChunksPanel.vue`, `ChunkItem.vue` (387), `StrategyPopover.vue` (369), `StaleStoresStrip.vue`, `index.ts` (le barrel n'est plus importé depuis que `23fb05e` a retiré `pushChunksToStore` du store document) ;
  - `features/store/` : `StoreForm.vue`, `StoreConfigForm.vue`, `OpenSearchConfigForm.vue`, `Neo4jConfigForm.vue`, `connectionForm.logic.ts`, `api.ts`, `index.ts` (tout le front des stores, déprécié) ;
  - `shared/ui/StatusBadge.vue`, `features/search/index.ts`.
  - La remédiation a retouché quatre de ces fichiers morts (`ee17245` couleurs de thème : `StoreForm.vue`, `StaleStoresStrip.vue`, `Neo4jConfigForm.vue`, `OpenSearchConfigForm.vue` ; `7a1f4d5` : `features/store/api.ts`).
- **Remediation** : supprimer `ChunksPanel.vue`, `ChunksEditor.vue`, `ChunkItem.vue`, `StrategyPopover.vue`, `StaleStoresStrip.vue`, `StatusBadge.vue` et les deux barrels morts (1 916 l., dont 4 fichiers > 300 lignes), ou acter leur conservation ; le front des stores avec l'ingestion en 0.8.0 ; `aggregate_lifecycle` et le promoteur avec leurs tests.

### [INFO] Commentaires périmés — statut : **partiellement corrigé**

- **Corrigé** : `services/chunk_service.py:76-77` dit maintenant « Wired by `bootstrap.builder` » ; le commentaire « tombstone » de `_finalize_analysis` a disparu avec le découpage, remplacé par la docstring de `_apply_analysis_effects` (`services/analysis_service.py:554-556`).
- **Restent 5 renvois à « main.py »** pour un câblage fait dans `bootstrap/` : `services/analysis_service.py:100` et `:107`, `services/app_config_service.py:9`, `services/reasoning_service.py:12`, `services/store_backend_resolver.py:95`.
- `services/analysis_service.py:100-104` dit toujours que le promoteur « populates the canonical chunkset on the first successful analysis », ce que contredit `:554-556` (« No canonical chunk promotion here ») et le commentaire de `bootstrap/builder.py:142-145`.
- `frontend/src/pages/StudioPage.vue:16`, `:287`, `:470`, `:479` : noms de modes en français dans des commentaires, inchangés.
- **Remediation** : 5 lignes à corriger, aucun risque ; supprimer le commentaire du promoteur avec le promoteur.

### [INFO] Booléens de configuration en paramètre Python (non comptés comme flag arguments) — statut : **inchangé**, 2 nouveaux cas du même type

- Cas 0.7.4, inchangés : `mcp_adapter/server.py:81` et `:98`, `mcp_adapter/prompts.py:56`, `mcp_adapter/apps.py:123`, `domain/ports.py:223` et `persistence/chunk_repo.py:161` (`include_deleted`), `services/store_service.py:195` et `:248` (`is_default`), `services/mcp_config_service.py:112`, `infra/opensearch_*` (`verify_certs`), `services/config_overrides.py:45` (`require_writable(read_only)`, positionnel, garde).
- **Nouveaux, keyword-only** :
  - `services/analysis_service.py:544`, `_apply_analysis_effects(..., *, chunked: bool)` : le booléen choisit l'état cible du cycle de vie (`:561`, `CHUNKED` ou `PARSED`), la fonction fait la même chose dans les deux cas. C'est une donnée, pas un flag. Passer directement l'état cible (`target_state=`) serait plus explicite.
  - `services/store_service.py:331`, `set_connection_policy(*, target_is_blocked, read_only)` : configuration posée une fois par la racine de composition.
- Aucun appel Python ne passe un booléen positionnel à une fonction du projet (seuls 4 `dict.get(key, False)` dans `api/analyses.py:239-263`). Côté TS, les 3 paramètres `boolean` restants sont des valeurs : `mcp-config/store.ts:92` (`setEnabled(on)`), `StoreForm.vue:325` (`onConfigValid(valid)`), `shared/routing/resolveMode.ts:18` (table de booléens).

### [INFO] Variables d'une lettre et abréviations (3.1.2 / 3.1.4 jugés conformes) — statut : **inchangé**

- Cas 0.7.4 présents : `services/source_service.py:95-96` (`(a, w, f)`), JS `sources_app.html` (`fr`, `num`, `pct`, `px`, `esc`).
- Nouveaux modules : `c`, `d`, `b` dans des compréhensions ou des helpers d'une ligne (`domain/chunk_serialization.py:32-99`, `services/chunk_push_service.py:95-109`), `cid` (`chunk_push_service.py:108`). Portées minuscules, lisibles ; même jugement qu'en 0.7.4.

### [INFO] `get_*` à mémoïsation (3.2.5 jugé conforme) — statut : **inchangé**

- 51 fonctions `get*`/`_get*` Python (47 en 0.7.4). Les 4 nouvelles sont des lectures pures : `services/document_tree_service.py:38` (`get_tree`), `api/deps.py:60` et `:67` (accesseurs de dépendances), `domain/ports.py:164` (`get_connection_password`, déclaration de port) ; `api/analyses.py:70` (`get_route_handler`) est une surcharge FastAPI qui renvoie un gestionnaire sans état. Les `get` de `domain/ports.py:427`, `:443` déclarent les pools mémoïsés déjà revus en 0.7.4.

### [INFO] JS inline des cartes MCP : hors lint, pont hôte dupliqué — statut : **inchangé**

- ≈ 1 650 lignes de JavaScript toujours hors ESLint, Prettier et typage (`frontend/eslint.config.js:10`). Pont JSON-RPC/postMessage en double : `citation_app.html:690-800` et `sources_app.html:991-1097`.
- Les refactorings 3.2.4 et 3.1.3 de cette passe ont touché ce JS. Les tests Python ne vérifient que des sous-chaînes ; `tests/test_mcp_apps.py:449-462` épingle désormais `fitToFrameIfResized()` dans `reportSize` et l'absence de `refitToFrame()` à cet endroit (garde anti-boucle).

### [INFO] Profondeur d'imbrication — statut : **inchangé**

- `document-parser/infra/local_chunker.py:24` (`_chunk_sync`, 7 niveaux). Partout ailleurs, 4 au maximum, dont le nouveau `infra/pdf_inspector.py:33` (`with` verrou → `try` → `for` → `try`, chaque niveau justifié par la fermeture des ressources pdfium).

### [INFO] Code de la remédiation : points de vigilance (nouveau)

- **17 modules créés** ; 14 sont conformes sur toutes les mesures (taille, longueur, paramètres, imports, langue). Seul `services/chunk_push_service.py` apporte de la dette nouvelle (339 l., constructeur à 7 paramètres, périmètre déprécié). `domain/doc_tree.py` et `mcp_adapter/sources_mapping.py` dépassent les seuils uniquement par des fonctions déplacées telles quelles (`build_doc_tree` 38 l., `_build_item_subtree` 6 paramètres, `_make_node` 5, `sources_card` 52 l.).
- `api/analyses.py:38-79` : la remédiation sécurité ajoute un mécanisme HTTP générique (`_BoundedBodyRequest`, `_BoundedBodyRoute`, limite de corps à 200 Mo) dans le module du routeur, dont la docstring (`:1`) dit encore « create, list, get, delete analysis jobs ». Second concept, petit et propre à ce routeur ; pas un fourre-tout au sens de 3.3.2. À déplacer dans `api/` (par exemple `api/body_limit.py`) s'il sert un jour à un autre routeur.
- `services/chunk_errors.py:60` héberge `require_document`, une garde qui lit le dépôt, dans un module d'erreurs. C'est annoncé par la docstring (`:1`) et justifié (partagé par les trois services chunk) ; à garder à l'œil s'il s'y ajoute d'autres gardes.
- `domain/chunk_editing.py` expose à la fois une fonction `split` (`:66`) et une méthode `EditJournal.split` (`:189`) de sens différent (découper un chunk / journaliser un découpage). Lisible en contexte, mais un nom comme `EditJournal.split_of` éviterait l'homonymie.

---

## Ampleur de la mise en conformité restante, item par item

Gain par item : poids 1 = **+5,6 points**, poids 2 = **+11,1 points** (base 10/18, soit 56).

| Item | Poids → gain | Travail exact restant | Dont déprécié ou mort | Effort | Risque | Quick win ? |
|------|--------------|-----------------------|-----------------------|--------|--------|-------------|
| **3.1.1** | 1 → +5,6 | Voie (a) : la fiche 3.1.1 acte « nom = valeur renvoyée » pour les fonctions pures, plus 2 renommages (`_anchor` `source_service.py:234`, `_resolvable` `:258` ; 3 appels, 0 test). Voie (b), stricte : ≈ 224 fonctions Python, ≈ 51 JS | — | (a) **S** ; (b) M | Faible | **Oui par (a)**, bloqué par la décision |
| **3.2.1** | 2 → +11,1 | 2 fonctions : `write_document` (`tree_writer.py:69`, 227 l.) et `fetch_graph` (`queries.py:137`, 115 l.) | **2 sur 2** | L (découpage) ou retrait anticipé de l'ingestion | Moyen ; tests Neo4j ignorés sans serveur | Non, sauf retrait anticipé |
| **3.1.3** | 2 → +11,1 | ≈ 106 fragments, ≈ 75-85 messages ; ≈ 10 phrases à accords ; `Intl.NumberFormat` ; `lang` dynamique ; source de locale ; ≈ 5 assertions | — | Option B : **M** | Moyen : JS non exécuté par la CI | Non : décision produit |
| **3.2.2** | 1 → +5,6 | 54 fonctions : 33 Python, 12 front, 9 JS (+3 internes aux stores) | 7 Python + `renderGraph` | L | Moyen | Non |
| **3.2.3** | 1 → +5,6 | 32 signatures | 9 dépréciées ; 6 constructeurs DI | L | Moyen | Non |
| **3.3.1** | 1 → +5,6 | 41 fichiers | 7 dépréciés + 4 non atteignables | L | Moyen | Partiel : −5 en supprimant les 4 composants morts et 11 lignes de `chunk_service.py`, l'item reste ❌ |

### Scénarios chiffrés

| Scénario | Items rendus conformes | Poids conformes | Score | Verdict |
|----------|------------------------|-----------------|-------|---------|
| État actuel | — | 10 / 18 | **56** | NO-GO |
| Décision 3.1.1 (voie a) + 2 renommages | 3.1.1 | 11 / 18 | **61** | GO CONDITIONNEL |
| Retrait anticipé de l'ingestion (ou découpage des 2 fonctions Neo4j) | 3.2.1 | 12 / 18 | **67** | GO CONDITIONNEL |
| Les deux | 3.1.1, 3.2.1 | 13 / 18 | **72** | GO CONDITIONNEL |
| + cartes bilingues (option B) | + 3.1.3 | 15 / 18 | **83** | GO |
| + 3.2.2, 3.2.3, 3.3.1 | tout | 18 / 18 | **100** | GO |

Le retrait de l'ingestion (prévu en 0.8.0) traite 3.2.1 entièrement et retire 8 des 54 fonctions longues, 9 des 32 signatures et 7 des 41 fichiers.

**Corrections hors barème, sans risque :** les 5 commentaires « main.py » et celui du promoteur ; la suppression des composants front non atteignables (`features/chunks/ui/*` sauf ce qui serait réintroduit, `StatusBadge.vue`, barrels morts).

---

## Delta vs 0.7.4

**Score : 39 → 56 (+17).** Items conformes : 6/14 → 8/14.

| Écart 0.7.4 | Statut | Preuve (code actuel) |
|-------------|--------|----------------------|
| [MAJ] 3.1.3 Cartes MCP en français | **Partiellement corrigé** | Les 3 textes anglais relevés (`citation_app.html:680`, `:706`, `:825`) et 3 non relevés (`:718`, `:957`, `sources_app.html:1024`) sont traduits. Texte français hors i18n inchangé (choix assumé) |
| [MAJ] 3.2.1 Orchestration multi-responsabilités | **Partiellement corrigé** | `chunk_push_service.py:114` (24 l.), `parse_index.py:80` (29 l.), `analysis_service.py:466` (8 l.). Restent `tree_writer.py:69`, `queries.py:137`, inchangés |
| [MAJ] 3.3.2 `chunk_service.py` / `sources_view.py` | **Corrigé** | `chunk_service.py` (311 l.) = édition du chunkset seule ; push → `chunk_push_service.py`, arbre → `document_tree_service.py` + `domain/doc_tree.py`, erreurs → `chunk_errors.py`. `sources_view.py` (105 l.) = enregistrement seul ; contrat → `sources_wire.py`, mapping → `sources_mapping.py`, texte → `sources_text.py` |
| [MIN] 3.1.1 Nommage nom vs verbe | **Inchangé** | `_anchor` `source_service.py:234`, `_resolvable` `:258` ; 45 % dans les modules MCP/navigation |
| [MIN] 3.2.2 Fonctions > 30 lignes | **Partiellement corrigé** | 45 → 33 Python ; front 12 et JS 9 inchangés ; `builder.py:102` 69 → 92 |
| [MIN] 3.2.3 Fonctions > 4 paramètres | **Inchangé (29 → 32)** | 5 nouvelles, 2 supprimées (voir liste) |
| [MIN] 3.2.4 Flag arguments | **Corrigé** | `citation_app.html:1034` `refitToFrame` / `:1041` `fitToFrameIfResized` ; `sources_app.html:613` `drawNeighbour` / `:616` `drawCurrent` ; `PagePreviewWithOverlay.vue:388` `keepRendered` / `:393` `releaseRendered`. Aucun autre littéral booléen passé à une fonction du projet |
| [MIN] 3.3.1 Fichiers > 300 lignes | **Inchangé (42 → 41)** | 2 sorties `.py`, 2 entrées (`chunk_push_service.py`, `settings.py`), `IngestLaunchDialog.vue` supprimé |
| [INFO] Constantes magiques | Inchangé | lignes décalées |
| [INFO] Code mort | Partiellement corrigé, constat élargi | 4 orphelins supprimés, `chunk_editing.py` et `formatAbsolute` vivants ; 15 modules front non atteignables |
| [INFO] Commentaires périmés | Partiellement corrigé | `chunk_service.py` et tombstone corrigés ; 5 « main.py » restent |
| [INFO] Booléens de configuration | Inchangé | + `_apply_analysis_effects(chunked=)`, `set_connection_policy(read_only=)` |
| [INFO] Variables d'une lettre | Inchangé | |
| [INFO] `get_*` à mémoïsation | Inchangé | + 4 lectures pures |
| [INFO] JS inline hors lint | Inchangé | |
| [INFO] Imbrication | Inchangé | |

**Régressions et nouveaux écarts introduits par la remédiation** (aucun ne fait basculer un item, aucun CRIT ni MAJ) :
- 3.2.3 : +5 signatures > 4 paramètres (`chunk_push_service.py:60`, `document_service.py:86`, `factories.py:220`, `ports.py:204`, `chunk_repo.py:80`), `analysis_service.py:71` passe de 9 à 10 — gravité MIN, dans l'écart existant.
- 3.3.1 : un nouveau fichier > 300 lignes (`chunk_push_service.py`, 339) et `infra/settings.py` franchit le seuil (320) — MIN, dans l'écart existant.
- 3.2.2 : `bootstrap/builder.py:102` +23 lignes (92), `setupObserver` +2 — MIN, dans l'écart existant.
- Code mort : `ChunksPanel.vue` devient orphelin par la suppression de `DocChunkTab.vue` ; `features/chunks/index.ts` n'est plus importé — INFO.

---

## Points positifs

- **Les deux fourre-tout sont démontés proprement, sans changer le contrat HTTP.** `ChunkService` ne fait plus qu'éditer le chunkset (`services/chunk_service.py:1-19`) ; les routes push, diff et historique passent par `ChunkPushServiceDep` et l'arbre par `DocumentTreeServiceDep` (`api/document_chunks.py:148-187`). Le découpage a été précédé de tests épinglant le comportement (`02fdaf0`, `14322f8`, `05768ae`).
- **Les règles métier descendent dans le domaine, pures** : découpage et fusion (`domain/chunk_editing.py`), formats de sérialisation (`domain/chunk_serialization.py`, une seule source pour les trois formes écrites), recherche de citation (`domain/citation_match.py`), budget de lecture (`domain/read_budget.py`), arbre du document (`domain/doc_tree.py`).
- **Une seule fabrique de lignes de journal** (`EditJournal`, `domain/chunk_editing.py:159`) remplace les constructions `ChunkEdit` dispersées ; `rechunk_document`, `split_chunk` et `merge_chunks` tombent de 56-79 lignes à 19-27.
- **Les flag arguments sont remplacés par des noms d'intention**, garde anti-boucle de `fitToFrame` conservée et testée (`tests/test_mcp_apps.py:449-462`).
- **Les docstrings des modules extraits disent pourquoi ils existent** (`services/chunk_push_service.py:1-10`, `services/document_tree_service.py:1-7`, `mcp_adapter/sources_wire.py:1-17`, qui documente aussi l'écart de vocabulaire *hop*/*round* conservé pour ne pas casser le contrat publié).
- **Aucun code commenté, aucun texte français, aucun import désordonné** introduits par ≈ 100 commits de remédiation ; `ruff check --select I` passe.
- 1 761 lignes de composants et de tests morts supprimées ; `i18n.ts` −69 lignes de traductions orphelines.

---

## Verdict partiel : NO-GO

Score **56/100** (< 60), **0 écart CRITICAL**, **2 écarts MAJOR** (sous le seuil de 3).

Le NO-GO vient du barème, pas d'un risque fonctionnel. La remédiation a corrigé les deux items qui ne dépendaient que du code (3.2.4, 3.3.2) et la moitié structurante de 3.2.1. Les deux MAJ restants dépendent d'une décision : la langue des cartes MCP (3.1.3) et le calendrier de retrait de l'ingestion (3.2.1, dont les 2 fonctions restantes sont dépréciées).

Le chemin le plus court vers le GO CONDITIONNEL est une décision de gouvernance : **acter la convention 3.1.1 (voie a) dans la fiche et renommer `_anchor` / `_resolvable`** (effort S) → **61**. Le retrait anticipé de l'ingestion porte ensuite le score à **72** ; les cartes bilingues (option B) à **83**.
