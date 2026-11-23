# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code
**Branche** : `fix/0.7.4-editor-followups` @ `eade7fa` = `release/0.7.4` @ `2f47f72` + 3 commits locaux non pousses (#391, #392, #393)
**Baseline** : re-audit 0.7.3 (`release/0.7.3` @ `e01fd95`, 100/100)
**Contexte** : 0.7.4 n'est pas encore figee. Le changelog sous `[Unreleased]` et la version `0.7.3` du frontend sont attendus avant le freeze (issue #373, « freeze commit »). La fiche est appliquee a la lettre ; la section « Score au freeze » dit ce qui disparait au freeze.

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 9 |
| Score | 61 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 8 |

Ponderation : poids total 18. Non conformes : 11.1.1 (3), 11.1.2 (2), 11.2.1 (2) = 7. `score = 11 / 18 * 100 = 61,1` -> **61**.

### Score au freeze

| Scenario | Ecarts restants | Score | Verdict |
|----------|-----------------|-------|---------|
| Etat actuel (pre-freeze) | 11.1.1 CRIT, 11.1.2 MAJ, 11.2.1 MAJ | 61 | NO-GO (CRIT) |
| Freeze fait selon `docs/maintainers.md:22-24` (date + version), changelog inchange par ailleurs | 11.1.2 MAJ | 89 | GO |
| Freeze + entree « Analysis editor » ajoutee au changelog | aucun | 100 | GO |

11.1.1 et 11.2.1 relevent du commit de freeze. **11.1.2 n'en releve pas** : c'est un manque de contenu (voir MAJ), qu'un freeze mecanique laisserait passer dans les notes de la GitHub Release.

| # | Item | Poids | Conforme | Preuve |
|---|------|-------|----------|--------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | **Non** (pre-freeze) | `CHANGELOG.md:7` `## [Unreleased]` |
| 11.1.2 | Modifications significatives listees | 2 | **Non** | L'editeur lui-meme, ses 6 routes et `ANALYSIS_EDITOR_ENABLED` sont absents (voir MAJ) |
| 11.1.3 | Breaking changes identifies | 3 | Oui | Aucune rupture identifiee (voir detail) ; pas de section BREAKING, ce qui est correct |
| 11.1.4 | Format Keep a Changelog | 1 | Oui | `CHANGELOG.md:5` ; `[Unreleased]` `:7` ; groupes `### Added` `:9`, `### Changed` `:14`, `### Fixed` `:19` (voir INFO « Fixed ») |
| 11.2.1 | `frontend/package.json` a la version X.Y.Z | 2 | **Non** (pre-freeze) | `frontend/package.json:3` = `"0.7.3"` ; lockfile `frontend/package-lock.json:3`, `:9` = `0.7.3`. Confirme par le log CI : `> docling-studio@0.7.3 type-check` |
| 11.2.2 | Version conforme au SemVer | 2 | Oui | `0.7.3 -> 0.7.4` (voir INFO SemVer) |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | Oui | `grep -rnE "TODO|FIXME|HACK|XXX"` : 0 dans `document-parser` (hors `.venv`) et `frontend/src` |
| 11.3.2 | Pas de `console.log` de debug | 2 | Oui | 0 `console.log` / `console.debug` dans `frontend/src` ; 2 `console.warn` en `catch`, anterieurs : `frontend/src/features/analysis/store.ts:117`, `:176`. Les `console.*` de `frontend/scripts/record-analysis-editor*.mjs` sont la sortie de scripts CLI, hors `src` |
| 11.3.3 | Pas de `print()` de debug | 2 | Oui | 0 `print(` executable hors `tests/` |

### Detail 11.1.3 — candidats examines

| Changement | Effet pour un utilisateur ou un client d'API existant | Rupture ? |
|------------|------------------------------------------------------|-----------|
| Editeur actif par defaut (`infra/settings.py:126`, `:279-280`) | Nouveaux boutons et nouvelles routes ; rien d'existant ne disparait | Non (ajout) |
| Schema : `document_analysis_state`, 3 tables d'edition, 2 colonnes `document_versions` | Base 0.7.3 mise a niveau au boot (`persistence/database.py:273-331`, #391). Une base 0.7.4 rouverte par 0.7.3 reste lisible (ajouts seulement) | Non, **si #391 est livre** — sans lui, une base 0.7.3 casse les versions et l'analyse active |
| Table `chunk_edits` plus creee | Aucune route ne la lisait ; elle reste en place sur les bases existantes | Non |
| Export md/json sans `analysisId` : « la plus recente terminee » -> « l'analyse active » (`api/documents.py:142`) | Meme reponse dans le cas courant (une nouvelle analyse devient active, `services/analysis_service.py:508`). Differe apres upgrade si la plus recente n'a pas de JSON Docling, ou apres restauration d'une version | Non, mais changement de comportement non documente (rattache au MAJ) |
| Re-chunk et arbre du document lisent le resultat edite (`services/chunk_service.py:376-384`, `:712-718`) | Identique tant qu'on n'edite pas | Non |
| Reponses enrichies (`/api/health` `analysisEditorEnabled`, `DocumentVersionResponse.chunksSource*`) | Champs ajoutes | Non |

---

## Ecarts constates

### [CRIT] La section `[Unreleased]` n'est pas figee (attendu pre-freeze)

- **Localisation** : `CHANGELOG.md:7`
- **Constat** : `## [Unreleased]` porte tout le contenu 0.7.4. L'extraction des notes de release (`docs/maintainers.md:39`) renverrait aujourd'hui une note vide. Le freeze est planifie (#373, ouvert) et n'a rien d'anormal a ce stade.
- **Regle violee** : 11.1.1 (poids 3).
- **Remediation** : commit `chore(release): freeze [0.7.4]` (`docs/maintainers.md:22-24`) : `## [0.7.4] - <date du tag>`, puis un `## [Unreleased]` vide au-dessus. Effort S.

### [MAJ] Le changelog ne dit pas que 0.7.4 livre un editeur d'analyse

- **Localisation** : `CHANGELOG.md:9-23`
- **Constat** :
  - Les 7 puces de `[Unreleased]` decrivent des aspects de l'editeur (« saved history » `:11`, « reading order » `:12`, « active result » `:16`, « persistence » `:17`) et 3 correctifs (`:21-23`) comme si l'editeur existait deja. Or il est **nouveau** en 0.7.4 : `git show 1de1929:CHANGELOG.md | grep -i editor` ne renvoie que deux lignes anciennes sans rapport (« single-page editor », « editable chunks editor »), et `frontend/src/features/analysis-editor/` n'existe pas a `1de1929`. Un lecteur de la note de release ne saura pas qu'il peut desormais corriger le texte, fusionner, supprimer, deplacer des elements et changer un niveau de titre (`051ec3f`, PR #388 et #319).
  - Absents aussi :
    - les 6 routes publiques : `GET /api/documents/{id}/analysis-editor`, `POST .../analysis-edits/preview`, `GET .../analysis-edits/history`, `PATCH .../analysis-edits/history/{sequence}`, `POST .../analysis-edits`, `POST .../analysis-edits/rebuild` (`document-parser/api/analysis_edits.py:120`, `:132`, `:145`, `:162`, `:184`, `:208`) ;
    - le parametre `edited` de l'export (`document-parser/api/documents.py:144`) et le champ `analysisEditorEnabled` de `/api/health` (`document-parser/main.py:169`) ;
    - la variable `ANALYSIS_EDITOR_ENABLED` (defaut `true`, `document-parser/infra/settings.py:279-280`), pourtant documentee dans `docs/configuration.md:26` et `.env.example:7-8` ;
    - le changement de defaut de l'export md/json sans `analysisId` (« latest completed » -> « active selection », `document-parser/api/documents.py:142`) ;
    - la detection de conflit a la sauvegarde (409, `25af0d6`) ;
    - les numeros de PR/issue de la fonctionnalite (#319, #388), alors que les correctifs citent #391-#393.
  - Aucune puce pour du contenu non livre : la PR #371 (plugin Claude, #370) n'est pas fusionnee et n'apparait pas, ce qui est correct.
- **Regle violee** : 11.1.2 (poids 2).
- **Remediation** : en tete de `### Added`, une puce **Analysis editor** (#319, #388) : actions disponibles, sauvegarde durable avec historique, conflit 409, telechargement edite, routes, `ANALYSIS_EDITOR_ENABLED` (defaut `true`) et renvoi vers `docs/analysis-editor.md`. Fusionner `:11-12` dans cette puce. Dans `### Changed`, une ligne sur le defaut de l'export. Effort S.

### [MAJ] `frontend/package.json` est encore en 0.7.3 (attendu pre-freeze)

- **Localisation** : `frontend/package.json:3` ; `frontend/package-lock.json:3`, `:9`
- **Constat** : version 0.7.3 partout. Prevue par le freeze (#373).
- **Regle violee** : 11.2.1 (poids 2).
- **Remediation** : `0.7.4` dans `package.json` et le lockfile, dans le commit de freeze. Effort S.

### [INFO] `docs/analysis-editor.md` decrit encore la fusion en ordre de selection, ce que #392 vient de changer

- **Localisation** : `docs/analysis-editor.md:18` ; `frontend/src/features/analysis-editor/store.ts:185-195` ; `document-parser/infra/docling_editor.py:89-98` (`_in_document_order`, `79035cb`)
- **Constat** : la doc dit « Their text joins in selection order under the first selected element ». Depuis #392, l'ordre de lecture du document fait foi, quel que soit l'ordre des clics, et la cible est le premier element dans cet ordre. `CHANGELOG.md:22` dit l'inverse de la doc.
- **Remediation** : « Their text joins in reading order under the first of them; the click order does not matter. » Effort S.

### [INFO] `docs/analysis-editor.md` ne dit pas que le serveur MCP lit aussi l'analyse d'origine

- **Localisation** : `docs/analysis-editor.md:41` ; `document-parser/services/parse_loader.py:73`, `:89` ; `document-parser/services/reasoning_service.py:101`
- **Constat** : la doc previent que **Ask** lit la derniere conversion, sans les editions. Le serveur MCP fait de meme (`parse_loader` prend la derniere analyse parsee, pas l'analyse active ni son resultat edite) : un agent citera donc le texte non corrige.
- **Remediation** : ajouter « and so does the MCP server » a la phrase. Effort S.

### [INFO] Correctifs de fonctionnalites non publiees classes en `### Fixed`

- **Localisation** : `CHANGELOG.md:19-23`
- **Constat** : #392 et #393 corrigent un editeur qui n'a jamais ete publie, et #391 est la migration de schema de 0.7.4 elle-meme. Pour un utilisateur de 0.7.3, rien de tout cela n'est une correction. Keep a Changelog reserve `Fixed` aux defauts d'une version publiee.
- **Remediation** : fondre #392/#393 dans la puce Analysis editor, et garder #391 comme note d'upgrade (par exemple sous `### Changed` : « a 0.7.3 database is upgraded in place on first boot »). Effort S.

### [INFO] Deux sections pour les interrupteurs dans `docs/configuration.md`

- **Localisation** : `docs/configuration.md:22-26` (« Feature flags », nouvelle) ; `docs/configuration.md:54-59` (« Feature switches », existante, avec `STUDIO_MODE_ENABLED`)
- **Constat** : `ANALYSIS_EDITOR_ENABLED` a ete place dans une nouvelle section au lieu du tableau existant.
- **Remediation** : deplacer la ligne dans « Feature switches » et supprimer la section ajoutee. Effort S.

### [INFO] README et page Architecture muets sur l'editeur

- **Localisation** : `README.md` (aucune occurrence de « editor » / « edit ») ; `docs/architecture.md:82`
- **Constat** : le README ne mentionne pas la fonctionnalite phare de la release. Le tableau des prefixes decrit `/api/documents` sans l'editeur (et toujours sans `/mcp`, INFO de la baseline). `docs/index.md` et `mkdocs.yml` ont bien la nouvelle page.
- **Remediation** : une ligne dans la liste des fonctionnalites du README ; « analysis editor » dans la ligne `/api/documents` de `docs/architecture.md:82`. Effort S.

### [INFO] Documents de conception de l'editeur : pas de statut, et un plan a la racine du depot

- **Localisation** : `docs/design/analysis-editor.md:1-3` ; `analysis_editor_path_to_alpha.md` (racine, 182 lignes)
- **Constat** : les design docs du projet portent une ligne `Status` (par exemple `docs/design/203-per-store-ingestion-state.md:7`) ; `analysis-editor.md` n'en a pas, ni de jalon ni d'issue. `analysis_editor_path_to_alpha.md` est un plan de travail (« Implementation Status », « Completed ») pose a la racine ; il n'est reference par aucune page.
- **Remediation** : ajouter `Status: Implemented (0.7.4)` et le jalon au design doc ; deplacer le plan dans `docs/design/` ou le supprimer. Effort S.

### [INFO] SemVer : un patch qui livre une fonctionnalite, 6 routes et une migration de schema

- **Localisation** : `CHANGELOG.md:7-23`
- **Constat** : 0.7.4 ajoute une fonctionnalite majeure activee par defaut, une API publique et une migration de base. 11.2.2 reste conforme (SemVer §4 en 0.y.z, precedent 0.7.3, decision du mainteneur). Le point est le meme que l'INFO SemVer de 0.7.3, en plus marque.
- **Remediation** : aucune pour 0.7.4. Ecrire la regle de numerotation dans `docs/maintainers.md` (deja recommande en 0.7.3).

### [INFO] Versions secondaires (baseline, inchange)

- **Localisation** : `document-parser/pyproject.toml:3` (`0.0.0`) ; `e2e/api/pom.xml:10`, `e2e/ui/pom.xml:10` (`0.3.1`)
- **Remediation** : inchangee — une ligne dans `docs/maintainers.md` sur le placeholder volontaire.

---

## Delta vs re-audit 0.7.3

| Item | 0.7.3 re-audit (`e01fd95`) | 0.7.4 (`eade7fa`) | Evolution |
|------|----------------------------|-------------------|-----------|
| 11.1.1 Changelog fige | OK | **CRIT** | pre-freeze, leve par #373 |
| 11.1.2 Changements listes | OK | **MAJ** | l'editeur n'est pas annonce |
| 11.1.3 Breaking identifies | OK | OK | = |
| 11.1.4 Keep a Changelog | OK | OK | = (`[Unreleased]` recree) |
| 11.2.1 Version front | OK | **MAJ** | pre-freeze, leve par #373 |
| 11.2.2 SemVer | OK | OK | = |
| 11.3.1 TODO/FIXME | OK | OK | = |
| 11.3.2 console.log | OK | OK | = |
| 11.3.3 print() | OK | OK | = |
| **Score** | **100** | **61** | **-39** (dont -28 leves au freeze) |

INFO de la baseline (10) :
- **Resolues (3)** : `[Unreleased]` recree au-dessus de `[0.7.3]` (`CHANGELOG.md:7`) ; « Analysis library » corrige dans la puce #323 avant le tag (`CHANGELOG.md:37`, « Saved analyses ») — il reste aux lignes `:31` et `:39`, figees dans `[0.7.3]` ; la puce BREAKING `ASK_MODE` est figee, sans objet.
- **Restantes ou sans objet pour 0.7.4 (7)** : versions secondaires (reprise ci-dessus), SemVer (reprise, plus marquee), Architecture/Configuration (Configuration a maintenant une entree pour l'editeur ; Architecture reste muette, reprise), variables `MCP_*`, avis certifi/uv, lieu de l'import combine, jalons : elles portent sur le texte fige de `[0.7.3]` ou sur GitHub, et ne sont pas reprises.

Nouvelles INFO (6) : doc de fusion perimee apres #392, MCP lit l'analyse d'origine, `Fixed` pour du non publie, deux sections d'interrupteurs, README/Architecture muets, statut du design doc et plan a la racine.

---

## Points positifs

- **Documentation utilisateur de l'editeur substantielle et juste dans l'ensemble** : `docs/analysis-editor.md` (actions et limites par action, brouillon recupere, conflit, historique revert/reapply, telechargements, modele d'immutabilite avec diagramme), section dans `docs/user-guide.md`, entree dans `docs/index.md` et `mkdocs.yml`.
- **La nouvelle variable est documentee la ou il faut** : `docs/configuration.md:26` dit ce qu'elle cache et que les routes repondent 404, ce que confirment `api/documents.py:147-148` et `test_analysis_editor_feature_flag.py`.
- **Les limites sont dites** : Ask ne voit pas les editions (`docs/analysis-editor.md:41`), les chunks deviennent perimes et doivent etre regeneres, la position des boites PDF ne bouge pas.
- **Correctifs documentes au moment ou ils sont faits** : chaque commit #391-#393 ajoute sa puce, avec le symptome et l'effet pour l'utilisateur.
- **`[Unreleased]` recree** apres le freeze 0.7.3, comme le recommandait la baseline.
- **Code propre** : 0 TODO/FIXME, 0 `console.log`, 0 `print()` executable, malgre +9 800 lignes.

---

## Verdict partiel : NO-GO (pre-freeze)

61/100, 1 CRITICAL, 2 MAJOR. Le NO-GO tient a la regle absolue sur 11.1.1, attendue tant que la release n'est pas figee. Le commit de freeze (#373) leve 11.1.1 et 11.2.1 et porte le score a 89 (GO). Il ne suffit pas pour 100 : avant le freeze, ajouter au changelog la puce qui annonce l'editeur d'analyse, ses routes et `ANALYSIS_EDITOR_ENABLED` (MAJ 11.1.2). Sinon la note de release 0.7.4 decrira l'historique et l'ordre de lecture d'un editeur qu'elle n'a jamais presente. A corriger dans la meme passe : `docs/analysis-editor.md:18`, contredit par #392.
