# Synthèse du contrôle final — Release 0.7.4

**Date** : 2026-11-20
**Branche** : `fix/0.7.4-editor-followups`, non poussée. C'est `release/0.7.4` (`f7fc791`) plus les correctifs locaux, la fusion `a6fb539` et les trois cycles de remédiation des 18 et 19 novembre.
**Auditeur** : claude-code
**Objet** : mesurer l'effet du troisième cycle (le [plan d'amélioration](../release-0.7.4-validation/improvement-plan.md) issu de l'audit de validation).

**Commits contrôlés** :
- huit audits sur `a744f48` : 01, 02, 03, 04, 08, 09, 11, 12 ;
- 01, 03 et 04 une seconde fois sur `707a486`, après les retouches que leur premier passage demandait ;
- 05, 06, 07 et 10 n'ont pas été recontrôlés : ils gardent leur note de validation, mesurée sur `efc0bc5`, avant le troisième cycle.

**Suites exécutées sur `707a486`**, machine calme : backend `ruff check` et `ruff format --check` propres, `pytest` 1789 passés et 15 ignorés ; frontend eslint, prettier et `vue-tsc` propres, vitest 604 passés sur 71 fichiers, `vite build` réussi.
**Non exécuté** : l'application, Docker, nginx, les e2e Karate, Trivy, les workflows.

---

## Tableau de bord

| #  | Audit                  | 13/11 | Contrôle 18/11 | Validation 19/11 | Final | CRIT | MAJ | Verdict |
|----|------------------------|-------|----------------|------------------|-------|------|-----|---------|
| 01 | Hexagonal Architecture | 69    | 78             | 91               | **97** | 0   | 0   | GO |
| 02 | DDD                    | 75    | 83             | 89               | 89    | 0    | 1   | GO |
| 03 | Clean Code             | 39    | 61             | 72               | 72    | 0    | 1   | GO CONDITIONNEL |
| 04 | KISS                   | 75    | 75             | 67               | **75** | 0   | 1   | GO CONDITIONNEL |
| 05 | DRY                    | 67    | 83             | 100              | 100 (non recontrôlé) | 0 | 0 | GO |
| 06 | SOLID                  | 87    | 100            | 100              | 100 (non recontrôlé) | 0 | 0 | GO |
| 07 | Decoupling             | 91    | 94             | 94               | 94 (non recontrôlé) | 0 | 1 | GO |
| 08 | Security               | 97    | 97             | 97               | 97    | 0    | 1   | GO, si le Trivy du gate est vert |
| 09 | Tests                  | 85    | 93             | 81               | **93** | 0   | 1   | GO |
| 10 | CI / Build             | 85    | 75             | 85               | 85 (non recontrôlé) | 1 | 0 | NO-GO (CRIT de procédure) |
| 11 | Documentation          | 61    | 72             | 67               | **72** (100 après le freeze) | 1 | 1 | NO-GO avant le freeze |
| 12 | Performance            | 52    | 95             | 95               | 95    | 0    | 0   | GO |

**Score global** : **≈ 89 / 100** (89,1). Il était de 87 à la validation, 84 au contrôle du 18/11, 74 le 13/11.
**Écarts CRITICAL** : 2, les mêmes depuis le 18/11, tous deux de procédure.
**Écarts MAJOR** : 7. Il y en avait 8 à la validation, 14 au contrôle du 18/11, 24 le 13/11.
**Audits sous 60** : aucun.

Projection après une CI verte sur la PR et le commit de freeze : audit 10 à 100, audit 11 à 100, global ≈ 93, 0 CRITICAL.

---

## Ce que le troisième cycle a fait

- **Corrigé le défaut fonctionnel** trouvé par la validation : supprimer l'analyse active d'un document sélectionne la dernière analyse terminée restante, dans la même transaction. Ask, MCP et l'éditeur gardent quelque chose à lire.
- **Simplifié.** La façade `ChunkService` a disparu (13 paramètres de constructeur ramenés à 5), l'agrégat d'état est gelé avec des écritures explicites, trois branches jamais exécutées sont supprimées, le garde `Host` ne compare plus que le nom. 2 189 lignes de code mort retirées côté frontend, et le code mort backend que rien n'appelait.
- **Fermé les défauts des relectures** : export PDF qui ne résolvait pas le chemin, 500 au lieu de 409 sur une restauration ou un rechunk concurrents d'une suppression, réponse de l'éditeur construite sur la boucle d'événements, `show_sources` passé d'environ 300 à 105 requêtes pour 50 citations.
- **Durci le Release Gate** : un run annulé ne publie plus de verdict, et tout ce qui n'est pas un succès bloque.

## Ce que le contrôle a corrigé dans le cycle lui-même

Le premier passage du contrôle a fait baisser trois notes, à cause de choix du cycle. Les trois sont corrigés et recontrôlés :

| Audit | Premier passage | Cause | Après retouche |
|-------|-----------------|-------|----------------|
| 04 KISS | 58, NO-GO | Les modèles de payload étaient générés par une quarantaine de lignes de méta-programmation | 75 : sept classes écrites à la main, et un test qui compare leurs champs à ceux des requêtes |
| 03 Clean Code | 61 | Deux fonctions nommées par leur résultat et deux drapeaux booléens ajoutés par le cycle | 72 |
| 01 Architecture | 91 | En gelant l'agrégat, la règle de sélection après une restauration était passée dans un service | 97 : deux fonctions pures dans le domaine |

---

## Ce que ces travaux ont mis au jour

- **Le tiroir d'historique n'est monté par aucun écran.** Depuis la refonte de l'espace document en 0.7.3, restaurer une version n'est possible que par l'API. `HistoryDrawer.vue`, le chemin de chargement « workspace » du store de documents et la spec `doc-history-drawer.feature` sont du code mort ou une fonctionnalité perdue : la décision revient au mainteneur. La documentation ne présente plus la restauration comme un geste utilisateur.
- **La suppression de masse dans l'éditeur reste lente**, à cause du `delete_items` de Docling lui-même, quadratique. Le code du projet est linéaire. Estimation de l'audit 12 : 20 à 45 s pour supprimer 1 000 éléments d'un document de 300 pages, rejoués à chaque aperçu.
- **Trois specs Karate UI visaient des éléments disparus.** Deux sont réparées, la troisième est celle du tiroir d'historique.

---

## Écarts CRITICAL

1. **[10 — 10.1.1] Aucune CI n'a tourné sur la tête de `release/0.7.4`.** Se lève par une CI verte sur la PR de cette branche, puis sur le commit de merge.
2. **[11 — 11.1.1] CHANGELOG non figé.** Attend le commit de freeze.

## Écarts MAJOR restants

| Audit / item | Écart | Ce qui le lève |
|--------------|-------|----------------|
| 02-2.3.1 | Vocabulaire : deux ports nommés « current » et « active » pour deux contenus, l'homonyme « version » | Renommages, dont un touche le contrat MCP public. En lecture non stricte l'item est conforme (audit à 94) |
| 03-3.2.1 | Deux fonctions Neo4j de 227 et 115 lignes | Les découper, ou sortir `infra/neo4j/` du périmètre : le module part en 0.8.0 (audit à 83) |
| 04-4.2 | « Plomberie » de l'éditeur : route `rebuild`, `engine_version`, champs `warnings` et `reference_changes` ; carte de citation ; cache d'aperçus ; question du tiroir d'historique | Décisions du mainteneur (audit à 92) |
| 07-7.4.2 | `StoreResponse.config` et `GraphNode` non typés | Volontaire ; avec une lecture qui l'accepte, audit à 100 |
| 08 | Garde `Host` désactivé par défaut | Valeur par défaut dans les fichiers compose : décision du mainteneur |
| 09-9.1.3 | Les specs Karate UI n'ont jamais tourné | Les lancer sur la pile, puis marquer `@critical` le scénario PDF.js |
| 11-11.2.1 | Version encore en 0.7.3 | Commit de freeze |

---

## Points non vérifiés

- **Rien n'a été regardé à l'écran depuis le 18/11.** Sont concernés : les couleurs (trois commits isolés), les composants de l'éditeur découpés et leur feuille de style partagée, le bandeau de refus d'enregistrement, la visionneuse PDF.js.
- Les workflows, les images Docker en Node 22 et les gabarits nginx n'ont jamais tourné avec ces changements.
- Les specs Karate UI réécrites n'ont jamais tourné.
- Les coûts de l'audit 12 sont estimés à la lecture, sans mesure.
- 05, 06, 07 et 10 n'ont pas été recontrôlés après le troisième cycle.

---

## Verdict : **NO-GO formel, par les deux CRITICAL de procédure**

Le score global est de 89, sept audits sur douze sont à 93 ou plus, aucun n'est sous 60, et les suites sont vertes. Il ne reste plus d'écart CRITICAL qui tienne au code.

Pour un GO, dans l'ordre :
1. lancer l'application et regarder les écrans listés ci-dessus ;
2. trancher les décisions du [plan d'amélioration](../release-0.7.4-validation/improvement-plan.md), au moins le tiroir d'historique et la PR #403 ;
3. pousser la branche, ouvrir la PR vers `release/0.7.4`, obtenir une CI verte ;
4. faire le commit de freeze ;
5. obtenir un Release Gate vert sur la PR de release.
