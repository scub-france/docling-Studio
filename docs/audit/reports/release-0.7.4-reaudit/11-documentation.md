# Rapport d'audit : Documentation & Changelog (re-audit)

**Release** : 0.7.4 (re-audit apres remediation)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` @ `a4d9679` (100 commits de remediation depuis `e6047c2`)

Baseline : `reports/release-0.7.4/11-documentation.md` (72/100 pre-gel, 1 CRIT + 1 MAJ + 16 INFO, code audite `1de1929`, rapport commite en `e6047c2`). Perimetre identique : `CHANGELOG.md`, `frontend/package.json`, `docs/`, `SECURITY.md`, `CONTRIBUTING.md`, `.env.example`, code source.

**Lecture des items.** C'est la meme qu'en 0.7.4 et qu'en 0.7.3. Pour 11.1.3, le rapport 0.7.4 range sous `### BREAKING CHANGES` « tout ce qui oblige l'operateur a agir ». La convention du projet (`CHANGELOG.md`, 0.6.1 et 0.7.3) ajoute « … pour garder le comportement precedent ». Un changement decrit ailleurs dans le changelog, meme avec la marche a suivre, reste non conforme s'il n'est pas classe en rupture : c'est le CRIT `ASK_MODE` de l'audit initial 0.7.3. Cette lecture fait tomber 11.1.3 sur un point (CRIT ci-dessous). Le score qu'on obtiendrait si le mainteneur juge ce point non cassant est aussi donne.

**Gel non fait, volontairement.** Le commit `chore(release): freeze [0.7.4]` (`docs/maintainers.md:22-24`) est l'etape du mainteneur au moment du tag. Ce rapport donne le score **actuel** et le score **apres le commit de gel**.

Methode :
- `[Unreleased]` lu puce par puce et confronte au code a `a4d9679` (settings, routes, nginx, workflows, `package-lock.json`, `pyproject.toml`). Les 100 commits `e6047c2..HEAD` ont ete relus pour trouver un changement significatif absent.
- Changements de comportement : avant / apres compare sur `e6047c2` et `HEAD` (nginx, uvicorn 0.52.4 du lock, `infra/rate_limiter.py`, persistance, stores).
- Variables d'environnement : liste extraite du code (`os.environ.get`, helpers de `infra/settings.py`, `persistence/database.py`, `embedding-service/main.py`), puis croisee avec `docs/configuration.md`, `docs/mcp-server.md` et `.env.example`.
- Glossaire : chaque nom de code cite est cherche dans `document-parser/`.
- `git grep` sur les fichiers suivis seulement (les worktrees `.claude/worktrees/` sont exclus).
- Jalons et PR : API GitHub (`gh api`).
- `mkdocs build --strict` non relance : le coordinateur l'a passe sur HEAD (OK).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 6 / 9 |
| Score | **56 / 100** (72 si le point X-Forwarded-For est juge non cassant) |
| Ecarts CRITICAL | 2 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 0 |
| Ecarts INFO | 11 |

Ponderation : items conformes = 10 pts / 18 pts totaux -> 55,6 -> **56/100**.
Items non conformes : 11.1.1 (poids 3, pre-gel), 11.1.3 (poids 3), 11.2.1 (poids 2, pre-gel).

### Score apres le commit de gel

| Scenario | 11.1.1 | 11.1.3 | 11.2.1 | Score | Verdict |
|----------|--------|--------|--------|-------|---------|
| Actuel (pre-gel) | NON | NON | NON | **56** | NO-GO (2 CRIT) |
| Gel tel que `docs/maintainers.md:22-24` le decrit (renommage `[Unreleased]` -> `[0.7.4] - date`, nouvel `[Unreleased]` vide, `npm version 0.7.4 --no-git-tag-version`) | OUI | **NON** | OUI | **83** | **NO-GO** (1 CRIT) |
| Gel + une puce `X-Forwarded-For` / `FORWARDED_ALLOW_IPS` sous `### BREAKING CHANGES` | OUI | OUI | OUI | **100** | GO |
| Lecture alternative (X-Forwarded-For non cassant) : actuel / apres gel | NON / OUI | OUI | NON / OUI | 72 / 100 | NO-GO / GO |

Le 100 suppose que 11.1.2 tienne au gel : voir INFO-N4, sur la PR #371 qui vise `release/0.7.4`.

---

## Grille item par item

| # | Item | Poids | 0.7.4 -> re-audit | Preuve |
|---|------|-------|-------------------|--------|
| 11.1.1 | `[Unreleased]` renommee en `[X.Y.Z] - YYYY-MM-DD` | 3 | NON -> **NON** (pre-gel) | `CHANGELOG.md:7` : `## [Unreleased]`, rempli (`:9-57`), pas encore renomme |
| 11.1.2 | Toutes les modifications significatives listees | 2 | OUI -> **OUI** | 100 commits relus ; chaque changement visible (securite, comportement, API, CI, doc) a sa puce, et chaque puce verifiee correspond au code (tableau plus bas) |
| 11.1.3 | Breaking changes clairement identifies | 3 | OUI -> **NON** | `LLM_PROVIDER_TYPE` et stores en lecture seule sont bien classes (`CHANGELOG.md:54-57`), mais le changement `X-Forwarded-For` (`:15`) oblige un operateur derriere un reverse proxy a agir, et il est range sous `### Security` |
| 11.1.4 | Format Keep a Changelog | 1 | OUI -> **OUI** | `[Unreleased]` en tete (`:7`), groupes standards `Security` / `Changed` / `Fixed` / `Removed` (`:11`, `:20`, `:36`, `:49`) plus `BREAKING CHANGES` (`:54`), convention du projet |
| 11.2.1 | `frontend/package.json` a la version X.Y.Z | 2 | NON -> **NON** (pre-gel) | `frontend/package.json:3` = `0.7.3` ; lockfile `frontend/package-lock.json:3`, `:9` = `0.7.3` |
| 11.2.2 | Version conforme au SemVer | 2 | OUI -> **OUI** | `0.7.3 -> 0.7.4` : patch en 0.y.z (SemVer §4), precedents 0.6.1, 0.6.2, 0.7.3. Voir INFO-14 |
| 11.3.1 | Pas de TODO/FIXME orphelin | 1 | OUI -> **OUI** | `git grep -E "TODO|FIXME|HACK|XXX"` : 0 dans `document-parser`, `frontend/src`, `embedding-service`, `e2e`, `.github` |
| 11.3.2 | Pas de `console.log` de debug | 2 | OUI -> **OUI** | 0 `console.log` / `console.debug` ; 2 `console.warn` en `catch` (`frontend/src/features/analysis/store.ts:131`, `:190`) ; 30 `console.error` ; regle `frontend/eslint.config.js:20` |
| 11.3.3 | Pas de `print()` de debug | 2 | OUI -> **OUI** | 0 `print(` executable ; 4 en commentaire ou docstring (`mcp_stdio.py:25`, `infra/settings.py:57`, `infra/secrets/fernet_box.py:46`, `:133`) |

Calcul actuel : (2 + 1 + 2 + 1 + 2 + 2) / 18 = 10 / 18 = **55,6 -> 56**.

---

## Verification du `[Unreleased]` contre le code

| Puce (`CHANGELOG.md`) | Verifie dans le code | Exact ? |
|------------------------|----------------------|---------|
| `:13` Import borne : `MAX_IMPORT_TABLE_CELLS` (defaut 100 000, `0` = pas de limite), 400 avant export ; 413 au-dela de 200 Mo sur `/api/analyses` | `infra/settings.py:40`, `:155`, `:257` ; `infra/docling_importer.py:58-76` ; `api/analyses.py:31-82` (`_BoundedBodyRoute`) | Oui. Nuance : « as the bundled nginx already did » n'est vrai qu'avec le defaut `NGINX_MAX_BODY_SIZE=200M`. Le plafond backend est code en dur (INFO-N3) |
| `:14` URI des stores filtrees (422), test de connexion refuse, message generique | `services/store_service.py:323-400` ; `infra/ssrf_guard.py` | Oui |
| `:15` `X-Forwarded-For` : nginx ajoute l'adresse du pair, uvicorn prend l'adresse non approuvee la plus a droite ; derriere un reverse proxy, `FORWARDED_ALLOW_IPS` | `nginx.conf.template:47-56`, `:71` ; `frontend/nginx.conf.template:47-56` ; `Dockerfile:65` (uvicorn sans `--forwarded-allow-ips`, defaut `127.0.0.1`, uvicorn 0.52.4 `uv.lock:3887`) ; `infra/rate_limiter.py:71` | Oui, mais c'est une rupture non classee (CRIT ci-dessous) |
| `:16` Convertisseur local reduit au PDF | `infra/local_converter.py:76` | Oui |
| `:17` npm audit 7 HIGH -> 0 (dompurify 3.4.17, vue 3.5.44, lodash 4.18.1, nanoid 3.3.20, postcss 8.5.32, source-map-js 1.2.2) ; vite 6.4.1 inchange | `frontend/package-lock.json` | Oui, les 7 versions concordent |
| `:18` torch / torchvision bornes | `document-parser/pyproject.toml:44-45` | Oui |
| `:22-23` chunkset en une transaction, historique compte en SQLite | `persistence/chunk_repo.py`, `persistence/document_version_repo.py` (audit 12) | Oui (chiffres de perf non re-mesures ici) |
| `:24` pages rendues en place ; comptage par pdfium au lieu de `pdfinfo` | `infra/pdf_inspector.py`, `infra/page_raster.py` ; `git grep pdfinfo -- document-parser` hors tests : 0 | Oui |
| `:25` `Cache-Control` de `/preview` et `/pages`, `/assets/` immuable, gzip, `/assets` manquant -> 404 | `api/documents.py:33`, `:176`, `:195` ; `nginx.conf.template:29-45` | Oui |
| `:26` listes d'analyses chargees depuis les summaries | `features/history/api.ts:9`, `features/analysis/store.ts:59`, `pages/DocsLibraryPage.logic.ts:34-44` | Oui (meme limite de 200 lignes que la liste complete, `persistence/analysis_repo.py:60`, `:70`) |
| `:27-28` plafond de rounds MCP enonce une fois ; carte des sources lit le parse une fois | `mcp_adapter/server.py`, `services/source_service.py` (audits 03 et 12) | Oui |
| `:29` logo 57 ko, favicon | `frontend/index.html:7` | Oui |
| `:30` config des stores et noeuds du graphe types ; cles non lues plus renvoyees | `api/graph.py` (`GraphNode`, `GraphProvenance`), `api/schemas.py` | Oui (INFO-N3) |
| `:31-32` gate : image `local` avec Ask, smoke sans reseau, audit Python `local` + `reasoning` ; CI : `ruff format`, Prettier, `@critical` une fois, `.dockerignore` | `release-gate.yml:132`, `:272`, `:378-419`, `:748` ; `ci.yml:47`, `:75`, `:226` ; `frontend/.dockerignore` | Oui |
| `:33` erreurs de service unifiees, statuts inchanges | `api/errors.py`, `services/errors.py`, `main.py:90` | Oui pour les statuts verifies (403 config, 404/400 import) ; verification exhaustive laissee aux audits 05/07 |
| `:34` documentation | voir « Coherence docs <-> code » | Oui |
| `:38-48` Fixed (transactions, dates UTC et date vide = erreur, niveau de titre, verrou pdfium, borne `MCP_MAX_READ_TOKENS`, couleurs, carte de citation en francais, gate, Karate, doc) | `persistence/timestamps.py:29-38` ; `infra/settings.py:117`, `:137`, `:212-234` ; `frontend/src/app/App.vue` (`--on-accent`) ; `mcp_adapter/citation_app.html` ; `release-gate.yml:87`, `:94`, `:537` | Oui |
| `:51` `LLM_PROVIDER_TYPE` n'est plus lu ; l'API d'admin renvoie `providerType: "ollama"` | `infra/settings.py:63-64` ; `tests/test_settings.py:187-191` | Oui |
| `:52` quatre composants Vue supprimes | `git diff --name-status` : `IngestLaunchDialog.vue`, `DocChunkTab.vue`, `HistoryDrawer.vue`, `InspectResultTabs.vue` en `D` | Oui |
| `:56` BREAKING `LLM_PROVIDER_TYPE` ignore | `bootstrap/factories.py` (plus de test du type) | Oui |
| `:57` BREAKING stores en lecture seule sur HF (403, test refuse) | `bootstrap/builder.py:162-165` ; `services/store_service.py:144`, `:344-346`, `:378-379` | Oui |

Changements significatifs sans puce : **aucun**. Les commits sans puce propre sont internes : `cba03bf`, `f6bced3`, `155294a`, `6daaa7c` (le contrat MCP `hops` / `hop_id` est garde, `mcp_adapter/sources_wire.py`), `44d0e2f`, `d094673`, `30d8ecb` (format de date de la page d'analyse), `23fb05e`. Ils sont couverts par la puce groupee « Internals » (`:33`).

---

## Ecarts constates

### [CRIT] Le changement `X-Forwarded-For` oblige les operateurs derriere un reverse proxy a agir, mais il n'est pas classe en rupture

- **Localisation** : `CHANGELOG.md:15` (puce rangee sous `### Security`, `:11`) ; section `### BREAKING CHANGES` `CHANGELOG.md:54-57` ; code : `nginx.conf.template:47-56`, `:71`, `frontend/nginx.conf.template:47-56`, `Dockerfile:65`, `document-parser/infra/rate_limiter.py:71` ; doc : `docs/configuration.md:33-34`
- **Statut vs 0.7.4** : **nouveau**, introduit par la remediation (`7f126e7`, `ee94598`).
- **Constat** :
  - **Avant** (`e6047c2:nginx.conf.template:20`, `:33`) : nginx ne posait que `X-Real-IP` et transmettait tel quel le `X-Forwarded-For` recu. uvicorn, lance sans `--forwarded-allow-ips` (`Dockerfile:65`), fait confiance a `127.0.0.1`, donc a nginx. Il lisait cet en-tete, et le limiteur compte par `request.client.host` (`infra/rate_limiter.py:71`). Derriere le reverse proxy d'un operateur (TLS, Traefik, nginx, Caddy…), qui pose `X-Forwarded-For: <client>`, chaque client avait donc son propre compteur `RATE_LIMIT_RPM`. C'est ce que permettait la faille corrigee.
  - **Apres** : nginx ajoute l'adresse du pair (`$proxy_add_x_forwarded_for`, `nginx.conf.template:56`). L'en-tete devient `<client>, <proxy>`, et uvicorn 0.52.4 retient l'adresse non approuvee la plus a droite, celle du proxy. **Tous les utilisateurs partagent alors un seul compteur** (100 requetes/min par defaut), tant que l'operateur n'ajoute pas son proxy a `FORWARDED_ALLOW_IPS`. La doc le confirme : « Behind your own reverse proxy, add its address so the rate limit counts per client instead of per proxy » (`docs/configuration.md:34`). Un onglet qui suit des analyses en lot fait deja environ 20 requetes/min (rafraichissement toutes les 3 s, `CHANGELOG.md:65`). Quelques utilisateurs suffisent donc a declencher des 429 pour tous.
  - Un Space Hugging Face (`DEPLOYMENT_MODE=huggingface`) tourne derriere le proxy de Hugging Face : il est vraisemblablement concerne. Sa configuration n'est pas dans le depot, et ce point n'est pas verifiable.
  - Le changelog decrit bien le changement et la marche a suivre (`:15`). Mais il le range sous `### Security`. Un operateur qui lit `### BREAKING CHANGES` avant de mettre a jour ne le voit pas. C'est le cas exact du CRIT `ASK_MODE` de l'audit initial 0.7.3 : changement decrit, remede donne (« Set `ASK_MODE=visible` to keep Ask as before »), mais hors section de rupture.
  - Le correctif lui-meme est bon. Il ferme une faille, et en image unique exposee directement, il corrige meme un compteur partage : sans proxy ni en-tete, tous les clients etaient `127.0.0.1`. Seul le classement est en cause.
- **Regle violee** : item 11.1.3, poids 3. Selon les conventions du projet (`CHANGELOG.md`, 0.6.1 et 0.7.3), un changement qui oblige l'operateur a agir pour garder le comportement precedent va dans `### BREAKING CHANGES`.
- **Remediation** : dans le commit de gel, ajouter sous `### BREAKING CHANGES` :
  ```markdown
  - **Rate limit behind a reverse proxy**: Studio now counts each client by the address its own nginx sees. Behind your own reverse proxy (TLS, Traefik, a Hugging Face Space…), every user now shares the proxy's `RATE_LIMIT_RPM` budget until you add the proxy's address to `FORWARDED_ALLOW_IPS` (never `*`). See [Configuration](docs/configuration.md#limits).
  ```
  Mettre aussi a jour `docs/troubleshooting.md:31` (INFO-N1). 5 min.
- **Lecture alternative** : si le mainteneur juge qu'un correctif de securite documente avec son remede sous `### Security` suffit, 11.1.3 est conforme. Le score est alors de 72 aujourd'hui et de 100 apres le gel.

### [CRIT] Pas de section `[0.7.4] - YYYY-MM-DD` dans le changelog (pre-gel)

- **Localisation** : `CHANGELOG.md:7`
- **Statut vs 0.7.4** : **partiellement corrige**. La moitie « des maintenant » de la remediation 0.7.4 est faite : `## [Unreleased]` est rouvert (`70cc43c`) et alimente au fil des commits (`a4d9679`). Le renommage, etape du gel, ne l'est pas, volontairement. L'extraction `awk '/^## \[0.7.4\]/…'` (`docs/maintainers.md:40`) renverrait aujourd'hui un fichier vide.
- **Regle violee** : item 11.1.1, poids 3.
- **Remediation** : commit `chore(release): freeze [0.7.4]` : renommer `## [Unreleased]` en `## [0.7.4] - <date du tag>` et recreer au-dessus un `## [Unreleased]` vide, comme le dit maintenant `docs/maintainers.md:23`. 5 min.

### [MAJ] `frontend/package.json` reste en 0.7.3 (pre-gel)

- **Localisation** : `frontend/package.json:3` ; `frontend/package-lock.json:3`, `:9`
- **Statut vs 0.7.4** : **inchange** (etape du gel). La procedure dit maintenant comment aligner les deux fichiers d'un coup (`docs/maintainers.md:24`).
- **Regle violee** : item 11.2.1, poids 2.
- **Remediation** : `cd frontend && npm version 0.7.4 --no-git-tag-version` dans le commit de gel. 2 min.

### [INFO-N1] Rate limit : `troubleshooting` contredit le correctif, et `FORWARDED_ALLOW_IPS` reste difficile a appliquer avec Compose

- **Localisation** : `docs/troubleshooting.md:29-31` ; `docs/configuration.md:6`, `:33-34` ; `docker-compose.yml` (pas de `FORWARDED_ALLOW_IPS`) ; `.env.example` (absente)
- **Statut** : **nouveau**, introduit par la remediation (`troubleshooting.md` n'a ete modifie que pour Ask).
- **Constat** :
  - `troubleshooting.md:31` dit toujours « Behind the bundled nginx, all users share this one limit. Raise it, or set `0` ». Ce n'est plus vrai dans l'image unique (chaque client est compte a part). La page ne cite pas `FORWARDED_ALLOW_IPS`, qui est justement le remede aux 429 apres mise a jour derriere un reverse proxy.
  - Avec Compose, `configuration.md:33` dit que tous les utilisateurs partagent la limite « until `FORWARDED_ALLOW_IPS` names it ». C'etait deja le cas avant, ce n'est pas une regression. Mais `docker-compose.yml` ne transmet pas la variable, et l'adresse du conteneur nginx n'est pas fixe. Le lecteur doit deviner qu'il faut ajouter la variable sous `environment` (regle generale `:6`) et y mettre le sous-reseau du reseau Compose, ce qu'uvicorn 0.52 accepte.
- **Remediation** : reecrire `troubleshooting.md:31` (image unique : par client ; derriere un proxy ou avec Compose : `FORWARDED_ALLOW_IPS`) ; transmettre `FORWARDED_ALLOW_IPS: ${FORWARDED_ALLOW_IPS:-127.0.0.1}` dans les deux fichiers Compose, avec un exemple de sous-reseau dans `configuration.md:34`. 10 min.

### [INFO-N2] `DEPLOYMENT_MODE` : la doc ne mentionne pas les stores en lecture seule

- **Localisation** : `docs/configuration.md:142` ; `.env.example:43-45`
- **Statut** : **nouveau** (consequence de la puce BREAKING `CHANGELOG.md:57`).
- **Constat** : `configuration.md:142` liste ce que fait `huggingface` (bandeau, Settings › Ask et MCP en lecture seule, MCP coupe) sans les stores, alors que `SECURITY.md` le dit (section « Store connections »). `.env.example:44` ne cite toujours que le bandeau.
- **Remediation** : ajouter « store configuration (403) » a `configuration.md:142` et completer le commentaire de `.env.example:44`. 2 min.

### [INFO-N3] Autres changements de comportement, a arbitrer par le mainteneur (non comptes)

**Statut** : **nouveau**. Chacun est decrit dans le changelog. Aucun n'est juge cassant ici : soit il corrige un defaut, soit il ne touche qu'un cas marginal ou une fonction depreciee. Si le mainteneur en juge un cassant, il doit aussi aller sous `### BREAKING CHANGES`.

| Changement | Puce | Lecture de cet audit |
|------------|------|----------------------|
| `MAX_IMPORT_TABLE_CELLS`, nouvelle limite par defaut (100 000 cellules) : un import accepte en 0.7.3 peut etre refuse (400) | `:13` | Non cassant : le message d'erreur nomme la variable (`docling_importer.py:58`, `:63`) et `0` leve la limite |
| Plafond de 200 Mo sur `/api/analyses`, **code en dur** (`api/analyses.py:35`) | `:13` | A surveiller. Un operateur qui avait monte `NGINX_MAX_BODY_SIZE` au-dessus de 200M pour importer de gros JSON Docling (images embarquees) les voit maintenant refuses par le backend, sans reglage pour revenir en arriere. « as the bundled nginx already did » n'est exact qu'avec le defaut. Ni `configuration.md:32` (`NGINX_MAX_BODY_SIZE`) ni `SECURITY.md` ne disent que le backend ne suit pas ce reglage |
| `GET /api/stores/{slug}` ne renvoie plus les cles de config que Studio ne lit pas | `:30` | Non cassant pour l'app ; contrat d'API modifie pour un client externe, sur une fonction depreciee (retrait en 0.8.0). Decrit explicitement |
| Date vide dans une colonne `NOT NULL` : erreur a la lecture au lieu de « maintenant » | `:39` | Non cassant en pratique : colonnes `NOT NULL` avec defaut `datetime('now')`. Une base corrompue renverrait toutefois un 500 sur toute la liste concernee (`persistence/timestamps.py:29-38`) |
| `MCP_MAX_READ_TOKENS` > 32000 ramene a 32000 au demarrage | `:42` | Non cassant : la valeur rendait deja les reglages MCP impossibles a enregistrer ; avertissement au log |
| `/assets/…` manquant -> 404 au lieu de l'app | `:25` | Correctif |

### [INFO-N4] Une PR de fonctionnalite vise `release/0.7.4`, alors que le changelog annonce « no new feature »

- **Localisation** : `CHANGELOG.md:9` ; GitHub : jalon `0.7.4` (#18) avec l'issue #370 « [FEATURE] Claude plugin for the Docling Studio MCP server » ; PR #371 ouverte, `feature/370-claude-plugin-docling-studio-mcp -> release/0.7.4` (8 fichiers, +133)
- **Statut** : **nouveau**.
- **Constat** : si #371 est mergee avant le gel, la phrase « A quality release: no new feature » (`:9`) devient fausse. Il faut alors une puce `### Added`, sinon 11.1.2 tombe (MAJ). Si elle part en 0.8.0, il faut deplacer l'issue de jalon.
- **Remediation** : decider avant le gel ; ajuster `:9` et `### Added`, ou le jalon.

### [INFO-8] CHANGELOG `[0.7.3]` : formulations inexactes restantes

- **Localisation** : `CHANGELOG.md:65`, `:67`, `:73`, `:85`
- **Statut vs 0.7.4** : **partiellement corrige**. La puce BREAKING « Settings has no Reasoning section » est corrigee (`CHANGELOG.md:90`, `fbba1ac`). Restent :
  - « Analysis library » (`:65`, `:73`), alors que l'interface dit « Analyses » ;
  - « new variable `MCP_MAX_ROUNDS` » (`:67`), alors que les 7 `MCP_*` sont nouvelles ;
  - l'attribution certifi / emSign (`:85`), non verifiable hors ligne.
- **Nouveau** : la section `[0.7.3]` publiee a ete modifiee apres le tag. La GitHub Release `v0.7.3` garde l'ancien texte. C'est acceptable, puisqu'il s'agit d'une correction, mais les deux textes divergent.

### [INFO-10] `docs/maintainers.md` : 3 manques sur 5 combles

- **Statut vs 0.7.4** : **partiellement corrige**.
  - Corriges :
    - gel : nouvel `[Unreleased]` vide et lockfile (`:23-24`) ;
    - « known gaps » : builds `local` sans modeles et arm64, et e2e UI hors `@critical` (`:69-73`, exacts) ;
    - exemple de hotfix `v1.2.4` (`:79`) ;
    - jalon `0.7.4` cree (GitHub #18).
  - Restent :
    - la doc n'est construite par aucun job de PR, et ce n'est pas dans les « known gaps » (INFO-15) ;
    - les notes de release tirees de l'`awk` (`:37-41`), alors que la Release `v0.7.3` publiee est un texte reecrit.

### [INFO-12] Jalons GitHub

**Statut vs 0.7.4** : **partiellement corrige**. Le jalon `0.7.4` existe (GitHub #18), mais il ne porte que l'issue de fonctionnalite #370 (INFO-N4), et aucune issue de remediation. Les jalons publies `0.6.2` (#15), `0.7.0` (#10), `0.7.2` (#16) et `0.7.3` (#17) sont toujours ouverts (1, 3, 1 et 3 issues ouvertes).

### [INFO-13] Versions secondaires

**Statut vs 0.7.4** : **inchange**. `document-parser/pyproject.toml:3` et `embedding-service/pyproject.toml:3` sont en `0.0.0`, `e2e/*/pom.xml:10` en `0.3.1`, et `docs/maintainers.md` n'explique toujours pas ce placeholder.

### [INFO-14] SemVer : trois ruptures dans un patch

**Statut vs 0.7.4** : **inchange**, contexte concretise. `[Unreleased]` porte deux ruptures classees (`:56-57`), une non classee (CRIT ci-dessus), un retrait (`### Removed`, `:51`) et une nouvelle variable. SemVer 2.0.0 §7-8 demanderait un mineur hors 0.y.z. 11.2.2 reste conforme, par la clause §4 et les precedents 0.6.1, 0.6.2 et 0.7.3. La regle « patch = correctifs ; mineur = API, depreciation ou rupture » n'est toujours pas ecrite dans `docs/maintainers.md`.

### [INFO-15] Construction de la doc

**Statut vs 0.7.4** : **partiellement corrige**. Les deux liens casses sont corriges (`.github/PULL_REQUEST_TEMPLATE.md:22`, `docs/design/329-…`, `8c1bcd9`). Restent :
- `mkdocs build --strict` ne tourne que dans `docs.yml`, sur push vers `main` (`docs.yml:3-9`, `:41`), et aucun job de PR ne construit la doc ;
- `pip install mkdocs-material` n'est pas epingle (`docs.yml:38`).

Le coordinateur a passe `mkdocs build --strict` sur HEAD : OK.

### [INFO-16] Docstrings : 9 routes actives sans description

**Statut vs 0.7.4** : **inchange**. 17 routes sur 51 n'ont ni docstring ni `summary`. Les 9 actives sont : `api/config.py:31`, `:36`, `:50`, `:56`, `:64`, `:69`, `:83`, `api/mcp.py:20`, `api/reasoning.py:30`.

---

## Coherence docs <-> code

| Point | Resultat | Preuve |
|-------|----------|--------|
| `LLM_PROVIDER_TYPE` retire partout | **Oui** : plus aucune occurrence dans `.env.example`, `docs/configuration.md`, `docs/troubleshooting.md`, `README.md`, Compose. Restent le changelog (`:51`, `:56`, historique `:261`), le commentaire `infra/settings.py:64` (« no longer read »), les tests de non-lecture et le design doc 317 (`Implemented`, historique) | `git grep LLM_PROVIDER_TYPE HEAD` |
| `MAX_IMPORT_TABLE_CELLS` | **Coherent partout** : code (`settings.py:40`, `:257`), `.env.example:39-41`, `configuration.md:31`, `SECURITY.md:68`, `docker-compose.yml:175`, `docker-compose.dev.yml:146`, changelog `:13`. Defaut 100 000 et `0` = sans limite identiques partout | — |
| `FORWARDED_ALLOW_IPS` | Documente (`configuration.md:33-34`, commentaires nginx), defaut exact (uvicorn `127.0.0.1`). Absent de `.env.example` et de Compose. `troubleshooting.md:31` est perime (INFO-N1) | — |
| Variables lues vs documentees | **48 / 48** variables backend et embedding documentees (`configuration.md` ou `mcp-server.md`), plus `NGINX_MAX_BODY_SIZE` et `FORWARDED_ALLOW_IPS`. 0 variable documentee sans lecteur. Les 3 variables lues sans effet sont declarees comme telles (`configuration.md:62-70`), le retrait de leurs champs de `/api/health` etant ecarte. `configuration.md:3` ne pretend plus que tout est dans `settings.py` | Extraction `os.environ.get` + helpers |
| « Settings › Reasoning » (INFO-2 0.7.4, 10 renvois) | **Corrige** : 0 renvoi dans `docs/`, `SECURITY.md`, `.env.example`, `settings.py`. Cle i18n morte `settings.reasoning.title` supprimee (`70ec48d`). `user-guide.md:95` (« Reasoning timeline ») designe un autre element, la frise de l'onglet Ask | `git grep` |
| Parcours Compose d'Ask (INFO-3) | **Corrige** : `ASK_MODE=visible WITH_REASONING=true docker compose up --build` (`getting-started.md:108`), section **Ask** (`:113`) | — |
| Commentaires « instant first /api/convert » (INFO-6) | **Corriges** dans les 4 fichiers (`Dockerfile:74-94`, `docker-compose.yml:146-157`, `release.yml:60-68`, `document-parser/Dockerfile`) ; `git grep "instant first\|/api/convert"` : 0 | — |
| Architecture / Configuration et MCP (INFO-5) | **Corrige** : prefixes `/api/config/mcp`, `/api/mcp`, `/mcp`, import et summaries (`architecture.md:91-97`) ; couche `mcp_adapter` (`:75`) ; section MCP (`configuration.md:72-78`) ; `DEPLOYMENT_MODE` complete, sauf les stores (INFO-N2) | — |
| Guide utilisateur (INFO-7) | **Corrige** : section « Import a Docling analysis » (`user-guide.md:60`) ; 0 mention figee « 0.7.3 » dans `docs/*.md` hors audit et design | — |
| Design docs (INFO-9) | **Corrige** : 16 docs passes `Implemented` (`201fe3c`), `Target milestone` de 363/364 corriges (`a90aab9`). 195 reste `Accepted` (`docs/design/195-…:33`) ; ses variables paste sont desormais documentees « read but unused » | — |
| `CONTRIBUTING.md` (INFO-11) | **Corrige** : la branche cible suit le jalon, sinon la plus basse `release/x.y.z` sans tag (`CONTRIBUTING.md:21-23`). Aujourd'hui, c'est `release/0.7.4` | — |
| Glossaire (`docs/architecture/glossary.md`, nouveau, dans la nav `mkdocs.yml:44`) | **Exact** : les 24 noms de code cites existent (`ParseLoader`, `LoadedParse`, `DocumentIndex`, `SourceRound`, `CitationStatus`, `ReasoningIteration`, `domain/anchors.py`, `domain/spans.py`…). `MIN_QUOTE_CHARS = 10` (`domain/citation_match.py:29`) confirme « at least 10 characters ». L'avertissement `version_id` et la correspondance round/hop (`sources_wire.py`) correspondent au code | — |
| `SECURITY.md` | **Exact** : section Ask renommee, nouvelles sections « Store connections » et « Imported Docling documents ». Elles correspondent au code : 403 HF, 422 URI, test refuse, message generique, pas de re-verification au push, DNS rebinding non couvert. Nuance du plafond de 200 Mo code en dur : INFO-N3 | `SECURITY.md:42-70` |
| `docs/maintainers.md` | **Exact** sur le gate : `pipefail` (`release-gate.yml:87`, `:94`), audit `local` + `reasoning` (`:132`), smoke `local` (`:378-419`), taille de l'image `remote` (`:537`). Les « known gaps » declares sont exacts. Manques restants : INFO-10 | — |
| TODO / FIXME / `console.log` / `print` | 0 / 0 / 0 / 0 | Grille 11.3 |

---

## Suivi des ecarts 0.7.4

| Ecart 0.7.4 | Statut re-audit | Preuve |
|-------------|-----------------|--------|
| [CRIT] 11.1.1 pas de `[0.7.4]` | **Partiellement corrige** : `[Unreleased]` rouvert et rempli ; renommage au gel | `CHANGELOG.md:7` |
| [MAJ] 11.2.1 version front | **Inchange** (gel) | `frontend/package.json:3` |
| [INFO-1] `[Unreleased]` absent | **Corrige** | `CHANGELOG.md:7` ; `docs/maintainers.md:23` |
| [INFO-2] « Settings › Reasoning » | **Corrige** | voir Coherence |
| [INFO-3] Compose d'Ask | **Corrige** | `getting-started.md:108` |
| [INFO-4] 8 variables non documentees | **Corrige** | 48/48 |
| [INFO-5] MCP absent d'Architecture / Configuration | **Corrige** (sauf stores HF, INFO-N2) | `architecture.md:75`, `:91-97` ; `configuration.md:72-78` |
| [INFO-6] Commentaires « instant first /api/convert » | **Corrige** | 4 fichiers |
| [INFO-7] Import d'analyse absent du guide, « 0.7.3 » fige | **Corrige** | `user-guide.md:60` ; `9a55b12` |
| [INFO-8] `[0.7.3]` inexact | **Partiellement corrige** | `CHANGELOG.md:90` corrige ; `:65`, `:67`, `:73`, `:85` restent |
| [INFO-9] 16 design docs non `Implemented` | **Corrige** | `201fe3c`, `a90aab9` |
| [INFO-10] `maintainers.md`, 5 manques | **Partiellement corrige** (3/5) | `:23-24`, `:69-73`, `:79` |
| [INFO-11] Branche de release ambigue | **Corrige** | `CONTRIBUTING.md:21-23` |
| [INFO-12] Jalons | **Partiellement corrige** (0.7.4 cree) | GitHub #18 |
| [INFO-13] Versions secondaires | **Inchange** | `pyproject.toml:3` |
| [INFO-14] SemVer | **Inchange** (contexte : 3 ruptures) | — |
| [INFO-15] Build et liens de la doc | **Partiellement corrige** (liens) | `docs.yml:38` |
| [INFO-16] Docstrings de routes | **Inchange** | 9 routes actives |

Nouveaux ecarts : 1 CRIT (11.1.3, X-Forwarded-For) et 4 INFO (N1 a N4). Ils viennent de la remediation elle-meme : nouveau comportement de nginx, nouvelle rupture HF, nouveaux plafonds, PR de fonctionnalite sur la branche.

---

## Contenu attendu du commit de gel `chore(release): freeze [0.7.4]`

Sur `release/0.7.4`, un seul commit :
1. `CHANGELOG.md` : renommer `## [Unreleased]` (`:7`) en `## [0.7.4] - <date du tag>`, recreer au-dessus un `## [Unreleased]` vide.
2. **Ajouter sous `### BREAKING CHANGES`** la puce rate limit / `FORWARDED_ALLOW_IPS` (texte propose au CRIT). Sans elle, le gel donne 83 et un NO-GO.
3. `cd frontend && npm version 0.7.4 --no-git-tag-version` (`package.json:3`, `package-lock.json:3`, `:9`).
4. Selon le sort de #371 : retirer « no new feature » (`:9`) et ajouter `### Added`, ou deplacer #370 de jalon.
5. Optionnel, meme commit : `docs/troubleshooting.md:31` (INFO-N1), stores dans `configuration.md:142` (INFO-N2), « Analyses » et les 7 `MCP_*` dans `[0.7.3]` (INFO-8).

Controle avant la PR vers `main` :
- `awk '/^## \[0.7.4\]/{f=1; next} /^## \[/{f=0} f' CHANGELOG.md` n'est pas vide et contient une ligne `FORWARDED_ALLOW_IPS` sous `BREAKING CHANGES` ;
- `grep '"version"' frontend/package.json` donne `0.7.4` ;
- `grep -n "Unreleased" CHANGELOG.md` trouve une seule section, vide.

---

## Ce qui reste a faire pour 100

1. Le commit de gel (11.1.1 + 11.2.1) : +28 points (56 -> 83).
2. La puce BREAKING `X-Forwarded-For` (11.1.3) : +17 points (83 -> 100). 5 min, aucun code touche.
3. Tenir 11.1.2 au gel : une puce pour toute PR mergee d'ici la (en particulier #371).

---

## Points positifs

- **Changelog tenu pendant la remediation** : `[Unreleased]` rouvert des le debut (`70cc43c`), complete a chaque passe (`a4d9679`). Chaque puce verifiee correspond au code, versions de dependances et valeurs par defaut comprises. Les ruptures `LLM_PROVIDER_TYPE` et stores HF sont classees, avec la facon de garder l'ancien comportement (`REASONING_ENABLED=false`).
- **Le changelog nomme ses propres effets de bord** : 404 sur `/assets`, cles de config de store non renvoyees, date vide en erreur, borne de `MCP_MAX_READ_TOKENS`, plafond de l'import. Rien n'est cache sous « Internals ».
- **Les 16 INFO 0.7.4 traitees en bloc** : 10 corrigees entierement, 4 en partie, 2 inchangees (versions secondaires et docstrings de routes, sans risque) ; INFO-14 SemVer reste ouverte sur le fond. Notamment : 10 renvois « Settings › Reasoning », toutes les variables d'environnement documentees (48/48), MCP dans Architecture et Configuration, import d'analyse dans le guide, 16 design docs `Implemented`, regle de branche dans `CONTRIBUTING.md`.
- **Nouvelle documentation exacte** : glossaire (24 noms de code verifies), sections « Store connections » et « Imported Docling documents » de `SECURITY.md`, « known gaps » du gate dans `docs/maintainers.md`.
- **Code propre** : 0 TODO / FIXME / HACK / XXX, 0 `console.log` / `console.debug`, 0 `print()` executable, malgre environ 10 000 lignes ajoutees.

---

## Verdict partiel : NO-GO (pre-gel, et un CRIT que le gel seul ne leve pas)

Score **56/100** aujourd'hui : **2 CRITICAL**, 1 MAJOR, 11 INFO. Il etait de 72 en 0.7.4. La baisse vient d'un ecart nouveau, 11.1.3. Le changement `X-Forwarded-For` de la remediation fait partager un seul compteur `RATE_LIMIT_RPM` a tous les utilisateurs derriere un reverse proxy, tant que l'operateur n'a pas regle `FORWARDED_ALLOW_IPS`. Il est decrit, avec la marche a suivre, mais sous `### Security`, pas sous `### BREAKING CHANGES`. C'est le cas du CRIT `ASK_MODE` de 0.7.3.

Le commit de gel tel que `docs/maintainers.md` le decrit donnerait **83/100**, toujours **NO-GO** (11.1.3). Le gel avec une puce BREAKING de plus donnerait **100/100, GO**. Avec la lecture alternative (point non cassant), le score est de 72 aujourd'hui et de 100 apres le gel.

Le reste de la documentation est en net progres : changelog complet et exact, 48/48 variables documentees, `LLM_PROVIDER_TYPE` retire partout, glossaire et `SECURITY.md` justes, 10 INFO 0.7.4 levees entierement et 4 en partie.

---

## Addendum — vérification post-correctifs (HEAD 3f1d1cb, 2026-11-03)

Verification dans le depot de la passe `a4d9679..3f1d1cb` (commits `3f1d1cb` et `c78b7cb` pour la documentation, et les puces de chaque correctif). Gates du coordinateur sur `3f1d1cb` : `mkdocs build --strict` OK, actionlint 0. Gel toujours **non fait, volontairement**. Etat de la PR #371 lu par l'API REST GitHub le 2026-11-03 : `open`, base `release/0.7.4`, non mergee.

### Ecarts vises

| Ecart | Statut | Preuve (`3f1d1cb`) |
|-------|--------|--------------------|
| [CRIT] 11.1.3 rupture `X-Forwarded-For` hors `### BREAKING CHANGES` | **Ferme** | `CHANGELOG.md:58` (« Rate limit behind your own reverse proxy », sous `### BREAKING CHANGES`, `:56`) donne l'avant / apres et le remede (`FORWARDED_ALLOW_IPS`, « never set it to `*` »). La puce Security `:17` y renvoie (« see BREAKING CHANGES ») |
| Nouvelle rupture : identifiants Neo4j limites a `NEO4J_URI` | **Signalee** | `CHANGELOG.md:59` (BREAKING : un store Neo4j sur sa propre URI doit porter son mot de passe), `:15` (Security, renvoi) ; `SECURITY.md:60`. Conforme au code (`services/store_backend_resolver.py:222-246`) |
| Nouvelle rupture : plafond de corps de 50 Mo | **Signalee** | `CHANGELOG.md:60` (BREAKING, avec le contournement `image_export_mode=placeholder`), `:13` (Security, renvoi) ; `docs/configuration.md:31` ; `SECURITY.md:68`. Conforme au code (`api/analyses.py:45`) |
| Autre rupture etendue : HF, retrait d'un document d'un store | **Signalee** | `CHANGELOG.md:62` (« and removing a document from it ») ; `SECURITY.md:55`. Code : `services/store_service.py:442` |
| [INFO-N1] `troubleshooting` contredit le correctif rate limit ; Compose ne transmet pas `FORWARDED_ALLOW_IPS` | **Fermee** | `docs/troubleshooting.md:29-31` : compte par client dans l'image unique ; en Compose ou derriere un proxy, compteur partage jusqu'a `FORWARDED_ALLOW_IPS` ; renvoi vers Limits. `docker-compose.yml:178` et `docker-compose.dev.yml:145` transmettent la variable (defaut `127.0.0.1`). `docs/configuration.md:33-34` le dit. L'exemple de sous-reseau propose n'est pas ajoute : detail |
| [INFO-N2] `DEPLOYMENT_MODE` : stores en lecture seule absents de la doc | **Fermee** | `docs/configuration.md:142` (« makes stores read-only (creating, editing and deleting a store answer 403, and connection tests are refused) ») ; `.env.example:43-44` (« the stores read-only »). Nuance en INFO-N5 |

### Grille apres correctifs

| # | Item | Poids | Re-audit | Post-correctifs | Preuve |
|---|------|-------|----------|-----------------|--------|
| 11.1.1 | `[X.Y.Z] - date` | 3 | NON (pre-gel) | **NON** (pre-gel) | `CHANGELOG.md:7` : `## [Unreleased]` |
| 11.1.2 | Modifications significatives listees | 2 | OUI | **OUI** | Chaque commit de la passe a sa puce : `:13` (budget de grilles, 50 Mo), `:14` (garde au push, 503 generique, `remove_document` HF), `:15` (Neo4j), `:16` (`/reasoning`), `:17` (Compose `FORWARDED_ALLOW_IPS`), `:32` (OpenAPI type, test, `document_version_id`), `:45` (couleurs, `--on-accent`), `:48` (Karate) ; internes (`94fbfcb`, `af5b62f`, `618a39a`, `ad8e2ae`, `db43a21`) sous « Internals » / `:30`. Tient au gel si #371 est tranchee (INFO-N4) |
| 11.1.3 | Breaking changes identifies | 3 | **NON** | **OUI** | `CHANGELOG.md:56-62` : 5 ruptures classees (`X-Forwarded-For`, Neo4j, 50 Mo, `LLM_PROVIDER_TYPE`, stores HF) |
| 11.1.4 | Keep a Changelog | 1 | OUI | OUI | `:7`, `:11`, `:22`, `:38`, `:51`, `:56` |
| 11.2.1 | `frontend/package.json` = X.Y.Z | 2 | NON (pre-gel) | **NON** (pre-gel) | `frontend/package.json:3` et `package-lock.json:3`, `:9` = `0.7.3` |
| 11.2.2 | SemVer | 2 | OUI | OUI | Patch en 0.y.z (SemVer §4) ; voir INFO-14 |
| 11.3.1 | Pas de TODO / FIXME | 1 | OUI | OUI | `git grep` : 0 ; aucun ajoute par la passe (scan des lignes `+` du diff) |
| 11.3.2 | Pas de `console.log` | 2 | OUI | OUI | 0 ajoute |
| 11.3.3 | Pas de `print()` | 2 | OUI | OUI | 0 ajoute |

### INFO mises a jour

- **INFO-N3** (changements a arbitrer) : le plafond de corps code en dur passe de 200 a **50 Mo**, et il est desormais classe en rupture (`:60`). Le budget `MAX_IMPORT_TABLE_CELLS` compte aussi les graphiques des images et les lignes sans colonnes (`:13`) : un import accepte en 0.7.3 peut etre refuse, avec un message qui nomme la variable. Lecture inchangee : non cassant. **Reste ouverte.**
- **INFO-N4** (#371 vers `release/0.7.4`) : **inchangee**. La PR est ouverte et non mergee, et `:9` dit toujours « no new feature ».
- **INFO-14** (SemVer) : **contexte aggrave** : `[Unreleased]` porte maintenant **5** ruptures classees dans un patch. 11.2.2 reste conforme par §4 et les precedents.
- **INFO-N5** (nouvelle, issue de la passe) — trois petites inexactitudes :
  1. `CHANGELOG.md:45` « Hard-coded colours now use the theme's tokens (the graph palette keeps its own) ». Au-dela de la palette du graphe, 7 regles restent codees en dur (`DocsLibraryPage.vue:416-418`, `StoreForm.vue:426-427`, `StrategyPopover.vue:361-362`, `ChunkPanel.vue:523`, `:527`, `:571`, `StatusBadge.vue:58` ; MIN couleurs (c) de l'audit 05).
  2. `.env.example:38-40` decrit encore `MAX_IMPORT_TABLE_CELLS` comme « all tables together (rows x columns of each table) », sans les graphiques ni les lignes sans colonnes. `docs/configuration.md:31` est exact.
  3. `docs/configuration.md:142` ne cite pas le refus du retrait d'un document d'un store, que disent `CHANGELOG.md:62` et `SECURITY.md:55`.

  Remediation : 3 lignes dans le commit de gel.
- INFO-8, 10, 12, 13, 15 et 16 : non visees, inchangees.

### Score recalcule

| Scenario | 11.1.1 | 11.1.3 | 11.2.1 | Score | Verdict |
|----------|--------|--------|--------|-------|---------|
| Re-audit, actuel (pre-gel) | NON | NON | NON | 56 | NO-GO (2 CRIT) |
| **Post-correctifs, actuel (pre-gel)** | NON | **OUI** | NON | **72** (13 / 18) | **NO-GO** (1 CRIT : 11.1.1) |
| **Post-correctifs, apres le commit de gel** de `docs/maintainers.md:22-24` | OUI | OUI | OUI | **100** (18 / 18) | **GO** |

La lecture alternative du re-audit (`X-Forwarded-For` juge non cassant) donnait 72 / 100. Elle coincide desormais avec la lecture retenue, puisque 11.1.3 est conforme dans les deux.

| Metrique | Re-audit | Post-correctifs (pre-gel) | Apres gel |
|----------|----------|---------------------------|-----------|
| Items conformes | 6 / 9 | **7 / 9** | 9 / 9 |
| Score | 56 | **72** | **100** |
| Ecarts CRITICAL | 2 | **1** (11.1.1) | 0 |
| Ecarts MAJOR | 1 | 1 (11.2.1) | 0 |
| Ecarts MINOR | 0 | 0 | 0 |
| Ecarts INFO | 11 | **10** (−N1, −N2, +N5) | 10 (9 si N5 est traitee au gel) |

Le 100 apres gel suppose que 11.1.2 tienne : trancher #371 avant le gel, soit une puce `### Added` et le retrait de « no new feature », soit le changement de jalon de #370.

### Verdict partiel apres correctifs : NO-GO pre-gel, GO apres le commit de gel

Aujourd'hui : **72 / 100**, 1 CRITICAL (section `[0.7.4]` absente, etape du gel), 1 MAJOR (version front, etape du gel), 10 INFO. Le gel decrit par `docs/maintainers.md:22-24` suffit desormais a lui seul : **100 / 100, GO**. La puce BREAKING supplementaire qu'exigeait le re-audit est faite. Les trois lignes de l'INFO-N5 peuvent entrer dans le meme commit.
