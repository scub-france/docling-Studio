# Synthèse du contrôle — Release 0.7.4, après le plan 90

**Date** : 2026-11-20
**Branche** : `fix/0.7.4-editor-followups`, non poussée.
**Auditeur** : claude-code
**Objet** : mesurer l'effet du [plan 90](../release-0.7.4-final/plan-90.md) sur les audits 03, 04 et 11, et vérifier que le refactoring n'a rien fait régresser ailleurs.

**Commits contrôlés**
- Premier passage sur `8dc0623` : audits 03, 04, 11 et contrôle de non-régression sur 01, 05, 06, 09.
- Recontrôle des audits 03 et 04 sur `513e8f9`, après correction de ce que le premier passage avait trouvé.
- Second puis troisième recontrôle de l'audit 04 sur `3ba8cf9` et `520aaf6`, après la suppression du code frontend des stores, puis de l'éditeur de chunks, décidées par le mainteneur.
- `6295dc0` corrige trois remarques sans effet sur la note.
- 02, 07, 08, 10 et 12 n'ont pas été recontrôlés : ils gardent leur dernière note.

**Suites exécutées**, machine calme : backend sur `6295dc0`, `ruff check` et `ruff format --check` propres, `pytest` 1776 passés et 15 ignorés ; frontend sur `520aaf6`, eslint, prettier et `vue-tsc` propres, vitest 517 passés sur 67 fichiers, `vite build` réussi. Le document OpenAPI est identique octet pour octet à celui d'avant les refactorings de l'audit 03.
**Non exécuté** : l'application, Docker, nginx, les e2e Karate, les tests `tests/neo4j/` (ils demandent un serveur), les workflows.

---

## Tableau de bord

| #  | Audit                  | Final (`707a486`) | Premier passage (`8dc0623`) | Après corrections | Ce qui reste |
|----|------------------------|-------------------|-----------------------------|-------------------------------|--------------|
| 03 | Clean Code             | 72                | 78                          | **94** (`513e8f9`)            | 3.3.1 : 47 fichiers de plus de 300 lignes, 42 depuis `520aaf6` |
| 04 | KISS                   | 75                | 75                          | **100** (`520aaf6`)           | rien ; 83 à `513e8f9` et `3ba8cf9` |
| 11 | Documentation          | 72                | 72                          | 72 (**100** après le freeze)  | 11.1.1 et 11.2.1 : le commit de freeze |
| 01 | Hexagonal Architecture | 97                | 97                          | non recontrôlé                | — |
| 05 | DRY                    | 100               | 100                         | non recontrôlé                | — |
| 06 | SOLID                  | 100               | 100                         | non recontrôlé                | — |
| 09 | Tests                  | 93                | 93                          | non recontrôlé                | 9.1.3 : les specs Karate UI n'ont jamais tourné |

**Score global** : **≈ 93 / 100** (93,0), contre 89 au contrôle final. Avec le commit de freeze : ≈ 95. Avec une CI verte sur la PR (audit 10) : ≈ 97.
**Écarts CRITICAL** : 2, inchangés et de procédure (10.1.1 CI jamais passée sur la tête de release, 11.1.1 CHANGELOG non figé).

---

## Ce que le plan a fait

**KISS.** Les écarts du contrôle final sont levés, preuve à l'appui dans le [rapport 04](04-kiss.md) :
- `API_ALLOWED_HOSTS` est une liste de noms seuls, avec une seule fonction d'analyse ; la limite d'import est une constante ; `OPENSEARCH_DEFAULT_LIMIT` et `VectorStore.get_chunks` sont supprimés.
- Éditeur : la route et le client `rebuild`, les champs `warnings` et `reference_changes` et le second protocole de déplacement (`beforeElementId`) sont supprimés. La version du moteur est comparée au chargement et estampillée à chaque sauvegarde.
- Frontend : le tiroir d'historique, le chemin « workspace » du store de documents et l'édition de chunk du panneau Propriétés, qu'aucun écran n'atteignait, sont supprimés. Sur décision du mainteneur, deux blocs restés sans écran depuis juillet le sont aussi : la gestion des stores (`features/store`, `StatusBadge.vue`) et l'éditeur de chunks d'un document (`features/chunks`), avec 206 clés de traduction par langue que plus rien ne lisait. −4 431 lignes de production. Un parcours du graphe des imports depuis `app/main.ts` atteint désormais tous les fichiers de production du frontend.

**Clean Code.** Voir le [rapport 03](03-clean-code.md) :
- Plus aucune fonction de plus de 30 lignes, backend et frontend : 65 → 0. Les deux fonctions Neo4j de 227 et 115 lignes sont découpées sous un test qui fige les requêtes Cypher et leurs paramètres.
- Signatures de plus de 4 paramètres : 45 → 15, toutes couvertes par la précision apportée à l'item 3.2.3 (11 constructeurs d'injection, 3 routes FastAPI, 1 outil MCP). Sans cette précision, il en serait resté 31 au départ : le code en a retiré 29 de lui-même.
- Tous les noms ajoutés (166 fonctions, une quinzaine d'objets valeur) sont jugés conformes.

**Documentation.** Tout le contenu est conforme ([rapport 11](11-documentation.md)). Six corrections de texte relevées par l'audit sont faites, dont une phrase fausse dans `.env.example` et une dans le CHANGELOG.

## Ce que le contrôle a corrigé dans le plan lui-même

Comme aux cycles précédents, le premier passage a trouvé des défauts créés par le travail qu'il contrôlait. Tous sont corrigés et recontrôlés.

| Origine | Défaut | Correction |
|---------|--------|------------|
| 03 | Deux fonctions extraites cachaient une écriture derrière leur nom (`_plan_batches`, `_clear_document_chunks`) | Planification redevenue pure ; création du nœud dans sa propre étape |
| 03 | Deux constructeurs faisaient plus que recevoir leurs collaborateurs | Délai et concurrence dans `AnalysisConfig` ; plafond en octets en propriété de `DocumentConfig` |
| 04 | Le nettoyage du tiroir laissait le mode édition du panneau Propriétés sans parent, et un fragment Karate qui passait sans rien vérifier | Supprimés |
| 04 | Un objet valeur portait trois champs jamais renseignés (`GraphDocument`) | Supprimé ; `write_document` reprend ses trois arguments |
| 04 | Deux relais introduits par le découpage : la façade `mcp_adapter.build_mcp_server` et le planificateur d'aperçu | Façade supprimée ; planificateur réécrit en une classe simple |
| Non-régression | Une version de moteur plus ancienne aurait fait rejouer le flux à chaque chargement, sans fin | La sauvegarde estampille le flux |
| Non-régression | `IngestionSource` importée à l'exécution depuis un service pair | Déplacée dans le domaine |
| Non-régression | Deux cas sans test, et un instantané Neo4j qui passait toujours en mode mise à jour | Tests ajoutés ; le mode mise à jour échoue explicitement |

---

## Décisions pour le mainteneur

| Sujet | Constat | Effet |
|-------|---------|-------|
| API de chunks de document | `api/document_chunks.py` (11 routes : CRUD, fusion, découpe, diff, push), `ChunkService` et `ChunkPushService` n'ont plus aucun client dans le dépôt, ni frontend ni MCP. Une spec Karate les couvre. L'auditeur les classe comme une API légitime, au même titre que l'API de versions et `/api/stores/*` | « API publique ou reste » : si c'est un reste, elle retombe sous l'item 4.2 |
| Commit de freeze | Il manque la date de release | Documentation passe de 72 à 100, un CRITICAL levé |
| Lecture de l'item 3.2.3 | Le constructeur d'`AnalysisService` crée encore son sémaphore à partir de la configuration reçue. L'auditeur l'a exempté et le dit : c'est une appréciation | En lecture stricte, Clean Code vaut 89 au lieu de 94 |
| Règle de sélection après un rechunk | Elle n'a plus de forme exécutable dans le domaine : elle est énoncée par le contrat du port et appliquée par l'écriture | En lecture stricte de 1.2.3, l'audit 01 vaut 91 au lieu de 97 |
| `docs/demo/video/mcp-card/record.py` | Le script importe une fonction supprimée. Il était déjà cassé avant ce cycle (anciennes signatures) | À supprimer ou à réécrire |

Les décisions déjà listées dans le [plan d'amélioration](../release-0.7.4-validation/improvement-plan.md) et non traitées ici restent ouvertes : valeur par défaut d'`API_ALLOWED_HOSTS`, PR #403, WAL pour SQLite, suppression de masse lente dans l'éditeur, `@critical` sur le scénario PDF.js.

## Changements de comportement à connaître

Aucun ne touche une version publiée : ce qui disparaît n'existait que sur la branche 0.7.4, sauf `OPENSEARCH_DEFAULT_LIMIT`.

- `API_ALLOWED_HOSTS` : une entrée avec un port, une URL ou `*` est ignorée et nommée dans le log de démarrage. `*` ne désactive plus le contrôle : pour le désactiver, laisser la variable vide.
- `MAX_IMPORT_SIZE_MB` n'est plus un réglage : un import est limité à 200 Mo.
- `OPENSEARCH_DEFAULT_LIMIT` est ignoré s'il est encore défini.
- Éditeur : plus de route `rebuild` ; `moveElement` exige `targetElementId` et `placement` ; la réponse n'a plus `warnings` ni `referenceChanges`.
- Le cache d'aperçu du serveur est borné à 16 Mo au lieu de 64.

## Points non vérifiés

- **Rien n'a été regardé à l'écran**, ni dans ce cycle ni depuis le 18/11. Les suppressions de `features/store` et `features/chunks` reposent sur le graphe des imports, pas sur une visite de l'application. S'ajoutent cette fois toutes les fonctions de dessin découpées (graphe, surcouches de bbox, canevas PDF), la vue Parse après le retrait du chemin « workspace », et le panneau Propriétés.
- Les écritures Neo4j ne sont vérifiées que par la séquence des requêtes envoyées à un faux pilote, pas contre un serveur. Les tests `tests/neo4j/` ont été adaptés à la main et seulement compilés.
- Les specs Karate UI, dont celle du panneau Propriétés modifiée dans ce cycle, n'ont jamais tourné.
- 02, 07, 08, 10 et 12 n'ont pas été recontrôlés après un refactoring qui touche une centaine de fichiers.

---

## Verdict : **NO-GO formel, par les deux CRITICAL de procédure**

Objectif du plan : Clean Code est à 94, KISS à 100, Documentation sera à 100 au freeze.

Pour un GO, dans l'ordre : lancer l'application et regarder les écrans ; pousser la branche et obtenir une CI verte ; faire le commit de freeze ; obtenir un Release Gate vert.
