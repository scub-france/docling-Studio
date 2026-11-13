# Synthèse d'audit — Release 0.7.4

**Date** : 2026-11-13
**Branche** : `fix/0.7.4-editor-followups` au commit `eade7fa`, c'est-à-dire `release/0.7.4` (`2f47f72`) plus les trois correctifs locaux #391 (mise à niveau d'une base 0.7.3), #392 (ordre de fusion de l'éditeur) et #393 (chunks de provenance inconnue).
**Auditeur** : claude-code
**Méthode** : lecture statique uniquement. Aucun test, lint, build ni scan n'a été exécuté pour cet audit, la machine étant occupée. Les 13 tests ajoutés par #391, #392 et #393 n'ont jamais tourné. Le dernier CI de `release/0.7.4` (run `43253020395` sur `3c00d44`) est vert : backend 1369 passés / 19 ignorés, frontend 570 tests, e2e API verts, e2e UI non lancés hors `main`. Le Release Gate n'a jamais tourné sur du contenu 0.7.4 : il ne se déclenche que sur une PR vers `main`.

Base de comparaison : premier audit 0.7.3 (`release-0.7.3/`) pour 01 à 06 et 09, re-audit 0.7.3 (`release-0.7.3-reaudit/`) pour 07, 08, 10, 11 et 12.

---

## Tableau de bord

| #  | Audit                  | Score | Δ vs 0.7.3 | CRIT | MAJ | MIN | INFO | Verdict |
|----|------------------------|-------|------------|------|-----|-----|------|---------|
| 01 | Hexagonal Architecture | 69    | −9         | 1    | 3   | 1   | 7    | NO-GO (CRIT) |
| 02 | DDD                    | 75    | −17        | 1    | 2   | 10  | 6    | NO-GO (CRIT) |
| 03 | Clean Code             | 39    | −5         | 0    | 3   | 6   | 6    | NO-GO (score) |
| 04 | KISS                   | 75    | 0          | 0    | 1   | 3   | 9    | GO CONDITIONNEL |
| 05 | DRY                    | 67    | 0          | 0    | 4   | 15  | 6    | GO CONDITIONNEL (4 MAJ > 3 : NO-GO en lecture stricte) |
| 06 | SOLID                  | 87    | 0          | 0    | 2   | 0   | 15   | GO |
| 07 | Decoupling             | 91    | −3         | 0    | 1   | 1   | 18   | GO |
| 08 | Security               | 97    | 0          | 0    | 1   | 8   | 7    | GO, si le Trivy du gate est vert |
| 09 | Tests                  | 85    | −8         | 0    | 2   | 2   | 11   | GO, provisoire (tests non exécutés) |
| 10 | CI / Build             | 85    | 0          | 0    | 1   | 1   | 12   | GO, provisoire (gate jamais lancé) |
| 11 | Documentation          | 61    | −39        | 1    | 2   | 0   | 8    | NO-GO avant le freeze |
| 12 | Performance            | 52    | −15        | 1    | 2   | 7   | 7    | NO-GO (CRIT + score) |

**Score global** : **≈ 74 / 100**, moyenne simple des 12 scores comme en 0.7.0 et 0.7.3. Le re-audit 0.7.3 était à 82.
**Écarts CRITICAL** : **4** entrées pour **3 causes distinctes**.
**Écarts MAJOR** : **24**.

La baisse vient presque entièrement de l'éditeur d'analyse (#319, #388), mergé sans passer par l'audit : pas de port pour le moteur Docling, projection synchrone sur la boucle d'événements, routes sans test d'API, CHANGELOG sans entrée « Added ».

---

## Écarts CRITICAL (tous audits confondus)

1. **[01 — 1.4.1] [02 — 2.5.3] Le moteur Docling de l'éditeur n'a pas de port.**
   - `DoclingDocumentEditor` (`infra/docling_editor.py:33`) et `DoclingAnalysisProjector` (`infra/docling_projector.py:31`) n'implémentent aucun Protocol de `domain/ports.py`.
   - `AnalysisEditService` les reçoit sans type (`services/analysis_edit_service.py:59-61`).
   - Leur contrat est `MutationResult`, une classe d'`infra/` qui transporte un `DoclingDocument` vivant de l'éditeur au projecteur à travers le service (`analysis_edit_service.py:298-311`).
   - **Remédiation** : un port `AnalysisDocumentEditor` qui compose éditeur et projecteur et renvoie `ProjectedAnalysis`, avec un constructeur de service typé. Les deux CRIT tombent ensemble ; 01 passe à 78, 02 à 83.
2. **[12 — 12.1.4] La projection de l'éditeur bloque la boucle d'événements.**
   - `_project` et `project_serialized` (`analysis_edit_service.py:94-98, 298-311`) tournent en synchrone.
   - Cela se produit à l'ouverture de chaque document, à chaque prévisualisation (400 ms après la frappe), deux fois par sauvegarde, sur l'export md/json par défaut et sur le rechunk (`export_service.py:78-79, 96-97` ; `chunk_service.py:376-381, 712-716`).
   - L'ordre de grandeur, environ 1,4 s CPU sur 28 pages, vient de la review de septembre et n'a pas été remesuré.
   - **Remédiation** : `asyncio.to_thread` autour de la projection, plus un test. 12 passe à 67.
3. **[11 — 11.1.1] CHANGELOG non figé.** `CHANGELOG.md:7` est encore `[Unreleased]`. C'est attendu avant le freeze (#373) : le commit de freeze le lève, avec 11.2.1 (`frontend/package.json:3` en 0.7.3). 11 passe alors à 89.

---

## Top blockers (poids 3 d'abord, puis MAJ structurants)

| Rang | Audit / item | Poids | Écart | Effort |
|------|--------------|-------|-------|--------|
| 1 | 01-1.4.1 + 02-2.5.3 | 3 | Port `AnalysisDocumentEditor` | M |
| 2 | 12-12.1.4 | 3 | Projection hors boucle (`to_thread`) | S |
| 3 | 11-11.1.1 | 3 | Freeze du CHANGELOG (#373) | S, au freeze |
| 4 | 12-12.1.1 | 2 | Une requête par chunk : `chunk_service.py:357-358, 397-398, 752-758`, `version_service.py:185-186` → UPDATE groupés | S |
| 5 | 12-12.1.5 | 2 | PDF entier lu à chaque page rendue : `infra/page_raster.py:26-28` → ouverture par chemin | S |
| 6 | 09-9.2.1 | 2 | Les 6 routes de l'éditeur (`api/analysis_edits.py:120-208`) n'ont aucun test d'API hors flag désactivé | M |
| 7 | 11-11.1.2 | 2 | L'éditeur n'a pas d'entrée « Added » dans le CHANGELOG | S |
| 8 | 05-5.1 | 2 | `_parse_iso` ×8 ; contrat d'erreur service→HTTP ×7 familles ; extraction des pages ×3 avec des types divergents (le projecteur émet `list_item` / `paragraph` / `caption`, ce qui ferait perdre leur couleur aux listes dans l'espace document — déduit du code, non exécuté) | M |
| 9 | 03-3.1.3 | 2 | Cartes MCP en français par défaut ; une douzaine de chaînes UI de l'éditeur hors i18n | S |
| 10 | 07-7.4.2 | 2 | `dict` dans les schémas de réponse (modèle, arbre et payload de l'éditeur) | M |

## Quick wins (poids 1, effort S)

- **03-3.2.4** : flag arguments `select_analysis` (`analysis_repo.py:175`), `edited` (`export_service.py:52`), `additive` (`AnalysisEditor.vue:376`).
- **03-3.2.3** : plus de 4 paramètres dans 7 nouvelles fonctions. Remède : un value object `EditTarget(document_id, analysis_id)` et des arguments keyword-only.
- **03-3.1.1** : noms sans verbe dans le nouveau code de l'éditeur (`history`, `_tree`, `_response`…).
- **10-10.2.4** : pas de `frontend/.dockerignore` ; `out/` manque à `.dockerignore`.
- **07-7.4.3** : document ou analyse inconnus servis en 409 au lieu de 404 (`analysis_edit_service.py:271-275`, `api/analysis_edits.py:113-114`).
- **Doc** : `docs/analysis-editor.md:18` dit encore « in selection order », alors que la fusion suit l'ordre de lecture depuis #392.

## Bugs fonctionnels relevés en passant (hors barème)

- Le front autorise la fusion texte + paragraphe (`commands.ts:78`), le back la refuse (`docling_editor.py:219-221`) : bouton actif puis 400.
- `EditorSnapshot` fabrique un `AnalysisJob` d'id `working:{doc}`, identique pour toutes les analyses d'un document (`analysis_edit_service.py:327`).
- `project_serialized` ne traduit pas les erreurs Pydantic : un cache corrompu remonte en HTTP 500.
- Avec `ANALYSIS_EDITOR_ENABLED=false`, les routes de l'éditeur répondent 404 mais les modifications sauvegardées s'appliquent toujours à l'export, au rechunk et à l'arbre.
- MCP (`services/parse_loader.py:89`) et Ask servent la dernière analyse terminée, sans les modifications ni la sélection active.
- Le job « Unit tests » du Release Gate ne peut pas échouer : `release-gate.yml:86, 92` passent pytest et vitest dans `tee` sans `pipefail`. C'est compensé par `ci.yml`.

---

## Verdict final : **NO-GO**

3 causes CRITICAL distinctes, dont 2 indépendantes du freeze, et un score global de 74, sous le seuil de 80.

Conditions pour un GO :
- Lever les 3 causes CRITICAL : port de l'éditeur, projection hors boucle, freeze du CHANGELOG.
- Faire tourner les 13 tests ajoutés par #391, #392 et #393, puis le Release Gate sur la PR de release (Trivy, e2e).
- Revenir à ≤ 3 MAJ non résolus par audit, ce qui concerne 05.

D'après les estimations des rapports, lever les CRIT et les MAJ de rang 4 à 9 ramènerait le score global vers 83, et vers 86 après le freeze.
