# Rapport d'audit : Sécurité (re-audit)

**Release** : 0.7.4 (re-audit après remédiation)
**Date** : 2026-11-03
**Auditeur** : claude-code
**Branche** : `claude/nifty-turing-fmn3wo` @ `a4d9679` (100 commits de remédiation depuis `e6047c2` ;
les commits suivants, `a2a10ac` et `4c59df0`, n'ajoutent que des rapports d'audit)

Baseline : `reports/release-0.7.4/08-security.md` (**97/100**, 0 CRIT, 3 MAJ, 7 MIN, 7 INFO, code
audité `1de1929`, rapport commité en `e6047c2`).

**Même lecture des items qu'en 0.7.4.** Le score reste strictement adossé à la checklist ; les
écarts hors checklist (exposition réseau, déni de service, SSRF, fuite d'identifiants) sont reportés
comme écarts réels sans faire basculer d'item, comme en 0.7.0, 0.7.3 et 0.7.4.

Méthode :
- Lecture du code à `a4d9679`. Chaque écart 0.7.4 est re-vérifié dans le code, pas dans les messages
  de commit. Recherche de régressions dans les fichiers ajoutés ou modifiés
  (`git diff --stat e6047c2..HEAD`), en particulier `infra/ssrf_guard.py`, `infra/file_storage.py`,
  `infra/docling_importer.py`, `api/errors.py`, `services/errors.py`, `services/store_service.py`,
  `services/chunk_push_service.py`, les deux templates nginx, `SECURITY.md`, `.dockerignore`.
- Commandes de la fiche 08 relancées (grep secrets, SQL, `eval/exec`, `v-html`, CORS, `.env`).
- Dépendances, en lecture seule : `npm audit --omit=dev` et `npm audit` (toutes dépendances) dans
  `frontend/` ; `uv export --frozen --no-dev [--group local --group reasoning] --no-hashes` vers le
  scratchpad, puis `uvx pip-audit -r … --no-deps --disable-pip` (format JSON).
- Quatre sondes ciblées, hors dépôt (scratchpad), avec le venv du projet (docling-core 2.92.0,
  uvicorn 0.52.4, neo4j 5.28.4, conformes à `uv.lock`) et `ulimit -v` :
  1. plafond d'import : tables, puis tables cachées dans les images (`pictures[].meta`,
     `pictures[].annotations`), références répétées, cycle de groupes, volume ;
  2. garde SSRF : formes alternatives d'adresse (IPv4 mappée en IPv6, décimal, octal, NAT64,
     `0.0.0.0`, `::`), sous Python 3.13 (venv) et 3.12 (version de l'image) ;
  3. `ProxyHeadersMiddleware` d'uvicorn avec `$proxy_add_x_forwarded_for` ;
  4. résolution d'un store Neo4j vers un faux serveur Bolt sur 127.0.0.1 (identifiants envoyés).
- État GitHub lu une fois par l'API REST : runs, issues, protection de `main`.

Non fait / non vérifiable : pas de démon Docker ni de Trivy dans le bac à sable, donc aucun scan
d'image ni build. `api.osv.dev` et `/advisories` de l'API GitHub sont refusés : la **sévérité** des
avis pip-audit n'a pas pu être lue. Application complète non lancée (sondes au niveau des fonctions,
comme en 0.7.4). Suites complètes non relancées : résultats du coordinateur sur HEAD, pytest
1673 passed / 19 skipped, vitest 522 passed, ruff, eslint, prettier, vue-tsc, build OK,
`npm audit --omit=dev` 0 vulnérabilité. `git status` propre après les sondes.

---

## Score de compliance

| Métrique | 0.7.4 | Re-audit |
|----------|-------|----------|
| Items conformes | 13 / 14 | **14 / 14** |
| Score | 97 / 100 | **100 / 100** |
| Écarts CRITICAL | 0 | 0 |
| Écarts MAJOR | 3 | **3** |
| Écarts MINOR | 7 | 6 |
| Écarts INFO | 7 | 8 |

Détail du calcul : poids total = 3+3+2 + 3+3+2 + 3+3+3 + 3+2+2 + 3+1 = **36**. L'item 8.5.2 (poids 1),
seul non conforme en 0.7.4, est corrigé. **Score = 36 / 36 = 100.**

Les 3 [MAJ] ne sont pas les mêmes qu'en 0.7.4 : le MAJ SSRF des stores est corrigé (résidus en
[MIN]), le MAJ import n'est corrigé qu'en partie (contournement démontré), et un MAJ **nouveau**
apparaît sur le même code des stores (fuite du mot de passe Neo4j de l'environnement, démontrée).
Ce dernier est antérieur à la remédiation (#279, 0.6.1) : ce n'est pas une régression.

**Sensibilité du score** : 8.5.1 reste adossé au dernier gate vert (run `41468347487`,
2026-11-02). Aucun scan Trivy n'a tourné depuis. Le prochain gate scannera pour la première fois
les 20 paquets du groupe `reasoning` (le build `local` du gate passe `WITH_REASONING=true`). Une
CRITICAL dans ce groupe, ou un scan lancé après le 2026-12-31 (expiration des 5 suppressions), fait
basculer 8.5.1 : 33/36 = **92**, 1 CRIT, **NO-GO**.

---

## Vérification par item

| # | Item | Poids | Conforme | Preuve (@ `a4d9679`) |
|---|------|-------|----------|----------------------|
| 8.1.1 | Aucun secret en dur | 3 | **Oui** | grep fiche 08 : vide (affectations depuis l'env ou paramètres). `git grep` des motifs `sk-…`, `ghp_…`, `hf_…`, `AKIA…`, `BEGIN … PRIVATE KEY` : vide. `git ls-files` : seul `.env.example`. `NEO4J_PASSWORD=changeme` reste un défaut dev documenté (`infra/settings.py:52,268`, avertissement `bootstrap/factories.py:153`) |
| 8.1.2 | `.env` dans `.gitignore` | 3 | **Oui** | `.gitignore:26-28` ; en plus `.dockerignore:25-26` (`**/.env`, `**/.env.*`), `frontend/.dockerignore:17-18` |
| 8.1.3 | Secrets Docker par env | 2 | **Oui** | ARG : `APP_VERSION`, `BAKE_MODELS`, `WITH_REASONING` (`Dockerfile:13,24,89,94` ; `document-parser/Dockerfile:62,67`). Build-args du gate (`release-gate.yml:270-272`) et de la publication (`release.yml:76-79`) sans secret |
| 8.2.1 | Entrées validées par Pydantic | 3 | **Oui** | 51 routes, inchangées ; grep `request.json/body/form` vide. Import : `ImportAnalysisRequest` puis `DoclingDocument.model_validate` (`infra/docling_importer.py:81`). Bornes : voir [MAJ] import |
| 8.2.2 | `MAX_FILE_SIZE_MB` appliqué | 3 | **Oui** | `api/documents.py:65-79` (Content-Length puis lecture par morceaux, 413) ; double contrôle `services/document_service.py:130-131` |
| 8.2.3 | Types de fichiers validés | 2 | **Oui** | magic `%PDF` (`services/document_service.py:37,133-134`), suffixe `.pdf` (`:275`) ; **convertisseur limité au PDF** (`infra/local_converter.py:76`, `allowed_formats=[InputFormat.PDF]`) |
| 8.3.1 | SQL en paramètres liés | 3 | **Oui** | f-strings limitées à des constantes et à des `?` : `persistence/document_repo.py:83,108`, `chunk_repo.py:170` (clause constante), `analysis_repo.py:64-136` ; `LIKE` échappé (`document_repo.py:80`) |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | **Oui** | grep `eval(`, `exec(`, `os.system(`, `subprocess.`, `shell=True`, `pickle.load`, `yaml.load(`, `__import__(`, `create_subprocess` : vide (hors `.venv`, tests) |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | **Oui** | seul `v-html` : `frontend/src/shared/ui/MarkdownViewer.vue:3`, assaini `:24`. Cartes MCP : changements de libellés et de mise en page seulement, toujours via `esc()` (`citation_app.html:587-607`) |
| 8.4.1 | CORS explicite | 3 | **Oui** | `main.py:91-97` ; défaut localhost (`infra/settings.py:86,283`) ; grep `allow_origins.*\*` vide |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | **Oui** | `main.py:98-103` ; exclusion `infra/rate_limiter.py:59,68`. Contournement `X-Forwarded-For` de l'image tout-en-un corrigé : voir [MIN] rate limiter |
| 8.4.3 | Nginx sans directory listing | 2 | **Oui** | `nginx.conf.template:23-25,39-45` et `frontend/nginx.conf.template` (identiques au port et au backend près) ; grep `autoindex` vide. `/assets/` manquant → 404 au lieu du shell |
| 8.5.1 | Pas de CVE critique connue | 3 | **Oui** (adossé au dernier gate vert) | voir détail ci-dessous |
| 8.5.2 | Versions épinglées | 1 | **Oui** (corrigé) | `document-parser/pyproject.toml:44-45` (`torch>=2.13.0,<3.0.0`, `torchvision>=0.28.0,<1.0.0`) ; `uv.lock:934-935` ; versions verrouillées inchangées. Plus aucun `>=` sans borne (seul `requires-python`). `frontend/package.json` : aucun `*`, `latest` ni `>=` |

### Détail 8.5.1

**`.trivyignore.yaml`** : inchangé depuis `e6047c2`. 5 suppressions (`CVE-2026-6653` libxml2 ;
`CVE-2026-112393/112398/112403/112900` Pillow 10.4.0), toutes `expired_at: 2026-12-31`
(`:20,38,44,50,56`), soit **J+58**. Aucune expirée.

**Gate** : aucun Release Gate depuis le run `41468347487` (2026-11-02, 13/13). Le run suivant
(`41625312292`, 2026-11-03) a été annulé. Aucun run n'existe sur cette branche (pas de PR).

**pip-audit (2026-11-03, lock `--frozen`)** : identique à 0.7.4.

| Périmètre | Résultat | Paquets |
|-----------|----------|---------|
| Image `remote` | 93 avis, 4 paquets | pillow 10.4.0 (66), cryptography 45.0.7 (13 entrées), filelock 3.32.3 (12), transformers 5.8.1 (2) |
| Image `local` (+ `local` + `reasoning`) | 111 avis, 9 paquets | ceux du remote + docling 2.121.0 (8), docling-slim 2.121.0 (7), accelerate 1.14.0 (1, sans correctif), nltk 3.10.3 (1, **correctif 3.10.4 désormais publié**), setuptools 84.0.0 (1). `torch`/`torchvision` `+cpu` non audités (absents de PyPI) |

Sévérité non lisible (voir Méthode). **Conforme**, avec la réserve de la sensibilité ci-dessus.

**npm** : `npm audit --omit=dev` → **0** (était 7 HIGH). Toutes dépendances : 1 HIGH (vite, dev
seulement) et 17 MODERATE (chaîne eslint / vitest / vue-tsc), voir [INFO] npm dev.

---

## Écarts constatés

### [MAJ] `/api/*` sans validation du `Host` : DNS rebinding possible contre une instance locale

**Statut vs 0.7.4 : inchangé, ouvert — décision laissée au mainteneur** (changement cassant).

- **Localisation** : `document-parser/main.py:91-103` (seuls `CORSMiddleware` et
  `RateLimiterMiddleware`) ; grep `TrustedHost|API_ALLOWED_HOSTS` vide dans `document-parser/` ;
  `nginx.conf.template:1-2` et `frontend/nginx.conf.template:1-2` (pas de `server_name`) ;
  `:54` (`proxy_set_header Host $host`).
- **Constat** : inchangé (voir le rapport 0.7.4, qui évalue la remédiation `API_ALLOWED_HOSTS`). La
  surface atteignable par rebinding s'est réduite d'un côté (test de connexion des stores ne renvoie
  plus le texte de l'exception, cibles link-local refusées) et confirmée de l'autre : un rebinding
  peut créer un store Neo4j vers son propre hôte et récupérer le mot de passe Neo4j de l'instance
  (voir [MAJ] identifiants Neo4j). **PLAUSIBLE**, dépend du navigateur.
- **Règle violée** : 8.4 (réseau). Écart additionnel, sans impact de score.
- **Remédiation** : celle évaluée en 0.7.4 (middleware `API_ALLOWED_HOSTS`, effort M, BREAKING pour
  l'accès LAN ou par domaine).

### [MAJ] Import Docling : le plafond ne compte que `document.tables` ; une table cachée dans une image garde l'amplification (751 octets → 25 s, 350 Mo)

**Statut vs 0.7.4 : partiellement corrigé.** Le vecteur démontré en 0.7.4 (tables) est fermé ; le
même vecteur reste ouvert par les données de graphique des images.

- **Corrigé** :
  - `infra/docling_importer.py:33-64` : `_check_table_budget` compte les cellules déclarées
    (`rows × cols`, dimensions négatives bornées à 0) et les positions couvertes par les cellules
    (`_filled_slots`, même bornage que docling-core), appelé après `model_validate` et avant tout
    export (`:84`) ; `ValueError` → 400 (`api/analyses.py:139-145`) ;
  - `MAX_IMPORT_TABLE_CELLS` (défaut 100 000, `0` = sans limite, négatif refusé au démarrage) :
    `infra/settings.py:40,155-157,257` ; passé par les deux compose ; documenté
    (`docs/configuration.md:31`, `.env.example`, `SECURITY.md`) ;
  - plafond de corps 200 Mo sur tout le routeur `/api/analyses` : `api/analyses.py:35,45-82`
    (Content-Length refusé d'emblée, corps chunked compté) ; tests
    `tests/test_api_endpoints.py:248-259,750-790`, `tests/test_docling_importer.py:60-127` ;
  - sonde de contrôle : table `400 × 400` (710 o) → **refusée en 0,00 s**.
- **Contournement (démontré)** : docling-core 2.92.0 porte d'autres `TableData`, dont la grille est
  aussi un `@computed_field` construit à chaque export :
  - `PictureMeta.tabular_chart.chart_data` (`docling_core/types/doc/items/picture/meta.py:44-48,56`) ;
  - `PictureTabularChartData.chart_data` (`…/picture/charts.py:169`), annotation historique migrée
    vers `meta` au chargement (`…/picture/picture.py:120-124`), et alors exportée deux fois.

  `_check_table_budget` ne parcourt que `document.tables` (`docling_importer.py:49`). Sonde
  `DoclingDocumentImporter(max_table_cells=100_000).deserialize(...)`, une image avec
  `{"table_cells": [], "num_rows": n, "num_cols": n}` :

  | Vecteur | n | Corps JSON | Temps | Pic tracemalloc | `document_json` stocké | Résultat |
  |---------|---|------------|-------|-----------------|------------------------|----------|
  | `tables[0].data` | 400 | 710 o | 0,00 s | 0 Mo | — | **refusé** (400) |
  | `pictures[0].meta.tabular_chart.chart_data` | 100 | 751 o | 1,4 s | 24 Mo | 2,4 Mo | accepté |
  | `pictures[0].meta.tabular_chart.chart_data` | 400 | 751 o | **24,9 s** | **350 Mo** | **38,5 Mo** | **accepté** |
  | `pictures[0].annotations[tabular_chart_data]` | 200 | 766 o | 7,9 s | 173 Mo | 19,2 Mo | accepté (grille ×2) |

  Coût identique à celui mesuré en 0.7.4 (≈ 2,2 Ko et 0,1 ms par cellule, linéaire) : vers
  n ≈ 1 350, la limite de 4 Go du conteneur est atteinte (**extrapolé, non exécuté**). Route active
  aussi sur le Space HF (pas de garde `read_only`, comme en 0.7.4).
- **Résidu de volume (mesuré puis extrapolé)** : sans aucune table, un document de petits items
  texte coûte, entre `json.loads` et la fin de `deserialize`, **≈ 33 fois sa taille** en mémoire
  Python et ≈ 6 s par Mo, linéairement (5 000 / 10 000 / 20 000 / 40 000 items : 0,9 / 1,8 / 3,7 /
  7,3 Mo → 32 / 62 / 121 / 240 Mo, 5,8 / 11 / 21 / 43 s). Le plafond de corps retenu (200 Mo,
  aligné sur nginx) dépasse donc ce que le conteneur de 4 Go peut importer : autour de 120 Mo de
  JSON (**PLAUSIBLE**, extrapolé ; le RSS réel est supérieur à tracemalloc). La 0.7.4 proposait
  un plafond aligné sur `MAX_FILE_SIZE_MB` (50 Mo).
- **Ce qui reste sain** : références répétées au même item (dédupliquées : 67 Ko → 0,85 s,
  4 Mo) ; cycle de groupes refusé par la validation (400).
- **Règle violée** : 8.2.1 / 8.2.2 dans leur esprit. Items conformes au sens strict. Écart
  additionnel, sans impact de score.
- **Remédiation** (effort **S**, risque **faible**) :
  1. compter toutes les grilles du document, pas seulement les tables : par exemple itérer
     `document.iterate_items()` / `document.pictures` et ajouter
     `picture.meta.tabular_chart.chart_data` et chaque `annotation.chart_data`, ou parcourir tout
     objet `TableData` du modèle validé ; le message et `MAX_IMPORT_TABLE_CELLS` restent les mêmes ;
  2. test : une image dont `meta.tabular_chart.chart_data` déclare `10**6 × 10**6` → 400 immédiat ;
     idem par `annotations` ;
  3. abaisser le plafond de corps de l'import (par exemple `MAX_FILE_SIZE_MB`, ou une variable
     dédiée), et mettre à jour `docs/configuration.md:31` et `SECURITY.md`.

### [MAJ] [NOUVEAU] Le mot de passe Neo4j de l'environnement part vers l'URI choisie par l'appelant

**Statut vs 0.7.4 : nouveau constat**, sur du code antérieur (#279, 0.6.1). Le rapport 0.7.4
affirmait, pour le MAJ SSRF des stores, « aucune donnée exfiltrée au-delà de ce que l'API expose
déjà » : c'est inexact.

- **Localisation** :
  - `document-parser/services/store_backend_resolver.py:135` (URI du store en priorité), `:142-143`
    (`user = store.connection_username or env_user` ; `password = env_password`), `:144-148` (le
    mot de passe du store ne remplace celui de l'environnement que s'il existe) ;
  - `infra/neo4j/driver_pool.py:89-90` : `AsyncGraphDatabase.driver(uri, auth=(user, password))`
    puis `verify_connectivity()` **dès la résolution** ;
  - déclencheurs : `POST /api/stores` puis `POST /api/stores/{slug}/test-connection`
    (`services/store_service.py:386`) ; le push (`services/chunk_push_service.py:205`) ;
  - comportement figé par un test : `tests/test_store_backend_resolver.py:201-222`
    (`test_uses_env_password_when_store_has_no_seal`, store avec sa propre URI) ;
  - `bootstrap/factories.py:171-190` : le fallback est décrit comme « transitional fallback for the
    seeded `default` store and any pre-#279 row without its own credentials », mais il s'applique à
    tout store sans mot de passe, quelle que soit son URI.
- **Constat (démontré)** : faux serveur Bolt sur 127.0.0.1 (il accepte la version 4.4 et enregistre
  ce qu'il reçoit), `StoreBackendResolver` câblé comme `build_backend_resolver` (`Neo4jDriverPool`,
  `Neo4jGraphWriter`), `env_neo4j_password="EnvSecretPw-1234"`, store `kind=neo4j`,
  `connection_uri=bolt://127.0.0.1:<port>`, sans mot de passe → **le serveur reçoit `neo4j` et
  `EnvSecretPw-1234` en clair** (message HELLO, `bolt://` sans TLS).
  La garde SSRF n'y peut rien : une adresse publique n'est pas bloquée, par conception
  (`infra/ssrf_guard.py:20-30`). Quiconque atteint `/api` (pas d'authentification) crée un store
  vers son propre serveur et lance le test : il reçoit le `NEO4J_USER` / `NEO4J_PASSWORD` de
  l'instance. Par rebinding, une page web peut faire de même (voir [MAJ] `Host`, PLAUSIBLE).
- **Atténuants** : refusé sur le Space HF (`store_service.py:208,378-379`) ; sans valeur si
  `NEO4J_PASSWORD` est resté au défaut `changeme` ; ne concerne que les déploiements qui
  configurent Neo4j (graphe, ingestion dépréciée, supprimée en 0.8.0). OpenSearch n'a pas ce
  fallback (`store_backend_resolver.py:124-129` : identifiants du store uniquement).
- **Règle violée** : 8.1 (secrets) et 8.2.1 (défense en profondeur). Items conformes au sens strict.
  Écart additionnel, sans impact de score.
- **Remédiation** (effort **XS-S**, risque **faible**) :
  - dans `_resolve_neo4j`, n'utiliser `NEO4J_USER` / `NEO4J_PASSWORD` que lorsque l'URI utilisée est
    celle de l'environnement (store sans `connection_uri`, ou URI égale à `NEO4J_URI`) ; sinon,
    seulement les identifiants du store ;
  - réécrire `test_uses_env_password_when_store_has_no_seal` en conséquence, et ajouter le cas
    « URI du store, pas de mot de passe → pas de mot de passe d'environnement » ;
  - une ligne dans `SECURITY.md` (section Store connections) et le CHANGELOG ; un store créé avec
    sa propre URI qui comptait sur le mot de passe de l'environnement devra recevoir le sien.

### [MIN] [NOUVEAU] Stores : résidus de la garde SSRF (push sans re-vérification, texte d'exception renvoyé, retrait de lien non protégé sur HF)

**Statut vs 0.7.4 : le [MAJ] SSRF des stores est corrigé**, ce [MIN] en reprend les résidus.

- **Corrigé** (vérifié dans le code) :
  - garde partagée `infra/ssrf_guard.py:17-64` (même logique que la garde Ollama de 0.7.0,
    factorisée ; `UnicodeError` désormais attrapé), appliquée à la création
    (`services/store_service.py:219-220`), à la modification (`:299-301`) et **avant chaque test**
    (`:380-382`), hors de la boucle d'événements (`:348-352`) ; 422 à l'écriture ;
  - lecture seule sur HF : création, modification, suppression → 403 (`:208,262,446`), test refusé
    sans connexion (`:378-379`) ; câblage `bootstrap/builder.py:162-165` ;
  - le test ne renvoie plus `str(exc)` : message générique, détail dans le log (`:389-391,403-405`) ;
  - sonde : `169.254.169.254`, `[::ffff:169.254.169.254]`, `[::ffff:a9fe:a9fe]`, `2852039166`,
    `0251.0376.0251.0376`, `0.0.0.0`, `[::]`, `[fe80::1]`, `[64:ff9b::a9fe:a9fe]` → tous bloqués,
    sous Python 3.13 et 3.12 ; `localhost` et `10.0.0.5` autorisés (voulu) ;
  - documenté : `SECURITY.md` (section Store connections), CHANGELOG `[Unreleased]` (dont BREAKING
    HF). Tests : `tests/test_ssrf_guard.py`, `test_store_service.py`, `test_api_stores.py`.
- **Reste** :
  - le **push** ne revérifie pas l'URI : `services/chunk_push_service.py:193-211` appelle
    `resolver.resolve(store)` directement. Une ligne écrite avant la garde (base existante), ou un
    nom re-pointé depuis, est encore atteinte. Documenté (`SECURITY.md`, « Pushing chunks does not
    run the check again ») ;
  - le push renvoie le texte de l'exception au client : `chunk_push_service.py:209`
    (`f"Cannot resolve backend for store {store.slug!r}: {exc}"`, 503 via `api/errors.py:24-25`).
    Comme `Neo4jDriverPool.get` se connecte pendant la résolution, c'est l'oracle que le test de
    connexion n'offre plus (adresse, port, raison de l'échec). Antérieur à la remédiation (déplacé
    de `chunk_service.py:636` à `e6047c2`) ; exige l'ingestion configurée et des chunks ;
  - `DELETE /api/stores/{slug}/documents/{doc_id}` n'est pas soumis à la lecture seule
    (`store_service.py:439-443`, sans `_require_writable`). Effet limité à la suppression d'une
    ligne de lien ;
  - la résolution DNS est faite une fois avant le client (TOCTOU), documenté.
- **Règle violée** : 8.2.1 (défense en profondeur). Item conforme.
- **Remédiation** (S) : `_reject_blocked_uri(store.connection_uri)` dans `push_to_store` avant
  `_resolve_backends` ; message générique à `:209` (détail en log) ; `_require_writable()` dans
  `remove_document`.

### [MIN] MCP actif par défaut, sans authentification, port publié sur toutes les interfaces

**Statut vs 0.7.4 : inchangé.**

- **Localisation** : `infra/settings.py:107` (MCP actif) ; `docker-compose.yml:209` (`"3000:80"`) ;
  `README.md:17`, `docs/getting-started.md:14,28,42,102` (`-p 3000:3000`).
- **Remédiation** : inchangée (`127.0.0.1:3000:80`, `-p 127.0.0.1:3000:3000`).

### [MIN] Risque accepté : 4 CVE CRITICAL de Pillow 10.4.0 supprimées jusqu'au 2026-12-31, toujours sans issue qui livre le correctif

**Statut vs 0.7.4 : inchangé.** Recherche REST `repo:scub-france/docling-Studio is:issue pillow` :
**0 résultat** ; dernières issues jusqu'à #370 (plugin MCP), aucune sur Pillow. #361 (montée docling)
toujours sans milestone.

- **Localisation** : `.trivyignore.yaml:21-56` ; `document-parser/pyproject.toml:14`
  (`pillow>=10.0.0,<11.0.0`).
- **Remédiation** : inchangée (issue au milestone 0.8.0, docling ≥ 2.132 et `pillow>=13,<14`,
  référencée dans `.trivyignore.yaml` ; re-justifier avant le 2026-12-31 si la 0.8.0 glisse).

### [MIN] Dépendances Python : avis connus avec correctif disponible, non appliqués ; plafond `cryptography<46`

**Statut vs 0.7.4 : inchangé** (mêmes 93 / 111 avis). Un correctif est apparu pour nltk
(3.10.4).

- **Localisation** : `document-parser/pyproject.toml:20` (`cryptography>=43.0.0,<46.0.0`) ;
  `uv.lock` (filelock 3.32.3, transformers 5.8.1, docling / docling-slim 2.121.0, nltk 3.10.3).
- **Fait nouveau** : le gate audite désormais les groupes `local` et `reasoning`
  (`release-gate.yml:132`) et Trivy scannera le groupe `reasoning` (`:272`). nltk et accelerate
  y deviennent visibles ; leur sévérité n'a pas pu être lue.
- **Remédiation** : inchangée, plus `uv lock --upgrade-package nltk` (3.10.4).

### [MIN] Écritures de config MCP sans authentification

**Statut vs 0.7.4 : inchangé.** `api/config.py:68-90` ; `domain/mcp_config.py:94-104` (schéma
`http(s)` et `netloc` seulement) ; 403 sur HF.

### [MIN] Rate limiter : global par défaut en compose, seaux jamais purgés

**Statut vs 0.7.4 : partiellement corrigé.** Le contournement par `X-Forwarded-For` de l'image
tout-en-un est corrigé.

- **Corrigé** : `nginx.conf.template:56,71` et `frontend/nginx.conf.template:56,71`
  (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`). uvicorn prend l'adresse la plus à
  droite non approuvée (`FORWARDED_ALLOW_IPS`, défaut `127.0.0.1`). Sonde
  `ProxyHeadersMiddleware` (uvicorn 0.52.4) :

  | Pair | `X-Forwarded-For` reçu | `request.client` |
  |------|------------------------|------------------|
  | 127.0.0.1 (nginx, image tout-en-un) | `1.2.3.4, 203.0.113.7` (valeur du client + adresse ajoutée par nginx) | `203.0.113.7` (réelle) |
  | 172.18.0.3 (nginx compose, non approuvé) | idem | `172.18.0.3` (seau global) |
  | 172.18.0.3 approuvé via `FORWARDED_ALLOW_IPS` | idem | `203.0.113.7` |

  Documenté : `docs/configuration.md:33-34` (dont « Never set it to `*` »), commentaires des
  templates, CHANGELOG.
- **Reste** :
  - en compose, le seau reste global par défaut (documenté), et `FORWARDED_ALLOW_IPS` n'est pas
    transmis par `docker-compose.yml` : il faut l'ajouter sous `environment` ou dans un override
    (règle générale rappelée en `docs/configuration.md:6`) ;
  - `_buckets` n'est jamais purgé (`infra/rate_limiter.py:65`) : la croissance ne dépend plus que du
    nombre d'adresses réelles ;
  - cas limite : un client dont l'adresse vue par nginx est 127.0.0.1 (processus dans le conteneur,
    `--network host`) choisit encore son adresse (sonde : `1.2.3.4, 127.0.0.1` → `1.2.3.4`).
    Négligeable.
- **Règle violée** : 8.4.2 (sémantique). Item conforme.
- **Remédiation** (XS) : `FORWARDED_ALLOW_IPS: ${FORWARDED_ALLOW_IPS:-127.0.0.1}` dans le service
  `document-parser` du compose ; purger les seaux vides.

### [INFO] SSRF Ollama : garde intacte, factorisée ; résidus inchangés

**Statut vs 0.7.4 : inchangé.** `infra/llm/ollama_probe.py:35` appelle désormais
`infra/ssrf_guard.resolved_target_is_blocked` (même logique) ; TOCTOU entre `:35` et `:40-41` ;
loopback et LAN autorisés ; Save sans contrôle (`domain/app_config.py:84`) ; documenté
(`SECURITY.md`).

### [INFO] API sans authentification

**Statut vs 0.7.4 : inchangé.** Socle des [MAJ] ci-dessus.

### [INFO] Pas de garde-fou contre `CORS_ORIGINS="*"` avec credentials

**Statut vs 0.7.4 : inchangé.** `infra/settings.py:283` ; `main.py:93-94`.

### [INFO] nginx : processus maître en root, pas de Content-Security-Policy

**Statut vs 0.7.4 : inchangé.** `frontend/Dockerfile:9` (`nginx:alpine`, sans `USER`) ;
`Dockerfile:65` ; en-têtes `nginx.conf.template:18-21` (répétés dans les `location` qui ajoutent les
leurs, correctement).

### [INFO] Clients OpenSearch des stores sans vérification TLS

**Statut vs 0.7.4 : inchangé.** `infra/opensearch_pool.py:49,71` ; `infra/opensearch_store.py:80,90`.

### [INFO] Étapes de build sur Node 20, en fin de vie

**Statut vs 0.7.4 : inchangé.** `Dockerfile:11`, `frontend/Dockerfile:1`,
`docker-compose.dev.yml:175`.

### [INFO] [NOUVEAU] Texte d'exception interne renvoyé par `/reasoning` (500)

- **Localisation** : `document-parser/api/reasoning.py:51-53`
  (`detail=f"Reasoning run failed: {exc}"`). Antérieur (`aed2d92`), non relevé auparavant.
- **Constat** : toute exception de l'exécution (Ollama, docling-agent) part au client. Le reste est
  sain : le nouveau gestionnaire `api/errors.py:24-30` ne traite que `ServiceError`, dont les
  messages sont écrits par les services ; aucun gestionnaire générique n'a été ajouté, une exception
  non prévue reste un 500 « Internal Server Error » sans trace.
- **Remédiation** : message générique, exception en log (déjà fait `:52`).

### [INFO] [NOUVEAU] npm, dépendances de développement : vite 6.4.1 (HIGH)

- **Constat** : `npm audit` (sans `--omit=dev`) : 1 HIGH (vite, serveur de dev et build) et
  17 MODERATE (eslint, typescript-eslint, vitest, vue-tsc). Rien dans l'image (seul `dist/` est
  copié). Annoncé par le CHANGELOG (« vite 6.4.1 … is not updated yet »).
- **Remédiation** : montée de vite au prochain cycle, avec vitest et le build.

---

## Delta vs 0.7.4

Score : **97 → 100**. Comptes : CRIT 0 → 0 ; MAJ 3 → 3 (1 inchangé, 1 en partie corrigé, 1 corrigé,
1 nouveau) ; MIN 7 → 6 ; INFO 7 → 8.

| Écart 0.7.4 | Statut re-audit | Preuve |
|-------------|-----------------|--------|
| [MAJ] `/api/*` sans contrôle `Host` | **Inchangé** (décision mainteneur) | `main.py:91-103` |
| [MAJ] Import Docling, amplification | **Partiellement corrigé** : tables bornées ; contournement par `pictures[].meta.tabular_chart` démontré ; corps 200 Mo > capacité du conteneur (extrapolé) | `docling_importer.py:49,84` ; sonde |
| [MAJ] SSRF des stores | **Corrigé** (garde, HF lecture seule, message générique) ; résidus → [MIN] | `store_service.py:208,219-220,299-301,378-391` |
| [MIN] MCP par défaut / port publié | Inchangé | `docker-compose.yml:209` |
| [MIN] Pillow, risque accepté sans issue | Inchangé | recherche REST : 0 issue |
| [MIN] Dépendances Python | Inchangé (nltk 3.10.4 disponible) | pip-audit 93 / 111 |
| [MIN] Écritures config MCP | Inchangé | `api/config.py:68-90` |
| [MIN] Rate limiter (XFF) | **Partiellement corrigé** (XFF fermé ; compose global, seaux) | `nginx.conf.template:56,71` ; sonde |
| [MIN] npm 7 HIGH | **Corrigé** (0 en production) | `npm audit --omit=dev` |
| [MIN] torch / torchvision (8.5.2) | **Corrigé** | `pyproject.toml:44-45` |
| [INFO] SSRF Ollama, résidus | Inchangé (garde factorisée) | `ollama_probe.py:35` |
| [INFO] API sans authentification | Inchangé | — |
| [INFO] Garde `CORS_ORIGINS="*"` | Inchangé | `settings.py:283` |
| [INFO] nginx root / CSP | Inchangé | `frontend/Dockerfile:9` |
| [INFO] Convertisseur docling tous formats | **Corrigé** | `local_converter.py:76` |
| [INFO] OpenSearch `verify_certs=False` | Inchangé | `opensearch_pool.py:49` |
| [INFO] Node 20 | Inchangé | `Dockerfile:11` |

Nouveaux : [MAJ] identifiants Neo4j de l'environnement envoyés à l'URI du store (antérieur, non
relevé) ; [MIN] résidus SSRF des stores ; [INFO] `str(exc)` de `/reasoning` ; [INFO] vite (dev).

**Régressions introduites par la remédiation : aucune trouvée.** Vérifié en particulier :
- `infra/file_storage.py` : noms de fichiers générés par le serveur (`uuid4` + `.pdf`, `:31`) ;
  `resolve()` ne prend que le nom de fichier sous la racine en repli (`:45-49`) ; `delete()` compare
  les chemins réels, liens compris (`:54-59`). Aucun chemin issu de l'utilisateur ;
- `Cache-Control: private, max-age=86400` sur `/preview` et `/pages` (`api/documents.py:33,176,195`) :
  `private` exclut les caches partagés ; identifiants `uuid4`, jamais réutilisés ; aucune
  authentification, donc pas de fuite inter-utilisateurs par cache. `/assets/` en `public, immutable`
  ne sert que les fichiers hachés de Vite ;
- `gzip_proxied any` sur le JSON de l'API : aucun secret ni jeton dans les réponses (pas de risque de
  type BREACH) ;
- `api/errors.py` : voir [INFO] `/reasoning` ;
- `.dockerignore` : `.env` exclus à toute profondeur, `.claude/` exclu.

---

## Ce qui reste pour 100 sans écart MAJ

Le score est déjà à 100 ; les actions ci-dessous retirent des écarts sans changer la note.

| Action | Effet | Effort | Risque |
|--------|-------|--------|--------|
| Fallback d'identifiants Neo4j limité à l'URI de l'environnement (`store_backend_resolver.py:142-143`) + test | −1 MAJ | XS-S | faible (un store à URI propre sans mot de passe devra recevoir le sien) |
| Budget de cellules étendu aux `TableData` des images (`meta.tabular_chart`, `annotations`) + 2 tests | −1 MAJ (avec la ligne suivante) | S | faible |
| Plafond de corps de l'import abaissé (≈ `MAX_FILE_SIZE_MB`) | ferme le résidu de volume | XS | faible (un Docling JSON avec images embarquées > 50 Mo serait refusé : à documenter) |
| `_reject_blocked_uri` dans le push, message générique à `chunk_push_service.py:209`, `_require_writable` sur `remove_document` | −1 MIN | S | nul |
| `FORWARDED_ALLOW_IPS` transmis par le compose, purge des seaux | −1 MIN | XS | faible |
| Garde `Host` sur `/api/*` (décision mainteneur) | −1 MAJ | M | moyen (BREAKING) |
| Issue « docling → Pillow 13 » (milestone 0.8.0) | protège 8.5.1 au 2026-12-31 | XS | nul |

---

## Points positifs

- **Deux MAJ sur trois traités en profondeur et documentés** : garde SSRF partagée et testée
  (formes d'adresse alternatives bloquées sous 3.12 et 3.13), lecture seule des stores sur HF,
  messages génériques, budget de cellules exact (dimensions négatives, cellules qui débordent,
  somme sur toutes les tables), plafond de corps qui tient aussi en chunked. `SECURITY.md` décrit
  honnêtement ce que la garde ne couvre pas (push, rebinding DNS).
- **8.5.2 corrigé** sans toucher aux versions verrouillées ; **npm production à 0** (7 HIGH en 0.7.4).
- **Convertisseur restreint au PDF** : les backends docling non-PDF visés par les avis 2.121.0 sont
  hors d'atteinte.
- **Rate limiter effectif dans l'image tout-en-un** : la valeur fournie par le client ne choisit plus
  le seau ; la règle « jamais `*` » est écrite dans la doc et dans le template.
- **Aucune régression** dans les nouveaux adaptateurs (stockage de fichiers, en-têtes de cache,
  gestionnaire d'erreurs, `.dockerignore`).
- **Toujours sains** : aucun secret en dur, SQL en paramètres liés, un seul `v-html` assaini,
  CORS explicite, upload borné et vérifié par magic bytes, mots de passe des stores scellés par
  Fernet et jamais renvoyés, backend non-root.

---

## Verdict partiel : GO

- **Score 100/100 ≥ 80, 0 CRITICAL, 3 MAJOR (≤ 3)** → **GO**, au seuil : un MAJ de plus ferait
  basculer le verdict.
- Les deux MAJ nouveaux ou résiduels (import par les images, identifiants Neo4j) se corrigent en
  quelques lignes, à risque faible, et sont recommandés **avant le tag** : le premier arrête
  toujours le backend avec moins de 1 Ko, le second livre le mot de passe Neo4j de l'instance à qui
  atteint l'API.
- Le MAJ `Host` relève de la décision du mainteneur (BREAKING, effort M).

Conditions :
1. Le premier Release Gate de cette branche doit être vert sur les **deux** scans Trivy, dont le
   groupe `reasoning`, scanné pour la première fois (sinon 8.5.1 → 92/100, 1 CRIT, NO-GO).
2. Il doit tourner **avant le 2026-12-31** (expiration commune des 5 suppressions).
3. Ouvrir l'issue « docling → Pillow 13 » au milestone 0.8.0 (demandée depuis la synthèse 0.7.3).
