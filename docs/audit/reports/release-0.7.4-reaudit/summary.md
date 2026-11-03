# Synthèse de re-audit — Release 0.7.4

**Date** : 2026-11-03
**Branche** : `claude/nifty-turing-fmn3wo`, branche qualité tirée de `release/0.7.4` (`1de1929`)
**Auditeur** : claude-code

Trois états ont été audités, dans l'ordre :

| État | Commit | Rapports |
|------|--------|----------|
| 1er audit | `1de1929` (code = tag `v0.7.3`), rapports en `e6047c2` | `docs/audit/reports/release-0.7.4/` |
| Re-audit, après deux passes de remédiation | `a4d9679` | corps des rapports de ce dossier |
| Vérification post-correctifs, après une troisième passe ciblée | `3f1d1cb` | section « Addendum » en fin des rapports 02, 05, 06, 07, 08, 09, 11 et 12 |

01, 03, 04 et 10 n'ont pas d'addendum : la troisième passe ne touchait pas leurs items. Leur score de re-audit est le score final.

---

## Tableau de bord

| #  | Audit                  | 0.7.4 | Re-audit | Final (`3f1d1cb`) | CRIT | MAJ | Verdict final |
|----|------------------------|-------|----------|-------------------|------|-----|---------------|
| 01 | Hexagonal Architecture | 78    | 97       | **97**            | 0    | 0   | GO |
| 02 | DDD                    | 92    | 94       | **100**           | 0    | 0   | GO |
| 03 | Clean Code             | 39    | 56       | **56**            | 0    | 2   | **NO-GO** (score) |
| 04 | KISS                   | 75    | 83       | **83**            | 0    | 1   | GO |
| 05 | DRY                    | 67    | 100 (83 en lecture stricte) | **100** (les deux lectures) | 0 | 0 | GO |
| 06 | SOLID                  | 87    | 100      | **100**           | 0    | 0   | GO |
| 07 | Decoupling             | 94    | 94       | **100**           | 0    | 0   | GO |
| 08 | Security               | 97    | 100      | **100**           | 0    | 1   | GO |
| 09 | Tests                  | 93    | 93       | **93**            | 0    | 1   | GO |
| 10 | CI / Build             | 85    | 100 (provisoire) | **100** (provisoire) | 0 | 0 | GO (provisoire) |
| 11 | Documentation          | 72    | 56       | **72** avant gel, **100** après gel | 1 → 0 | 1 → 0 | NO-GO avant gel → GO |
| 12 | Performance            | 67    | 90       | **100**           | 0    | 0   | GO |

**Score global** (moyenne simple des 12 scores, même méthode que les releases précédentes) :

| État | Score | CRIT | MAJ |
|------|-------|------|-----|
| 1er audit 0.7.4 | **79** | 1 | 22 |
| Re-audit (`a4d9679`) | **89** | 2 | 10 |
| Final avant gel (`3f1d1cb`) | **92** | 1 | 6 |
| Final après le commit de gel | **94** | 0 | 5 |

**Réserve sur 10.** Aucun run CI ni Release Gate n'a encore tourné sur la branche. Lu strictement, 10.1.1 tombe tant que le gate n'est pas vert : 10 vaudrait alors 85, avec 1 CRIT, et le score global perdrait un peu plus d'un point.

**Gates locaux sur `3f1d1cb`** :
- backend : ruff et ruff format OK (232 fichiers), `uv lock --check` OK, pytest **1723 passed, 19 skipped** (1323 au 1er audit) ;
- frontend : eslint, prettier et vue-tsc OK, vitest **53 fichiers, 522 passed** (545 au 1er audit : les tests de code mort supprimé sont partis avec lui), build OK ;
- `npm audit --omit=dev` : 0 vulnérabilité (7 HIGH au 1er audit) ;
- actionlint : 0 erreur ; `mkdocs build --strict` OK.

---

## Ce que la remédiation a changé

132 commits depuis l'audit. Le détail est dans `CHANGELOG.md` `[Unreleased]`. Points saillants :

- **Sécurité.**
  - Import Docling borné : des grilles déclarées avec moins de 1 Ko faisaient tomber le backend (démontré). Le budget compte désormais les tables, les graphiques des images et les lignes sans colonnes, sur le JSON brut, et le corps est plafonné à 50 Mo.
  - Garde SSRF sur les URI de stores, au test comme au push.
  - Les identifiants Neo4j de l'environnement ne partent plus vers une URI choisie par l'appelant (démontré avec un faux serveur Bolt ; défaut présent depuis 0.6.1).
  - Le rate limiter ne se contourne plus par `X-Forwarded-For`.
  - Le convertisseur local est limité au PDF.
  - npm : 7 HIGH → 0. torch et torchvision sont bornés.
- **Performance** (mesures dans les rapports 12).
  - Rechunk de 500 chunks : 4,6 s → 0,1 s ; restore : 4,5 s → 0,06 s, en une transaction atomique.
  - Rendu de page sans copie du PDF : −48 Mo écrits par page et −40 % de mémoire sur un PDF de 48 Mo.
  - Liste des versions en SQL.
  - Listes d'analyses sur `/summaries`.
  - nginx : gzip et cache des assets ; logo 879 Ko → 57 Ko.
- **Architecture.**
  - Ports complets, et plus aucun import `infra` ou `persistence` dans `services/` (garde AST).
  - Ports PDF et de stockage fichier.
  - Règles métier ramenées dans le domaine : split/merge, hash, citations, budget de lecture, arbre du document.
  - Contrat d'erreur unique service → HTTP.
  - `chunk_service.py` passe de 1 045 à 311 lignes.
- **CI.**
  - L'image `local` publiée (reasoning) est construite, scannée et démarrée par le gate.
  - `pipefail` sur les tests ; contrôle de format en CI.
  - Specs Karate UI purgées et rebasées. Un bug rendait **tous** les uploads UI en échec (`driver.inputFile`) ; il est corrigé.
- **Documentation.**
  - Toutes les variables lues sont documentées.
  - Glossaire du domaine.
  - Section `SECURITY.md` sur les stores et l'import.
  - CHANGELOG `[Unreleased]` complet, avec 5 changements cassants identifiés.

---

## Écarts encore ouverts

### CRITICAL (1, levé par le gel)

1. **[11.1.1]** `CHANGELOG.md` est en `## [Unreleased]`, pas en `## [0.7.4] - <date>`. C'est l'étape de gel (`docs/maintainers.md`), faite au moment du tag.

### MAJOR (6 avant gel, 5 après)

| Audit | Écart | Nature | Piste |
|-------|-------|--------|-------|
| 11 | `frontend/package.json` et son lockfile en `0.7.3` | Gel | `npm version 0.7.4 --no-git-tag-version`, dans le commit de gel |
| 08 | `/api/*` ne contrôle pas `Host` (DNS rebinding contre une instance locale) | **Décision du mainteneur** : une liste blanche par défaut casse l'accès par IP LAN ou par nom | Opt-in en 0.7.4, défaut avec l'authentification en 0.8.0 |
| 04 | Carte MCP `show_citation`, désactivée par défaut, 1 177 lignes (item 4.2) | **Décision du mainteneur** : la retirer, ou nommer dans la doc le besoin qui la justifie | Retrait (M) ou justification écrite → 04 à 100 |
| 03 | Textes français en dur dans les cartes MCP (item 3.1.3) | **Décision produit** (français assumé depuis 0.7.3) | Table `{ en, fr }` (M) |
| 03 | 2 fonctions multi-responsabilités dans le code Neo4j déprécié (`infra/neo4j/tree_writer.py:69`, `queries.py:137`) | Code retiré en 0.8.0 | Découpage (L) ou retrait anticipé de l'ingestion |
| 09 | Suite Karate UI sans preuve d'exécution complète (item 9.1.3) | Environnement | Les specs modifiées passent (8/8 en local, avec un faux Docling Serve). Il manque `UIRunner#testLocal` à 29/29 sur la stack documentée, rapport joint, ou un job `@regression` au gate |

L'audit 03 reste **NO-GO sur son score** (56). Les points manquants dépendent surtout de décisions :
- lecture de l'item 3.1.1 : « nom = valeur renvoyée » pour les fonctions pures, +5 points ;
- langue des cartes MCP (3.1.3) ;
- retrait de l'ingestion en 0.8.0, qui enlève une partie des fonctions longues, des signatures larges et des gros fichiers (3.2.2, 3.2.3, 3.3.1).

---

## Verdict

- **Avant gel : NO-GO**, à cause du seul CRIT 11.1.1, qui est l'étape de gel elle-même.
- **Après le commit de gel : GO CONDITIONNEL** au sens du master : score global **94** et **0 CRIT**, mais **5 MAJ**, donc plus que le seuil strict de 3.
  - 3 de ces MAJ attendent une décision du mainteneur (garde `Host`, carte `show_citation`, langue des cartes MCP).
  - 1 porte sur du code retiré en 0.8.0.
  - 1 attend une exécution de la suite Karate UI.
  - C'est le même traitement qu'en 0.7.3, partie avec 20 MAJ de dette (`docs/audit/reports/release-0.7.3-reaudit/summary.md`). La 0.7.4 en solde 17 sur 22.

### Étapes avant le tag

1. Fusionner cette branche dans `release/0.7.4`.
2. Trancher la PR #371 (issue #370), ouverte vers `release/0.7.4`. La 0.7.4 est annoncée comme « no new feature » : la reporter, ou lui ajouter une section `### Added`.
3. Ouvrir la PR `release/0.7.4` → `main` : le Release Gate et la CI tournent pour la première fois sur ce code. Points à surveiller :
   - les premiers Trivy sur le groupe `reasoning` ;
   - le nouveau smoke `local` avec `--network none` ;
   - le tokenizer HuggingFace téléchargé par les e2e `@critical` de rechunk hybride.
4. Ajouter `Docker smoke test — local` aux checks requis de `main` (action administrateur).
5. Lancer `UIRunner#testLocal` sur la stack documentée et joindre le rapport (audit 09).
6. Commit de gel : `[Unreleased]` → `[0.7.4] - <date>`, `npm version 0.7.4 --no-git-tag-version`.
7. Ouvrir l'issue « docling → Pillow 13 » : les suppressions de `.trivyignore.yaml` expirent le **2026-12-31**, et un gate lancé après cette date échoue.
8. Trancher les décisions ci-dessus, ou les inscrire au plan 0.8.0.

### Points relevés hors barème (pour 0.8.0)

- Code front non atteignable depuis `main.ts` : 15 modules, environ 3 000 lignes, dont toute l'UI des stores, `features/chunks/ui` et `ChunksPanel`. Le supprimer est une décision produit.
- Les règles pytestarch sur `domain`, `api`, `infra` et `persistence` ne vérifient rien ; seule la règle AST sur `services/` mord. À convertir en tests AST.
- Les imports Docling ne passent pas par le sémaphore des analyses : au plafond par défaut, un import coûte encore environ 10 s et 220 Mo.
- `AnalysisService` passe encore le chemin de stockage brut, sans `FileStorage.resolve`. L'impact se limite au développement hors Docker.
