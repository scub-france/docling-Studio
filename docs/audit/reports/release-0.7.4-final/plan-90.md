# Plan 90+ — Clean Code, KISS, Documentation

**Date** : 2026-11-20
**Point de départ** : [contrôle final](summary.md) sur `707a486`. Clean Code 72, KISS 75, Documentation 72.
**Cible** : chacun des trois à 90 ou plus.

---

## 1. Pourquoi ces trois notes sont basses

Les trois grilles sont courtes et chaque item est binaire : conforme ou non, sans note partielle.

| Audit | Points obtenus | Items en échec | Ce que coûte un item |
|-------|----------------|----------------|----------------------|
| 11 Documentation | 13 / 18 | 11.1.1 (poids 3), 11.2.1 (poids 2) | 11 à 17 points |
| 04 KISS | 9 / 12 | 4.2 (poids 2), 4.5 (poids 1) | 8 à 17 points |
| 03 Clean Code | 13 / 18 | 3.2.1 (poids 2), 3.2.2, 3.2.3, 3.3.1 (poids 1) | 6 à 11 points |

- **Documentation.** Les deux items en échec sont le freeze : `CHANGELOG.md` encore en `[Unreleased]`, version encore en 0.7.3 dans `frontend/package.json`. Tout le contenu documentaire est conforme. La note mesure « release pas encore figée ».
- **KISS.** L'item 4.2 échoue sur du code laissé en place exprès aux cycles précédents, parce que le retirer relève du mainteneur : fonctionnalités de la PR #319, tiroir d'historique. L'item 4.5 échoue sur de la configuration, dont deux réglages ajoutés par la seconde remédiation.
- **Clean Code.** Trois items sont écrits « aucune fonction », « aucun fichier » : une seule fonction de 31 lignes coûte autant que 65. La note est passée de 39 à 72 en corrigeant ce qui relève du jugement (nommage, fichiers fourre-tout, fonctions à plusieurs responsabilités, drapeaux). Il reste les trois items de comptage et deux fonctions Neo4j.

---

## 2. Cible par audit

| Audit | Aujourd'hui | Après le plan | Condition |
|-------|-------------|---------------|-----------|
| 11 Documentation | 72 | **100** | Le commit de freeze |
| 04 KISS | 75 | **100** (92 si 4.5 reste) | Décisions D1 à D4 |
| 03 Clean Code | 72 | **94** (17 / 18) | Décision D5 ; sans elle, plafond à 89 |
| Global | ≈ 89 | **≈ 95** | ≈ 97 avec une CI verte sur la PR (audit 10) |

---

## 3. Lots

### Lot 1 — Documentation, 72 → 100

Un commit, à faire en dernier parce que les lots 2 et 3 touchent encore le CHANGELOG.

- `CHANGELOG.md` : `## [Unreleased]` devient `## [0.7.4] - AAAA-MM-JJ`, avec une section `[Unreleased]` vide au-dessus.
- `frontend/package.json` et `frontend/package-lock.json` (deux endroits) : `0.7.4`.

Il manque une seule donnée : la date de release.

### Lot 2 — KISS, 75 → 100

**2a. Sans décision** (code ajouté par les cycles précédents, ou sans aucun appelant) :

| Sujet | Changement | Item |
|-------|------------|------|
| `API_ALLOWED_HOSTS` | Liste de noms seuls : plus de `:port`, `:*` ni `*`. Une seule fonction d'analyse, l'avertissement au démarrage est gardé | 4.5 |
| `MAX_IMPORT_SIZE_MB` | Redevient une constante ; retiré de la documentation, de `.env.example` et des fichiers compose | 4.5 |
| Règle de rechunk calculée deux fois | `ChunkService` ne lit plus l'état : l'écriture applique déjà la règle. Un paramètre de constructeur en moins | INFO |
| Code backend sans appelant | `DocumentMerger` et `infra/docling_merger.py`, `DocumentStoreLink.mark_stale`, `serve_converter.health_check`, `INSTRUCTIONS`, `_neutralise_all` en double | 4.2 |
| Code frontend sans appelant | `StaleStoresStrip.vue` | 4.2 |
| Cache d'aperçu | Ramené à sa forme la plus simple pour un chemin de repli | 4.2 |

**2b. Sur décision** :

| # | Sujet | Proposition | Conséquence |
|---|-------|-------------|-------------|
| D1 | Plomberie de l'éditeur (PR #319) | Retirer la route `POST .../analysis-edits/rebuild` et son client, jamais appelés ; retirer les champs `warnings`, `reference_changes`, `beforeElementId`, jamais lus ; comparer `engine_version` au chargement et reconstruire le cache s'il est périmé | Une route annoncée au CHANGELOG disparaît avant d'avoir été publiée. Aucun changement de schéma de base |
| D2 | Tiroir d'historique | Supprimer `HistoryDrawer.vue`, le chemin « workspace » du store de documents, les deux branches inatteignables de `DocParseTab.vue` et `doc-history-drawer.feature` (environ 450 lignes) | Aucun changement visible : rien ne monte ce tiroir depuis la 0.7.3. Restaurer une version reste possible par l'API. Le remonter devient un sujet 0.8.0, à valider à l'écran |
| D3 | `VectorStore.get_chunks` et `OPENSEARCH_DEFAULT_LIMIT` | Les supprimer ensemble | Un réglage documenté disparaît : entrée « Removed » au CHANGELOG |
| D4 | Carte de citation, désactivée par défaut | La garder : le choix est documenté et motivé | Seul point incertain : si le contrôle maintient 4.2 en échec sur elle seule, KISS reste à 83 et il faudra choisir entre la retirer et accepter la note |

### Lot 3 — Clean Code, 72 → 94

Il faut 17 points sur 18 : l'item 3.2.1, plus deux des trois items de comptage. Le plan vise 3.2.2 et 3.2.3 et laisse 3.3.1.

**3a. Item 3.2.1 — les deux fonctions Neo4j.** Découper `write_document` (227 lignes) et `fetch_graph` (115 lignes) sous un test de caractérisation : un faux pilote enregistre chaque requête Cypher et ses paramètres avant le découpage, et la séquence doit être identique après. Aucun serveur Neo4j n'est nécessaire. L'autre voie, sortir `infra/neo4j/` du périmètre par écrit, reste possible mais ne corrige rien.

**3b. Item 3.2.2 — 65 fonctions de plus de 30 lignes.** Extractions pures, sans changement de comportement, un commit par couche.

| Périmètre | Nombre | Remarque |
|-----------|--------|----------|
| Python | 45 | 21 font entre 31 et 40 lignes, 11 dépassent 60 (`builder.build` 117, `write_chunks` 107, `build_mcp_server` 87, `Settings.from_env` 85) |
| Frontend | 20 | Une de 216 lignes (`GraphView.renderGraph`), les autres entre 31 et 70 |

**3c. Item 3.2.3 — 45 signatures de plus de 4 paramètres.**

| Groupe | Nombre | Traitement |
|--------|--------|------------|
| Signatures métier | ≈ 28 | Objets valeur : `StoreDraft` et `StoreUpdate` (signatures de 9 et 10 paramètres), `ChunkReplacement` (5 signatures d'un coup), un objet de requête pour `read_element`, etc. |
| Constructeurs d'injection | 13 | De 5 à 10 collaborateurs. Passer sous 5 demande soit des paquets de dépendances artificiels, que l'audit KISS relèverait, soit un redécoupage des services, hors 0.7.4 |
| Signatures imposées | 4 | Trois routes FastAPI et l'outil MCP `read_element`, dont les paramètres sont le contrat public |

**D5.** Préciser l'item 3.2.3 de la fiche comme l'est déjà le 3.2.2 (« hors boilerplate inévitable ») : hors constructeurs d'injection et signatures imposées par FastAPI ou MCP. Sans cette précision, l'item reste en échec quoi qu'on fasse de raisonnable et Clean Code plafonne à 89. La fiche est celle du mainteneur ; la modification serait notée dans le rapport, puisqu'elle change la règle de mesure par rapport aux audits précédents.

**3d. Item 3.3.1 — 47 fichiers de plus de 300 lignes : laissé.** 27 sont des composants Vue, style compris. Les découper sans regarder l'écran est le changement le plus risqué de toute la campagne. Sujet 0.8.0.

### Lot 4 — Contrôle

Suites complètes quand la machine est calme, puis nouvel audit 03, 04 et 11 par des auditeurs qui n'ont pas écrit le code, et mise à jour de la synthèse. Les trois cycles précédents ont chacun introduit des régressions que seul ce contrôle a vues.

---

## 4. Ordre et risques

Ordre : 2a, 2b, 3a, 3b, 3c, contrôle, puis le freeze.

- **Volume.** La documentation tient en un commit et KISS est surtout de la suppression. Clean Code est le gros du travail : environ 65 extractions et 28 signatures, du même ordre que la seconde remédiation.
- **Non vérifiable ici.** Les fonctions de dessin (`GraphView.renderGraph`, `BboxOverlay.draw`, `BboxCanvas.draw`, `PdfPageCanvas.render`) n'ont pas de test visuel : à regarder à l'écran, comme le reste de la branche.
- **Contrat.** Le document OpenAPI est comparé avant et après chaque lot, comme aux cycles précédents. Seuls D1 et D3 le changent, volontairement.
- **Rien n'est poussé.** Commits locaux, sans réécriture des commits existants.
