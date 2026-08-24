# Synthèse d'audit — Release 0.7.0

**Date** : 2026-08-24
**Branche** : `release/0.7.0` au commit `6aaf98f`
**Auditeur** : claude-code
**Périmètre** : 12 audits du quality-gate (`docs/audit/master.md`)

---

## Tableau de bord

| #  | Audit                  | Score | CRIT | MAJ | MIN | INFO | Verdict          |
|----|------------------------|-------|------|-----|-----|------|------------------|
| 01 | Hexagonal Architecture | 78    | 0    | 3   | 1   | 2    | GO CONDITIONNEL  |
| 02 | DDD                    | 100   | 0    | 0   | 0   | 3    | GO               |
| 03 | Clean Code             | 61    | 0    | 2   | 3   | 4    | GO CONDITIONNEL  |
| 04 | KISS                   | 83    | 0    | 1   | 0   | 3    | GO               |
| 05 | DRY                    | 67    | 0    | 3   | 2   | 2    | GO CONDITIONNEL  |
| 06 | SOLID                  | 100   | 0    | 0   | 0   | 4    | GO               |
| 07 | Decoupling             | 80    | 1    | 2   | 0   | 2    | **NO-GO**        |
| 08 | Security               | 97    | 0    | 1   | 1   | 3    | GO               |
| 09 | Tests                  | 93    | 0    | 1   | 3   | 3    | GO               |
| 10 | CI / Build             | 85    | 0    | 0   | 3   | 3    | GO               |
| 11 | Documentation          | 72    | 1    | 1   | 0   | 2    | **NO-GO**        |
| 12 | Performance            | 76    | 0    | 1   | 3   | 4    | GO CONDITIONNEL  |

**Score global** : **83 / 100** (moyenne des 12 audits)
**Écarts CRITICAL totaux** : **2**
**Écarts MAJOR totaux** : **15**
**Écarts MINOR totaux** : 16
**Écarts INFO totaux** : 35

---

## Écarts CRITICAL (tous audits confondus)

1. **[07 Decoupling]** Imports croisés systémiques bidirectionnels entre features frontend (`document`↔`analysis`, `document`↔`chunks`, `reasoning`→`document`, …) — `frontend/src/features/reasoning/store.ts:3` (+ ~19 autres sites). Dette d'architecture réelle : les features ne sont pas isolées, aucune couche `shared/` ne porte les contrats communs.
2. **[11 Documentation]** Section `[Unreleased]` du changelog non figée en `[0.7.0] - 2026-08-24` — `CHANGELOG.md:7`. Le changelog n'est pas gelé pour la release (étape de release-prep manquante, trivial à corriger).

> **Règle absolue** : tout `[CRIT]` non résolu ⇒ **NO-GO**. De plus, **15 écarts MAJOR** dépassent largement le seuil (> 3 MAJ non résolus ⇒ bloquant).

---

## Top blockers (à traiter avant tag)

### Bloquant #1 — release-prep triviale (rapide, purement mécanique)
- `CHANGELOG.md:7` — figer `[Unreleased]` → `[0.7.0] - 2026-08-24` **(CRIT, audit 11)**
- `frontend/package.json:3` — bump `0.6.2` → `0.7.0` **(MAJ, audit 11)**

### Bloquant #2 — découplage frontend (dette réelle)
- `frontend/src/features/reasoning/store.ts:3` (+~19) — imports croisés inter-features **(CRIT, audit 07)**. Effort non trivial ; à arbitrer : corriger maintenant vs. accepter comme dette documentée pour 0.7.x.

### Bloquant #3 — sécurité (self-hosted)
- SSRF sur la probe `test-connection` : `validate_host_url` ne bloque pas loopback / RFC1918 / cibles internes — `document-parser/domain/app_config.py:83`, `services/app_config_service.py:146`, `infra/llm/ollama_probe.py:29` **(MAJ, audit 08)**. À corriger avant expo publique ; sur HF les writes config sont déjà refusés (403).

### Autres MAJOR (15 au total)
| Audit | Écart | Localisation |
|-------|-------|--------------|
| 01 | Règles split/merge de chunks réimplémentées dans le service (`domain/chunk_editing.py` mort et divergent) | `services/chunk_service.py:335` |
| 01 | Services importent directement des libs infra PDF (`pypdfium2`, `pdf2image`) hors port/injection | `services/document_service.py:13` |
| 01 | `GET /api/documents/{id}` orchestre 2 dépôts + jointure dans la couche HTTP | `api/documents.py:41` |
| 03 | Fonctions d'orchestration multi-responsabilités (`push_to_store`, `write_document`, `fetch_graph`) | `services/chunk_service.py:574` |
| 03 | Fichier fourre-tout `chunk_service.py` (édition chunks + push store + projection d'arbre) | `services/chunk_service.py:146` |
| 04 | Généricité prématurée de l'abstraction LLM-provider (enum 1 membre + port + knob pour un seul backend) | `domain/value_objects.py:167`, `infra/settings.py:49` |
| 05 | `ELEMENT_COLORS` redéfinie dans 4 fichiers au lieu d'importer `elementColors.ts` | `BboxOverlay.vue:42`, `StructureViewer.vue:68`, `ResultTabs.vue:199` |
| 05 | Helper `_parse_iso`/`_parse_dt` copié dans 6-7 repos (divergence coercition UTC dans `analysis_repo`) | `persistence/document_repo.py:11` (+6) |
| 05 | Couleurs UI en dur (`#dc2626`×11, `#6b7280`×12, `#d1d5db`×7) éparpillées au lieu de tokens | `store/ui/StoreForm.vue:389` (+…) |
| 07 | Type partagé `RechunkOptions` logé dans la feature `document` au lieu de `shared/types.ts` | `features/document/api.ts:40` |
| 07 | `dict` non typé dans un schéma de réponse (`StoreResponse.config`) + `GraphNode extra=allow` | `api/schemas.py:310` |
| 08 | SSRF probe test-connection (voir Bloquant #3) | `domain/app_config.py:83` |
| 09 | Cas d'erreur 413 (payload trop volumineux) non testé (upload + graph) | `api/documents.py:80` |
| 11 | `frontend/package.json` reste en 0.6.2 (voir Bloquant #1) | `frontend/package.json:3` |
| 12 | Requêtes N+1 dans `StoreService` (`list_stores`, `list_documents`) — 1 requête SQLite + connexion neuve par itération | `services/store_service.py:164` |

---

## Quick wins (faciles, forte valeur)

- Figer le changelog + bump version (Bloquant #1) — débloque 1 CRIT + 1 MAJ en quelques minutes.
- `ELEMENT_COLORS` : importer la source unique `elementColors.ts` (supprime la duplication x4).
- Couleurs UI en dur → tokens de design centralisés (`--color-*`).
- Factoriser `_parse_iso`/`_parse_dt` dans un util partagé (corrige aussi la divergence UTC de `analysis_repo`).
- Ajouter le test du 413 (upload + graph) — 1 test manquant sur un chemin d'erreur connu.

---

## Points forts

- **DDD (100)** et **SOLID (100)** : backend domaine propre — bounded contexts nets, ports/adapters respectés côté services reasoning, aucune violation.
- **Security (97)** : un seul MAJ (SSRF probe), le reste conforme (secrets, CORS, injection, writes config refusés 403 sur HF).
- **Tests (93)** : couverture solide des chemins critiques reasoning trace / config runtime / parse-chunk ; un seul trou (413).
- **CI / Build (85)** : pipeline sain (uv, docling-serve remote, bake HF opt-in), seulement des MIN.

---

## Verdict final : **NO-GO**

La 0.7.0 **ne peut pas être taguée en l'état** : 2 écarts CRITICAL + 15 écarts MAJOR (> seuil de 3).

### Conditions pour repasser en GO
1. **Obligatoire (release-prep)** : figer `CHANGELOG.md` en `[0.7.0] - 2026-08-24` **et** bumper `frontend/package.json` en 0.7.0. → lève le CRIT-11 et le MAJ-11.
2. **Obligatoire (sécurité)** : corriger la SSRF de la probe `test-connection` (bloquer loopback / RFC1918 dans `validate_host_url`). → lève le MAJ-08.
3. **Arbitrage requis** : le CRIT-07 (imports croisés frontend) — soit remédiation (introduire `shared/` + inverser les dépendances), soit reclassement en dette documentée assumée pour 0.7.x avec ticket de suivi. Tant qu'il reste `[CRIT]`, le verdict reste NO-GO.
   - **Adressé (Option B, barrel boundary)** sur `fix/release-0.7.0-audit-blockers` : briques partagées extraites vers `shared/`, tous les accès inter-features passent par les barrels publics `@/features/<name>`, invariant imposé par la règle ESLint `no-restricted-imports` (pas d'inversion de stores). → à re-auditer pour lever le CRIT-07.
4. **Recommandé avant tag** : ramener les MAJOR sous le seuil de 3 (au moins les quick wins DRY + le N+1 StoreService).

Après corrections : re-auditer **07, 08, 11** (et 01/03/05/12 pour le score) avant de merger dans `main` et taguer `v0.7.0`.
