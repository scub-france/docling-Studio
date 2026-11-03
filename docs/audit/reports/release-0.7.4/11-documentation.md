# Rapport d'audit : Documentation & Changelog

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : release/0.7.4 @ 1de1929 (= tag `v0.7.3` sur `2b4ef25` + 2 commits README, `0465e70` et `1de1929`)
**Baseline** : re-audit 0.7.3 (`docs/audit/reports/release-0.7.3-reaudit/11-documentation.md`, 100/100 sur `e01fd95`) ; audit initial 0.7.3 (`docs/audit/reports/release-0.7.3/11-documentation.md`, 44/100 sur `02adc68`)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 7 / 9 |
| Score | 72 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 16 |

Ponderation : items conformes = 13 pts / 18 pts totaux → 72/100 (72,2).
Items non conformes : 11.1.1 (poids 3), 11.2.1 (poids 2).

> Contexte : la release 0.7.4 vient d'etre ouverte. Elle servira de **release qualite** (remediation de la dette d'audit). A ce stade, elle ne contient aucun changement fonctionnel par rapport a `v0.7.3` : `git diff --stat v0.7.3..HEAD` = `README.md` (1 ligne), `docs/screenshots/mcp-demo.gif` ajoute, `docs/screenshots/presentation.gif` retire. L'etape 2 « Freeze » de `docs/maintainers.md:22-24` n'est donc pas faite, et c'est normal : les deux ecarts ponderes (11.1.1, 11.2.1) sont exactement ce que le commit de gel corrige. On avait le meme etat au premier audit de 0.7.0 (72/100) et de 0.7.3. Le contenu attendu du commit de gel est detaille plus bas.

---

## Grille item par item

| # | Item | Poids | Conforme | Preuve |
|---|------|-------|----------|--------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | **NON** | `CHANGELOG.md:5-7` : la premiere section est `## [0.7.3] - 2026-11-02`. Il n'y a ni `[Unreleased]` ni `[0.7.4]` |
| 11.1.2 | Toutes les modifications significatives listees | 2 | OUI | `git log v0.7.3..HEAD` : 2 commits, `docs(readme)` (remplacement du GIF d'en-tete, `README.md:12`). Rien de significatif a lister |
| 11.1.3 | Breaking changes clairement identifies | 3 | OUI | Aucun changement de comportement dans `v0.7.3..HEAD`. La rupture 0.7.3 reste classee (`CHANGELOG.md:36-38`) |
| 11.1.4 | Format Keep a Changelog | 1 | OUI | `CHANGELOG.md:5` ; groupes standards (`:9`, `:17`, `:27`, `:31`) ; dates ISO ; ordre decroissant (`:7`, `:40`, `:50`, `:61`, `:80`…). Voir INFO-1 sur `[Unreleased]` |
| 11.2.1 | `frontend/package.json` a la version X.Y.Z | 2 | **NON** | `frontend/package.json:3` = `0.7.3` (lockfile `frontend/package-lock.json:3`, `:9` = `0.7.3`) |
| 11.2.2 | Version conforme au SemVer | 2 | OUI | `0.7.3 → 0.7.4` : patch pour une release de correctifs. Voir INFO-14 |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | OUI | 0 occurrence (`document-parser` hors `.venv`, tests compris ; `frontend/src` ; aussi `embedding-service`, `e2e`, `.github`) |
| 11.3.2 | Pas de `console.log` de debug | 2 | OUI | 0 `console.log` / `console.debug`. 2 `console.warn`, dans des `catch` (`frontend/src/features/analysis/store.ts:117`, `:176`). 31 `console.error`, tous en gestion d'erreur. La regle versionnee les autorise (`frontend/eslint.config.js:20`, `no-console` avec `allow: ['warn', 'error']`) |
| 11.3.3 | Pas de `print()` de debug | 2 | OUI | 0 `print(` executable. 4 occurrences en commentaire ou docstring (`document-parser/mcp_stdio.py:25`, `infra/settings.py:45`, `infra/secrets/fernet_box.py:46`, `:133`) |

Calcul : (2 + 3 + 1 + 2 + 1 + 2 + 2) / 18 × 100 = 13 / 18 × 100 = **72,2 → 72/100**.

---

## Metriques collectees

| Metrique | Valeur |
|----------|--------|
| Commits `v0.7.3..HEAD` | 2 (`0465e70`, `1de1929`), `docs(readme)`, tous deux `[skip ci]`, pousses directement sur `main` (l'API GitHub ne leur associe aucune PR), puis `release/0.7.4` tiree de `main` |
| Changements fonctionnels depuis `v0.7.3` | 0 |
| Premiere section du CHANGELOG | `## [0.7.3] - 2026-11-02` (`CHANGELOG.md:7`). La date est celle du commit tague (`2b4ef25`, 2026-11-02), la GitHub Release `v0.7.3` est publiee (2026-11-02T16:05:45Z) |
| Versions | `frontend/package.json` 0.7.3 ; lockfile 0.7.3 ; `pyproject.toml` ×2 `0.0.0` (placeholder) ; `e2e/*/pom.xml` ×2 `0.3.1` |
| TODO / FIXME / HACK / XXX | 0 |
| `console.log` / `console.debug` | 0 (`console.warn` : 2 en `catch` ; `console.error` : 31) |
| `print(` executable | 0 |
| Variables d'environnement lues a l'execution | **49** : 45 dans `document-parser/infra/settings.py:199-276`, plus `DEFAULT_EMBEDDER` (`persistence/database.py:249`), `EMBEDDING_MODEL` et `EMBEDDING_BATCH_SIZE` (`embedding-service/main.py:19-20`), `NGINX_MAX_BODY_SIZE` (`Dockerfile:61`, `:65`). Plus 7 variables de build ou de dev |
| … presentes dans `.env.example` | 35 / 49 |
| … presentes dans `docs/configuration.md` | 34 / 49 (les 7 `MCP_*` sont dans `docs/mcp-server.md:42-50`) |
| … documentees nulle part | **8** : 2 effectives, 3 sans effet, 3 d'ingestion (depreciee). Voir INFO-4 |
| Variables documentees mais jamais lues | 0 |
| Valeurs par defaut documentees ≠ code | 0 (une nuance, `.env.example:117`, voir INFO-4) |
| Liens relatifs Markdown (72 fichiers, hors rapports d'audit) | 2 casses, tous deux hors du site : `.github/PULL_REQUEST_TEMPLATE.md:22`, `docs/design/329-…:592` |
| Liens absolus vers `github.com/scub-france/Docling-Studio/(blob\|tree)/main/…` | 0 casse |
| `mkdocs build --strict` | **Non execute localement** : `mkdocs` est dans `document-parser/.venv`, mais le theme `material` n'y est pas (et l'audit n'installe rien). Le dernier run de `docs.yml` est vert sur `2b4ef25` (run `41477971397`, 2026-11-02). Depuis, aucune page publiee n'a change (seulement le GIF et des rapports exclus du site) |
| Docstrings backend | 112 / 113 modules (seul `document-parser/conftest.py` n'en a pas) ; 349 / 471 definitions publiques de premier niveau ; 34 / 51 routes avec docstring ou `summary`/`description` |
| Design docs livres encore `Accepted` ou `Draft` | 16 (voir INFO-9) |

### Matrice exhaustive des variables d'environnement

Les colonnes donnent la ligne ou chaque fichier documente la variable. « — » signifie absente. Lignes de code : `document-parser/infra/settings.py`, sauf mention contraire. Compose : `docker-compose.yml`.

| Variable | Lue (code) | `.env.example` | `configuration.md` | Autre doc | Compose | Statut |
|----------|-----------|----------------|--------------------|-----------|---------|--------|
| `APP_VERSION` | `:204` | `:44` | `:121`, `:132` | — | build-arg | OK |
| `ASK_MODE` | `:236` | `:88-90` | `:35`, `:41` | — | `:190` | OK (texte « Reasoning » faux, INFO-2) |
| `BATCH_PAGE_SIZE` | `:222` | `:10-13` | `:20` | — | `:173` | OK |
| `CONVERSION_ENGINE` | `:205` | `:15-17` | `:14` | — | `Dockerfile:69`, `:117` | OK |
| `CONVERSION_TIMEOUT` | `:209` | `:23-24` | `:19`, `:22` | — | — | OK |
| `CORS_ORIGINS` | `:199` | `:46-47` | `:118` | — | `:164` | OK |
| `DB_PATH` | `:240` ; `persistence/database.py:26` ; `mcp_stdio.py:44` | `:53` | `:120` | `mcp-server.md:119` | `Dockerfile:60` | OK |
| `DEFAULT_EMBEDDER` | `persistence/database.py:249` | — | — | — | — | **Non documentee** (ingestion) |
| `DEFAULT_TABLE_MODE` | `:213` | — | `:17` | — | — | OK (configuration seule) |
| `DEPLOYMENT_MODE` | `:206`, `:258` | `:39-41` | `:117` | `mcp-server.md:25` | — | OK, effet decrit incompletement (INFO-5) |
| `DOCLING_SERVE_API_KEY` | `:208` | `:21` | `:16` | — | `:170` | OK |
| `DOCLING_SERVE_URL` | `:207` | `:20` | `:15` | — | `:169` | OK |
| `DOCUMENT_TIMEOUT` | `:210` | — | `:22` | — | — | OK (configuration seule) |
| `EMBEDDING_BATCH_SIZE` | `embedding-service/main.py:20` | — | — | — | `:84` | **Non documentee** (ingestion) |
| `EMBEDDING_DIMENSION` | `:238` | `:68-69` | `:92` | — | — | OK |
| `EMBEDDING_MODEL` | `embedding-service/main.py:19` | `:65-66` | `:109` | — | `:80` | OK |
| `EMBEDDING_URL` | `:224` | `:62-63` | `:90` | — | `:175` | OK |
| `INSPECT_MODE_ENABLED` | `:250` | — | — | — | — | **Non documentee, effective** |
| `LINKED_MODE_ENABLED` | `:252` | — | — | — | — | **Non documentee, sans effet** |
| `LLM_PROVIDER_TYPE` | `:231` | `:86-87` | `:46` | — | — | OK |
| `LOCK_TIMEOUT` | `:211` | — | `:22` | — | — | OK (configuration seule) |
| `MAX_CONCURRENT_ANALYSES` | `:212` | `:26-27` | `:18` | — | — | OK |
| `MAX_FILE_SIZE` | `:215` | — | — | — | — | **Non documentee, effective** |
| `MAX_FILE_SIZE_MB` | `:216` | `:29-30` | `:28` | — | `:172` | OK |
| `MAX_PAGE_COUNT` | `:214` | `:36-37` | `:29` | — | — | OK |
| `MAX_PASTE_IMAGE_SIZE_MB` | `:241` | — | — | `CHANGELOG.md:205` (0.5.0) | — | **Non documentee, sans effet** |
| `MCP_ALLOWED_HOSTS` | `:262-268` | `:111-113` | — | `mcp-server.md:45` | `:194` | Absente de configuration (INFO-5) |
| `MCP_APPS_ENABLED` | `:269` | `:123-124` | — | `mcp-server.md:49` | — | idem |
| `MCP_CITATION_CARD` | `:271` | `:125-127` | — | `mcp-server.md:50` | — | idem |
| `MCP_ENABLED` | `:256-260` | `:102-110` | — | `mcp-server.md:44` | `:193` | idem |
| `MCP_MAX_READ_TOKENS` | `:273` | `:118-119` | — | `mcp-server.md:47` | — | idem |
| `MCP_MAX_ROUNDS` | `:274` | `:120-122` | — | `mcp-server.md:48` | — | idem |
| `MCP_STUDIO_BASE_URL` | `:275` | `:116-117` | — | `mcp-server.md:46` | `:195` | idem, et nuance de valeur (INFO-4) |
| `NEO4J_PASSWORD` | `:227` | `:75` | `:94` | — | `:178` | OK |
| `NEO4J_URI` | `:225` | `:73` | `:93` | — | `:176` | OK |
| `NEO4J_USER` | `:226` | `:74` | `:94` | — | `:177` | OK |
| `NGINX_MAX_BODY_SIZE` | `Dockerfile:61`, `:65` ; `nginx.conf.template:23` | `:32-34` | `:30` | — | `:208` | OK |
| `OLLAMA_HOST` | `:232` | `:82` | `:43` | — | — | OK |
| `OPENSEARCH_DEFAULT_LIMIT` | `:237` | — | — | — | — | **Non documentee** (ingestion) |
| `OPENSEARCH_URL` | `:223` | `:58-60` | `:91` | — | `:174` | OK |
| `PASTE_ALLOWED_IMAGE_TYPES` | `:200-202`, `:242` | — | — | `CHANGELOG.md:205` (0.5.0) | — | **Non documentee, sans effet** |
| `RAG_PIPELINE_ENABLED` | `:247` | — | `:52` | — | `:188` | OK (configuration seule) |
| `RATE_LIMIT_RPM` | `:217` | — | `:31` | — | `:171` | OK (configuration seule) |
| `REASONING_ENABLED` | `:229` | `:81` | `:42` | — | — | OK |
| `REASONING_MAX_ITERATIONS` | `:234` | `:84-85` | `:45` | — | — | OK |
| `REASONING_MODEL_ID` | `:233` | `:83` | `:44` | — | — | OK |
| `STORE_SECRET_KEY` | `:228` ; `infra/secrets/fernet_box.py:126` | `:92-100` | `:95` | — | `:183` | OK |
| `STUDIO_MODE_ENABLED` | `:245` | — | `:53` | — | `:187` | OK (configuration seule) |
| `UPLOAD_DIR` | `:239` | `:49-50` | `:119` | — | `Dockerfile:59` | OK |
| *Build / dev* | | | | | | |
| `CONVERSION_MODE` | `docker-compose.yml:144` | `:7-8` | `:129` | — | `:144` | OK |
| `WITH_REASONING` | `Dockerfile:90` | — | `:130` | — | `:157` | OK |
| `BAKE_MODELS` | `Dockerfile:86` | — | `:131` | — | `:156` | OK |
| `BAKE_MODEL` | `embedding-service/Dockerfile:31` | — | — | `docs/architecture/huggingface-dependency-map.md:20` | `:81` | OK (ingestion) |
| `FRONTEND_HOST_PORT` | `docker-compose.dev.yml:176` | — | — | `CONTRIBUTING.md:52` | dev | OK (dev) |
| `VITE_APP_VERSION` | `frontend/vite.config.js:19` | — | — | — | `Dockerfile:19` | Interne |
| `VITE_API_PROXY_TARGET` | `frontend/vite.config.js:7` | — | — | — | `docker-compose.dev.yml:182` | Interne (dev) |

Les 6 variables marquees « configuration seule » sont absentes de `.env.example`, mais ce fichier renvoie a `docs/configuration.md` comme reference complete (`.env.example:5`). Le re-audit 10 de 0.7.3 a juge ce renvoi suffisant : ce n'est pas compte comme ecart ici.

---

## Ecarts constates

### [CRIT] Pas de section `[0.7.4] - YYYY-MM-DD` dans le changelog

- **Localisation** : `CHANGELOG.md:5-7`
- **Statut vs 0.7.3** : resolu au re-audit 0.7.3 (`## [0.7.3] - 2026-11-02`), **reapparait** avec la nouvelle release, au stade pre-gel attendu.
- **Constat** : apres l'en-tete (`CHANGELOG.md:5`), le changelog passe directement a `## [0.7.3] - 2026-11-02` (`CHANGELOG.md:7`). Il n'y a pas de section `## [0.7.4]`, ni meme de section `## [Unreleased]` ou l'accumuler (voir INFO-1). L'extraction des notes de GitHub Release (`awk '/^## \[0.7.4\]/…'`, `docs/maintainers.md:40`) renverrait un fichier vide. C'est l'etape standard du commit de gel (`docs/maintainers.md:22-23`), que la procedure place apres l'audit (`docs/maintainers.md:21`).
- **Regle violee** : item 11.1.1, poids 3.
- **Remediation** : en deux temps.
  1. **Maintenant**, avant la premiere PR de remediation : ajouter `## [Unreleased]` au-dessus de `CHANGELOG.md:7`. Chaque PR de la release qualite y ajoute son entree, comme le demandent `CONTRIBUTING.md:107` et `.github/PULL_REQUEST_TEMPLATE.md:26`.
  2. **Au gel**, dans le commit `chore(release): freeze [0.7.4]` : renommer `## [Unreleased]` en `## [0.7.4] - <date du tag>` et recreer au-dessus un `## [Unreleased]` vide. Le contenu attendu est detaille plus bas.
- **Effort** : 2 min maintenant, 5 a 10 min au gel (hors redaction des entrees, faite au fil des PR).

### [MAJ] `frontend/package.json` reste en 0.7.3 au lieu de 0.7.4

- **Localisation** : `frontend/package.json:3` ; lockfile `frontend/package-lock.json:3`, `:9`
- **Statut vs 0.7.3** : resolu au re-audit 0.7.3, **reapparait** avec la nouvelle release, au stade pre-gel attendu.
- **Constat** : `"version": "0.7.3"`. Cette valeur sert de repli a la version affichee quand `VITE_APP_VERSION` n'est pas fourni (`frontend/vite.config.js:19`). L'image publiee recoit bien la version du tag (`.github/workflows/release.yml:71`, `Dockerfile:13-19`), mais une construction depuis les sources sans cet argument afficherait `0.7.3`. Le gel de 0.7.3 avait aussi aligne le lockfile, qu'il faut garder au meme niveau.
- **Regle violee** : item 11.2.1, poids 2.
- **Remediation** : dans le commit de gel, `cd frontend && npm version 0.7.4 --no-git-tag-version`. La commande met a jour `package.json:3` et `package-lock.json:3`, `:9` d'un coup.
- **Effort** : 2 min.

### [INFO-1] Pas de section `[Unreleased]` alors que le cycle 0.7.4 est ouvert

- **Localisation** : `CHANGELOG.md:5-7` ; `CONTRIBUTING.md:107` ; `.github/PULL_REQUEST_TEMPLATE.md:26` ; `docs/maintainers.md:22-24`
- **Statut vs 0.7.3** : **inchangee** (INFO du re-audit 0.7.3), **contexte aggrave**. Au gel, l'absence etait sans effet. Maintenant que le cycle est ouvert, elle en a un : les PR de remediation n'ont aucune section ou ecrire.
- **Constat** : `CONTRIBUTING.md:107` (« add a line under `[Unreleased]` ») et le modele de PR (`.github/PULL_REQUEST_TEMPLATE.md:26`) renvoient a une section qui n'existe pas. La procedure de gel elle-meme suppose qu'elle existe (« renames `[Unreleased]` », `docs/maintainers.md:23`). Les gels 0.7.1 et 0.7.2 avaient garde un `## [Unreleased]` vide (`git show e95680a:CHANGELOG.md`, `git show caddf30:CHANGELOG.md`). Ce n'est pas le cas du gel 0.7.3 (`99e1230`). Le changelog n'a pas non plus de liens de comparaison en pied de page (recommandation Keep a Changelog, jamais appliquee dans ce projet).
- **Regle violee** : hors checklist ponderee (11.1.4 reste conforme : `[Unreleased]` est une recommandation). Prerequis direct de 11.1.1 et 11.1.2.
- **Remediation** : voir l'etape 1 du CRIT. Ajouter a `docs/maintainers.md:22-24` la ligne « recreates an empty `[Unreleased]` above it ».

### [INFO-2] « Settings › Reasoning » : la section n'existe pas, 10 renvois la citent

- **Localisation** :
  - `docs/configuration.md:35`, `:37`, `:117` ;
  - `docs/getting-started.md:113` ;
  - `docs/troubleshooting.md:7`, `:9` ;
  - `SECURITY.md:44` ;
  - `.env.example:89` ;
  - `document-parser/infra/settings.py:62-64` (commentaire) ;
  - `CHANGELOG.md:38` (publie, et repris dans la GitHub Release `v0.7.3`).
- **Statut vs 0.7.3** : **etendue**. Le re-audit ne relevait que `CHANGELOG.md:38`. Les 9 autres renvois existent depuis 0.7.3 (fichiers inchanges) mais n'avaient pas ete releves.
- **Constat** : les reglages de raisonnement sont dans la section **Ask** de Settings. Ils sont montes par `<AccordionSection id="ask" :title="t('settings.ask.title')">` (`frontend/src/features/settings/ui/SettingsPanel.vue:86`). Le titre vaut « Ask » en anglais **et** en francais (`frontend/src/shared/i18n.ts:374`, `:1097`). La cle `settings.reasoning.title` (`i18n.ts:381` « Raisonnement », `:1104` « Reasoning ») n'est plus utilisee nulle part. `docs/getting-started.md:113` dit « section **Reasoning** (**Paramètres**, **Raisonnement** in the French interface) » : aucun des deux libelles n'existe. Deuxieme inexactitude : `docs/configuration.md:35` et `docs/troubleshooting.md:7` disent que, cache, Settings n'affiche rien. En realite, la section **Ask** reste visible, avec la pastille *Hidden/Masqué* et le texte « Start the backend with ASK_MODE=visible… » (`SettingsPanel.vue:87-100`, `i18n.ts:1101-1102`). Le re-audit 0.7.3 avait deja corrige cette affirmation pour le changelog.
- **Regle violee** : hors checklist ponderee (exactitude de la documentation).
- **Remediation** : remplacer partout « **Settings** › **Reasoning** » par « **Settings** › **Ask** ». Ecrire l'etat cache comme il est : « the **Ask** section shows *Hidden* and how to show it ». Corriger le commentaire de `settings.py:62-64`. Optionnel : supprimer la cle morte `settings.reasoning.title`. 10 renvois dans 7 fichiers, environ 20 min.

### [INFO-3] Get started : le parcours Docker Compose d'Ask n'affiche jamais Ask

- **Localisation** : `docs/getting-started.md:105-117`
- **Statut vs 0.7.3** : **nouveau** (fichier inchange depuis 0.7.3, non releve).
- **Constat** : pour Compose, le guide fait construire avec `WITH_REASONING=true docker compose up --build` (`:108`), puis demande d'ouvrir les reglages de raisonnement dans Settings (`:113-115`). Mais compose transmet `ASK_MODE: ${ASK_MODE:-hidden}` (`docker-compose.yml:190`) : sans `ASK_MODE=visible`, la section Ask n'affiche que l'indication (`SettingsPanel.vue:94-100`), et les etapes `:113-115` sont impossibles. La phrase « The **Ask** tab then shows up » (`:117`) est donc fausse en suivant le guide. La variante `docker run` passe bien `-e ASK_MODE=visible` (`:102`). Seule la phrase generale `:88` le mentionne.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : `ASK_MODE=visible WITH_REASONING=true docker compose up --build` a `:108` (compose transmet deja `ASK_MODE`), et « section **Ask** » a `:113`. Environ 5 min.

### [INFO-4] Variables d'environnement : 8 variables lues ne sont documentees nulle part, dont 3 sans effet

- **Localisation** : voir la matrice ci-dessus ; `docs/configuration.md:3` ; `.env.example:117`
- **Statut vs 0.7.3** : **nouveau** (premiere comparaison exhaustive). Le MIN 10.3.2 de 0.7.3 (variables compose) reste corrige.
- **Constat** :
  1. **Effectives, non documentees** :
     - `INSPECT_MODE_ENABLED` (`settings.py:250`). A `false`, il retire le mode Parse : `modeFlags()` (`frontend/src/features/feature-flags/store.ts:216-219`) est lu par le garde du routeur (`frontend/src/app/router/index.ts:52`), qui redirige `/docs/:id` vers la bibliotheque avec `reason=no-mode-enabled`.
     - `MAX_FILE_SIZE` (`settings.py:215`, en octets). Il est passe a Docling (`infra/local_converter.py:116-117`) et peut preter a confusion avec `MAX_FILE_SIZE_MB`.
  2. **Lues mais sans effet** :
     - `LINKED_MODE_ENABLED` (`settings.py:252`). Il est expose dans `/api/health` (`main.py:166`) et enregistre dans le registre des flags (`store.ts:104-107`), mais aucune route ni aucun composant ne consulte `linkedMode`.
     - `MAX_PASTE_IMAGE_SIZE_MB` et `PASTE_ALLOWED_IMAGE_TYPES` (`settings.py:241-242`). Ils sont exposes dans `/api/health` (`main.py:151-154`), mais aucun consommateur n'existe dans `frontend/src` (grep `maxPasteImageSizeMb` / `pasteAllowedImageTypes` : 0). Seul le changelog 0.5.0 les mentionne (`CHANGELOG.md:205`).
  3. **Ingestion (depreciee, retiree en 0.8.0)** : `OPENSEARCH_DEFAULT_LIMIT` (`settings.py:237`), `DEFAULT_EMBEDDER` (`persistence/database.py:249`), `EMBEDDING_BATCH_SIZE` (`embedding-service/main.py:20`, transmise par `docker-compose.yml:84`).
  4. `docs/configuration.md:3` affirme que « the full list is in `document-parser/infra/settings.py` ». C'est faux pour `DEFAULT_EMBEDDER`, `EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE` et `NGINX_MAX_BODY_SIZE`, lues ailleurs.
  5. Nuance de valeur : `.env.example:117` montre `MCP_STUDIO_BASE_URL=http://localhost:3000`, qui est le defaut de compose (`docker-compose.yml:195`), alors que les autres lignes commentees montrent le defaut du code. Ici, le defaut du code est vide (`settings.py:275`). Le commentaire `:116` (« Empty: no deep links ») et `docs/mcp-server.md:46` lèvent l'ambiguite.

  Aucune variable documentee n'est absente du code, et toutes les valeurs par defaut documentees correspondent au code.
- **Regle violee** : hors checklist ponderee.
- **Remediation** :
  - documenter `INSPECT_MODE_ENABLED` et `MAX_FILE_SIZE` dans `docs/configuration.md` (Feature switches, Limits), ou les retirer ;
  - **supprimer** les 3 variables sans effet et leurs champs de `/api/health`. C'est un changement du contrat de `/api/health` : il faut le lister sous `### Removed` du `[0.7.4]` ;
  - laisser les 3 variables d'ingestion partir avec elle en 0.8.0 ;
  - corriger `configuration.md:3` (« most of them are in… »).

### [INFO-5] Pages Architecture et Configuration muettes sur le serveur MCP

- **Localisation** : `docs/architecture.md:65-71`, `:80-87` ; `docs/configuration.md` (0 occurrence de « MCP ») ; `docs/configuration.md:117`
- **Statut vs 0.7.3** : **inchangee** (INFO de l'audit initial et du re-audit 0.7.3), **precisee**.
- **Constat** :
  - Le tableau des prefixes (`architecture.md:80-87`) n'a ni `/mcp` ni `/api/mcp`. Il decrit `/api/config` comme « The reasoning settings » (`:86`), alors qu'il porte aussi `/api/config/mcp` (`document-parser/api/config.py:76-98`). Il decrit `/api/analyses` comme « start, read, delete » (`:83`), sans l'import ni les summaries.
  - Le tableau des couches (`architecture.md:65-71`) n'a pas `mcp_adapter`, alors que `tests/test_architecture.py:197-201` le contraint (pas d'import de `api`, `infra`, `persistence`).
  - `docs/configuration.md` ne renvoie pas vers les 7 `MCP_*` de `docs/mcp-server.md:42-50`.
  - Son entree `DEPLOYMENT_MODE` (`:117`) ne cite que la lecture seule de « Settings › Reasoning ». Elle oublie que `huggingface` coupe aussi le MCP par defaut (`settings.py:256-258`) et met la section MCP en lecture seule (`bootstrap/builder.py:255`).
- **Regle violee** : hors checklist ponderee.
- **Remediation** :
  - ajouter `/mcp`, `/api/mcp` et `/api/config/mcp` au tableau des prefixes, et une ligne `mcp_adapter` au tableau des couches ;
  - ajouter a `configuration.md` une section « MCP server » qui renvoie vers `mcp-server.md#turn-it-on-or-off` ;
  - completer `:117`.

  Environ 20 min.

### [INFO-6] Commentaires de build : « instant first /api/convert » contredit la doc et le code

- **Localisation** : `Dockerfile:74-75` ; `document-parser/Dockerfile:47-48` ; `docker-compose.yml:146-153` ; `.github/workflows/release.yml:56-58`
- **Statut vs 0.7.3** : **nouveau** (non releve).
- **Constat** :
  - Ces commentaires promettent qu'avec `BAKE_MODELS=true`, la premiere conversion de `latest-local` est instantanee. Or aucun code ne pointe Docling vers `/home/appuser/.cache/docling/models` : `grep artifacts_path|DOCLING_ARTIFACTS` donne 0 occurrence dans `document-parser`.
  - La doc dit l'inverse, et elle a raison : `docs/configuration.md:131` (« The backend does not point Docling at this copy yet »), `docs/architecture/huggingface-dependency-map.md:37` (« The copy baked into the image is not read »), `docs/troubleshooting.md:24`, `docs/getting-started.md:21`.
  - Ces commentaires citent aussi une route `/api/convert` qui n'existe pas : les routeurs sont montes en `main.py:103-118`, et une analyse demarre par `POST /api/analyses`.
- **Regle violee** : hors checklist ponderee (commentaires trompeurs pour les mainteneurs).
- **Remediation** : aligner les 4 commentaires sur la doc (« models are baked but not read yet, see huggingface-dependency-map.md »). Ou bien brancher `artifacts_path`, puis mettre a jour les 4 pages de doc.

### [INFO-7] Guide utilisateur : import d'analyse absent, mentions « 0.7.3 » figees

- **Localisation** : `docs/user-guide.md:34-42`, `:111` ; `docs/configuration.md:86`
- **Statut vs 0.7.3** : import d'analyse : **inchangee** (INFO du re-audit 0.7.3 ; la partie changelog « upload dialog » est resolue, `CHANGELOG.md:14` dit « upload area »). Mentions de version : **nouveau**.
- **Constat** :
  - Le guide ne decrit que l'import de PDF. L'import d'une analyse Docling (#359) n'y figure pas : **Import analysis** dans le menu d'actions d'un document (`frontend/src/features/document/ui/DocumentActionsMenu.vue`), et **Upload PDF and Docling analysis** sur Home (`DocumentUpload.vue:38-40`, monte par `HomePage.vue:12`).
  - `user-guide.md:111` (« no default screen reaches them in 0.7.3 ») et `configuration.md:86` (« In 0.7.3 only the older Studio pages use it ») seront perimes au tag 0.7.4.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : une sous-section « Import a Docling analysis » dans `user-guide.md` (environ 10 min). Au gel, remplacer « 0.7.3 » par « 0.7.4 », ou retirer la version de ces deux phrases.

### [INFO-8] CHANGELOG `[0.7.3]` : formulations inexactes restantes

- **Localisation** : `CHANGELOG.md:13`, `:15`, `:21`, `:33`, `:38`
- **Statut vs 0.7.3** : **partiellement resolue**. `:19` a ete corrige par `a43c107` (« **Saved analyses** (#323) »). Le reste est inchange.
- **Constat** :
  - `:13` (« opens the Analysis library ») et `:21` (« found in the Analysis library ») : l'interface dit toujours « Analyses » (`frontend/src/shared/i18n.ts:753`, `:990`).
  - `:15` : « new variable `MCP_MAX_ROUNDS` », alors que les 7 `MCP_*` sont nouvelles en 0.7.3.
  - `:33` : les intermediaires emSign sont attribues a certifi. Le commit `7246efe` les attribuait a uv (GHSA-hq85-5cpj-mr62) et citait GHSA-6q48-6c7w-9gw2 pour certifi. Point non verifiable hors ligne.
  - `:38` : « Settings has no Reasoning section » (voir INFO-2).

  La GitHub Release `v0.7.3` est publiee avec un texte reecrit (voir INFO-10), qui reprend l'erreur de `:38`.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : optionnelle, la version est publiee. Si on la fait, la faire dans le commit de gel 0.7.4 : « the **Analyses** page » a `:13` et `:21`, liste des 7 variables a `:15`, « **Settings › Ask** shows *Hidden* » a `:38`.

### [INFO-9] Statut des design docs : 16 docs livres jamais passes a `Implemented`

- **Localisation** : `docs/design/202-…` a `210-…` (ligne `:7`, `Accepted`) ; `254-docker-slim-post-uv.md:17` (`Draft`) ; `256-doc-tab-chunk-mode-404.md:33` (`Draft`) ; `264-…:33`, `269-…:14`, `279-…:33`, `303-…:33`, `317-…:33` (`Accepted`) ; `363-…:8`, `364-…:8` (`Target milestone: 0.8.0`)
- **Statut vs 0.7.3** : **etendue**. 363, 364 et 329 sont resolus depuis le re-audit. Le detail « Target milestone 0.8.0 » de 363 et 364 reste. Les 16 autres docs n'avaient pas ete releves.
- **Constat** : le cycle de vie versionne, ecrit en tete de chaque doc (par exemple `254-docker-slim-post-uv.md:9`), est « Draft → In review → Accepted → Implemented (or Superseded) ». Le changelog atteste la livraison des 16 docs suivants :
  - 202-210, en 0.6.0 (`CHANGELOG.md:165`) ;
  - 254, en 0.6.2 (`:89-90`) ;
  - 256, 264, 269 et 279, en 0.6.1 (`:116-128`) ;
  - 303 et 317, en 0.7.0 (`:66-68`).

  Ils restent pourtant `Accepted`, ou `Draft` pour 254 et 256. 195 (`Accepted`, 0.5.0) est a verifier : ses variables paste n'ont plus de consommateur (INFO-4). `neo4j-integration.md` et `reasoning-trace.md` n'ont pas de ligne de statut. Correction de l'audit initial 0.7.3 : il citait `docs/design/TEMPLATE.md:9`. Ce fichier est ignore par git (`.gitignore:59`) : c'est un fichier local, non versionne.
- **Regle violee** : hors checklist ponderee. Ces docs ne sont pas publies (`mkdocs.yml:51-54`), l'impact se limite aux mainteneurs.
- **Remediation** : un commit `docs(design): mark shipped designs Implemented` qui met a jour 16 lignes `Status` et 2 lignes `Target milestone`. Environ 10 min.

### [INFO-10] `docs/maintainers.md` : fidele aux workflows, 5 manques

- **Localisation** : `docs/maintainers.md:22-24`, `:37-41`, `:45`, `:68`, `:74`
- **Statut vs 0.7.3** : **nouveau** (premiere verification croisee).
- **Constat** : ce qui est decrit est exact.
  - Verdict en commentaire : `.github/workflows/release-gate.yml:729-737`, `:809`. Une approbation requise sur `main` : protection de branche, `required_approving_review_count: 1` (API GitHub).
  - Images : `release.yml:23`, `:41-44`, `:55`, `:70-73`. Pas de creation de GitHub Release dans `release.yml`.
  - GO CONDITIONAL : `release-gate.yml:733`. Tableau des controles : jobs `:23`, `:59`, `:102`, `:184`, `:226-230`, `:281`, `:335-343`, `:405`, `:509`, `:582` ; tags E2E `:564`, `:650`.
  - Les trois « known gaps » de `:68` sont exacts : `tee` sans `pipefail` (`:86`, `:92`, sans `defaults.run.shell`), `profiles/` ignore par git (`.gitignore:51`), `pip-audit` sans severite (`:134-137`). Les checks CI « Backend tests » et « Frontend tests & build » sont bien requis sur `main`.

  Manques :
  1. **Gel** (`:22-24`) : il ne dit ni de recreer `[Unreleased]` (INFO-1), ni d'aligner `frontend/package-lock.json`.
  2. **Etape 9** (`:45`, « and its milestone on GitHub ») : `release/0.7.4` existe, mais il n'y a pas de jalon `0.7.4` (API `milestones?state=all`).
  3. **Known gaps** (`:68`) : il manque le build `local` du gate, avec seulement `APP_VERSION` (`release-gate.yml:245-252`), alors que `release.yml:70-73` publie avec `WITH_REASONING` et `BAKE_MODELS` (MAJ ouvert de l'audit 10). Il manque aussi le fait que la doc n'est construite par aucun job de PR (INFO-15).
  4. **Hotfix** (`:74`) : l'exemple « `v0.7.4` » est la version de la release en preparation.
  5. **Notes de release** (`:37-41`) : la procedure les tire de la section du changelog. La GitHub Release `v0.7.3` publiee est un texte reecrit : 10 380 caracteres, contre 9 057 pour l'extraction `awk`, avec une autre structure.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : completer `:22-24` (`[Unreleased]`, `npm version … --no-git-tag-version`), `:68` (build `local`, doc). Prendre `v0.7.5` en exemple a `:74`. Ecrire que les notes peuvent etre redigees a partir de la section, ou s'en tenir a l'`awk`. Creer le jalon 0.7.4.

### [INFO-11] Processus : branche de release ambigue, commits directs sur `main`

- **Localisation** : `CONTRIBUTING.md:21`, `:24` ; commits `0465e70`, `1de1929`
- **Statut vs 0.7.3** : **nouveau**.
- **Constat** :
  - `CONTRIBUTING.md:21` : « The current release branch is the highest one in `git branch -r --list 'origin/release/*'` ». Aujourd'hui, c'est `origin/release/0.8.0`, au meme commit `1de1929` que `release/0.7.4`. Un contributeur qui suit la regle cible 0.8.0, et non la release qualite 0.7.4.
  - Le meme paragraphe dit que « `main` only receives releases and hotfixes ». Or les deux commits README de 0.7.4 ont ete pousses directement sur `main`, sans PR (API GitHub `commits/{sha}/pulls` : vide), avec `[skip ci]`. Ni `ci.yml` ni `docs.yml` n'a tourne sur `1de1929`. Seul « Code Quality: Push on main » a tourne.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : dire explicitement quelle branche reçoit les PR de la release qualite (une ligne dans `CONTRIBUTING.md`), ou ne creer `release/0.8.0` qu'apres le merge de 0.7.4. Faire passer les changements de doc par la branche de release, ou ecrire l'exception « docs-only » dans `CONTRIBUTING.md`.

### [INFO-12] Jalons GitHub incoherents avec le contenu livre

- **Localisation** : GitHub, API `milestones?state=all` et `issues/{n}`
- **Statut vs 0.7.3** : **inchangee**, plus un nouveau point (jalon 0.7.4 absent).
- **Constat** :
  - Le jalon `0.7.3` (#17) est toujours ouvert, avec #348, #349 et #358 ouverts (reportes).
  - #327 et #363 sont OPEN sous `0.8.0` ; #364 est CLOSED sous `0.8.0` ; #329 est OPEN sous `0.8.0`, alors que son design doc dit « Superseded by #363 » ; #361 est OPEN sans jalon.
  - Nouveau : pas de jalon `0.7.4`.
  - Les jalons de versions publiees `0.6.2` (#15, 1 issue ouverte), `0.7.0` (#10, 3 ouvertes) et `0.7.2` (#16, 1 ouverte) sont toujours ouverts.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : creer `0.7.4` et y rattacher les issues de remediation. Deplacer #348, #349 et #358. Rattacher #327, #363 et #364 a 0.7.3 et fermer #327 et #363. Fermer #329. Fermer les jalons publies apres avoir deplace leurs issues ouvertes.

### [INFO-13] Versions secondaires

- **Localisation** : `document-parser/pyproject.toml:3`, `embedding-service/pyproject.toml:3` (`0.0.0`) ; `e2e/api/pom.xml:10`, `e2e/ui/pom.xml:10` (`0.3.1`)
- **Statut vs 0.7.3** : **inchangee** (le lockfile frontend, aligne en 0.7.3, est a re-bumper avec `package.json`, voir MAJ).
- **Constat** : la version servie vient de `APP_VERSION` (`settings.py:204`), injectee depuis le tag (`release.yml:71`). `docs/maintainers.md` n'explique toujours pas le placeholder `0.0.0`.
- **Regle violee** : hors checklist ponderee.
- **Remediation** : une ligne dans `docs/maintainers.md`.

### [INFO-14] SemVer : 0.7.4 en patch, a surveiller pendant la remediation

- **Localisation** : `CHANGELOG.md:5`
- **Statut vs 0.7.3** : **inchangee** (note SemVer de 0.7.3), contexte nouveau.
- **Constat** : un patch convient a une release de correctifs. Si la remediation ajoute de l'API publique, retire des champs de `/api/health` (INFO-4), ou change un defaut (par exemple une authentification du MCP), SemVer 2.0.0 §7 demanderait un bump mineur. 11.2.2 resterait conforme (clause §4 en 0.y.z, precedent 0.6.1, 0.6.2 et 0.7.3), mais la rupture devrait aller sous `### BREAKING CHANGES` (11.1.3). La regle n'est toujours pas ecrite dans `docs/maintainers.md`.
- **Regle violee** : item 11.2.2 conforme ; simple note.
- **Remediation** : decider au gel. Ecrire la regle (patch = correctifs ; mineur = nouvelle API, depreciation ou rupture).

### [INFO-15] Construction et liens de la doc

- **Localisation** : `.github/workflows/docs.yml:3-9`, `:38` ; `.github/PULL_REQUEST_TEMPLATE.md:22` ; `docs/design/329-mcp-investigation-journal-navigation-tree.md:592`
- **Statut vs 0.7.3** : **nouveau**.
- **Constat** :
  1. `mkdocs build --strict` ne tourne que dans `docs.yml`, sur push vers `main` (`:3-9`). Ni `ci.yml` ni `release-gate.yml` ne construisent la doc : une page cassee sur `release/0.7.4` n'est detectee qu'apres le merge, au deploiement. `pip install mkdocs-material` n'est pas epingle (`:38`) ; le re-audit 0.7.3 notait deja le bandeau « MkDocs 2.0 » de Material.
  2. Liens relatifs casses, hors site :
     - `.github/PULL_REQUEST_TEMPLATE.md:22` pointe vers `docs/git-workflow/commit-conventions.md`, resolu depuis `.github/` (fichier absent). Dans le corps d'une PR, un lien relatif ne se resout pas non plus. Le bon lien est dans `CONTRIBUTING.md:105`.
     - `docs/design/329-…:592` pointe vers `../mcp-server.md#investigations` : l'ancre a disparu avec le journal (#363).
  3. Pages publiees : 0 lien relatif casse, 0 lien absolu GitHub casse. Les exclusions `mkdocs.yml:55-56` visent des fichiers locaux ignores par git (`.gitignore:58`, `:60`) : c'est coherent.
- **Regle violee** : hors checklist ponderee.
- **Remediation** :
  - ajouter un job `mkdocs build --strict` a `ci.yml` sur les PR vers `release/**` et `main`, avec `mkdocs-material` epingle ;
  - lien absolu `https://github.com/scub-france/Docling-Studio/blob/main/docs/git-workflow/commit-conventions.md` dans le modele de PR.

### [INFO-16] Docstrings : modules documentes, 9 routes actives sans description

- **Localisation** : `document-parser/api/config.py:32`, `:37`, `:56`, `:65`, `:76`, `:81`, `:98` ; `document-parser/api/mcp.py:20` ; `document-parser/api/reasoning.py:29`
- **Statut vs 0.7.3** : **nouveau** (premiere mesure).
- **Constat** :
  - 112 des 113 modules du backend ont une docstring de module (seul `document-parser/conftest.py` n'en a pas).
  - 349 des 471 definitions publiques de premier niveau en ont une. Il manque surtout les schemas Pydantic (`api/schemas.py`), les dependances FastAPI (`api/deps.py`) et des exceptions, ce que permet la regle du projet (« Write a docstring only when the code is not obvious », `docs/architecture/coding-standards.md:33`).
  - En revanche, 17 des 51 routes n'ont ni docstring ni `summary`/`description` : Swagger (`/docs`, signale par `docs/troubleshooting.md:53-55` et `CONTRIBUTING.md:64`) les affiche sans description. 8 sont depreciees (`api/stores.py:81-189`, `api/graph.py:66`). Les 9 autres sont actives : la config reasoning et MCP, `GET /api/mcp/server` (nouvelle en 0.7.3) et Ask.
- **Regle violee** : hors checklist ponderee (conforme a `coding-standards.md:33`).
- **Remediation** : une docstring d'une ligne sur ces 9 routes. Environ 10 min.

---

## Suivi des ecarts precedents

| Ecart (rapport d'origine) | Statut 0.7.4 | Preuve |
|---------------------------|--------------|--------|
| [CRIT] 11.1.1 changelog non fige (0.7.3 initial) | Resolu en 0.7.3, **reapparu** (nouvelle release, pre-gel) | `CHANGELOG.md:7` |
| [CRIT] 11.1.3 `ASK_MODE` hors BREAKING (0.7.3 initial) | Resolu, maintenu | `CHANGELOG.md:36-38` |
| [MAJ] 11.1.2 #359/#323 absents (0.7.3 initial) | Resolu, maintenu | `CHANGELOG.md:14`, `:19` |
| [MAJ] 11.2.1 version front (0.7.3 initial) | Resolu en 0.7.3, **reapparu** (pre-gel) | `frontend/package.json:3` |
| [INFO] `.env.example` et `BATCH_PAGE_SIZE` | Resolue, maintenue | `.env.example:10-13` |
| [INFO] Statut des design docs 363/364/329 | Resolue ; « Target milestone 0.8.0 » reste ; **etendue** a 16 autres docs | INFO-9 |
| [INFO] Jalons GitHub | Inchangee, plus jalon 0.7.4 absent | INFO-12 |
| [INFO] Versions secondaires | Inchangee (lockfile aligne en 0.7.3) | INFO-13 |
| [INFO] SemVer patch avec API | Inchangee | INFO-14 |
| [INFO] Architecture/Configuration muettes sur MCP | Inchangee, precisee | INFO-5 |
| [INFO] 4 des 7 variables `MCP_*` nommees | Inchangee | INFO-8, `CHANGELOG.md:15` |
| [INFO] « Analysis library » (`CHANGELOG.md:19`) | **Resolue** a `:19` (`a43c107`) ; reste `:13`, `:21` | INFO-8 |
| [INFO] Import combine (« upload dialog ») | **Resolue** dans le changelog (`:14`) ; guide utilisateur toujours muet | INFO-7 |
| [INFO] Puce BREAKING « Reasoning » | Inchangee, **etendue** a 9 autres renvois (6 fichiers) | INFO-2 |
| [INFO] `[Unreleased]` absent | Inchangee, contexte aggrave | INFO-1 |
| [INFO] Security certifi/uv | Inchangee | INFO-8 |
| Hors audit 11 (08) : « localhost only » | **Resolue** | `README.md:31` ; `frontend/src/shared/i18n.ts:415-416`, `:1137-1138` |
| Date du tag vs `CHANGELOG.md:7` (re-audit) | **OK** : tag pose le 2026-11-02 | `git log -1 v0.7.3` |

---

## Delta vs 0.7.3

| Item | 0.7.3 initial | 0.7.3 re-audit (base) | 0.7.4 | Evolution |
|------|---------------|-----------------------|-------|-----------|
| 11.1.1 Changelog fige | CRIT | OK | **CRIT** | gel pas encore fait (pre-gel) |
| 11.1.2 Changements listes | MAJ | OK | OK | = (rien de significatif depuis `v0.7.3`) |
| 11.1.3 Breaking identifies | CRIT | OK | OK | = |
| 11.1.4 Keep a Changelog | OK | OK | OK | = (INFO-1) |
| 11.2.1 Version front | MAJ | OK | **MAJ** | bump pas encore fait (pre-gel) |
| 11.2.2 SemVer | OK | OK | OK | = |
| 11.3.1 TODO/FIXME | OK | OK | OK | = (0) |
| 11.3.2 console.log | OK | OK | OK | = |
| 11.3.3 print() | OK | OK | OK | = |
| **Score** | 44 | **100** | **72** | **−28 vs re-audit** ; identique au premier audit 0.7.0 au meme stade (72) |

INFO : 10 au re-audit 0.7.3. Aucune n'est entierement resolue ; 2 le sont en partie (« Analysis library », import combine). Les 10 sont reprises dans INFO-1, 2, 5, 7, 8, 12, 13 et 14 (INFO-8 regroupe les trois points du changelog `[0.7.3]`). 16 INFO aujourd'hui, dont 7 nouvelles (INFO-3, 4, 6, 10, 11, 15, 16), plus la partie « mentions 0.7.3 » d'INFO-7. Deux INFO sont etendues (INFO-2, INFO-9 ; INFO-9 reprend une INFO de l'audit initial 0.7.3, resolue au re-audit pour 363/364/329).

---

## Contenu attendu du commit de gel `chore(release): freeze [0.7.4]`

Prerequis, **des maintenant** : un commit `docs(changelog): open [Unreleased]` qui ajoute `## [Unreleased]` au-dessus de `CHANGELOG.md:7`. Chaque PR de remediation y ajoute son entree.

Au gel, sur `release/0.7.4` (`docs/maintainers.md:22`), un seul commit :

1. **`CHANGELOG.md`** : renommer `## [Unreleased]` en `## [0.7.4] - <date du tag>`, puis recreer au-dessus un `## [Unreleased]` vide. La section contient :
   - une entree par PR de remediation significative, dans les groupes standards :
     - `### Fixed` : correctifs, et corrections de doc visibles des utilisateurs (par exemple INFO-2 et INFO-3) ;
     - `### Changed` ;
     - `### Security` : dependances, suppressions Trivy (rappel : Pillow expire le 2026-12-31) ;
     - `### Removed` : par exemple les variables sans effet d'INFO-4 et leurs champs de `/api/health`.

     Les refactorings internes des audits 01 a 06 et 12 tiennent en une puce groupee, avec leurs references ;
   - **`### BREAKING CHANGES`** pour tout ce qui oblige l'operateur a agir : authentification MCP activee par defaut, defaut modifie, variable retiree ou renommee, contrat de `/api/health` modifie. Sans cela, 11.1.3 redevient CRIT ;
   - aucune puce pour un sujet non merge.
2. **Version** : `cd frontend && npm version 0.7.4 --no-git-tag-version`, qui passe `package.json:3` et `package-lock.json:3`, `:9` a `0.7.4`.
3. **Mentions de version** dans les pages publiees : `docs/user-guide.md:111` et `docs/configuration.md:86` (« 0.7.3 »).
4. Optionnel, dans le meme commit :
   - corrections du `[0.7.3]` (INFO-8) ;
   - statut `Implemented` des design docs livres en 0.7.4 ;
   - mise a jour de `docs/maintainers.md:22-24` (INFO-1, INFO-10).

Controle avant la PR vers `main` :
- `awk '/^## \[0.7.4\]/{f=1; next} /^## \[/{f=0} f' CHANGELOG.md` n'est pas vide ;
- `grep '"version"' frontend/package.json` donne `0.7.4` ;
- `grep -n "Unreleased" CHANGELOG.md` trouve une seule section, vide.

**Projection** :
- 11.1.1 seul : +16,7 pts, soit 89 ;
- 11.2.1 seul : +11,1 pts, soit 83 ;
- le commit de gel complet : **18/18 = 100**, a condition que 11.1.2 et 11.1.3 tiennent.

Chaque PR significative sans entree coute 11 points (11.1.2, MAJ). Une rupture non classee coute 17 points et un CRIT (11.1.3).

---

## Points positifs

- **Code propre** : 0 TODO, FIXME, HACK ou XXX (backend, frontend, embedding-service, e2e, `.github`). 0 `console.log` ou `console.debug`. 0 `print()` executable. Les `console.warn`/`error` restants suivent la regle versionnee (`frontend/eslint.config.js:20`).
- **Gel 0.7.3 propre** : le tag `v0.7.3` (`2b4ef25`) a la date de `CHANGELOG.md:7`, la GitHub Release est publiee, `package.json` et le lockfile ont ete alignes. Les corrections de suivi ont ete appliquees avant le tag : `a43c107` pour #323 et #359, `6cb61d3` pour « localhost only » dans `README.md:31` et le libelle Settings.
- **Variables d'environnement fiables** : sur 49 variables lues, aucune variable documentee n'est absente du code. Toutes les valeurs par defaut documentees sont exactes. Le MCP a sa table complete avec le defaut compose (`docs/mcp-server.md:42-50`).
- **`docs/maintainers.md` fidele aux workflows** : gate, `release.yml`, protection de `main` (1 approbation, checks requis). Les « known gaps » qu'il declare sont exacts.
- **Liens sains sur le site** : 0 lien casse dans les pages publiees, 0 lien absolu vers le depot casse. `docs.yml` est vert sur `v0.7.3`.
- **Documentation du code** : 112 des 113 modules du backend ont une docstring de module.
- **README a jour** : il presente le MCP sans promesse trompeuse (`README.md:31`), avec un GIF de demo actuel (`README.md:12`).

---

## Verdict partiel : NO-GO (stade pre-gel, attendu)

Il reste un ecart `[CRIT]` : 11.1.1, pas de section `[0.7.4] - YYYY-MM-DD`. La regle absolue du master s'applique : **NO-GO**, quel que soit le score (72/100). Ce resultat est attendu a l'ouverture d'une release. Le CRIT et le MAJ 11.2.1 (`frontend/package.json` en 0.7.3) se corrigent dans le seul commit de gel `chore(release): freeze [0.7.4]`, sans toucher au code, ce qui donnerait 100/100 et GO. Une condition prealable, a remplir **des maintenant** : rouvrir `## [Unreleased]`, pour que les PR de la release qualite y consignent leurs changements. Sinon, 11.1.2 et 11.1.3 risquent de tomber au gel.

Les 16 INFO ne bloquent pas. Trois meritent d'entrer dans la release qualite, parce qu'elles trompent l'utilisateur :
- INFO-2 : « Settings › Reasoning », 10 renvois dans 7 fichiers ;
- INFO-3 : le parcours Compose d'Ask ne montre jamais Ask ;
- INFO-4 : 3 variables lues mais sans effet, et 2 variables effectives non documentees.
