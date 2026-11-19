# Plan d'amélioration — Release 0.7.4, troisième cycle

**Date** : 2026-11-19
**Point de départ** : audit de validation sur `efc0bc5`, global ≈ 87, 2 CRITICAL de procédure, 8 MAJOR ([summary.md](summary.md)).
**Règle** : corriger d'abord les défauts trouvés par les relectures, puis simplifier ce que la seconde remédiation a alourdi (audit 04), puis les corrections ponctuelles. Chaque lot est vérifié par les suites quand la machine est calme.

---

## 1. Lots de ce cycle

| Lot | Contenu | Audits visés |
|-----|---------|--------------|
| A — Analyse courante cohérente | Supprimer l'analyse active resélectionne la dernière analyse terminée restante ; défauts D1, D2, D3, D5 de l'audit 02 ; noms `load_current_original` / `load_current_edited` au lieu de « current » et « active » pour deux contenus ; la dépendance toujours injectée devient obligatoire, trois branches de repli supprimées ; prédicat unique « une analyse terminée peut être courante » ; localisation de citation et choix de lecture déplacés dans le domaine ; suivi des champs modifiés de l'agrégat remplacé par des écritures explicites ; `show_sources` résout l'analyse une fois par appel ; l'export PDF résout le chemin | 01-1.2.3, 02-2.3.1, 04, 06 INFO, 12 |
| B — Simplifications | Façade `ChunkService` retirée : services construits dans le câblage, appelés par les routes ; garde `Host` réduit à une vérification du nom, réponse JSON, analyse stricte de l'en-tête ; modèles de payload de l'historique dérivés des modèles de requête ; réponse de l'éditeur construite hors de la boucle d'événements ; suppression et fusion de masse en temps linéaire ; enregistrement des commandes en un seul `executemany` ; code mort backend supprimé ; deux tests rétablis | 04-4.3, 04-4.5, 06 INFO 26, 08, 09 MIN, 12 |
| C — Frontend | Code mort supprimé après preuve fichier par fichier ; un document sans analyse courante n'en charge aucune ; un enregistrement refusé s'affiche dans un bandeau sans masquer l'éditeur ; reliquats sans effet | 02 D4, 03, 04, 07 |
| D — CI, e2e, documentation | Le gate ne publie plus de verdict sur un run annulé et tout ce qui n'est pas un succès bloque ; jeton en lecture seule pour le gate ; le scénario PDF.js nomme ses sélecteurs ; corrections de la documentation et du CHANGELOG relevées par l'audit 11 | 08 MIN, 10 INFO, 11 |

---

## 2. Décisions laissées au mainteneur

| Sujet | Ce que l'audit propose | Pourquoi ce n'est pas fait d'office |
|-------|------------------------|-------------------------------------|
| 08 MAJ, garde `Host` désactivé par défaut | Mettre `API_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,[::1]:*` par défaut dans les fichiers compose | Coupe l'accès par nom de machine ou adresse IP sur le réseau local pour toute installation qui ne règle pas la variable |
| 03 MAJ, deux fonctions Neo4j de 227 et 115 lignes | Les découper, ou sortir `infra/neo4j/` du périmètre d'audit puisque le module part en 0.8.0 | Leurs tests demandent un serveur Neo4j que ni la CI ni ce poste ne lancent : un découpage ne serait vérifié par rien |
| 04 MAJ, « plomberie de l'éditeur » | Retirer la route `rebuild`, le champ `engine_version`, les champs `warnings` et `reference_changes` | Fonctionnalités de la PR #319 d'un contributeur, listées dans le CHANGELOG de la release |
| 07 MAJ, `StoreResponse.config` et `GraphNode` non typés | Les typer | Configuration ouverte par conception pour le premier, module Neo4j promis au retrait pour le second |
| 09 MAJ, specs Karate UI | Les lancer, puis marquer `@critical` le scénario PDF.js | Jamais exécutées : en faire un critère bloquant du gate avant de les avoir vues passer bloquerait la release sur un test non éprouvé |
| 12, WAL et `busy_timeout` pour SQLite | `PRAGMA journal_mode=WAL` | Change les fichiers de la base (`-wal`, `-shm`) et donc la consigne de sauvegarde documentée |
| Ask et les éditions | Mention dans le panneau Ask quand l'analyse a des éditions enregistrées | Ajout d'interface à valider à l'écran |
| Tiroir d'historique | `HistoryDrawer.vue`, le chemin « workspace » du store de documents et la spec `doc-history-drawer.feature` ne sont atteints par aucun écran depuis la 0.7.3 : les supprimer, ou remonter le tiroir | Code mort ou fonctionnalité perdue : seul le mainteneur le sait. Tant que rien ne le monte, restaurer une version passe par l'API |
| Suppression de masse dans l'éditeur | Aperçu incrémental à partir du cache enregistré, ou contournement du `delete_items` quadratique de Docling | Effort moyen, à mesurer d'abord sur un vrai document ; le correctif propre est en amont, dans docling-core |
| `VectorStore.get_chunks` et `OPENSEARCH_DEFAULT_LIMIT` | Les supprimer ensemble : le réglage ne borne que cette méthode, que rien n'appelle | Retire un réglage documenté |
| Autre code sans appelant | `DocumentMerger` et `infra/docling_merger.py`, `DocumentStoreLink.mark_stale`, `StaleStoresStrip.vue`, `rebuildAnalysisEdits` côté frontend | Relevé au contrôle final, hors de la liste initiale ; à vérifier avant suppression |
| Journal SQLite | `PRAGMA journal_mode=WAL`, `busy_timeout` explicite, index partiel pour la resélection après suppression | Voir la ligne WAL ci-dessus |

---

## 3. Toujours à faire par le mainteneur

Inchangé depuis le [plan du 18/11](../release-0.7.4-reaudit/remediation-plan.md) : lancer l'application et regarder les écrans, pousser la branche et obtenir une CI verte, trancher la PR #403, faire le commit de freeze, obtenir un Release Gate vert, protéger `release/**`, fermer ou redater #378 avant le 2026-12-31.

Vérifications à la charge de protection de branche, d'après l'audit 10 : `Backend tests`, `Frontend tests & build`, `E2E API tests (Karate)` sur `release/**` ; les mêmes plus `Backend tests (docling)` sur `main`.

---

## 4. Résultat du cycle

Les quatre lots sont faits, contrôlés et, pour trois audits, retouchés puis recontrôlés. Détail dans la [synthèse du contrôle final](../release-0.7.4-final/summary.md).

| Audit | Validation | Final | Remarque |
|-------|------------|-------|----------|
| 01 Hexagonal Architecture | 91 | 97 | Plus de MAJ |
| 02 DDD | 89 | 89 | Défauts D1 à D5 corrigés ; le MAJ de vocabulaire reste en lecture stricte |
| 03 Clean Code | 72 | 72 | 61 au premier passage, deux items perdus par le cycle puis regagnés |
| 04 KISS | 67 | 75 | 58 au premier passage, à cause de modèles générés par méta-programmation, réécrits à la main |
| 08 Security | 97 | 97 | Garde `Host` réécrit, sans contournement trouvé |
| 09 Tests | 81 | 93 | Suites vertes, aucun test perdu sur du code existant |
| 11 Documentation | 67 | 72 | 100 après le freeze |
| 12 Performance | 95 | 95 | Deux régressions de la validation résolues |
| Global | ≈ 87 | ≈ 89 | ≈ 93 après CI verte et freeze |

Vérifié sur `707a486`, machine calme : backend ruff propre et 1789 tests passés ; frontend eslint, prettier et `vue-tsc` propres, 604 tests passés, build réussi.
