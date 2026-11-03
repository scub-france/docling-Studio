# Rapport d'audit : Clean Code

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : release/0.7.4 @ 1de1929 (= tag v0.7.3 + 2 commits README)
**Baseline** : `docs/audit/reports/release-0.7.3/03-clean-code.md` (commit `02adc68`, score 44). Le re-audit 0.7.3 n'avait pas re-noté l'audit 03.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 14 |
| Score | 39 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 3 |
| Ecarts MINOR | 5 |
| Ecarts INFO | 8 |

**Detail du calcul** : somme des poids conformes = 7 (3.1.2=1, 3.1.4=1, 3.2.5=2, 3.3.3=1, 3.4.1=1, 3.4.2=1) sur un total de 18, soit `7 / 18 * 100 = 38,9`, arrondi à **39**.

**Pourquoi le score baisse (44 → 39) alors que le code n'a pas régressé.** Depuis `02adc68`, le code source n'a bougé que dans 5 fichiers (voir « Delta »), et aucun écart de 0.7.3 n'est corrigé. La perte de 5 points vient d'un seul item : **3.2.4 (flag arguments, poids 1) passe de conforme à non conforme**.
- En 0.7.3, cet item avait été jugé sur les seuls booléens Python, qui sont des options de configuration en keyword-only.
- Cet audit a aussi examiné le TS/Vue et le JS des cartes MCP. Il y trouve trois vrais flag arguments, **tous antérieurs à 0.7.3** : `fitToFrame(true)` / `fitToFrame(false)`, `draw(true)` / `draw(false)` et `updateRenderWindow(page, isIntersecting)`.
- Avec la lecture de 0.7.3, le score serait resté à 44.
- La correction est un quick win, de taille S (voir § Ampleur).

**Périmètre.**
- `document-parser/`, hors `.venv/`, `__pycache__/` et `tests/` : 119 fichiers `.py` (19 773 lignes) et les 2 pages HTML servies par le serveur MCP, `mcp_adapter/citation_app.html` (1 177 l.) et `sources_app.html` (1 188 l.). Ces pages sont auditées comme du code source.
- `frontend/src/`, hors `*.test.*` : 150 fichiers `.vue`/`.ts` (26 386 lignes).

**Méthode.** Analyse statique uniquement ; les suites de tests n'ont pas été lancées.
- **Tailles de fichiers** : `wc -l`.
- **Fonctions Python** : mesurées par AST. On compte les lignes de corps, sans la signature ni la docstring, et les paramètres hors `self`/`cls`.
- **Fonctions TS, Vue et JS des cartes** : mesurées avec le parseur TypeScript du projet (`frontend/node_modules/typescript`). L'étendue compte la signature, comme en 0.7.3.
- **Littéraux français des cartes** : extraits avec le même parseur (chaînes, gabarits, attributs `aria-label`/`title`/`alt`), puis filtrés par lexique et relus à la main.
- **Imports** : `ruff check` 0.16.4 avec la configuration du projet ; heuristique d'ordre côté front.
- **Booléens** : inventaire par AST des paramètres `bool` en Python, et des appels qui passent un littéral `true`/`false` en TS et dans le JS des cartes.

---

## Metriques

| Mesure | 0.7.3 (`02adc68`) | 0.7.4 (`1de1929`) | Commentaire |
|--------|-------------------|-------------------|-------------|
| Fichiers `.py` source (hors tests) | 119 (19 769 l.) | 119 (19 773 l.) | +4 l. : commentaires dans `settings.py` et `analysis_service.py` |
| Fichiers `.vue`/`.ts` source (hors tests) | 150 (26 379 l.) | 150 (26 386 l.) | +7 l. : `ConfigSource` déplacé, libellés MCP |
| `.py` > 300 lignes | 14 (+2 HTML) | **14 (+2 HTML)** | inchangé ; `analysis_service.py` 586 → 589 |
| `.vue`/`.ts` > 300 lignes | 26 | **26** | dont `shared/i18n.ts` (1 474 l., données). Le rapport 0.7.3 annonçait « 16 fichiers entre 301 et 456 » ; recomptés sur `02adc68`, ils sont 15 |
| Fonctions Python > 30 lignes de corps | 45 | **45** | identiques ; 83 si l'on compte signature et docstring |
| Fonctions TS/Vue > 30 lignes (hors stores Pinia setup) | 12 | **12** | + 3 fonctions internes à des stores (35, 33 et 32 l.) |
| Fonctions JS des cartes MCP > 30 lignes | 6 relevées | **9** | 3 non relevées en 0.7.3, code inchangé |
| Fonctions Python > 4 paramètres | 29 | **29** | identiques ; 0 côté front et JS des cartes |
| Flag arguments (TS / JS) | non mesuré | **3** | préexistants (voir MIN 3.2.4) |
| Imbrication max (Python / TS / JS) | 7 / 4 / 4 | 7 / 4 / 4 | `local_chunker.py:24`, inchangé |
| Code commenté laissé en place | 0 | 0 | |
| Texte UI français hors `i18n.ts` (cartes MCP) | « ~64 lignes » | **≈ 80 lignes, ≈ 100 fragments** | Même code. Le comptage est plus exhaustif : attributs `aria-label`/`alt`/`title`, table `KIND_LABELS`, fragments de phrases composées. S'y ajoutent **3 textes anglais** affichés dans une carte française |
| Composants Vue orphelins (0 importeur) | non mesuré | **4 (1 034 l.)** | préexistants (voir INFO code mort) |

### Fichiers > 300 lignes (liste exhaustive)

**Python (14)** :

| Fichier | Lignes | Note |
|---------|--------:|------|
| `services/chunk_service.py` | 1019 | identique à v0.7.0 |
| `api/schemas.py` | 849 | |
| `services/analysis_service.py` | 589 | +3 |
| `domain/ports.py` | 542 | |
| `infra/serve_converter.py` | 402 | |
| `services/store_service.py` | 395 | déprécié, retiré en 0.8.0 |
| `domain/navigation.py` | 385 | |
| `mcp_adapter/sources_view.py` | 369 | |
| `domain/source_map.py` | 354 | |
| `bootstrap/factories.py` | 354 | |
| `domain/models.py` | 331 | |
| `infra/neo4j/tree_writer.py` | 310 | déprécié |
| `services/citation_service.py` | 307 | |
| `infra/docling_tree.py` | 307 | |

**Hors `.py`** : `mcp_adapter/sources_app.html` (1 188) et `mcp_adapter/citation_app.html` (1 177). `services/source_service.py` (293) et `infra/settings.py` (280) restent sous le seuil.

**Front (26)**, avec le détail script / template / style :

| Fichier | Lignes | Script / template / style | Note |
|---------|-------:|---------------------------|------|
| `shared/i18n.ts` | 1474 | — | données |
| `pages/StudioPage.vue` | 1450 | 175 / 505 / 762 | |
| `features/mcp-config/ui/McpConfigSection.vue` | 1110 | 170 / 355 / 577 | |
| `features/chunking/ui/ChunkPanel.vue` | 801 | 111 / 221 / 461 | |
| `pages/DocParseTab.vue` | 794 | **318** / 160 / 308 | |
| `features/document/ui/PagePreviewWithOverlay.vue` | 720 | **400** / 121 / 191 | |
| `pages/DocsLibraryPage.vue` | 701 | 157 / 201 / 335 | |
| `features/analysis/ui/ResultTabs.vue` | 679 | | |
| `features/analysis/ui/GraphView.vue` | 657 | **437** / 59 / 153 | déprécié |
| `features/chunks/ui/ChunksEditor.vue` | 622 | | |
| `features/store/ui/StoreForm.vue` | 520 | | déprécié |
| `features/document/ui/ElementProperties.vue` | 456 | | |
| `features/analysis/ui/StructureViewer.vue` | 438 | 242 / 58 / 130 | |
| `pages/DocumentsPage.vue` | 436 | | |
| `features/analysis/ui/NodeDetailsPanel.vue` | 409 | | vue graphe, dépréciée |
| `pages/IngestLaunchDialog.vue` | 399 | | **orphelin** |
| `pages/DocsNewPage.vue` | 391 | | |
| `features/chunks/ui/ChunkItem.vue` | 387 | | |
| `features/admin-config/ui/ReasoningConfigSection.vue` | 386 | | |
| `features/chunks/ui/StrategyPopover.vue` | 369 | | |
| `pages/AnalysisLibraryPage.vue` | 365 | | |
| `features/ingestion/ui/IngestPanel.vue` | 346 | | déprécié |
| `features/analysis/ui/BboxOverlay.vue` | 312 | | |
| `shared/ui/AppSidebar.vue` | 304 | | |
| `features/chunks/ui/ChunksPanel.vue` | 301 | | |
| `app/App.vue` | 301 | 26 / 42 / 225 | |

---

## Checklist

| # | Item | Poids | Conforme | Statut vs 0.7.3 |
|---|------|-------|----------|-----------------|
| 3.1.1 | Fonctions nommées avec des verbes d'action | 1 | ❌ | inchangé |
| 3.1.2 | Variables qui expriment l'intention | 1 | ✅ | inchangé |
| 3.1.3 | Tout le code en anglais — traductions dans `shared/i18n.ts` | 2 | ❌ | inchangé (`lang` corrigé) |
| 3.1.4 | Pas d'abréviations ambiguës | 1 | ✅ | inchangé |
| 3.2.1 | Chaque fonction fait une seule chose | 2 | ❌ | inchangé |
| 3.2.2 | Aucune fonction > 30 lignes | 1 | ❌ | inchangé |
| 3.2.3 | Aucune fonction > 4 paramètres | 1 | ❌ | inchangé (29) |
| 3.2.4 | Pas de flag arguments | 1 | ❌ | **nouveau** : préexistant, non relevé en 0.7.3 |
| 3.2.5 | Un `get_*` ne modifie pas d'état | 2 | ✅ | inchangé |
| 3.3.1 | Aucun fichier source > 300 lignes | 1 | ❌ | inchangé |
| 3.3.2 | Un seul concept par fichier | 2 | ❌ | inchangé |
| 3.3.3 | Imports ordonnés | 1 | ✅ | inchangé |
| 3.4.1 | Commentaires = « pourquoi » | 1 | ✅ | inchangé |
| 3.4.2 | Pas de code commenté laissé en place | 1 | ✅ | inchangé |

---

## Ecarts constates

### [MAJ] Cartes MCP : libellés UI en français codés en dur, hors i18n — statut : **inchangé** (seul `lang` est corrigé)

- **Localisation**
  - **`document-parser/mcp_adapter/citation_app.html`** : environ 24 lignes et 27 fragments français.
    - `:395` (« En attente d'une citation… ») ;
    - `:426-439` (table `KIND_LABELS` : « titre de section », « paragraphe », « élément de liste », « tableau », « légende »…) ;
    - `:599-615` (« Texte exact du document », « Lire la suite », « Copier la citation », « Ouvrir dans Docling Studio ») ;
    - `:644`, `:650`, `:814`, `:832`, `:836`, `:855`, `:857`, `:991`, `:1153`, `:1157`, `:1165`.
  - **`document-parser/mcp_adapter/sources_app.html`** : environ 57 lignes et 70 fragments.
    - `:317` ;
    - `:391-400` (verdicts « vérifiée », « non vérifiée », « introuvable ») ;
    - `:489-491`, `:509`, `:531`, `:548`, `:569-590`, `:632-635`, `:650` ;
    - `:722-751` (onglet Détails) ;
    - `:779-787`, `:798-855`, `:951`, `:972`, `:979` ;
    - `:998` (`TIMEOUT_MESSAGE = "l’hôte n’a pas répondu"`) ;
    - `:1165-1175`.
  - **Formatage figé en français** : `sources_app.html:343-348` (`fr()` fixé sur `"fr-FR"`), `:336-341` (`num()`, espace comme séparateur de milliers) et `:358` (`plural()`).
- **Constat**
  - Les deux fichiers sont inchangés depuis `02adc68`, à une ligne près : `citation_app.html:2` passe de `lang="en"` à `lang="fr"` (commit `6711444`). L'incohérence `lang` relevée en 0.7.3 est donc **corrigée**, et les deux pages déclarent maintenant `lang="fr"`.
  - Le reste n'a pas bougé. Les cartes affichent environ 80 lignes de texte français en dur, sans aucun mécanisme de traduction. Le mainteneur assume ce choix produit, fait pour la démo.
  - **Nouveau détail factuel : la carte de citation mélange les langues.** Trois textes anglais s'affichent dans la carte, pourtant déclarée française :
    - `citation_app.html:680` : « Clipboard blocked — select the text below » ;
    - `:706` : « the host did not answer » ;
    - `:825` : « the server refused ».

    Les deux derniers sont insérés dans une phrase française à `:832`, ce qui produit par exemple « Aperçu de la page indisponible — the host did not answer. ».
  - Le même timeout est en français dans `sources_app.html:998`.
  - Le repli texte serveur `mcp_adapter/sources_view.py:336-369` (`sources_text`) reste en anglais.
  - Côté Studio, la seule chaîne française hors `i18n.ts` est l'autonyme « Français » du sélecteur de langue (`frontend/src/features/settings/ui/SettingsPanel.vue:58`, `:136`). C'est une convention UX, pas un écart.
- **Regle violee** : item 3.1.3 — « Tout le code est en anglais — les traductions i18n sont dans `shared/i18n.ts` » (poids 2).
- **Coût réel d'une table de libellés** (évaluation demandée). Les mesures sont faites sur le code actuel.
  1. **Inventaire.** Il faut sortir ≈ 100 fragments, soit ~70-80 messages une fois les phrases recomposées, plus les 3 chaînes anglaises citées plus haut.
  2. **La grammaire française est codée dans le JS : ce n'est pas un simple remplacement de chaînes.**
     - `plural()` (`sources_app.html:358`) ajoute un « s » aux noms **et aux participes et adjectifs**. Par exemple : `plural(n, "lue")` (`:771`, `:833`), `plural(n, "affichée")` et `plural(n, "introuvable")` (`:748`), `plural(n, "cité")` (`:836`).
     - `une ${noun} par tour` (`:735`) suppose que « page » et « section » sont tous deux féminins.
     - En anglais ces accords n'existent pas, et d'autres apparaissent. Une dizaine de phrases composées (`:731`, `:735`, `:748`, `:770-783`, `:822`, `:833-836`, `:570`, `:583`, `:590`) doivent donc devenir des **messages paramétrés par langue**, par exemple `t.sectionsRead(n, noun)`, et non des entrées d'un dictionnaire.
  3. **Autres adaptations.**
     - Remplacer `fr()` et `num()` par `Intl.NumberFormat(locale)`.
     - Les guillemets « » (`:632`, `:850`) dépendent de la langue.
     - L'attribut `lang` (`:2` des deux pages) doit devenir dynamique.
  4. **Source de la locale : il n'en existe aucune aujourd'hui.**
     - Le backend ne connaît pas la langue de Studio, qui est stockée par navigateur (`frontend/src/features/settings/store.ts:25`, `localStorage`, défaut `fr`).
     - Option 1 : `navigator.language` dans l'iframe.
     - Option 2 : le `hostContext` du handshake. Il est déjà lu (`citation_app.html:752`, `sources_app.html:1048`) et réappliqué sur `host-context-changed` (`citation_app.html:1142`, `sources_app.html:1158`). **Je n'ai pas pu vérifier localement que la spec MCP Apps y définit un champ `locale`.**
     - Option 3 : un réglage serveur injecté dans le HTML. C'est compatible avec `_versioned_uri` (`mcp_adapter/apps.py:50-64`), qui hache le contenu : chaque variante de langue aurait sa propre URI.
  5. **Tests.**
     - `tests/test_mcp_apps.py` et `tests/test_mcp_sources_app.py` épinglent ≈ 20 chaînes françaises. Exemples : `test_mcp_apps.py:317`, `:324`, `:327-328` (`test_the_element_kind_is_said_in_french`) ; `test_mcp_sources_app.py:314`, `:361-364`, `:370-373`, `:376`, `:381-382`.
     - Si la table `fr` reste dans le fichier, les assertions par sous-chaîne passent toujours.
     - Celles qui épinglent la **forme du code** cassent : `'tab("details", "Détails")'` (`:314`), `'return "vérifiée"'` (`:364`), `"<b>Pourquoi</b>"` (`:373`) et `'text: "paragraphe"'` (`:327`), selon la structure retenue. Cela fait environ 5 assertions à réécrire, plus des tests de sélection de locale.
  6. **Risque.** Aucun test n'exécute le JS des cartes : ce ne sont que des recherches de sous-chaînes. Les cartes échappent aussi à ESLint, Prettier et au typage (`frontend/eslint.config.js:10`). Une refonte d'environ 100 chaînes dans ≈ 1 650 lignes de JS non exécuté par la CI doit donc être vérifiée à la main, dans un hôte réel et dans les deux langues.
  7. **Estimation.**

     | Option | Contenu | Effort | Effet sur 3.1.3 |
     |--------|---------|--------|-----------------|
     | A | Tout en anglais, sans table | S-M (≈ ½ j) | Conforme à la lettre, mais contredit le choix produit |
     | B | Table locale `MESSAGES = { en, fr }`, `en` par défaut, locale lue depuis l'hôte | M (≈ 1 à 1,5 j, recette manuelle comprise) | Le rapport 0.7.3 jugeait cette remédiation suffisante ; même lecture ici |
     | C | Lecture stricte : clés dans `shared/i18n.ts`, exportées au build vers `document-parser` | L | Disproportionné : crée un couplage de build entre le front et l'image backend, qui a son propre `Dockerfile` |
- **Remediation** : option B si le français doit rester disponible pour la démo, avec l'anglais par défaut. Dans tous les cas, corriger tout de suite les 3 chaînes anglaises de la carte de citation (`:680`, `:706`, `:825`) : 3 lignes, risque nul.

### [MAJ] Fonctions d'orchestration multi-responsabilités — statut : **inchangé** (dette 0.7.0, cas 0.7.3 toujours présents)

- **Localisation**
  - Dette 0.7.0 :
    - `document-parser/services/chunk_service.py:574` (`push_to_store`, 103 l. de corps) ;
    - `document-parser/infra/neo4j/tree_writer.py:69` (`write_document`, 227 l.) ;
    - `document-parser/infra/neo4j/queries.py:137` (`fetch_graph`, 115 l.).

    `git diff v0.7.0..HEAD` est vide sur les trois fichiers.
  - Cas 0.7.3 :
    - `document-parser/domain/parse_index.py:80` (`build_index`, 79 l., inchangé) ;
    - `document-parser/services/analysis_service.py:460` (`_finalize_analysis`, 67 l. ; ligne `:457` → `:460` à cause du commentaire `to_thread` ajouté en `:177-179`).
- **Constat**
  - Aucune extraction n'a été faite.
  - `build_index` enchaîne toujours quatre calculs indépendants : indexation `by_ref` (`:84-88`), pile des titres vers `heading_path`/`section_end` (`:93-111`), tailles de page (`:113-120`), puis provenance et bbox (`:122-137`).
  - `_finalize_analysis` sérialise, chunke, marque terminé, enregistre la version, met à jour le statut et le nombre de pages, fait la transition de cycle de vie, puis écrit le graphe. Elle termine aussi le chemin d'import (`analysis_service.py:187`).
  - Trois des cinq cas (`push_to_store`, `write_document`, `fetch_graph`) relèvent du périmètre ingestion Neo4j/OpenSearch, déprécié et retiré en 0.8.0 (`CHANGELOG.md:27-29`).
- **Regle violee** : item 3.2.1 — « Chaque fonction fait une seule chose » (poids 2).
- **Remediation**
  - `build_index` : extraire `_items_by_ref`, `_heading_paths`, `_page_sizes` et `_provenance`, des fonctions pures déjà couvertes indirectement (`tests/test_navigation_domain.py`, `test_source_service.py`, `test_page_regions.py`). Effort S, risque faible.
  - `_finalize_analysis` : séparer « persister le résultat » des « effets post-analyse » (version, cycle de vie, graphe). L'ordre doit être conservé : la version est enregistrée (`:498`) **avant** le passage à COMPLETED (`update_status`, `:508`). Effort M, risque moyen.
  - Les trois cas dépréciés : les refactorer coûte L, sur du code dont les tests Neo4j sont ignorés sans serveur. Mieux vaut **anticiper leur suppression**, ou la dater explicitement en 0.8.0.

### [MAJ] Fichiers fourre-tout `chunk_service.py` et `sources_view.py` — statut : **inchangé**

- **Localisation**
  - `document-parser/services/chunk_service.py` (1 019 l., identique à v0.7.0) :
    - classe `ChunkService` `:146` ;
    - push et diff vers un store : `:540` (`diff_against_store`), `:574` (`push_to_store`), `:693` (`list_pushes`), `:743` (`_upsert_link_ingested`), `:765` (`_mark_link_failed`), avec `_chunk_to_ingestion_dict` `:851` et `_compute_chunkset_hash` `:865` ;
    - projection d'arbre : `get_tree` `:789`, `_build_tree_nodes` `:885`, `_build_item_subtree` `:942`, `_make_node` `:975`, `_display_label` `:990`, `_truncate` `:1015`.
  - `document-parser/mcp_adapter/sources_view.py` (369 l., inchangé) :
    - DTO du contrat `:43-153` ;
    - enregistrement de l'outil `:163` ;
    - mapping domaine → wire `:223-335` ;
    - rendu texte `:336-369`.
- **Constat**
  - `chunk_service.py` porte trois concepts : édition du chunkset, push/diff vers un store, projection d'affichage de l'arbre.
  - `sources_view.py` mélange contrat, traduction et rendu, précisément ce que la docstring de `mcp_adapter/wire_mapping.py:3-6` dit avoir voulu éviter.
- **Regle violee** : item 3.3.2 — « Un seul concept par fichier » (poids 2).
- **Remediation** (voir aussi § Ampleur)
  - **Projection d'arbre** vers `services/tree_projection.py` (`:789-813` et `:885-1019`, environ 160 lignes). C'est mécanique : les tests n'importent de `chunk_service` que `ChunkService` et les classes d'erreur (`tests/test_chunk_service.py:30-37`, `tests/test_document_chunks_api.py:12-17`). Risque faible.
  - **Push** (`:540-787`, environ 250 lignes) vers un `ChunkStorePushService`. Il faut toucher le câblage (`bootstrap/factories.py:231`, `bootstrap/builder.py:115`), les 3 routes (`api/document_chunks.py:189-233`) et environ 34 références de tests dans 3 fichiers. Effort M, risque moyen. Ou bien suppression avec l'ingestion.
  - **`sources_view.py`** :
    - DTO vers un nouveau `sources_wire.py`. `wire.py`, à 227 lignes, passerait à 338 lignes s'il les recevait.
    - Mapping et rendu texte vers `sources_mapping.py`.
    - Seul l'enregistrement reste dans `sources_view.py`.

    Les tests n'importent que `SOURCES_APP_HTML` (`test_mcp_sources_app.py:20`, `test_mcp_apps.py:26`). Risque très faible.

### [MIN] Convention de nommage : environ la moitié des fonctions MCP/navigation portent un nom, pas un verbe — statut : **inchangé**

- **Localisation**
  - Python : tous les cas relevés en 0.7.3 sont présents aux mêmes lignes.
    - `domain/source_map.py:236` (`_totals`), `:292` (`_hops`), `:347` (`_cost`), `:351` (`_stronger`) ;
    - `services/source_service.py:224` (`_marks`), `:234` (`_title`), `:258` (`_anchor`), `:282` (`_resolvable`) ;
    - `mcp_adapter/sources_view.py:278` (`_hop`), `:323` (`_node`), `:365` (`_said`) ;
    - `mcp_adapter/wire_mapping.py:46` (`document_row`), `:57` (`search_result`), `:71` (`outline_entry`), `:84` (`outline_result`), `:106` (`citation_ref`), `:120` (`citation_out`), `:165` (`excerpt_result`), `:188` (`verification_result`) ;
    - `domain/quote_marks.py:79-132` ;
    - `services/citation_image_service.py:133` (`_image`).
  - JS : `sources_app.html:483` (`head`), `:506` (`sources`), `:639` (`foot`), `:710` (`details`), `:758` (`coverage`), `:803` (`roundsTable`), `:842` (`quotesList`)…
- **Constat**
  - Même heuristique qu'en 0.7.3, avec une liste de verbes : **96 fonctions sur 199 (48 %)** dans les 28 modules Python ajoutés depuis v0.7.2. On compte **19 % (100/530)** dans les autres modules.
  - JS des cartes : 49 noms non verbaux sur 96 fonctions nommées, dont une poignée de faux positifs (`handshake`, `flush`).
  - Coût concret, inchangé : `_anchor(uri, unknown)` (`services/source_service.py:258-263`) et `_resolvable(...)` (`:282-293`) **ajoutent à la liste `unknown` reçue en argument** (`:262`, `:290`). Rien dans leur nom ne le signale. Elles sont appelées en `:101`, `:103` et `:111`, dans `show`.
- **Regle violee** : item 3.1.1 (poids 1).
- **Remediation** : voir § Ampleur. Deux voies :
  - (a) **décision de gouvernance** : acter dans la fiche 3.1.1 la convention « nom = valeur renvoyée » pour les fonctions **pures**, puis renommer les 2 fonctions à effet de bord (`_anchor` → `_parse_or_report`, `_resolvable` → `_partition_known`). Il y a 3 sites d'appel et 0 référence dans les tests ;
  - (b) **lecture stricte** : environ 140 renommages mécaniques.

### [MIN] Fonctions au-delà de 30 lignes — statut : **inchangé** (45 Python ; 3 cas JS non relevés en 0.7.3)

- **Localisation** : liste exhaustive. **Python (45)** :
  - **Dépréciées (ingestion, 9)** :
    - `infra/neo4j/tree_writer.py:69` (227 l.), `infra/neo4j/queries.py:137` (115), `infra/neo4j/chunk_writer.py:55` (107) ;
    - `services/chunk_service.py:574` (103), `services/chunk_service.py:693` (32) ;
    - `services/store_service.py:237` (58), `services/store_service.py:186` (37) ;
    - `domain/vector_schema.py:121` (50) ;
    - `bootstrap/factories.py:316` (34).
  - **Code mort (3)** : `domain/chunk_editing.py:169` (36) et `:116` (33), `services/chunk_service.py:205` (35).
  - **Code vivant (33)** :

    | Module | Fonctions > 30 lignes (ligne de début, lignes de corps) |
    |--------|------------------------------------------------------|
    | `mcp_adapter/server.py` | `:95` (87) |
    | `infra/docling_agent_reasoning.py` | `:149` (86) |
    | `mcp_adapter/apps.py` | `:146` (80) |
    | `services/chunk_service.py` | `:451` (79), `:335` (56), `:393` (56), `:885` (38), `:149` (33) |
    | `domain/parse_index.py` | `:80` (79) |
    | `infra/settings.py` | `:197` (78), `:125` (69) |
    | `bootstrap/builder.py` | `:98` (69), `:185` (33) |
    | `services/analysis_service.py` | `:460` (67), `:285` (46) |
    | `services/citation_service.py` | `:94` (62) |
    | `infra/local_chunker.py` | `:24` (60) |
    | `mcp_adapter/sources_view.py` | `:223` (52), `:163` (38) |
    | `services/version_service.py` | `:148` (48) |
    | `infra/docling_pages.py` | `:68` (48) |
    | `domain/outline_builder.py` | `:75` (43) |
    | `services/export_service.py` | `:43` (41) |
    | `services/source_service.py` | `:91` (40) |
    | `main.py` | `:129` (37) |
    | `bootstrap/mcp_mount.py` | `:84` (37) |
    | `services/document_service.py` | `:67` (35) |
    | `services/navigation_service.py` | `:124` (34) |
    | `infra/serve_converter.py` | `:141` (34), `:339` (32) |
    | `domain/source_map.py` | `:178` (33), `:292` (32) |
    | `domain/trace_builder.py` | `:40` (31) |

  - **Front (12, hors stores Pinia setup)** :
    - `features/analysis/ui/GraphView.vue:193` (`renderGraph`, 216 l., déprécié) ;
    - `features/document/ui/BboxCanvas.vue:62` (75) ;
    - `features/analysis/ui/StructureViewer.vue:146` (66) ;
    - `features/analysis/ui/BboxOverlay.vue:85` (61) et `:152` (35) ;
    - `features/analysis/sectionParenting.ts:31` (58) ;
    - `shared/composables/usePagination.ts:19` (53) ;
    - `features/document/ui/PagePreviewWithOverlay.vue:331` (53) et `:425` (46) ;
    - `features/document/ui/DownloadDropdown.vue:130` (49) ;
    - `shared/ui/accordion.ts:58` (40) ;
    - `app/router/index.ts:39` (32).

    S'y ajoutent 3 fonctions internes à des stores : `features/feature-flags/store.ts:154` (35), `features/reasoning/store.ts:77` (33), `features/analysis/store.ts:100` (32).
  - **JS des cartes (9)** :
    - `citation_app.html:460` (`renderMarkdown`, 77), `:808` (`hydrateLocator`, 68), `:565` (`render`, 66) ;
    - `sources_app.html:710` (`details`, 45), `:516` (`strip`, 38), `:803` (`roundsTable`, 37) ;
    - **non relevées en 0.7.3** : `citation_app.html:1123` (écouteur `message`, 45), `sources_app.html:1143` (écouteur `message`, 35), `sources_app.html:758` (`coverage`, 32).
- **Constat** : aucun corps n'a changé depuis 0.7.3. Les deux écouteurs `message` sont des tables de dispatch commentées, proches du « boilerplate inévitable ». `build_mcp_server`, `_register_citation_card` et `register_sources_view` enregistrent des outils FastMCP par fermetures décorées, ce qui relève du même cas.
- **Regle violee** : item 3.2.2 (poids 1).
- **Remediation** : traiter d'abord `build_index` (voir 3.2.1), `renderMarkdown` (un rendu par type de bloc) et `hydrateLocator`. Dans `build_mcp_server`, une fonction `_register_<tool>` par outil.

### [MIN] Fonctions à plus de 4 paramètres — statut : **inchangé** (29)

- **Localisation** : liste exhaustive, nombre de paramètres hors `self` entre parenthèses.
  - **Dépréciées (9)** :
    - `services/store_service.py:237` (10) et `:186` (9) ;
    - `services/store_backend_resolver.py:78` (8) ;
    - `infra/neo4j/tree_writer.py:69` (7) ;
    - `infra/opensearch_pool.py:43` (5) ;
    - `infra/opensearch_store.py:76` (5) ;
    - `services/chunk_service.py:743` (5) ;
    - `services/ingestion_service.py:85` (5) et `:161` (5).
  - **Code mort (1)** : `domain/chunk_editing.py:46` (6).
  - **Constructeurs DI (5)** :
    - `services/chunk_service.py:149` (12) ;
    - `services/analysis_service.py:83` (9) ;
    - `services/app_config_service.py:68` (7) ;
    - `services/mcp_config_service.py:112` (6) ;
    - `services/source_service.py:76` (5).
  - **Autres (14)** :
    - `mcp_adapter/server.py:95` (6) et `:168` (`read_element`, 6, miroir du schéma publié) ;
    - `services/chunk_service.py:942` (6) et `:975` (5) ;
    - `services/citation_image_service.py:133` (6) et `:81` (5) ;
    - `services/navigation_service.py:124` (6) ;
    - `domain/models.py:105` (`mark_completed`, 5) ;
    - `domain/source_map.py:236` (5) ;
    - `infra/serve_converter.py:141` (5) ;
    - `services/analysis_service.py:285`, `:411` et `:555` (5 chacune) ;
    - `services/config_overrides.py:79` (5).
- **Constat** : liste identique à 0.7.3. 22 de ces signatures sur 29 ont au moins un paramètre keyword-only. Côté front et JS des cartes : aucune fonction au-delà de 4 paramètres.
- **Regle violee** : item 3.2.3 (poids 1).
- **Remediation** : inchangée.
  - Value object `ReadRequest` pour `read_element` côté `NavigationService`.
  - Objet de dépendances pour les constructeurs.
  - Le retrait de l'ingestion supprime 9 cas sur 29.

### [MIN] Flag arguments dans le JS des cartes et le front — statut : **nouveau** (préexistant, non relevé en 0.7.3)

- **Localisation**
  - **`document-parser/mcp_adapter/citation_app.html:1033`**, `fitToFrame(contentChanged)`.
    - Appels `fitToFrame(true)` en `:628`, `:645`, `:873` et `:881` ; `fitToFrame(false)` en `:1068`.
    - Le booléen court-circuite la garde de mémoïsation (`:1039`).
  - **`document-parser/mcp_adapter/sources_app.html:601`**, `const draw = (other) => …`.
    - Appels `draw(true)` en `:614` et `draw(false)` en `:615`.
    - Le booléen décide si le passage est dessiné par bloc quand aucune ligne n'est trouvée (`:610`).
  - **`frontend/src/features/document/ui/PagePreviewWithOverlay.vue:385`**, `updateRenderWindow(pageNumber, isIntersecting)`, appelée en `:369`.
    - Selon le booléen, la fonction fait deux choses distinctes : ajout à la fenêtre de rendu (`:386-388`), ou retrait et libération du raster (`:390-396`).
    - Introduite en 0.7.0 (`79f083e`), étendue en 0.7.2 (#336, `5ba48a2`).
- **Constat**
  - Ce sont des flag arguments au sens strict de l'item : « un booléen qui change le comportement ». Pour les deux premiers, des littéraux `true`/`false` sont passés aux sites d'appel.
  - Le rapport 0.7.3 avait jugé 3.2.4 conforme en n'examinant que les booléens Python. Ceux-ci restent hors de cause : voir l'INFO plus bas.
  - Aucun appel Python ne passe un booléen positionnel à une fonction du projet ; les 4 seuls cas trouvés sont des `dict.get(key, False)`.
- **Regle violee** : item 3.2.4 — « Pas de flag arguments » (poids 1).
- **Remediation**
  - `fitToFrame` : séparer `refitToFrame()` (contenu changé) et `fitToFrameIfResized()`, qui partagent un cœur privé. **Conserver la garde anti-boucle** sur `fittedFor`, que vérifie `tests/test_mcp_apps.py:442-447`. Ce test épingle la forme `fitToFrame(true)` / `fitToFrame(false)` et devra être adapté (2 assertions).
  - `draw` : deux fermetures nommées, `drawNeighbour` et `drawCurrent`.
  - `updateRenderWindow` : `entry.isIntersecting ? keepRendered(page) : releaseRendered(page)`.
  - Effort S (≈ 1 h), risque faible.

### [MIN] Fichiers sources au-delà de 300 lignes — statut : **inchangé**

- **Localisation** : liste exhaustive dans « Fichiers > 300 lignes » ci-dessus. Il y a 14 `.py`, 2 `.html` et 26 `.vue`/`.ts`, soit **42 fichiers**, dont `shared/i18n.ts`.
- **Constat**
  - Les volumes sont identiques à 0.7.3, à quelques lignes de commentaires près (`analysis_service.py` +3, `McpConfigSection.vue` +1, `i18n.ts` +2).
  - Plusieurs gros `.vue` dépassent le seuil surtout par leur CSS (`StudioPage.vue` : 762 l. de style).
  - `GraphView.vue` (437), `PagePreviewWithOverlay.vue` (400) et `DocParseTab.vue` (318) dépassent 300 lignes **de script seul**.
  - `McpConfigSection.vue` rend toujours trois sections d'accordéon dans un seul SFC.
  - 7 des 42 fichiers relèvent du périmètre déprécié ou orphelin : `store_service.py`, `tree_writer.py`, `GraphView.vue`, `NodeDetailsPanel.vue`, `StoreForm.vue`, `IngestPanel.vue`, `IngestLaunchDialog.vue`.
- **Regle violee** : item 3.3.1 (poids 1).
- **Remediation** : inchangée.
  - Découper `McpConfigSection.vue` en trois sections.
  - Sortir le pont hôte et le CSS commun des cartes.
  - Découper `chunk_service.py` (voir 3.3.2).
  - Supprimer `IngestLaunchDialog.vue`, qui est orphelin.

### [INFO] Constantes magiques, dont des doublons de constantes nommées — statut : **inchangé**

- **Localisation**
  - `document-parser/services/navigation_service.py:281` (`[:96]`, alors que `_MAX_TITLE_LEN = 96` et `truncate_title` existent dans `domain/parse_index.py:29` et `:204`) ;
  - `mcp_adapter/apps.py:206` et `mcp_adapter/sources_view.py:205` (`max(120, min(max_width, 1600))` en double) ;
  - `services/navigation_service.py:109` (`min(depth, 6)`, à côté de `_MAP_DEPTH = 6`, `services/source_service.py:48`) ;
  - `domain/outline_builder.py:44` (`max_nodes=200`, doublon de `services/navigation_config.py:33`) ;
  - `services/citation_image_service.py:71` (`24`, `72.0`, aussi dans `domain/navigation.py:75`) ;
  - `services/analysis_service.py:89` (`conversion_timeout = 600`) ;
  - `frontend/src/features/mcp-config/ui/McpConfigSection.vue:517` (`1500`, était `:516`) ;
  - `timeoutMs = 8000` dans `citation_app.html:701` et `sources_app.html:1000`.
- **Remediation** : réutiliser `truncate_title` et `NavigationConfig.max_outline_nodes` ; une constante `IMAGE_WIDTH_BOUNDS` partagée ; `POINTS_PER_INCH = 72`.

### [INFO] Code mort — statut : **inchangé**, avec **4 composants Vue orphelins non relevés en 0.7.3**

- **Localisation**
  - Déjà relevé en 0.7.3, toujours présent :
    - `document-parser/domain/chunk_editing.py`, importé seulement par `tests/test_chunk_editing.py` ;
    - `domain/lifecycle_aggregation.py:35`, `aggregate_lifecycle`, appelé seulement par `tests/test_lifecycle_aggregation.py` ;
    - `_chunk_promoter`, posé par `services/analysis_service.py:126` via `bootstrap/builder.py:137` mais jamais lu ;
    - `services/chunk_service.py:205`, `promote_from_analysis_if_empty`, sans appelant hors tests ;
    - `frontend/src/features/store/api.ts:84-129` : 8 des 9 fonctions n'ont aucun appelant hors tests ; seule `testStoreConnection` est utilisée, par `StoreForm.vue:334` ;
    - `features/chunks/api.ts:82` (`fetchChunkPushes`) et `shared/format.ts:26` (`formatAbsolute`), sans appelant.
  - **Non relevé en 0.7.3** : 4 composants `.vue` qu'aucun fichier de `frontend/src` n'importe.
    - `pages/IngestLaunchDialog.vue` (399 l.), avec sa dépendance `pages/DocIngestTab.logic.ts`, utilisée seulement par ce composant et par son test ;
    - `pages/DocChunkTab.vue` (241 l.) ;
    - `features/document/ui/HistoryDrawer.vue` (263 l.). La spec e2e `e2e/ui/src/test/resources/documents/doc-history-drawer.feature:49` l'attend encore (voir audit 09) ;
    - `features/analysis/ui/InspectResultTabs.vue` (131 l.), déjà signalé comme orphelin dans `docs/design/303-reasoning-trace-v2-parse-view.md:74`.

    Les quatre sont présents depuis au moins `dc87383` (2026-08-08).
- **Constat** : 0.7.4 n'ajoute aucun code mort. Les orphelins Vue, à eux seuls, totalisent 1 034 lignes, dont un fichier de plus de 300 lignes.
- **Remediation** : supprimer les 4 composants orphelins (`IngestLaunchDialog.vue` et `DocIngestTab.logic.ts` avec l'ingestion) ; le reste en 0.8.0 avec le retrait de l'ingestion. Supprimer `chunk_editing.py` ou le brancher (voir audit 01).

### [INFO] Commentaires périmés — statut : **inchangé**, constat élargi

- **Localisation**
  - **7 commentaires et docstrings** disent que le câblage est fait « in main.py », alors qu'il est fait dans `bootstrap/builder.py` et `bootstrap/factories.py` :
    - `services/analysis_service.py:108`, `:115`, `:518` ;
    - `services/chunk_service.py:194` ;
    - `services/app_config_service.py:9` ;
    - `services/reasoning_service.py:12` ;
    - `services/store_backend_resolver.py:93`.
  - Le commentaire « tombstone » `analysis_service.py:513-520` (était `:510-517`) contredit `:108-112`.
  - `frontend/src/pages/StudioPage.vue:16`, `:287`, `:470` et `:479` : noms de modes en français (« Configurer / V&eacute;rifier / PREPARER »).
- **Constat** : les commentaires restent majoritairement du « pourquoi », donc 3.4.1 est conforme ; ces blocs décrivent un état disparu. Le rapport 0.7.3 n'en citait qu'un sur sept.
- **Remediation** : remplacer « main.py » par `bootstrap/builder.py` (7 lignes, aucun risque) ; supprimer le tombstone avec le promoteur mort.

### [INFO] Booléens de configuration en paramètre Python (non comptés comme flag arguments) — statut : **inchangé**

- **Localisation**
  - Options de configuration MCP : `mcp_adapter/server.py:81` (`instructions(apps=…)`), `:95` (`build_mcp_server(apps=…, citation_card=…)`), `mcp_adapter/prompts.py:56` et `mcp_adapter/apps.py:123`.
  - Filtre `include_deleted` : `domain/ports.py:173` et `persistence/chunk_repo.py:117`.
  - Champs de données ou de configuration : `services/store_service.py:186` et `:237` (`is_default`), `services/mcp_config_service.py:112` (`read_only`, `mounted`), `infra/opensearch_*` (`verify_certs`).
  - Garde : `services/config_overrides.py:43` (`require_writable(read_only)`).
- **Analyse** : tous sont keyword-only, sauf la garde. Ils portent une configuration ou une donnée ; la fonction ne fait pas deux choses distinctes selon leur valeur. Ce jugement est celui de 0.7.3. Le non-conforme 3.2.4 vient du TS/JS (voir le MIN ci-dessus).

### [INFO] Variables d'une lettre et abréviations (3.1.2 / 3.1.4 jugés conformes) — statut : **inchangé**

- **Localisation**
  - `services/source_service.py:101` (`(a, w, f)`) et `:103` (`(a, q, st)`) ;
  - `mcp_adapter/sources_view.py:177` (`e`) ;
  - JS `sources_app.html:343` (`fr`), `pct`, `px`, `num`, `esc` ;
  - `chunk_service.py:98`, `:112`, `:116`, `:851`.
- **Analyse** : portées minuscules (compréhensions, helpers d'une ligne). Le sondage des identifiants Python de 4 caractères ou moins ne fait pas apparaître de nouvelle abréviation ambiguë. `neo`, `prov`, `cid` et `cur` sont locaux et lisibles.

### [INFO] `get_*` à mémoïsation (3.2.5 jugé conforme) — statut : **inchangé**

- **Localisation**
  - `services/navigation_service.py:101` (`get_outline` → cache LRU, `services/parse_loader.py`) ;
  - `infra/opensearch_pool.py:131`, `infra/neo4j/driver_pool.py:161` et `infra/secrets/fernet_box.py:114` (singletons paresseux) ;
  - à noter : `infra/neo4j/driver_pool.py:60` (`get`) lance `bootstrap_schema` au premier appel pour une clé (`:95-97`). C'est documenté dans la docstring (`:71`), et le module est déprécié.
- **Analyse** : les 47 fonctions `get*`/`_get*` Python et les 6 `get*` du front ont été revues. Ce sont des lectures pures, ou des effets de cache idempotents et documentés. Aucun effet de bord métier caché.

### [INFO] JS inline des cartes MCP : hors lint, pont hôte dupliqué — statut : **inchangé**

- **Localisation**
  - JS : `citation_app.html:396-1175` et `sources_app.html:319-1186`.
  - Périmètre ESLint : `frontend/eslint.config.js:10` (`src/**/*.{ts,js,vue}`).
  - Pont JSON-RPC/postMessage en double : `citation_app.html:690-800` et `sources_app.html:984-1090`.
- **Constat** : environ 1 650 lignes de JavaScript échappent à ESLint, Prettier et au typage. Les tests Python ne font que des recherches de sous-chaînes. C'est la principale source de risque pour toute remédiation de 3.1.3, 3.1.1 ou 3.2.4 dans les cartes.
- **Remediation** : renvoi aux audits 05 (DRY) et 10 (CI).

### [INFO] Profondeur d'imbrication — statut : **inchangé**

- **Localisation** : `document-parser/infra/local_chunker.py:24` (`_chunk_sync`, 7 niveaux) ; partout ailleurs, 4 au maximum.
- **Remediation** : extraire `_collect_bboxes(doc_item, doc)`.

---

## Ampleur de la mise en conformité, item par item

Gain par item : poids 1 = **+5,6 points**, poids 2 = **+11,1 points** (base 7/18, soit 39).

| Item | Poids → gain | Travail exact pour devenir conforme | Dont déprécié ou mort | Effort | Risque | Quick win ? |
|------|--------------|-------------------------------------|-----------------------|--------|--------|-------------|
| **3.2.4** | 1 → +5,6 | 3 fonctions (`fitToFrame`, `draw`, `updateRenderWindow`), 8 sites d'appel, 2 assertions (`test_mcp_apps.py:446-447`) | — | **S** (≈ 1 h) | Faible : garder la garde anti-boucle de `fitToFrame` | **Oui** |
| **3.1.1** | 1 → +5,6 | Voie (a) : la fiche 3.1.1 acte la convention « nom = valeur renvoyée » pour les fonctions pures, plus 2 renommages (`_anchor`, `_resolvable` : 3 appels, 0 test). Voie (b), stricte : ≈ 96 fonctions Python (28 modules) et ≈ 45 fonctions JS des cartes | — | (a) **S** ; (b) M | Faible : renommages mécaniques, ruff et pytest en filet ; JS non testé pour (b) | **Oui** par (a), qui demande une décision de gouvernance |
| **3.3.2** | 2 → +11,1 | `chunk_service.py` : sortir la projection d'arbre (≈ 160 l., mécanique) **et** le push (≈ 250 l., 3 routes, DI, ≈ 34 refs de tests). `sources_view.py` : DTO et mapping dans 2 modules (tests : `SOURCES_APP_HTML` seulement) | push = ingestion dépréciée | **M** | Faible (arbre, `sources_view`) à moyen (push) | **Partiellement** : arbre et `sources_view` sont des quick wins, mais l'item reste ❌ tant que le push reste dans `chunk_service.py` |
| **3.1.3** | 2 → +11,1 | ≈ 100 fragments, soit ~70-80 messages ; une dizaine de phrases à accords à paramétrer ; `Intl.NumberFormat` ; `lang` dynamique ; source de locale ; ≈ 5 assertions | — | A : S-M ; **B : M** ; C : L | Moyen : JS non exécuté par la CI, recette manuelle dans un hôte | Non : bloqué par la décision produit, techniquement M |
| **3.2.1** | 2 → +11,1 | 5 fonctions : `build_index` (S), `_finalize_analysis` (M), plus 3 dépréciées (`push_to_store`, `write_document`, `fetch_graph`) | 3 sur 5 | M + L, ou suppression de l'ingestion | Moyen ; tests Neo4j ignorés sans serveur | Non pour 0.7.4, sauf retrait anticipé de l'ingestion |
| **3.2.2** | 1 → +5,6 | 66 fonctions : 45 Python, 12 front (+3 internes aux stores) et 9 JS | 9 dépréciées + 3 mortes (Python), `renderGraph` (front) | L | Moyen | Non |
| **3.2.3** | 1 → +5,6 | 29 signatures | 9 dépréciées + 1 morte ; restent 19, dont 5 constructeurs DI | L | Moyen | Non |
| **3.3.1** | 1 → +5,6 | 42 fichiers, dont `i18n.ts` (1 474 l. de données : il faudrait le découper par namespace) | 7 dépréciés ou orphelins | L | Moyen | Non |

### Scénarios chiffrés

| Scénario | Items rendus conformes | Poids conformes | Score | Verdict |
|----------|------------------------|-----------------|-------|---------|
| État actuel | — | 7 / 18 | **39** | NO-GO |
| Quick win 1 | 3.2.4 | 8 / 18 | **44** | NO-GO |
| Quick wins 1 + 2 | 3.2.4, 3.1.1 par la voie (a) | 9 / 18 | **50** | NO-GO |
| Seuil GO CONDITIONNEL, sans toucher au choix produit | 3.2.4, 3.1.1 (a), 3.3.2 avec extraction du push | 11 / 18 | **61** | GO CONDITIONNEL |
| Avec les cartes bilingues (option B) | les précédents + 3.1.3 | 13 / 18 | **72** | GO CONDITIONNEL |
| Avec le retrait anticipé de l'ingestion et le découpage de `build_index` / `_finalize_analysis` | les précédents + 3.2.1 | 15 / 18 | **83** | GO |

Autre chemin vers 61 si l'extraction du push paraît trop risquée : 3.2.4, 3.1.1 (a) et 3.1.3 (option B). Les éléments de 3.2.2, 3.2.3 et 3.3.1 sont trop nombreux pour être des quick wins. Le retrait de l'ingestion en 0.8.0 en supprime environ un quart (12 fonctions longues, 10 signatures, 7 fichiers).

**Corrections hors barème, sans risque et à faire de toute façon :**
- les 3 chaînes anglaises de la carte de citation (`citation_app.html:680`, `:706`, `:825`) ;
- les 7 commentaires « main.py » ;
- la suppression des 4 composants Vue orphelins (−1 034 l., dont 1 fichier de plus de 300 lignes).

---

## Delta vs 0.7.3

**Score : 44 → 39 (−5).** Items conformes : 7/14 → 6/14.

**Code modifié depuis `02adc68`** : `infra/settings.py` (commentaire), `mcp_adapter/citation_app.html:2` (`lang`), `services/analysis_service.py:177-180` (`asyncio.to_thread`), le déplacement de `ConfigSource` vers `frontend/src/shared/types.ts`, et des libellés MCP dans `i18n.ts`. Aucun de ces changements ne touche un écart de l'audit 03, sauf `lang`.

| Écart 0.7.3 | Statut 0.7.4 | Détail |
|-------------|--------------|--------|
| [MAJ] 3.1.3 Cartes MCP en français | **Inchangé** | `lang="en"` corrigé en `lang="fr"` (`6711444`). Nouveau constat : 3 chaînes anglaises dans la carte française |
| [MAJ] 3.2.1 Orchestration multi-responsabilités | **Inchangé** | `_finalize_analysis` : ligne `:457` → `:460` |
| [MAJ] 3.3.2 `chunk_service.py` / `sources_view.py` | **Inchangé** | fichiers identiques |
| [MIN] 3.1.1 Nommage nom vs verbe | **Inchangé** | 96/199 (48 %), comme en 0.7.3 |
| [MIN] 3.2.2 Fonctions > 30 lignes | **Inchangé** | 45 Python, 12 front ; JS : 9 (3 non relevées en 0.7.3) |
| [MIN] 3.2.3 Fonctions > 4 paramètres | **Inchangé** | 29 |
| [MIN] 3.3.1 Fichiers > 300 lignes | **Inchangé** | 14 + 2 + 26 |
| [INFO] Constantes magiques | Inchangé | `McpConfigSection.vue:516` → `:517` |
| [INFO] Code mort | Inchangé, constat élargi | + 4 composants Vue orphelins (1 034 l.) |
| [INFO] Commentaires périmés | Inchangé, constat élargi | 7 renvois à `main.py` au lieu d'un |
| [INFO] Booléens de configuration | Inchangé | `ports.py:173` ; `chunk_repo.py:117` |
| [INFO] Variables d'une lettre | Inchangé | |
| [INFO] `get_*` à mémoïsation | Inchangé | + `driver_pool.get` (bootstrap de schéma documenté) |
| [INFO] JS inline hors lint | Inchangé | |
| [INFO] Imbrication | Inchangé | |

**Nouvel écart** : [MIN] 3.2.4, avec 3 flag arguments préexistants. **Aucun écart corrigé.**

---

## Points positifs

- **La remédiation 0.7.3 n'a pas dégradé la lisibilité.**
  - `asyncio.to_thread` s'accompagne d'un commentaire « pourquoi » exemplaire (`services/analysis_service.py:177-179`).
  - `ConfigSource` est déplacé dans `shared/types.ts` avec sa docstring (`frontend/src/shared/types.ts:1-5`).
  - Le commentaire de `infra/settings.py:90-96` décrit maintenant exactement ce que `MCP_ALLOWED_HOSTS` protège et ne protège pas.
- **Adaptateur MCP mince** : chaque outil de `mcp_adapter/server.py` fait 4 à 10 lignes, et le contrat (`wire.py`) est séparé de la traduction (`wire_mapping.py`).
- **Langue côté application** : aucun texte français en Python ni dans les `.vue`/`.ts` hors `i18n.ts`, à l'exception de l'autonyme « Français » du sélecteur de langue. Tous les composants passent par `t()`.
- **Imports (3.3.3)** : `ruff check` avec la configuration du projet (règle `I` active) donne « All checks passed ». Côté front, aucun import externe ne suit un import interne dans les 121 fichiers qui importent.
- **Aucun code commenté** laissé en place, ni en Python, ni en TS/Vue, ni dans le JS des cartes.
- **Pas de flag argument en Python** : aucun appel ne passe un booléen positionnel à une fonction du projet, et les booléens de configuration sont keyword-only.
- **Getters purs** : les 47 `get*` Python et les 6 du front sont des lectures, ou des caches documentés.
- **Nouveau code plat** : imbrication maximale de 4 hors `local_chunker.py`. `domain/` reste fait de fonctions pures et testables.

---

## Verdict partiel : NO-GO

Score **39/100** (< 60), **0 écart CRITICAL**, **3 écarts MAJOR** (au seuil, pas au-delà de 3).

Le NO-GO vient du barème, pas d'un risque fonctionnel ou de sécurité. Le code audité est celui de 0.7.3, à cinq retouches près. Aucun des 3 MAJ et des 4 MIN de 0.7.3 n'a été traité. La baisse de 44 à 39 vient d'un item que l'examen du TS/JS fait passer en non conforme (3.2.4).

Pour revenir en GO CONDITIONNEL (≥ 60) sans revenir sur le choix produit des cartes en français, voir les scénarios ci-dessus :
1. **3.2.4** : supprimer les 3 flag arguments. Effort S, risque faible. Score : 44.
2. **3.1.1** : le mainteneur acte la convention « nom = valeur renvoyée » pour les fonctions pures dans la fiche 3.1.1, puis on renomme `_anchor` et `_resolvable`. Effort S. Score : 50.
3. **3.3.2** : découper `chunk_service.py`. La projection d'arbre se sort mécaniquement ; le push part dans un service dédié. Il faut aussi scinder `sources_view.py`. Effort M. Score : **61**.

L'option B des cartes bilingues (+11) et le retrait anticipé de l'ingestion (+11 via 3.2.1, et une partie de 3.2.2, 3.2.3 et 3.3.1) sont les deux leviers suivants.
