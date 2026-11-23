# Rapport d'audit : Sécurité

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `efc0bc5`, arbre de travail
**Nature** : Audit de validation après la seconde remédiation ; base : contrôle du 2026-11-18
(`release-0.7.4-control/08-security.md` sur `a12b744` : 97/100, 13/14, 0 CRIT, 1 MAJ, 9 MIN, 9 INFO)

Code non exécuté : aucune suite n'a tourné sur ce commit.

Méthode : lecture statique de l'arbre de travail ; `git log` / `git diff b5f8c7f..efc0bc5` et
`a12b744..efc0bc5` ; `git show b5f8c7f:...` pour comparer le code déplacé ; lecture des sources
installées de Starlette (`.venv`, version 1.0.0 en local, 1.6.0 dans `uv.lock`) pour `Headers`
et `redirect_slashes` ; `gh issue view 378` (lecture seule). Rien n'a été lancé : ni pytest, ni
ruff, ni `npm audit`, ni Docker, ni uvicorn ; l'application n'a pas été importée. Les deux
nouveaux middlewares n'ont donc **jamais tourné** au moment de cet audit, pas même leurs tests
(`tests/test_api_host_guard.py`, `tests/test_body_limit.py`).

Convention : **[lu]** = confirmé en lisant le code de l'arbre de travail ; **[hyp.]** =
hypothèse ou comportement d'une dépendance non vérifié par exécution.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 97 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 8 |
| Écarts INFO | 11 |

Calcul : poids total 36 ; seul 8.5.2 (poids 1) est non conforme. `35 / 36 × 100 = 97,2` → **97**.
Même lecture que la base : 8.5.1 est compté conforme **sous réserve du scan Trivy du Release
Gate**, qui n'a pas tourné sur cet arbre. Le gate scanne désormais aussi l'image `local`
(torch, Docling, `release-gate.yml:386-419`) : la réserve pèse plus qu'avant. S'il échoue :
`33 / 36` = **92**, 1 CRIT → NO-GO.

Le MAJ (DNS rebinding) et les MIN hors grille ne changent pas le score : ils ne relèvent d'aucun
item pondéré de la fiche.

### Détail par item

| # | Item | Poids | Conforme | Justification (arbre `efc0bc5`) |
|---|------|-------|----------|---------------------------------|
| 8.1.1 | Aucun secret en dur | 3 | oui | grep des lignes ajoutées par `a12b744..efc0bc5` (`password=`, `secret=`, `api_key=`, `token=`, `sk-`, `ghp_`, `hf_`, `AKIA`, `PRIVATE KEY`) : seules occurrences = le rapport d'audit précédent et des variables `secret = tmp_path / "secret.txt"` dans des tests ; aucun binaire modifié (`git diff --numstat`) |
| 8.1.2 | `.env` dans `.gitignore` | 3 | oui | `.gitignore:26-28` inchangé |
| 8.1.3 | Secrets Docker par env | 2 | oui | Dockerfiles et `pyproject.toml` / `uv.lock` / manifestes npm : diff vide ; compose ne gagne que `MAX_IMPORT_SIZE_MB` et `API_ALLOWED_HOSTS` (`docker-compose.yml:174-176`), aucun secret ; `frontend/.dockerignore` exclut maintenant `.env`, `.env.*`, `.claude/` |
| 8.2.1 | Entrées validées par Pydantic | 3 | oui | schémas de l'éditeur bornés (`api/schemas.py:152-219`) ; import toujours `document: dict` (`:513-517`) mais plafonné en octets par le middleware |
| 8.2.2 | `MAX_FILE_SIZE_MB` appliqué | 3 | oui | `services/document_service.py:84-97` inchangé dans sa logique ; écriture déplacée dans `infra/document_file_store.py:24-31` |
| 8.2.3 | Types de fichiers validés | 2 | oui | magic `%PDF` (`document_service.py:96`), nom `uuid4` + `.pdf` (`:100`), limite de pages avec `discard` (`:108-116`) : même ordre qu'à `b5f8c7f` |
| 8.3.1 | SQL en paramètres liés | 3 | oui | `persistence/document_analysis_repo.py`, `chunk_repo.py` (`replace_for_document`), `analysis_repo.py:83-96` (`find_summaries_by_document`) : constantes SQL et `?` ; les seules f-strings injectent des listes de `?` (`document_analysis_repo.py:93-96`) ou des fragments constants (`chunk_repo.py:197-202`) |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | oui | aucune ligne ajoutée avec `eval(`, `exec(`, `os.system(`, `subprocess`, `shell=True` (la seule occurrence de « subprocess » est un commentaire) |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | oui | seul `v-html` : `frontend/src/shared/ui/MarkdownViewer.vue:3` (assaini) ; aucun ajout de puits HTML |
| 8.4.1 | CORS explicite | 3 | oui | `main.py:102-108` inchangé sur le fond |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | oui | `main.py:109-114` ; `infra/rate_limiter.py:59` |
| 8.4.3 | Nginx sans directory listing | 2 | oui | `nginx.conf.template`, `frontend/nginx.conf.template` : diff vide depuis le contrôle |
| 8.5.1 | Pas de CVE critique connue | 3 | oui, **sous réserve du gate** | `uv.lock` et `package-lock.json` inchangés ; `.trivyignore.yaml` inchangé (5 suppressions au 2026-12-31) ; `npm audit` non relancé (outillage Node interdit sur cette machine) ; images non scannées |
| 8.5.2 | Versions épinglées | 1 | **non** | `document-parser/pyproject.toml:45-46` (`torch`, `torchvision` sans version) |

---

## Écarts constatés

### [MAJ] `/api/*` sans validation du `Host` sur une installation par défaut — réduit, pas levé

- **Localisation** : `document-parser/infra/settings.py:111` (`api_allowed_hosts` vide par
  défaut), `:283-286` ; `document-parser/main.py:117-119` (le middleware n'est ajouté que si
  `is_host_check_on`) ; `docker-compose.yml:176` (`${API_ALLOWED_HOSTS:-}`).
- **Constat [lu]** : un contrôle existe désormais (`infra/host_guard.py`), correct à la lecture
  pour le scénario visé (voir la revue). Mais il est **inactif par défaut** : une installation
  `docker compose up` sans `.env` reste exposée exactement comme au contrôle du 2026-11-18. Le
  démarrage le dit dans les journaux (`host_guard.py:82-86`), la doc aussi.
- **Scénario [hyp.]** : inchangé pour une installation par défaut (page hostile, domaine
  rebindé sur 127.0.0.1, lecture des PDF par `/api/documents/{id}/export?format=pdf`,
  suppression, réécriture d'éditions).
- **Pourquoi MAJ et pas MIN** : la fiche juge l'état livré, pas l'état atteignable. Ce que
  l'utilisateur obtient sans rien régler n'a pas bougé. Ce qui a bougé : la protection existe, est
  documentée (`SECURITY.md:53-59`, `docs/configuration.md:132-147`, `.env.example:44-49`) et
  s'active d'une variable.
- **Règle violée** : 8.4 (réseau), hors pondération.
- **Remédiation** : valeur par défaut `API_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,[::1]:*` dans
  `docker-compose.yml` et `docker-compose.dev.yml` (installations de poste de travail), en
  laissant le défaut du code vide pour les déploiements derrière proxy ; ou défaut actif dans le
  code avec `*` documenté pour le retirer. Valeur recommandée par la doc :
  `API_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,[::1]:*`. Effort XS.

### [MIN] Routes de l'éditeur : bornées, mais la borne de 100 000 identifiants laisse un coût quadratique — réduit

- **Localisation** : `document-parser/api/schemas.py:152-219` (bornes) ;
  `infra/docling_editor.py:150-162` (`_delete_elements`), `:233-252` (`_gather_merge_run`).
- **Constat [lu]** : chaînes, listes et nombre de commandes sont bornés (`max_length` Pydantic,
  aucune regex). Mais `_delete_elements` dédoublonne par `any(existing is item for existing in
  items)` : O(k × d), k identifiants, d éléments distincts déjà retenus ; `_gather_merge_run`
  appelle `list(parent.children).index(...)` pour chaque élément fusionné : O(k × enfants).
  Les identifiants inconnus lèvent tout de suite (`_get`, `:110-114`), donc d est borné par la
  taille du document.
- **Scénario [hyp.]** : sur un document de 30 000 éléments, un `deleteElements` qui les nomme
  tous fait de l'ordre de 4,5·10⁸ comparaisons Python dans un thread
  (`services/analysis_edit_service.py:291,318`), et la commande enregistrée est rejouée à chaque
  projection. Coût réel non mesuré.
- **Autre limite [lu]** : les bornes s'appliquent après lecture et analyse du JSON entier. La
  taille d'une requête de l'éditeur n'est bornée que par nginx (`client_max_body_size
  ${NGINX_MAX_BODY_SIZE}`, 200M par défaut, `nginx.conf.template:42`) ; uvicorn exposé en direct
  (`document-parser/Dockerfile:38`, `0.0.0.0`) n'en a aucune. Le compose ne publie pas ce port
  (`docker-compose.yml:158-159`, `expose`).
- **Remédiation** : dédoublonner par `id(item)` dans un `set` ; calculer les index d'enfants une
  fois par parent ; ramener `MAX_ELEMENT_IDS` vers 10 000 ou au nombre d'éléments du document.

### [MIN] MCP actif par défaut, port publié sur toutes les interfaces — inchangé

- **Localisation** : `document-parser/infra/settings.py:100` ; `docker-compose.yml:210-211`
  (`"3000:80"`).

### [MIN] Écritures de configuration MCP sans authentification — inchangé

- **Localisation** : `document-parser/api/config.py:81-104` (PUT / DELETE `/api/config/mcp`) ;
  fichier non modifié. Le contrôle `Host` (s'il est activé) ferme la voie navigateur par
  rebinding, pas un client du réseau.

### [MIN] Rate limiter « par IP » en réalité global derrière nginx — inchangé

- **Localisation** : `document-parser/infra/rate_limiter.py:71` (`request.client.host`) ;
  `Dockerfile:65` (uvicorn sans `--proxy-headers`). Désormais documenté honnêtement
  (`docs/configuration.md:33`).

### [MIN] `npm audit` (production) : 7 HIGH, 0 CRITICAL — inchangé, non re-mesuré

- **Constat** : mesure du 2026-11-18 reprise ; `frontend/package.json` et `package-lock.json`
  inchangés depuis. `npm audit` n'a pas été relancé (règle machine) : un nouvel avis publié
  depuis hier ne serait pas vu.
- **Remédiation** : `npm audit fix`.

### [MIN] Dépendances backend sans version : torch / torchvision — inchangé (item 8.5.2)

- **Localisation** : `document-parser/pyproject.toml:45-46`.

### [MIN] Risque accepté Pillow / libxml2 jusqu'au 2026-12-31 — inchangé (J-42)

- **Localisation** : `.trivyignore.yaml:20,38,44,50,56` ; #378 **OPEN** au 2026-11-19.

### [MIN] Jeton CI en écriture : `ci.yml` corrigé, `release-gate.yml` pas — réduit

- **Constat [lu]** : `ci.yml:9-12` porte `permissions: contents: read` (`53e3633`) : la partie
  du constat qui visait les push `release/**` est levée. `release-gate.yml` n'a toujours pas de
  bloc `permissions` en tête (`:1-16`) ; seuls deux jobs en déclarent un (`:462`, `:750`). Les
  autres jobs (lint, tests, build, Trivy, UI) tournent sur `pull_request` vers `main` avec le
  jeton par défaut du dépôt (en écriture, réglage lu le 2026-11-18) et exécutent `npm ci`,
  `uv sync --group local --group reasoning` (`:141` environ), des builds Docker.
- **Remédiation** : `permissions: contents: read` en tête de `release-gate.yml`, élargi job par
  job là où il faut écrire.

### [INFO] Contrôle `Host` : des valeurs qu'aucun navigateur n'envoie passent pour du loopback

- **Localisation** : `document-parser/infra/host_guard.py:50-51` (`partition(":")`), `:44-49`
  (IPv6), `:59-61`.
- **Constat [lu]** : le nom est tout ce qui précède le premier `:`. `Host: localhost:80@evil.com`
  donne le nom `localhost` → accepté. `Host: [::1]evil` donne `[::1]` → accepté. Le port n'est
  jamais validé.
- **Portée** : nulle pour le DNS rebinding. Un navigateur envoie le nom de l'URL de la page
  (`attacker.example:3000`), ne met jamais d'identifiants dans `Host`, et le script de la page ne
  peut pas fixer `Host` (en-tête interdit). Seul un client hors navigateur peut envoyer ces
  valeurs, et lui n'a pas besoin de contourner quoi que ce soit (`SECURITY.md:59` le dit).
- **Remédiation (robustesse)** : refuser un `Host` dont le port n'est pas numérique ou qui
  contient `@`, `/`, un espace. Effort XS.

### [INFO] Contrôle `Host` : un journal WARNING par requête refusée, avant le rate limiter

- **Localisation** : `host_guard.py:111` ; `main.py:115-118` (le contrôle est le plus externe).
- **Constat [lu]** : `%r` neutralise les retours à la ligne (pas d'injection de journal), mais
  les refus ne sont pas comptés par le rate limiter, donc rien ne borne ce journal.
- **Remédiation** : niveau DEBUG, ou un WARNING agrégé par période.

### [INFO] Limite de corps : un `Content-Length` en chiffres non ASCII ferait un 500 — inatteignable avec les serveurs livrés [hyp.]

- **Localisation** : `document-parser/infra/body_limit.py:40`.
- **Constat [lu]** : Starlette décode les en-têtes en latin-1. `"²".isdigit()` vaut `True` mais
  `int("²")` lève `ValueError` ; même chose pour une chaîne de plus de 4 300 chiffres (limite
  `int` de Python 3.12). L'exception sort du middleware : 500.
- **[hyp.]** httptools (installé par `uvicorn[standard]`, `uv.lock`) et h11 refusent un
  `Content-Length` non numérique avant l'application, nginx aussi : le cas ne devrait jamais
  arriver. Non vérifié par exécution.
- **Remédiation** : `declared.isascii() and declared.isdigit()` (ou `try: int(...)`).

### [INFO] Import : le plafond égale celui de nginx, l'amplification mémoire demeure

- **Constat [lu]** : `MAX_IMPORT_SIZE_MB=200` donne `200 × 1024 × 1024` octets
  (`main.py:99`), soit exactement `client_max_body_size 200M`. Derrière le nginx livré, c'est
  nginx qui répond 413 (page HTML, sans `detail` JSON) ; le 413 du backend ne sert qu'en accès
  direct à uvicorn ou si `NGINX_MAX_BODY_SIZE` est relevé. Le middleware garde jusqu'à 200 MiB
  en mémoire (`body_limit.py:44-56`), puis FastAPI joint les morceaux et analyse le JSON en un
  `dict` (`schemas.py:517`) : plusieurs fois la taille du corps par requête **[hyp.]**.
- **Remédiation** : défaut plus bas (50 MB), ou mettre `NGINX_MAX_BODY_SIZE` au-dessus comme la
  doc le demande.

### [INFO] Doc : trois précisions, aucune surévaluation de la protection

- `docs/configuration.md:143`, `.env.example:47` : « `name:port` pour un port ». Derrière le
  nginx livré, `Host $host` retire le port (`nginx.conf.template:38`) : un motif `name:port`
  n'y correspond jamais et l'utilisateur légitime prend un 421. Le motif `name:*` marche ;
  la doc gagnerait à dire que `name:port` ne vaut qu'en accès direct.
- `docs/configuration.md:31-32`, `.env.example:40` : « gardez `NGINX_MAX_BODY_SIZE` au-dessus de
  `MAX_IMPORT_SIZE_MB` », alors que les deux défauts sont égaux (voir l'INFO précédent).
- `docs/configuration.md:146` : « Only `/api/*` is checked » est exact ; `/docs`, `/redoc`,
  `/openapi.json` (FastAPI) ne sont pas contrôlés, mais ne livrent que le schéma public.

### [INFO] Garde de suppression déplacée dans `infra/document_file_store.py` — identique, vérifié

- **Constat [lu]** : `delete` (`infra/document_file_store.py:36-51`) reprend mot pour mot le bloc
  de `b5f8c7f:services/document_service.py:194-206` : `realpath` du chemin et du dossier,
  `startswith(real_upload_dir + os.sep)`, refus journalisé hors du dossier. Seul appelant :
  `document_service.py:176` ; instance unique créée avec `settings.upload_dir`
  (`bootstrap/factories.py:222-224`). `discard` (`:33-34`) ne confine pas, comme avant
  (`os.unlink(file_path)`), et ne reçoit que le chemin que `save` vient de construire à partir
  d'un nom `uuid4` (`document_service.py:100,108-113`). `resolve` (`:56-65`) garde le repli
  `upload_dir / path.name`, qui ne peut pas sortir du dossier (`name` est un nom de base) ;
  `read_fingerprint` est un `stat`. Aucun de ces chemins n'est écrit par une route.
- **Journaux** : les chemins serveur apparaissent dans les journaux de suppression
  (`:45-51`), comme avant ; jamais dans une réponse.

### [INFO] Traduction des erreurs de preview / pages — vérifié, aucun chemin dans une réponse

- **Constat [lu]** : `services/preview_service.py:122-140` (`_translate_pdf_read_errors`) :
  `FileNotFoundError` → « PDF file not found on disk » ; `OSError` → « Failed to read PDF
  file » ; toute autre exception → message fixe (`failure`) ; `ServiceError` relancée telle
  quelle. `_render` remplace le `ValueError` de l'adaptateur (qui porte le chemin) par « Page N
  not found » (`:109-118`). Les routes ne renvoient que `str(ServiceError)`
  (`api/documents.py:160-196`, `api/errors.py:25-31`). Un `ValueError` d'octet nul dans
  `storage_path` tombe désormais dans le cas générique, message fixe : mieux qu'au contrôle.

### [INFO] Mots de passe de connexion des stores — vérifié, aucune exposition nouvelle

- **Constat [lu]** : `services/chunk_push_service.py` (déplacé depuis `chunk_service.py`) ne
  journalise que `docId`, slug, nombre de chunks et de tokens (`:151-157`). Le mot de passe
  n'est lu que dans `services/store_backend_resolver.py:128-131,143-151` et n'est jamais
  sérialisé (`api/stores.py:50-52`, `has_connection_password`). Le message
  `Cannot resolve backend for store {slug}: {exc}` renvoyé en 503 (`chunk_push_service.py:221-
  224`) est identique à `a12b744:services/chunk_service.py:536` : il recopie le message de
  l'exception du client OpenSearch / Neo4j ; aucun de ces clients ne reçoit le mot de passe
  dans l'URL **[hyp.]**, constat reconduit tel quel.

### [INFO] `frontend/.dockerignore` — résolu

- `.env`, `.env.*`, `.claude/` sont exclus (`frontend/.dockerignore`).

### [INFO] Mode dev : le proxy Vite réécrit `Host`

- **Constat [lu]** : `frontend/vite.config.js:26-30` (`changeOrigin: true` sur `/api`) : le
  backend voit `Host` = la cible du proxy, donc un nom loopback, toujours accepté. En dev, la
  protection contre le rebinding vient du contrôle d'hôte de Vite (`allowedHosts`, `:25`,
  Vite 6.4.1), pas du backend. Acceptable pour un serveur de développement.

### [INFO] Constats reconduits sans changement

| Constat | Localisation vérifiée |
|---------|-----------------------|
| SSRF Ollama : résidus (TOCTOU, LAN autorisé) | `infra/llm/ollama_probe.py` (diff vide) |
| API sans authentification (documenté) | `SECURITY.md:51` |
| Pas de garde `CORS_ORIGINS="*"` avec credentials | `infra/settings.py:212,257` ; `main.py:102-108` |
| nginx maître en root, pas de CSP | `Dockerfile:65` ; `nginx.conf.template:13-17` |
| Surface PDF.js / export : confinement par `realpath` seulement à la suppression | `infra/document_file_store.py:56-65` ; `services/export_service.py` |
| DDL de montée de schéma en f-string sur des constantes | `persistence/database.py` |
| Messages 400 qui recopient la validation Pydantic interne | `infra/docling_editor.py`, `infra/docling_importer.py`, `api/analyses.py:83-88` |
| Images de build `node:22-alpine` non épinglées par digest | `Dockerfile:11`, `frontend/Dockerfile:1` |

---

## Delta vs contrôle

| Écart du contrôle (`a12b744`) | Statut à `efc0bc5` |
|-------------------------------|--------------------|
| [MAJ] `Host` non validé sur `/api/*` | **Réduit** : contrôle livré et documenté, mais inactif par défaut → reste MAJ pour une installation par défaut |
| [MIN] Routes de l'éditeur non bornées | **Réduit** : bornées (`schemas.py:152-219`) ; résidu de coût quadratique à 100 000 identifiants |
| [MIN] Import JSON sans plafond | **Résolu** : `MAX_IMPORT_SIZE_MB` (défaut 200) ; résidu en INFO (égal au plafond nginx, amplification mémoire) |
| [MIN] MCP actif par défaut, 0.0.0.0 | Inchangé |
| [MIN] Écritures config MCP sans auth | Inchangé |
| [MIN] Rate limiter global | Inchangé (documenté) |
| [MIN] `npm audit` 7 HIGH | Inchangé, **non re-mesuré** (manifestes inchangés) |
| [MIN] torch / torchvision (8.5.2) | Inchangé |
| [MIN] Pillow / libxml2 risque accepté | Inchangé ; J-42 ; #378 OPEN |
| [MIN] Jeton CI en écriture | **Réduit** : `ci.yml` en lecture ; `release-gate.yml` toujours sans bloc de tête |
| [INFO] Traduction des erreurs | Re-vérifié après déplacement ; légère amélioration |
| [INFO] `frontend/.dockerignore` incomplet | **Résolu** |
| [INFO] nginx `/assets/`, gzip | Fichiers inchangés ; non repris |
| [INFO] Surface PDF.js, cache preview, verrou pdfium, DDL, messages Pydantic, flag éditeur, reconduits | Inchangés |
| — | **Nouveaux [INFO]** : `Host` non-navigateur accepté comme loopback ; journal des 421 non borné ; `Content-Length` non ASCII → 500 [hyp. inatteignable] ; plafond d'import égal à nginx ; trois précisions de doc ; proxy Vite |

Aucune régression trouvée. Aucun contournement du contrôle `Host` par un navigateur, aucun
contournement de la limite de corps sur la route visée. Score **97 → 97** ; MIN 9 → 8.

---

## Revue des nouveaux contrôles

Tout ce qui suit est **[lu]** sauf mention : le comportement des serveurs HTTP (httptools, h11,
nginx) est **[hyp.]**, faute d'exécution.

### Contrôle `Host` — `document-parser/infra/host_guard.py`

Configuration de référence pour les cas : `API_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,[::1]:*`
(valeur recommandée par la doc) sauf mention.

| Entrée | Ce que fait le code | Verdict |
|--------|---------------------|---------|
| `Host: attacker.example:3000` (rebinding, accès direct) | `split_host` → `attacker.example` ; pas loopback ; aucun motif ne correspond (`:62-67`) → 421 | Correct : le cas visé est fermé |
| Même requête via le nginx livré | nginx envoie `Host $host` = `attacker.example` (`nginx.conf.template:38`) → 421 | Correct |
| `Host: localhost.evil.com` | `partition(":")` → nom complet `localhost.evil.com` ; comparaison d'égalité stricte (`name in LOOPBACK_HOSTS`, `:60`), pas de préfixe ni de sous-chaîne → 421 | Correct |
| `Host: evil.com@localhost` | nom `evil.com@localhost` → 421 | Correct |
| `Host: localhost:80@evil.com` | nom `localhost` (avant le premier `:`) → accepté | Défaut de robustesse ; inatteignable par un navigateur (INFO) |
| `Host: [::1]:8000`, `[::1]` | `[::1]` (crochets gardés, `:44-49`) → accepté | Correct |
| `Host: [::1]evil` | nom `[::1]`, reste ignoré → accepté | Robustesse (INFO), non navigateur |
| `Host: [::1` (crochet manquant) | nom `[::1` → 421 | Correct (fermé) |
| `Host: [0:0:0:0:0:0:0:1]`, `127.0.0.2`, `0.0.0.0`, `2130706433` | pas dans la liste exacte → 421 | Correct (fermé ; rejette aussi des formes loopback légitimes) |
| `Host: localhost.` (point final) | `localhost.` ≠ `localhost` → 421 | Correct (fermé) |
| `Host: LOCALHOST:3000` | minuscules (`:43`, `:58`) → accepté | Correct |
| Motif en majuscules ou avec espaces | `strip().lower()` (`:63`) | Correct |
| `Host` absent (HTTP/1.0) | `Headers.get` → `None` → `False` (`:56-57`) → 421 | Correct (fermé) |
| `Host` vide | `""` → `False` → 421 | Correct |
| Deux en-têtes `Host` | `Headers.get` prend le premier (`starlette/datastructures.py:546`) ; nginx refuse un double `Host` (400) **[hyp.]** ; httptools ne le refuse peut-être pas **[hyp.]** | Sans portée : un navigateur n'en envoie qu'un |
| Octets non ASCII | décodage latin-1, jamais d'exception ; comparaison stricte → 421 | Correct |
| Motif `studio.lan:*`, `Host: studio.lan` (derrière nginx) | `name == pattern[:-2]` (`:66`) → accepté | Correct, comme documenté |
| Motif `studio.lan:3000`, `Host: studio.lan` (derrière nginx) | `full != pattern` → 421 | Fermé ; piège de configuration (INFO doc) |
| Motif `*` seul ou dans la liste | `is_host_check_on` → `False`, middleware non ajouté (`:71-74`, `main.py:117`) | Correct, documenté |
| Motif `:*` (mauvaise config) | accepterait un `Host: :80` (nom vide) | Sans portée navigateur |
| `/api/documents` | `startswith("/api/")` (`:104`) → contrôlé | Correct |
| `/api` (sans barre) | non contrôlé ; aucune route → 404 | Correct |
| `/API/documents` | non contrôlé ; routes sensibles à la casse → 404 | Correct |
| `/%61pi/documents` | uvicorn décode `scope["path"]` → `/api/documents` ; contrôle et routage lisent le même champ → contrôlé | Correct |
| `/api/../x`, `//api/x` | non normalisé ; `/api/../x` contrôlé ; `//api/x` ne correspond à aucune route | Correct |
| `root_path` | aucun déploiement ne le fixe (`rg root.path` vide) ; s'il l'était, `scope["path"]` porterait le préfixe et le contrôle sauterait **[hyp.]** | Sans objet aujourd'hui |
| `/mcp` | hors préfixe ; contrôlé par sa propre sécurité de transport (`bootstrap/mcp_mount.py`, renommage seul) | Correct |
| `/docs`, `/openapi.json` | non contrôlés | Schéma public seulement (INFO doc) |
| Scope `websocket` / `lifespan` | passés tels quels (`:104`) ; aucune route websocket (`rg websocket` vide hors `uv.lock`) | Correct |
| Réponse 421 | `PlainTextResponse("Invalid Host header", 421)` ; corps non lu, pas d'en-tête CORS | Correct ; même forme que `/mcp` |
| Ordre des middlewares | ajouté en dernier → le plus externe : Host → rate limiter → CORS → limite de corps → app (`main.py:92-118`) | Correct : un refus ne compte pas dans le rate limit et n'atteint aucune route |
| Préflight CORS d'un `Host` étranger | 421 sans en-tête CORS | Correct |
| `/api/health` depuis un healthcheck | `localhost` toujours accepté | Correct |
| Défaut (variable absente) | middleware non monté, journal « open to DNS rebinding » (`:82-86`) | **Le MAJ reste ouvert** pour une installation par défaut |

**Question « le loopback toujours accepté est-il lui-même le trou ? »** Non. Dans une attaque par
rebinding, le navigateur envoie le nom de la page (`attacker.example[:port]`), et le code compare
le nom entier à un ensemble fermé de trois chaînes (`:33`, `:60`) : ni préfixe, ni sous-chaîne,
ni résolution DNS. Accepter `localhost` ne donne rien à une page distante.

### Limite de corps — `document-parser/infra/body_limit.py`

| Entrée | Ce que fait le code | Verdict |
|--------|---------------------|---------|
| `Content-Length: 300000000` sur `/api/analyses/import` | `isdigit` puis `int` > max → 413 sans lire le corps (`:39-42`) | Correct |
| `Content-Length` ≤ max | comptage quand même pendant la lecture | Correct (défense si le corps dépasse) |
| `Content-Length: abc`, `-1`, `1e9` | `isdigit()` faux → comptage | Correct |
| `Content-Length: ²` ou > 4 300 chiffres | `isdigit()` vrai, `int()` lève → 500 | Défaut ; inatteignable derrière httptools / h11 / nginx **[hyp.]** (INFO) |
| Deux `Content-Length` | `Headers.get` prend le premier ; httptools / nginx refusent des valeurs divergentes **[hyp.]** | Sans portée |
| Corps chunked > max | additionne `len(body)` à chaque message ; dès `received > max`, 413 et `return` (`:46-54`) | Correct : arrêt au premier morceau qui dépasse, pas de lecture du reste |
| Mémoire pendant le comptage | les messages sont gardés dans un `deque` jusqu'à `max_bytes` (`:44-48`) | Borné à 200 MiB + un morceau ; FastAPI aurait lu autant |
| L'app reçoit-elle un corps tronqué ? | non : après le refus, `return` ; l'app n'est appelée que si tout le corps tient (`:55-63`) | Correct |
| `more_body` absent ou `False` | sortie de boucle, rejeu complet | Correct |
| `http.disconnect` en cours de lecture | ajouté au `deque` puis rejoué ; l'app voit la déconnexion | Correct |
| Après le rejeu | `replay` retombe sur `receive()` d'origine (`:58-61`) : l'attente de déconnexion d'une réponse en flux fonctionne | Correct |
| `/api/analyses/import/` | ne correspond pas ; Starlette répond 307 vers le chemin exact sans lire le corps (`routing.py:695-698`) ; le client renvoie sur le chemin limité | Correct |
| `/API/analyses/import` | ne correspond pas ; aucune route → 404 | Correct |
| Autres routes | non touchées (`:36-38`) | Correct, voulu |
| Upload | inchangé : 413 sur `file.size` dans la route, plus `MAX_FILE_SIZE_MB` dans le service ; le multipart est mis en tampon par Starlette avant (comme avant) | Inchangé |
| Sauvegarde de l'éditeur | aucune limite d'octets backend ; nginx 200M ; bornes Pydantic après analyse | Inchangé (voir MIN éditeur) |
| nginx | `client_max_body_size 200M` = `MAX_IMPORT_SIZE_MB=200` : nginx répond le premier | INFO |
| `MAX_IMPORT_SIZE_MB=0` | middleware non monté (`main.py:95`) | Correct, documenté |
| `MAX_IMPORT_SIZE_MB` négatif | refusé au démarrage (`settings.py:154-155`) | Correct |
| Ordre | le plus interne : le 413 passe par CORS et porte ses en-têtes | Correct, comme le commentaire `main.py:92-94` |

### Bornes des requêtes de l'éditeur — `document-parser/api/schemas.py:152-219`

| Entrée | Ce que fait le code | Verdict |
|--------|---------------------|---------|
| `text` de 1 000 001 caractères | `max_length` Pydantic → 422 | Correct |
| `elementIds` de 100 001 entrées | `Field(max_length=MAX_ELEMENT_IDS)` → 422 | Correct |
| Identifiant de 1 001 caractères | `ElementId` → 422 | Correct |
| 10 001 commandes | `max_length=MAX_EDIT_COMMANDS` → 422 | Correct |
| Validateur coûteux | aucune regex ni `pattern=` ajoutés ; seulement des longueurs | Pas de risque ReDoS |
| Mémoire par requête | bornée par le corps (nginx 200M), pas par les schémas : 10 000 × 1 000 000 caractères est permis par le schéma | Bornes utiles contre le travail, pas contre la mémoire |
| `deleteElements` de 100 000 identifiants valides distincts | dédoublonnage O(k²) (`docling_editor.py:159-162`) | MIN (coût CPU, [hyp.] sur la durée) |
| `level`, `expectedAppliedThroughSequence` | `int` sans borne | Sans portée sécurité (contrôle de domaine en aval) |
| Payloads d'historique en réponse | `extra="forbid"`, sans borne, voulu (une ligne stockée doit se relire) | Correct |

### Code déplacé

| Surface | Vérifié comment | Résultat |
|---------|-----------------|----------|
| Garde de suppression (`ac7ac17`) | comparaison ligne à ligne avec `b5f8c7f:services/document_service.py:184-206` | Identique (voir INFO) |
| Écriture d'upload, `discard`, `resolve`, empreinte | lecture de `infra/document_file_store.py:24-69`, appelants dans `document_service.py`, `preview_service.py` | Même logique ; aucun chemin venant du client |
| Traduction des erreurs preview / pages | lecture de `preview_service.py:79-140`, `api/documents.py:160-196`, `api/errors.py` | Aucun chemin dans une réponse |
| SQL déplacé (`4939413`) | grep des f-strings dans `persistence/` | Paramètres liés partout |
| `currentAnalysisId`, analyse par défaut de MCP / Ask | lecture de `DocumentResponse` (`schemas.py:120-123`) | Un identifiant d'analyse, rien de sensible ; pas d'authentification de toute façon |
| Push vers les stores (`8a60cee`) | grep `password`, journaux, messages d'erreur | Aucun mot de passe journalisé ni renvoyé |
| CI (`23e4c81`, `53e3633`) | lecture des en-têtes et blocs `permissions` | `ci.yml` en lecture ; `release-gate.yml` à compléter (MIN) |

**Non vérifié sans exécution** : que les deux middlewares se chargent et répondent comme lu
(aucun test lancé, application non importée) ; le refus par httptools / h11 / nginx des
`Content-Length` et `Host` malformés ; le coût réel d'un `deleteElements` de 100 000 éléments ;
l'empreinte mémoire d'un import de 200 MiB ; le scan Trivy des images `remote` et `local` ;
`npm audit` et `pip-audit` ; l'exploitabilité réelle du DNS rebinding sur une installation par
défaut.

---

## Points positifs

- **Contrôle `Host` juste sur le cas visé** : comparaison exacte du nom entier, minuscules,
  crochets IPv6, refus quand `Host` manque, middleware ASGI pur placé le plus à l'extérieur.
- **Limite de corps sans tampon inutile** : refus sur `Content-Length` avant toute lecture,
  comptage du chunked avec arrêt au premier dépassement, jamais de corps tronqué vers l'app.
- **Doc honnête** : `SECURITY.md:59` dit que ni `/mcp` ni `/api` ne font du contrôle d'accès ;
  le journal de démarrage dit quand `/api` est ouvert au rebinding.
- **Code déplacé sans perte** : garde de suppression identique, traduction d'erreurs plus sûre
  qu'avant.
- **CI** : `ci.yml` passe en jeton en lecture.

---

## Verdict partiel : GO conditionnel

Score **97/100**, **0 CRIT**, **1 MAJ**, **8 MIN**, **11 INFO** — score inchangé, un MIN résolu,
trois réduits. Conditions :

1. 8.5.1 conforme **sous réserve du scan Trivy du Release Gate** (images `remote` et `local`),
   qui n'a pas tourné sur cet arbre ; s'il échoue : 92/100, 1 CRIT → NO-GO.
2. Le code n'a jamais tourné : `tests/test_api_host_guard.py` et `tests/test_body_limit.py`
   doivent passer avant le tag.
3. #378 soldé (ou re-daté avec justification) avant le 2026-12-31.
4. Recommandé avant publication : `API_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,[::1]:*` par défaut
   dans les fichiers compose (lève le MAJ pour l'installation par défaut),
   `permissions: contents: read` en tête de `release-gate.yml`, `isascii()` dans la limite de
   corps, dédoublonnage par `set` dans `_delete_elements`.
