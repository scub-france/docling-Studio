# Rapport d'audit : Sécurité

**Release** : 0.7.4
**Date** : 2026-11-18
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a6fb539` (= `release/0.7.4` @ `f7fc791`, avec PR #401 et #402, + 13 commits locaux #391-#400 + merge), arbre de travail
**Baseline** : `release-0.7.4/08-security.md` (2026-11-13, `eade7fa`, 97/100, 0 CRIT, 1 MAJ, 8 MIN, 7 INFO)

Méthode : lecture statique de l'arbre de travail, `git diff eade7fa a6fb539` (121 fichiers),
`npm audit` (lecture seule), `gh run list` / `gh run view` / `gh issue view` (lecture seule).
Rien n'a été exécuté côté application. Trivy n'est pas installé localement et le
**Release Gate n'a jamais tourné sur `release/0.7.4` ni sur `a6fb539`** (il ne se déclenche
que sur les PR vers `main`, `.github/workflows/release-gate.yml:3-5` ; la CI des PR #401 ne
contient aucun scan de sécurité, run 43752042089). Les CVE des images restent donc à
confirmer par le gate.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 97 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 8 |
| Écarts INFO | 8 |

Calcul : poids total 36 ; seul 8.5.2 (poids 1) est non conforme. `35 / 36 × 100 = 97,2` → **97**.
Même lecture que la baseline : 8.5.1 est compté conforme **sous réserve du scan Trivy du
gate** ; s'il échoue, 33/36 = **92** avec 1 CRIT → NO-GO. (La baseline annonçait 89 dans ce
cas : `32/36` ; le bon calcul est `33/36 = 91,7`.)

### Détail par item

| # | Item | Poids | Conforme | Justification (arbre `a6fb539`) |
|---|------|-------|----------|---------------------------------|
| 8.1.1 | Aucun secret en dur | 3 | oui | grep du diff `eade7fa..a6fb539` (`password=`, `secret=`, `api_key=`, `token=`, `sk-`, `ghp_`, `hf_`, `AKIA`, clés PEM) : seule occurrence = le rapport d'audit précédent ; dossier non suivi `experiments/mcp-bench/` également propre |
| 8.1.2 | `.env` dans `.gitignore` | 3 | oui | `.gitignore:26-28` ; seul `.env.example` est suivi |
| 8.1.3 | Secrets Docker par env | 2 | oui | `Dockerfile`, `document-parser/Dockerfile`, `docker-compose*.yml` inchangés depuis `eade7fa` (diff vide) |
| 8.2.1 | Entrées validées par Pydantic | 3 | oui | nouveau paramètre `format: Literal["png","webp"]` (`api/documents.py:179`), `page ge=1`, `dpi 72..300` (`:177-178`) ; schémas de l'éditeur inchangés, toujours sans borne de taille ([MIN]) |
| 8.2.2 | `MAX_FILE_SIZE_MB` appliqué | 3 | oui | `api/documents.py:76-89` (413 sur Content-Length puis lecture par blocs) ; `services/document_service.py:75-76` |
| 8.2.3 | Types de fichiers validés | 2 | oui | magic `%PDF` `services/document_service.py:27,78-79`, extension forcée et nom UUID `:81-83` |
| 8.3.1 | SQL en paramètres liés | 3 | oui | toutes les f-strings SQL de `persistence/` n'interpolent que des constantes du module ou des suites de `?` : `database.py:292-295,321,324`, `chunk_repo.py:109-112,163`, `analysis_repo.py:66-138`, `document_repo.py:78-81,106` |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | oui | grep `eval(`, `exec(`, `os.system(`, `subprocess.`, `shell=True`, `pickle.load` vide hors tests |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | oui | seul `v-html` : `frontend/src/shared/ui/MarkdownViewer.vue:3`, assaini `:24` ; PDF.js rend sur `<canvas>` sans calque d'annotations (`PdfPageCanvas.vue:51-58`) ; les apps MCP échappent les nouvelles interpolations (`esc()`, `textContent`) |
| 8.4.1 | CORS explicite | 3 | oui | `main.py:90-96`, `infra/settings.py:202,246` |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | oui | `main.py:97-102` ; exclusion `infra/rate_limiter.py:59,68` ; la nouvelle route preview et l'export PDF passent par le middleware |
| 8.4.3 | Nginx sans directory listing | 2 | oui | `nginx.conf.template:19-21`, `frontend/nginx.conf.template:13-15` (`try_files`), pas d'`autoindex` |
| 8.5.1 | Pas de CVE critique connue | 3 | oui, **sous réserve du gate** | npm prod : 0 CRITICAL (7 HIGH) ; `pdfjs-dist` 6.5.438 absent des avis ; Python : lock inchangé hors ajouts, Pillow 10.4.0 couvert par des suppressions valides jusqu'au 2026-12-31 ; images non scannées |
| 8.5.2 | Versions épinglées | 1 | **non** | `document-parser/pyproject.toml:45-46` (`torch`, `torchvision` sans version) |

---

## Écarts constatés

### [MAJ] `/api/*` sans validation du `Host` : DNS rebinding contre une instance locale — toujours présent

- **Localisation** : `document-parser/main.py:90-102` (CORS et rate limiter seulement, aucun
  `TrustedHostMiddleware` : grep `TrustedHost` vide) ; `nginx.conf.template:1-2` et
  `frontend/nginx.conf.template:1-2` (pas de `server_name`, pas de serveur par défaut qui
  rejette).
- **Constat (lu dans le code)** : rien n'a changé depuis `eade7fa`. `/mcp` reste protégé par
  `MCP_ALLOWED_HOSTS` (`infra/settings.py:265-268`), pas `/api/*`.
- **Scénario (hypothèse, non démontrée)** : un utilisateur qui fait tourner Studio sur
  `localhost:3000` visite une page hostile ; celle-ci fait résoudre son propre domaine vers
  127.0.0.1 et appelle en same-origin `GET /api/documents` puis
  `GET /api/documents/{id}/export?format=pdf` (lecture de tous les PDF), `DELETE
  /api/documents/{id}` ou `POST /api/documents/{id}/analysis-edits` (réécriture durable).
  PR #401 ne crée pas de nouvelle capacité (l'export PDF existait), mais rend la lecture plus
  commode (Range). Dépend du navigateur (protections anti-rebinding, Private Network Access).
- **Règle violée** : 8.4 (réseau), hors pondération.
- **Remédiation** : `TrustedHostMiddleware` aligné sur `MCP_ALLOWED_HOSTS`, ou
  `server_name` explicite + serveur par défaut en 421 dans nginx. Effort S.

### [MIN] Routes de l'éditeur sans borne de taille ; rejeu synchrone et persistant — toujours présent

- **Localisation** : `document-parser/api/schemas.py:150` (`text: str`), `:155-156`
  (`element_ids`, `separator`), `:180`, `:195` (`commands`) sans `max_length`.
- **Constat** : inchangé. Le diff `#394` déplace la projection dans
  `infra/docling_analysis_engine.py` sans ajouter de borne.
- **Scénario (hypothèse)** : un client non authentifié POST quelques Mo de commandes sur
  `/api/documents/{id}/analysis-edits` ; si c'est un *save*, elles sont persistées et
  rejouées à chaque reconstruction.
- **Remédiation** : `Field(max_length=...)` sur `commands`, `element_ids`, `text`,
  `separator`.

### [MIN] MCP actif par défaut, port publié sur toutes les interfaces — toujours présent

- **Localisation** : `document-parser/infra/settings.py:97` (`mcp_enabled = True`),
  `docker-compose.yml:208` (`"3000:80"`) ; documenté `README.md:31`, `SECURITY.md:51`.
- **Remédiation** : `127.0.0.1:3000:80` par défaut ; `MCP_TOKEN` en 0.8.0.

### [MIN] Risque accepté Pillow 10.4.0 / libxml2 : suppressions jusqu'au 2026-12-31, 43 jours restants — toujours présent

- **Localisation** : `.trivyignore.yaml:7-20` (libxml2), `:33-56` (Pillow ×4) ;
  `document-parser/pyproject.toml:14` ; `document-parser/uv.lock:2452-2453`.
- **Constat** : fichier inchangé. #378 (milestone 0.7.4) est toujours **OPEN** au
  2026-11-18. Les commentaires reportent la vraie correction à 0.8.0 (montée Docling) : si
  0.8.0 n'est pas sorti au 2026-12-31, le premier gate de 2027 échoue sur 8.5.1 (CRIT).
  La justification tient pour le code nouveau : la preview n'encode que du PNG ou du WebP
  sans perte (`services/document_service.py:175-178`), sans décodage d'image entrante.
- **Remédiation** : solder #378 avant le 2026-12-31 ou re-dater avec justification.

| Entrée ignorée | Composant | `expired_at` | État au 2026-11-18 |
|----------------|-----------|--------------|--------------------|
| CVE-2026-6653 (`.trivyignore.yaml:7`) | libxml2 (Debian 13, image `local`) | 2026-12-31 | valide, J-43 |
| CVE-2026-112393 (`:33`) | Pillow 10.4.0 (TIFF write) | 2026-12-31 | valide, J-43 |
| CVE-2026-112398 (`:39`) | Pillow 10.4.0 (FPX JPEG) | 2026-12-31 | valide, J-43 |
| CVE-2026-112403 (`:45`) | Pillow 10.4.0 (JPEG decode) | 2026-12-31 | valide, J-43 |
| CVE-2026-112900 (`:51`) | Pillow 10.4.0 (Ghostscript/EPS) | 2026-12-31 | valide, J-43 |

Aucune entrée expirée. Toutes expirent avant la livraison prévue de leur correctif (0.8.0).

### [MIN] Écritures de configuration MCP sans authentification — toujours présent

- **Localisation** : `document-parser/api/config.py:81-104` (PUT / DELETE `/api/config/mcp`) ;
  `document-parser/domain/mcp_config.py:94-104`.
- **Remédiation** : `MCP_STUDIO_BASE_URL` en redémarrage seul ou liste d'hôtes autorisés.

### [MIN] Import d'analyse Docling sans plafond de taille — toujours présent

- **Localisation** : `document-parser/api/analyses.py:73-87` ; `api/schemas.py:364`
  (`document: dict`) ; seul plafond : `client_max_body_size` nginx.
- **Remédiation** : plafond Content-Length aligné sur `MAX_FILE_SIZE_MB`.

### [MIN] Rate limiter « par IP » en réalité global derrière nginx — toujours présent

- **Localisation** : `document-parser/infra/rate_limiter.py:71` (`request.client.host`) ;
  `Dockerfile:65` (uvicorn sans `--proxy-headers`).
- **Constat** : toutes les requêtes arrivent de 127.0.0.1, donc un seul seau de 100 req/min
  (`infra/settings.py:29`) pour tous les utilisateurs. Avec PDF.js, chaque page visitée d'un
  gros PDF ajoute des requêtes Range de 256 Ko (`usePdfDocument.ts:29`) : un client peut
  épuiser le seau commun (déni de service applicatif, hypothèse).
- **Remédiation** : `--proxy-headers --forwarded-allow-ips 127.0.0.1`, ou `limit_req` nginx.

### [MIN] `npm audit` (production) : 7 HIGH, 0 CRITICAL — re-mesuré, inchangé

- **Localisation** : `frontend/package.json:24,28` ; `frontend/package-lock.json:2430-2431`
  (dompurify 3.3.3).
- **Constat (mesuré le 2026-11-18)** : `npm audit --omit=dev` → 7 high (`dompurify`,
  `vue` via `@vue/server-renderer`, `lodash`, `nanoid`, `postcss`, `source-map-js`) ;
  `npm audit` complet → 27 (17 moderate, 10 high, 0 critical). Exploitabilité lue dans le
  code : les avis DOMPurify visent `IN_PLACE`, `RETURN_DOM`, `SAFE_FOR_TEMPLATES`,
  `ADD_TAGS` en fonction, `CUSTOM_ELEMENT_HANDLING`, `setConfig()` ou un hook ; Studio
  appelle `DOMPurify.sanitize(html)` avec la config par défaut (`MarkdownViewer.vue:24`),
  sans hook ni `setConfig` (grep vide). L'avis Vue vise le rendu serveur, non utilisé.
  `pdfjs-dist` n'apparaît pas.
- **Remédiation** : `npm audit fix` (correctifs disponibles sans saut majeur selon npm).

### [MIN] Dépendances backend sans version : torch / torchvision — toujours présent (item 8.5.2)

- **Localisation** : `document-parser/pyproject.toml:45-46`.
- **Constat** : atténué par `uv.lock` en `--frozen`.
- **Remédiation** : `torch>=2,<3`, `torchvision<1`, ou exemption documentée.

### [INFO] PR #401 : l'original PDF chargé par PDF.js — surface vérifiée, pas d'écart

- **Route servie** : `GET /api/documents/{id}/export?format=pdf` (`usePdfDocument.ts:25-30`,
  `features/document/api.ts:68-76`) → `FileResponse(doc.storage_path)`
  (`api/documents.py:159-164`, `services/export_service.py:85-91`). Les Range sont gérés par
  Starlette 1.6.0 (`uv.lock:3597-3598`), version postérieure aux correctifs connus du
  parsing de Range.
- **Chemin (lu dans le code)** : `doc_id` ne sert qu'à une recherche par paramètre lié
  (`persistence/document_repo.py:90-93`). `storage_path` est toujours produit par le serveur
  (`uuid4` + `.pdf`, `services/document_service.py:81-83,106`) et **aucune route n'écrit ce
  champ** (grep `storage_path=` : seul `document_service.py:106`). Le repli de
  `resolve_storage_path` (`services/document_service.py:127-131`) prend `Path.name`, donc
  reste dans le dossier d'upload ; un nom `..` donne un dossier, refusé par `is_file()`.
  Conclusion : **aucune lecture hors du dossier d'upload n'est atteignable par HTTP**.
- **Défense en profondeur (hypothèse : base SQLite modifiée)** : l'export PDF et la preview
  servent tout fichier existant désigné par `storage_path` sans le confiner au dossier
  d'upload, alors que la suppression le fait (`document_service.py:144-149`). Écart de
  cohérence, à aligner (une fonction `confined_storage_path` partagée). Note fonctionnelle :
  l'export PDF n'utilise pas le repli de `resolve_storage_path`, la preview oui.
- **PDF.js** : `pdfjs-dist` 6.5.438 (`package.json:26`, `package-lock.json:3527-3528`).
  L'option `isEvalSupported` n'existe plus dans cette version : 0 occurrence de
  `isEvalSupported` et de `new Function(` dans `pdf.worker.mjs` installé. Pas de calque
  d'annotations ni `enableScripting`. Worker chargé depuis un asset du même origine
  (`usePdfDocument.ts:3,24` ; build : `dist/assets/pdf.worker.min-*.js`). Le PDF d'origine
  est désormais aussi analysé dans le navigateur : second parseur exposé aux PDF importés.

### [INFO] Cache de preview et `Cache-Control` — vérifiés, pas d'écart

- **Localisation** : `infra/preview_cache.py:16-40`, `services/preview_service.py:36-50`,
  `api/documents.py:183-188`.
- **Constat (lu dans le code)** : plafond de 64 Mo en octets avec éviction LRU sous verrou ;
  une image plus grosse que le plafond n'est pas stockée (`infra/preview_cache.py:30-31`). Clé = chemin résolu,
  taille, `mtime_ns`, page, dpi, format : deux documents ont des chemins UUID distincts, donc
  pas d'empoisonnement croisé ; le nombre d'entrées est borné par le plafond en octets. La
  page est vérifiée contre `page_count` **avant** la lecture du cache
  (`services/preview_service.py:31-39`).
  `private, max-age=86400, immutable` est sans risque : `private` exclut les caches partagés,
  les identifiants sont des UUID non réutilisés et le PDF n'est jamais remplacé.
- **Observation** : pas de coalescence des rendus concurrents sur un même miss (rendu 300 dpi
  coûteux, poppler en thread) ; sujet performance (audit 12).

### [INFO] nginx : le diff est un ajout gzip, pas Range/MIME

- **Localisation** : `nginx.conf.template:4-8` (`gzip on`, `gzip_types application/json`).
- **Constat** : aucun en-tête de sécurité retiré ; les `add_header` du niveau `server`
  (`:14-17`) restent hérités par `/api/` (aucun `add_header` dans la location). Compression
  JSON sans risque BREACH pratique : aucune réponse JSON ne porte de secret (schémas de
  config sans clé ni jeton). `frontend/nginx.conf.template` n'a pas reçu le même ajout.
  Toujours pas de CSP (reconduit).

### [INFO] DDL de montée de schéma 0.7.3 → 0.7.4 en f-string sur des constantes (#391)

- **Localisation** : `document-parser/persistence/database.py:292-295` (`_ADDED_COLUMNS`,
  tuple littéral), `:320-324` (`PRAGMA table_info`, `ALTER TABLE ... ADD COLUMN`) ; le
  backfill `_BACKFILL_ACTIVE_ANALYSIS` est une constante sans interpolation.
- **Constat** : aucune entrée utilisateur. Conforme à 8.3.1 ; garder ce tuple littéral.

### [INFO] Messages d'erreur 400 qui recopient la validation Pydantic interne — toujours présent

- **Localisation** : `document-parser/infra/docling_editor.py:46,61`, renvoyés en `detail`
  par `api/errors.py:31` (nouveau point unique de traduction, #396).

### [INFO] Flag éditeur coupé : l'export par défaut sert toujours le résultat actif (édité) — toujours présent

- **Localisation** : `services/export_service.py:114-120,136-138` ; `services/chunk_service.py:369-371,702-704`.
- **Constat** : le défaut passe par `active_result_service`, qui applique les éditions
  sauvegardées ; le flag n'est pas un interrupteur de retour arrière. Pas de fuite.

### [INFO] Constats reconduits sans changement

| Constat | Localisation vérifiée |
|---------|-----------------------|
| SSRF Ollama : résidus (TOCTOU, LAN autorisé) | `document-parser/infra/llm/ollama_probe.py` (hors diff) ; `SECURITY.md` |
| API sans authentification (documenté) | `SECURITY.md:51` ; `main.py:90-102` |
| Pas de garde `CORS_ORIGINS="*"` avec credentials | `infra/settings.py:246` ; `main.py:92-93` |
| nginx maître en root, pas de CSP | `Dockerfile:65` ; `nginx.conf.template:13-17` |

---

## Delta vs audit du 2026-11-13

| Écart du 2026-11-13 | Statut à `a6fb539` |
|---------------------|--------------------|
| [MAJ] `Host` non validé sur `/api/*` | **Toujours présent** (`main.py:90-102`) |
| [MIN] Routes de l'éditeur non bornées | Toujours présent (`api/schemas.py:150,155-156,180,195`) |
| [MIN] MCP actif par défaut, 0.0.0.0 | Toujours présent (`settings.py:97`, `docker-compose.yml:208`) |
| [MIN] Pillow / libxml2 risque accepté | Toujours présent ; J-43 ; #378 OPEN |
| [MIN] Écritures config MCP sans auth | Toujours présent (`api/config.py:81-104`) |
| [MIN] Import JSON sans plafond | Toujours présent (`api/analyses.py:73-87`) |
| [MIN] Rate limiter global | Toujours présent (`rate_limiter.py:71`) ; pression accrue par les Range PDF.js |
| [MIN] `npm audit` 7 HIGH | **Re-mesuré** : 7 HIGH / 0 CRIT en prod ; 27 au total |
| [MIN] torch / torchvision (8.5.2) | Toujours présent (`pyproject.toml:45-46`) |
| [INFO] flag et lectures par défaut | Toujours présent (code de l'export restructuré, même effet) |
| [INFO] détail d'erreur Pydantic | Toujours présent (désormais via `api/errors.py:31`) |
| [INFO] DDL f-string | Toujours présent, constantes vérifiées |
| — | **Nouveaux [INFO]** : surface PDF.js / export PDF (pas d'écart, confinement à aligner), cache de preview (vérifié), gzip nginx |

Aucun écart résolu, aucun écart nouveau de poids. Score **97 → 97**.

---

## Points positifs

- **Pas de traversée de chemin par HTTP** : `storage_path` n'est jamais pris de la requête ;
  le repli par nom de base reste dans le dossier d'upload.
- **PDF.js récent et sans chemin `eval`** ; rendu canvas seul, worker du même origine.
- **Cache de preview borné** en octets, verrouillé, clé incluant taille et `mtime`.
- **Paramètres de preview typés** : `format` en `Literal`, `dpi` et `page` bornés.
- **Montée de schéma #391** sans aucune interpolation d'entrée.
- **Erreurs HTTP centralisées** (`api/errors.py`) : les routes ne capturent plus
  `Exception` mais seulement `AnalysisEditError`, ce qui évite de convertir une erreur interne
  en 400 avec son message.

---

## Verdict partiel : GO

Score **97/100**, **0 CRIT**, **1 MAJ**, **8 MIN**, **8 INFO** — inchangé par rapport au
2026-11-13. Conditions :

1. 8.5.1 reste conforme **sous réserve du scan Trivy du Release Gate**, qui n'a pas tourné
   sur cet arbre ; s'il échoue : 92/100, 1 CRIT → NO-GO.
2. #378 doit être soldé (ou re-daté avec justification) avant le 2026-12-31.
3. Recommandé avant publication : `TrustedHostMiddleware` (lève le seul MAJ), bornes
   `max_length` de l'éditeur, `npm audit fix`.
