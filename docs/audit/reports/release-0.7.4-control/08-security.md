# Rapport d'audit : Sécurité

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a12b744`, arbre de travail
**Nature** : Audit de contrôle après remédiation ; base : re-audit du 2026-11-18 sur `a6fb539`
(`release-0.7.4-reaudit/08-security.md` : 97/100, 13/14, 0 CRIT, 1 MAJ, 8 MIN, 8 INFO)

Méthode : lecture statique de l'arbre de travail ; `git log` / `git diff a6fb539 a12b744`
(15 commits, 232 fichiers) ; `npm audit --omit=dev` et `npm audit` (lecture seule) ;
`gh issue view 378`, `gh api .../actions/permissions/workflow` (lecture seule). Rien n'a été
lancé côté application. nginx, Trivy et Docker ne sont pas utilisés ici : la syntaxe nginx a été
vérifiée à la lecture, les images ne sont pas scannées. Les suites de tests (1559 backend,
605 frontend, lint, typage, build) ont été exécutées avant cet audit sur `a12b744` et ne sont
pas relancées.

Convention : **[lu]** = confirmé en lisant le code de l'arbre de travail ; **[hyp.]** =
hypothèse ou scénario non démontré.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 97 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 9 |
| Écarts INFO | 9 |

Calcul : poids total 36 ; seul 8.5.2 (poids 1) est non conforme. `35 / 36 × 100 = 97,2` → **97**.
Même lecture que la base : 8.5.1 est compté conforme **sous réserve du scan Trivy du Release
Gate**, qui n'a pas tourné sur cet arbre ; s'il échoue : `33 / 36` = **92**, 1 CRIT → NO-GO.

Le MIN supplémentaire (9 au lieu de 8) est un constat CI hors grille (jeton `GITHUB_TOKEN` en
écriture par défaut dans `ci.yml`, désormais aussi sur les push `release/**`) ; il ne change pas
le score.

### Détail par item

| # | Item | Poids | Conforme | Justification (arbre `a12b744`) |
|---|------|-------|----------|---------------------------------|
| 8.1.1 | Aucun secret en dur | 3 | oui | grep des lignes ajoutées par `a6fb539..a12b744` (`password=`, `secret=`, `api_key=`, `token=`, `sk-`, `ghp_`, `hf_`, `AKIA`, `PRIVATE KEY`) : seules occurrences = le rapport d'audit précédent et `readToken` (`BboxCanvas.vue`, lecture de variable CSS). Seul binaire modifié : `frontend/public/logo.png` (métadonnées XMP « Made with Google AI », déjà présentes avant, aucune donnée personnelle). Les nouveaux tests génèrent leurs PDF dans `tmp_path` (`tests/test_pdf_inspector.py:19-61`, `test_page_raster_real.py:35`, `test_document_export_range.py:45`) : aucune fixture binaire commitée |
| 8.1.2 | `.env` dans `.gitignore` | 3 | oui | `.gitignore:26-28` inchangé |
| 8.1.3 | Secrets Docker par env | 2 | oui | diff Docker = `node:20-alpine` → `node:22-alpine` (`Dockerfile:11`, `frontend/Dockerfile:1`, `docker-compose.dev.yml:174`) ; aucun `ARG`/`ENV` secret ajouté ; `.dockerignore:23-25` exclut toujours `.env`, `.env.*` |
| 8.2.1 | Entrées validées par Pydantic | 3 | oui | paramètres preview inchangés (`api/documents.py:152-154` : `page ge=1`, `dpi 72..300`, `format Literal`) ; schémas de l'éditeur toujours sans borne ([MIN] reconduit) |
| 8.2.2 | `MAX_FILE_SIZE_MB` appliqué | 3 | oui | route : 413 sur `file.size` puis lecture par blocs (`api/documents.py:55-68`) ; service : `services/document_service.py:96-97` |
| 8.2.3 | Types de fichiers validés | 2 | oui | magic `%PDF` `document_service.py:99-100`, nom `uuid4` + `.pdf` `:102-104`, limite de pages avec suppression du fichier `:116-124` ; ordre identique à `a6fb539` (voir revue) |
| 8.3.1 | SQL en paramètres liés | 3 | oui | diff de `persistence/` = renommages (`analysis_repo.py` : `find_latest_parsed_ids`, `find_parsed_document_id`) ; aucune requête modifiée ; Cypher (`infra/neo4j/queries.py`, `tree_writer.py`) : renommages seuls |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | oui | aucune ligne ajoutée ne contient `eval(`, `exec(`, `os.system(`, `subprocess`, `shell=True` ; l'adaptateur `pdf_inspector.py` appelle `pdfinfo_from_bytes` comme avant |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | oui | seul `v-html` : `frontend/src/shared/ui/MarkdownViewer.vue:3` (assaini) ; 0 ajout de `v-html`, `innerHTML`, `insertAdjacentHTML`, `new Function`, `eval(` dans `frontend/src` ; `package.json` / `package-lock.json` : diff vide |
| 8.4.1 | CORS explicite | 3 | oui | `main.py:90-96` inchangé |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | oui | `main.py:97-102` inchangé ; `/pages` et `/preview` toujours sous `/api/` |
| 8.4.3 | Nginx sans directory listing | 2 | oui | nouvelle `location /assets/` en `try_files $uri =404` (`nginx.conf.template:26-34`, `frontend/nginx.conf.template:26-34`), pas d'`autoindex` |
| 8.5.1 | Pas de CVE critique connue | 3 | oui, **sous réserve du gate** | npm prod : 0 CRITICAL, 7 HIGH (inchangé) ; `uv.lock` inchangé ; `.trivyignore.yaml` inchangé (5 suppressions au 2026-12-31) ; images non scannées |
| 8.5.2 | Versions épinglées | 1 | **non** | `document-parser/pyproject.toml:45-46` (`torch`, `torchvision` sans version) |

---

## Écarts constatés

### [MAJ] `/api/*` sans validation du `Host` : DNS rebinding contre une instance locale — inchangé

- **Localisation** : `document-parser/main.py:90-102` (CORS et rate limiter seulement ; aucun
  `TrustedHost` dans `main.py`, `api/`, `bootstrap/`, `infra/`) ; `nginx.conf.template:1-2`,
  `frontend/nginx.conf.template:1-2` (pas de `server_name`).
- **Constat [lu]** : non touché par la remédiation. `/mcp` reste protégé par la sécurité de
  transport (`bootstrap/mcp_mount.py`, `_build_transport_security`, simple renommage).
- **Scénario [hyp.]** : identique à la base (page hostile, domaine rebindé sur 127.0.0.1, lecture
  des PDF par `/api/documents/{id}/export?format=pdf`, suppression, réécriture d'éditions).
- **Règle violée** : 8.4 (réseau), hors pondération.
- **Remédiation** : `TrustedHostMiddleware` aligné sur `MCP_ALLOWED_HOSTS`, ou `server_name`
  explicite + serveur par défaut en 421. Effort S.

### [MIN] `ci.yml` sans bloc `permissions` : jeton en écriture, désormais aussi sur les push `release/**` — nouveau constat (condition préexistante, surface élargie)

- **Localisation** : `.github/workflows/ci.yml:3-7` (aucun `permissions:` dans le fichier) ;
  réglage du dépôt lu par `gh api repos/:owner/:repo/actions/permissions/workflow` :
  `default_workflow_permissions = write`.
- **Constat [lu]** : `c4c0474` ajoute `release/**` aux déclencheurs `push`. Ces runs reçoivent le
  `GITHUB_TOKEN` par défaut, donc en écriture, et exécutent du code tiers (`npm ci`,
  `uv sync`, dépendances Karate, Chrome). `ci.yml` n'utilise aucun secret (`grep secrets.` vide)
  et ne réagit pas à `pull_request_target` : les PR de forks gardent un jeton en lecture seule et
  aucun secret. Le seul code non maître qui tourne sur un push `release/**` est celui des
  dépendances.
- **Scénario [hyp.]** : une dépendance npm compromise, installée par `npm ci` lors d'un push sur
  `release/0.7.4`, lit le jeton du runner et pousse sur une branche ou modifie une release. Ce
  risque existait déjà pour les push sur `main` et les PR internes ; la remédiation l'étend aux
  push de branche de release. Confiance dans l'exploitation : faible ; dans la condition : élevée.
- **Règle violée** : aucune de la grille 08 (hygiène CI, à rapprocher de l'audit 10).
- **Remédiation** : `permissions: contents: read` en tête de `ci.yml` (et de
  `release-gate.yml`, qui n'a de bloc qu'au niveau de deux jobs : `:410-411`, `:696`), ou passer
  le réglage du dépôt en lecture seule.

### [MIN] Routes de l'éditeur sans borne de taille — inchangé

- **Localisation** : `document-parser/api/schemas.py:150` (`text: str`), `:155-156`
  (`element_ids`, `separator`), `:180`, `:195` (`commands`) ; fichier non modifié.
- **Remédiation** : `Field(max_length=...)`.

### [MIN] MCP actif par défaut, port publié sur toutes les interfaces — inchangé

- **Localisation** : `document-parser/infra/settings.py:97` ; `docker-compose.yml:208`
  (`"3000:80"`) ; fichiers non modifiés.

### [MIN] Risque accepté Pillow 10.4.0 / libxml2 jusqu'au 2026-12-31 — inchangé (J-43)

- **Localisation** : `.trivyignore.yaml:20,38,44,50,56` (`expired_at: 2026-12-31`) ; fichier non
  modifié ; #378 **OPEN** au 2026-11-18 (`gh issue view 378`).
- **Note [lu]** : le nouvel adaptateur encode toujours du PNG ou du WebP sans perte
  (`infra/page_raster.py:35-40`), sans décoder d'image entrante : la justification tient.

### [MIN] Écritures de configuration MCP sans authentification — inchangé

- **Localisation** : `document-parser/api/config.py:81-104` (PUT / DELETE `/api/config/mcp`) ;
  diff = renommage `http_error` → `to_http_error`.

### [MIN] Import d'analyse Docling sans plafond de taille — inchangé

- **Localisation** : `document-parser/api/analyses.py:75-90` ; `api/schemas.py` (`document: dict`)
  non modifié.

### [MIN] Rate limiter « par IP » en réalité global derrière nginx — inchangé

- **Localisation** : `document-parser/infra/rate_limiter.py:71` (`request.client.host`) ;
  `Dockerfile:65` (uvicorn sans `--proxy-headers`).

### [MIN] `npm audit` (production) : 7 HIGH, 0 CRITICAL — re-mesuré, inchangé

- **Constat (mesuré le 2026-11-18 sur `a12b744`)** : `npm audit --omit=dev` → 7 high
  (`@vue/server-renderer`, `dompurify`, `lodash`, `nanoid`, `postcss`, `source-map-js`, `vue`),
  0 critical ; `npm audit` complet → 27 (17 moderate, 10 high, 0 critical). Identique à la base ;
  cohérent avec le diff vide de `package.json` / `package-lock.json`.
- **Remédiation** : `npm audit fix`.

### [MIN] Dépendances backend sans version : torch / torchvision — inchangé (item 8.5.2)

- **Localisation** : `document-parser/pyproject.toml:45-46` (le diff du fichier ne touche que
  des commentaires, `:52`, `:57`).

### [INFO] Traduction des erreurs : aucun chemin serveur dans une réponse HTTP — vérifié

- **Constat [lu]** :
  - `infra/page_raster.py:29-33` lève `FileNotFoundError(storage_path)` et
    `ValueError("Page … not found in {storage_path}")`. Le `ValueError` est intercepté dans
    `services/preview_service.py:79-88` et remplacé par `PreviewPageNotFoundError("Page N not
    found")`, sans le chemin. Le `FileNotFoundError` (comme celui de `path.stat`,
    `preview_service.py:62`) tombe sur `api/documents.py:168-169`, message fixe.
  - Le `except ValueError → 404 str(e)` restant (`api/documents.py:166-167`) ne peut plus
    recevoir qu'un `ValueError` hors rendu ; le seul candidat lu est un octet nul dans
    `storage_path` (`os.stat`, message « embedded null byte », sans chemin), et `storage_path`
    n'est écrit que par le serveur (`document_service.py:131`). Les exceptions de `pdf2image`
    (`PDFPageCountError`, `PDFSyntaxError`, …) héritent d'`Exception`, pas de `ValueError`
    (`.venv/.../pdf2image/exceptions.py`) : elles finissent en 422 « Failed to generate
    preview » (`:173-175`), même si leur message contient la sortie de poppler avec le chemin.
  - `/pages` : `PdfiumInspector.page_sizes` lève `FileNotFoundError(storage_path)`
    (`infra/pdf_inspector.py:28-29`) → message fixe (`api/documents.py:186-187`) ; toute autre
    erreur pdfium → 422 fixe (`:188-190`).
  - Messages de `ServiceError` désormais renvoyés par `to_http_error`
    (`api/errors.py:25-31`) dans les routes modifiées : `PreviewDocumentNotFoundError`
    (« Document not found »), `PreviewPageOutOfRangeError` (numéro de page et nombre de pages,
    `preview_service.py:56-59`), `ExportNotFoundError` (messages constants ou identifiant
    d'analyse fourni par le client, `services/export_service.py:83-149`) ; l'export attrape
    maintenant `ServiceError` au lieu d'`ExportNotFoundError`, mais le service ne lève que
    cette dernière : aucun message nouveau.
  - Import (`api/analyses.py:83-88`) : `ImportDocumentNotFoundError` reprend le même texte
    qu'avant (« Document not found: {id} », id du client) ; `InvalidDoclingDocumentError`
    reprend mot pour mot le `ValueError` de l'adaptateur (`infra/docling_importer.py:28-29`,
    « Invalid Docling document: {e} »), qui passait déjà en 400 par la route : exposition
    identique à `a6fb539` (voir l'INFO « messages Pydantic » ci-dessous).
- **Conclusion** : la remédiation **retire** une fuite potentielle (le chemin de l'adaptateur) et
  n'en ajoute aucune.

### [INFO] nginx : `location /assets/` et `gzip_types` élargi — vérifié, pas d'écart

- **Localisation** : `nginx.conf.template:4-8,13-17,26-34` ; `frontend/nginx.conf.template:4-8,
  13-17,26-34` (le second reçoit aussi `gzip on`, absent auparavant).
- **Constat [lu]** :
  - Les quatre en-têtes du bloc `server` (`X-Frame-Options`, `X-Content-Type-Options`,
    `X-XSS-Protection`, `Referrer-Policy`, `:14-17`) sont répétés à l'identique, avec `always`,
    dans `/assets/` (`:29-32`). `/` et `/api/`, sans `add_header` propre, en héritent toujours.
    Pas de CSP (reconduit).
  - Syntaxe relue : directives valides dans un `location` (`expires`, `add_header`,
    `try_files`), accolades équilibrées, points-virgules présents. `$uri` n'est pas substitué
    par `envsubst` : filtre explicite `'${NGINX_MAX_BODY_SIZE}'` dans `Dockerfile:65` ; l'image
    `nginx:alpine` ne substitue que les variables d'environnement définies. `expires 1y` émet
    `Cache-Control: max-age=31536000` et `add_header` un second `Cache-Control: public,
    immutable` : deux champs, valides et fusionnés par les clients. `expires` et ce
    `add_header` (sans `always`) ne s'appliquent pas aux 404 : pas de mise en cache d'une
    erreur.
  - `try_files $uri =404` : nginx normalise l'URI (décodage, `..` résolus) avant la recherche de
    `location` ; `$uri` reste sous `root` ; un dossier donne 404 (pas de `$uri/`, pas
    d'`autoindex`).
  - Contenu de `/assets/` : sortie de `vite build` uniquement (JS/CSS empaquetés, worker
    PDF.js) ; pas de sourcemap (`vite.config.js` sans `build.sourcemap`, aucun `.map` dans
    `dist/assets`) ; seule variable d'environnement lue dans `src` : `import.meta.env.DEV`.
    Uploads et API ne passent pas par `root` (`/api/` est proxifié, les PDF sont lus par
    FastAPI). `public, immutable` ne concerne donc que des fichiers publics par nature.
  - BREACH : les nouveaux types compressés (JS, CSS, SVG) sont des fichiers statiques sans
    entrée utilisateur ni secret. Sur `/api/`, `application/json` était déjà compressé ; dans
    `frontend/nginx.conf.template`, `gzip on` compresse aussi désormais le JSON et le
    `text/html` proxifiés. Aucune réponse ne porte de secret par requête (pas de session, pas
    de jeton CSRF ; `DocStoreLinkResponse` = slug, état, date, `api/schemas.py:85-99`) : pas
    de cible BREACH **[hyp. raisonnable]**. Le PDF (`application/pdf`) et le flux MCP ne sont
    pas dans `gzip_types` : Range et streaming intacts.
- **Observation** : une requête `/assets/x` absente répond 404 au lieu de l'`index.html` de la
  SPA : comportement souhaitable.

### [INFO] `frontend/.dockerignore` nouveau mais incomplet (`.env*`, `.claude/`) — amélioration nette

- **Localisation** : `frontend/.dockerignore:1-9` ; contexte `./frontend` utilisé par
  `docker-compose.yml:206`.
- **Constat [lu]** : avant `10ecb05`, aucun fichier : tout `frontend/` entrait dans l'étape de
  build. Désormais `node_modules/`, `dist/`, `coverage/` sont exclus. Restent copiés dans
  l'étape **de build** (pas dans l'image finale, qui ne prend que `dist`) : un éventuel
  `frontend/.env*` et `frontend/.claude/` (présent localement, `launch.json`, ignoré par git).
  Vite n'injecterait que des `VITE_*` référencés, or seul `import.meta.env.DEV` l'est : pas de
  fuite dans le bundle. Le `.dockerignore` racine gagne `**/__pycache__`, `**/*.pyc`, `out/` :
  rien de sensible n'y entre.
- **Remédiation** : ajouter `.env`, `.env.*`, `.claude/` à `frontend/.dockerignore`.

### [INFO] Surface PDF.js / export PDF : confinement au dossier d'upload toujours à aligner — inchangé

- **Localisation** : `services/export_service.py:85-91` (`FileResponse` sur `doc.storage_path`) ;
  `services/document_service.py:170-182` (`resolve_storage_path`), `:193-200` (seule la
  suppression confine par `realpath`).
- **Constat [lu]** : aucune route n'écrit `storage_path` (seule écriture
  `document_service.py:131`) ; la remédiation déplace `resolve_storage_path` derrière le port
  `DocumentFileLocator` sans en changer le code. Écart de défense en profondeur seulement.

### [INFO] Cache de preview — inchangé

- **Constat [lu]** : la page est toujours vérifiée contre `page_count` avant la lecture du cache
  (`preview_service.py:56-64`) ; clé identique (chemin, taille, `mtime_ns`, page, dpi, format).

### [INFO] Verrou pdfium partagé — effet de bord positif

- **Localisation** : `infra/pdfium_lock.py:13-17` ; `infra/pdf_inspector.py:30,47`.
- **Constat [lu]** : la lecture des tailles de page prend désormais le verrou pdfium de Docling ;
  à `a6fb539` elle appelait pdfium sans verrou depuis un thread, en parallèle d'une conversion
  (risque de plantage du processus). **[hyp.]** Un PDF aux milliers de pages tient le verrou le
  temps de la lecture et retarde une conversion : sujet de performance (audit 12), pas de
  sécurité.

### [INFO] DDL de montée de schéma en f-string sur des constantes — inchangé

- `persistence/database.py` non modifié.

### [INFO] Messages d'erreur 400 qui recopient la validation Pydantic interne — inchangé

- **Localisation** : `infra/docling_editor.py:46,61` (diff = renommages) ;
  `infra/docling_importer.py:28-29` (même mécanisme pour l'import, désormais via
  `InvalidDoclingDocumentError`) ; renvoyés par `api/errors.py:31` et `api/analyses.py:83-88`.

### [INFO] Flag éditeur coupé : l'export par défaut sert le résultat actif — inchangé

- **Constat [lu]** : `export_document` vérifie le flag dans le corps (`api/documents.py:123-124`,
  `deps.ensure_analysis_editor_enabled`, même 404 qu'avant, `api/deps.py:53-56`) ; le chemin
  par défaut est inchangé.

### [INFO] Constats reconduits sans changement

| Constat | Localisation vérifiée |
|---------|-----------------------|
| SSRF Ollama : résidus (TOCTOU, LAN autorisé) | `infra/llm/ollama_probe.py` (diff = renommage `_is_resolved_target_blocked`) |
| API sans authentification (documenté) | `SECURITY.md:51` ; `main.py:90-102` |
| Pas de garde `CORS_ORIGINS="*"` avec credentials | `infra/settings.py:246` ; `main.py:92-93` |
| nginx maître en root, pas de CSP | `Dockerfile:65` ; `nginx.conf.template:13-17` |
| Images de build `node:22-alpine` non épinglées par digest | `Dockerfile:11`, `frontend/Dockerfile:1` (comme `node:20-alpine` avant) |

---

## Delta vs re-audit a6fb539

| Écart du re-audit (`a6fb539`) | Statut à `a12b744` |
|-------------------------------|--------------------|
| [MAJ] `Host` non validé sur `/api/*` | **Inchangé** (`main.py:90-102`) |
| [MIN] Routes de l'éditeur non bornées | Inchangé (`api/schemas.py` non modifié) |
| [MIN] MCP actif par défaut, 0.0.0.0 | Inchangé |
| [MIN] Pillow / libxml2 risque accepté | Inchangé ; J-43 ; #378 OPEN |
| [MIN] Écritures config MCP sans auth | Inchangé (renommage seul) |
| [MIN] Import JSON sans plafond | Inchangé |
| [MIN] Rate limiter global | Inchangé |
| [MIN] `npm audit` 7 HIGH | **Re-mesuré, inchangé** : 7 HIGH / 0 CRIT prod ; 27 au total |
| [MIN] torch / torchvision (8.5.2) | Inchangé |
| [INFO] Surface PDF.js / confinement | Inchangé |
| [INFO] Cache de preview | Inchangé |
| [INFO] gzip nginx | **Remplacé** par l'INFO `/assets/` + gzip élargi : vérifié, pas d'écart |
| [INFO] DDL f-string | Inchangé |
| [INFO] Détail d'erreur Pydantic | Inchangé (même texte pour l'import, nouvelle classe) |
| [INFO] Flag éditeur | Inchangé |
| [INFO] Reconduits | Inchangé (+ ligne `node:22-alpine` non épinglé) |
| — | **Nouveau [MIN]** : `ci.yml` sans `permissions`, jeton en écriture sur push `release/**` |
| — | **Nouveaux [INFO]** : traduction d'erreurs vérifiée (fuite de chemin évitée), `frontend/.dockerignore` incomplet, verrou pdfium partagé |

Aucun écart résolu, aucun écart aggravé. Aucune régression de sécurité trouvée dans le code
applicatif. Score **97 → 97**.

---

## Revue de sécurité de la remédiation

| Surface modifiée | Vérifié comment | Résultat |
|------------------|-----------------|----------|
| `nginx.conf.template`, `frontend/nginx.conf.template` (`/assets/`, gzip) | lecture complète des deux fichiers ; comparaison en-tête par en-tête avec le bloc `server` ; filtre `envsubst` (`Dockerfile:65`) ; contenu de `dist/assets` et `vite.config.js` | 4/4 en-têtes répétés avec `always` ; syntaxe correcte à la lecture ; aucun fichier sensible sous `/assets/` ; pas d'évasion de `root` ; pas de cible BREACH. **Pas d'écart.** |
| `api/documents.py` preview / pages | lecture des routes (`:148-193`) et de tous les chemins d'exception ; hiérarchie des exceptions `pdf2image` | aucun message client ne contient de chemin ; le `ValueError` porteur du chemin est remplacé (`preview_service.py:79-88`). **Pas d'écart, amélioration.** |
| `services/preview_service.py`, `infra/page_raster.py`, `infra/pdf_inspector.py`, `infra/pdfium_lock.py` | lecture complète ; comparaison avec `DocumentService.generate_preview` / `page_sizes` de `a6fb539` | même contrôle de page avant cache ; même format de sortie (PNG / WebP sans perte) ; ajout d'un verrou pdfium. **Pas d'écart.** |
| `api/errors.py`, `services/errors.py`, `services/analysis_service.py` (`ImportDocumentNotFoundError`, `InvalidDoclingDocumentError`) | inventaire des `ServiceError` atteignables par chaque route modifiée ; comparaison des textes avant / après | mêmes messages qu'avant ; le 400 de l'import recopie l'erreur de validation Docling comme avant (INFO reconduit). **Pas de nouvelle exposition.** |
| `services/document_service.py` (upload, `find_with_store_links`) | diff ligne à ligne de `upload` contre `a6fb539` ; ancien `_count_pages` contre `PdfiumInspector.count_pages_in_bytes` ; `DocumentStoreLinkView` et `DocStoreLinkResponse` | contrôles et ordre identiques : taille (`:96-97`), `%PDF` (`:99-100`), nom UUID (`:102-104`), comptage par `pdfinfo_from_bytes` avec repli `None` (`pdf_inspector.py:54-64`), limite de pages avec `unlink` (`:116-124`). La vue de lien ne porte que slug, état, date (`:46-52`), réponse inchangée (`api/documents.py:26-31`) ; le `Store` complet ne sort pas du service. **Pas d'écart.** |
| `api/` (autres routes), `bootstrap/`, `mcp_adapter/`, `infra/neo4j/`, `persistence/` | `git diff` complet, lignes `+/-` relues | renommages et typage par ports ; la porte `/mcp` (`_wrap_route`, `_is_serving`, `_build_transport_security`) garde le même code. **Pas d'écart.** |
| `.github/workflows/ci.yml` (push `release/**`) | lecture des déclencheurs, des `${{ }}` dans `run:`, des `permissions` ; réglage du dépôt via `gh api` | pas de `pull_request_target`, pas de secret, expressions sûres (`github.ref`, `github.base_ref`) ; **mais** pas de bloc `permissions` et jeton en écriture par défaut → [MIN] nouveau. |
| `.github/workflows/release-gate.yml` (`set -o pipefail`) | lecture `:81-95` | durcit seulement (un test rouge fait échouer l'étape). **Pas d'écart.** |
| `Dockerfile`, `frontend/Dockerfile`, `docker-compose.dev.yml` | diff | Node 22 en étape de build seulement ; aucun secret ; tag non épinglé comme avant. **Pas d'écart.** |
| `.dockerignore`, `frontend/.dockerignore` | lecture ; contextes de build dans les compose | réduction du contexte ; `frontend/.dockerignore` n'exclut pas `.env*`/`.claude/` (étape de build seulement) → [INFO]. |
| Frontend (`BboxCanvas.vue`, CSS de `1516a0c`, renommages) | grep des puits HTML et d'`eval` dans les lignes ajoutées ; diff des manifestes npm | 0 nouveau `v-html`/`innerHTML`/`eval` ; couleurs lues par `getPropertyValue` et passées au canvas (pas de DOM) ; aucune dépendance ajoutée. **Pas d'écart.** |
| Tests et binaires | `git diff --numstat` (binaires) ; grep de secrets ; lecture des nouveaux tests | seul binaire : `logo.png` (XMP sans donnée personnelle) ; PDF de test générés dans `tmp_path`. **Pas d'écart.** |

**Non vérifié** : scan Trivy des images (gate non exécuté sur cet arbre, Docker interdit) ;
comportement réel de nginx (`nginx -t` impossible, vérification à la lecture seulement) ;
`pip-audit` non lancé (lock inchangé) ; exploitabilité réelle du DNS rebinding et du scénario CI.

---

## Points positifs

- **Fuite de chemin évitée par construction** : l'adaptateur garde le chemin dans son message,
  le service le remplace avant la frontière HTTP (`preview_service.py:79-88`), avec un
  commentaire qui dit pourquoi.
- **Validations d'upload intactes** et dans le même ordre ; le comptage de pages reste sur
  poppler, avec le même repli.
- **Les en-têtes de sécurité survivent** à la nouvelle `location` nginx, et le commentaire
  explique le piège d'héritage d'`add_header`.
- **Les liens de store restent étanches** : le service ne remonte que slug, état, date.
- **`pipefail` dans le gate** : un test rouge ne peut plus passer pour vert derrière `tee`.
- **pdfium sérialisé** : plus d'appel concurrent non protégé depuis la route `/pages`.

---

## Verdict partiel : GO

Score **97/100**, **0 CRIT**, **1 MAJ**, **9 MIN**, **9 INFO** — score inchangé par rapport au
re-audit sur `a6fb539` ; la remédiation n'introduit aucune régression de sécurité dans le code
applicatif, et un seul constat d'hygiène CI (MIN). Conditions, inchangées :

1. 8.5.1 conforme **sous réserve du scan Trivy du Release Gate**, qui n'a pas tourné sur cet
   arbre ; s'il échoue : 92/100, 1 CRIT → NO-GO.
2. #378 soldé (ou re-daté avec justification) avant le 2026-12-31.
3. Recommandé avant publication : `TrustedHostMiddleware` (lève le seul MAJ),
   `permissions: contents: read` dans `ci.yml`, bornes `max_length` de l'éditeur,
   `npm audit fix`.
