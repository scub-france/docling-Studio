# Rapport d'audit : Sécurité

**Release** : 0.7.4
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `release/0.7.4` @ `1de1929` (= tag `v0.7.3` + 2 commits README : `0465e70`, `1de1929`)

Baseline : re-audit 0.7.3 (`reports/release-0.7.3-reaudit/08-security.md`, **97/100**, 0 CRIT,
2 MAJ, 6 MIN, 4 INFO), lui-même après l'audit initial 0.7.3 (89/100, 1 CRIT).

Méthode :
- `git diff e01fd95..HEAD` (tête du re-audit → tête actuelle). Seuls ont changé : `README.md`,
  `CHANGELOG.md`, `.trivyignore.yaml` (commentaire), `.github/workflows/release-gate.yml`,
  `frontend/src/shared/i18n.ts`, `frontend/src/features/mcp-config/ui/McpConfigSection.vue`, les
  rapports d'audit et deux GIF. `git diff --quiet e01fd95..HEAD -- document-parser nginx.conf.template
  frontend/nginx.conf.template docker-compose.yml docker-compose.dev.yml Dockerfile frontend/Dockerfile
  SECURITY.md frontend/package.json frontend/package-lock.json` → **aucun changement** : backend,
  lockfiles, images et nginx sont ceux du tag `v0.7.3`.
- Re-vérification de chaque item de la checklist et de chaque écart précédent au working tree, avec
  les commandes de la fiche 08 (lignes citées relues).
- Dépendances, en lecture seule :
  - `npm audit --omit=dev` dans `frontend/` ;
  - `uv export --frozen --no-dev [--group local --group reasoning] --no-hashes` (vers le scratchpad,
    aucun fichier du dépôt modifié), puis `uvx pip-audit 2.10.1 -r … --no-deps --disable-pip`
    (service de vulnérabilités PyPI).
- Lecture une seule fois de l'état des runs `Release Gate` (`gh run list` / `gh run view`).
- Deux sondes ciblées, avec le venv du projet (docling-core 2.92.0, uvicorn 0.52.4, conformes à
  `uv.lock`) et une limite mémoire (`ulimit -v`) :
  - coût de l'import Docling en fonction de `num_rows × num_cols` ;
  - résolution du client par `ProxyHeadersMiddleware` d'uvicorn avec ses valeurs par défaut.
- Lecture de `docling/document_converter.py` dans la roue `docling-slim 2.121.0` (version verrouillée),
  téléchargée dans le scratchpad, non installée.

Non fait / non vérifiable : Trivy n'est pas installé et aucun Docker n'est disponible, donc pas de
scan d'image local. L'API GitHub Advisory globale et `api.osv.dev` sont inaccessibles depuis le bac à
sable : la **sévérité** des avis remontés par pip-audit n'a pas pu être lue. Ni l'app ni les suites
de tests n'ont été lancées.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | **97 / 100** |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 3 |
| Écarts MINOR | 7 |
| Écarts INFO | 7 |

Détail du calcul : poids total de la checklist = 3+3+2 + 3+3+2 + 3+3+3 + 3+2+2 + 3+1 = **36**.
Seul l'item 8.5.2 (poids 1) est non conforme. Poids conformes = 36 − 1 = 35.
**Score = 35 / 36 = 97,2 → 97.**

Comme en 0.7.0 et 0.7.3, les trois [MAJ] portent sur des sujets que la checklist ne pondère pas :
exposition réseau, déni de service applicatif et SSRF. Ils sont reportés comme écarts de sécurité
réels, mais ne font basculer aucun item. Le score reste strictement adossé à la checklist.

**Sensibilité du score** : 8.5.1 est conforme sur la foi du dernier gate vert (2026-11-02). Si le
prochain scan Trivy remonte une nouvelle CRITICAL (base mise à jour chaque jour) ou tourne après le
2026-12-31 (expiration des 5 suppressions), 8.5.1 bascule : 32/36 = **89**, 1 CRIT, **NO-GO**.

---

## Vérification par item

| # | Item | Poids | Conforme | Preuve (@ `1de1929`) |
|---|------|-------|----------|----------------------|
| 8.1.1 | Aucun secret en dur | 3 | **Oui** | grep fiche 08 : seules des affectations depuis l'env ou des paramètres. `git ls-files` → seul `.env.example` (+ un design doc nommé `…credentials.md`). `git grep` des motifs `sk-…`, `ghp_…`, `hf_…`, `AKIA…`, `BEGIN … PRIVATE KEY` : vide. `NEO4J_PASSWORD=changeme` est un défaut dev documenté (`infra/settings.py:35-40`, `docker-compose.yml:7,178`), avec avertissement au boot (`bootstrap/factories.py:160`) |
| 8.1.2 | `.env` dans `.gitignore` | 3 | **Oui** | `.gitignore:26-28` (`.env`, `.env.local`, `.env.production`) |
| 8.1.3 | Secrets Docker par env, pas en build args | 2 | **Oui** | ARG : `APP_VERSION`, `BAKE_MODELS`, `WITH_REASONING` (`Dockerfile:13,24,86,90` ; `document-parser/Dockerfile:59,63`) ; `release.yml:70-73` ne passe que ces trois build-args ; secrets en `environment:` (`docker-compose.yml:163-195`) |
| 8.2.1 | Entrées validées par Pydantic | 3 | **Oui** | 51 routes sous `api/`, aucune lecture brute du corps (`request.json/body/form` : grep vide) ; `ImportAnalysisRequest` (`api/schemas.py:272-276`) puis `DoclingDocument.model_validate` (`infra/docling_importer.py:18`) ; `McpConfigUpdateRequest` (`api/schemas.py:803-814`) + `validate_base_url` (`domain/mcp_config.py:94-104`). Validation **sans bornes** sur l'import : voir [MAJ] import |
| 8.2.2 | `MAX_FILE_SIZE_MB` appliqué à l'upload | 3 | **Oui** | `api/documents.py:69-88` (Content-Length, puis lecture bornée par morceaux, 413) ; défaut 50 Mo (`infra/settings.py:28,216`) ; double contrôle `services/document_service.py:75-76` |
| 8.2.3 | Types de fichiers validés | 2 | **Oui** | magic `%PDF` (`services/document_service.py:27,78-79`), extension forcée `.pdf` (`:81`). Voir [INFO] convertisseur docling |
| 8.3.1 | SQL en paramètres liés | 3 | **Oui** | f-strings limitées à des constantes et à des `?` : `persistence/document_repo.py:93,118`, `chunk_repo.py:122-124`, `analysis_repo.py:72,82,94,104,112,129,144-153` ; `LIKE` échappé (`document_repo.py:21-23,89-90`). Cypher : label tiré d'une table fixe (`infra/docling_tree.py:41-43` → `infra/neo4j/tree_writer.py:181-183`) |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | **Oui** | grep `eval(`, `exec(`, `os.system(`, `subprocess.`, `shell=True`, `pickle.load`, `yaml.load(`, `__import__(`, `create_subprocess` : vide |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | **Oui** | seul `v-html` : `frontend/src/shared/ui/MarkdownViewer.vue:3`, assaini `:24`. Cartes MCP : `esc()` (`mcp_adapter/sources_app.html:326`, `citation_app.html:402`), liens limités à `http(s)` (`sources_app.html:360`) |
| 8.4.1 | CORS explicite, pas de `*` | 3 | **Oui** | `main.py:89-95` ; défaut localhost (`infra/settings.py:76-78,199`) ; grep `allow_origins.*\*` vide |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | **Oui** | `main.py:96-101` ; exclusion `infra/rate_limiter.py:59,68`. Sémantique « par IP » non tenue, et contournable dans l'image tout-en-un : voir [MIN] |
| 8.4.3 | Nginx sans directory listing | 2 | **Oui** | `nginx.conf.template:13-15` et `frontend/nginx.conf.template:13-15` (`try_files`) ; grep `autoindex` vide |
| 8.5.1 | Pas de CVE critique connue | 3 | **Oui** (adossé au dernier gate vert) | voir détail ci-dessous |
| 8.5.2 | Versions épinglées | 1 | **Non** | `document-parser/pyproject.toml:42-43` (`torch`, `torchvision` sans version) |

### Détail 8.5.1

**`.trivyignore.yaml` : dates d'expiration au 2026-11-03**

| Entrée | Ligne | Paquet / image | `expired_at` | Marge |
|--------|-------|----------------|--------------|-------|
| CVE-2026-6653 | `:7` (exp. `:20`) | libxml2, image `local` | 2026-12-31 | J+58 |
| CVE-2026-112393 | `:33` (exp. `:38`) | Pillow 10.4.0, deux images | 2026-12-31 | J+58 |
| CVE-2026-112398 | `:39` (exp. `:44`) | Pillow 10.4.0 | 2026-12-31 | J+58 |
| CVE-2026-112403 | `:45` (exp. `:50`) | Pillow 10.4.0 | 2026-12-31 | J+58 |
| CVE-2026-112900 | `:51` (exp. `:56`) | Pillow 10.4.0 | 2026-12-31 | J+58 |

Aucune suppression n'est expirée, et aucune n'expire dans une fenêtre de release 0.7.4 tenue en
novembre ou en décembre. Les 5 entrées tombent **le même jour** : tout Release Gate lancé à partir du
2026-12-31 (la date est incluse ou non selon la sémantique de Trivy, non vérifiée) échouera au pas
bloquant (`.github/workflows/release-gate.yml:357-365`, `exit-code: 1`, `severity: CRITICAL`). C'est le
mécanisme qui a fait le CRIT de l'audit initial 0.7.3.

**Gate**
- Dernier scan complet : run `41468347487` (PR #366, 2026-11-02 15:06 UTC), **13/13 jobs verts**, dont
  `Security scan — local` et `Security scan — remote`. Annotations : 4 HIGH par image, et
  « pip-audit: 95 known vulnerabilities ».
- Run suivant, `41625312292` (2026-11-03 11:10 UTC, branche `hotfix/readme-mcp-gif`) : **annulé** par
  le mainteneur pendant les builds Docker, donc aucun scan Trivy depuis le 2026-11-02.
- Le lock, les Dockerfiles et le `.trivyignore.yaml` (hors commentaire) sont identiques à ceux du run
  vert. Seule la base Trivy a pu évoluer : c'est **non vérifiable** ici, sans Trivy.

**pip-audit (2026-11-03, lock `--frozen`)**

| Périmètre | Résultat | Paquets |
|-----------|----------|---------|
| Image `remote` (`--no-dev`) | 93 avis, 4 paquets | pillow 10.4.0 (66 entrées, correctifs jusqu'à 13.0.0) ; cryptography 45.0.7 (7 avis distincts, correctifs 46.0.5 → 50.0.0) ; filelock 3.32.3 (12 avis, 4.0.9 / 4.2.1) ; transformers 5.8.1 (2 avis, 5.10.0 / aucun) |
| Image `local` (`+ local + reasoning`) | 111 avis, 9 paquets | ceux du remote + docling 2.121.0 (8) et docling-slim 2.121.0 (7), correctifs 2.131.0 / 2.132.0 ; accelerate 1.14.0 (1, pas de correctif) ; nltk 3.10.3 (1, pas de correctif) ; setuptools 84.0.0 (1, Windows seulement, 84.1.0). `torch 2.13.0+cpu` et `torchvision 0.28.0+cpu` **non audités** (absents de PyPI) |

pip-audit ne fournit pas de sévérité. Le dernier scan Trivy, qui en fournit une, n'a remonté aucune
CRITICAL hors suppressions le 2026-11-02, sur ces mêmes versions. **Conforme**, avec les réserves
ci-dessus. Le détail est dans [MIN] dépendances Python.

**npm audit `--omit=dev` (2026-11-03)** : `{high: 7, critical: 0}`, identique à 0.7.3. Voir [MIN].

---

## Écarts constatés

### [MAJ] `/api/*` sans validation du `Host` : DNS rebinding possible contre une instance locale

**Statut vs 0.7.3 : inchangé, ouvert** (code identique au tag ; le re-audit l'avait renvoyé en 0.8.0).

- **Localisation** :
  - `document-parser/main.py:89-101` : seuls `CORSMiddleware` et `RateLimiterMiddleware`. Aucun
    `TrustedHostMiddleware` ni contrôle équivalent dans `document-parser/` (grep vide).
  - `nginx.conf.template:1-2` et `frontend/nginx.conf.template:1-2` : un seul `server`, sans
    `server_name`, donc serveur par défaut pour tout `Host`.
  - `:17-19` : `/api/` est proxifié avec `proxy_set_header Host $host`.
- **Constat** : `/mcp` est protégé contre le rebinding (421, `bootstrap/mcp_mount.py:210-231`), mais
  `/api/*` ne l'est pas, alors qu'il sert les mêmes documents et **toutes** les écritures. Une page web
  ouverte par quelqu'un qui fait tourner Studio en local peut faire résoudre son domaine vers
  127.0.0.1 sur le port 3000. Elle émet alors des requêtes *same-origin* et lit les réponses ; CORS
  n'intervient pas. Elle obtient :
  - la lecture de tous les documents et analyses ;
  - `DELETE /api/documents/{id}` (`api/documents.py:125`) ;
  - `PUT /api/config/reasoning` (`api/config.py:36`) et `PUT /api/config/mcp` (`:80`) ;
  - via `POST /api/stores` + `/test-connection`, un balayage du LAN de la victime depuis son propre
    Studio (voir [MAJ] SSRF stores) ;
  - via `POST /api/analyses/import`, l'arrêt du backend avec un JSON de moins de 1 Ko (voir [MAJ]
    import).
- **Exploitabilité** : **PLAUSIBLE**, non démontrée ; elle dépend du navigateur (Chrome récent
  demande l'accès au réseau local).
- **Règle violée** : 8.4 (réseau). Écart additionnel, sans impact de score.

#### Évaluation de la remédiation : garde `Host` pilotée par variable d'environnement

**Proposition** : une variable `API_ALLOWED_HOSTS` (liste de noms d'hôte, sans port, avec `*.domaine`
et `*`), lue dans `infra/settings.py` comme `MCP_ALLOWED_HOSTS` (`:262-268`). Valeurs par défaut :
- `localhost,127.0.0.1,[::1]` ;
- `*` si `DEPLOYMENT_MODE=huggingface`, sur le modèle de `MCP_ENABLED` (`:256-259`).

Le middleware, ajouté **en dernier** dans `main.py` pour être le plus externe :
- ne contrôle que les chemins `/api/` ;
- exempte `/api/health`, comme le rate limiter ;
- laisse `/mcp` à son propre contrôle, `MCP_ALLOWED_HOSTS` ;
- répond 400 avec un message qui nomme la variable, et journalise un WARNING une fois par hôte refusé.

**`TrustedHostMiddleware` de Starlette tel quel est déconseillé.** Starlette 1.6.0 extrait l'hôte par
`headers.get("host").split(":")[0]` (`starlette/middleware/trustedhost.py:40`) : `Host: [::1]:3000`
donne `"["`, donc un accès par IPv6 littéral ne peut être autorisé que par `*`. Il s'appliquerait aussi
à `/api/health` et à `/mcp`. Un petit middleware d'une trentaine de lignes, qui reprend la sémantique
de wildcard de Starlette avec un découpage de port correct, évite ces deux pièges.

| Contexte | `Host` vu par le backend | Défaut proposé | Casse ? |
|----------|--------------------------|----------------|---------|
| `docker run -p 3000:3000` (README:17), navigation sur `localhost` | `localhost` (nginx `$host`, `nginx.conf.template:19`) | accepté | non |
| `docker compose up`, navigation sur `localhost` | `localhost` (`frontend/nginx.conf.template:19`) | accepté | non |
| Instance ouverte depuis une autre machine (IP LAN, nom NAS) | `192.168.x.y`, `nas.local`… | **refusé** | **oui** : SPA chargée, chaque `/api` en 400 → il faut `API_ALLOWED_HOSTS` |
| Reverse proxy avec domaine (`studio.example.com`) | le domaine | **refusé** | **oui** → `API_ALLOWED_HOSTS=studio.example.com` |
| Hugging Face Space | `*.hf.space` | `*` (mode huggingface) | non. La config du Space est hors dépôt, non vérifiée |
| `docker-compose.dev.yml` (Vite → `http://document-parser:8000`, `changeOrigin: true`) | `document-parser:8000` (`frontend/vite.config.js:27-29`, `docker-compose.dev.yml:182`) | **refusé** | **oui** → ajouter `document-parser` au défaut du compose dev, ou `changeOrigin: false` sur `/api` (le serveur Vite filtre déjà le `Host`, `vite.config.js:25`) |
| `npm run dev` + uvicorn local (`vite.config.js:7`) | `localhost:8000` | accepté | non |
| CI : smoke test, E2E API et UI (`release-gate.yml:304,563,648-649` ; `ci.yml:139,218-219`) | `localhost` | accepté | non |
| Karate local, défaut `http://localhost:8000` (`e2e/*/karate-config.js:3`) | `localhost:8000` | accepté | non |
| Tests unitaires : `TestClient(app)` dans 13 fichiers de `tests/`, `Host: testserver` | `testserver` | **refusé** | **oui** → `conftest.py` doit fixer `API_ALLOWED_HOSTS` avant l'import de `infra.settings` (singleton, `:280`), plus un test 400 et un test pour `/api/health` exempté |
| Sondes Docker / Kubernetes sur `/api/health` (IP du pod) | IP | exempté | non |

- **Risque de régression** : **moyen**. CI et quick-start local ne cassent pas. Cassent, en revanche,
  les instances consultées par IP LAN ou par domaine (changement **BREAKING** à annoncer dans le
  CHANGELOG, `docs/configuration.md`, `.env.example` et un passthrough
  `API_ALLOWED_HOSTS: ${API_ALLOWED_HOSTS:-}` dans les deux compose), le compose dev et la suite
  unitaire, tant qu'ils ne sont pas ajustés dans la même PR.
- **Effort** : **M**. Middleware et réglage : S. Le reste : compose dev, `conftest`, tests, docs et note
  BREAKING.
- **Alternative nginx** : un `server_name` explicite et un `default_server` qui répond 421. Elle demande
  d'ajouter la variable à l'`envsubst` de `Dockerfile:65`, qui ne substitue que `NGINX_MAX_BODY_SIZE`.
  Elle ne couvre pas uvicorn exposé directement, et n'est pas testable en unitaire. Moins bonne.
- **Complément peu coûteux** : refuser les requêtes mutantes dont l'`Origin` n'est pas dans
  `CORS_ORIGINS`. Cela bloque les écritures par rebinding, pas les lectures, avec la même casse pour
  l'accès LAN.

### [MAJ] Import d'analyse Docling : déni de service par amplification. Un JSON de 691 octets coûte 18 s de CPU et 347 Mo, sans plafond de corps

**Statut vs 0.7.3 : aggravé, MIN → MAJ.** Le constat est nouveau, démontré, et absorbe l'ancien [MIN]
« import sans plafond de taille ».

- **Localisation** :
  - route : `document-parser/api/analyses.py:73-87`, sans garde `read_only`, donc active sur le Space HF ;
  - schéma : `api/schemas.py:276` (`document: dict`) ;
  - traitement : `infra/docling_importer.py:18,22,23,26` (`model_validate`, puis `export_to_markdown`,
    `export_to_html`, `export_to_dict`), appelé dans un thread (`services/analysis_service.py:180`) ;
  - cause : docling-core 2.92.0, `docling_core/types/doc/items/table/table_data.py:105-106`
    (`num_rows: int = 0`, `num_cols: int = 0`, sans borne) et `:109-128` (`grid` est un
    `@computed_field` qui alloue `num_rows × num_cols` objets `TableCell`) ;
  - plafond de corps : nginx seul, 200 Mo (`docker-compose.yml:208`, `Dockerfile:61`).
- **Constat (démontré)** : sonde avec le venv du projet, un document vide plus une table
  `{"table_cells": [], "num_rows": n, "num_cols": n}`, passée à `DoclingDocumentImporter().deserialize` :

  | n | Cellules | Corps JSON | Temps | Pic d'allocation (tracemalloc) |
  |---|----------|------------|-------|--------------------------------|
  | 100 | 10 000 | 691 o | 1,0 s | 24 Mo |
  | 200 | 40 000 | 691 o | 3,8 s | 85 Mo |
  | 400 | 160 000 | 691 o | 18,0 s | 347 Mo |

  - **Coût par cellule** : environ 2,2 Ko et 0,11 ms, linéaire.
  - **Stockage** : la grille calculée est aussi stockée. À n = 100, `document_json` pèse 2,4 Mo,
    soit 3 400 fois la requête.
  - **Extrapolation, non exécutée** : à n ≈ 1 350, la limite de 4 Go du conteneur
    (`docker-compose.yml:196-199`) est atteinte. Avec `num_rows = num_cols = 100000`, la mémoire
    croît jusqu'au kill OOM.
  - **Absence de redémarrage** : aucune politique `restart:` dans les compose (grep vide), et dans
    l'image tout-en-un uvicorn est le processus principal (`Dockerfile:65`). Le backend reste donc
    arrêté. **PLAUSIBLE** pour l'arrêt, **démontré** pour l'amplification.
  - **Requêtes parallèles** : `asyncio.to_thread` laisse la boucle répondre, mais plusieurs imports
    s'additionnent dans le pool de threads.
- **Ce qui reste sain** : exports en mode placeholder, aucun chemin de fichier lu depuis le JSON
  (vérifié au re-audit 0.7.3, code inchangé).
- **Règle violée** : 8.2.1 et 8.2.2 dans leur esprit (entrée validée mais non bornée). Items conformes
  au sens strict. Écart additionnel, sans impact de score.
- **Remédiation** (effort **S**, risque **faible**) :
  1. dans `DoclingDocumentImporter.deserialize`, juste après `model_validate`, refuser en `ValueError`
     (donc 400) tout document dont une table dépasse un plafond de cellules (par exemple 250 000), ou
     dont le total dépasse un budget. Le plafond doit être généreux, car les vraies tables comptent
     quelques milliers de cellules ;
  2. plafonner le corps (Content-Length et lecture bornée, alignés sur `MAX_FILE_SIZE_MB`) et réduire
     `client_max_body_size` sur `location = /api/analyses/import` ;
  3. ajouter un test avec `num_rows = num_cols = 10**6`, qui doit répondre 400 immédiatement.

### [MAJ] SSRF non filtrée via les stores (OpenSearch / Neo4j) : `connection_uri` libre et `test-connection`, actifs aussi sur un Space Hugging Face

**Statut vs 0.7.3 : nouveau constat.** Le code est antérieur (#279, 0.6.1) et n'avait jamais été
relevé. Les audits 0.6.2 n'avaient examiné que la gestion du mot de passe.

- **Localisation** :
  - routes : `document-parser/main.py:106` (routeur des stores toujours monté) ;
    `api/stores.py:86` (POST), `:118` (PATCH), `:143-164` (`/test-connection`) ;
  - validation : `services/store_service.py:109-127`, qui ne contrôle que le schéma (`http(s)` ou
    `bolt…`) ;
  - sonde : `services/store_service.py:310-343`, qui renvoie `str(exc)` au client (`:329,342`) ;
  - cible : `services/store_backend_resolver.py:117-129,131-151` (URI du store en priorité),
    `infra/opensearch_store.py:101-107` (`info()`, c'est-à-dire `GET /` sur l'URL) ;
  - garde Hugging Face posée pour reasoning et MCP seulement : `bootstrap/builder.py:218,255`. Le grep
    `read_only` ne trouve rien dans `store_service`.
- **Constat** : quiconque atteint `/api` crée un store dont l'URL est `http://169.254.169.254/`,
  `http://10.x.y.z:port/` ou `bolt://interne:7687`, puis appelle `test-connection`. Le backend envoie
  alors la requête et renvoie un booléen plus le texte de l'exception (oracle de balayage interne, et
  fuite partielle possible du message d'erreur). C'est exactement la classe de faille que la 0.7.0
  avait classée [MAJ] et corrigée pour la sonde Ollama (`infra/llm/ollama_probe.py:31-73,82`). La
  garde n'a pas été appliquée ici. Contrairement aux écritures reasoning et MCP, rien n'est refusé en
  `DEPLOYMENT_MODE=huggingface` : la démo publique peut servir de pivot. Cela est vérifié dans le code ;
  la configuration réelle du Space est hors dépôt et n'a pas pu être vérifiée.
- **Atténuants** : surface d'ingestion dépréciée, supprimée en 0.8.0 (`CHANGELOG.md:29`) ; posture
  « no login » (`SECURITY.md:51`) ; aucune donnée exfiltrée au-delà de ce que l'API expose déjà.
- **Règle violée** : 8.2.1 (validation, défense en profondeur). Item conforme. Écart additionnel, sans
  impact de score.
- **Remédiation** (effort **S**, risque **faible**) :
  - appliquer `_resolved_target_is_blocked` à `connection_uri` à l'écriture et dans `test_connection` ;
  - refuser en 403 les écritures de stores et `test-connection` quand `DEPLOYMENT_MODE=huggingface`
    (même `read_only` que `builder.py:218`), ou ne monter le routeur que si l'ingestion est configurée ;
  - ne plus renvoyer `str(exc)` brut.

### [MIN] MCP actif par défaut, sans authentification, port publié sur toutes les interfaces. Les textes sont désormais exacts

**Statut vs 0.7.3 : MAJ → MIN**, comme le re-audit l'avait annoncé une fois les deux textes corrigés.

- **Corrigé** par `6cb61d3` :
  - `README.md:31` : « no authentication: keep port 3000 private » ;
  - `frontend/src/shared/i18n.ts:415-416` (FR) et `:1137-1138` (EN) : « bloque le DNS rebinding, pas
    le réseau : sans authentification, gardez le port privé » ;
  - `McpConfigSection.vue:410-411` : le commentaire n'affirme plus l'isolement réseau.

  Restent exacts : `infra/settings.py:90-97`, `CHANGELOG.md:15`, `docs/mcp-server.md:14-20,324-331`,
  `.env.example:102-113`, et le log `bootstrap/mcp_mount.py:120-124`.
- **Reste** :
  - le défaut est inchangé : `infra/settings.py:97,256-259` (MCP actif), `docker-compose.yml:193` et
    `:205-206` (`"3000:80"`), `README.md:17` et `docs/getting-started.md:14,28,42,102` (`-p 3000:3000`) ;
  - dans le panneau, le cas par défaut garde l'icône bouclier sans style `warn`
    (`McpConfigSection.vue:55-59`) ;
  - la colonne « Adresses acceptées » / « Accepted addresses » (`i18n.ts:465,1186`) peut se lire comme
    une liste d'IP clientes ;
  - deux design docs affirment encore « localhost only » :
    `docs/design/364-mcp-admin-panel-section.md:216` et
    `docs/design/363-mcp-chunkless-rag-simplification.md:74`. Ce sont des archives, mais publiées.
- **Règle violée** : 8.4 (exposition par défaut). Écart additionnel, sans impact de score.
- **Remédiation** : publier `127.0.0.1:3000:80` en compose et `-p 127.0.0.1:3000:3000` dans le README
  et le guide de démarrage, ce qui lève l'écart. Le jeton `MCP_TOKEN` reste pour la 0.8.0.

### [MIN] Risque accepté : 4 CVE CRITICAL de Pillow 10.4.0 supprimées jusqu'au 2026-12-31, toujours sans issue qui livre le correctif

**Statut vs 0.7.3 : inchangé.** Le commentaire nomme désormais le plafond `pillow<11` de Studio
(`d81deb0`), mais l'issue demandée n'existe pas.

- **Localisation** :
  - `.trivyignore.yaml:21-56` ;
  - `document-parser/pyproject.toml:14` (`pillow>=10.0.0,<11.0.0`) ;
  - `CHANGELOG.md:34`.
- **Constat** : la justification reste exacte (vérifiée au re-audit, code inchangé). En revanche :
  - aucune issue ne livre Pillow 13. Les 30 dernières issues ont été listées par l'API REST, jusqu'à
    #369 : aucune ne porte sur Pillow ;
  - #361 n'a ni milestone ni mise à jour depuis le 2026-10-20. Elle vise docling-core 2.102.0 et
    docling-ibm-models 4.0.3, sous les seuils de `.trivyignore.yaml:22-25`, et exclut de toucher
    `pyproject.toml` ;
  - les 5 suppressions expirent le même jour (voir 8.5.1).

  La synthèse 0.7.3 demandait cette issue « avant l'expiration ».
- **Règle violée** : 8.5.1, défense en profondeur. Item conforme par acceptation de risque datée.
- **Remédiation** : ouvrir l'issue au milestone 0.8.0, avec docling ≥ 2.142, docling-core ≥ 2.104,
  docling-parse ≥ 7.22.4, docling-ibm-models ≥ 4.0.4 **et** `pillow>=13,<14`. La référencer dans
  `.trivyignore.yaml`. Si la 0.8.0 n'est pas prête au 2026-12-31, re-justifier les entrées avant cette
  date.

### [MIN] Dépendances Python : avis connus avec correctif disponible, non appliqués ; deux plafonds propres à Studio bloquent les correctifs

**Statut vs 0.7.3 : nouveau.** C'est la première mesure pip-audit réelle : en 0.7.3, pip-audit n'avait
pas pu tourner localement. Le constat prolonge l'ancien [INFO] « plafonds Pillow / cryptography ».

- **Localisation** :
  - `document-parser/pyproject.toml:20` (`cryptography>=43.0.0,<46.0.0`, verrouillé 45.0.7 :
    `uv.lock:626-627`). Seuls Studio et PyJWT en dépendent, et seul Studio la plafonne ;
  - `uv.lock:1019-1020` (filelock 3.32.3, via huggingface-hub et torch) ;
  - `:3708-3709` (transformers 5.8.1, via docling-core[chunking]) ;
  - `:692-693,817-818` (docling et docling-slim 2.121.0, image `local`).
- **Constat** : voir le tableau 8.5.1. Pertinence pour Studio :
  - **cryptography** : 7 avis. Courbe EC non validée, contraintes de noms X.509, buffers non contigus,
    PKCS7, et OpenSSL embarqué dans la roue (avis OpenSSL du 2026-06-09, corrigé en 48.0.1). Studio
    n'utilise que Fernet (`infra/secrets/fernet_box.py:31`), donc l'exposition est faible. Mais le
    plafond `<46` empêche tout correctif ;
  - **docling local** : correctifs en 2.131 / 2.132 (#361 vise 2.140). Les backends concernés (HTML,
    JATS, ODS, METS-GBS, LaTeX, plugins, `JSON_DOCLING`) ne sont pas atteints par l'upload, filtré par
    magic `%PDF` (voir [INFO] convertisseur) ;
  - **transformers / filelock** : chemins (`save_pretrained`, `load_custom_generate`, verrous SQLite /
    Windows) non utilisés par Studio. Non démontré atteignable.
  - La sévérité n'a pas pu être lue (voir Méthode).
- **Règle violée** : 8.5.1 (hygiène). Aucune CRITICAL établie : item non impacté.
- **Remédiation** :
  - relever le plafond (`cryptography>=48.0.1,<51`) puis `uv lock --upgrade-package cryptography` ;
  - `uv lock --upgrade-package filelock transformers` si les contraintes amont le permettent (non
    vérifié) ;
  - livrer #361.

### [MIN] Écritures de config MCP sans authentification : bascule du serveur et réécriture de la base des deep links

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/api/config.py:80-103` ; `domain/mcp_config.py:94-104` (schéma
  `http(s)` et `netloc` seulement) ; `services/citation_service.py:279-292`. 403 sur Hugging Face
  (`bootstrap/builder.py:255`).
- **Constat** : `PUT /api/config/mcp` peut rallumer ou éteindre le serveur, et pointer
  `studioBaseUrl` vers un hôte tiers. La valeur est persistée. Atteignable aussi par rebinding (voir le
  [MAJ] `Host`).
- **Règle violée** : 8.2.1 (défense en profondeur). Item conforme.
- **Remédiation** : rendre `MCP_STUDIO_BASE_URL` restart-only, ou le limiter à une liste d'hôtes ;
  journaliser chaque changement en WARNING.

### [MIN] Rate limiter « par IP » : global derrière nginx, et contournable par `X-Forwarded-For` dans l'image tout-en-un

**Statut vs 0.7.3 : code inchangé, constat précisé.** Le contournement n'avait pas été relevé.

- **Localisation** :
  - `document-parser/infra/rate_limiter.py:71` (`request.client.host`) et `:65` (seaux jamais purgés) ;
  - `Dockerfile:65` (uvicorn sur 127.0.0.1, options proxy par défaut) ;
  - `nginx.conf.template:17-20,29-33` (aucun `X-Forwarded-For` posé ni effacé, donc l'en-tête du
    client est transmis tel quel) ;
  - uvicorn 0.52.4 : `config.py:220` (`proxy_headers=True`), `:357` (`FORWARDED_ALLOW_IPS` vaut
    `127.0.0.1` par défaut).
- **Constat (démontré sur le middleware uvicorn)** :

  | Pair | En-tête | `request.client` |
  |------|---------|------------------|
  | 127.0.0.1 (nginx dans le même conteneur) | `X-Forwarded-For: 203.0.113.7` | `('203.0.113.7', 0)` |
  | 127.0.0.1 | aucun | `('127.0.0.1', …)` |
  | 172.18.0.3 (nginx d'un autre conteneur, compose) | `X-Forwarded-For` | `('172.18.0.3', …)` |

  Conséquences :
  - **image tout-en-un** (`docker run`, quick-start du README) : un client honnête partage le seau
    unique de 127.0.0.1, ce qui permet un DoS par 429 global. Un client malveillant change de seau à
    chaque requête en changeant l'en-tête, ce qui contourne la limite. Chaque valeur neuve ajoute une
    entrée jamais purgée à `_buckets`, d'où une croissance mémoire lente ;
  - **compose** : l'en-tête est ignoré, et le seau reste global.
- **Règle violée** : 8.4.2 (sémantique). L'item est conforme : le middleware est actif partout sauf
  `/api/health`.
- **Remédiation** (effort **XS**, risque faible) :
  - ajouter `proxy_set_header X-Forwarded-For $remote_addr;` dans `/api/` et `/mcp` des deux templates,
    pour écraser et non ajouter. L'image tout-en-un limite alors par IP réelle ;
  - en compose, `--forwarded-allow-ips` sur l'IP du conteneur nginx ;
  - purger les seaux vides.

### [MIN] `npm audit` (production) : 7 HIGH, 0 CRITICAL

**Statut vs 0.7.3 : inchangé** (`{high: 7, critical: 0}` le 2026-11-03).

- **Localisation** : `frontend/package.json:22` (dompurify `^3.3.3`), `:25` (vue `^3.4.0`) ;
  transitives lodash ≤ 4.17.23 (via cytoscape-dagre), postcss ≤ 8.5.22, nanoid ≤ 3.3.17,
  source-map-js 1.0.0-1.2.1, @vue/server-renderer ≤ 3.5.41.
- **Constat** :
  - le seul avis DOMPurify classé HIGH (GHSA-mrv2-3pqr-j5jr) vise `IN_PLACE` avec des hooks ;
  - `MarkdownViewer.vue:24` appelle `sanitize(html)` sans option ;
  - l'avis Vue vise le SSR, non utilisé ;
  - lodash `_.template` n'est pas appelé par Studio.

  Correctifs disponibles (`fixAvailable: true` pour les 7).
- **Règle violée** : hygiène. 8.5.1 non impacté.
- **Remédiation** : `npm audit fix` (dompurify ≥ 3.4.17, vue ≥ 3.5.42), puis vitest et build.

### [MIN] Dépendances backend sans version : torch / torchvision

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/pyproject.toml:42-43`.
- **Constat** : `torch` et `torchvision` sans spécificateur. Atténuants : `uv.lock` est utilisé en
  `--frozen` (`Dockerfile:42,103-105`), groupe `local`. Versions verrouillées : `2.13.0+cpu` et
  `0.28.0+cpu`.
- **Règle violée** : 8.5.2.
- **Remédiation** : `torch>=2.13,<3` et `torchvision>=0.28,<1`, puis `uv lock`. Les versions
  verrouillées satisfont déjà ces bornes.

### [INFO] SSRF Ollama : garde intacte, résidus inchangés

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/infra/llm/ollama_probe.py:60` puis `:87-88` (TOCTOU), `:69-72`
  (loopback et LAN autorisés) ; `domain/app_config.py:77-86` (Save : schéma seul) ; documenté dans
  `SECURITY.md:48`.

### [INFO] API sans authentification

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/main.py:89-125` ; `SECURITY.md:51`.
- **Constat** : socle des trois [MAJ] ci-dessus.

### [INFO] Pas de garde-fou contre `CORS_ORIGINS="*"` avec credentials

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `document-parser/infra/settings.py:199,243` ; `main.py:92`.

### [INFO] nginx : processus maître en root, pas de Content-Security-Policy

**Statut vs 0.7.3 : inchangé.**

- **Localisation** : `frontend/Dockerfile:9-16` (`nginx:alpine`, sans `USER`) ; `Dockerfile:65` ;
  `frontend/nginx.conf.template:7-11` et `nginx.conf.template:7-11`.

### [INFO] Convertisseur docling local : tous les formats d'entrée acceptés ; seul le contrôle `%PDF` en amont restreint au PDF

**Statut vs 0.7.3 : nouveau.** Il corrige une affirmation du re-audit 0.7.3 (« le convertisseur local
ne configure que `InputFormat.PDF` »).

- **Localisation** : `document-parser/infra/local_converter.py:71-75`
  (`DoclingConverter(format_options={InputFormat.PDF: …})`, sans `allowed_formats`) ;
  `docling/document_converter.py:380-381` (docling-slim 2.121.0 : `allowed_formats` vaut
  `list(InputFormat)` par défaut).
- **Constat** : `format_options` ne restreint pas les formats. Le seul filtre est le magic `%PDF` et
  l'extension `.pdf` forcée (`services/document_service.py:78-81`). Il est efficace aujourd'hui pour
  l'upload. Mais plusieurs avis docling 2.121.0 visent des backends non-PDF, dont
  GHSA-p944-4xh2-x776 (`JSON_DOCLING`, lecture d'images locales) : le jour où un autre chemin appellera
  le convertisseur, ils seront atteignables.
- **Remédiation** : `DoclingConverter(allowed_formats=[InputFormat.PDF], format_options=…)`. Une ligne.

### [INFO] Clients OpenSearch des stores sans vérification TLS

**Statut vs 0.7.3 : nouveau** (non relevé auparavant).

- **Localisation** : `document-parser/infra/opensearch_pool.py:49,71` et
  `infra/opensearch_store.py:80,90` (`verify_certs: bool = False`).
- **Constat** : le mot de passe d'un store, scellé au repos par Fernet, part en Basic auth vers un
  endpoint `https` dont le certificat n'est pas vérifié, donc exposé à un MITM. Surface d'ingestion
  dépréciée.
- **Remédiation** : `verify_certs=True` par défaut, avec option explicite par store si besoin, ou
  rien d'ici la suppression en 0.8.0.

### [INFO] Étapes de build sur Node 20, en fin de vie

**Statut vs 0.7.3 : nouveau.**

- **Localisation** : `Dockerfile:11` et `frontend/Dockerfile:1` (`node:20-alpine`, étape de build) ;
  `docker-compose.dev.yml:173` (frontend dev en `node:20-alpine`).
- **Constat** : Node 20 n'a plus de correctifs de sécurité depuis le 2026-04-30 (calendrier Node.js).
  Il n'est pas embarqué dans l'image finale, donc Trivy ne le voit pas. La CI tourne déjà en Node 22
  (`release-gate.yml:118`).
- **Remédiation** : `node:22-alpine` dans les trois emplacements.

---

## Delta vs 0.7.3 (re-audit)

Score : **97 → 97, inchangé.** Comptes : CRIT 0 → 0 ; MAJ 2 → 3 ; MIN 6 → 7 ; INFO 4 → 7.
La hausse ne vient d'aucune régression : le code est identique au tag. Elle vient d'analyses plus
poussées (sondes, pip-audit) sur du code existant.

| Écart 0.7.3 (re-audit) | Statut 0.7.4 | Preuve |
|------------------------|--------------|--------|
| [MAJ] MCP « localhost only » dans le README et le panneau ; défaut inchangé | **Corrigé en partie → [MIN]** (textes exacts ; défaut inchangé) | `6cb61d3` ; `README.md:31` ; `i18n.ts:415-416,1137-1138` ; `docker-compose.yml:205-206` |
| [MAJ] `/api/*` sans validation du `Host` | **Inchangé, ouvert** ; remédiation évaluée | `main.py:89-101` |
| [MIN] Pillow : risque accepté, sans issue | **Inchangé** ; le commentaire nomme le plafond `<11` ; l'issue n'a pas été créée | `.trivyignore.yaml:21-26` (`d81deb0`) |
| [MIN] Écritures config MCP | **Inchangé** | `api/config.py:80-103` |
| [MIN] Import JSON sans plafond | **Aggravé → [MAJ]** (amplification démontrée) | `table_data.py:105-128` ; sonde |
| [MIN] Rate limiter global | **Inchangé, constat précisé** (contournable par XFF dans l'image tout-en-un) | `Dockerfile:65` ; `nginx.conf.template:17-20` |
| [MIN] npm 7 HIGH | **Inchangé** | `npm audit --omit=dev` |
| [MIN] torch / torchvision (8.5.2) | **Inchangé** | `pyproject.toml:42-43` |
| [INFO] SSRF Ollama, résidus | **Inchangé** | `ollama_probe.py:60,69-72,87-88` |
| [INFO] API sans authentification | **Inchangé** | `SECURITY.md:51` |
| [INFO] Pas de garde `CORS_ORIGINS="*"` | **Inchangé** | `settings.py:199,243` |
| [INFO] nginx root / pas de CSP | **Inchangé** | `frontend/Dockerfile:9-16` |

Nouveaux : [MAJ] SSRF des stores ; [MIN] dépendances Python (pip-audit) ; [INFO] convertisseur docling
tous formats ; [INFO] OpenSearch `verify_certs=False` ; [INFO] Node 20 en fin de vie.

Corrections de suivi vérifiées (`55d32be`) : `fail-fast: false` sur la matrice de scan
(`release-gate.yml:339-341`) ; avertissement si pip-audit ne produit pas de rapport (`:143-144`) ;
libellé « npm CRITICAL only » dans le résumé. Aucune régression.

---

## Quick wins

Seul 8.5.2 fait bouger le score. Les autres actions retirent des écarts sans changer la note, puisque
leurs items sont déjà conformes.

| Action | Item | Gain de score | Effet sur les écarts | Effort | Risque de régression |
|--------|------|---------------|----------------------|--------|----------------------|
| Borner `torch>=2.13,<3`, `torchvision>=0.28,<1` (`pyproject.toml:42-43`) + `uv lock` | 8.5.2 (poids 1) | **+3 (97 → 100)** | −1 MIN | XS | nul : versions verrouillées inchangées ; vérifier `uv lock --check` |
| Plafond de cellules par table dans `DoclingDocumentImporter` (+ plafond de corps) | 8.2.1 / 8.2.2 (déjà conformes) | 0 | −1 MAJ | S | faible (seuil généreux) |
| `_resolved_target_is_blocked` + `read_only` HF sur les stores | 8.2.1 (conforme) | 0 | −1 MAJ | S | faible (surface dépréciée) |
| `proxy_set_header X-Forwarded-For $remote_addr;` (2 templates × 2 locations) | 8.4.2 (conforme) | 0 | rend le rate limiter effectif dans l'image tout-en-un | XS | faible |
| `allowed_formats=[InputFormat.PDF]` (`local_converter.py:71`) | 8.2.3 (conforme) | 0 | −1 INFO | XS | nul (seul le PDF est accepté en amont) |
| `npm audit fix` | 8.5.1 (conforme) | 0 | −1 MIN | S | faible à modéré (vue 3.5.30 → ≥ 3.5.42 ; lancer vitest et build) |
| Relever `cryptography<46` → `>=48.0.1,<51` | 8.5.1 (conforme) | 0 | réduit le MIN dépendances | S | faible (Fernet stable) |
| Créer l'issue « docling → Pillow 13 » (milestone 0.8.0) | 8.5.1 | 0 (protège contre −8 au 2026-12-31) | prérequis du MIN Pillow | XS | nul |
| `127.0.0.1:3000:80` en compose, `-p 127.0.0.1:3000:3000` dans le README et le guide | 8.4 | 0 | −1 MIN (MCP) ; réduit aussi la surface du MAJ `Host` | XS | moyen pour qui accède par le LAN (à annoncer) |
| Garde `Host` sur `/api/*` (voir évaluation) | 8.4 | 0 | −1 MAJ | M | moyen (BREAKING pour l'accès LAN / domaine) |

---

## Points positifs

- **Remédiation 0.7.3 tenue** : les textes MCP sont exacts partout où l'opérateur les lit (README,
  panneau, docs, CHANGELOG, `.env.example`, log de montage). Le gate scanne les deux images même si
  l'une échoue (`fail-fast: false`).
- **Aucune suppression Trivy expirée** ; chaque entrée est justifiée et datée, et le CHANGELOG annonce
  le risque accepté.
- **Surface MCP** (code inchangé, analyse 0.7.3 reprise) : outils en lecture seule, identifiants
  uniquement, sorties plafonnées, `neutralise()` contre l'injection de prompt, erreurs masquées,
  anti-rebinding testé (421).
- **Entrées** : upload borné et vérifié par magic bytes ; SQL en paramètres liés, `LIKE` échappé ;
  labels Cypher tirés d'une table fixe ; un seul `v-html`, assaini ; `preview` borné
  (`dpi` 72-300, `page ≥ 1`, `api/documents.py:168-169`).
- **Secrets** : aucun secret en dur ; mots de passe des stores scellés par Fernet et jamais renvoyés ;
  build-args sans secret ; backend non-root.
- **Garde SSRF Ollama** toujours en place, et écritures reasoning et MCP refusées en 403 sur Hugging
  Face.

---

## Verdict partiel : GO

- **Score 97/100 ≥ 80, 0 CRITICAL, 3 MAJOR (≤ 3)** → **GO**.
- Les 3 MAJ ne bloquent pas seuls, mais atteignent le seuil : un MAJ de plus ferait basculer le
  verdict.
- Deux d'entre eux (import, stores) se corrigent en quelques lignes, à risque faible. Ils sont
  recommandés **avant le tag** : le premier arrête le backend avec moins de 1 Ko, le second ouvre la
  démo publique comme pivot SSRF.
- Le MAJ `Host` relève d'un changement BREAKING (effort M) : à planifier, avec sa note de migration.

Conditions :
1. Le Release Gate 0.7.4 doit être vert sur les **deux** scans Trivy. La base Trivy a pu évoluer depuis
   le run `41468347487` (2026-11-02) ; aucun scan n'a tourné depuis.
2. Le gate doit tourner **avant le 2026-12-31**, date d'expiration commune des 5 suppressions. Sinon,
   8.5.1 bascule en [CRIT] : 89/100, **NO-GO**.
3. Ouvrir l'issue « docling → Pillow 13 » au milestone 0.8.0, attendue depuis la synthèse 0.7.3.
