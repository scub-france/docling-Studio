# Synthèse de l'audit de contrôle — Release 0.7.4

**Date** : 2026-11-18
**Branche** : `fix/0.7.4-editor-followups`, non poussée. C'est `release/0.7.4` (`f7fc791`) plus les correctifs locaux #391 à #400, la fusion `a6fb539` et 22 commits de remédiation.
**Auditeur** : claude-code
**Objet** : mesurer l'effet de la remédiation du 2026-11-18 sur les notes, et vérifier qu'elle n'a rien cassé.

**Commits contrôlés** :
- les 12 audits sur `a12b744`, après la première passe de remédiation ;
- les audits 03 et 05 une seconde fois, sur `2d5a80e` puis `b5f8c7f`, après une passe ciblée sur ce que le premier contrôle avait trouvé.

Les commits entre `a12b744` et `b5f8c7f` ne touchent pas le barème des dix autres audits : renommages, couleurs, lecture des tailles de page, ajustements CI et documentation demandés par les contrôles.

**Suites exécutées sur `b5f8c7f`** : backend `ruff` propre, `pytest` 1563 passés et 15 ignorés (1501 avant remédiation). Frontend eslint, prettier et `vue-tsc` propres, vitest 605 passés sur 65 fichiers (586 avant), `vite build` réussi.
**Non exécuté** : l'application, Docker, nginx, les e2e Karate, Trivy, le Release Gate.

---

## Tableau de bord

| #  | Audit                  | 13/11 | Re-audit `a6fb539` | Contrôle | Δ remédiation | CRIT | MAJ | Verdict |
|----|------------------------|-------|--------------------|----------|---------------|------|-----|---------|
| 01 | Hexagonal Architecture | 69    | 78                 | 78       | 0             | 0    | 3   | GO CONDITIONNEL |
| 02 | DDD                    | 75    | 83                 | 83       | 0             | 0    | 2   | GO |
| 03 | Clean Code             | 39    | 56                 | **61**   | +5            | 0    | 2   | GO CONDITIONNEL (était NO-GO) |
| 04 | KISS                   | 75    | 75                 | 75       | 0             | 0    | 1   | GO CONDITIONNEL |
| 05 | DRY                    | 67    | 67                 | **83**   | +16           | 0    | 1   | GO (était GO CONDITIONNEL) |
| 06 | SOLID                  | 87    | 87                 | **100**  | +13           | 0    | 0   | GO |
| 07 | Decoupling             | 91    | 94                 | 94       | 0             | 0    | 1   | GO |
| 08 | Security               | 97    | 97                 | 97       | 0             | 0    | 1   | GO, si le Trivy du gate est vert |
| 09 | Tests                  | 85    | 93                 | 93       | 0             | 0    | 1   | GO |
| 10 | CI / Build             | 85    | 70                 | **75**   | +5            | 1    | 1   | NO-GO (CRIT) |
| 11 | Documentation          | 61    | 72                 | 72       | 0             | 1    | 1   | NO-GO avant le freeze (100 après) |
| 12 | Performance            | 52    | 86                 | **95**   | +9            | 0    | 0   | GO |

**Score global** : **≈ 84 / 100** (83,8). Il était de 80 avant la remédiation et de 74 le 13/11.
**Écarts CRITICAL** : **2**, inchangés. Aucun ne se lève par du code (voir plus bas).
**Écarts MAJOR** : **14**. Il y en avait 17 avant la remédiation et 24 le 13/11.
**Audits sous 60** : aucun. Il y en avait un (03).

Projection après une CI verte sur la PR et le commit de freeze : audit 10 à 90, audit 11 à 100, global ≈ 87, 0 CRITICAL.

---

## Ce qui a bougé

- **06 SOLID, 87 → 100.** Les deux MAJ sont levés. Un script indépendant a croisé 236 appels faits par les services sur une dépendance injectée : aucun n'est hors du `Protocol` qui la type, et plus aucun service n'est typé sur une classe concrète. `services/` n'importe plus aucune bibliothèque PDF, et le test d'architecture l'interdit.
- **05 DRY, 67 → 83.** L'item des couleurs est conforme : plus aucun token non défini (49 usages avant), plus aucun repli littéral (71 avant), plus aucun littéral qui recopie la valeur d'un token. Il a fallu deux passes : le premier contrôle avait trouvé 37 contournements, le second une dernière ligne.
- **12 Performance, 86 → 95.** Logo de 878 Ko réduit à 61 Ko, cache d'un an et compression des fichiers statiques dans nginx. L'analyse du verrou pdfium ne trouve aucun interblocage.
- **03 Clean Code, 56 → 61.** L'item de nommage est conforme après trois passes et plus de 200 renommages. Le contrôle a montré que le script de mesure d'origine sous-comptait : sa liste de verbes contenait des noms.
- **10 CI / Build, 70 → 75.** `.dockerignore` conformes. Le CRITICAL reste, il attend une exécution de CI.

## Ce qui n'a pas bougé, et pourquoi

- **01 (78).** Les corrections sont réelles : 4 routes sur 6 ne font plus le travail d'un service, la liste des imports tolérés passe de 11 entrées à 1. Mais un item ne passe que si toutes ses occurrences disparaissent. Il reste des accès directs au système de fichiers dans les services (`os.unlink`, `open`, `Path.stat`) et deux reliquats de routes. Un port de stockage de fichiers donnerait 84, les deux routes en plus 91. Cela touche l'upload et la suppression : non fait sans pouvoir lancer l'application.
- **02, 04, 07, 08, 09, 11.** Leurs écarts restants n'étaient pas visés : ils demandent une décision produit, un changement de contrat ou l'application lancée. Ils sont dans le plan de remédiation.

---

## Vérifications de non-régression

| Point vérifié | Méthode | Résultat |
|---------------|---------|----------|
| Contrat d'API | Document OpenAPI généré à `a6fb539` et à `a12b744`, puis empreinte avant et après la dernière passe de renommage | Identique octet pour octet : 45 chemins, 58 operationIds, 75 schémas |
| Outils et prompts MCP | `list_tools()` et `list_prompts()` comparés sur les 4 configurations | Identiques |
| Clés JSON, i18n, colonnes, clés de stockage | Balayage des littéraux de chaîne aux deux commits | Aucun changement |
| Tests perdus ou affaiblis | Identifiants collectés aux deux commits, assertions comptées par fichier | 12 tests déplacés avec leurs assertions, aucun supprimé, aucune cible de `patch` cassée |
| Sécurité | Relecture de chaque surface modifiée | Aucune régression applicative. Les messages d'erreur ne peuvent plus contenir de chemin serveur |
| Sur-ingénierie | Revue de chaque port, adaptateur et classe ajoutés | Tous jugés justifiés |
| Verrou pdfium | Lecture du code de Docling et mesures | Aucun interblocage possible |

Une seule différence de comportement, hors contrat documenté : sur `GET /api/documents/{id}/pages`, une exception inattendue pendant la lecture en base renvoie 422 au lieu de 500.

Les contrôles ont aussi trouvé des défauts de la remédiation elle-même, tous corrigés depuis :
- 5 des 26 fonctions mal nommées avaient été ajoutées par la remédiation ;
- déclencher la CI sur les branches de release donnait à ces runs un jeton en écriture : `ci.yml` a maintenant un jeton en lecture seule ;
- `page_sizes` tenait le verrou pdfium 106 ms sur 300 pages : 2,6 ms désormais ;
- trois phrases de la documentation écrite dans la nuit étaient fausses dans des cas limites ;
- un test ajouté ne pouvait pas échouer.

---

## Écarts CRITICAL

1. **[10 — 10.1.1] Aucune CI n'a tourné sur la tête de `release/0.7.4`.** La cause est corrigée dans `ci.yml`, mais l'écart ne se lève qu'avec une CI verte sur la PR de cette branche, puis sur le commit de merge.
2. **[11 — 11.1.1] CHANGELOG non figé.** Il attend le commit de freeze.

## Points non vérifiés

- Rien n'a été regardé à l'écran. Les deux commits de couleurs (`1516a0c`, `2d5a80e`) changent l'aspect de plusieurs écrans : ils sont isolés pour pouvoir être annulés seuls.
- Les gabarits nginx et les Dockerfiles modifiés n'ont pas été exécutés : relus par deux contrôles, à valider par les e2e de la CI.
- Le chemin d'upload passe maintenant par un adaptateur. Trois tests y envoient un vrai PDF, mais l'application n'a pas été lancée.
- Le Release Gate n'a jamais tourné sur du contenu 0.7.4.

---

## Verdict : **NO-GO formel, par les deux CRITICAL de procédure**

Plus aucun écart CRITICAL ne tient au code, plus aucun audit n'est sous 60, et le score global est de 84.

Pour un GO :
1. lancer l'application et regarder les écrans touchés par les couleurs, l'éditeur, la visionneuse PDF et un upload ;
2. pousser la branche, ouvrir la PR vers `release/0.7.4`, obtenir une CI verte ;
3. faire le commit de freeze ;
4. Release Gate vert sur la PR de release.

Le détail de ce qui a été fait et de ce qui reste est dans [le plan de remédiation](../release-0.7.4-reaudit/remediation-plan.md).
