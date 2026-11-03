# Synthèse d'audit — Release 0.7.4

**Date** : 2026-11-03
**Branche** : `release/0.7.4` au commit `1de1929` (= tag `v0.7.3` + 2 commits README qui remplacent le GIF de présentation)
**Auditeur** : claude-code
**Périmètre de la release** : la 0.7.4 ne contient encore aucun changement fonctionnel. Elle est ouverte comme **release qualité** : son but est de remonter la note de ce gate en soldant la dette d'audit.
**Baseline** : re-audit 0.7.3 (`docs/audit/reports/release-0.7.3-reaudit/`) pour 07, 08, 10, 11 et 12 ; 1er audit 0.7.3 (`docs/audit/reports/release-0.7.3/`) pour les autres.

---

## Tableau de bord

| #  | Audit                  | Score (0.7.3 → 0.7.4) | CRIT | MAJ | MIN | INFO | Verdict |
|----|------------------------|-----------------------|------|-----|-----|------|---------|
| 01 | Hexagonal Architecture | 78 → **78**           | 0    | 3   | 1   | 7    | GO CONDITIONNEL |
| 02 | DDD                    | 92 → **92**           | 0    | 1   | 6   | 5    | GO |
| 03 | Clean Code             | 44 → **39**           | 0    | 3   | 5   | 8    | **NO-GO** (score) |
| 04 | KISS                   | 75 → **75**           | 0    | 1   | 2   | 7    | GO CONDITIONNEL |
| 05 | DRY                    | 67 → **67**           | 0    | 3   | 16  | 6    | GO CONDITIONNEL |
| 06 | SOLID                  | 87 → **87**           | 0    | 2   | 0   | 12   | GO |
| 07 | Decoupling             | 94 → **94**           | 0    | 1   | 0   | 15   | GO |
| 08 | Security               | 97 → **97**           | 0    | 3   | 7   | 7    | GO |
| 09 | Tests                  | 93 → **93**           | 0    | 1   | 4   | 11   | GO |
| 10 | CI / Build             | 85 → **85** (provisoire) | 0 | 1   | 1   | 13   | GO (provisoire) |
| 11 | Documentation          | 100 → **72** (pré-gel) | 1   | 1   | 0   | 16   | **NO-GO** (CRIT) |
| 12 | Performance            | 67 → **67**           | 0    | 2   | 7   | 9    | GO CONDITIONNEL |

**Score global** : **79 / 100** (moyenne simple des 12 scores, 946 / 12 = 78,8), même méthode qu'en 0.7.0 et 0.7.3. C'était ≈ 82 au re-audit 0.7.3.
**Écarts CRITICAL** : **1** (11.1.1, CHANGELOG sans section pour la version — étape normale du gel).
**Écarts MAJOR** : **22**.

### Pourquoi la note baisse alors que le code n'a pas bougé

`git diff v0.7.3..1de1929` ne touche que `README.md` et deux GIF. **Aucun écart n'est corrigé, aucun n'est aggravé par du code nouveau.** La baisse de 82 à 79 vient de deux causes, toutes deux attendues ou méthodologiques :

1. **11 — Documentation, 100 → 72** : la nouvelle release n'a ni section `[Unreleased]`/`[0.7.4]` dans `CHANGELOG.md`, ni bump de `frontend/package.json` (encore `0.7.3`). C'est le même score qu'au premier audit 0.7.0 au même stade pré-gel. Le commit de gel ramène l'audit à 100.
2. **03 — Clean Code, 44 → 39** : l'item 3.2.4 (flag arguments, poids 1) a été évalué cette fois sur le TS/Vue et le JS des cartes MCP, et plus seulement sur Python. Trois flag arguments, tous antérieurs à 0.7.3, le rendent non conforme (`mcp_adapter/citation_app.html:1033`, `mcp_adapter/sources_app.html:601`, `PagePreviewWithOverlay.vue:385`). **Avec la lecture de 0.7.3, l'audit 03 resterait à 44** et le score global à 79,3.

Les audits ont aussi relevé des écarts **anciens jamais vus jusqu'ici** (aucune régression) : notamment deux MAJ sécurité démontrés (08), le détail des specs Karate UI cassées (09), et des règles domaine dupliquées dans les services (01).

### État de la branche au moment de l'audit

- **Gates statiques locaux verts** : ruff, ruff format, `uv lock --check`, eslint, prettier, vue-tsc, vite build. actionlint 0 erreur (audit 10).
- **Tests unitaires locaux verts** : backend 1323 passed, 19 skipped (15 Neo4j absent, 4 `docling` non installé dans le groupe `dev`) ; frontend 53 fichiers, 545 passed.
- **CI / Release Gate** : aucun run sur `1de1929`. Les deux commits README ont été poussés sur `main` avec `[skip ci]`. Le dernier gate complet est vert (13/13, run `41468347487`) sur `59674be`, dont l'arbre est identique au tag `v0.7.3`. Le score 10 est donc **provisoire** jusqu'au gate de la PR `release/0.7.4` → `main`.

---

## Écart CRITICAL

1. **[11] Pas de section `[0.7.4] - <date>` dans le CHANGELOG** — `CHANGELOG.md:5-7`. Il n'y a même pas de section `[Unreleased]` où les PR de remédiation pourraient écrire leur entrée (`CONTRIBUTING.md:107`, `.github/PULL_REQUEST_TEMPLATE.md:26`). Étape de gel : `docs/maintainers.md:21-24`.

---

## MAJOR (22)

### Nouveaux, requalifiés ou étendus en 0.7.4 (aucun ne vient de code nouveau)

| Audit | Écart | Localisation | Effort / risque |
|-------|-------|--------------|-----------------|
| 08 | **Import Docling : déni de service par amplification** (MIN → MAJ, démontré). Un JSON de 691 octets décrivant une table de 400 × 400 coûte 18 s et 347 Mo ; vers ~1 350 × 1 350, on atteint la limite mémoire du conteneur. `num_rows`/`num_cols` ne sont pas bornés et `grid` est un `computed_field` dans docling-core. | `api/analyses.py:73-87`, `infra/docling_importer.py:18-26` | S / faible : plafond de cellules après `model_validate` + plafond de corps |
| 08 | **SSRF via les stores** : `connection_uri` est libre, sans la garde `_resolved_target_is_blocked` utilisée pour la sonde Ollama, et les erreurs renvoient `str(exc)`. Code de la 0.6.1 (#279), surface dépréciée. | `api/stores.py:86,118,143-164`, `services/store_service.py:109-127,310-343` | S / faible |
| 09 | **Karate UI** : 9 features (11 scénarios) pilotent une UI qui n'existe plus (3 annoncées en 0.7.3), dont la feature #342 cassée par #359 ; 21 features sur 26 ne tournent dans aucun workflow (`--tags @critical` seulement). | `e2e/…/documents/*.feature`, `navigation/sidebar.feature:14`, `ci.yml:220`, `release-gate.yml:650` | S (purge et rebasage) + preuve d'exécution |
| 11 | `frontend/package.json:3` et son lockfile en `0.7.3` | `frontend/package.json:3`, `package-lock.json:3,9` | XS (gel) |

### Dette reconduite (18 MAJ)

| Audit | Écart | Statut 0.7.4 |
|-------|-------|--------------|
| 01 | Règles métier dans les services : split/merge (`chunk_service.py:335,393`, alors que `domain/chunk_editing.py` n'est importé par aucun code de production), citations, lecture budgétée ; **nouveau** : hash de chunkset recalculé (`chunk_service.py:865`) au lieu de `domain/hashing.py:43`, niveau de titre réécrit (`chunk_service.py:928`) | Inchangé, périmètre précisé |
| 01 | Services dépendant de concrétions : pypdfium2/pdf2image et I/O disque dans `document_service.py:14-15`, `analysis_service.py:17` ; typage `Sqlite*` | Inchangé, périmètre précisé |
| 01 | Orchestration et I/O dans les routeurs : `api/documents.py:40-66,176-216` ; `api/analyses.py:84` choisit 404/400 d'après le **texte** du message | Inchangé |
| 02 | Langage ubiquitaire : `version_id` d'ancre = id d'`AnalysisJob` ≠ `DocumentVersion` ; round / hop / iteration ; « History » désigne deux choses au front | Inchangé, constat complété |
| 03 | Cartes MCP en français en dur (choix produit 0.7.3) ; ~80 lignes, ~100 fragments, plus 3 chaînes anglaises dans la carte française (`citation_app.html:680,706,825`) | Inchangé |
| 03 | Fonctions multi-responsabilités (5, dont 3 dans l'ingestion dépréciée) | Inchangé |
| 03 | Fichiers fourre-tout : `chunk_service.py` (1 019 lignes, trois concepts), `mcp_adapter/sources_view.py` | Inchangé |
| 04 | Abstraction LLM-provider prématurée (4e constat) : enum à un seul membre, `health_check` sans appelant, double garde | Inchangé |
| 05 | `_parse_iso` copié 7 fois, divergence UTC (`persistence/*_repo.py`) | Inchangé |
| 05 | Couleurs UI en dur : 74 sites dans 14 SFC, dont 33 `var(--color-*)` d'un namespace jamais défini et 3 `var(--danger)` qui n'existe pas | Inchangé, inventaire complété |
| 05 | Contrat d'erreur service → HTTP copié : 6 bases `XServiceError`, 14 mappings en ligne, 2 helpers `_raise_for` ; « document introuvable » exprimé de 6 façons | Inchangé, constat complété |
| 06 | `DocumentService` contourne `PageRasterizer` / `PageTextReader` | Inchangé |
| 06 | Ports incomplets : 16 sites appellent des méthodes absentes du port ; pas de `DocumentVersionRepository` ; 4 services typés sur des classes concrètes | Inchangé, inventaire complet |
| 07 | `StoreResponse.config: dict` / `GraphNode extra="allow"` (ingestion dépréciée) | Inchangé |
| 08 | `/api/*` ne contrôle pas `Host` (DNS rebinding contre une instance locale) | Inchangé |
| 10 | La variante `local` publiée (reasoning, arm64) n'est ni construite, ni scannée, ni démarrée par le gate | Inchangé (3e audit) |
| 12 | Chaque page rendue relit le PDF entier puis en écrit une copie temporaire (mesuré : +69 ms et 48 Mo écrits par page sur un PDF de 48 Mo) | Inchangé |
| 12 | Écritures de chunks : une connexion et un commit par chunk (mesuré : 500 suppressions + audit = 3 043 ms contre 14 ms en `executemany`) ; la docstring de `chunk_edit_repo.py:52-56` promet une transaction unique qui n'existe pas | Inchangé |

Le MAJ 0.7.3 « exposition MCP » est **reclassé MIN** par l'audit 08 : les textes (README, i18n, doc, CHANGELOG, `.env.example`) sont désormais exacts. Reste le défaut (MCP actif, port publié sur toutes les interfaces).

---

## Points de vigilance avant le tag

1. **`.trivyignore.yaml`** : les 5 suppressions (Pillow ×4, libxml2) expirent le **2026-12-31**. Un gate lancé à partir de cette date échoue (08 → 89, 10 → 70, CRIT). Aucune issue « docling → Pillow 13 » n'a été ouverte, alors que la synthèse 0.7.3 la demandait.
2. **Dépendances** : `npm audit --omit=dev` remonte 7 paquets HIGH (dont `dompurify` 3.3.3, utilisé au runtime), tous corrigeables par `npm audit fix`. pip-audit sur le groupe `local`, que le gate n'audite pas, trouve des avis sur `docling`/`docling-slim` 2.121.0 (corrigés en 2.131/2.132), `nltk`, `accelerate`, `setuptools`. `torch`/`torchvision` n'ont pas de borne de version (seul item non conforme de 08).
3. **Ne pas taguer un commit `[skip ci]`** : `release.yml` pourrait ne pas partir (non vérifié).

---

## Chemin vers le score maximal

Chaque audit est noté par item, en tout ou rien. Gains estimés par les auditeurs (score de l'audit concerné) :

| Action | Audit(s) | Gain | Effort / risque |
|--------|----------|------|-----------------|
| Commit de gel : `[0.7.4] - <date>` + bump `package.json` | 11 | 72 → **100** | XS / nul |
| Bornes `torch` / `torchvision` | 08 | 97 → **100** | XS / nul |
| `.dockerignore` frontend + motifs Python récursifs ; build `local` avec `WITH_REASONING` + smoke `local` au gate | 10 | 85 → **100** | S / faible |
| Rendu par chemin (`convert_from_path`, pdfium par chemin sous verrou) ; cache nginx `/assets` + gzip ; favicon/logo ; bibliothèque d'analyses sur `/summaries` | 12 | 67 → **90** | S / faible |
| + écritures de chunks en lot + 2 MIN | 12 | → **100** | M / moyen |
| Ports complets + `DocumentVersionRepository` + test AST | 06 | 87 → **94** | S / très faible |
| + ports PDF pour `DocumentService` | 06 | → **100** | M / modéré |
| `_parse_iso` unique + contrat d'erreur unique (`exception_handler`) | 05 | 67 → **83** | M / moyen |
| + tokens de couleur | 05 | → **100** | M / visuel modéré |
| Validation `MCP_MAX_READ_TOKENS` + plafond de rounds à un seul endroit | 04 | 75 → **83** | S / faible |
| Routeur `documents` qui délègue au service | 01 | 78 → **84** | M / faible |
| Typer `StoreResponse.config` et `GraphNode` | 07 | 94 → **100** | S-M / modéré |
| StrEnum pour les statuts textuels | 02 | 92 → **94** | S / faible |
| Specs Karate purgées et rebasées + preuve d'exécution | 09 | 93 → **100** | S + exécution |
| Flag arguments (3 fonctions) + scission de `sources_view.py` et de `chunk_service.py` | 03 | 39 → **61** | M / moyen |

**Estimation** : la remédiation sans décision produit mène à un score global d'environ **92-93 / 100**. Le reste dépend des décisions ci-dessous.

---

## Décisions attendues du mainteneur

1. **Contrôle `Host` sur `/api/*` (MAJ 08).** Une liste blanche par défaut (`localhost,127.0.0.1,[::1]`) ferme le DNS rebinding, mais **casse l'accès par IP LAN ou par nom de domaine** : c'est un changement BREAKING pour une version patch. Alternative : le livrer en opt-in en 0.7.4, puis l'activer par défaut avec l'authentification en 0.8.0.
2. **Langue des cartes MCP (MAJ 03, item 3.1.3).** Garder le français assumé (l'item reste non conforme), ou passer par une table `{ en, fr }` avec l'anglais par défaut (effort M, 1 à 1,5 j, JS non testé par la CI : recette manuelle nécessaire).
3. **Carte `show_citation` (KISS 4.2).** Désactivée par défaut depuis 0.7.3 (`MCP_CITATION_CARD`), elle fait 1 177 lignes de HTML. La retirer fait gagner 17 points à l'audit 04 (avec l'option B LLM-provider), mais c'est le retrait d'une fonctionnalité annoncée.
4. **Lecture de l'item 3.1.1 (nommage verbal).** Accepter « nom = valeur renvoyée » pour les fonctions pures (+5,6 points sur 03) ou appliquer la lecture stricte (~96 fonctions Python et ~45 JS à renommer).
5. **Lecture de l'item 6.5.1 (SOLID, DIP)**, comme en 0.7.0 et 0.7.3 : la synthèse garde MAJ pour les imports `persistence`/`infra` sous `TYPE_CHECKING`. Une lecture stricte en ferait un CRIT. La correction des ports (ligne 06 du tableau) clôt la question.

---

## Verdict final : **NO-GO** (au stade pré-gel)

- 1 écart CRITICAL non résolu (CHANGELOG), levé par le commit de gel.
- Score global 79 : zone GO CONDITIONNEL, mais 22 MAJ dépassent le seuil de 3.
- 2 audits sur 12 sous 60 ou en CRIT (03 et 11).

Comme la 0.7.4 sert de release qualité, la suite est une **branche de remédiation** qui traite le tableau « Chemin vers le score maximal », dans cet ordre : sécurité et CI (08, 10), performance (12), ports et contrats (06, 05, 01), documentation (11), puis Clean Code (03). Elle sera suivie d'un re-audit des audits touchés, dans `docs/audit/reports/release-0.7.4-reaudit/`.
