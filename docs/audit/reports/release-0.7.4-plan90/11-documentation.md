# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.4
**Date** : 2026-11-20
**Auditeur** : claude-code
**Branche** : `fix/0.7.4-editor-followups` @ `8dc0623`. Arbre de travail lu tel quel (seul `experiments/mcp-bench/` est non suivi).
**Nature** : contrôle après le « plan 90 ». Base : contrôle final sur `707a486` (`release-0.7.4-final/11-documentation.md` : 72/100, 100 au freeze, 1 CRIT, 1 MAJ, 15 INFO).
**Contexte** : le commit de freeze n'est toujours pas fait. `CHANGELOG.md:7` est `## [Unreleased]`, `frontend/package.json:3` est `0.7.3`. Deux scores, comme la base.

Commits relus : `git log 039778c..HEAD` (12 commits). Changements de comportement documentés : `16144f4` (hôtes en noms seuls, plafond d'import en constante, cache d'aperçu 16 Mo, code sans appelant), `0ac6ee2` (route `rebuild`, `warnings`, `referenceChanges`, `beforeElementId`), `92390c6` (`OPENSEARCH_DEFAULT_LIMIT`), `1ad4846` (tiroir d'historique). Documentation : `e4a73b3` (fiche 03), `86cd310` (plan 90). Les sept autres sont des refactorings sans changement de contrat (OpenAPI identique, selon la consigne ; aucune route ni variable touchée, vérifié par grep). Rien n'a été exécuté hors grep, `git` en lecture et les deux scripts de mesure `pyfuncs.py` / `tsfuncs.cjs` (machine calme, `nice`).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 9 |
| Score | 72 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 13 |

Pondération : poids total 18. Non conformes : 11.1.1 (3), 11.2.1 (2) = 5. `13 / 18 * 100 = 72,2` -> **72**.

### Score au freeze

| Scénario | Écarts restants | Score | Verdict |
|----------|-----------------|-------|---------|
| Aujourd'hui (pré-freeze) | 11.1.1 CRIT, 11.2.1 MAJ | 72 | NO-GO (CRIT) |
| Après le commit de freeze | aucun | 100 | GO |

Le commit de freeze doit contenir exactement :

1. `CHANGELOG.md:7` : `## [Unreleased]` devient `## [0.7.4] - AAAA-MM-JJ` (date du jour de release). Au-dessus, une section `## [Unreleased]` vide, comme le prévoit `plan-90.md:42`.
2. `frontend/package.json:3` : `"version": "0.7.4"`.
3. `frontend/package-lock.json:3` et `:9` : `"version": "0.7.4"` (les deux occurrences du paquet racine).

Rien d'autre n'est exigé par la fiche. `document-parser/pyproject.toml:3` (`0.0.0`) et `e2e/api/pom.xml:10` (`0.3.1`) ne sont pas dans son périmètre (INFO 7).

### Détail par item

| # | Item | Poids | Conforme | Justification |
|---|------|-------|----------|---------------|
| 11.1.1 | `[Unreleased]` renommée en `[X.Y.Z] - YYYY-MM-DD` | 3 | **Non** (pré-freeze) | `CHANGELOG.md:7` `## [Unreleased]` |
| 11.1.2 | Modifications significatives listées | 2 | Oui | Les six changements du cycle sont reportés : route `rebuild` retirée de la liste (`:11`), cache 16 MB (`:17`), plafond d'import en constante (`:31`), entrée `Removed` (`:41`), hôtes sans port (`:59`). Aucune entrée ne décrit une route, un réglage ou un champ disparu. Une phrase devenue fausse (F2) ; deux précisions utiles absentes (F3) |
| 11.1.3 | Breaking changes identifiés | 3 | Oui | Par rapport à `v0.7.3` : aucune route retirée (diff des décorateurs `@router` de `v0.7.3` et `HEAD` : 5 routes ajoutées, 0 retirée) ; une seule variable retirée, `OPENSEARCH_DEFAULT_LIMIT`, sous `### Removed` (`:39-41`), sans effet si elle reste posée. `rebuild`, `warnings`, `referenceChanges`, `beforeElementId`, `MAX_IMPORT_SIZE_MB` et `API_ALLOWED_HOSTS` n'existent pas dans `v0.7.3` (`git grep` sur le tag) : rien de publié ne casse. `HistoryDrawer` n'était déjà monté par aucun composant dans `v0.7.3` |
| 11.1.4 | Format Keep a Changelog | 1 | Oui | `:9` Added, `:15` Changed, `:35` Deprecated, `:39` Removed, `:43` Fixed, `:57` Security : ordre canonique, une section de chaque |
| 11.2.1 | `frontend/package.json` en X.Y.Z | 2 | **Non** (pré-freeze) | `frontend/package.json:3`, `frontend/package-lock.json:3`, `:9` = `0.7.3` |
| 11.2.2 | Version SemVer | 2 | Oui | `0.7.3 -> 0.7.4` (INFO 6) |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | Oui | 0 `TODO|FIXME|HACK|XXX` dans `document-parser` (hors `.venv`) et `frontend/src` |
| 11.3.2 | Pas de `console.log` de debug | 2 | Oui | 0 `console.log` / `console.debug` / `console.info`. 31 `console.error` et 2 `console.warn` (`features/analysis/store.ts:128`, `:183`), tous dans un `catch` ou un abandon de polling. Le seul `console.` dans les lignes ajoutées du cycle (`features/analysis/store.ts:114`) est un `console.error` déplacé par une extraction |
| 11.3.3 | Pas de `print()` de debug | 2 | Oui | 0 `print(` en début de ligne hors `tests/`. Les 4 `print(` restants sont dans des commentaires ou un message d'aide (`mcp_stdio.py:25`, `infra/settings.py:46`, `infra/secrets/fernet_box.py:46`, `:133`) |

---

## Delta vs contrôle final

| Item | Final (`707a486`) | Plan 90 (`8dc0623`) | Évolution |
|------|-------------------|---------------------|-----------|
| 11.1.1 | CRIT | CRIT | = (pré-freeze) |
| 11.1.2 | OK | OK | = ; F5, F6, F7 de la base corrigés (`CHANGELOG.md:55`, `:20`, `:11`, `:25`) ; les changements du cycle sont reportés |
| 11.1.3 | OK | OK | = ; nouvelle section `Removed`, seule suppression publiée |
| 11.1.4 | OK | OK | = ; `Removed` insérée à sa place, entre `Deprecated` et `Fixed` |
| 11.2.1 | MAJ | MAJ | = (pré-freeze) |
| 11.2.2 | OK | OK | = |
| 11.3.1 | OK | OK | = |
| 11.3.2 | OK | OK | = |
| 11.3.3 | OK | OK | = |
| **Score** | **72** (100 au freeze) | **72** (100 au freeze) | **=** |

INFO de la base (15) :

| # | Sujet | Statut |
|---|-------|--------|
| F1 | `user-guide.md:119` | résolue (`:119`, texte proposé repris) |
| F2 | **New analysis** dans un menu | résolue (`user-guide.md:49`) |
| F3 | `bbox-pipeline.md:86` onglet Chunk | résolue (`:86`) |
| F4 | `maintainers.md:54` run annulé | résolue (`:54`) |
| F5 | **Download PDF** | résolue (`CHANGELOG.md:55`) |
| F6 | « document History » | résolue (`CHANGELOG.md:20`) |
| F7 | deux entrées manquantes | résolue (`CHANGELOG.md:11`, `:25`) |
| F8 | 421 au dépannage | résolue (`troubleshooting.md:34-36`) |
| 1-7 | Reprises | inchangées, voir plus bas |

Nouvelles INFO : F1 à F6 ci-dessous. Total : 7 reprises + 6 = 13.

---

## Ecarts constates

### [CRIT] `[Unreleased]` non figée (attendu pré-freeze)

- **Localisation** : `CHANGELOG.md:7`
- **Constat** : inchangé. Normal tant que la date de release n'est pas connue.
- **Regle violee** : 11.1.1 (poids 3).
- **Remediation** : commit de freeze décrit plus haut, après les retouches de texte ci-dessous.

### [MAJ] `frontend/package.json` encore en 0.7.3 (attendu pré-freeze)

- **Localisation** : `frontend/package.json:3` ; `frontend/package-lock.json:3`, `:9`
- **Constat** : inchangé.
- **Regle violee** : 11.2.1 (poids 2).
- **Remediation** : `0.7.4` dans les trois emplacements, dans le commit de freeze.

### [INFO] F1. `.env.example:42-43` : « a port in an entry is ignored » est faux depuis `16144f4`

- **Localisation** : `.env.example:42-43`
- **Constat** : le fichier dit « Only the host name is compared (a port in an entry is ignored) ». Le code ignore maintenant l'entrée entière : `split_allowed_hosts` garde une entrée seulement si `parse_host_name(entry) == entry` (`document-parser/infra/host_guard.py:41-53`), donc `studio.lan:3000` est écarté et `studio.lan` reçoit 421. `docs/configuration.md:140`, `docs/troubleshooting.md:36` et `CHANGELOG.md:59` ont été mis à jour ; `.env.example` non. C'est le fichier que `document-parser/CLAUDE.md` et `docs/configuration.md` désignent comme point de départ.
- **Remediation** : remplacer `:42-43` par « its domain at 127.0.0.1 and use the API through your browser. List host names only, without a port: an entry with a port, a URL or `*` is ignored and named in the start-up log. Loopback is always allowed. »

### [INFO] F2. `CHANGELOG.md:29` : « The JSON returned is unchanged » n'est plus vrai

- **Localisation** : `CHANGELOG.md:29`
- **Constat** : `0ac6ee2` a retiré `warnings` et `referenceChanges` de la réponse de l'éditeur (`document-parser/api/schemas.py:287-295`) et rendu `targetElementId` et `placement` obligatoires (`:194-198`). La phrase était vraie quand l'entrée a été écrite ; elle ne l'est plus par rapport à cet état. Pour un utilisateur de 0.7.3, l'éditeur n'existait pas : la phrase ne lui apprend rien. C'est aussi la reprise 3 (entrée `Changed` sur une fonctionnalité `Added`).
- **Remediation** : supprimer la phrase « The JSON returned is unchanged. ». Mieux : fondre les bornes de requête dans la puce `Added` `:11` et retirer l'entrée `:29`.

### [INFO] F3. Deux précisions absentes du CHANGELOG et de la configuration

- **Localisation** : `CHANGELOG.md:59`, `docs/configuration.md:140`, `:31`
- **Constat** :
  - (a) Une liste `API_ALLOWED_HOSTS` faite seulement d'entrées ignorées (par exemple `*`) laisse la vérification **active**, loopback seul : le middleware est monté dès que la variable est non vide (`main.py:120-121`) et `describe_host_check` annonce « /api accepts loopback » (`host_guard.py:63-66`). `MCP_ALLOWED_HOSTS=*`, lui, délègue la vérification (`docs/mcp-server.md:45`, `bootstrap/mcp_mount.py:236`). La page dit que `*` est ignoré et qu'il faut laisser vide pour couper, ce qui est exact, mais quelqu'un qui recopie l'usage de `MCP_ALLOWED_HOSTS` coupe tout accès par un autre nom que loopback. `CHANGELOG.md:59` ne dit pas qu'une entrée avec port est ignorée.
  - (b) `configuration.md:31` : avec les valeurs par défaut, `NGINX_MAX_BODY_SIZE=200M` et le plafond d'import (`main.py:53`, 200 Mio) sont égaux, et nginx est devant : un import trop gros reçoit la page 413 de nginx, pas le message du backend. L'ancienne version le disait ; la nouvelle dit « over it, the backend answers 413 », ce qui ne vaut que si nginx est réglé plus haut ou absent.
- **Remediation** :
  - `configuration.md:140`, fin de puce : « A list made only of ignored entries keeps the check on, for loopback names only. »
  - `CHANGELOG.md:59` : remplacer « Entries are host names, without a port. » par « Entries are host names without a port; any other entry is ignored and named in the start-up log. »
  - `configuration.md:31` : remplacer « over it, the backend answers `413`. » par « over it, the backend answers `413`. With the default `200M`, nginx refuses such a body first, with its own `413` page. »

### [INFO] F4. `docs/design/analysis-editor.md` décrit encore la route `rebuild` et `beforeElementId`

- **Localisation** : `docs/design/analysis-editor.md:135`, `:509`, `:752` ; lien depuis la page publiée `docs/analysis-editor.md:86`
- **Constat** : le design doc est exclu du site (`mkdocs.yml`, `exclude_docs: design/`) mais la page publiée y renvoie « For the persistence details ». Il montre `beforeElementId: string | null` dans la commande de déplacement, `POST .../analysis-edits/rebuild` dans la liste des routes, et `:752` cite « rebuild » parmi les opérations qui prennent `analysisId`. Les trois ont disparu avec `0ac6ee2`. `:247` (« warnings ») est une étape de séquence, pas un champ : acceptable.
- **Remediation** : en tête du design doc, ajouter « Implementation differences as of 0.7.4: no `rebuild` route (a stale or unreadable working copy is replayed on load); `moveElement` takes `targetElementId` and `placement` only; the editor response has no `warnings` or `referenceChanges`. ». Ou corriger les trois lignes.

### [INFO] F5. `docs/maintainers.md:22-24` : la procédure de freeze oublie le lockfile

- **Localisation** : `docs/maintainers.md:22-24`
- **Constat** : la procédure publiée dit « sets `version` in `frontend/package.json` ». `frontend/package-lock.json:3`, `:9` portent aussi la version, et `plan-90.md:43` les cite. Suivre la page à la lettre laisse le lockfile en 0.7.3. Elle ne dit pas non plus de rouvrir une section `[Unreleased]` vide (`plan-90.md:42`).
- **Remediation** : `:24` « - sets `version` in `frontend/package.json` and `frontend/package-lock.json` (run `npm install --package-lock-only` in `frontend/`), » et ajouter « - adds an empty `## [Unreleased]` above it. »

### [INFO] F6. `plan-90.md` : trois affirmations ne correspondent pas à ce qui a été fait

- **Localisation** : `docs/audit/reports/release-0.7.4-final/plan-90.md`
- **Constat** :
  - `:86` annonce les objets valeur `StoreDraft` et `StoreUpdate`. Le code a `StoreDraft` et `StoreChanges` (`document-parser/services/store_service.py:78`, `:93`).
  - `:106` « Seuls D1 et D3 le changent [le document OpenAPI] ». D3 (`92390c6`) ne touche aucun fichier `api/` : `VectorStore.get_chunks` n'était derrière aucune route et `OPENSEARCH_DEFAULT_LIMIT` est un réglage. Seul D1 change le contrat (route `rebuild`, champs de `AnalysisEditorResponse`, `MoveElementEditRequest`).
  - `:65` « environ 450 lignes » pour D2. `1ad4846` retire 559 lignes hors tests (dont `HistoryDrawer.vue` 263, `store.ts` 155, `DocParseTab.vue` 80) et 385 lignes de tests et de spec Karate, soit 944.
  - Le reste est conforme à ce qui a été fait : lot 2a (`16144f4`, y compris « un paramètre de constructeur en moins » : `analysis_state_repo` retiré de `ChunkService`), D1 avec la comparaison de `engine_version` (`services/analysis_edit_service.py:84-93`), D2, D3 avec l'entrée `Removed`, D5 (`e4a73b3`), 3a (`79463bb`), 3b (0 fonction de plus de 30 lignes mesurée par `pyfuncs.py` et `tsfuncs.cjs`), 3d laissé (19 fichiers Python BIG). Aucun schéma de base modifié (`persistence/database.py` intact), comme annoncé pour D1. Le freeze reste à faire, comme `:40` le prévoit.
- **Remediation** : `:86` « `StoreDraft` et `StoreChanges` » ; `:106` « Seul D1 le change, volontairement » ; `:65` « environ 560 lignes de code et 380 de tests ». Le plan pourrait aussi porter une ligne d'état « exécuté le 2026-11-20, freeze en attente ».

### [INFO] 1 à 7. Reprises de la base

1. `### Fixed` : #391-#398 corrigent du code jamais publié ; seul `:55` (chemin du PDF) corrige un défaut publié.
2. #398 (`:50`) encore à part de #401 (`:17`).
3. Puces redondantes autour de l'éditeur (`:11-13`, `:19-20`, `:29`, `:46-54`) ; `analysisEditorEnabled` de `/api/health` non cité. Aggravée par F2.
4. `docs/design/pdf-loading-performance.md:1-5` sans `Status`.
5. Fichiers de travail suivis à la racine : `analysis_editor_path_to_alpha.md`, `orca.yaml`.
6. SemVer : un patch qui livre une fonctionnalité, une API et une migration.
7. Versions secondaires : `document-parser/pyproject.toml:3` (`0.0.0`), `e2e/api/pom.xml:10` (`0.3.1`).

Constat mineur antérieur, non compté : `docs/bbox-pipeline.md:60` dit que `infra/local_converter.py` logue l'avertissement de page sans taille ; il est émis par `infra/docling_pages.py:103`, appelé par le convertisseur local. Le comportement décrit est exact.

---

## Vérification des affirmations

### Changements du cycle et documentation

| Changement (commit) | Code à HEAD | CHANGELOG | Pages | Verdict |
|---------------------|-------------|-----------|-------|---------|
| `API_ALLOWED_HOSTS` noms seuls (`16144f4`) | `host_guard.py:31-53` ; `main.py:120-122` | `:59` | `configuration.md:125`, `:140` ; `troubleshooting.md:36` ; `SECURITY.md:58` ; `mcp-server.md:334-336` | V, sauf `.env.example:42-43` (F1) ; précision F3a |
| `MAX_IMPORT_SIZE_MB` en constante (`16144f4`) | `main.py:51-53`, `:99-104` ; plus lu par `settings.py` | `:31` | `configuration.md:31` ; retiré de `.env.example`, `docker-compose.yml`, `docker-compose.dev.yml` | V ; précision F3b |
| `OPENSEARCH_DEFAULT_LIMIT` retiré (`92390c6`) | plus lu (`git grep` : aucune occurrence hors CHANGELOG et rapports) | `:39-41` `Removed` | retiré de `configuration.md` | V |
| Route `rebuild` retirée (`0ac6ee2`) | `api/analysis_edits.py` : 5 routes | `:11` (5 routes listées) | `analysis-editor.md:67-73` | V ; design doc F4 |
| `warnings`, `referenceChanges` retirés (`0ac6ee2`) | `api/schemas.py:287-295` | `:29` « unchanged » | non cités | F2 |
| `moveElement` : `targetElementId` + `placement` (`0ac6ee2`) | `api/schemas.py:194-198` ; frontend `store.ts:207`, `EditableStructureNode.vue:39`, `:97-117` (glisser = `before`) | non cité | `analysis-editor.md:21` (« drag … before that row ») | V ; design doc F4 |
| Cache de travail rejoué si autre `engine_version` (`0ac6ee2`) | `analysis_edit_service.py:84-96` | non cité (interne) | `analysis-editor.md:61` | V |
| Cache d'aperçu 16 Mo (`16144f4`) | `infra/preview_cache.py:21` | `:17` | `configuration.md:160` | V |
| Tiroir d'historique supprimé (`1ad4846`) | aucun `HistoryDrawer` dans `frontend/src` ; routes `versions` toujours là (`api/document_versions.py:54`, `:66`) | `:22` « no screen offers it in this release » | aucune page publiée ne le cite ; `CHANGELOG.md:171` (0.7.3) historique | V |
| Rechunk sans lecture préalable de l'état (`16144f4`) | `chunk_service.py:220-232` ; 409 si l'analyse disparaît | `:25` (409) | — | V |
| Code sans appelant (`DocumentMerger`, `mark_stale`, `health_check`, `INSTRUCTIONS`, `_neutralise_all`, `StaleStoresStrip.vue`) | supprimés | — | aucune page ne les cite ; `mcp-server.md:85`, `:328` parlent des instructions construites par `build_instructions` (`mcp_adapter/server.py`), toujours présentes | V |

### Variables d'environnement

- Les 44 variables lues par `document-parser` hors `tests/` (`os.environ.get` et `_read_flag`, plus `DEFAULT_EMBEDDER` dans `persistence/database.py:342` et `STORE_SECRET_KEY` dans `infra/secrets/fernet_box.py:126`) sont toutes documentées dans `docs/configuration.md`, `docs/mcp-server.md` ou `docs/getting-started.md`.
- Chaque valeur par défaut des tableaux de `configuration.md` et `mcp-server.md:44-50` est celle du code (`infra/settings.py:249-336`) : 50, 0, 0, 100, 10, `image/png,image/jpeg,image/webp`, 900, 120, 300, 3, `accurate`, 0, `hidden`, `false`, `gpt-oss:20b`, 5, `ollama`, les cinq drapeaux, 384, `neo4j`/`changeme`, `bge-m3`, `self-hosted`, la valeur de `CORS_ORIGINS`, vide pour `API_ALLOWED_HOSTS`, `./uploads`, `./data/docling_studio.db`, `dev`, et pour MCP `127.0.0.1:*,localhost:*,[::1]:*`, 4000, 5, `true`, `false`, `true` (`false` sur un Space).
- Inversement, chaque variable des tableaux est lue par le code ou par la configuration Docker (`EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE` par le service d'embedding, `CONVERSION_MODE`, `NGINX_MAX_BODY_SIZE`, `WITH_REASONING`, `BAKE_MODELS` par compose et les Dockerfile).
- Seules `NEO4J_TEST_*` et `NEO4J_SNAPSHOT_UPDATE` (lues par `tests/`) ne sont pas documentées : normal.
- Par rapport à `v0.7.3` : variables ajoutées `ANALYSIS_EDITOR_ENABLED`, `API_ALLOWED_HOSTS` (toutes deux au CHANGELOG) ; retirée `OPENSEARCH_DEFAULT_LIMIT` (`Removed`).

### Noms cités par `architecture.md` et `bbox-pipeline.md`

Tous existent à HEAD : `tests/test_architecture.py`, `api/reasoning.py`, `services/reasoning_service.py`, `ReasoningRunner` (`domain/ports.py:809`), `infra/docling_agent_reasoning.py`, `domain/trace_builder.py`, `GET /api/mcp/server` (`api/mcp.py:19`), `/api/config` (`api/config.py:29`), `docs/architecture/adr-guide.md`, ADR-001, design doc 269 ; `to_topleft_list` et `EMPTY_BBOX` (`infra/bbox.py:20`, `:23`), `computeScale`, `bboxToRect`, `EMPTY_RECT`, `isPointInRect` (`shared/bboxScaling.ts`), `BboxCanvas.vue`, `PagePreviewWithOverlay.vue`, `BboxOverlay.vue` (et son `devicePixelRatio`), `LocalConverter`, `ServeConverter`. Aucune des pages publiées ne cite `ChunkService`, `write_document`, `build_mcp_server`, `AppStateBuilder` ni un port retiré : les refactorings n'y ont rien cassé.

### Fiche 03 modifiée (`e4a73b3`)

La précision du 3.2.3 correspond à D5 du plan (`plan-90.md:90`). Elle dit qu'elle change la règle de mesure et que les rapports antérieurs ne sont pas comparables. « Décision du mainteneur » : non vérifiable ici.

---

## Points positifs

- Les huit INFO de la base sont toutes corrigées, la plupart avec le texte proposé.
- La doc a suivi le code dans les mêmes commits : chaque commit qui change un comportement documenté touche aussi `CHANGELOG.md` et la page concernée (`16144f4`, `0ac6ee2`, `92390c6`).
- La seule suppression d'un réglage publié a sa section `Removed`, à sa place.
- 0 TODO, 0 `console.log`, 0 `print()` de debug, y compris dans les quelque 3 000 lignes ajoutées par le cycle.

---

## Verdict partiel : NO-GO (pré-freeze)

72/100, 1 CRITICAL, 1 MAJOR, 0 MINOR, 13 INFO. Le commit de freeze lève les deux : 100, GO.

### Corrections de documentation à faire avant le freeze

Aucune n'est bloquante pour la note. Par ordre d'importance :

1. `.env.example:42-43` : texte de F1 (affirmation fausse).
2. `CHANGELOG.md:29` : supprimer « The JSON returned is unchanged. » (F2).
3. `docs/maintainers.md:24` : ajouter le lockfile et la section `[Unreleased]` vide (F5).
4. `CHANGELOG.md:59`, `docs/configuration.md:140`, `:31` : trois phrases de F3.
5. `docs/design/analysis-editor.md` : note d'écart en tête ou correction de `:135`, `:509`, `:752` (F4).
6. `docs/audit/reports/release-0.7.4-final/plan-90.md:65`, `:86`, `:106` (F6).

### Non vérifiable ici

- Le rendu des pages et des diagrammes (`mkdocs build --strict` non lancé). Les liens n'ont pas été recontrôlés par script : aucun titre de section n'a changé dans ce cycle, les ancres citées (`#host-check-on-the-api`, `#limits`, `#behind-your-own-proxy`, `analysis-editor.md#api`) existent.
- Le comportement réel derrière nginx (413 au même seuil, 421) : déduit du code et de `nginx.conf.template:38`, `:42`, non exécuté.
- Que le document OpenAPI soit identique avant et après les refactorings : repris de la consigne, non regénéré.
- `CHANGELOG.md:48` (coût linéaire, temps hors boucle) : exige une mesure.
- Le caractère « décision du mainteneur » de la modification de la fiche 03.
