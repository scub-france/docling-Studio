# Synthèse de re-audit — Release 0.7.3

**Date** : 2026-11-02
**Branche** : `release/0.7.3` au commit `e01fd95`, le merge de la remédiation (PR #367)
**Auditeur** : claude-code
**Objet** : confirmer que la release peut partir, avec **0 CRITICAL** et un **score global ≥ 80**. Le premier audit (`docs/audit/reports/release-0.7.3/`, sur `02adc68`) avait conclu NO-GO.

Seuls les **5 audits touchés** par la remédiation sont re-audités : 07, 08, 10, 11 et 12. Les 7 autres (01, 02, 03, 04, 05, 06, 09) gardent le score de leur premier audit, car la remédiation n'a pas touché leur périmètre ou n'a pas changé leur notation. Deux exceptions mineures :
- 03 reçoit `lang="fr"` sur la carte de citation, sans effet sur l'item 3.1.3 ;
- 09 reçoit un test de plus.

**Release Gate** (PR #366, run `41464248455` sur `e01fd95`) : **`success`, 13 jobs sur 13**. Les scans Trivy `remote` et `local` sont verts, comme le smoke test, la taille d'image et les E2E API et UI. Le commentaire du gate sur #366 indique **🟢 GO**.

---

## Tableau de bord (12 audits)

| #  | Audit                  | Score (1er audit → re-audit) | CRIT | MAJ | Verdict         |
|----|------------------------|------------------------------|------|-----|-----------------|
| 01 | Hexagonal Architecture | 78 (inchangé)                | 0    | 3   | GO CONDITIONNEL |
| 02 | DDD                    | 92 (inchangé)                | 0    | 1   | GO              |
| 03 | Clean Code             | 44 (inchangé)                | 0    | 3   | NO-GO (score)   |
| 04 | KISS                   | 75 (inchangé)                | 0    | 1   | GO CONDITIONNEL |
| 05 | DRY                    | 67 (inchangé)                | 0    | 3   | GO CONDITIONNEL |
| 06 | SOLID                  | 87 (inchangé)                | 0    | 2   | GO              |
| 07 | Decoupling             | 89 → **94**                  | 0    | **1** | **GO**        |
| 08 | Security               | 89 → **97**                  | **0** | 2  | **GO**          |
| 09 | Tests                  | 93 (inchangé)                | 0    | 1   | GO              |
| 10 | CI / Build             | 70 → **85**                  | **0** | 1  | **GO**          |
| 11 | Documentation          | 44 → **100**                 | **0** | **0** | **GO**       |
| 12 | Performance            | 52 → **67**                  | 0    | **2** | GO CONDITIONNEL |

**Score global** : **≈ 82 / 100**, moyenne simple des 12 scores comme en 0.7.0. C'était 73.
**Écarts CRITICAL** : **0**. Il y en avait 4 entrées, pour 3 causes distinctes, toutes levées.
**Écarts MAJOR** : **20**. Il y en avait 24 ; 4 sont levés : 07-`ConfigSource`, 11-CHANGELOG #359/#323, 11-version frontend, 12-import bloquant.

---

## CRITICAL — statut

Les 3 causes distinctes du premier audit sont levées et vérifiées :

1. **[08 + 10] Release Gate rouge (Trivy CRITICAL).**
   - **Causes réelles**, lues dans les artefacts du run `41452005966` : des paquets corrigeables.
   - **Corrections** : PyJWT 2.15.1, certifi 2026.10.23, `uv` 0.13.6 (plus de crate `zip`), mcp 2.2.0.
   - **Risques acceptés jusqu'au 2026-12-31** :
     - Pillow 10.4.0, 4 CVE, corrigées seulement en 13.0.0, que docling n'autorise qu'à partir de ses versions majeures d'octobre 2026. C'est une décision du mainteneur ; la montée docling est prévue pour la 0.8.0.
     - libxml2 (CVE-2026-6653), toujours sans correctif Debian.
   - **Vérification** : les justifications ont été vérifiées dans le code (re-audit 08).
   - **Run `41464248455`** : les deux scans sont verts.
2. **[11] CHANGELOG non figé** → `## [0.7.3] - 2026-11-02` (`CHANGELOG.md:7`), `frontend/package.json` et son lockfile en 0.7.3.
3. **[11] `ASK_MODE` non signalé comme breaking** → section `### BREAKING CHANGES` (`CHANGELOG.md:36-38`).

→ **0 CRITICAL restant.**

---

## MAJOR restants (20) — dette suivie, non bloquante pour ce tag

| Audit | Écart | Statut / cible |
|-------|-------|----------------|
| 01 ×3 | Règles split/merge dans le service, PDF hors port, orchestration et I/O dans `api/documents.py` (dont `/pages`) | Dette 0.7.0, aggravée par 0.7.3 → 0.8.0 |
| 02 | Vocabulaire non unifié : `version`, round/hop/iteration, `citation` | Nouveau 0.7.3 → 0.8.0 |
| 03 ×3 | Textes français en dur dans les cartes MCP (choix produit assumé), `chunk_service` god-file, fonctions multi-responsabilités | Dette 0.7.0, plus un choix assumé |
| 04 | Abstraction LLM-provider prématurée | Dette 0.7.0 (3e report) |
| 05 ×3 | `_parse_iso` copié 7 fois et divergence UTC, couleurs en dur, contrat d'erreur service → HTTP copié | Dette 0.7.0, plus 1 nouveau |
| 06 ×2 | `DocumentService` contourne les ports PDF ; services typés sur `Sqlite*`, avec des méthodes absentes des ports | Antérieur à 0.7.0 → 0.8.0 |
| 07 | `StoreResponse.config: dict` / `GraphNode extra=allow` | Ingestion, supprimée en 0.8.0 |
| 08 | **Exposition MCP** : docs, CHANGELOG, `.env.example` et commentaire rendus exacts ; le défaut n'a pas changé (activée, sans authentification). `README.md:31` et le libellé Settings (`i18n.ts`) promettaient encore « localhost only » | **Corrigé sur la branche de suivi** `fix/release-0.7.3-reaudit-followups`. Le re-audit 08 le reclasse en MIN une fois ces deux textes corrigés |
| 08 | `/api/*` ne contrôle pas `Host` (DNS rebinding contre une instance locale) | Antérieur à 0.7.3 → 0.8.0, avec l'authentification |
| 10 | Variante `local` publiée (reasoning) ni construite ni scannée par le gate | Dette 0.7.0 → 0.8.0 |
| 09 | Karate UI : 3 specs obsolètes, 8 features 0.7.3 absentes de la CI | Nouveau → 0.8.0 |
| 12 ×2 | PDF entier relu pour chaque page rendue ; un commit par chunk | → 0.8.0 |

---

## Branche de suivi (avant le tag)

`fix/release-0.7.3-reaudit-followups`, tirée de `release/0.7.3`, rassemble ce que les re-audits ont relevé et qu'il vaut mieux corriger avant le tag, puisque ces textes partent dans les notes de release :

- **CHANGELOG** :
  - #323 annonçait un renommage « Analysis library » que l'interface n'a pas fait (elle dit toujours « Analyses », `i18n.ts:752`) ;
  - #359 parlait d'un « upload dialog » : c'est la zone d'upload.
- **MCP** : `README.md:31` et le libellé Settings ne promettent plus « localhost only ».
- **Gate** :
  - `fail-fast: false` sur la matrice de scan, pour que `local` soit toujours scanné ;
  - avertissement si `pip-audit` ne produit pas de rapport ;
  - libellé « npm CRITICAL only » dans le résumé.
- **`.trivyignore.yaml`** : la note Pillow mentionne aussi le plafond `pillow<11` de Studio.
- Ces rapports de re-audit.

---

## Verdict du gate : **GO** (au sens strict du master : GO CONDITIONNEL)

- **0 CRITICAL** ✅
- **Score global ≈ 82 ≥ 80** ✅
- **Release Gate vert** sur #366 (13/13 jobs) ✅

**Nuance.** La règle stricte du master (« > 3 MAJ non résolus ⇒ bloquant ») n'est pas respectée : il reste 20 MAJ. Il faut aussi noter que l'audit 03 reste sous 60, à cause des textes français assumés des cartes MCP et de la dette `chunk_service`. Cette dette est documentée ci-dessus avec sa cible (0.8.0), ce qui répond à la clause GO CONDITIONNEL du master (« autorisée si 0 CRITICAL + plan de remédiation pour les MAJOR »). C'est le même traitement qu'en 0.7.0.

**Prochaines étapes** (`docs/maintainers.md`) :
1. Merger la branche de suivi dans `release/0.7.3`.
2. Le gate repasse sur #366.
3. **Rebase and merge** vers `main`.
4. Tag `v0.7.3`, puis images via `release.yml`.
5. GitHub Release à partir de la section `[0.7.3]` du CHANGELOG.
6. Déploiement et smoke test.

**À faire hors tag** :
- déplacer #348, #349 et #358 vers le milestone 0.8.0 ;
- créer l'issue « montée docling → Pillow 13 » avant l'expiration des suppressions au 2026-12-31.
