# Synthèse de l'audit de validation — Release 0.7.4

**Date** : 2026-11-19
**Branche** : `fix/0.7.4-editor-followups` au commit `efc0bc5`, non poussée.
**Auditeur** : claude-code
**Objet** : mesurer l'effet de la seconde remédiation (les écarts que le plan du 18/11 avait reportés) et relire son code avant sa première exécution.

**Particularité de cette passe** : les 15 commits de `b5f8c7f` à `efc0bc5` ont été écrits sans rien exécuter, la machine étant occupée. Chaque auditeur a donc eu deux missions : noter son audit, et relire le code neuf de son périmètre comme avant une première exécution.

**Suites** : elles ont tourné pendant l'audit, dès que la machine s'est calmée.

| Suite | Résultat sur `efc0bc5` | Après correction (`89c33f0`) |
|-------|------------------------|------------------------------|
| Backend, `pytest` | 1748 passés, **1 échec**, 15 ignorés | 1750 passés, 15 ignorés |
| Backend, `ruff check` | 10 erreurs, toutes dans des tests | propre |
| Backend, `ruff format --check` | 4 fichiers à reformater | propre |
| Frontend, eslint, prettier, `vue-tsc` | propres | — |
| Frontend, vitest | 633 passés sur 72 fichiers | — |

Le seul test en échec venait du test lui-même : le client de test ne sait pas construire une URL IPv6. Le code qu'il visait était correct.

**Non exécuté** : `vite build`, l'application, Docker, nginx, les e2e Karate, Trivy, les workflows.

---

## Tableau de bord

| #  | Audit                  | Contrôle 18/11 | Validation | Δ    | CRIT | MAJ | Verdict |
|----|------------------------|----------------|------------|------|------|-----|---------|
| 01 | Hexagonal Architecture | 78             | **91**     | +13  | 0    | 1   | GO |
| 02 | DDD                    | 83             | **89**     | +6   | 0    | 1   | GO |
| 03 | Clean Code             | 61             | **72**     | +11  | 0    | 1   | GO CONDITIONNEL |
| 04 | KISS                   | 75             | **67**     | −8   | 0    | 1   | GO CONDITIONNEL |
| 05 | DRY                    | 83             | **100**    | +17  | 0    | 0   | GO |
| 06 | SOLID                  | 100            | 100        | 0    | 0    | 0   | GO |
| 07 | Decoupling             | 94             | 94         | 0    | 0    | 1   | GO |
| 08 | Security               | 97             | 97         | 0    | 0    | 1   | GO, si le Trivy du gate est vert |
| 09 | Tests                  | 93             | 81, puis **93** une fois le test corrigé | 0 | 0 | 1 | GO après `89c33f0` |
| 10 | CI / Build             | 75             | **85**     | +10  | 1    | 0   | NO-GO (CRIT de procédure) |
| 11 | Documentation          | 72             | 67 (94 à 100 après le freeze) | −5 | 1 | 1 | NO-GO avant le freeze |
| 12 | Performance            | 95             | 95         | 0    | 0    | 0   | GO |

**Score global** : **≈ 87 / 100** sur `efc0bc5` avec l'audit 09 à 81 (86,5), et 87,5 une fois le test corrigé. Il était de 84 au contrôle du 18/11, de 80 avant la première remédiation, de 74 le 13/11.
**Écarts CRITICAL** : 2, les mêmes, tous deux de procédure (CI jamais passée sur la tête de release, CHANGELOG non figé).
**Écarts MAJOR** : 8. Il y en avait 14 au contrôle.

---

## Ce qui a bougé

- **05 DRY, 83 → 100.** La marche des titres n'existe plus qu'une fois (`domain/heading_tree.py`), comme les hachages du flux d'édition, les règles de découpage et de fusion des chunks, et l'horloge. La vérification d'équivalence, règle par règle contre les anciennes copies, ne trouve aucune différence involontaire : les valeurs persistées restent valides.
- **01 Architecture, 78 → 91.** Plus aucun accès au disque dans les services (port `DocumentFileStore`, interdit par le test d'architecture), routes allégées.
- **03 Clean Code, 61 → 72.** Les cinq fichiers fourre-tout sont résolus, sept des neuf fonctions à plusieurs responsabilités aussi. Restent deux fonctions Neo4j, laissées volontairement.
- **10 CI / Build, 75 → 85.** L'image `local` est construite et scannée par le gate.
- **02 DDD, 83 → 89.** L'état « analyse active et source des chunks » a un agrégat et un seul dépôt.

## Ce qui a baissé

- **04 KISS, 75 → 67.** C'est le contrepoids de cette passe. Elle a supprimé de vraies duplications, mais ajouté de la structure : six méthodes qui ne font que transmettre un appel (la façade `ChunkService`), deux réglages de plus, un mécanisme de suivi des champs modifiés dans l'agrégat, sept modèles de réponse qui recopient sept modèles de requête, et +1 245 lignes Python nettes. L'audit confirme aussi du code mort : environ 1 700 lignes côté frontend.
- **11 Documentation, 72 → 67.** Deux sections du CHANGELOG ajoutées dans le mauvais ordre.
- **09 Tests, 93 → 81** sur le commit audité, à cause du seul test en échec, corrigé depuis.

---

## Relecture avant première exécution

Les relectures annonçaient ce que les suites ont confirmé :
- **06 SOLID** : 239 appels de services sur une dépendance injectée, 134 constructions dans le câblage, 1 206 dans les tests, aucune incompatibilité de signature.
- **01 Architecture** : aucun défaut probable à l'import ou à l'exécution.
- **03 Clean Code** : aucun défaut probable de typage, de lint ou d'exécution dans les composants et modules extraits.
- **10 CI / Build** : aucun défaut qui ferait échouer un job ou le ferait passer à tort.

Défauts réels trouvés par ces relectures, à corriger :

| Origine | Défaut | Gravité |
|---------|--------|---------|
| 02, 07 | Après suppression de l'analyse active, le document n'a plus d'analyse courante pour Ask et MCP alors que d'autres analyses terminées existent, et le frontend se rabat sur une version qu'ils refusent de lire | Bug fonctionnel probable |
| 02 | Rechunk ou restauration sur un document sans ligne d'état : crée une ligne à sélection vide qui masque l'analyse de repli | Rare |
| 02 | Analyse supprimée pendant une restauration : 500 au lieu de 409 | Rare |
| 01, 06 | L'export PDF ne résout pas le chemin stocké, contrairement à l'aperçu | Faible |
| 12 | La réponse typée de l'éditeur est construite sur la boucle d'événements : environ 0,1 s de blocage en plus par aperçu à 300 pages (estimé) | Régression mineure |
| 12 | `show_sources` résout l'analyse courante une fois par citation | Régression mineure |
| 08, 12 | Suppression et fusion de masse dans l'éditeur : coût quadratique | Ancien, confirmé |
| 10 | Un run du Release Gate annulé publiait un verdict GO | Ancien |
| 09 | Deux tests supprimés sans équivalent pendant les déplacements | Mineur |

---

## Points non vérifiés

- Rien n'a été regardé à l'écran depuis le début de ces travaux : couleurs, composants de l'éditeur découpés, visionneuse.
- Les workflows, les images Docker et nginx n'ont jamais tourné avec ces changements.
- Les specs Karate UI réécrites n'ont jamais tourné.
- Les coûts de l'audit 12 sont estimés à la lecture, sans mesure.

---

## Verdict : **NO-GO formel, par les deux CRITICAL de procédure**

Le score global passe à 87, plus aucun audit n'est sous 60, et les suites sont vertes. Les deux CRITICAL restants se lèvent par une CI verte sur la PR et par le commit de freeze.

Le plan d'amélioration issu de cet audit est dans [improvement-plan.md](improvement-plan.md).
