# Synthèse de re-audit — Release 0.7.4

**Date** : 2026-11-18
**Branche** : `fix/0.7.4-editor-followups` au commit `a6fb539`, c'est-à-dire `release/0.7.4` (`f7fc791`, avec les PR #401 et #402) plus les 13 commits correctifs locaux (#391 à #400) et le commit de fusion. La branche n'est pas poussée.
**Auditeur** : claude-code
**Objet** : re-audit complet (12 audits) après la remédiation du 2026-11-13 et l'arrivée de #401 (rendu PDF.js, cache d'aperçus, résumés d'analyse) et #402 (correctifs de l'éditeur).

**Méthode** : lecture du code, plus exécution des suites sur `a6fb539`, ce que le premier audit n'avait pas pu faire.

- Backend : `ruff check` et `ruff format --check` propres, `pytest` 1501 passés, 15 ignorés (Neo4j absent).
- Frontend : eslint, prettier et `vue-tsc` propres, vitest 586 passés sur 62 fichiers, `vite build` réussi.
- Non exécuté : l'application, Docker, les e2e Karate, Trivy, le Release Gate.

Base de comparaison : `docs/audit/reports/release-0.7.4/` (2026-11-13, commit `eade7fa`, global 74, NO-GO).

---

## Tableau de bord

| #  | Audit                  | Score | Δ vs 13/11 | CRIT | MAJ | MIN | INFO | Verdict |
|----|------------------------|-------|------------|------|-----|-----|------|---------|
| 01 | Hexagonal Architecture | 78    | +9         | 0    | 3   | 1   | 9    | GO CONDITIONNEL |
| 02 | DDD                    | 83    | +8         | 0    | 2   | 12  | 9    | GO |
| 03 | Clean Code             | 56    | +17        | 0    | 2   | 4   | 9    | NO-GO (score) |
| 04 | KISS                   | 75    | 0          | 0    | 1   | 4   | 13   | GO CONDITIONNEL |
| 05 | DRY                    | 67    | 0          | 0    | 2   | 18  | 9    | GO CONDITIONNEL |
| 06 | SOLID                  | 87    | 0          | 0    | 2   | 0   | 17   | GO |
| 07 | Decoupling             | 94    | +3         | 0    | 1   | 0   | 12   | GO |
| 08 | Security               | 97    | 0          | 0    | 1   | 8   | 8    | GO, si le Trivy du gate est vert |
| 09 | Tests                  | 93    | +8         | 0    | 1   | 3   | 11   | GO |
| 10 | CI / Build             | 70    | −15        | 1    | 1   | 1   | 14   | NO-GO (CRIT) |
| 11 | Documentation          | 72    | +11        | 1    | 1   | 0   | 11   | NO-GO avant le freeze (100 après) |
| 12 | Performance            | 86    | +34        | 0    | 0   | 6   | 9    | GO |

**Score global** : **≈ 80 / 100** (79,8, moyenne simple des 12 scores). L'audit du 13/11 était à 74.
**Écarts CRITICAL** : **2**. Il y en avait 4 pour 3 causes.
**Écarts MAJOR** : **17**. Il y en avait 24.

---

## Écarts CRITICAL

1. **[10 — 10.1.1] Aucune CI n'a tourné sur la tête de `release/0.7.4`.**
   - `.github/workflows/ci.yml:4-5` ne se déclenche pas sur un push vers `release/**`.
   - La PR #402 vient d'un fork : ses runs attendaient une approbation et ont été clos sans exécuter un seul job (run `44149188645`).
   - Le dernier CI vert sur du contenu #401 date de `de5fe66`. L'ensemble #401 + #402 n'a donc jamais été validé en CI.
   - Les suites locales sont vertes sur `a6fb539`, ce qui limite le risque sans lever l'écart.
   - **Levée** : une CI verte sur la PR de `fix/0.7.4-editor-followups` vers `release/0.7.4`. Le score repasse alors à 85.
2. **[11 — 11.1.1] CHANGELOG non figé.** `CHANGELOG.md:7` est encore `[Unreleased]` et `frontend/package.json:3` en 0.7.3. C'est attendu avant le commit de freeze, qui lève les deux et porte l'audit 11 à 100.

Les 3 causes CRITICAL du 13/11 liées au code sont levées et vérifiées dans le code :
- le moteur Docling de l'éditeur est derrière le port `AnalysisDocumentEngine` (`domain/ports.py:305`) ;
- la projection de l'éditeur tourne hors de la boucle d'événements (`services/analysis_edit_service.py:304-309`, `:331-336`), avec un test (`tests/test_analysis_editing.py:641`).

---

## Écarts MAJOR, par cause

| Audit / item | Écart | Statut |
|--------------|-------|--------|
| 01-1.2.3 | Règles métier hors de `domain/` : chaîne de hash du flux d'édition en double (service et dépôt), règles de split/merge dans `chunk_service.py`, règles d'édition dans l'adaptateur Docling | Inchangé |
| 01-1.2.4, 06-6.1.4 | Services couplés à des classes concrètes. Aggravé par #401 : `PreviewService` appelle `DocumentService.generate_preview` en statique et contourne le port `PageRasterizer` | Aggravé |
| 01-1.3.3 | Routes qui font le travail d'un service (`api/documents.py`, `api/analysis_edits.py`, `api/analyses.py:84`) | Réduit |
| 02-2.3.1 | « Analyse courante » a trois définitions. MCP et Ask lisent encore le texte non édité | Inchangé depuis 0.7.3 |
| 02-2.4.3 | Pas de racine d'agrégat pour l'état « analyse active + source des chunks » | Réduit |
| 03-3.2.1 | 10 fonctions d'orchestration à plusieurs responsabilités, dont une nouvelle (`AnalysisDetailPage.vue:107`) | Inchangé |
| 03-3.3.2 | Fichiers fourre-tout : `chunk_service.py` (921 lignes), store et composant de l'éditeur, `PagePreviewWithOverlay.vue` (deux chemins de rendu) | Aggravé |
| 04-4.2 | Abstraction de fournisseur LLM à un seul membre | 4e report |
| 05-5.1 | Algorithme de pile de titres écrit 4 fois, avec des divergences | Promu de MIN à MAJ |
| 05-5.3 | Couleurs codées en dur et tokens CSS non définis (33 `var(--color-*)`) | Inchangé |
| 06-6.2.1 | 15 appels de services vers des méthodes absentes du `Protocol` qui type la dépendance ; pas de port `DocumentVersionRepository` | Réduit |
| 07-7.4.2 | `dict` non typés dans les schémas de réponse de l'éditeur | Inchangé |
| 08 | `/api/*` ne valide pas l'en-tête `Host` : rebinding DNS possible contre une instance locale | Inchangé |
| 09-9.1.3 | Karate UI : 3 specs périmées, la feature de l'éditeur n'est pas `@critical`, le job ne tourne que sur `main` | Inchangé |
| 10-10.2.3 | L'image `local` publiée n'est ni construite ni scannée par le gate | Inchangé |
| 11-11.2.1 | Version encore en 0.7.3 | Attendu avant le freeze |

---

## Ce que la fusion du 18/11 a montré

- La branche de correctifs était restée 5 jours en local sans être exécutée. La première exécution a fait tomber 8 tests backend, tous périmés par les renommages de #397 (`export(edited=True)` devenu `export_edited`) ou par un libellé de log.
- #395 a été corrigé deux fois, en local et dans #402. La fusion a gardé une seule implémentation de chaque règle (validation de fusion en clés i18n, mapping d'erreurs dans `api/errors.py`, rejeu du cache corrompu derrière le port).
- La PR #403, ouverte vers `release/0.7.4`, corrige #393 une seconde fois : elle entrera en conflit avec le correctif local.

---

## Points non vérifiés

- Le Release Gate n'a jamais tourné sur du contenu 0.7.4 : build de l'image unique, variante `local`, Trivy, `pip-audit`, smoke test, e2e UI `@critical`.
- Aucun job n'a chargé le chemin PDF.js à l'exécution : worker sous `nosniff`, requêtes `Range` à travers nginx.
- Le rebinding DNS de l'audit 08 est déduit du code, pas démontré.
- La montée de version d'une vraie base 0.7.3 (#391) n'est testée que sur un schéma recopié à la main.

---

## Verdict final : **NO-GO**, à deux pas d'un GO conditionnel

Le score global atteint 80, mais il reste 2 CRITICAL et l'audit 03 est sous 60.

Conditions pour un GO :
- pousser la branche et obtenir une CI verte sur la PR vers `release/0.7.4` (lève 10.1.1) ;
- faire le commit de freeze : CHANGELOG daté `[0.7.4]`, versions montées (lève 11.1.1 et 11.2.1) ;
- remonter l'audit 03 à 60 ou plus : l'item de nommage 3.1.1 suffit (61) ;
- Release Gate vert sur la PR de release vers `main`.

Le plan de remédiation est dans [remediation-plan.md](remediation-plan.md).
