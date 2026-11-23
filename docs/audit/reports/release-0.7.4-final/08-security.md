# Rapport d'audit : Sécurité

**Release** : 0.7.4
**Date** : 2026-11-19
**Auditeur** : claude-code
**Arbre audité** : branche `fix/0.7.4-editor-followups` @ `a744f48`, arbre de travail
**Nature** : Contrôle final après le troisième cycle ; base : validation du 2026-11-19 sur `efc0bc5`
(`release-0.7.4-validation/08-security.md` : 97/100, 13/14, 0 CRIT, 1 MAJ, 8 MIN, 11 INFO)

Méthode : lecture statique de l'arbre de travail ; `git log` / `git diff efc0bc5..a744f48` ;
`gh issue view 378` (lecture seule). Rien n'a été lancé : ni pytest, ni ruff, ni `npm audit`, ni
Docker, ni uvicorn ; l'application n'a pas été importée. Les suites ont été lancées par le
mainteneur sur ce commit (backend : ruff propre, 1773 passés / 15 ignorés, dont
`tests/test_api_host_guard.py` et `tests/test_body_limit.py` ; frontend : 604 tests) ; je ne les
ai pas relancées et je reprends ce résultat tel quel.

Convention : **[lu]** = confirmé en lisant le code de l'arbre de travail ; **[hyp.]** =
hypothèse, ou comportement d'une dépendance (regex Python, Pydantic, serveurs HTTP) non vérifié
par exécution.

---

## Score de compliance

| Métrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 97 / 100 |
| Écarts CRITICAL | 0 |
| Écarts MAJOR | 1 |
| Écarts MINOR | 6 |
| Écarts INFO | 8 |

Calcul : poids total 36 ; seul 8.5.2 (poids 1) est non conforme. `35 / 36 × 100 = 97,2` → **97**.
Même lecture que la base : 8.5.1 est compté conforme **sous réserve du scan Trivy du Release
Gate** (images `remote` et `local`), qui n'a pas tourné sur cet arbre. S'il échoue : `33 / 36` =
**92**, 1 CRIT → NO-GO.

Le MAJ (DNS rebinding) et les MIN hors grille ne changent pas le score : ils ne relèvent d'aucun
item pondéré de la fiche.

### Détail par item

| # | Item | Poids | Conforme | Justification (arbre `a744f48`) |
|---|------|-------|----------|---------------------------------|
| 8.1.1 | Aucun secret en dur | 3 | oui | grep des lignes ajoutées par `efc0bc5..a744f48` hors `docs/audit` (`password=`, `secret=`, `api_key=`, `token=`, `sk-`, `ghp_`, `hf_`, `AKIA`, `PRIVATE KEY`) : aucune occurrence ; aucun binaire modifié (`git diff --numstat`) |
| 8.1.2 | `.env` dans `.gitignore` | 3 | oui | `.gitignore` : diff vide |
| 8.1.3 | Secrets Docker par env | 2 | oui | Dockerfiles, fichiers compose, `pyproject.toml`, `uv.lock`, manifestes npm : diff vide |
| 8.2.1 | Entrées validées par Pydantic | 3 | oui | requêtes de l'éditeur inchangées et bornées (`api/schemas.py:173-235`) ; modèles de payload stocké générés, toujours `extra="forbid"` (`:317-359`) |
| 8.2.2 | `MAX_FILE_SIZE_MB` appliqué | 3 | oui | `services/document_service.py` : seules 7 lignes retirées, sans rapport avec le contrôle de taille |
| 8.2.3 | Types de fichiers validés | 2 | oui | magic `%PDF`, nom `uuid4` + `.pdf` : inchangés |
| 8.3.1 | SQL en paramètres liés | 3 | oui | nouvelles requêtes de `persistence/analysis_repo.py:206-271` en `?` ; la seule f-string (`:256-269`) est la requête déplacée telle quelle, qui n'injecte qu'une liste de `?` ; `document_repo.py:74-81` n'injecte qu'un fragment constant |
| 8.3.2 | Pas de `eval/exec/os.system` | 3 | oui | aucune ligne ajoutée avec `eval(`, `exec(`, `os.system`, `subprocess`, `shell=True` |
| 8.3.3 | DOMPurify sur rendu HTML/MD | 3 | oui | seul `v-html` : `frontend/src/shared/ui/MarkdownViewer.vue:3` (assaini) ; la nouvelle bannière interpole (`EditorBanners.vue:5-8`) |
| 8.4.1 | CORS explicite | 3 | oui | `main.py:102-108` inchangé |
| 8.4.2 | Rate limiter actif sauf `/api/health` | 2 | oui | `main.py:109-114` inchangé |
| 8.4.3 | Nginx sans directory listing | 2 | oui | gabarits nginx : diff vide |
| 8.5.1 | Pas de CVE critique connue | 3 | oui, **sous réserve du gate** | `uv.lock`, `package-lock.json`, `.trivyignore.yaml` inchangés ; `npm audit` non relancé (règle machine) ; images non scannées |
| 8.5.2 | Versions épinglées | 1 | **non** | `document-parser/pyproject.toml:45-46` (`torch`, `torchvision` sans version) |

---

## Écarts constatés

### [MAJ] `/api/*` sans validation du `Host` sur une installation par défaut — inchangé

- **Localisation** : `document-parser/infra/settings.py:112` (`api_allowed_hosts` vide par
  défaut), `:284-287` ; `document-parser/main.py:117-119` (le middleware n'est monté que si
  `is_host_check_on`) ; `docker-compose.yml:176` et `docker-compose.dev.yml:148`
  (`${API_ALLOWED_HOSTS:-}`).
- **Constat [lu]** : le contrôle réécrit est correct à la lecture (voir la revue), mais toujours
  **inactif par défaut**. Une installation `docker compose up` sans `.env` reste exposée au DNS
  rebinding comme à la validation. Le journal de démarrage le dit
  (`host_guard.py:56-60`), la doc aussi (`SECURITY.md:58`, `docs/configuration.md:134`,
  `.env.example:45-49`).
- **Pourquoi MAJ, même lecture que la base** : la fiche juge l'état livré. Ce qu'obtient
  l'utilisateur qui ne règle rien n'a pas bougé.
- **Règle violée** : 8.4 (réseau), hors pondération.
- **Décision laissée au mainteneur** : soit (a) mettre `API_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]`
  par défaut dans les deux fichiers compose (le code garde un défaut vide pour les déploiements
  derrière proxy) — le MAJ est levé, mais un utilisateur qui ouvre Studio par un nom LAN ou une
  IP prend un 421 sur `/api` tant qu'il n'a pas ajouté ce nom ; soit (b) livrer tel quel et
  accepter le MAJ comme risque connu et documenté. Effort de (a) : XS.

### [MIN] MCP actif par défaut, port publié sur toutes les interfaces — inchangé

- **Localisation** : `document-parser/infra/settings.py:100` ; `docker-compose.yml:210-211`
  (`"3000:80"`).

### [MIN] Écritures de configuration MCP sans authentification — inchangé

- **Localisation** : `document-parser/api/config.py` (PUT / DELETE `/api/config/mcp`), fichier
  non modifié. Le contrôle `Host`, s'il est activé, ferme la voie navigateur, pas un client du
  réseau.

### [MIN] Rate limiter « par IP » en réalité global derrière nginx — inchangé

- **Localisation** : `document-parser/infra/rate_limiter.py:71` ; uvicorn sans
  `--proxy-headers`. Documenté (`docs/configuration.md:33`).

### [MIN] `npm audit` (production) : 7 HIGH, 0 CRITICAL — inchangé, non re-mesuré

- Manifestes npm inchangés depuis la mesure du 2026-11-18 ; `npm audit` non relancé (règle
  machine). Remédiation : `npm audit fix`.

### [MIN] Dépendances backend sans version : torch / torchvision — inchangé (item 8.5.2)

- **Localisation** : `document-parser/pyproject.toml:45-46`.

### [MIN] Risque accepté Pillow / libxml2 jusqu'au 2026-12-31 — inchangé (J-42)

- **Localisation** : `.trivyignore.yaml:20,38,44,50,56` ; #378 **OPEN** (lu le 2026-11-19,
  dernière mise à jour le 2026-11-04).

### [INFO] Garde `Host` : une entrée mal formée de la liste est ignorée sans le dire

- **Localisation** : `document-parser/infra/host_guard.py:75-76` (`names - {None}`), `:61`
  (journal de démarrage).
- **Constat [lu]** : `parse_host_name(entry, port_wildcard=True)` rend `None` pour une entrée
  hors motif (`http://studio.lan`, `*.example.com`, `studio.lan:abc`, `[fe80::1%eth0]`) ;
  l'entrée disparaît sans erreur ni journal. Le journal de démarrage, lui, recopie la liste brute
  (« accepts loopback and http://studio.lan »), ce qui est faux.
- **Portée** : aucune pour la sécurité. Le défaut est fermé : le nom mal écrit n'est pas accepté,
  l'utilisateur prend un 421.
- **Remédiation** : refuser l'entrée au démarrage (`Settings.validate`, comme
  `mcp_allowed_hosts`), ou journaliser les noms retenus plutôt que la liste brute. Effort XS.

### [INFO] Garde `Host` : tolérances sans portée navigateur

- **Constat [lu]** : `str.strip()` (`:39`) retire tout blanc Unicode, y compris `\x85`, `\xa0`,
  `\x1c`-`\x1f`, plus que les espaces permis par HTTP ; le port accepte `0` à `99999` et des zéros
  de tête ; des écritures équivalentes du loopback (`[0:0:0:0:0:0:0:1]`, `[::ffff:127.0.0.1]`,
  `127.0.0.2`) sont refusées. Rien de cela ne donne un nom accepté à partir d'un nom refusé : le
  nom extrait est toujours comparé par égalité à un ensemble fermé.
- **Remédiation** : aucune exigée.

### [INFO] Éditeur : coût résiduel des déplacements — réduit depuis le MIN de la base [hyp.]

- **Localisation** : `document-parser/infra/docling_editor.py:307,311,336-337`
  (`list(parent.children).index(...)` une fois par commande `moveElement`) ; le déplacement
  lui-même passe par `DoclingDocument._move_subtree`, dont le coût n'a pas été lu.
- **Constat [lu]** : les deux points quadratiques de la base sont corrigés (voir le delta). Il
  reste un coût linéaire en nombre d'enfants **par commande** : au pire 10 000 commandes × la
  taille d'un parent. C'est le coût normal d'une liste ordonnée, exécuté hors de la boucle
  d'événements (`services/analysis_edit_service.py:294,321`, `api/analysis_edits.py:62`).
- **Remédiation** : aucune exigée ; `MAX_EDIT_COMMANDS` plus bas si une mesure le justifie.

### [INFO] Import : plafond égal à celui de nginx, amplification mémoire — documenté

- **Constat [lu]** : défauts toujours égaux (`MAX_IMPORT_SIZE_MB=200`, `client_max_body_size
  200M`), mais la doc le dit désormais (`docs/configuration.md:32` : nginx répond le premier,
  relever les deux ensemble). L'amplification mémoire du `dict` analysé demeure **[hyp.]**.

### [INFO] Export du PDF : chemin stocké non confiné, repli confiné — vérifié, rien de nouveau

- **Localisation** : `document-parser/services/export_service.py:93-101` ;
  `infra/document_file_store.py:56-65`.
- **Constat [lu]** : `resolve` rend le chemin stocké s'il existe (comme avant, où l'export
  servait `doc.storage_path` directement), sinon `upload_dir.resolve() / path.name`. Le repli ne
  peut pas sortir du dossier : `path.name` est un nom de base, jamais `..` ni un séparateur. Le
  seul écrivain de `storage_path` est `document_service.py:180` (`file_store.save`, nom `uuid4`)
  ; aucune route n'écrit ce champ. La suppression, elle, confine par `realpath` +
  `startswith(real_upload_dir + os.sep)` (`:36-51`). Le changement n'élargit donc pas ce que
  l'export peut lire ; l'absence de confinement du chemin stocké est le constat reconduit de la
  base.
- **Seule nuance [lu]** : un fichier de même nom de base dans le dossier d'upload remplace un
  chemin stocké absent ; les noms sont des `uuid4`, donc propres à chaque document.

### [INFO] Doc : `/docs`, `/redoc`, `/openapi.json` hors du contrôle — reconduit

- `docs/configuration.md:145` dit « Only `/api/*` is checked », ce qui est exact ; ces routes ne
  livrent que le schéma public.

### [INFO] Mode dev : le proxy Vite réécrit `Host` — reconduit

- `frontend/vite.config.js` (`changeOrigin: true`) : en dev, la protection vient de
  `allowedHosts` de Vite. Acceptable.

### [INFO] Constats reconduits sans changement

| Constat | Localisation vérifiée |
|---------|-----------------------|
| SSRF Ollama : résidus (TOCTOU, LAN autorisé) | `infra/llm/ollama_probe.py` (4 lignes modifiées, logique de garde inchangée) |
| API sans authentification (documenté) | `SECURITY.md:51` |
| Pas de garde `CORS_ORIGINS="*"` avec credentials | `main.py:102-108` |
| nginx maître en root, pas de CSP | gabarits nginx inchangés |
| DDL de montée de schéma en f-string sur des constantes | `persistence/database.py` |
| Messages 400 qui recopient la validation Pydantic interne | `infra/docling_editor.py`, `infra/docling_importer.py` |
| Images de build `node:22-alpine` non épinglées par digest | Dockerfiles inchangés |
| Message 503 du push vers un store qui recopie l'exception du client | `services/chunk_push_service.py` (9 lignes modifiées, message inchangé) |

---

## Delta vs validation

| Écart de la validation (`efc0bc5`) | Statut à `a744f48` |
|------------------------------------|--------------------|
| [MAJ] `Host` non validé sur `/api/*` par défaut | **Inchangé** : contrôle réécrit et juste, toujours inactif par défaut |
| [MIN] Éditeur : coût quadratique (dédoublonnage, `.index()` par élément) | **Résolu** : `set` d'identités (`docling_editor.py:158-173`), index des enfants lus une fois (`:250-264`) ; résidu linéaire par commande en INFO |
| [MIN] MCP actif par défaut, 0.0.0.0 | Inchangé |
| [MIN] Écritures config MCP sans auth | Inchangé |
| [MIN] Rate limiter global | Inchangé (documenté) |
| [MIN] `npm audit` 7 HIGH | Inchangé, **non re-mesuré** |
| [MIN] torch / torchvision (8.5.2) | Inchangé |
| [MIN] Pillow / libxml2 risque accepté | Inchangé ; J-42 ; #378 OPEN |
| [MIN] Jeton CI en écriture (`release-gate.yml`) | **Résolu** : `permissions: contents: read` en tête (`release-gate.yml:12-15`) ; seuls `image-size` (`packages: read`, `:469-471`) et `release-summary` (`pull-requests: write`, `actions: read`, `:759-762`) élargissent ; un run annulé ne publie plus de verdict (`:747`) et tout résultat autre que `success` bloque (`:794-800`) |
| [INFO] `Host` non navigateur accepté comme loopback (`localhost:80@evil.com`, `[::1]evil`) | **Résolu** : `fullmatch` d'un motif strict, `@` et texte après `]` refusés (voir la revue) |
| [INFO] Journal WARNING par 421, non borné | **Résolu** : `logger.debug` (`host_guard.py:86-87`) |
| [INFO] `Content-Length` non ASCII → 500 | **Résolu** : `isascii() and isdigit()`, au plus 20 chiffres, sinon 400 JSON (`body_limit.py:40-45`) |
| [INFO] Plafond d'import égal à nginx | **Réduit** : documenté (`docs/configuration.md:32`) ; amplification mémoire inchangée |
| [INFO] Doc : `name:port` ne correspond jamais derrière nginx | **Résolu** : le port est ignoré dans le code et la doc le dit (`docs/configuration.md:142`) |
| [INFO] Doc : « gardez nginx au-dessus » alors que les défauts sont égaux | **Résolu** : `docs/configuration.md:32` le dit |
| [INFO] Doc : `/docs`, `/openapi.json` non contrôlés | Reconduit |
| [INFO] Garde de suppression, traduction des erreurs, mots de passe des stores, `.dockerignore`, proxy Vite | Reconduits ; fichiers concernés non modifiés ou modifiés sans toucher ces points |
| — | **Nouveaux [INFO]** : entrée mal formée de `API_ALLOWED_HOSTS` ignorée sans le dire (journal trompeur) ; tolérances du garde sans portée ; résidu linéaire de l'éditeur |

Aucune régression trouvée. Aucun contournement du garde `Host` trouvé. Score **97 → 97** ;
MIN 8 → 6 ; INFO 11 → 8.

---

## Revue du garde Host réécrit

Fichier : `document-parser/infra/host_guard.py` (89 lignes). Tout est **[lu]** sauf mention ; le
comportement du moteur `re` et des serveurs HTTP est **[hyp.]** quand il n'est pas couvert par
les tests listés.

Le cœur :

```python
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})                     # :31
_HOST = re.compile(r"(?P<name>[a-z0-9_.-]+|\[[0-9a-f:.]+\])(?::(?:[0-9]{1,5}|\*))?", re.ASCII)  # :34
match = _HOST.fullmatch((host or "").strip().lower())                              # :39
```

- **Ancrage** : `fullmatch` (`:39`), donc ancré aux deux bouts ; pas de `^`/`$` à oublier.
- **Comparaison** : le nom extrait est cherché par égalité dans un `frozenset`/`set` (`:83`) ; ni
  préfixe, ni sous-chaîne, ni résolution DNS. `None` (Host mal formé) n'est jamais dans
  l'ensemble : `names - {None}` (`:76`).
- **Retour arrière** : aucun quantificateur imbriqué ; les deux branches commencent par des
  caractères disjoints (`[` contre `[a-z0-9_.-]`), le port commence par `:`, absent des deux
  classes. Coût linéaire en longueur **[hyp., par lecture du motif]**.

| Entrée (`Host`) | Ce que fait le code | Verdict |
|-----------------|---------------------|---------|
| `attacker.example:3000` (rebinding) | nom `attacker.example`, pas dans l'ensemble → 421 JSON | Fermé |
| `localhost.evil.com` | nom entier `localhost.evil.com` ≠ `localhost` → 421 | Fermé (testé, `test_api_host_guard.py:110`) |
| `evil.com.localhost` | nom entier ≠ `localhost` → 421 | Fermé |
| `localhost%00.evil.com` | `%` hors classe → `fullmatch` échoue → `None` → 421 | Fermé |
| `localhost:80@evil.com` (défaut de la base) | `@` hors classe et hors port → `None` → 421 | **Fermé** (testé, `:100`, `:127`) |
| `[::1]evil` (défaut de la base) | après `]` il faut `:` ou la fin → `None` → 421 | **Fermé** (testé, `:101`, `:128`) |
| `evil.com@localhost` | `@` → `None` → 421 | Fermé (testé, `:109`) |
| `localhost.` (point final) | nom `localhost.` ≠ `localhost` → 421 | Fermé (testé, `:111`) ; un nom listé écrit avec point final ne correspond pas non plus |
| `LOCALHOST:3000` | `.lower()` avant le motif → `localhost` → accepté | Correct |
| `` (vide), absent | `(host or "")` → `""` ; `+` exige un caractère → `None` → 421 | Fermé |
| `:80` (nom vide) | `None` → 421 | Fermé |
| Nom de 10 000 caractères | une seule classe répétée, retour arrière linéaire **[hyp.]** ; nom refusé sauf s'il est listé ; uvicorn borne la taille des en-têtes en amont **[hyp.]** | Pas de ReDoS |
| `[::1]`, `[::1]:8000` | branche IPv6, nom `[::1]` → accepté | Correct (testé, `:75-76`) |
| `[::ffff:127.0.0.1]` | motif accepté, nom ≠ `[::1]` → 421 | Fermé |
| `[::1` (crochet non fermé) | aucune branche ne correspond → `None` → 421 | Fermé (testé, `:102`) |
| `[::1]:` (port vide) | `[0-9]{1,5}` exige un chiffre → `None` → 421 | Fermé |
| `localhost:*` dans une requête | motif accepté, mais `endswith(":*")` sans `port_wildcard` → `None` → 421 (`:40`) | Fermé (testé, `:104`, `:138`) |
| `localhost:99999` | port 1 à 5 chiffres sans borne 65535 → accepté | Sans portée (le nom est loopback) |
| Octets non ASCII (`café.lan`) | décodage latin-1 par Starlette ; `re.ASCII` et classe ASCII → `None` → 421 ; aucun caractère latin-1 ne devient ASCII par `.lower()` | Fermé (testé, `:129`) |
| Blancs Unicode autour (`\xa0localhost`) | `strip()` les retire → `localhost` → accepté | Sans portée (INFO) : le nom est vraiment loopback ; un navigateur ne l'envoie pas |
| Deux en-têtes `Host` | `Headers.get` prend le premier ; h11 / httptools / nginx peuvent refuser avant **[hyp.]** | Sans portée navigateur : un navigateur n'en envoie qu'un et le script ne peut pas fixer `Host` |
| Liste `studio.lan:3000`, `Host: studio.lan` (nginx retire le port) | entrée → nom `studio.lan` ; requête → `studio.lan` → accepté | Correct, piège de la base levé (testé, `:90`) |
| Liste `*` (seule ou parmi d'autres) | `is_host_check_on` → `False`, middleware non monté (`:45-48`, `main.py:117`) | Correct : `*` = aucun contrôle, documenté |
| Liste `*.example.com`, `http://x` | entrée → `None`, ignorée ; contrôle actif avec loopback seul | Fermé ; journal trompeur (INFO) |
| Liste `" , "` ou vide | `settings.py:285-287` filtre les vides → liste vide → contrôle off | Correct, documenté |
| `/api/documents` | `startswith("/api/")` (`:79`) → contrôlé | Correct |
| `/api` (sans barre), `/API/x` | non contrôlés ; aucune route ne correspond → 404 | Correct |
| `/mcp` | hors préfixe ; son propre contrôle (`bootstrap/mcp_mount.py:136`, `MCP_ALLOWED_HOSTS`) | Correct |
| `/docs`, `/openapi.json` | non contrôlés | Schéma public (INFO) |
| Scope `websocket` | passé tel quel (`:79`) ; aucune route websocket dans `document-parser` (`rg -i websocket` vide hors dépendances) | Correct aujourd'hui ; une future route websocket sous `/api` ne serait pas contrôlée |
| Scope `lifespan` | passé tel quel | Correct |
| Réponse 421 | `JSONResponse({"detail": "Invalid Host header"}, 421)` (`:88-89`) ; corps non lu ; pas d'en-tête CORS (le garde est le plus externe) | Correct, conforme à la doc |
| Journal du refus | `logger.debug` avec `%r` (`:86-87`) : pas d'injection de retour à la ligne, pas de bruit au niveau par défaut | Défaut de la base levé |
| Ordre des middlewares | ajouté en dernier → le plus externe (`main.py:115-118`) | Correct : un refus ne compte pas dans le rate limit |
| Défaut (variable absente) | middleware non monté ; journal « open to DNS rebinding » | **MAJ toujours ouvert** |

**Les deux défauts de la base sont fermés** (et couverts par des tests). **La réécriture n'ouvre
rien** : le passage d'une comparaison du `Host` complet à une comparaison du nom seul élargit ce
qui est accepté pour un nom listé (tout port), ce qui est sans effet contre le rebinding, où
l'attaquant ne choisit pas le nom (c'est celui de sa page). Le seul effet indésirable trouvé est
le journal de démarrage qui liste une entrée que le code a écartée (INFO).

### Autres changements relus

| Surface | Ce que fait le code | Verdict |
|---------|---------------------|---------|
| Limite de corps (`infra/body_limit.py:39-48`) | `Content-Length` non ASCII, non numérique (`-1`, `1e9`, `abc`) ou de plus de 20 chiffres → 400 JSON ; `int()` ne peut plus lever ; au-dessus du plafond → 413 | Correct. Changement de comportement : `abc` donnait un comptage, donne maintenant 400 ; plus strict, sans risque |
| Suppression d'analyse (`persistence/analysis_repo.py:206-237`) | `BEGIN IMMEDIATE`, lecture du `document_id` de l'analyse, lecture de l'état du document, `DELETE` ; si c'était l'active, `_find_latest_parsed_ids(db, [document_id])` puis `write_selection(db, document_id, ...)` ; commit ; une exception ferme la connexion sans commit (`database.py:367-373`) → retour arrière | Tout en `?` ; la requête de resélection filtre `WHERE document_id IN (?)` avec `PARTITION BY document_id` et le résultat est lu par `latest.get(document_id)` : **un document ne peut pas adopter l'analyse d'un autre**. En plus, les déclencheurs `document_analysis_state_validate_insert/update` refusent une analyse d'un autre document (`database.py:96-113`). L'identifiant vient du chemin de la route, jamais d'un SQL construit |
| Export PDF (`services/export_service.py:93-101`) | `resolve` puis `has_file` sur le chemin résolu | Pas d'élargissement (INFO ci-dessus) |
| Analyse demandée à l'export (`:131-136`, `_load_requested_analysis`) | `can_be_current_of(doc_id)` = même document et terminée (`domain/models.py:188-190`) | Équivalent à l'ancien test explicite |
| Bannière de refus (`frontend/src/features/analysis-editor/ui/EditorBanners.vue:5-8`) | `{{ saveError }}` : interpolation Vue, texte échappé | **Pas de XSS** ; aucun nouveau `v-html` dans `frontend/src` |
| Payloads stockés (`api/schemas.py:317-359`) | un modèle par requête, champs repris sans `type` et sans bornes (`_strip_bounds`), base `_StoredPayload` en `extra="forbid"`, tous les champs requis | Toujours `extra="forbid"` : un payload stocké avec une clé en trop fait échouer la validation, il ne peut pas injecter de champ dans la réponse. Les six formes restent disjointes (clés différentes, ou `text: str` contre `level: int`). Elles relisent tout payload écrit par `_to_edit_commands` (`api/analysis_edits.py:94-103`, `model_dump(by_alias=True, exclude={"type"})`, toutes les clés) **[hyp. pour les lignes anciennes : formes identiques à l'ancien code à la lecture]** |
| Dépendances de routes (`api/deps.py:42-46,91-102`) | `require(...)` → `HTTPException(503, detail=<texte fixe>)` (`api/state.py:104-108`) | Pas de fuite : message constant, aucune trace. Le message de `DocumentTreeService` dit « Chunk service not available » : imprécis, sans portée |
| Réponse de l'éditeur dans un thread (`api/analysis_edits.py:62`) | `asyncio.to_thread` | Améliore la tenue de la boucle d'événements |
| Release Gate | voir le delta | Correct |

### Doc contre code

| Document | Dit | Code | Verdict |
|----------|-----|------|---------|
| `docs/configuration.md:136` | 421 avec `{"detail": "Invalid Host header"}` si non listé ou mal formé | `host_guard.py:83-89` | Exact |
| `docs/configuration.md:142` | nom seul comparé, port d'une entrée ignoré, `*` = aucun contrôle | `:34-42`, `:45-48`, `:75-76` | Exact |
| `docs/configuration.md:143` | loopback toujours accepté une fois le contrôle actif | `:31`, `:76` | Exact |
| `docs/configuration.md:145` | seul `/api/*` est contrôlé | `:79` | Exact |
| `docs/configuration.md:146` | une ligne au démarrage | `main.py:119` | Exact ; la ligne recopie la liste brute (INFO) |
| `.env.example:44-49` | nom seul, port ignoré, loopback toujours, 421 ; valeur recommandée | idem | Exact |
| `SECURITY.md:53-59` | off par défaut, valeur à mettre sur un poste, « Neither check is access control » | `settings.py:112` | Exact, ne surévalue pas |
| `CHANGELOG.md:55` | 421 JSON, nom seul, off par défaut | idem | Exact |

Rien de surévalué. Seul manque : la doc ne dit pas qu'une entrée mal formée est ignorée.

---

## Points positifs

- **Garde `Host` plus simple et plus strict** : un motif ancré, une comparaison d'égalité, refus
  de tout `Host` mal formé ; les deux défauts de robustesse de la base sont fermés et testés.
- **Plus de 500 sur `Content-Length`** ; plus de journal non borné.
- **Suppression d'analyse atomique** sous verrou d'écriture, resélection bornée au document et
  doublée par les déclencheurs SQL.
- **Release Gate en jeton de lecture** par défaut ; pas de verdict sur un run annulé.
- **Doc alignée sur le code**, y compris sur ce que le contrôle ne fait pas.

---

## Verdict partiel : GO conditionnel

Score **97/100**, **0 CRIT**, **1 MAJ**, **6 MIN**, **8 INFO** — score inchangé, deux MIN résolus,
tous les défauts de la base sur le garde `Host` et la limite de corps fermés. Conditions :

1. 8.5.1 conforme **sous réserve du scan Trivy du Release Gate** (images `remote` et `local`),
   non lancé sur cet arbre ; s'il échoue : 92/100, 1 CRIT → NO-GO.
2. Décision explicite du mainteneur sur le MAJ : défaut `API_ALLOWED_HOSTS` dans les fichiers
   compose, ou risque accepté et documenté pour 0.7.4.
3. #378 soldé (ou re-daté avec justification) avant le 2026-12-31.

**Non vérifié sans exécution** : le comportement réel du moteur `re` sur des `Host` très longs ;
le refus par httptools / h11 / nginx des `Host` dupliqués ; le coût réel de
`DoclingDocument._move_subtree` ; la relecture des payloads stockés par d'anciennes versions
(seulement comparée au code) ; le comportement de `BEGIN IMMEDIATE` sous contention (attente puis
erreur « database is locked ») ; le scan Trivy ; `npm audit` et `pip-audit` ; l'exploitabilité
réelle du rebinding sur une installation par défaut.
