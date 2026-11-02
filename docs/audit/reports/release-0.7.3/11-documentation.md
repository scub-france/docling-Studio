# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 5 / 9 |
| Score | 44 / 100 |
| Ecarts CRITICAL | 2 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 7 |

Ponderation : items conformes = 8 pts / 18 pts totaux → 44/100 (44,4).
Items non conformes : 11.1.1 (poids 3), 11.1.2 (poids 2), 11.1.3 (poids 3), 11.2.1 (poids 2).

> Contexte : la preparation de release (etape 2 « Freeze » de `docs/maintainers.md:21-24`) n'est pas encore faite. Elle vient apres l'audit (etape 1) dans la procedure du projet. Deux des quatre ecarts (11.1.1, 11.2.1) sont exactement ce que ce commit de freeze corrige. Les deux autres (11.1.2, 11.1.3) demandent du contenu de changelog en plus, a mettre dans le meme commit.

---

## Grille item par item

| # | Item | Poids | Conforme | Preuve |
|---|------|-------|----------|--------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | **NON** | `CHANGELOG.md:7` |
| 11.1.2 | Toutes les modifications significatives listees | 2 | **NON** | #359 et #323 absents |
| 11.1.3 | Breaking changes clairement identifies | 3 | **NON** | `CHANGELOG.md:19` (ASK_MODE) hors section BREAKING |
| 11.1.4 | Format Keep a Changelog | 1 | OUI | `CHANGELOG.md:5`, groupes Added/Changed/Deprecated `:9`, `:16`, `:26` |
| 11.2.1 | `frontend/package.json` a la version X.Y.Z | 2 | **NON** | `frontend/package.json:3` = `0.7.2` |
| 11.2.2 | Version conforme au SemVer | 2 | OUI | `0.7.2 → 0.7.3`, voir INFO SemVer |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | OUI | grep : 0 occurrence (back + front) |
| 11.3.2 | Pas de `console.log` de debug | 2 | OUI | 2 `console.warn` en `catch` seulement |
| 11.3.3 | Pas de `print()` de debug | 2 | OUI | 0 `print(` executable |

Calcul : (1 + 2 + 1 + 2 + 2) / 18 × 100 = 8 / 18 × 100 = **44,4 → 44/100**.

---

## Metriques collectees

| Metrique | Valeur |
|----------|--------|
| Merges first-parent depuis `caddf30` (freeze 0.7.2) | 12 (#323, #339, #341, #345, #346, #347, #353, #355, #357, #359, #362, #328) |
| Merges couverts par une entree du changelog | 10 / 12 (#357 est de la doc, couvert par l'entree #340) ; **absents : #359, #323** |
| Puces pour des issues reportees (#348, #349, #358, #350, #351, #319) | 0 (correct) |
| Affirmations du changelog verifiees dans le code | 16 / 16 exactes (voir ci-dessous) |
| Variables d'env nouvelles en 0.7.3 | 8 (`ASK_MODE`, 7 × `MCP_*`), absentes de `caddf30` |
| Documentees dans `.env.example` | 8 / 8 (`.env.example:88-90`, `:102-125`) |
| Documentees sur le site de doc | 8 / 8 (`docs/configuration.md:41`, `docs/mcp-server.md:40-46`) |
| Transmises par Docker Compose | `ASK_MODE`, `MCP_ENABLED`, `MCP_ALLOWED_HOSTS`, `MCP_STUDIO_BASE_URL` (`docker-compose.yml:190-195`) ; les autres demandent un override, ce que disent `.env.example:1-4` et `docs/configuration.md:6` |
| TODO / FIXME / HACK / XXX (back hors `.venv`, tests compris ; `frontend/src`) | 0 |
| `console.log` / `console.debug` dans `frontend/src` | 0 (`console.warn` : 2, tous deux en `catch`) |
| `print(` executable dans `document-parser` | 0 (4 occurrences en commentaire / docstring) |
| `mkdocs build --strict` | OK (seulement des messages INFO de pages hors nav) |

### Affirmations du changelog verifiees dans le code

| Affirmation (`CHANGELOG.md`) | Code | Resultat |
|------------------------------|------|----------|
| MCP active par defaut, desactive sur un Space HF (`:14`) | `document-parser/infra/settings.py:255-259` | exact |
| `MCP_ENABLED=false` ne monte rien (`:14`) | `document-parser/bootstrap/mcp_mount.py:90` | exact |
| `MCP_ALLOWED_HOSTS` par defaut = localhost (`:14`) | `document-parser/infra/settings.py:260-267` | exact |
| `MCP_CITATION_CARD` desactive par defaut (`:14`) | `document-parser/infra/settings.py:270` | exact |
| `MCP_MAX_ROUNDS`, 5 tours (`:14`) | `document-parser/infra/settings.py:273`, bornes 1-20 `document-parser/domain/mcp_config.py:29-30` | exact |
| Off depuis Settings → `/mcp` repond 503 (`:14`) | `document-parser/bootstrap/mcp_mount.py:152-166` | exact |
| `GET/PUT/DELETE /api/config/mcp` (`:14`) | `document-parser/api/config.py:75`, `:80`, `:97` | exact |
| `GET /api/mcp/server` (`:14`) | `document-parser/api/mcp.py:16-19` | exact |
| `defaults` dans `GET /api/config/mcp` (`:18`) | `document-parser/api/schemas.py:783` | exact |
| Outils `verify_citation`, `show_sources`, `show_citation`, prompt `chunkless_rag` (`:14`) | `mcp_adapter/server.py:194`, `sources_view.py:172`, `apps.py:164`, `prompts.py:62` | exact |
| Lien profond `/analyses/{id}?ref=…&page=N` (`:14`) | `document-parser/services/citation_service.py:292`, `frontend/src/app/router/routes.ts:46-47` | exact |
| nginx route `/mcp` (`:14`) | `nginx.conf.template:29`, `frontend/nginx.conf.template:29` | exact |
| `ASK_MODE` = `hidden` sauf `visible`, `askMode` dans `/api/health` (`:19`) | `document-parser/infra/settings.py:235`, `document-parser/main.py:160` | exact |
| `GET /api/analyses/summaries`, toutes les 3 s (`:13`) | `document-parser/api/analyses.py:104`, `frontend/src/features/analysis/store.ts:34` | exact |
| `GET /api/documents/{id}/pages` (`:21`) | `document-parser/api/documents.py:204` | exact |
| `docling-core` ≥ 2.65.2, batchs fusionnes (`:23`) ; Docling Serve `v1.37.0` dans les deux compose (`:24`) | `document-parser/pyproject.toml:9`, `infra/local_converter.py:157-179` ; `docker-compose.yml:112`, `docker-compose.dev.yml:104` | exact |

---

## Ecarts constates

### [CRIT] La section `[Unreleased]` n'a pas ete renommee en `[0.7.3] - YYYY-MM-DD`

- **Localisation** : `CHANGELOG.md:7`
- **Constat** : le changelog commence toujours par `## [Unreleased]` (`CHANGELOG.md:7`). Il n'y a pas de section `## [0.7.3]`. Le contenu de la release est sous `[Unreleased]` (`CHANGELOG.md:9-28` : Added, Changed, Deprecated), mais la section n'est pas figee. La note de GitHub Release, que l'on extrait avec `awk '/^## \[0.7.3\]/…'` (`docs/maintainers.md:40`), serait donc vide. C'est l'etape standard de preparation de release, pas encore faite : la procedure du projet place ce freeze apres l'audit (`docs/maintainers.md:21-24`). On avait la meme situation au premier audit de 0.7.0, corrigee avant le tag.
- **Regle violee** : item 11.1.1, poids 3.
- **Remediation** : dans un seul commit `chore(release): freeze [0.7.3]` sur `release/0.7.3` (`docs/maintainers.md:22`) :
  1. Remplacer `CHANGELOG.md:7` `## [Unreleased]` par `## [0.7.3] - <date du tag>`.
  2. Recreer au-dessus une section `## [Unreleased]` vide pour le cycle suivant, comme au freeze 0.7.0.
  3. Dans le meme commit, appliquer le bump de `frontend/package.json` (MAJ ci-dessous) et les ajouts de changelog des ecarts 11.1.2 et 11.1.3.

### [CRIT] Changements a rupture non identifies : `ASK_MODE` cache Ask par defaut

- **Localisation** : `CHANGELOG.md:19` (entree rangee dans `### Changed`, `CHANGELOG.md:16`) ; il n'y a pas de section `### BREAKING CHANGES` sous `[Unreleased]` (`CHANGELOG.md:7-28`).
- **Constat** : `ASK_MODE` vaut `hidden` par defaut (`document-parser/infra/settings.py:235`). Quand Ask est cache, l'onglet Ask disparait de la vue Parse (`frontend/src/features/feature-flags/store.ts:78`). La section **Settings › Reasoning** disparait aussi (`frontend/src/features/settings/ui/SettingsPanel.vue:94`, `v-if="askShown"`). En 0.7.2, cette section s'affichait toujours (`git diff 836e585^ 836e585`). Un operateur 0.7.2 qui avait active le raisonnement par l'env ou par Settings perd donc, a la mise a jour, l'onglet Ask **et** l'ecran ou on l'active. L'interface ne donne aucun indice : il faut redemarrer avec `ASK_MODE=visible`. L'entree du changelog decrit bien le changement et la facon de revenir en arriere (« Set `ASK_MODE=visible` to keep Ask as before »). Mais elle n'est pas classee comme rupture. Or le projet classe ce cas comme rupture : en 0.6.1, des flags de surface desactives par defaut figurent sous `### BREAKING CHANGES` (`CHANGELOG.md:146`, « Operators relying on the legacy `/studio` page … must explicitly set them to `true` »). Le gate 0.6.2 a aussi donne un CRIT 11.1.3 pour une fonctionnalite passee en opt-in et decrite seulement sous « Changed » (reasoning `WITH_REASONING`, corrige ensuite en `CHANGELOG.md:96-99`). Deuxieme candidat, a arbitrer : avec Docling Serve v1.37.0, le Markdown et le HTML d'une analyse distante contiennent un placeholder au lieu d'une image base64 (`CHANGELOG.md:24`). La sortie d'export change pour les utilisateurs du mode `remote`.
- **Regle violee** : item 11.1.3, poids 3. Selon les conventions du projet (`CHANGELOG.md:96`, `:144`), un changement qui oblige l'operateur a agir pour garder le comportement precedent va dans `### BREAKING CHANGES`.
- **Remediation** : ajouter sous la future section `## [0.7.3]` :
  ```markdown
  ### BREAKING CHANGES

  - **Ask hidden by default** (`ASK_MODE`): after the upgrade, the Parse view has no Ask tab and Settings has no Reasoning section, even where reasoning was turned on in 0.7.2. Set `ASK_MODE=visible` (and pass it through compose) to keep Ask.
  - **Remote Markdown/HTML exports** (Docling Serve v1.37.0): picture images now come as a placeholder instead of base64. The Docling JSON is unchanged.
  ```
  Si le mainteneur decide que le point Docling Serve n'est pas une rupture, la premiere puce suffit a lever l'ecart.

### [MAJ] Changelog incomplet : import d'analyses Docling (#359) et page de detail d'analyse (#323) absents

- **Localisation** : `CHANGELOG.md:9-28` (section `[Unreleased]`). Aucune occurrence de `359`, `323` ni de l'import d'analyse (`grep -n "359\|#323\|Import" CHANGELOG.md`).
- **Constat** : deux merges first-parent de la release, visibles par l'utilisateur, n'ont pas d'entree :
  1. **#359 « feat: import Docling analyses »** (`ec3eb00`, PR mergee le 2026-10-15). Elle apporte une nouvelle route `POST /api/analyses/import` (`document-parser/api/analyses.py:73-87`, corps `documentId` + `DoclingDocument` serialise, `document-parser/api/schemas.py:272-276`). Elle ajoute aussi un bouton « Import analysis » et un import combine PDF + JSON Docling (`frontend/src/features/analysis/ui/AnalysisImportButton.vue`, `frontend/src/features/document/ui/DocumentActionsMenu.vue`, libelles `frontend/src/shared/i18n.ts:981-985`), ainsi qu'un `.pre-commit-config.yaml`. Le guide utilisateur n'en parle pas non plus (`docs/user-guide.md:29`, `:34-42` decrivent seulement l'import de PDF) : la reecriture #340 (2026-09-28) a precede ce merge.
  2. **#323 « align frontend library naming and dev route visibility »** (`d67b404`). Elle corrige un bogue : depuis la page de detail d'une analyse ancienne, le telechargement Markdown/JSON exportait la derniere analyse et non celle affichee (`56df3b4`). L'export accepte maintenant `analysisId` et repond 404 si l'id est inconnu (`document-parser/api/documents.py:133-146`). La PR ajoute aussi un lien « Open document » (`frontend/src/pages/AnalysisDetailPage.vue:21`), retire « New analysis » de la page de detail, renomme la page en « Analysis library » (`frontend/src/pages/AnalysisLibraryPage.vue`) et ajoute un badge de route en mode dev (`frontend/src/app/App.vue:22`).
- **Regle violee** : item 11.1.2, poids 2.
- **Remediation** : ajouter au changelog 0.7.3, par exemple :
  - `### Added` — **Import a Docling analysis** (#359) : importer une analyse terminee depuis un JSON `DoclingDocument`, seule ou avec son PDF ; nouvelle route `POST /api/analyses/import`.
  - `### Fixed` — **Saved analysis downloads what it shows** (#323) : `GET /api/documents/{id}/export` prend `analysisId` en option (404 si inconnu). La page de detail devient en lecture seule, avec un lien « Open document ». La page « Analyses » devient « Analysis library ».
  - Optionnel : une ligne dans `docs/user-guide.md` sur l'import d'analyse, et une mention de `pre-commit` dans `CONTRIBUTING.md`.

### [MAJ] `frontend/package.json` reste en 0.7.2 au lieu de 0.7.3

- **Localisation** : `frontend/package.json:3`
- **Constat** : `"version": "0.7.2"`. Les releases precedentes bumpent ce champ au freeze (`caddf30` 0.7.2, `e95680a` 0.7.1, `f5a7733` 0.7.0). Ce n'est pas encore fait pour 0.7.3. Cette valeur sert de repli pour la version affichee quand `VITE_APP_VERSION` n'est pas fourni (`frontend/vite.config.js:19`). L'image publiee recoit bien `APP_VERSION` depuis le tag (`.github/workflows/release.yml:71`, `Dockerfile:13-19`), mais une construction depuis les sources sans cet argument afficherait `0.7.2`. C'est l'etape standard de preparation de release, decrite en `docs/maintainers.md:24`.
- **Regle violee** : item 11.2.1, poids 2.
- **Remediation** : passer `frontend/package.json:3` a `"version": "0.7.3"` dans le commit de freeze. Optionnel : `npm install --package-lock-only` dans `frontend/` pour aligner le lockfile (voir INFO versions).

### [INFO] `.env.example` contredit #344 sur `BATCH_PAGE_SIZE`

- **Localisation** : `.env.example:11-12`
- **Constat** : le fichier dit encore « Batching drops the document structure: no tree and no Ask on PDFs longer than this. Keep 0 unless memory is short. » Ces lignes viennent de `ea47a3e9` (2026-09-25), avant le merge de #344 (`a422773`, 2026-09-28). Or #344 fusionne justement les documents des batchs (`document-parser/infra/local_converter.py:157-179`), et le changelog l'annonce (`CHANGELOG.md:23`). `docs/configuration.md:20` est a jour. Le commentaire decourage a tort un reglage qui vaut `10` par defaut en compose (`docker-compose.yml:173`).
- **Regle violee** : hors checklist ponderee (exactitude de la documentation d'environnement).
- **Remediation** : reprendre la formulation de `docs/configuration.md:20` (borne la memoire, affiche la progression, un tableau a cheval sur deux batchs sort en deux tableaux).

### [INFO] Statut des design docs non tenu pour les issues livrees

- **Localisation** : `docs/design/363-mcp-chunkless-rag-simplification.md:7-8`, `docs/design/364-mcp-admin-panel-section.md:7-8`, `docs/design/329-mcp-investigation-journal-navigation-tree.md:33-34`
- **Constat** : le cycle de vie defini par le gabarit est Draft → In review → Accepted → Implemented, ou Superseded (`docs/design/TEMPLATE.md:9`). Or le doc 363 est `Accepted` et le doc 364 `In review`, alors que les deux sont livres dans 0.7.3, et tous deux visent le jalon `0.8.0`. Le doc 329 est `Accepted (amended after build)`, mais le journal d'investigation a ete retire par #363 : aucune occurrence de `open_investigation`, `plan_steps` ou `record_attempt` dans `document-parser`, et le doc 363 dit lui-meme qu'il « reverses #329 » (`:11`). Ces docs ne sont plus publies sur le site (`mkdocs.yml:51-53`), l'impact se limite aux mainteneurs.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : passer 363 et 364 a `Implemented`, avec le jalon `0.7.3`, et 329 a `Superseded by #363`.

### [INFO] Jalons GitHub incoherents avec le contenu livre

- **Localisation** : GitHub, jalons `0.7.3` et `0.8.0 — Production ready` (`gh issue list --milestone 0.7.3`, `gh issue view`)
- **Constat** : le jalon `0.7.3` liste encore #348, #349 et #358 comme ouverts. Ils sont reportes par decision du mainteneur, et leur deplacement vers 0.8.0 est prevu. Le changelog ne contient aucune puce pour eux (correct). A l'inverse, le serveur MCP livre dans 0.7.3 a ses issues sous `0.8.0` : #327 (OPEN), #363 (OPEN), #364 (CLOSED). #329 est OPEN alors qu'il est remplace par #363. #361 est OPEN : seule la partie Docling Serve v1.37.0 est livree, et l'entree `CHANGELOG.md:24` le dit correctement. La partie docling 2.140.0 ne l'est pas.
- **Regle violee** : hors checklist ponderee (suivi du perimetre de la release).
- **Remediation** : deplacer #348, #349 et #358 vers 0.8.0. Rattacher #327, #363 et #364 a 0.7.3 et fermer #327 et #363 au merge. Fermer #329 comme remplace. Garder #361 ouvert pour la partie docling.

### [INFO] Versions secondaires non alignees

- **Localisation** : `frontend/package-lock.json:3` et `:9` (`0.6.2`), `document-parser/pyproject.toml:3` et `embedding-service/pyproject.toml:3` (`0.0.0`), `e2e/api/pom.xml:10` et `e2e/ui/pom.xml:10` (`0.3.1`)
- **Constat** : le lockfile frontend est reste a 0.6.2 depuis `f9c7b40`, et les freezes 0.7.0, 0.7.1 et 0.7.2 n'y ont pas touche. Le `version = "0.0.0"` du backend est un placeholder depuis la migration uv (`7a7b159`, 2026-05-21), jamais modifie depuis. A l'execution, la version vient de `APP_VERSION` (`document-parser/infra/settings.py:203`), que le build de release injecte depuis le tag (`.github/workflows/release.yml:71`, `Dockerfile:24-25`) et que `/api/health` expose. Ce point etait deja en INFO en 0.6.2. Pas d'impact sur la version vue par les utilisateurs de l'image publiee.
- **Regle violee** : hors checklist ponderee (11.2.1 ne vise que `frontend/package.json`).
- **Remediation** : aligner le lockfile au freeze (`npm install --package-lock-only`). Documenter dans `docs/maintainers.md` que `pyproject.toml` garde volontairement `0.0.0`.

### [INFO] SemVer : un patch qui ajoute de l'API publique et une depreciation

- **Localisation** : `CHANGELOG.md:9-28`
- **Constat** : 0.7.3 ajoute plusieurs routes publiques (`/mcp`, `GET/PUT/DELETE /api/config/mcp`, `GET /api/mcp/server`, `GET /api/analyses/summaries`, `POST /api/analyses/import`, `GET /api/documents/{id}/pages`). Elle declare aussi une depreciation (ingestion, `CHANGELOG.md:26-28`). Au sens strict de SemVer 2.0.0 §7, cela demande un bump mineur. L'item 11.2.2 reste conforme pour trois raisons : la clause §4 (en 0.y.z, l'API publique n'est pas consideree stable), le precedent du projet (0.6.1 et 0.6.2 etaient des patchs avec des ajouts, juges conformes par les gates 0.6.x) et la decision du mainteneur de livrer en 0.7.3, 0.8.0 etant reserve au retrait de l'ingestion.
- **Regle violee** : item 11.2.2 conforme ; simple note.
- **Remediation** : aucune pour 0.7.3. Pour 0.8.0, envisager une regle ecrite dans `docs/maintainers.md` (patch = correctifs ; mineur = nouvelle API ou depreciation).

### [INFO] Pages Architecture et Configuration muettes sur le serveur MCP

- **Localisation** : `docs/architecture.md:80-87`, `docs/configuration.md:3`, `.env.example:5`
- **Constat** : `docs/architecture.md` ne mentionne pas le MCP. Le tableau des prefixes ne contient ni `/mcp` ni `/api/mcp`. Il decrit `/api/config` comme « The reasoning settings edited in Settings » (`:86`), alors qu'il porte maintenant `/api/config/mcp`, et `/api/analyses` comme « start, read, delete » (`:83`), sans l'import ni les summaries. Le schema du backend ne montre pas `mcp_adapter/`. De son cote, `docs/configuration.md` ne liste ni ne lie les 7 variables `MCP_*`. Elles sont documentees, et bien, dans `docs/mcp-server.md:40-46`. Mais `.env.example:5` presente `docs/configuration.md` comme « Full reference ».
- **Regle violee** : hors checklist ponderee.
- **Remediation** : ajouter `/mcp`, `/api/mcp` et `/api/config/mcp` au tableau d'architecture, avec une ligne sur `mcp_adapter/`. Ajouter dans `docs/configuration.md` une section « MCP server » qui renvoie vers `mcp-server.md#turn-it-on-or-off`.

### [INFO] Le changelog ne nomme que 4 des 7 variables `MCP_*` nouvelles

- **Localisation** : `CHANGELOG.md:14`
- **Constat** : l'entree MCP nomme `MCP_ENABLED`, `MCP_ALLOWED_HOSTS` et `MCP_CITATION_CARD`, puis « new variable `MCP_MAX_ROUNDS` ». Cette formulation laisse croire a une seule nouvelle variable. En realite, les sept `MCP_*` sont nouvelles en 0.7.3 (aucune n'existe a `caddf30`). `MCP_APPS_ENABLED`, `MCP_MAX_READ_TOKENS` et `MCP_STUDIO_BASE_URL` ne sont evoquees qu'en prose (« the read ceiling and the deep-link base »). Leur renvoi vers `docs/mcp-server.md` est present.
- **Regle violee** : hors checklist ponderee (exactitude du changelog).
- **Remediation** : remplacer « new variable `MCP_MAX_ROUNDS` » par « new variables `MCP_ENABLED`, `MCP_ALLOWED_HOSTS`, `MCP_STUDIO_BASE_URL`, `MCP_MAX_READ_TOKENS`, `MCP_MAX_ROUNDS`, `MCP_APPS_ENABLED`, `MCP_CITATION_CARD` ».

---

## Delta vs 0.7.0

| Item | 0.7.0 initial | 0.7.0 re-audit (base) | 0.7.3 | Evolution |
|------|---------------|-----------------------|-------|-----------|
| 11.1.1 Changelog fige | CRIT | OK | **CRIT** | freeze pas encore fait (meme etat qu'au 1er audit 0.7.0) |
| 11.1.2 Changements listes | OK | OK | **MAJ** | regression : #359 et #323 absents |
| 11.1.3 Breaking identifies | OK (INFO) | OK (INFO) | **CRIT** | le point de vigilance 0.7.0 se concretise : ASK_MODE hors BREAKING |
| 11.1.4 Keep a Changelog | OK | OK | OK | = |
| 11.2.1 Version front | MAJ | OK | **MAJ** | bump pas encore fait (meme etat qu'au 1er audit 0.7.0) |
| 11.2.2 SemVer | OK | OK | OK | = (INFO ajoutee) |
| 11.3.1 TODO/FIXME | OK | OK | OK | = (0 occurrence) |
| 11.3.2 console.log | OK | OK | OK | = |
| 11.3.3 print() | OK | OK | OK | = |
| **Score** | 72 | **100** | **44** | **−56 pts vs re-audit** (−28 vs l'audit 0.7.0 initial, au meme stade avant freeze) |

INFO du re-audit 0.7.0 :
- Note README « pagination ships in v0.6 » : **resolue**. Le README a ete reecrit par #340 (59 lignes, plus de mention de version perimee).
- Arbitrage `BREAKING CHANGES` : **pas fait, et escalade en CRIT** pour 0.7.3 (ASK_MODE).

Projection : avec le commit de freeze seul (11.1.1 + 11.2.1), le score passe a 13/18 = **72**, mais un CRIT resterait. Avec les ajouts de changelog des ecarts 11.1.2 et 11.1.3 dans le meme commit, il passe a 18/18 = **100**.

---

## Points positifs

- **Contenu du changelog exact** : les 16 affirmations verifiees (variables, valeurs par defaut, routes, outils MCP, 503, liens profonds, nginx, docling-core, version de Docling Serve) correspondent au code. Aucune puce pour une issue reportee (#348, #349, #358, #350, #351, #319).
- **Section `### Deprecated` correcte** pour l'ingestion (`CHANGELOG.md:26-28`), avec la version de retrait (0.8.0) et le perimetre exact. Elle est reprise dans `.env.example:55-56` et `docs/configuration.md:63-84`.
- **Variables d'environnement documentees partout** : les 8 nouvelles variables sont dans `.env.example` avec leurs valeurs par defaut exactes, sur le site (`docs/configuration.md:35-46`, `docs/mcp-server.md:40-46`) et dans les deux fichiers compose pour celles qui sont transmises. `.env.example:1-4` explique quelles variables compose transmet.
- **Documentation reecrite et coherente** (#340) : `ASK_MODE` est explique la ou on le cherche (`docs/getting-started.md:88`, `:102`, `docs/troubleshooting.md:7`, `docs/user-guide.md:32`, `docs/architecture.md:129`). Le MCP a sa page complete (`docs/mcp-server.md`, 339 lignes : activation, Settings, clients, outils, securite, limites), liee depuis le README (`README.md:31`, `:40`). `mkdocs build --strict` passe.
- **Code propre** : 0 TODO/FIXME/HACK/XXX dans le backend (tests compris) et le frontend. Pas de `console.log` ni `console.debug` : les deux `console.warn` (`frontend/src/features/analysis/store.ts:117`, `:176`) sont dans des `catch`, ce que la convention autorise (`frontend/CLAUDE.md`). Pas de `print()` executable : les 4 occurrences sont des commentaires ou docstrings (`document-parser/mcp_stdio.py:25`, `document-parser/infra/settings.py:45`, `document-parser/infra/secrets/fernet_box.py:46`, `:133`).
- **Format Keep a Changelog** : en-tete Keep a Changelog + SemVer (`CHANGELOG.md:5`), groupes standards, dates ISO, ordre decroissant.

---

## Verdict partiel : NO-GO

Il reste deux ecarts `[CRIT]` : 11.1.1 (changelog non fige) et 11.1.3 (rupture `ASK_MODE` hors `### BREAKING CHANGES`). La regle absolue du master s'applique : **NO-GO**, quel que soit le score (44/100). Les quatre ecarts ponderes se corrigent dans le seul commit `chore(release): freeze [0.7.3]` de `docs/maintainers.md:22`, sans toucher au code :

1. renommer `CHANGELOG.md:7` en `## [0.7.3] - <date>` et recreer un `[Unreleased]` vide (CRIT 11.1.1) ;
2. ajouter `### BREAKING CHANGES` avec la puce `ASK_MODE`, et la puce export distant si elle est retenue (CRIT 11.1.3) ;
3. ajouter les entrees #359 (Added) et #323 (Fixed) (MAJ 11.1.2) ;
4. `frontend/package.json:3` → `"version": "0.7.3"` (MAJ 11.2.1).

Apres ces corrections, un re-audit attendu a 100/100 donnerait GO. Les 7 INFO peuvent attendre le cycle suivant. Le commentaire `.env.example:11-12` est trompeur et merite d'etre corrige dans le meme commit.
