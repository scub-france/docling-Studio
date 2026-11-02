# Rapport d'audit : Securite

**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Branche** : release/0.7.3 @ 02adc68

Baseline : re-audit 0.7.0 (`reports/release-0.7.0-reaudit/08-security.md`, 97/100,
0 CRIT, 0 MAJ, 1 MIN, 4 INFO).

Methode : analyse statique du working tree (backend, frontend, infra, CI),
`npm audit --omit=dev` dans `frontend/`, lecture une seule fois de l'etat du run
release-gate en cours sur la PR `release/0.7.3 -> main`. `pip-audit` n'est pas
installe dans le venv (non installe, conformement aux regles). Ni l'app ni les
tests n'ont ete lances.

Hypothese de deploiement retenue : les deux modes documentes de quick-start,
`docker run -p 3000:3000 ghcr.io/scub-france/docling-studio:latest-local`
(`README.md:17`) et `docker compose up` (`docker-compose.yml`, port `3000:80`).
Dans les deux cas le port 3000 est publie sur **toutes les interfaces** et nginx
proxifie `/api/` et `/mcp` vers le backend. Modele de confiance du projet :
« The app has no login » (`SECURITY.md:51`).

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 12 / 14 |
| Score | 89 / 100 |
| Ecarts CRITICAL | 1 |
| Ecarts MAJOR | 2 |
| Ecarts MINOR | 5 |
| Ecarts INFO | 5 |

Detail du calcul : poids total de la checklist = 36. Items non conformes :
8.5.1 (poids 3) et 8.5.2 (poids 1). Poids conformes = 36 - 3 - 1 = 32.
**Score = 32 / 36 = 88,9 -> 89.**

Note de methode (identique a 0.7.0) : les deux ecarts [MAJ] portent sur
l'exposition reseau et l'absence d'authentification, que la checklist ne
pondere pas. Ils sont reportes comme ecarts de securite reels mais ne font pas
basculer d'item ; le score reste strictement adosse a la checklist.

---

## Verification par item

| # | Item | Poids | Conforme | Preuve |
|---|------|-------|----------|--------|
| 8.1.1 | Aucun secret en dur | 3 | Oui | grep code + `git ls-files` : seul `.env.example` ; aucun motif `sk-`/`ghp_`/`hf_`/`AKIA` |
| 8.1.2 | `.env` dans `.gitignore` | 3 | Oui | `.gitignore:26-28` |
| 8.1.3 | Secrets Docker par env, pas build args | 2 | Oui | `docker-compose.yml:163-195` (`environment:`) ; seuls ARG = `APP_VERSION`, `BAKE_MODELS`, `WITH_REASONING` (`Dockerfile:13,24,84,88`, `document-parser/Dockerfile:59,63`) |
| 8.2.1 | Entrees validees par Pydantic | 3 | Oui | nouvelles routes : `McpConfigUpdateRequest` (`api/schemas.py:803-814`) + bornes domaine (`domain/mcp_config.py:107-123`) ; `ImportAnalysisRequest` (`api/schemas.py:272-276`) puis `DoclingDocument.model_validate` (`infra/docling_importer.py:18`) ; arguments MCP valides par le schema du SDK |
| 8.2.2 | `MAX_FILE_SIZE_MB` applique a l'upload | 3 | Oui | `api/documents.py:69-88` (Content-Length + lecture bornee, 413), defaut 50 Mo (`infra/settings.py:28,215`) — voir [MIN] import JSON |
| 8.2.3 | Types de fichiers valides | 2 | Oui | magic bytes `%PDF` (`services/document_service.py:27`) ; import JSON valide par schema |
| 8.3.1 | SQL en parametres lies | 3 | Oui | f-strings limitees a des constantes / `?` (`persistence/analysis_repo.py:144-153`, `document_repo.py:93,118`) ; `LIKE` echappe (`document_repo.py:21,89-90`) |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | Oui | grep : aucun `eval(`, `exec(`, `os.system(`, `subprocess.`, `shell=True`, `pickle.load` |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | Oui | unique `v-html` assaini (`frontend/src/shared/ui/MarkdownViewer.vue:3,24`) ; cartes MCP : echappement systematique (voir Points positifs) |
| 8.4.1 | CORS explicite, pas de `*` | 3 | Oui | `main.py:89-95`, defaut localhost (`infra/settings.py:76-78,198`) |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | Oui | `main.py:96-101`, `infra/rate_limiter.py:59,68` ; s'applique aussi a `/mcp` — voir [MIN] cle par IP |
| 8.4.3 | Nginx sans directory listing | 2 | Oui | `frontend/nginx.conf.template`, `nginx.conf.template` : `try_files`, pas d'`autoindex` |
| 8.5.1 | Pas de CVE critique connue | 3 | **Non** | gate Trivy CRITICAL en echec, 5 suppressions expirees — voir [CRIT] |
| 8.5.2 | Versions epinglees | 1 | **Non** | `document-parser/pyproject.toml:41-42` (`torch`, `torchvision` sans version) |

---

## Ecarts constates

### [CRIT] Gate Trivy CRITICAL en echec sur l'image release : 5 suppressions `.trivyignore.yaml` expirees

> **Vérification de l'orchestrateur (2026-11-02, artefacts `trivy-remote` / `trivy-local` du run `41452005966`)** :
> la cause de l'échec n'est pas celle supposée ci-dessous. Le scan CRITICAL remonte des paquets **corrigeables** :
> PyJWT 2.13.0 (CVE-2026-102268, fix 2.14.0), certifi 2026.7.22 (GHSA-6q48-6c7w-9gw2), Pillow 10.4.0
> (CVE-2026-112393, -112398, -112403, -112900, fix 13.0.0), le paquet `uv` 0.11.6 (GHSA-hq85-5cpj-mr62) et le
> crate `zip` 8.1.0 embarqué dans `/usr/local/bin/uv` et `uvx` (CVE-2026-115905). Côté OS, seule
> CVE-2026-6653 (libxml2, image `local`) réapparaît. Les autres suppressions expirées ne sont plus
> détectées, car Debian a publié les correctifs. Le constat CRIT et le score restent inchangés.

- **Localisation** : `.trivyignore.yaml:25` (CVE-2026-7598 libssh2, `expired_at: 2026-08-31`),
  `:40` (CVE-2026-42496 perl-base, 2026-09-30), `:52` (CVE-2026-8376 perl-base,
  2026-09-30), `:67` (CVE-2026-58016 glib, 2026-10-31), `:81` (CVE-2026-6653
  libxml2, 2026-10-31) ; `:13` (CVE-2026-40393) et `:93` (CVE-2026-13221) expirent
  le 2026-11-30. Gate : `.github/workflows/release-gate.yml:352-366` (`severity:
  CRITICAL`, `exit-code: 1`, pas d'`ignore-unfixed`). Cause racine non livree :
  `Dockerfile:90-92` et `document-parser/Dockerfile:66-68` installent toujours
  `libgl1` + `libglib2.0-0` (#189, opencv-headless).
- **Constat** : au 2026-11-02, 5 des 7 suppressions sont expirees. Les commits qui
  les ont posees (`fc26e01`, `f2351db`, `fbd9608`, `5a49e69`) les qualifient de
  CVE **CRITICAL** sans correctif amont ni backport Debian 13. Aucun release gate
  n'a tourne entre le 2026-08-24 et aujourd'hui (0.7.2 gelee le 2026-09-07 sans run
  release-gate), donc ces expirations n'avaient jamais ete exercees. Le run
  release-gate de la PR `release/0.7.3 -> main` (run `41452005966`, ouvert le
  2026-11-02 a 13:19 UTC, consulte une fois) a deja le job **`Security scan —
  remote` en echec a l'etape `Run Trivy — CRITICAL (blocking)`** (job
  `125301667028`, annotation « Process completed with exit code 1 ») ; l'etape
  HIGH suivante a tourne normalement (8 HIGH annotees), ce qui exclut a priori un
  echec de telechargement de la base Trivy. `Security scan — local` etait encore en
  cours. Le CVE exact n'est pas lisible tant que le run n'est pas termine :
  l'attribution aux suppressions perl-base / libssh2 expirees (presentes dans
  `python:3.12-slim`, base de l'image remote, `Dockerfile:22`) est **PLAUSIBLE** ;
  l'image local porte en plus glib + libxml2 (suppressions expirees le 2026-10-31).
- **Regle violee** : 8.5.1 — l'image de release embarque au moins une CVE CRITICAL
  connue sans correctif ni acceptation de risque en cours de validite, et le gate
  bloquant du projet echoue.
- **Remediation** : a la fin du run, lire `trivy-critical-remote.txt` /
  `trivy-critical-local.txt` ; pour chaque CVE, soit reconstruire sur une base
  patchee (`apt-get upgrade` / bump `python:3.12-slim`), soit renouveler
  l'entree avec une justification et une date a jour ; prolonger aussi
  CVE-2026-40393 / CVE-2026-13221 (J-28). Livrer #189 pour supprimer
  `libgl1`/`libglib2.0-0` et trois des entrees d'un coup.

### [MAJ] Serveur MCP actif par defaut, sans authentification : `MCP_ALLOWED_HOSTS` ne filtre que l'en-tete `Host`, forgeable — `/mcp` lisible depuis le reseau dans les deploiements documentes

- **Localisation** : `document-parser/bootstrap/mcp_mount.py:210-231` (la garde est
  un `TransportSecuritySettings` Host/Origin) ; SDK
  `.venv/lib/python3.12/site-packages/mcp/server/transport_security.py:50-70,113-121`
  (mcp 2.1.1 : comparaison de chaine sur `Host`, `Origin` absent = accepte) ;
  `frontend/nginx.conf.template:29-38` et `nginx.conf.template:29-38`
  (`proxy_set_header Host $http_host` : le `Host` du client est transmis tel quel ;
  bloc `server` sans `server_name`) ; `docker-compose.yml:193-195` (MCP on) et
  `:205-206` (`"3000:80"`) ; `README.md:17` (`-p 3000:3000`). Affirmations :
  `document-parser/infra/settings.py:90-95`, `CHANGELOG.md:14`,
  `docs/mcp-server.md:14-16,320-323`, log `bootstrap/mcp_mount.py:120-124`.
- **Constat** : la liste d'hotes est une protection **anti DNS-rebinding** (elle
  bloque un navigateur dont le `Host` est un domaine tiers), pas un controle
  d'acces. Tout client non-navigateur qui atteint le port 3000 envoie
  `Host: localhost:3000` : `_validate_host` l'accepte via le motif `localhost:*`,
  un `Origin` absent est accepte, et le client obtient tous les outils
  (`find_documents` liste tous les documents, `read_element` lit tout le texte,
  `get_source_page` rend les pages). Or les deux quick-start publient 3000 sur
  toutes les interfaces et routent `/mcp`. Le commentaire `settings.py:92-94`
  affirme que la liste « is what keeps it off a backend reachable from
  elsewhere », le CHANGELOG qu'elle « keeps it to clients that reach it as
  localhost » : c'est vrai pour un client honnete, faux face a un adversaire.
- **Facteurs attenuants** : outils strictement en lecture seule ; les memes
  donnees sont deja lisibles sans authentification via `/api/documents/*`
  (posture « no login », `SECURITY.md:51`), donc pas de nouvelle donnee exposee ;
  le DNS rebinding navigateur est bien bloque (421, `tests/test_mcp_mount.py:117,136`) ;
  `docs/mcp-server.md:320` dit aussi « Anyone who can reach `/mcp` can read every
  document » ; off par defaut sur Hugging Face.
- **Regle violee** : 8.4 (CORS et reseau, exposition reseau) ; aucun item pondere
  ne couvre l'authentification, d'ou un ecart additionnel sans impact de score.
- **Remediation** : (1) corriger les affirmations (settings, CHANGELOG, docs) :
  garde anti-rebinding, pas restriction reseau ; (2) publier par defaut
  `127.0.0.1:3000:80` en compose et `-p 127.0.0.1:3000:3000` dans le README ;
  (3) a terme, un jeton porteur optionnel (`MCP_TOKEN`) verifie par la route `/mcp`.

### [MAJ] `/api/*` sans validation du `Host` : DNS rebinding possible contre une instance locale (lecture de tous les documents, ecritures de config), en asymetrie avec `/mcp`

- **Localisation** : `document-parser/main.py:89-101` (seuls `CORSMiddleware` et
  `RateLimiterMiddleware`, aucun `TrustedHostMiddleware`) ;
  `frontend/nginx.conf.template:1-24` et `nginx.conf.template:1-24` (serveur par
  defaut sans `server_name`, `/api/` proxifie quel que soit le `Host`).
- **Constat** : le projet traite explicitement le DNS rebinding comme une menace
  pour `/mcp` (`bootstrap/mcp_mount.py:210-216`, `docs/mcp-server.md:84-85`), mais
  `/api/*`, qui sert les memes documents et **toutes** les ecritures, n'a aucun
  controle du `Host`. Une page web visitee par quelqu'un qui fait tourner Studio
  en local (`http://localhost:3000`, le cas que `SECURITY.md:51` presente comme
  sur) peut faire pointer son domaine vers 127.0.0.1 sur le port 3000 puis
  emettre des requetes *same-origin* et lire les reponses : lecture de tous les
  documents et analyses, `DELETE /api/documents/{id}`,
  `PUT /api/config/reasoning` (Ask envoie alors prompts et extraits a l'hote
  choisi), `PUT /api/config/mcp` (rallume MCP, reecrit les deep links). CORS
  n'intervient pas : pour le navigateur la requete est same-origin.
- **Exploitabilite** : **PLAUSIBLE**, depend du navigateur (Chrome recent affiche
  une invite d'acces au reseau local ; Firefox et Safari protegent moins). Le
  defaut existait avant 0.7.3 et n'a pas ete releve en 0.7.0 ; 0.7.3 en augmente
  l'impact (nouvelles ecritures `/api/config/mcp`, `POST /api/analyses/import`).
- **Regle violee** : 8.4 (reseau). Ecart additionnel, sans impact de score.
- **Remediation** : `TrustedHostMiddleware` cote FastAPI (liste configurable,
  defaut `localhost`, `127.0.0.1`, `[::1]` avec port), ou dans nginx un
  `server_name` explicite et un `default_server` qui repond 421 ; refuser les
  requetes mutantes dont l'`Origin` est hors `CORS_ORIGINS`.

### [MIN] Ecritures de config MCP sans authentification : bascule du serveur et reecriture de la base des deep links (lien de phishing dans les citations)

- **Localisation** : `document-parser/api/config.py:80-103` ; validation
  `document-parser/domain/mcp_config.py:94-104` (schema http(s) + `netloc`
  seulement) ; construction `document-parser/services/citation_service.py:279-292` ;
  rendu `document-parser/mcp_adapter/sources_app.html:491,881`,
  `citation_app.html:615,656`, texte `mcp_adapter/sources_view.py:352-353`.
- **Constat** : en self-hosted, quiconque atteint `/api` peut
  `PUT /api/config/mcp` pour (a) rallumer un serveur que l'operateur a eteint
  dans Settings, ou l'eteindre (deni de service des clients MCP), et (b) fixer
  `studioBaseUrl` a `https://attaquant.example`. Chaque citation et le bouton
  « Ouvrir dans Studio » des cartes pointent alors vers l'attaquant, avec un
  chemin credible `/analyses/<id>?ref=…&page=N` relaye par l'agent IA de
  l'utilisateur. La valeur est persistee en base et survit au redemarrage.
  `MCP_ALLOWED_HOSTS` a ete volontairement garde hors de l'API pour cette raison
  (`docs/mcp-server.md:84-87`), mais pas la cible des liens.
- **Facteurs attenuants** : meme posture que `PUT /api/config/reasoning`
  ([INFO] 0.7.0) ; 403 sur Hugging Face (`bootstrap/builder.py:255`) ; pas de CSRF
  navigateur cross-origin (`PUT` absent de `allow_methods`, `main.py:93`, plus
  preflight JSON) ; l'hote MCP confirme `ui/open-link` ; les cartes n'acceptent
  que `http(s)` (`sources_app.html:360`).
- **Regle violee** : 8.2.1 (validation, defense en profondeur). Item conforme.
- **Remediation** : rendre `MCP_STUDIO_BASE_URL` restart-only (env), comme
  `MCP_ALLOWED_HOSTS`, ou le restreindre a une liste d'hotes autorises ; journaliser
  chaque changement en WARNING.

### [MIN] Import d'analyse Docling (#359) : corps JSON sans plafond applicatif, desserialisation et exports synchrones sur la boucle d'evenements

- **Localisation** : `document-parser/api/analyses.py:73-87` ;
  `document-parser/api/schemas.py:272-276` (`document: dict`) ;
  `document-parser/services/analysis_service.py:177` ;
  `document-parser/infra/docling_importer.py:16-29` ; plafond nginx seul :
  `frontend/nginx.conf.template:23`, `docker-compose.yml:208` (200 Mo).
- **Constat** : `MAX_FILE_SIZE_MB` (50) ne s'applique qu'a l'upload PDF. L'import
  accepte un JSON arbitraire, borne seulement par nginx (200 Mo par defaut) et sans
  borne si l'on lance uvicorn directement. Le corps est charge en entier, puis
  `DoclingDocument.model_validate`, `export_to_markdown`, `export_to_html` et
  `json.dumps(export_to_dict())` tournent dans la coroutine, sans
  `asyncio.to_thread`. Un gros document bloque donc toutes les requetes (API,
  MCP, health) pendant le traitement et peut epuiser la memoire du conteneur
  (limite 4g, `docker-compose.yml:196-199`, pas de politique `restart:`) —
  **PLAUSIBLE**. Aucune verification de taille cote client
  (`frontend/src/features/analysis/ui/AnalysisImportButton.vue:49`).
- **Ce qui est sain** : validation stricte du schema `DoclingDocument`, exports en
  `ImageRefMode.PLACEHOLDER` (defaut de docling-core 2.92 : aucun acces fichier ni
  URL depuis le JSON importe), aucun chemin de fichier issu du JSON, labels Neo4j
  pris dans une table fixe (`infra/docling_tree.py:42-43`), erreurs rendues en 400.
- **Regle violee** : 8.2.2 dans son esprit (upload borne). Item conforme au sens
  strict (upload PDF).
- **Remediation** : plafonner le corps (Content-Length et lecture bornee, alignes
  sur `MAX_FILE_SIZE_MB`), appeler `await asyncio.to_thread(importer.deserialize, ...)`,
  et fixer un `client_max_body_size` plus bas pour `/api/analyses/import`.

### [MIN] Rate limiter « par IP » en realite global derriere nginx

- **Localisation** : `document-parser/infra/rate_limiter.py:71`
  (`request.client.host`) ; `frontend/nginx.conf.template:20,33` (`X-Real-IP`
  envoye, jamais lu) ; `Dockerfile:63` (uvicorn sur 127.0.0.1 derriere nginx) ;
  `document-parser/Dockerfile:38`.
- **Constat** : dans les deux deploiements documentes, toutes les requetes
  arrivent de l'IP de nginx (127.0.0.1 ou IP du conteneur frontend) : un seul
  seau de 100 requetes par minute pour toute l'instance. Un seul client, ou un
  agent MCP bavard plus le polling de `GET /api/analyses/summaries` pendant un
  batch, epuise le quota de tout le monde et declenche des 429 globaux (DoS
  trivial). Pre-existant, non releve en 0.7.0 ; `/mcp` et le polling batch le
  rendent plus probable.
- **Regle violee** : 8.4.2. Item conforme : le middleware est actif sur tous les
  endpoints sauf `/api/health`, `/mcp` compris. La semantique par IP n'est pas tenue.
- **Remediation** : faire confiance a `X-Forwarded-For` uniquement depuis le proxy
  (`proxy_set_header X-Forwarded-For` + uvicorn `--proxy-headers
  --forwarded-allow-ips`), ou limiter dans nginx (`limit_req`).

### [MIN] `npm audit` (production) : 7 vulnerabilites HIGH, 0 CRITICAL

- **Localisation** : `frontend/package.json:22` (dompurify, verrouille 3.3.3,
  `frontend/package-lock.json:1917-1918`), `:25` (vue, verrouille 3.5.30,
  `package-lock.json:3194-3195`) ; transitives lodash 4.17.23 (via
  cytoscape-dagre), postcss, nanoid, source-map-js.
- **Constat** : `npm audit --omit=dev` le 2026-11-02 donne 7 HIGH et 0 CRITICAL.
  Les avis DOMPurify (<= 3.4.16) visent IN_PLACE, la forme fonction d'ADD_TAGS,
  hooks et setConfig, SAFE_FOR_TEMPLATES avec RETURN_DOM, PARSER_MEDIA_TYPE xhtml :
  aucun n'est atteint par l'appel par defaut `DOMPurify.sanitize(html)`
  (`MarkdownViewer.vue:24`). L'avis Vue vise `@vue/server-renderer` (SSR, non
  utilise). postcss, nanoid et source-map-js sont de l'outillage de build.
  Correctifs disponibles via `npm audit fix`.
- **Regle violee** : aucune CVE critique, donc 8.5.1 non impacte cote npm.
  Ecart d'hygiene.
- **Remediation** : `npm audit fix` ; dompurify >= 3.4.17, vue >= 3.5.42.

### [MIN] Dependances backend sans version (torch / torchvision) — inchange

- **Localisation** : `document-parser/pyproject.toml:41-42` (anciennement 35-36).
- **Constat** : inchange depuis le re-audit 0.7.0. La nouvelle dependance `mcp`
  est bornee (`>=2.1.1,<3.0.0`, `pyproject.toml:24`). Attenuant : `uv.lock` en
  `--frozen`, groupe optionnel `local`.
- **Regle violee** : 8.5.2.
- **Remediation** : plafond majeur (`torch>=2,<3`, `torchvision<1`) ou exemption
  documentee dans la fiche.

### [INFO] SSRF Ollama : garde intacte, residus inchanges, chemin Save non filtre (desormais documente)

- **Localisation** : `document-parser/infra/llm/ollama_probe.py:60` puis `:87-88`
  (TOCTOU : resolution, puis nouvelle resolution par httpx) ; `:69-72` (loopback
  et LAN autorises) ; `document-parser/domain/app_config.py:77-86` (Save : schema
  http(s) seul) ; `SECURITY.md:47-49`.
- **Constat** : la garde du probe reste en place (`ollama_probe.py:31-73`, appel `:82`). Les
  residus releves au re-audit sont inchanges. `SECURITY.md:48` dit maintenant
  explicitement que **Save** n'applique pas la garde : « Anyone who can reach the
  settings can point Ask at any address the server can reach ». Ask enverra alors
  prompts et extraits a cet hote. Attenuant : Ask masque par defaut
  (`ASK_MODE=hidden`, qui ne masque que l'UI, `docs/configuration.md:35`) et
  reasoning optionnel (`WITH_REASONING`).
- **Remediation** : appliquer aussi `_resolved_target_is_blocked` au Save ;
  epingler l'IP resolue pour la requete httpx.

### [INFO] API sans authentification : surface elargie (inchange, documente)

- **Localisation** : `document-parser/main.py:89-125` ; `SECURITY.md:51`.
- **Constat** : toujours aucune authentification. Nouvelles routes dans le meme
  regime : `PUT/DELETE /api/config/mcp`, `GET /api/mcp/server`,
  `POST /api/analyses/import`, `GET /api/analyses/summaries`,
  `GET /api/documents/{id}/pages`, et `/mcp`. Ecritures refusees en 403 sur
  Hugging Face (`bootstrap/builder.py:218,255`).
- **Remediation** : reverse-proxy authentifie pour tout deploiement expose (deja
  recommande) ; voir les deux [MAJ] pour les defauts.

### [INFO] Absence de garde-fou contre `CORS_ORIGINS="*"` avec credentials (inchange)

- **Localisation** : `document-parser/infra/settings.py:198,242` ;
  `document-parser/main.py:89-95` (`allow_credentials=True`).
- **Constat** : defaut explicite (localhost), donc conforme ; rien n'empeche
  `CORS_ORIGINS="*"`.
- **Remediation** : refuser au boot la combinaison `"*"` + credentials.

### [INFO] Audit des dependances Python non verifiable : gate pip-audit inoperant en CI, plafonds Pillow / cryptography

- **Localisation** : `.github/workflows/release-gate.yml:135-141` ;
  `document-parser/pyproject.toml:14` (`pillow<11.0.0`, verrouille 10.4.0),
  `:20` (`cryptography<46.0.0`, verrouille 45.0.7).
- **Constat** : le filtre CI teste `'CRITICAL' in v.get('fix_versions', [''])`.
  Or pip-audit ne fournit pas de severite et `fix_versions` contient des numeros
  de version : la condition n'est jamais vraie, `critical=false` est constant, et
  le job « Dependency audit » vert ne prouve rien cote Python. `pip-audit` absent
  du venv local : 8.5.1 n'a pas pu etre verifie pour les wheels Python dans cet
  audit. Les plafonds majeurs empechent de prendre les correctifs des branches
  Pillow 11/12 et cryptography 46 ; la presence d'avis connus sur 10.4.0 / 45.0.7
  est **PLAUSIBLE**, a confirmer avec pip-audit.
- **Remediation** : echouer sur toute vulnerabilite (ou mapper la severite via
  OSV) ; lancer `uv run pip-audit` avant le tag ; relever les plafonds.

### [INFO] nginx : processus maitre en root, pas de Content-Security-Policy

- **Localisation** : `frontend/Dockerfile:9-16` (`nginx:alpine`, sans `USER`) ;
  `Dockerfile:63` (nginx lance en root, uvicorn via `su appuser`) ;
  `frontend/nginx.conf.template:7-11`.
- **Constat** : le backend tourne bien en non-root (`document-parser/Dockerfile:37,91`,
  `Dockerfile:52,63`). nginx garde le schema standard (maitre root, workers non
  privilegies). Aucune CSP sur la SPA : DOMPurify reste la seule barriere XSS.
  Risque faible.
- **Remediation** : `nginxinc/nginx-unprivileged` ou port > 1024 sans root ; CSP
  `default-src 'self'` apres verification.

---

## Delta vs 0.7.0

Score : **97 (re-audit 0.7.0) -> 89 (0.7.3), soit -8**, du uniquement a la bascule
de l'item 8.5.1 (poids 3). Comptes : CRIT 0 -> 1, MAJ 0 -> 2, MIN 1 -> 5,
INFO 4 -> 5.

| Ecart baseline (0.7.0 / re-audit) | Statut en 0.7.3 | Preuve |
|-----------------------------------|-----------------|--------|
| [MAJ] SSRF probe test-connection (initial) | **Corrige, toujours en place** | `infra/llm/ollama_probe.py:31-73,82` |
| [MIN] 8.5.2 deps sans borne (torch/torchvision) | **Toujours ouvert** | `pyproject.toml:41-42` |
| [INFO] Suppression trivyignore expiree (CVE-2026-40393) | **Change, aggrave en [CRIT]** : 40393 prolonge au 2026-11-30, mais 5 autres entrees ont expire et le gate CRITICAL echoue | `.trivyignore.yaml:13,25,40,52,67,81` ; run `41452005966` |
| [INFO] SSRF residus (TOCTOU, LAN) (re-audit) | **Toujours present** ; chemin Save non filtre desormais documente | `ollama_probe.py:60,87-88` ; `SECURITY.md:48` |
| [INFO] API sans authentification | **Toujours present, surface elargie** (config MCP, import, `/mcp`) | `main.py:89-125` ; `SECURITY.md:51` |
| [INFO] Pas de garde CORS `"*"` + credentials | **Toujours present** | `settings.py:198,242` ; `main.py:89-95` |

Nouveaux ecarts 0.7.3 : [MAJ] garde MCP Host forgeable avec MCP actif par defaut ;
[MAJ] DNS rebinding sur `/api/*` (pre-existant, non releve en 0.7.0) ;
[MIN] base des deep links MCP inscriptible ; [MIN] import JSON sans plafond ;
[MIN] rate limiter global derriere nginx (pre-existant) ; [MIN] npm 7 HIGH ;
[INFO] gate pip-audit inoperant ; [INFO] nginx root / pas de CSP.

---

## Points positifs

- **Surface MCP en lecture seule et bornee** : tous les outils sont annotes
  read-only (`mcp_adapter/server.py:92`) et ne prennent que des identifiants,
  jamais de chemin ni de requete libre. Les sorties sont plafonnees : 50 documents
  (`services/navigation_config.py:34`), profondeur 1 a 6
  (`services/navigation_service.py:109`), 200 noeuds, plafond de lecture, 50 ancres
  et 2 000 caracteres par texte (`navigation_config.py:33,60-61`,
  `services/source_service.py:197-207`).
- **Ancres `dstudio://`** : regex stricte (`domain/anchors.py:34`) ; ids utilises
  seulement en parametres SQL lies ; une version qui n'appartient pas au document
  est refusee (`services/parse_loader.py:82-87`). Aucun path traversal possible.
- **Rendu des pages (`get_source_page` / `get_citation_image`)** : `max_width`
  borne a 120-1600 (`mcp_adapter/sources_view.py:205`, `apps.py:206`), dpi
  plafonne (`services/citation_image_service.py:71`), page bornee au nombre de
  pages (`:69`), fichier lu depuis le `storage_path` en base. Ces outils sont
  reserves a la carte (`visibility=["app"]`, `apps.py:193`, `sources_view.py:196`).
- **XSS dans les cartes MCP Apps** : chaque chaine passe par `esc()`
  (`sources_app.html:326-331`, `citation_app.html:402-404`) et chaque nombre par
  `num`/`pct`/`px`. Le mini-markdown echappe d'abord, puis balise
  (`citation_app.html:461`). Liens limites a `http(s)` (`sources_app.html:360`),
  ouverture deleguee a l'hote (`ui/open-link`). CSP par defaut de l'hote, sans
  permission presse-papiers sur la carte sources.
- **Injection de prompt** : `neutralise()` desamorce le delimiteur
  `</document-content>` dans chaque chaine issue d'un document (`mcp_adapter/wire.py:40,61-69`),
  et les instructions serveur declarent le contenu non fiable.
- **Pas de fuite interne** : `ToolErrors` masque les crashs
  (`mcp_adapter/tool_errors.py:51-53`), et le SDK 2.1.1 masque aussi les
  exceptions inattendues.
- **Anti-rebinding sur `/mcp`** : 421 pour un `Host` etranger (teste) ;
  desactivation (`*`) explicite ; `MCP_ALLOWED_HOSTS` non modifiable par l'API ;
  `MCP_ENABLED=false` ne monte rien ; MCP off par defaut sur Hugging Face ;
  avertissement « UNAUTHENTICATED » au montage. La documentation de securite MCP
  est presente (`docs/mcp-server.md:314-335`).
- **Config runtime** : ecritures MCP et reasoning refusees en 403 sur Hugging Face
  (`bootstrap/builder.py:218,255`) ; bornes domaine pour rounds, tokens et URL.
- **SQL** : `LIKE` echappe (`persistence/document_repo.py:21,89-90`) ; f-strings
  limitees a des placeholders ; labels Neo4j pris dans une table fixe.
- **Import #359** : schema `DoclingDocument` strict, images en placeholder, aucun
  chemin fichier issu du JSON.
- **Inchanges** : aucun secret en dur ; `.env*` ignores ; pas de secret en build
  arg ; upload PDF borne et verifie par magic bytes ; CORS explicite ; backend
  non-root ; garde SSRF du probe en place.

---

## Verdict partiel : NO-GO

Le score de 89/100 donnerait GO, mais **1 ecart CRITICAL** (8.5.1) rend l'audit
NO-GO par la regle absolue. Le gate Trivy bloquant de la PR `release/0.7.3 -> main`
echoue deja sur l'image remote. Les 2 ecarts MAJOR (<= 3) ne bloquent pas seuls.

Pour lever le NO-GO :
1. Trier la sortie Trivy du run `41452005966` quand il se termine. Corriger, ou
   renouveler avec une justification et une date a jour, chaque CVE CRITICAL
   (5 suppressions expirees, 2 a J-28). Livrer #189 si possible. Une fois 8.5.1
   retabli, le score revient a 35/36 = **97**.
2. Plan de remediation des MAJ : corriger les affirmations sur `MCP_ALLOWED_HOSTS`
   et publier 3000 sur 127.0.0.1 par defaut ; ajouter une validation du `Host` sur
   `/api/*` (TrustedHost ou `server_name` nginx).
3. Prochain cycle : base des deep links en env-only, plafond et offload de
   l'import, rate limiter derriere proxy, `npm audit fix`, filtre pip-audit,
   bornes torch/torchvision.
