# Rapport d'audit : Sécurité

> **Re-audit de release/0.7.3 @ e01fd95 — score 89 → 97 (scan Trivy `local` du run `41464248455` vert)**

> **Résultat du gate, relevé par l'orchestrateur après la fin du run (2026-11-02)** : le Release Gate
> `41464248455` (PR #366, `e01fd95`) a fini en **`success`, avec les 13 jobs verts**. Les deux scans,
> `Security scan — remote` et `Security scan — local`, sont verts. `Docker smoke test`, `Image size check`,
> `E2E API tests (full scope)`, `E2E UI tests (@critical)` et `Release summary` sont verts aussi.
> Les scores et les verdicts provisoires ci-dessous sont donc confirmés dans leur branche « gate vert ».


**Release** : 0.7.3
**Date** : 2026-11-02
**Auditeur** : claude-code
**Type** : re-audit après remédiation (audit initial @ `02adc68` = 89/100, 1 CRIT, 2 MAJ, 5 MIN, 5 INFO ; rapport `reports/release-0.7.3/08-security.md`)
**Branche** : `release/0.7.3` @ `e01fd95` (merge de la PR #367)

Méthode : lecture de `git log` et `git diff 02adc68..e01fd95` (commits sécurité
`7246efe`, `3cc0160`, `79b9ae9`, plus `d1a131f` et `eb84d77`), re-vérification de
chaque item de la checklist au working tree (les fichiers que la remédiation n'a pas
touchés sont confirmés inchangés par
`git diff --quiet 02adc68..e01fd95 -- api/ domain/ persistence/ bootstrap/ main.py
infra/rate_limiter.py infra/llm/ nginx*.template docker-compose.yml README.md
SECURITY.md frontend/src/shared/ frontend/src/features/mcp-config/ui/` ; l'analyse
initiale est reprise pour eux), vérification ponctuelle dans le code des affirmations
qui justifient les suppressions Pillow, `npm audit --omit=dev` dans `frontend/`
(lecture seule), et **une seule** lecture de l'état du Release Gate (run
`41464248455`, PR #366, tête `e01fd95`). `pip-audit` n'est pas installé : il n'a pas
été installé. Ni l'app ni Docker n'ont été lancés.

Note : le venv local est en retard sur `uv.lock` (installés : docling-core 2.87.1,
mcp 2.1.1, PyJWT 2.13.0, docling-parse 5.11.0 ; verrouillés : 2.92.0, 2.2.0, 2.15.1,
7.15.0). Les comportements de bibliothèque cités ci-dessous (docling-core, pdf2image)
ont été lus dans le venv. Les images, elles, sont construites depuis `uv.lock` en
`--frozen`.

---

## Score de compliance

| Métrique | Si `Security scan — local` est vert | Si `Security scan — local` échoue |
|----------|-------------------------------------|-----------------------------------|
| Items conformes | 13 / 14 | 12 / 14 |
| Score | **97 / 100** | 89 / 100 |
| Écarts CRITICAL | **0** | 1 |
| Écarts MAJOR | 2 | 2 |
| Écarts MINOR | 6 | 6 |
| Écarts INFO | 4 | 4 |

Détail du calcul : poids total = 36. Item 8.5.2 (poids 1) toujours non conforme.
Item 8.5.1 (poids 3) **en attente du gate (run 41464248455)**.
- Scan local vert : 36 − 1 = 35 → 35/36 = 97,2 → **97**.
- Scan local rouge : 36 − 3 − 1 = 32 → 32/36 = 88,9 → **89**.

État du gate, lu une fois (2026-11-02) : run `in_progress`. Docker build remote et
local, Unit tests, Lint & type-check, Dependency audit, Audit checks, Image size et
Docker smoke test sont en `success`. **`Security scan — remote` : `success`**.
**`Security scan — local` : en cours**. Les E2E API et UI sont en cours. Je ne l'ai
pas attendu, conformément à la consigne.

Comme dans l'audit initial, les deux [MAJ] portent sur l'exposition réseau et
l'authentification, que la checklist ne pondère pas : ils ne font pas basculer
d'item.

---

## Vérification de la remédiation (par item)

| # | Item | Poids | Initial | Re-audit | Preuve (@ `e01fd95`) |
|---|------|-------|---------|----------|----------------------|
| 8.1.1 | Aucun secret en dur | 3 | Oui | **Oui** (inchangé) | la remédiation n'ajoute que des commentaires, des versions et des statements ; `git ls-files` → seul `.env.example` ; grep `sk-`/`ghp_`/`hf_`/`AKIA` vide |
| 8.1.2 | `.env` dans `.gitignore` | 3 | Oui | **Oui** (inchangé) | `.gitignore:26-28` |
| 8.1.3 | Secrets Docker par env | 2 | Oui | **Oui** | ARG toujours limités à `APP_VERSION`, `BAKE_MODELS`, `WITH_REASONING` (`Dockerfile:13,24,86,90`, `document-parser/Dockerfile:59,63`) ; le bump uv n'ajoute ni ARG ni secret (`Dockerfile:36`, `document-parser/Dockerfile:17`) |
| 8.2.1 | Entrées validées par Pydantic | 3 | Oui | **Oui** (inchangé) | `api/` et `domain/` inchangés ; `api/schemas.py:272-276` puis `infra/docling_importer.py:18` |
| 8.2.2 | `MAX_FILE_SIZE_MB` appliqué à l'upload | 3 | Oui | **Oui** (inchangé) | `api/documents.py:69-88` ; `infra/settings.py:28,216`. L'import JSON n'a toujours pas de plafond, voir [MIN] |
| 8.2.3 | Types de fichiers validés | 2 | Oui | **Oui** (inchangé) | `services/document_service.py:27,78-81` (`%PDF`, extension forcée `.pdf`) |
| 8.3.1 | SQL en paramètres liés | 3 | Oui | **Oui** (inchangé) | `persistence/` inchangé ; `analysis_repo.py:144`, `document_repo.py:93,118` (f-strings de constantes et de `?`) ; `LIKE` échappé (`document_repo.py:21,89-90`) |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | Oui | **Oui** | grep `eval(`, `exec(`, `os.system(`, `subprocess.`, `shell=True`, `pickle.load` vide |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | Oui | **Oui** | seul `v-html` : `frontend/src/shared/ui/MarkdownViewer.vue:3,24`. `citation_app.html` ne change que `lang="en"` → `lang="fr"` (`6711444`) |
| 8.4.1 | CORS explicite | 3 | Oui | **Oui** (inchangé) | `main.py:89-95` ; `infra/settings.py:76-78,199` (+1 ligne de décalage, commentaire MCP) |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | Oui | **Oui** (inchangé) | `main.py:96-101` ; `infra/rate_limiter.py:59,71` |
| 8.4.3 | Nginx sans directory listing | 2 | Oui | **Oui** (inchangé) | `frontend/nginx.conf.template:14`, `nginx.conf.template:14` (`try_files`), pas d'`autoindex` |
| 8.5.1 | Pas de CVE critique connue | 3 | **Non** | **En attente du gate (run 41464248455)**. Remote vert ; local en cours | paquets corrigés : `uv.lock:2748-2749` (PyJWT 2.15.1), `:300-301` (certifi 2026.10.23), `:1725-1726` (mcp 2.2.0, borne `pyproject.toml:25`), uv 0.13.6 (`Dockerfile:36`, `document-parser/Dockerfile:17`, `embedding-service/Dockerfile:9`). Risques acceptés : `.trivyignore.yaml:7-20` (libxml2, renouvelée), `:21-55` (Pillow ×4). npm : 0 CRITICAL |
| 8.5.2 | Versions épinglées | 1 | Non | **Non** (inchangé) | `document-parser/pyproject.toml:42-43` (`torch`, `torchvision` sans version) |

### Détail 8.5.1

- **Ce que prouve le scan `remote` vert** : sur l'image `remote`, aucune CVE CRITICAL
  hors suppressions valides. Les cinq causes relevées par l'orchestrateur sur le run
  `41452005966` ne bloquent plus : PyJWT, certifi, le paquet `uv`, le crate `zip` de
  `/usr/local/bin/uv` et Pillow (supprimé). Les nouvelles versions (aiohttp 3.14.5,
  multidict 6.9.1, opentelemetry-api 1.45.2, urllib3 2.8.0, yarl 1.25.1, mcp 2.2.0)
  n'apportent aucune CRITICAL. La suppression anticipée de CVE-2026-13221 (perl,
  présent dans `python:3.12-slim`) n'a pas fait réapparaître d'alerte. Les builds
  verts confirment aussi que `uv==0.13.6` s'installe, et les unit tests verts que
  mcp 2.2.0 garde la garde anti-rebinding (421, `tests/test_mcp_mount.py`).
- **Ce qui reste à confirmer sur le scan `local`** : la suppression de CVE-2026-40393
  (mesa, tiré par `libgl1`, `Dockerfile:92-95`) et de CVE-2026-58016 (glib), que
  `.trivyignore.yaml:2-6` retire avant expiration au motif que Debian a publié les
  correctifs ; le renouvellement de CVE-2026-6653 (libxml2) ; et les wheels du
  groupe `local` (docling, torch, opencv).
- **Si le scan local échoue** : télécharger l'artefact `trivy-local`, nommer les CVE,
  puis corriger ou accepter chaque entrée comme pour Pillow. 8.5.1 reste alors
  [CRIT] et le verdict est NO-GO.

---

## État des écarts de l'audit initial

| Écart initial | Statut au re-audit | Preuve |
|---------------|--------------------|--------|
| [CRIT] Gate Trivy CRITICAL en échec (8.5.1) | **Corrigé côté remote ; en attente côté local.** Paquets corrigeables montés ; 4 CVE Pillow et libxml2 en **risque accepté**, daté et justifié | `7246efe`, `79b9ae9` ; `.trivyignore.yaml:7-55` ; `CHANGELOG.md:31-34` ; run `41464248455` |
| [MAJ] MCP actif par défaut, garde `Host` forgeable, présentée comme restriction réseau | **Partiellement corrigé : reste [MAJ]**, à périmètre réduit. Doc, CHANGELOG, commentaire et `.env.example` sont exacts ; README et panneau Settings disent encore « localhost only » ; défaut inchangé | voir [MAJ] ci-dessous |
| [MAJ] `/api/*` sans validation du `Host` (DNS rebinding) | **Inchangé : ouvert** | `main.py:89-101` ; nginx inchangé |
| [MIN] Écritures de config MCP sans auth (base des deep links) | **Inchangé** | `api/config.py:80-103` ; `domain/mcp_config.py:94-104` |
| [MIN] Import JSON sans plafond, traitement sur la boucle | **Partiellement corrigé** : validation et exports dans un thread ; pas de plafond | `services/analysis_service.py:177-180` ; `api/schemas.py:276` |
| [MIN] Rate limiter global derrière nginx | **Inchangé** | `infra/rate_limiter.py:71` |
| [MIN] `npm audit` : 7 HIGH, 0 CRITICAL | **Inchangé** (re-vérifié : `{'high': 7, 'critical': 0}`) | `frontend/package-lock.json` (seul le champ `version` a changé) |
| [MIN] torch / torchvision sans version (8.5.2) | **Inchangé** | `pyproject.toml:42-43` |
| [INFO] SSRF Ollama : résidus | **Inchangé** | `infra/llm/ollama_probe.py:60,69-72,87-88` |
| [INFO] API sans authentification | **Inchangé** | `SECURITY.md:51` |
| [INFO] Pas de garde `CORS_ORIGINS="*"` + credentials | **Inchangé** | `infra/settings.py:199,243` ; `main.py:92` |
| [INFO] Gate pip-audit inopérant | **Corrigé.** L'étape ne prétend plus bloquer : elle compte les avis et émet un warning. Les CRITICAL Python sont bloqués par Trivy (python-pkg) sur les images | `.github/workflows/release-gate.yml:127-145,175-179,352-360` (`eb84d77`) |
| [INFO] nginx maître en root, pas de CSP | **Inchangé** | `frontend/Dockerfile` ; `frontend/nginx.conf.template:7-11` |

---

## Vérification des affirmations qui justifient les suppressions Pillow

Mécanisme : 4 CVE CRITICAL de Pillow 10.4.0, présentes dans les deux images, sont
supprimées jusqu'au 2026-12-31 (`.trivyignore.yaml:32-55`). La justification est
commune (`:21-31`), il y a un statement par CVE, et le risque est annoncé dans
`CHANGELOG.md:34`. C'est le même mécanisme que celui que le gate 0.7.0 a admis pour
les suppressions OS : je le compte comme une acceptation de risque valide pour 8.5.1.

| Affirmation | Verdict | Preuve |
|-------------|---------|--------|
| « Studio's own code opens with Pillow only the PNG pages it renders itself » | **Exact**, avec une nuance | le seul `Image.open` du code Studio est `infra/page_raster.py:44`, sur le PNG produit par `render_page` (`:26-33`). Son seul appelant passe ce PNG (`services/citation_image_service.py:90-91`). Nuance : `pdf2image` (`page_raster.py:28`, `document_service.py:162`) décode aussi avec Pillow le flux **PPM** que `pdftoppm` génère (`.venv/.../pdf2image/pdf2image.py:283` `fmt="ppm"`, `parsers.py:28`). C'est un raster produit par poppler, pas un codec choisi par l'attaquant. Aucun des quatre vecteurs (écriture TIFF, FPX, JPEG, EPS) n'est en jeu |
| « saves only PNG and WebP » | **Exact** | `page_raster.py:32,61,63` ; `document_service.py:167`. Aucun autre `.save(` dans `document-parser/` hors tests |
| « uploads are PDFs only » | **Exact** | `services/document_service.py:78-79` (magic `%PDF`), `:81` (extension forcée) ; le convertisseur local ne configure que `InputFormat.PDF` (`infra/local_converter.py:71-75`) |
| « the Docling import keeps embedded images as data and its exports use placeholders, so nothing decodes them » | **Exact** | `infra/docling_importer.py:18-26` : `model_validate` (`ImageRef` n'a qu'un validateur de `mimetype`, `docling_core/types/doc/common/reference.py:130`), `export_to_markdown` et `export_to_html` (défaut `ImageRefMode.PLACEHOLDER`, `document.py:3664,3969`), `export_to_dict`. Aucun code Studio ne lit `.image`, `pil_image` ou `get_image` (grep vide). Le décodage est paresseux (`reference.py:93-126`) et n'est jamais déclenché. `file://` est refusé par défaut (`reference.py:100-101`) |
| « no Ghostscript is installed » | **Exact (vérifié statiquement)** | listes apt : `Dockerfile:28-32` (poppler-utils, nginx, gettext-base) et `:92-95` (libgl1, libglib2.0-0) ; `document-parser/Dockerfile:13-15,66-69`. Toutes en `--no-install-recommends`. Pas de vérification sur SBOM |
| « Not checked: every path inside docling during a conversion » | **Honnête** | conversion locale de PDF non fiables avec Pillow chargé (image `local`). Je ne l'ai pas vérifié non plus |
| « the docling packages the lock pins cap Pillow below 13 » | **Exact mais incomplet** | docling-core, docling-parse et docling-ibm-models déclarent `pillow<13` (vu dans le venv). Mais Studio plafonne **lui-même** `pillow>=10.0.0,<11.0.0` (`document-parser/pyproject.toml:14`, `uv.lock:919`) : ce plafond devra aussi être relevé, et la justification ne le dit pas |
| « Upgrading docling is planned for 0.8.0 » | **Non tracé** | aucune issue ne porte la montée Pillow 13. L'issue #361 (sans milestone) vise docling 2.140.0, docling-core 2.102.0, docling-parse 7.22.3 et docling-ibm-models 4.0.3, soit **sous** les seuils cités par `.trivyignore.yaml:22-24` (2.142, 2.104, 7.22.4, 4.0.4). Elle exclut aussi de toucher `pyproject.toml`. Telle que cadrée, elle n'apporterait pas Pillow 13 |

Conclusion : les déclarations sont honnêtes. Elles disent ce qui a été vérifié et ce
qui ne l'a pas été, et les vérifications annoncées tiennent dans le code. Les deux
manques, le plafond `<11` propre à Studio et l'absence d'issue qui livre réellement
Pillow 13, portent sur la levée du risque, pas sur sa description. Ils sont reportés
en [MIN] ci-dessous.

---

## Écarts constatés (restants)

### [MAJ] MCP : la garde `MCP_ALLOWED_HOSTS` est encore présentée comme « localhost only » dans le README et le panneau Settings ; défaut inchangé (MCP actif, port publié sur toutes les interfaces)

- **Localisation** :
  - affirmations encore inexactes : `README.md:31` (« over MCP (on by default,
    localhost only, switchable in Settings) ») ;
    `frontend/src/features/mcp-config/ui/McpConfigSection.vue:55-59` (libellé et
    icône de bouclier, sans style `warn`) et `:410-415` (le commentaire « the server
    is out of reach of other machines ») ; `frontend/src/shared/i18n.ts:415`
    (« En local uniquement, sans authentification ») et `:1136` (« Local only, no
    authentication »).
  - défaut inchangé : `document-parser/infra/settings.py:97` (`mcp_enabled = True`),
    `docker-compose.yml:193` et `:205-206` (`"3000:80"`), `README.md:17`
    (`-p 3000:3000`).
  - corrigé par `3cc0160` : `infra/settings.py:90-96`, `CHANGELOG.md:15`,
    `docs/mcp-server.md:14-20,324-331`, `.env.example:102-106`.
- **Constat** : la remédiation a rendu exacts les quatre emplacements que l'audit
  initial citait. `docs/mcp-server.md:17-19` dit même que compose publie 3000 sur
  toutes les interfaces et propose de le lier à `127.0.0.1`. Deux emplacements, que
  l'audit initial n'avait pas relevés, affirment toujours le contraire, et ce sont
  les plus lus : la page d'accueil du dépôt, et le panneau que l'opérateur ouvre pour
  piloter le serveur. Le panneau affiche « Local only » avec un bouclier dès que la
  liste d'hôtes ne contient que des adresses loopback, **c'est-à-dire par défaut**.
  L'alerte « No authentication: anyone who can reach this port reads every
  document » (`i18n.ts:1137-1138`) n'apparaît que si la liste est élargie : c'est
  l'inverse du cas dangereux. Or un client réseau qui envoie `Host: localhost:3000`
  passe la garde (constat initial inchangé, nginx transmet `$http_host`,
  `frontend/nginx.conf.template:32`).
- **Niveau : MAJ maintenu.** La fiche 08 ne pondère ni l'authentification ni
  l'exposition par défaut (8.4 ne couvre que CORS, rate limiter et nginx). Le niveau
  relève donc du jugement de l'auditeur (master §2). L'argument du mainteneur tient
  sur le fond : l'app n'a pas de login (`SECURITY.md:51`), donc qui atteint le port
  3000 lit déjà tout via `/api/documents/*`. `/mcp`, en lecture seule, n'expose aucune
  donnée nouvelle. L'audit initial avait déjà retenu cet atténuant et classé MAJ
  malgré lui. **Seule**, l'exposition par défaut ne vaudrait donc qu'un [MIN] (défaut
  non sécurisé, même posture que `/api`, documentée). Le MAJ tenait à autre chose :
  une garde anti-rebinding était présentée à l'opérateur comme une restriction
  réseau. Cette fausse assurance subsiste dans le produit lui-même. La correction
  documentaire, qui était l'option retenue par le mainteneur, est donc incomplète,
  et l'écart n'est pas résolu. Il ne bloque pas seul : 2 MAJ ≤ 3.
- **Règle violée** : 8.4 (réseau), écart additionnel sans impact de score.
- **Remédiation** :
  1. `README.md:31` : remplacer « localhost only » par « no authentication; keep
     port 3000 off untrusted networks ».
  2. Panneau Settings : afficher toujours l'avertissement « sans authentification »,
     et décrire la liste loopback comme une « protection anti-DNS-rebinding », pas
     comme « local uniquement » (`McpConfigSection.vue:55-59,410-415` ;
     `i18n.ts:415,1136`).
  3. Avec ces deux corrections, l'écart **descend en [MIN]**. Publier
     `127.0.0.1:3000:80` par défaut en compose (et `-p 127.0.0.1:3000:3000` dans le
     README) le lèverait entièrement. Le jeton `MCP_TOKEN` reste pour la 0.8.0.

### [MAJ] `/api/*` sans validation du `Host` : DNS rebinding possible contre une instance locale (inchangé)

- **Localisation** : `document-parser/main.py:89-101` (`CORSMiddleware` et
  `RateLimiterMiddleware` seulement, aucun `TrustedHostMiddleware` dans
  `document-parser/`) ; `frontend/nginx.conf.template:1-24` et `nginx.conf.template:1-24`
  (serveur par défaut sans `server_name`).
- **Constat** : fichiers inchangés depuis `02adc68`, analyse initiale reprise. Une
  page web peut faire pointer son domaine vers 127.0.0.1:3000 et émettre des requêtes
  same-origin : lecture de tous les documents, `DELETE /api/documents/{id}`,
  `PUT /api/config/reasoning`, `PUT /api/config/mcp`. `/mcp` est protégé contre ce
  scénario (421), `/api/*` ne l'est pas. L'exploitation est **PLAUSIBLE** et dépend
  du navigateur. Cet écart ne figurait pas parmi les décisions soumises au mainteneur
  et n'a pas été traité.
- **Règle violée** : 8.4 (réseau), écart additionnel sans impact de score.
- **Remédiation** : `TrustedHostMiddleware` (défaut `localhost`, `127.0.0.1`,
  `[::1]`, configurable), ou `server_name` explicite et `default_server` qui répond
  421 dans nginx.

### [MIN] Risque accepté : 4 CVE CRITICAL de Pillow 10.4.0 supprimées jusqu'au 2026-12-31, sans issue qui livre le correctif

- **Localisation** : `.trivyignore.yaml:21-55` ; `CHANGELOG.md:34` ;
  `document-parser/pyproject.toml:14` (`pillow>=10.0.0,<11.0.0`) ;
  `document-parser/uv.lock:2377-2378` (10.4.0). Renouvellement de libxml2 :
  `.trivyignore.yaml:7-20`.
- **Constat** : risque explicitement accepté, daté et justifié, et les vérifications
  annoncées tiennent (tableau ci-dessus). Le risque résiduel n'est pas le même dans
  les deux images :
  - **image `remote`** : Pillow n'y est atteint que par le code Studio, sur des
    rasters qu'il a lui-même produits, et par l'import, qui reste en mode
    placeholder. Le risque est négligeable.
  - **image `local`** : docling convertit des PDF non fiables avec Pillow chargé, et
    ce chemin n'est pas vérifié, ce que la justification reconnaît. CVE-2026-112403
    (`ImagingJpegDecode`) est la seule des quatre qu'un chemin interne à docling
    pourrait plausiblement atteindre. **Non démontré.**

  Trois manques portent sur la levée du risque :
  1. le plafond `pillow<11` de Studio n'est pas mentionné ;
  2. aucune issue ne livre Pillow 13 : #361, sans milestone, vise des versions docling
     sous les seuils de `.trivyignore.yaml:22-24` et exclut `pyproject.toml` ;
  3. les 5 suppressions restantes expirent toutes le 2026-12-31 : le premier gate
     lancé après cette date échouera si la 0.8.0 n'est pas sortie.

  Le statement libxml2 est daté et exact quant à son impact (DoS, image `local`). Je
  n'ai pas pu revérifier hors ligne le tracker Debian qu'il cite.
- **Règle violée** : 8.5.1, défense en profondeur. L'item est conforme par
  acceptation de risque, sous réserve du scan `local`. Un risque accepté à lever au
  prochain cycle relève du [MIN]. **Il ne bloque pas.**
- **Remédiation** : ouvrir une issue au milestone 0.8.0, ou élargir #361, avec
  docling ≥ 2.142, docling-core ≥ 2.104, docling-parse ≥ 7.22.4, docling-ibm-models
  ≥ 4.0.4 **et** `pillow>=13,<14` dans `pyproject.toml:14`. La référencer dans
  `.trivyignore.yaml:21-31`. Retirer les 4 suppressions dans la même PR.

### [MIN] Écritures de config MCP sans authentification : bascule du serveur et réécriture de la base des deep links (inchangé)

- **Localisation** : `document-parser/api/config.py:80-103` ;
  `document-parser/domain/mcp_config.py:94-104` ; `services/citation_service.py:279-292`.
- **Constat** : fichiers inchangés, analyse initiale reprise. `PUT /api/config/mcp`
  peut rallumer ou éteindre le serveur, et fixer `studioBaseUrl` à un hôte
  attaquant. Les liens des citations relayés par l'agent pointent alors vers cet
  hôte, et la valeur est persistée en base. 403 sur Hugging Face
  (`bootstrap/builder.py:255`).
- **Règle violée** : 8.2.1 (défense en profondeur). Item conforme.
- **Remédiation** : `MCP_STUDIO_BASE_URL` restart-only, ou liste d'hôtes autorisés ;
  journaliser chaque changement en WARNING.

### [MIN] Import d'analyse Docling (#359) : toujours sans plafond de taille (traitement désormais hors boucle)

- **Localisation** : `document-parser/api/analyses.py:73-87` ;
  `document-parser/api/schemas.py:276` (`document: dict`) ; plafond nginx seul :
  `docker-compose.yml:208` (200 Mo).
- **Constat** : `d1a131f` exécute la validation et les trois exports dans un thread
  (`services/analysis_service.py:177-180`). La moitié « boucle d'événements » de
  l'écart est corrigée. Restent deux points :
  - le corps n'a toujours pas de plafond applicatif, et le parse JSON de la requête
    se fait encore sur la boucle, avant le handler ;
  - plusieurs imports peuvent maintenant tourner en parallèle dans le pool de
    threads, ce qui fait monter la mémoire plus vite pour un même volume de requêtes.

  Épuisement mémoire du conteneur (limite 4g) : **PLAUSIBLE**.
- **Règle violée** : 8.2.2 dans son esprit. Item conforme au sens strict (upload PDF).
- **Remédiation** : Content-Length et lecture bornée, alignés sur
  `MAX_FILE_SIZE_MB` ; `client_max_body_size` réduit sur `/api/analyses/import`.

### [MIN] Rate limiter « par IP » en réalité global derrière nginx (inchangé)

- **Localisation** : `document-parser/infra/rate_limiter.py:71` (`request.client.host`) ;
  `Dockerfile:65` (uvicorn sur 127.0.0.1 derrière nginx).
- **Constat** : inchangé. Toutes les requêtes partagent le seau de l'IP de nginx.
- **Règle violée** : 8.4.2 (sémantique). Item conforme.
- **Remédiation** : `--proxy-headers --forwarded-allow-ips`, ou `limit_req` dans nginx.

### [MIN] `npm audit` (production) : 7 HIGH, 0 CRITICAL (inchangé)

- **Localisation** : `frontend/package.json` ; `frontend/package-lock.json` (dompurify,
  lodash, nanoid, postcss, source-map-js, vue).
- **Constat** : `npm audit --omit=dev` le 2026-11-02 donne `high: 7, critical: 0`,
  comme à l'audit initial. Les avis DOMPurify visent des options non utilisées
  (`MarkdownViewer.vue:24` appelle `sanitize(html)` sans option).
- **Règle violée** : hygiène, 8.5.1 non impacté.
- **Remédiation** : `npm audit fix`.

### [MIN] Dépendances backend sans version : torch / torchvision (inchangé)

- **Localisation** : `document-parser/pyproject.toml:42-43`.
- **Constat** : inchangé ; atténué par `uv.lock` en `--frozen`, groupe `local`.
- **Règle violée** : 8.5.2.
- **Remédiation** : `torch>=2,<3`, `torchvision<1`, ou exemption documentée.

### [INFO] SSRF Ollama : garde intacte, résidus inchangés

- **Localisation** : `document-parser/infra/llm/ollama_probe.py:60,69-72,87-88` ;
  `domain/app_config.py:77-86`.
- **Constat** : inchangé (TOCTOU, LAN autorisé, Save non filtré, documenté
  `SECURITY.md:48`).

### [INFO] API sans authentification (inchangé, documenté)

- **Localisation** : `document-parser/main.py:89-125` ; `SECURITY.md:51`.
- **Constat** : inchangé. C'est le socle de l'argument du mainteneur sur MCP, voir le
  [MAJ] MCP.

### [INFO] Pas de garde-fou contre `CORS_ORIGINS="*"` avec credentials (inchangé)

- **Localisation** : `document-parser/infra/settings.py:199,243` ; `main.py:92`.

### [INFO] nginx : processus maître en root, pas de Content-Security-Policy (inchangé)

- **Localisation** : `frontend/Dockerfile` (`nginx:alpine`, sans `USER`) ;
  `Dockerfile:65` ; `frontend/nginx.conf.template:7-11`.

---

## La remédiation a-t-elle introduit un écart ?

Non. Points vérifiés :
- `7246efe` : uniquement des montées de version. Builds, unit tests et scan
  `remote` sont verts sur le run `41464248455`, et npm n'a pas bougé (0 CRITICAL).
- `79b9ae9` : la suppression est honnête et datée. Ses manques sont reportés en [MIN].
- `3cc0160` : documentation et commentaires seulement, aucun changement de
  comportement. Couverture incomplète, voir [MAJ].
- `d1a131f` : `asyncio` est importé (`services/analysis_service.py:9`) et un test a
  été ajouté. Le parallélisme qui en découle est noté dans le [MIN] import.
- `eb84d77` : le contrôle pip-audit cesse de mentir. Pas de régression, puisque
  l'ancien filtre ne se déclenchait jamais.
- `6711444` et `8465931` : attribut `lang` et déplacement de types, sans surface de
  sécurité.

---

## Points positifs

- Les paquets corrigeables du CRIT ont tous été montés. La version est expliquée
  dans le Dockerfile (`Dockerfile:34-36`) et dans `pyproject.toml:24-25`.
- Les suppressions OS devenues inutiles sont retirées au lieu d'être prolongées,
  avec une trace (`.trivyignore.yaml:2-6`).
- L'acceptation de risque Pillow est un modèle du genre : elle sépare « vérifié » et
  « non vérifié », chaque statement dit pourquoi la CVE est peu atteignable, le
  délai est court et le CHANGELOG l'annonce aux utilisateurs.
- La documentation MCP (`docs/mcp-server.md:14-20,324-331`) décrit maintenant
  exactement ce que la garde protège et ce qu'elle ne protège pas, et propose les
  bonnes mesures (`127.0.0.1`, pare-feu, proxy authentifiant, `MCP_ENABLED=false`).
- Le gate Python est honnête (`release-gate.yml:134-145`).

---

## Verdict partiel : GO (scans `remote` et `local` verts, run `41464248455`)

- **Scan local vert** : 97/100, 0 CRIT, 2 MAJ (≤ 3) → **GO**. Les deux MAJ (libellé
  MCP « local only » dans le README et le panneau Settings ; `Host` non validé sur
  `/api/*`) vont au plan de remédiation. Le premier se règle en deux chaînes de
  caractères et passe alors en [MIN].
- **Scan local rouge** : 89/100, 1 CRIT (8.5.1) → **NO-GO** par la règle absolue,
  jusqu'au tri de l'artefact `trivy-local`.

Avant 0.8.0 : ouvrir une issue qui livre réellement Pillow 13, avec docling aux seuils
cités et le plafond `pillow<11` relevé, avant le 2026-12-31.
