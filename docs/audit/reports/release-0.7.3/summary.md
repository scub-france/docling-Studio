# Synthèse d'audit — Release 0.7.3

**Date** : 2026-11-02
**Branche** : `release/0.7.3` au commit `02adc68` (merge de la PR #328, serveur MCP)
**Auditeur** : claude-code
**Périmètre de la release** : figé par le mainteneur à `02adc68`. Les PR #350, #351 et #319, ainsi que les issues #348, #349 et #358, sont reportées et ne sont pas comptées comme des manques.
**Baseline** : re-audit 0.7.0 (`docs/audit/reports/release-0.7.0-reaudit/`) pour 05, 07, 08, 09, 11 et 12 ; 1er audit 0.7.0 (`docs/audit/reports/release-0.7.0/`) pour les autres. La 0.7.1 et la 0.7.2 n'ont pas été auditées.

---

## Tableau de bord

| #  | Audit                  | Score (0.7.0 → 0.7.3) | CRIT | MAJ | MIN | INFO | Verdict         |
|----|------------------------|-----------------------|------|-----|-----|------|-----------------|
| 01 | Hexagonal Architecture | 78 → **78**           | 0    | 3   | 1   | 6    | GO CONDITIONNEL |
| 02 | DDD                    | 100 → **92**          | 0    | 1   | 6   | 5    | GO              |
| 03 | Clean Code             | 61 → **44**           | 0    | 3   | 4   | 8    | **NO-GO** (score) |
| 04 | KISS                   | 83 → **75**           | 0    | 1   | 2   | 7    | GO CONDITIONNEL |
| 05 | DRY                    | 67 → **67**           | 0    | 3   | 10  | 5    | GO CONDITIONNEL |
| 06 | SOLID                  | 100 → **87**          | 0    | 2   | 0   | 10   | GO              |
| 07 | Decoupling             | 94 → **89**           | 0    | 2   | 0   | 12   | GO              |
| 08 | Security               | 97 → **89**           | 1    | 2   | 5   | 5    | **NO-GO** (CRIT) |
| 09 | Tests                  | 100 → **93**          | 0    | 1   | 3   | 8    | GO              |
| 10 | CI / Build             | 85 → **70**           | 1    | 1   | 1   | 8    | **NO-GO** (CRIT) |
| 11 | Documentation          | 100 → **44** (72 au même stade pré-gel en 0.7.0) | 2 | 2 | 0 | 7 | **NO-GO** (CRIT) |
| 12 | Performance            | 86 → **52**           | 0    | 3   | 6   | 6    | **NO-GO** (score) |

**Score global** : **73 / 100**, moyenne simple des 12 scores, même méthode qu'en 0.7.0. C'était 83 au 1er audit 0.7.0 et 88 après remédiation.
**Écarts CRITICAL** : **4 entrées, 3 causes distinctes**. Les CRIT de 08 et de 10 ont la même cause.
**Écarts MAJOR** : **24 entrées**, dont plusieurs se recoupent : PDF hors port (01 et 06), `chunk_service` (01, 03 et 12), import #359 bloquant (12 ; même import sans plafond de taille en MIN dans 08).

État de la branche au moment de l'audit :
- Tests unitaires verts : backend 1386 passed, 0 failed, 15 skipped (Neo4j absent) ; frontend 545 passed.
- Gates statiques locaux verts : ruff, ruff format, `uv lock --check`, eslint, prettier, vue-tsc, vite build, `mkdocs build --strict`.
- Le Release Gate GitHub de la PR #366 (`release/0.7.3` → `main`), run `41452005966`, est **en échec**.

---

## Écarts CRITICAL (tous audits confondus)

1. **[08 + 10] Release Gate rouge : le scan Trivy CRITICAL échoue sur l'image `remote`.**
   - **Suppressions expirées** : 5 des 7 suppressions de `.trivyignore.yaml` sont expirées, aux lignes `.trivyignore.yaml:25` (2026-08-31), `:40` et `:52` (2026-09-30), `:67` et `:81` (2026-10-31). Les 2 dernières, `:13` et `:93`, expirent le 2026-11-30.
   - **Run** : vérifié sur le run `41452005966`. `Security scan — remote` est en `failure` au pas bloquant (`exit-code: 1`, `severity: CRITICAL`) et `Security scan — local` est `cancelled` par le fail-fast. **L'image `local` publiée n'a donc pas été scannée.**
   - **CVE en cause** : vérifiées dans les artefacts `trivy-remote` et `trivy-local` du run. Ce ne sont **pas** les suppressions expirées, mais des paquets corrigeables :
     - PyJWT 2.13.0 (CVE-2026-102268, contournement d'authentification, corrigé en 2.14.0) ;
     - certifi 2026.7.22 (GHSA-6q48-6c7w-9gw2) ;
     - **Pillow 10.4.0** (CVE-2026-112393, -112398, -112403, -112900, corrigées en **13.0.0**) ;
     - le paquet `uv` 0.11.6 (GHSA-hq85-5cpj-mr62) ;
     - le crate `zip` 8.1.0 embarqué dans `/usr/local/bin/uv` et `uvx` (CVE-2026-115905).

     Côté OS, seule CVE-2026-6653 (libxml2, image `local`) réapparaît. Les 4 autres suppressions expirées ne sont plus détectées, parce que Debian a publié les correctifs.
   - **Pillow 13 exige la dernière génération de docling** : `docling-core` ≥ 2.104, `docling-parse` ≥ 7.22.4, `docling-ibm-models` ≥ 4.0.4 et `docling-slim` ≥ 2.142, toutes publiées en octobre 2026, alors que le lock actuel est sur docling-parse 5.11 et docling-ibm-models 3.13.
   - Voir `08-security.md` et `10-ci-build.md` ; `.github/workflows/release-gate.yml:352`.

2. **[11] `[Unreleased]` n'est pas figé en `[0.7.3] - <date>`** — `CHANGELOG.md:7`.
   C'est l'étape normale de préparation (`docs/maintainers.md:21-24`). Elle reste bloquante selon l'item 11.1.1, de poids 3.

3. **[11] Le passage de `ASK_MODE` à `hidden` par défaut n'est pas signalé comme breaking change** — `CHANGELOG.md:19`.
   - **Effet** : après la mise à jour, l'onglet Ask et Settings › Reasoning disparaissent pour les opérateurs qui avaient activé le reasoning.
   - **Ce qui manque** : le changement est documenté sous `### Changed`, avec la façon de revenir en arrière, mais pas identifié comme breaking (item 11.1.3, poids 3).
   - **Précédent** : la 0.6.1 avait rangé un changement de flag du même type sous BREAKING (`CHANGELOG.md:146`).
   - C'est une appréciation, gardée ici par cohérence avec les précédents. Le correctif tient en une ligne.

---

## MAJOR à traiter avant le tag (recommandation)

Le master bloque au-delà de 3 MAJ non résolus. Avec 24 MAJ, la grande majorité est de la dette déjà présente en 0.7.0, voire avant. Quatre MAJ concernent le comportement livré et méritent d'être traités, ou au moins tranchés, avant le tag.

| Audit | Écart | Localisation | Pourquoi maintenant |
|-------|-------|--------------|---------------------|
| 08 | **Le contrôle d'hôte de la MCP est contournable depuis le réseau.** `MCP_ALLOWED_HOSTS` est une protection DNS-rebinding qui compare l'en-tête `Host`, que n'importe quel client non-navigateur peut forger. nginx transmet le `Host` du client (`proxy_set_header Host $http_host`) et compose publie `3000:80` sur toutes les interfaces. Un client du LAN qui envoie `Host: localhost:3000` lit donc tous les documents. Le commentaire de `infra/settings.py:90-95`, le CHANGELOG et la doc affirment que ce contrôle réserve `/mcp` à localhost. | `bootstrap/mcp_mount.py:210-231`, `frontend/nginx.conf.template` (bloc `location = /mcp`), `docker-compose.yml:206` | La MCP est activée par défaut et sans authentification, et la doc promet une protection qui n'existe pas. |
| 10 | **`pip-audit` ne bloque jamais**, car son filtre sur `fix_versions` est cassé. Il signale notamment 4 CVE sur `mcp 2.1.1` (version verrouillée dans `uv.lock:1684`), corrigées en 2.2.0. Le détail de ces CVE n'a pas été revérifié. | `.github/workflows/release-gate.yml:139` | Ce paquet porte la nouvelle surface exposée. |
| 12 | **L'import Docling (#359) tourne sur l'event loop.** `deserialize` est synchrone, suivi des exports, sans `to_thread`, et sans plafond de taille (MIN dans 08). | `services/analysis_service.py:177` | Un gros JSON importé fige toute l'API. Le correctif tient en quelques lignes, et à lui seul il fait passer l'audit 12 de 52 à 67. |
| 11 | **Il manque au CHANGELOG #359** (import, `POST /api/analyses/import`) **et #323** (l'export d'une analyse sauvegardée respecte `analysisId`, page de détail en lecture seule). **`frontend/package.json` est encore en `0.7.2`.** | `CHANGELOG.md:9-28`, `frontend/package.json:3` | Ces deux points se règlent dans le commit de gel. |

### Dette reconduite depuis 0.7.0 (9 MAJ, aucun corrigé)

| Audit | Écart | Statut 0.7.3 |
|-------|-------|--------------|
| 01 | Règles split/merge dans `services/chunk_service.py:335` | Ouvert. Le même schéma réapparaît dans `services/citation_service.py:201` |
| 01 | Libs PDF hors port (`services/document_service.py:14`) | **Aggravé**. pypdfium2 est ajouté par #352, alors que le port `PageRasterizer` livré dans cette release n'est pas utilisé |
| 01 | Orchestration et I/O dans le routeur (`api/documents.py:40`) | **Aggravé** par la nouvelle route `/pages` (`:212`) |
| 03 | Fonctions d'orchestration multi-responsabilités (`chunk_service.py:574`) | Ouvert, fichier identique à 0.7.0 |
| 03 | God-file `chunk_service.py:146` | Ouvert, fichier identique à 0.7.0 |
| 04 | Abstraction LLM-provider prématurée (`domain/value_objects.py:167`) | Ouvert, inchangé, reporté pour la 2e fois |
| 05 | `_parse_iso` copié 7 fois, divergence UTC (`persistence/analysis_repo.py:11`) | Ouvert. Le nouveau `/summaries` hérite de la divergence |
| 05 | Couleurs UI en dur (`features/store/ui/StoreForm.vue:389`) | Ouvert, avec 3 littéraux de plus dans `McpConfigSection.vue` |
| 07 | `StoreResponse.config: dict` / `GraphNode extra=allow` (`api/schemas.py:349`, `api/graph.py:32`) | Ouvert. Surface d'ingestion dépréciée, supprimée en 0.8.0 |

### Nouveaux MAJ de dette (non bloquants pour ce tag, à planifier)

- **[01]** Voir le tableau ci-dessus : la nouvelle route `/pages` et le contournement du port PDF.
- **[02]** Le vocabulaire n'est pas unifié. « version » est un homonyme (un `version_id` d'ancre est un id d'AnalysisJob, distinct de `DocumentVersion`), et l'étape de la boucle s'appelle round, hop ou iteration selon le fichier (`domain/anchors.py:7` vs `domain/models.py:312`).
- **[03]** Les cartes MCP contiennent environ 64 textes français en dur, et `citation_app.html` déclare `lang="en"` (`mcp_adapter/sources_app.html:998`, `citation_app.html:395`). **Le français est un choix produit du mainteneur, fait pour la démo**, voir les décisions plus bas.
- **[05]** Le contrat d'erreur service → HTTP est copié : 6 bases `XServiceError` et 16 sites `HTTPException(exc.http_status)` (`services/navigation_errors.py:13`).
- **[06]** Des services appellent 13 méthodes absentes de leurs ports, et 4 services sont typés sur des classes `Sqlite*` (`services/version_service.py:87`). C'est antérieur à 0.7.0, mais jamais relevé jusqu'ici. Lu strictement, l'item 6.5.1 (poids 3) en ferait un CRIT. Le classement MAJ reprend la lecture du gate 0.7.0, faute de dépendance runtime.
- **[06]** `DocumentService` rend les PDF lui-même, en contournant `PageRasterizer` et `PageTextReader` (`services/document_service.py:14`). C'est le même constat que 01.
- **[07]** `ConfigSource`, partagé entre deux features, est rangé dans la feature `admin-config` au lieu de `shared/` (`features/admin-config/types.ts:2`).
- **[09]** Karate UI n'est pas vert dans son ensemble. 3 specs pilotent une UI supprimée (`documents/doc-ingest-view.feature:38`…), et les 8 features UI de 0.7.3, dont `navigation/mcp-config.feature`, ne tournent dans aucun workflow, car la CI ne lance que `@critical`.
- **[10]** La variante `local` publiée (reasoning, modèles, arm64) n'est ni construite ni scannée par le gate (`release-gate.yml:250` vs `release.yml:70-73`).
- **[12]** Chaque page rendue relit le PDF entier en mémoire, puis en écrit une copie temporaire (`infra/page_raster.py:27-28`). Cela touche les rasters MCP, `/preview` et `/pages`.
- **[12]** Les écritures de chunks font une connexion et un commit par chunk (`services/chunk_service.py:474-486`).
- **[08]** `/api/*` ne contrôle pas l'en-tête `Host`, ce qui ouvre au DNS rebinding contre une instance locale (`main.py:89-101`). C'était déjà le cas avant 0.7.3. L'exploitation dépend du navigateur, elle est plausible mais non démontrée.

---

## Quick wins

| Action | Effet | Effort |
|--------|-------|--------|
| **Commit de gel** : `[Unreleased]` → `[0.7.3] - <date>`, section `### BREAKING CHANGES` pour `ASK_MODE`, bullets #359 et #323, `frontend/package.json` → `0.7.3` | Lève 2 CRIT et 2 MAJ. L'audit 11 passe de 44 à 100 | 1 commit, aucun code |
| Mettre `mcp` à 2.2.0 dans `uv.lock` | Ferme 4 CVE signalées sur la surface MCP | 1 ligne + `uv lock` |
| Corriger le filtre `pip-audit` (`release-gate.yml:139`) | `pip-audit` ne fournit aucune sévérité. Le contrôle cesse donc de prétendre bloquer et devient un avertissement chiffré, et le blocage des CRITICAL Python reste assuré par Trivy (python-pkg) | Quelques lignes YAML |
| `asyncio.to_thread` autour de l'import #359 | Lève le MAJ 12-a. L'audit 12 passe de 52 à 67 | Quelques lignes |
| `citation_app.html` : `lang="en"` → `lang="fr"` | Supprime l'incohérence de langue | 1 ligne |
| Déplacer `ConfigSource` vers `shared/types.ts` | Lève le MAJ 07 | Imports seulement |
| Rafraîchir `.env.example:11-12` (périmé depuis #344) et les statuts des design docs 329, 363 et 364 | 3 INFO de l'audit 11 | Docs |

---

## Décisions attendues du mainteneur

1. **Trivy, puis Pillow.** Les montées sans risque (PyJWT, certifi, `uv`, mcp) sont faites sur la branche de remédiation. Il reste Pillow 10.4.0, avec 4 CRITICAL. Deux options :
   - (a) monter toute la famille docling à ses versions d'octobre 2026, qui autorisent Pillow 13 : c'est un gros saut, à valider sur de vrais documents ;
   - (b) accepter le risque jusqu'en 0.8.0, avec une suppression courte et justifiée honnêtement. Ces CVE ne peuvent pas être déclarées inatteignables : l'import #359 accepte un JSON Docling non fiable, qui peut embarquer des images.

   Dans les deux cas, il faut relancer le gate pour voir le résultat du scan `local`.

   **Décision du mainteneur (2026-11-02) : (b).** Les 4 CVE Pillow sont supprimées jusqu'au 2026-12-31 dans `.trivyignore.yaml`, avec une justification qui dit ce qui a été vérifié et ce qui ne l'a pas été. La montée docling vers Pillow 13 est prévue pour la 0.8.0.
2. **Exposition par défaut de la MCP.** Trois options :
   - corriger d'abord la doc et le commentaire, qui promettent une restriction à localhost que le code ne fournit pas ;
   - et/ou changer le défaut : publier le port compose sur `127.0.0.1`, ou mettre `MCP_ENABLED=false` en compose ;
   - et/ou ajouter une authentification, qui relève plutôt de la 0.8.0.
3. **Langue des cartes MCP.** Si le français est assumé, l'item 3.1.3 reste non conforme (textes UI en dur) et l'audit 03 reste NO-GO sur le score. Sinon, il faut passer les cartes par une table de libellés.
4. **Lecture de l'item 6.5.1 (SOLID, DIP).** Cette synthèse garde MAJ, comme en 0.7.0. Une lecture stricte en ferait un 4e CRIT.

---

## Verdict final : **NO-GO**

- 3 écarts CRITICAL distincts sont non résolus (4 entrées). La règle absolue du master s'applique.
- Le score global de 73 serait dans la zone GO CONDITIONNEL, mais 24 MAJ dépassent le seuil de 3.
- 4 audits sur 12 ont un score sous 60 ou un CRIT.

### Chemin vers le GO

1. Faire le commit de gel du CHANGELOG et le bump de version. L'audit 11 passe de 44 à 100, et deux CRIT sont levés.
2. Remettre le Release Gate au vert en traitant Trivy (décision 1). L'audit 10 passe de 70 à environ 85, l'audit 08 de 89 à 97, et le dernier CRIT est levé.
3. Estimation après les étapes 1 et 2 : **0 CRIT, score global ≈ 80**. Avec le `to_thread` de l'import #359, on arrive à **≈ 81**.
4. Corriger ou documenter honnêtement l'exposition de la MCP (décision 2), et monter `mcp` en 2.2.0. Ce sont des MAJ, mais ils portent sur la surface phare de la release.
5. Le reste des MAJ, dont les 9 de dette 0.7.0, part dans un plan de remédiation 0.8.0, conformément à la clause GO CONDITIONNEL du master.

Ensuite : re-audit ciblé des audits 08, 10, 11 et 12, puis merge de la PR #366, tag `v0.7.3`, et build des images par `release.yml`.

---

## Notes

- **Milestones GitHub incohérentes (INFO).** #348, #349 et #358 sont encore rattachées au milestone 0.7.3, alors qu'elles sont reportées : leur déplacement vers 0.8.0 reste à faire. Les issues MCP sont rattachées au milestone 0.8.0.
- **SemVer (INFO).** Cette version « patch » ajoute des routes, une dépréciation et un changement de comportement par défaut (`ASK_MODE`).
- **Test d'architecture inopérant (INFO, 01 et 06).** Les règles pytestarch de `tests/test_architecture.py` ne détectent rien : `TestPersistenceLayerIsolation` passe alors que `persistence/store_repo.py:25` importe `infra`. Le test le reconnaît lui-même dans sa docstring.
- **Couverture de lignes non mesurée.** Ni `pytest-cov` ni le provider de couverture vitest ne sont installés en local.
