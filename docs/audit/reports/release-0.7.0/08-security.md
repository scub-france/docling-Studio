# Rapport d'audit : Securite

**Release** : 0.7.0
**Date** : 2026-08-24
**Auditeur** : claude-code

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 13 / 14 |
| Score | 97 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 1 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 3 |

Detail du calcul : poids total de la checklist = 36. Seul l'item 8.5.2
(poids 1) est non conforme. Poids conformes = 35. Score = 35 / 36 = 97.

Note de methode : l'ecart [MAJ] "SSRF" ci-dessous est un constat de securite
reel mais qui ne fait pas basculer un item pondere en non-conforme (l'item le
plus proche, 8.2.1, reste satisfait — la validation Pydantic est bien
presente). Il est reporte comme ecart mais ne diminue pas le score de
compliance, qui reste strictement adosse a la checklist.

---

## Ecarts constates

### [MAJ] Probe test-connection : SSRF cote serveur sur URL fournie par l'utilisateur (deploiement self-hosted)

- **Localisation** : `document-parser/domain/app_config.py:83` (validation) + `document-parser/services/app_config_service.py:146` (`test_connection`) + `document-parser/infra/llm/ollama_probe.py:29` (requete sortante)
- **Constat** : `POST /api/config/reasoning/test` et `PUT /api/config/reasoning`
  acceptent un `host` arbitraire. `validate_host_url` ne controle que le schema
  (`http`/`https`) et la presence d'un `netloc` — aucune liste de blocage des
  cibles internes (loopback `127.0.0.1`, lien-local `169.254.169.254` metadata,
  plages RFC1918 `10.0.0.0/8`, `192.168.0.0/16`, etc.). Le serveur emet alors un
  `GET {host}/api/tags` (`ollama_probe.py:29-33`) et renvoie au client la
  joignabilite + la chaine d'erreur. L'API n'ayant aucune authentification, sur
  un deploiement `self-hosted` tout appelant capable d'atteindre le backend peut
  s'en servir pour sonder des hotes/ports internes (SSRF, scan de reseau via les
  messages d'erreur et le timing).
- **Regle violee** : 8.2.1 (validation des entrees — robustesse / defense en
  profondeur). L'item est nominalement satisfait (schemas Pydantic presents),
  d'ou le classement en ecart de securite additionnel plutot qu'en bascule
  d'item.
- **Facteurs attenuants** : le probe est explicitement refuse (403) sur le seul
  mode de deploiement public/non-fiable — `read_only = deployment_mode ==
  "huggingface"` (`document-parser/bootstrap/builder.py:203`,
  `app_config_service.py:153` via `_require_writable`), ce qui est documente
  dans le docstring de `test_connection` ("SSRF surface on a public Space").
  Timeout court (3 s), pas de proxy du corps de reponse, CORS restreint a
  localhost par defaut.
- **Remediation** : ajouter dans `validate_host_url` (ou le port `LLMHostProbe`)
  une resolution DNS suivie d'un rejet des adresses loopback / lien-local /
  privees / reservees avant toute requete sortante ; documenter le modele de
  confiance self-hosted (reseau maitrise) dans `SECURITY.md`.

### [MIN] Dependances backend sans borne superieure de version

- **Localisation** : `document-parser/pyproject.toml:10` (`python-multipart>=0.0.12`), `document-parser/pyproject.toml:35-36` (`torch`, `torchvision` sans contrainte de version)
- **Constat** : la quasi-totalite des dependances est bornee (`>=X,<Y`), mais
  `python-multipart>=0.0.12` n'a pas de borne superieure et `torch` /
  `torchvision` sont declares sans aucune version. La checklist 8.5.2 exige
  "pas de `>=` sans borne superieure".
- **Regle violee** : 8.5.2 — Les versions des dependances sont epinglees.
- **Facteurs attenuants** : `uv.lock` est resolu en `--frozen` dans le
  Dockerfile (`Dockerfile:40`, `Dockerfile:100-104`), ce qui epingle les
  versions exactes a l'installation ; `torch`/`torchvision` sont volontairement
  laisses libres pour etre rediriges vers l'index CPU via `[tool.uv.sources]`.
  Le risque reel est donc faible (lockfile deterministe).
- **Remediation** : ajouter une borne superieure a `python-multipart`
  (ex. `>=0.0.12,<1.0.0`) et, si possible, un plafond majeur sur
  `torch`/`torchvision`, pour aligner la declaration sur le lockfile.

### [INFO] Suppression trivyignore expiree

- **Localisation** : `.trivyignore.yaml:6` (`CVE-2026-40393`, `expired_at: 2026-06-30`)
- **Constat** : la fenetre de suppression de `CVE-2026-40393` (Mesa OOB read,
  tire transitivement par `libgl1`) a expire le 2026-06-30 ; a la date de
  l'audit (2026-08-24) elle n'est plus active et re-apparaitra dans le scan
  Trivy. Trois autres entrees restent valides (`2026-08-31`, `2026-09-30` x2)
  avec justification (non atteignables depuis le code applicatif).
- **Regle violee** : 8.5.1 (item nominalement conforme — CVE OS transitive,
  documentee, non atteignable) ; observation de maintenance.
- **Remediation** : re-trier `CVE-2026-40393` (drop de `libgl1` via
  `opencv-python-headless`, cf. #189) ou prolonger `expired_at` avec une
  justification a jour.

### [INFO] API sans authentification — endpoints de configuration inscriptibles en self-hosted

- **Localisation** : `document-parser/main.py:77` (aucun middleware d'auth)
- **Constat** : aucune couche d'authentification/autorisation n'est presente.
  Sur `huggingface` les ecritures de config sont neutralisees (403), mais en
  `self-hosted` `PUT/DELETE /api/config/reasoning` et l'ensemble des routes CRUD
  sont ouverts a quiconque atteint le backend. C'est un choix d'architecture
  assume (outil studio local / demo Space), a garder explicite.
- **Regle violee** : aucune (la checklist ne couvre pas l'authentification) —
  observation de posture.
- **Remediation** : documenter le modele de confiance dans `SECURITY.md` ;
  prevoir une protection reseau (reverse-proxy authentifie) pour tout
  deploiement self-hosted expose.

### [INFO] Absence de garde-fou contre `CORS_ORIGINS="*"` avec credentials

- **Localisation** : `document-parser/infra/settings.py:146` + `document-parser/main.py:79-83`
- **Constat** : `allow_credentials=True` est combine a une liste d'origines
  configuree par `CORS_ORIGINS`. Le defaut est explicite (localhost), donc
  conforme, mais rien n'empeche un operateur de positionner `CORS_ORIGINS="*"`,
  configuration dangereuse avec `allow_credentials=True`.
- **Regle violee** : 8.4.1 (item conforme par defaut) — durcissement suggere.
- **Remediation** : rejeter au boot (dans `Settings.__post_init__`) la
  combinaison `"*"` + credentials, ou logger un avertissement fort.

---

## Points positifs

- **Secrets** : aucun secret en dur dans le code ni dans le depot (`git
  ls-files` ne remonte aucun `.env`/`.pem`/`.key`) ; `.env`, `.env.local`,
  `.env.production` sont dans `.gitignore`. Les valeurs sensibles
  (`DOCLING_SERVE_API_KEY`, `NEO4J_PASSWORD`, `STORE_SECRET_KEY`) transitent par
  `environment:` dans `docker-compose.yml`, jamais par des build args (seuls des
  flags de bake modele sont passes en args).
- **Chiffrement au repos** : les mots de passe de connexion des stores sont
  scelles via `FernetBox` (`infra/secrets/fernet_box.py`) ; le backend refuse de
  booter si un secret scelle existe sans `STORE_SECRET_KEY`. Les valeurs
  scellees ne sont jamais loggees.
- **Injection SQL** : toutes les requetes utilisent des parametres lies (`?`).
  Les deux f-strings SQL (`persistence/analysis_repo.py`, `chunk_repo.py:122`)
  n'interpolent que des constantes de module / clauses litterales, jamais
  d'entree utilisateur. Aucun `eval`/`exec`/`os.system`/`subprocess`.
- **XSS** : l'unique `v-html` du frontend
  (`frontend/src/features/analysis/ui/MarkdownViewer.vue:24`) est assaini par
  `DOMPurify.sanitize` apres `marked`. Les reponses du moteur de reasoning
  (#303) sont rendues en interpolation texte (`TurnCard.vue:15` — echappement
  Vue automatique).
- **Upload** : double controle de taille (Content-Length puis lecture en
  streaming borne, `api/documents.py:79-89`), validation de type par magic bytes
  `%PDF` (`services/document_service.py:75`), stockage sous nom `uuid4().pdf`
  (pas de path traversal via le nom de fichier), plafond de pages.
- **CORS** : liste d'origines explicite, methodes et en-tetes restreints ; pas
  de `*`.
- **Rate limiting** : middleware par IP fenetre glissante, actif par defaut
  (100 rpm), `/api/health` exclu (`infra/rate_limiter.py:59`).
- **Nginx** : en-tetes de securite (`X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, `X-XSS-Protection`), pas de directive `autoindex` (listing
  desactive), body size borne. Conteneur execute en utilisateur non-root
  (`Dockerfile:52,63`).
- **Config runtime** : ecritures et probe explicitement refusees (403) sur le
  deploiement `huggingface` (surface non-fiable), lectures tolerantes.
- **Dependances** : `.trivyignore.yaml` documente chaque CVE OS transitive avec
  une justification d'inatteignabilite et une date d'expiration ; dependances
  applicatives majoritairement bornees.

---

## Verdict partiel : GO

0 ecart CRITICAL, score 97/100 (>= 80), 1 seul ecart MAJOR (<= 3, non
bloquant). Conditions de suivi recommandees avant/juste apres release :
1. Corriger l'ecart [MAJ] SSRF — blocklist des cibles internes dans
   `validate_host_url` (durcissement du probe test-connection en self-hosted).
2. Traiter l'ecart [MIN] 8.5.2 (bornes superieures manquantes) et la
   suppression trivyignore expiree ([INFO] `CVE-2026-40393`).
