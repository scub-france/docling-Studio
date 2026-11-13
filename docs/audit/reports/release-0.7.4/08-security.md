# Rapport d'audit : Sécurité

**Release** : 0.7.4 (branche fix/0.7.4-editor-followups @ eade7fa)
**Date** : 2026-11-13
**Auditeur** : claude-code
**Baseline** : `release-0.7.3-reaudit/08-security.md` (97/100, GO, 0 CRIT, 2 MAJ, 6 MIN, 4 INFO) et `release-0.7.3/08-security.md` (89/100)
**Delta examiné** : `git diff 1de1929..eade7fa` (97 fichiers, 26 commits). Surface nouvelle : 6 routes `/api/documents/{id}/analysis-editor|analysis-edits*` (dont 4 en écriture), paramètre `edited` de l'export, 4 tables SQLite et une montée de schéma au boot (#391).

Méthode : lecture statique uniquement. **Ni Trivy, ni `npm audit`, ni `pip-audit` n'ont été
lancés** (consigne : machine occupée) ; le Release Gate de cette branche n'a pas été lu.
L'item 8.5.1 est donc évalué sur les pins (`pyproject.toml`, `uv.lock`,
`package-lock.json`) et sur `.trivyignore.yaml`, et doit être confirmé par le gate.
Une lecture `gh` (issues #361, #378) a été faite pour le suivi du risque Pillow.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 97 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 8 |
| Écarts INFO | 7 |

Détail du calcul : poids total = 36. Seul 8.5.2 (poids 1) est non conforme.
`35 / 36 * 100 = 97,2` → **97**. Réserve : 8.5.1 (poids 3) suppose le scan Trivy du gate
vert ; s'il échouait, le score tomberait à 89 avec 1 CRIT (NO-GO).

| # | Item | Poids | Statut | Preuve (arbre `eade7fa`) |
|---|------|-------|--------|--------------------------|
| 8.1.1 | Aucun secret en dur | 3 | Oui | scan des fichiers modifiés (`password=`, `secret=`, `api_key=`, `token=`, `sk-`, `ghp_`, `hf_`, `AKIA`) : seuls les placeholders connus (`.env.example:24,78`, défaut `changeme` signalé au boot `bootstrap/factories.py:160`) |
| 8.1.2 | `.env` dans `.gitignore` | 3 | Oui | `.gitignore:26-28` |
| 8.1.3 | Secrets Docker par env | 2 | Oui | ARG inchangés (`Dockerfile:13,24,86,90`, `document-parser/Dockerfile:59,63`) ; nouveau `ANALYSIS_EDITOR_ENABLED` en `environment:` (`docker-compose.yml:197`) |
| 8.2.1 | Entrées validées par Pydantic | 3 | Oui | union discriminée `AnalysisEditCommandRequest` (`api/schemas.py:147-191`), `AnalysisEditRequest` (`:194-196`), `AnalysisEditHistoryActionRequest` (`:217-219`) ; `level` borné en domaine (`infra/docling_editor.py:176-177`). Pas de bornes de taille : [MIN] |
| 8.2.2 | `MAX_FILE_SIZE_MB` appliqué à l'upload | 3 | Oui | `api/documents.py:76-87` (413) ; inchangé |
| 8.2.3 | Types de fichiers validés | 2 | Oui | `services/document_service.py` inchangé (magic `%PDF`, extension forcée) |
| 8.3.1 | SQL en paramètres liés | 3 | Oui | nouveaux repos 100 % `?` (`persistence/analysis_edit_repo.py:100-212`, `persistence/document_analysis_repo.py:12-82`, `persistence/analysis_repo.py:202-209`) ; seules f-strings SQL nouvelles : DDL sur des constantes du module (`persistence/database.py:292-295` → `:321,324`), INFO |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | Oui | grep `eval(`, `exec(`, `os.system(`, `subprocess.`, `shell=True`, `pickle.load` vide hors tests |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | Oui | seul `v-html` : `frontend/src/shared/ui/MarkdownViewer.vue:3,24` ; l'éditeur affiche le Markdown édité en interpolation échappée (`features/analysis-editor/ui/AnalysisEditor.vue:278-279`) ; `contentHtml` n'est rendu nulle part |
| 8.4.1 | CORS explicite | 3 | Oui | `document-parser/main.py:90-96` ; `infra/settings.py:76,246` |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | Oui | middleware global `main.py:97-102`, qui couvre aussi le routeur de l'éditeur (`main.py:107`) ; exclusion `infra/rate_limiter.py:59,68` |
| 8.4.3 | Nginx sans directory listing | 2 | Oui | `nginx.conf.template:14`, `frontend/nginx.conf.template:14` (`try_files`), pas d'`autoindex` ; templates inchangés |
| 8.5.1 | Pas de CVE critique connue | 3 | Oui (risque accepté, **à confirmer par le gate**) | dépendances d'exécution inchangées : `pillow>=10.0.0,<11.0.0` (`document-parser/pyproject.toml:14`) → 10.4.0 (`uv.lock:2452-2453`) ; seuls ajouts du lock : `fpdf2` 2.8.9 et `fonttools` 4.67.0, groupe `ci` (`pyproject.toml:35-37`) **non installé** dans les images (`uv sync --frozen --no-dev [--group local]`, `Dockerfile:42,103-105`, `document-parser/Dockerfile:24,77-79`) ; npm : ajouts **dev uniquement** (`jsdom`, `playwright-core`, `axe-core`, `@vue/test-utils`, `frontend/package.json:36-43`), aucune version de prod modifiée dans `package-lock.json` ; suppressions `.trivyignore.yaml:7-20` (libxml2) et `:21-56` (Pillow ×4), toutes `expired_at: 2026-12-31`, inchangées |
| 8.5.2 | Versions épinglées | 1 | **Non** | `document-parser/pyproject.toml:45-46` (`torch`, `torchvision` sans version) |

### Routes de l'éditeur : contrôle ciblé

| Contrôle | Résultat | Preuve |
|----------|----------|--------|
| Validation d'entrée | Typée, **non bornée** | `api/schemas.py:150` (`text: str`), `:155-156` (`element_ids`, `separator`), `:180`, `:195` (`commands: list[...]`) sans `max_length` ; voir [MIN] |
| Plafond de taille du corps | Aucun côté app ; nginx 200 Mo | `Dockerfile:61`, `docker-compose.yml:210` |
| Parité d'autorisation | Identique aux autres routes (aucune auth, documentée `SECURITY.md:51`) ; **contrôle d'appartenance présent** | l'analyse demandée doit appartenir au document (`services/analysis_edit_service.py:278-281`), sinon refus ; export `edited` : même contrôle (`services/export_service.py:127-131` → `:110-118`) ; les commandes ne peuvent viser que des éléments du document chargé (`infra/docling_editor.py:82-87,101-105`) |
| Application du feature-flag | Routes de l'éditeur : **oui** (404) ; export `edited=true` : **oui** ; lectures par défaut : non, voir INFO | `api/deps.py:46-49` (dépendance commune aux 6 routes, `api/analysis_edits.py:123,136,151,167,188,211`) ; `api/documents.py:147-148` ; front en échec fermé `features/feature-flags/store.ts:135,186` |
| SQL | Paramètres liés partout | `persistence/analysis_edit_repo.py:100-212` |
| Concurrence / intégrité | Transaction `BEGIN IMMEDIATE`, séquence attendue revérifiée, chaîne de hash | `persistence/analysis_edit_repo.py:149-207` ; `UNIQUE(analysis_id, sequence)` `persistence/database.py:254` |
| Désérialisation | JSON uniquement, revalidé par le modèle Docling | `infra/docling_editor.py:43-46,53-61` |
| Images (Pillow) | Exports en mode placeholder, aucun décodage | `infra/docling_projector.py:73-74` (défauts de `export_to_markdown` / `export_to_html`) ; aucun `pil_image` / `get_image` / `Image.open` hors `infra/page_raster.py:44` |

---

## Écarts constatés

### [MAJ] `/api/*` sans validation du `Host` : DNS rebinding possible contre une instance locale — inchangé, surface élargie

- **Localisation** : `document-parser/main.py:90-102` (`CORSMiddleware` et
  `RateLimiterMiddleware` seulement ; aucun `TrustedHostMiddleware` dans
  `document-parser/`) ; `frontend/nginx.conf.template:1-24`, `nginx.conf.template:1-24`
  (pas de `server_name` ni de `default_server` de rejet). Nouvelles cibles :
  `api/analysis_edits.py:132,162,184,208` (POST preview, PATCH historique, POST save,
  POST rebuild).
- **Constat** : analyse 0.7.3 reprise, fichiers inchangés. Une page web qui fait pointer
  son domaine vers 127.0.0.1:3000 émet des requêtes same-origin vers `/api/*`. En 0.7.4,
  elle peut en plus **réécrire durablement le contenu des analyses** (commandes persistées,
  rejouées pour tous les usages en aval : export, rechunk, workspace) et, faute de borne
  de taille, saturer l'event loop (voir [MIN] ci-dessous). Exploitation **PLAUSIBLE**,
  dépendante du navigateur. `/mcp` reste protégé (421).
- **Règle violée** : 8.4 (réseau), écart additionnel sans impact de score.
- **Remédiation** : `TrustedHostMiddleware` (défaut `localhost`, `127.0.0.1`, `[::1]`,
  configurable, aligné sur `MCP_ALLOWED_HOSTS`), ou `server_name` explicite + serveur par
  défaut qui répond 421 dans nginx. Effort S.

### [MIN] Routes de l'éditeur : aucune borne de taille sur les commandes ; rejeu synchrone et persistant (nouveau)

- **Localisation** : `document-parser/api/schemas.py:150,155-156,180,195` (aucun
  `max_length`) ; rejeu sur l'event loop `services/analysis_edit_service.py:131,172,253,298-311` ;
  persistance `persistence/analysis_edit_repo.py:166-194` ; coût quadratique
  `infra/docling_editor.py:157-163` (`_delete_elements` : `_is_descendant` pour chaque paire
  d'ids) et `:89-99` (`_in_document_order` réénumère tout le document pour chaque fusion) ;
  plafond nginx seul `Dockerfile:61` (200 Mo).
- **Constat** : un seul POST de quelques Mo (milliers de `deleteElements` ou un
  `elementIds` de plusieurs milliers d'entrées) est entièrement rejoué de façon synchrone
  sur la boucle, ce qui gèle toutes les requêtes, `/mcp` et `/api/health` compris. Si la
  requête est un *save*, les commandes sont **persistées** et rejouées à chaque
  chargement suivant de l'analyse dont le cache n'est pas valide (`rebuild`, changement de
  flux). Le rate limiter (par requête) ne borne pas le coût d'une requête. Déni de
  service **PLAUSIBLE**, non démontré (pas d'exécution). Mêmes acteurs que pour le reste
  de l'API sans authentification : MIN.
- **Règle violée** : 8.2.1 / 8.2.2 dans leur esprit (items conformes au sens strict).
- **Remédiation** : `Field(max_length=...)` sur `commands` (ex. 500), `element_ids`
  (ex. 1 000), `text` (ex. 100 000), `separator` (ex. 16) ; plafond `Content-Length` sur
  le routeur de l'éditeur ; projection hors loop (audit 12). Effort S.

### [MIN] MCP actif par défaut, port publié sur toutes les interfaces — **rétrogradé de MAJ**

- **Localisation** : défaut `document-parser/infra/settings.py:97` (`mcp_enabled = True`),
  `docker-compose.yml:208` (`"3000:80"`). Libellés corrigés : `README.md:31`
  (« no authentication: keep port 3000 private »), `frontend/src/shared/i18n.ts:416,1202`
  (« bloque le DNS rebinding, pas le réseau »), commit `6cb61d3`.
- **Constat** : les deux corrections demandées au re-audit 0.7.3 sont faites : le README et
  le panneau Settings ne promettent plus « localhost only ». Comme annoncé dans ce rapport,
  l'écart descend en [MIN] : il ne reste que le défaut non sécurisé (MCP actif, port publié
  sur 0.0.0.0), même posture que `/api`, documentée.
- **Règle violée** : 8.4, hors pondération.
- **Remédiation** : `127.0.0.1:3000:80` par défaut dans compose et
  `-p 127.0.0.1:3000:3000` dans le README ; `MCP_TOKEN` en 0.8.0.

### [MIN] Risque accepté : 4 CVE CRITICAL de Pillow 10.4.0 et libxml2, suppressions jusqu'au 2026-12-31 — inchangé, désormais suivi

- **Localisation** : `.trivyignore.yaml:7-20` (libxml2), `:21-56` (Pillow ×4) ;
  `document-parser/pyproject.toml:14` ; `document-parser/uv.lock:2452-2453`.
- **Constat** : pins et suppressions inchangés depuis 0.7.3 ; la note nomme désormais le
  plafond `<11` propre à Studio (`.trivyignore.yaml:22`, commit `d81deb0`). Le manque
  « aucune issue » est **résolu** : #378 (milestone 0.7.4, P1) porte l'expiration et la
  montée Pillow 13. #361 (montée Docling) reste sans milestone. La justification tient
  pour le code neuf : le projecteur de l'éditeur exporte en mode placeholder
  (`infra/docling_projector.py:73-74`) et `DoclingDocument.model_validate_json`
  (`infra/docling_editor.py:44,58`) ne décode pas les images. Il reste **48 jours** avant
  l'expiration : un gate lancé après le 2026-12-31 échouera sur 8.5.1 (CRIT).
- **Règle violée** : 8.5.1 (défense en profondeur ; item conforme par acceptation).
- **Remédiation** : traiter #378 avant le 2026-12-31 (Docling ≥ seuils + `pillow>=13,<14`,
  ou re-justification datée).

### [MIN] Écritures de config MCP sans authentification — inchangé

- **Localisation** : `document-parser/api/config.py:80-98` ;
  `document-parser/domain/mcp_config.py:94-104`.
- **Remédiation** : `MCP_STUDIO_BASE_URL` restart-only ou liste d'hôtes autorisés ;
  journaliser chaque changement.

### [MIN] Import d'analyse Docling sans plafond de taille — inchangé

- **Localisation** : `document-parser/api/analyses.py:73-87` ;
  `document-parser/api/schemas.py:364` (`document: dict`) ; plafond nginx seul
  `docker-compose.yml:210`.
- **Remédiation** : Content-Length et lecture bornée alignés sur `MAX_FILE_SIZE_MB`.

### [MIN] Rate limiter « par IP » en réalité global derrière nginx — inchangé

- **Localisation** : `document-parser/infra/rate_limiter.py:71` ; `Dockerfile:65`.
- **Remédiation** : `--proxy-headers --forwarded-allow-ips`, ou `limit_req` nginx.

### [MIN] `npm audit` (production) : 7 HIGH, 0 CRITICAL au 2026-11-02 — non re-mesuré

- **Localisation** : `frontend/package.json`, `frontend/package-lock.json`.
- **Constat** : `npm audit` non lancé (consigne). Le diff du lock n'ajoute que des paquets
  de développement et ne modifie aucune version existante : l'état de production est
  vraisemblablement celui de 0.7.3.
- **Remédiation** : `npm audit fix` ; relire le job « Dependency audit » du gate.

### [MIN] Dépendances backend sans version : torch / torchvision (item 8.5.2) — inchangé

- **Localisation** : `document-parser/pyproject.toml:45-46`.
- **Constat** : atténué par `uv.lock` en `--frozen`, groupe `local`.
- **Règle violée** : 8.5.2 (poids 1).
- **Remédiation** : `torch>=2,<3`, `torchvision<1`, ou exemption documentée.

### [INFO] Flag désactivé : les lectures par défaut servent quand même le résultat édité

- **Localisation** : `document-parser/services/export_service.py:78-79,96-97,121-125`
  (export md/json sans `analysisId`), `services/chunk_service.py:376-381` (rechunk),
  `:712-716` (arbre sans `analysisId`) ; le service est câblé sans condition
  (`bootstrap/builder.py:124-134,145,172,176`) ; doc `docs/configuration.md:26`
  (« keeping read-only analysis inspection available »).
- **Constat** : avec `ANALYSIS_EDITOR_ENABLED=false`, les routes de l'éditeur répondent
  404, mais les commandes déjà sauvegardées restent appliquées à l'export par défaut, au
  rechunk et à l'arbre. C'est cohérent avec le modèle « l'analyse active inclut ses
  éditions » (`domain/models.py` docstring de `DocumentVersion`), mais le flag n'est pas un
  interrupteur de retour arrière. Pas de fuite (ce sont les données de l'utilisateur).
- **Suggestion** : le dire dans `docs/configuration.md`, ou ignorer les éditions quand le
  flag est coupé.

### [INFO] Messages d'erreur 400 qui recopient la validation Pydantic interne

- **Localisation** : `document-parser/infra/docling_editor.py:46,61` ; renvoyés tels
  quels en `detail` par `api/analysis_edits.py:115-116`.
- **Constat** : divulgation de structure interne mineure, sans secret.

### [INFO] DDL de montée de schéma en f-string sur des constantes

- **Localisation** : `document-parser/persistence/database.py:292-295` (`_ADDED_COLUMNS`),
  `:321,324` (`PRAGMA table_info({table})`, `ALTER TABLE ... ADD COLUMN`).
- **Constat** : pas d'entrée utilisateur (tuple littéral du module). Conforme à 8.3.1 ;
  garder ce tuple littéral.

### [INFO] Constats reconduits sans changement

| Constat | Localisation vérifiée |
|---------|-----------------------|
| SSRF Ollama : résidus (TOCTOU, LAN autorisé) | `document-parser/infra/llm/ollama_probe.py` (inchangé) ; `SECURITY.md:48` |
| API sans authentification (documenté) | `SECURITY.md:51` ; `main.py:90-102` |
| Pas de garde `CORS_ORIGINS="*"` avec credentials | `infra/settings.py:246` ; `main.py:92-93` |
| nginx maître en root, pas de CSP | `frontend/Dockerfile` ; `Dockerfile:65` ; `frontend/nginx.conf.template:7-11` |

---

## Statut des écarts du re-audit 0.7.3

| Écart 0.7.3 | Statut à `eade7fa` | Preuve |
|-------------|--------------------|--------|
| [MAJ] MCP présenté « localhost only » ; défaut actif | **Partiellement corrigé → [MIN]** (libellés exacts ; défaut inchangé) | `README.md:31`, `i18n.ts:416,1202` (commit `6cb61d3`) ; `infra/settings.py:97`, `docker-compose.yml:208` |
| [MAJ] `/api/*` sans validation du `Host` | **Toujours ouvert**, surface élargie par l'éditeur | `main.py:90-102` |
| [MIN] Pillow / libxml2 risque accepté | **Ouvert, désormais suivi** (#378, milestone 0.7.4) ; pins et dates inchangés | `.trivyignore.yaml:7-56` ; `pyproject.toml:14` ; `uv.lock:2452-2453` |
| [MIN] Écritures de config MCP sans auth | Inchangé | `api/config.py:80-98` |
| [MIN] Import JSON sans plafond | Inchangé | `api/analyses.py:73-87` |
| [MIN] Rate limiter global | Inchangé | `infra/rate_limiter.py:71` |
| [MIN] `npm audit` 7 HIGH | Non re-mesuré ; prod inchangée | `frontend/package-lock.json` |
| [MIN] torch / torchvision (8.5.2) | Inchangé | `pyproject.toml:45-46` |
| 4 [INFO] | Inchangés | ci-dessus |
| — | **Nouveau [MIN]** : routes de l'éditeur non bornées | `api/schemas.py:150,155-156,180,195` |
| — | **Nouveaux [INFO]** : flag et lectures par défaut, détail d'erreur, DDL f-string | ci-dessus |

---

## Points positifs

- **Contrôle d'appartenance systématique** : une analyse d'un autre document est refusée
  partout dans l'éditeur et l'export édité, et un trigger SQLite interdit de sélectionner
  comme active une analyse d'un autre document (`persistence/database.py:96-114`).
- **Intégrité du flux d'édition** : écriture sous `BEGIN IMMEDIATE`, séquence attendue
  revérifiée dans la transaction, hash chaîné et unicité `(analysis_id, command_hash)`.
- **Validation stricte des commandes** : union discriminée Pydantic côté HTTP, puis
  revalidation complète du document Docling après application (`validate_tree`,
  `validate_document`, aller-retour JSON) avant toute persistance.
- **Flag appliqué au bon endroit** : une seule dépendance FastAPI garde les six routes, et
  le front échoue fermé face à un backend qui n'annonce pas l'éditeur.
- **Aucune nouvelle dépendance d'exécution** : les ajouts Python et npm sont limités aux
  groupes CI et dev, hors images.
- **Suivi du risque Pillow** enfin tracé (#378, P1, milestone 0.7.4).

---

## Verdict partiel : GO

Score **97/100** (= 0.7.3), **0 CRIT**, **1 MAJ** (`Host` non validé sur `/api/*`, à
périmètre élargi par l'éditeur), **8 MIN**, **7 INFO**. Le MAJ MCP de 0.7.3 descend en MIN.

Conditions de lecture :
1. 8.5.1 reste conforme **sous réserve du scan Trivy du gate** sur cette branche (non lu
   ici) ; s'il échoue : 89/100, 1 CRIT → NO-GO.
2. #378 doit être soldé avant le 2026-12-31, faute de quoi le premier gate de 2027 passe
   8.5.1 en CRIT.
3. Recommandé avant publication : bornes `max_length` sur `AnalysisEditRequest` (S), et
   `TrustedHostMiddleware` (S) qui lèverait le seul MAJ.
