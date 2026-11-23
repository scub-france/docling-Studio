# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Branche** : `fix/0.7.4-editor-followups` @ `a6fb539` = `release/0.7.4` @ `f7fc791` (PR #401 rendu PDF.js, cache des apercus, resumes d'analyses ; PR #402 correctifs editeur) + 13 commits locaux #391-#400 + merge. Arbre de travail lu tel quel.
**Baseline** : `docs/audit/reports/release-0.7.4/11-documentation.md` (2026-11-13, `eade7fa`, 61/100, 1 CRIT, 2 MAJ)
**Contexte** : la release n'est pas figee. `[Unreleased]` et la version `0.7.3` du frontend sont attendus jusqu'au commit de freeze (`docs/maintainers.md:22-24`). La fiche est appliquee a la lettre, avec la meme lecture que la baseline ; deux scores sont donnes.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 9 |
| Score | 72 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 11 |

Ponderation : poids total 18. Non conformes : 11.1.1 (3), 11.2.1 (2) = 5. `score = 13 / 18 * 100 = 72,2` -> **72**.

### Score au freeze

| Scenario | Ecarts restants | Score | Verdict |
|----------|-----------------|-------|---------|
| Aujourd'hui (pre-freeze) | 11.1.1 CRIT, 11.2.1 MAJ | 72 | NO-GO (CRIT) |
| Apres le commit de freeze (`## [0.7.4] - YYYY-MM-DD`, `frontend/package.json` + lockfile en `0.7.4`) | aucun | 100 | GO |

Les deux ecarts restants relevent uniquement du commit de freeze. Les INFO ci-dessous ne changent pas le score, mais plusieurs touchent le texte qui deviendra la note de la GitHub Release : a corriger avant le freeze.

### Detail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | **Non** (pre-freeze) | `CHANGELOG.md:7` `## [Unreleased]` |
| 11.1.2 | Modifications significatives listees | 2 | Oui | Editeur (`CHANGELOG.md:11`), rendu PDF (`:17`), resumes (`:18`), export par defaut (`:21`), #391-#398 (`:26-35`). Manques mineurs en INFO |
| 11.1.3 | Breaking changes identifies | 3 | Oui | Aucune rupture ; le seul changement de comportement d'API (export par defaut) est annonce `CHANGELOG.md:21` |
| 11.1.4 | Format Keep a Changelog | 1 | Oui | `CHANGELOG.md:5` ; une seule section `### Added` `:9`, `### Changed` `:15`, `### Fixed` `:24`. Classement de `Fixed` contestable (INFO) |
| 11.2.1 | `frontend/package.json` en X.Y.Z | 2 | **Non** (pre-freeze) | `frontend/package.json:3` et `frontend/package-lock.json:3`, `:9` = `0.7.3` |
| 11.2.2 | Version SemVer | 2 | Oui | `0.7.3 -> 0.7.4`, conforme SemVer §4 en 0.y.z (INFO) |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | Oui | 0 `TODO|FIXME|HACK|XXX` dans `document-parser` (hors `.venv`) et `frontend/src` |
| 11.3.2 | Pas de `console.log` de debug | 2 | Oui | 0 `console.log`/`console.debug` ; 2 `console.warn` en `catch` : `frontend/src/features/analysis/store.ts:124`, `:183` |
| 11.3.3 | Pas de `print()` de debug | 2 | Oui | 0 `print(` executable hors `tests/` (4 occurrences en commentaire/docstring : `mcp_stdio.py:25`, `infra/settings.py:45`, `infra/secrets/fernet_box.py:46`, `:133`) |

### Detail 11.1.3 — candidats examines

| Changement | Effet pour un client existant | Rupture ? |
|------------|-------------------------------|-----------|
| Export md/json sans `analysisId` : analyse active au lieu de la plus recente (`document-parser/api/documents.py:140-144`) | Meme resultat dans le cas courant ; annonce `CHANGELOG.md:21` | Non (annonce) |
| `GET /api/documents/{id}/preview` : parametre `format` (`png` par defaut, `webp`), cache memoire, `Cache-Control: private, max-age=86400, immutable` (`api/documents.py:179`, `:187`) | Defaut inchange (`png`) ; codes 404/400 conserves (`:189-192`) | Non |
| Viewer PDF.js : le navigateur lit `GET /api/documents/{id}/export?format=pdf` par plages (`frontend/src/features/document/ui/usePdfDocument.ts:25-29`) | Repli sur les apercus serveur si PDF.js echoue (`PdfPagePreview.vue:13-14`) | Non |
| Schema 0.7.4 (#391, `document-parser/persistence/database.py:315`) | Base 0.7.3 mise a niveau au boot | Non |
| Table `chunk_edits` plus ecrite | Annonce `CHANGELOG.md:20` | Non |

---

## Ecarts constates

### [CRIT] La section `[Unreleased]` n'est pas figee (attendu pre-freeze)

- **Localisation** : `CHANGELOG.md:7`
- **Constat** : tout le contenu 0.7.4 est sous `## [Unreleased]`. La commande d'extraction des notes (`docs/maintainers.md:39`) renverrait une note vide pour `[0.7.4]`. Normal tant que le freeze n'est pas fait.
- **Regle violee** : 11.1.1 (poids 3).
- **Remediation** : commit `chore(release): freeze [0.7.4]` : `## [0.7.4] - <date>`, puis un `## [Unreleased]` vide au-dessus. Faire d'abord les retouches de texte des INFO 1 a 3. Effort S.

### [MAJ] `frontend/package.json` encore en 0.7.3 (attendu pre-freeze)

- **Localisation** : `frontend/package.json:3` ; `frontend/package-lock.json:3`, `:9`
- **Constat** : `"version": "0.7.3"`. La PR #401 a modifie ces deux fichiers (ajout de `pdfjs-dist`, `frontend/package.json:26`) sans toucher la version, ce qui est correct.
- **Regle violee** : 11.2.1 (poids 2).
- **Remediation** : `0.7.4` dans `package.json` et le lockfile, dans le commit de freeze. Effort S.

### [INFO] 1. `### Fixed` ne contient aucune correction d'un defaut publie

- **Localisation** : `CHANGELOG.md:24-35`
- **Constat** : 10 puces. Aucune ne corrige un comportement de 0.7.3 :
  - `:26` (#391) est la migration du schema introduit par 0.7.4 : une note d'upgrade, pas un correctif ;
  - `:27`, `:29`, `:30`, `:32-35` (#392, #394, #396, #395 x4) corrigent l'editeur, jamais publie ;
  - `:28` (#393) porte sur la provenance des chunks, ajoutee en 0.7.4 ;
  - `:31` (#398) est une optimisation (une requete SQL au lieu de N, ouverture du PDF par chemin), donc `Changed`.
  La baseline comptait 3 puces de ce type ; il y en a 10. Un utilisateur 0.7.3 lira dix « corrections » d'un editeur qu'il n'a jamais eu. En lecture stricte, 11.1.4 deviendrait MIN (-6 points) ; il reste conforme ici pour garder la lecture de la baseline.
- **Remediation** : supprimer `### Fixed`. Fondre #392-#396 dans la puce `:11` (« merges keep reading order and only same-type elements; work runs off the event loop; a missing document or analysis answers 404 »). Deplacer `:26` sous `### Changed` (texte propose en fin de rapport) et `:31` sous `### Changed`. Effort S.

### [INFO] 2. Entrees #401 sans numero, et sans les details d'API et d'exploitation

- **Localisation** : `CHANGELOG.md:17-18` ; `document-parser/api/documents.py:179`, `:187` ; `document-parser/infra/preview_cache.py:16` ; `nginx.conf.template:4-8`
- **Constat** :
  - `:17` et `:18` n'ont ni issue ni PR (#401), alors que toutes les autres puces de la release en ont, sauf `:12-13`, `:19-21`.
  - Non annonces : le parametre `format=webp` de `GET /api/documents/{id}/preview` (le frontend l'utilise : `frontend/src/features/document/api.ts:50`), le cache memoire des apercus (64 Mo par processus, non configurable, `preview_cache.py:16`), l'en-tete `Cache-Control: private, max-age=86400, immutable`, la compression gzip des reponses JSON dans nginx (`nginx.conf.template:4-8`), la nouvelle dependance `pdfjs-dist` (`frontend/package.json:26`).
  - `:17` (« Faster PDF viewing ») et `:31` (#398, « page previews open the PDF by path ») sont **tous deux vrais** au commit audite : les apercus serveur restent le repli (`frontend/src/features/document/ui/PdfPagePreview.vue:13-14`) et le service les rend par chemin (`document-parser/services/preview_service.py:41-48`, `services/document_service.py:170`). Pas de contradiction, mais deux puces dans deux sections pour le meme sujet.
- **Remediation** : une seule puce « Faster PDF viewing (#398, #401) » sous `### Changed` (texte propose en fin de rapport). Effort S.

### [INFO] 3. Puces redondantes ou sans numero autour de l'editeur

- **Localisation** : `CHANGELOG.md:12-13`, `:19-21`, `:32-35`
- **Constat** : `:12` (historique) et `:13` (ordre de lecture) sont des aspects de la fonctionnalite annoncee `:11`, sans numero. `:19-20` decrivent la persistance interne d'un editeur nouveau. `:32-35` sont quatre puces pour #395, issues de PR #402 ; le travail #395 de la branche locale (`9d3510d`, `c6b7e6d`) n'a pas ajoute de puce, donc pas de doublon textuel apres le merge, mais une seule issue occupe quatre lignes. Le champ `analysisEditorEnabled` de `/api/health` (`document-parser/main.py:169`) n'est pas cite.
- **Remediation** : fusionner `:12-13` et `:32-35` dans `:11` ; garder de `:19-20` la seule information utile a un utilisateur 0.7.3 (la table `chunk_edits` n'est plus ecrite ; l'historique des versions garde les snapshots de chunks). Effort S.

### [INFO] 4. Rien dans la documentation publiee sur le nouveau rendu PDF

- **Localisation** : `docs/design/pdf-loading-performance.md` (exclu du site, `mkdocs.yml:52-57`) ; aucune occurrence de `PDF.js`, `pdfjs`, `range`, `webp`, `gzip` ou « preview cache » dans `docs/*.md`, `README.md`, `CONTRIBUTING.md`
- **Constat** : le viewer lit le PDF par plages HTTP (`usePdfDocument.ts:25-29`, blocs de 256 Kio). Le backend sait repondre aux plages (Starlette 1.0, `FileResponse` gere `Range` et `Accept-Ranges`), et le nginx fourni transmet l'en-tete sans configuration (`nginx.conf.template:23-30`) : aucune exigence nginx nouvelle pour le deploiement fourni. Mais un exploitant derriere un autre proxy n'est pas prevenu qu'un proxy qui retire `Range` ou met la reponse en tampon fait telecharger tout le PDF, ni que le cache d'apercus prend jusqu'a 64 Mo de RAM par processus. Le design doc n'a ni statut, ni issue, ni jalon, et decrit des phases 2 et 3 non livrees.
- **Remediation** : deux phrases dans `docs/troubleshooting.md` ou `docs/configuration.md` (proxy et `Range`, memoire du cache) ; une ligne `Status: phase 1 + scrolling follow-up shipped in 0.7.4 (#401); phases 2-3 not started` en tete du design doc. Effort S.

### [INFO] 5. Note d'upgrade 0.7.3 -> 0.7.4 seulement dans le changelog

- **Localisation** : `CHANGELOG.md:26` ; `document-parser/persistence/database.py:276`, `:288-315` ; aucune occurrence de « upgrade » ou « backup » dans `docs/*.md`
- **Constat** : la migration est automatique et idempotente au boot, ce que dit le changelog. Aucune page ne conseille de sauvegarder `DB_PATH` avant la mise a jour ni ne dit ce que donne un retour en 0.7.3 sur une base migree.
- **Remediation** : une ligne « Upgrading » dans `docs/maintainers.md` ou `docs/getting-started.md` : sauvegarder la base, la migration est faite au premier demarrage. Effort S.

### [INFO] 6. `docs/configuration.md` : deux sections d'interrupteurs, et « 0.7.3 » dans le texte courant

- **Localisation** : `docs/configuration.md:22-26` (« Feature flags ») et `:54-59` (« Feature switches ») ; `docs/configuration.md:92` et `docs/user-guide.md:125` (« In 0.7.3 », « in 0.7.3 »)
- **Constat** : inchange depuis la baseline pour les deux sections. Les mentions « 0.7.3 » restent vraies en 0.7.4 mais dateront la doc publiee. Variables : la seule nouvelle variable depuis `v0.7.3`, `ANALYSIS_EDITOR_ENABLED` (`document-parser/infra/settings.py`, diff `v0.7.3..a6fb539`), est documentee (`docs/configuration.md:26`, `.env.example`, `docker-compose.yml`). Les variables citees par la doc et absentes du backend (`NGINX_MAX_BODY_SIZE`, `CONVERSION_MODE`, `WITH_REASONING`, `BAKE_MODELS`, `EMBEDDING_MODEL`) existent bien ailleurs (nginx, build, service d'embedding). Les `MCP_*` sont dans `docs/mcp-server.md`. Non documentees, anterieures a 0.7.4 et couvertes par le renvoi a `settings.py` (`docs/configuration.md:3`) : `INSPECT_MODE_ENABLED`, `LINKED_MODE_ENABLED`, `DEFAULT_EMBEDDER`, `MAX_FILE_SIZE`, `MAX_PASTE_IMAGE_SIZE_MB`, `PASTE_ALLOWED_IMAGE_TYPES`, `OPENSEARCH_DEFAULT_LIMIT`.
- **Remediation** : deplacer la ligne `:26` dans « Feature switches » ; passer les deux « 0.7.3 » en « 0.7.4 » au freeze. Effort S.

### [INFO] 7. `docs/architecture.md` incomplet sur les modules et les prefixes

- **Localisation** : `docs/architecture.md:67-73`, `:84`, `:88` ; `document-parser/tests/test_architecture.py:60`, `:65-77` ; `document-parser/api/mcp.py:16` ; `document-parser/main.py:127`
- **Constat** : le paragraphe modifie par #401 (`:63-65`) est exact : le test liste bien ses exceptions historiques (`test_architecture.py:65-77`). Mais le tableau des couches omet `mcp_adapter/`, que le test contraint (`:60`). Le tableau des prefixes omet `/api/mcp` et `/mcp`, ne cite pas l'editeur dans `/api/documents` (`:84`) et decrit `/api/config` comme « reasoning settings » seulement (`:88`), alors qu'il porte aussi la config MCP. Le port `PreviewImageCache` et `services/preview_service.py` ajoutes par #401 ne demandent pas de mention a ce niveau de detail.
- **Remediation** : une ligne `mcp_adapter` dans le tableau des couches ; « analysis editor » ligne `:84` ; lignes `/api/mcp` et `/mcp`. Effort S.

### [INFO] 8. README muet sur l'editeur

- **Localisation** : `README.md:24-31`, `:35-43`
- **Constat** : la liste « What it does » ne cite ni l'editeur ni la correction d'une analyse ; le tableau de documentation n'a pas la page `docs/analysis-editor.md` (presente dans `mkdocs.yml:38` et `docs/index.md:36`). Inchange depuis la baseline.
- **Remediation** : une puce « Lets you correct the extracted text and structure, with a saved edit history » et une ligne de tableau. Effort S.

### [INFO] 9. Fichiers de travail suivis a la racine

- **Localisation** : `analysis_editor_path_to_alpha.md` (182 lignes, suivi par git, reference par aucune page) ; `orca.yaml` (suivi, commit `7ed04cf`, documente nulle part) ; `docs/design/analysis-editor.md:1-3` (pas de ligne `Status`)
- **Constat** : `2602.14276v2.pdf`, `out/`, `site/` sont ignores (`.gitignore:71`, `:65`, `:7`) : pas de probleme. Le plan « Path To Alpha » et `orca.yaml` partiront dans le tag. `paseo.json` est suivi mais documente dans `[0.7.2]`.
- **Remediation** : deplacer le plan dans `docs/design/` ou le supprimer ; une ligne sur `orca.yaml` a cote de `paseo.json` dans `CONTRIBUTING.md`, ou le retirer ; `Status: Implemented (0.7.4)` dans le design doc. Effort S.

### [INFO] 10. SemVer : un patch qui livre une fonctionnalite, une API et une migration

- **Localisation** : `CHANGELOG.md:7-35`
- **Constat** : inchange depuis la baseline. 11.2.2 reste conforme (0.y.z, decision du mainteneur).
- **Remediation** : ecrire la regle de numerotation dans `docs/maintainers.md`.

### [INFO] 11. Versions secondaires

- **Localisation** : `document-parser/pyproject.toml:3` (`0.0.0`) ; `e2e/api/pom.xml:10`, `e2e/ui/pom.xml:10` (`0.3.1`)
- **Constat** : inchange. La version exposee vient de `APP_VERSION` (`document-parser/infra/settings.py:16`, `:207` ; `/api/health`, `document-parser/main.py:147`), fixee par la CI au build (`.github/workflows/release.yml:71`), pas de ces fichiers.
- **Remediation** : une ligne dans `docs/maintainers.md` sur le placeholder volontaire.

---

## Verifications sans ecart

- **`docs/analysis-editor.md` conforme au code** : fusion en ordre de lecture et meme type uniquement (`:18` ; `frontend/src/features/analysis-editor/commands.ts:84-91` ; `document-parser/infra/docling_editor.py:214-221`) ; Ask et MCP lisent la derniere conversion (`:41` ; `document-parser/services/parse_loader.py:89`) ; `ANALYSIS_EDITOR_ENABLED` et `edited=true` en 404 quand l'editeur est coupe (`:43` ; `document-parser/api/documents.py:148-149`, `document-parser/api/deps.py:55`). La doc ne parle pas des codes 404/409 ; le changelog `:35` dit 404 pour une ressource absente, ce que confirment `document-parser/api/errors.py:17-22` et `document-parser/services/analysis_edit_service.py:274-289`.
- **Routes du changelog** : les 6 routes `:11` existent (`document-parser/api/analysis_edits.py:108`, `:120`, `:135`, `:152`, `:174`, `:198`), ainsi que `export?edited=true` (`document-parser/api/documents.py:145`).
- **Affirmations #395 verifiees** : id `working:{document}:{analysis}` (`analysis_edit_service.py:354`), cache corrompu ignore et rejoue (`:300-312`), fusion bloquee entre types (`commands.ts:89-91`).
- **#397** : cartes MCP en anglais sauf navigateur francais (`document-parser/mcp_adapter/sources_app.html:532`, `citation_app.html:497`).
- **Liens** : script sur `docs/**/*.md` (hors `audit/reports`), `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md` : 0 lien relatif casse ; les 10 entrees `.md` de la nav `mkdocs.yml:34-46` existent. `mkdocs build --strict` non execute : le theme `material` n'est pas installe dans `document-parser/.venv`.
- **`SECURITY.md:9`** couvre `0.7.x`.

---

## Delta vs audit du 2026-11-13

| Item | 2026-11-13 (`eade7fa`) | 2026-11-18 (`a6fb539`) | Evolution |
|------|------------------------|------------------------|-----------|
| 11.1.1 Changelog fige | CRIT | CRIT | = (pre-freeze) |
| 11.1.2 Changements listes | MAJ | OK | leve par `f06e085` (#400) : puce Analysis editor `CHANGELOG.md:11`, export par defaut `:21` |
| 11.1.3 Breaking identifies | OK | OK | = |
| 11.1.4 Keep a Changelog | OK | OK | = ; `Fixed` passe de 3 a 10 puces hors sujet (INFO 1) |
| 11.2.1 Version front | MAJ | MAJ | = (pre-freeze) |
| 11.2.2 SemVer | OK | OK | = |
| 11.3.1 TODO/FIXME | OK | OK | = |
| 11.3.2 console.log | OK | OK | = |
| 11.3.3 print() | OK | OK | = |
| **Score** | **61** | **72** | **+11** ; au freeze 89 -> **100** |

INFO de la baseline (8) :
- **Resolues (3)** : doc de fusion (`docs/analysis-editor.md:18` dit maintenant ordre de lecture et meme type) ; MCP lit l'analyse d'origine (`docs/analysis-editor.md:41`) ; l'editeur est annonce (ancien MAJ).
- **Aggravee (1)** : `Fixed` pour du non publie (3 -> 10 puces).
- **Inchangees (4)** : deux sections d'interrupteurs, README et Architecture muets, statut du design doc et plan a la racine, SemVer et versions secondaires.

Nouvelles INFO : #401 sans numero ni details d'API, puces redondantes, rien de publie sur le rendu PDF, pas de note d'upgrade hors changelog, `orca.yaml`.

---

## Points positifs

- **Le manque principal de la baseline est corrige** : `CHANGELOG.md:11` presente l'editeur, ses actions, le 409, les 6 routes, `edited=true`, `ANALYSIS_EDITOR_ENABLED` et renvoie vers la doc.
- **La doc utilisateur suit le code apres #392 et #395** : ordre de lecture, meme type, MCP et Ask sans les editions.
- **Chaque correctif #391-#398 et chaque commit de #402 ajoute sa puce au changelog** ; le merge n'a produit ni doublon textuel ni conflit de texte.
- **Une seule variable nouvelle, documentee partout** (`docs/configuration.md:26`, `.env.example`, `docker-compose.yml`).
- **Le paragraphe d'architecture touche par #401 est exact**, et l'optimisation PDF a un design doc avec mesures avant/apres.
- **Code propre** : 0 TODO/FIXME, 0 `console.log`, 0 `print()` executable.
- **Aucun lien casse, aucune entree de nav orpheline.**

---

## Verdict partiel : NO-GO (pre-freeze)

72/100, 1 CRITICAL, 1 MAJOR, tous deux leves par le commit de freeze, qui porte le score a 100 (GO). Avant ce commit, retoucher le texte de `[Unreleased]` : vider `### Fixed` en fondant #392-#396 dans la puce editeur, deplacer #391 et #398 sous `### Changed`, et numeroter les puces #401. Sinon la note de la GitHub Release 0.7.4 presentera dix correctifs d'une fonctionnalite qu'elle introduit.

### Texte propose pour `[Unreleased]`

- `### Changed` — **Upgrade from 0.7.3** (#391) : « The first boot on a 0.7.3 database adds the new columns and tables and selects an active analysis for each analysed document. Nothing needs re-analysing. Back up `DB_PATH` before upgrading. »
- `### Changed` — **Faster PDF viewing** (#398, #401) : « The analysis, editor, document and Studio views render the visible page in the browser with PDF.js, loading the PDF by byte ranges; server-rendered previews remain the fallback. Previews are cached in memory (64 MB per process), sent as lossless WebP (`GET /api/documents/{id}/preview?format=webp`, `png` stays the default) and cached by the browser; the server opens the PDF by path instead of reading it whole. nginx now gzips JSON responses. A proxy in front of Studio must pass `Range` headers, or the browser downloads the whole PDF. Chunk inserts, splits, merges, regeneration and version restore write in one SQL statement instead of one per chunk. »
- `### Changed` — **Faster analysis lists** (#401) : texte actuel `:18` + numero.
- `### Added` — **Analysis editor** (#319, #388) : texte actuel `:11`, plus `:12-13`, plus : « Merges keep the document's reading order and only join elements of the same type; editor work runs off the event loop; a missing document or analysis answers 404, an outdated save 409 (#392-#396). `/api/health` reports `analysisEditorEnabled`. »
- Supprimer `### Fixed` (`:24-35`) une fois son contenu deplace.
