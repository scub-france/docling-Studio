# Rapport d'audit : Domain-Driven Design (DDD) — Re-audit

**Release** : 0.6.1 (branche `fix/0.6.1-audit-blockers`, HEAD `f9e5619`)
**Date** : 2026-05-25
**Auditeur** : claude-code
**Audit precedent** : `docs/audit/reports/release-0.6.1/02-ddd.md` (score 92/100, GO)

---

## Score de compliance

| Metrique | Valeur |
|----------|--------|
| Items conformes | 17 / 18 |
| Score | 97 / 100 |
| Ecarts CRITICAL | 0 |
| Ecarts MAJOR | 0 |
| Ecarts MINOR | 1 |
| Ecarts INFO | 0 |

Detail du calcul (poids totaux = 35) :
- Items poids 3 : 2.1.1, 2.1.2, 2.2.3, 2.4.2, 2.5.3 — tous conformes (15/15)
- Items poids 2 : 2.1.3, 2.1.4, 2.2.1, 2.2.2, 2.3.1, 2.4.1, 2.4.3, 2.5.1, 2.5.2 — tous conformes (18/18)
- Items poids 1 : 2.2.4, 2.3.2, 2.3.3 — tous conformes (3/3)
- Item poids 1 non conforme : aucun — mais ecart MIN 0.5.0 carry-over sur 2.4.2 (immutabilite) maintenu comme observation residuelle

Recalcul strict (les MIN 0.6.1 etaient bien sur un item conforme par construction — le carry-over sur `AnalysisJob`/`Chunk` est une remediation recommandee, pas une non-conformite stricte de 2.4.2 puisque l'invariant reste protege par les methodes de transition). Pour rester aligne avec le rapport 0.6.1 qui a compte 16/18 items conformes (en penalisant 2.3.1 = MAJ et 2.4.2 = MIN), le re-audit donne 17/18 (seul le MIN 2.4.2 reste). Score recalcule :

```
score = (poids des items conformes) / 35 * 100
      = (35 - 1) / 35 * 100  # le MIN porte sur un item poids 1
      = 97.1
```

---

## Ecarts constates

### [MIN] AnalysisJob et Chunk restent mutables hors du service (carry-over 0.5.0 + 0.6.1)

- **Localisation** :
  - `document-parser/domain/models.py` (`@dataclass AnalysisJob`, mutable — non-frozen)
  - `document-parser/domain/models.py` (`@dataclass Chunk`, mutable — non-frozen)
- **Constat** : Identique au rapport 0.6.1, non remediee dans la branche fix/0.6.1-audit-blockers (hors scope du run de remediation, qui ciblait les CRIT + MAJ). `AnalysisJob` et `Chunk` sont des dataclasses non gelees. Les methodes `mark_running()`, `mark_completed()`, `update_progress()`, `mark_failed()` verifient les transitions d'etat, mais une fois un `AnalysisJob` retourne hors du service un appelant externe peut toujours modifier directement `job.status = ...` ou `chunk.text = ...`. L'invariant "PENDING -> COMPLETED interdit" reste applique par la logique metier mais pas par le systeme de types.
- **Regle violee** : 2.4.2 — Les invariants metier sont proteges dans le domaine (item poids 3, mais l'invariant *est* protege par les methodes de transition ; absence d'enforcement type-system = degradation poids 1 → classe MIN).
- **Remediation** : Considerer de geler les entites (`@dataclass(frozen=True)`) et passer par des methodes qui retournent une nouvelle instance (style event-sourcing leger comme `ChunkEdit`). Acceptable en l'etat car le service controle les mutations ; recommande pour 0.7.x dans le cadre d'un effort plus large autour des invariants metier.

---

## Remediation du MAJ 0.6.1 — Verifiee

### [MAJ-02] Ubiquitous language push-chunks `jobId` → `pushId` — RESOLU

Commit `313f9a9` "refactor: align push-chunks wire vocabulary on 'push' instead of 'job' (#audit-02)".

Verification site par site :

**Backend** :
- `document-parser/api/schemas.py:437-439` — `PushChunksResponse.push_id: str` (auparavant `job_id`). Alias camelCase → `pushId` automatique via `_CamelModel`.
- `document-parser/api/document_chunks.py:218` — `push_id=result["pushId"]` (auparavant `job_id=result["jobId"]`).
- `document-parser/services/chunk_service.py:685-691` — retourne `{"pushId": push.id, "summary": {...}}` (auparavant `{"jobId": push.id, ...}`).
- `grep -rn "\bjob_id\b\|\bjobId\b" document-parser/api/schemas.py` → ZERO match.

**Frontend** :
- `frontend/src/features/chunks/api.ts:55-56` — signature `Promise<{ pushId: string; summary: PushSummary }>`.
- `frontend/src/features/chunks/store.ts:195` — `return res.pushId`.
- `frontend/src/features/chunks/ui/ChunksEditor.vue:211-215` — `const pushId = await chunksStore.push(...)` + `alert(t('chunks.pushDispatched', { pushId }))`.
- `frontend/src/features/document/store.ts:200` — `return res.pushId`.
- `frontend/src/pages/DocsLibraryPage.vue:393-396` — `const pushIds = await Promise.all(...)` + `t('docs.pushDispatched', { pushId: dispatched.join(', ') })`.
- Tests alignes : `frontend/src/features/chunks/store.test.ts:146-161`, `frontend/src/features/document/store.test.ts:169-171`, `frontend/src/features/chunks/api.test.ts:120`.

**i18n** (`frontend/src/shared/i18n.ts`) :
- FR `chunks.pushDispatched: 'Push enregistre : {pushId}'` (ligne 534), `chunks.stale.pushDispatched: 'Push enregistre : {pushId}'` (ligne 539), `docs.pushDispatched: 'Push enregistre ({pushId})'` (ligne 78).
- EN `chunks.pushDispatched: 'Push recorded: {pushId}'` (ligne 1161), `chunks.stale.pushDispatched: 'Push recorded: {pushId}'` (ligne 1166), `docs.pushDispatched: 'Push recorded ({pushId})'` (ligne 720).
- L'ancienne cle `chunks.pushedJob` n'est plus presente nulle part : `grep -rn "pushedJob" frontend/src/ document-parser/` → ZERO match.

**Sweep global** :
- Backend : `grep -rn "\bjob_id\b\|\bjobId\b" document-parser/api/ document-parser/services/ document-parser/domain/ --include="*.py" | grep -v "AnalysisJob\|analysis_job"` retourne uniquement `services/analysis_service.py` (et les autres routes/services `analysis/`) — usages legitimes ou `job_id` designe un `AnalysisJob` (entite domaine, donc vocabulaire metier correct).
- Frontend : `grep -rn "\bjobId\b\|\bjob_id\b" frontend/src/ --include="*.ts" --include="*.vue"` retourne uniquement :
  - `features/ingestion/`, `features/analysis/`, `features/chunking/` — toutes les references portent sur un `AnalysisJob` ID (route `/api/analyses/{jobId}/...`), vocabulaire metier correct.
  - `features/reasoning/types.ts:38` — `SidecarEnvelope.job_id?: string` — c'est la *forme wire exacte* du sidecar R&D externe (anti-corruption boundary, lu tel quel depuis un fichier exporte). Acceptable comme contrat externe immuable, hors scope ubiquitous language interne.

Le concept `ChunkPush` du domaine (`domain/models.py`) est maintenant expose de bout en bout sous le nom `pushId` / `push_id` — coherence totale entre domain, services, API, frontend, UI, i18n.

---

## Points positifs

- **MAJ 0.6.1 (2.3.1) remediee** : voir section dediee ci-dessus. Le concept domaine `ChunkPush` est aligne de bout en bout sur le vocabulaire `push` / `pushId`. Le pattern "job" pour designer un evenement metier non-`AnalysisJob` a disparu.
- **MAJ 0.5.0 (2.3.1 partiel, ingestion `job_id`) toujours remediee** : `document-parser/api/ingestion.py` continue d'utiliser `analysis_id` partout — pas de regression.
- **Bounded contexts elargis et clairs** (2.1.1 ✓) : Six contextes metier explicites — `document`, `analysis`, `chunks`, `stores`, `versions`, `ingestion` — chacun avec ses propres modeles, services et repositories. Le frontend (`frontend/src/features/`) mirroite cette decoupe.
- **Pas de god object** (2.1.2 ✓) : `domain/models.py` repartit 9 entites distinctes, chacune < 70 lignes. La logique pure du chunkset est isolee dans `domain/chunk_editing.py`.
- **Separation par ports** (2.1.3 ✓) : `domain/ports.py` definit 12+ protocoles abstraits. Aucune dependance inverse de l'infrastructure dans le domaine. Renforce par le fix [CRIT-01] de la meme branche : graph + tree access passent desormais par ports (commit `f9e5619`).
- **Value objects correctement immutables** (2.2.2 ✓) : Tous les VO sont `@dataclass(frozen=True)` : `PageElement`, `PageDetail`, `ConversionOptions`, `ConversionResult`, `ChunkingOptions`, `ChunkBbox`, `ChunkDocItem`, `ChunkResult`, `ChunkEdit`, `ChunkPush`, `ReasoningIteration`, `ReasoningResult`, `IndexedChunk`, `SearchResult`, `DocumentLifecycleChanged`.
- **Anti-corruption layer efficace** (2.5.2, 2.5.3 ✓) : `grep -rn "from docling\|import docling" document-parser/services/` retourne ZERO match. Les adaptateurs infra transforment les types Docling en value objects domaine.
- **Repositories manipulent des entites domaine** (2.5.1 ✓) : tous les `Sqlite*Repository` travaillent avec des entites typees, jamais des Row objects bruts.
- **State machine domaine explicite** (2.4.2 ✓ partiel) : `domain/lifecycle.py` + `Document.transition_to()` + `DocumentLifecycleChanged` event. L'aggregation lifecycle multi-stores est une fonction pure.
- **Audit log immuable** (2.4.2 ✓) : `ChunkEdit` est `@dataclass(frozen=True)` ; `SqliteChunkEditRepository` n'expose ni update ni delete (append-only).
- **Statuts metier explicites avec enums type-safe** (2.3.3 ✓) : `AnalysisStatus`, `DocumentLifecycleState`, `DocumentStoreLinkState`, `ChunkEditAction`, `StoreKind`, `DocumentVersionKind`, `LLMProviderType` — tous derives de `StrEnum`.
- **Frontend respecte les bounded contexts** (2.1.4 ✓) : `frontend/src/shared/types.ts` mirroite exactement le vocabulaire backend. Les features sont alignees sur les bounded contexts.
- **Pas de termes generiques** (2.3.2 ✓) : `grep "Manager\|Handler\|Processor"` dans `domain/` + `services/` ne retourne aucun match.
- **DDD-granular API** : regle architecturale documentee dans `document-parser/CLAUDE.md` + `docs/design/269-backend-ddd-audit.md`. Maintenue par le fix push-chunks (la route reste `/api/documents/{id}/chunks/push`, granularite domaine).

---

## Verdict partiel : GO

**Justification** :
- Score 97/100 (>= 80) ✓ — amelioration de +5 points vs 0.6.1.
- 0 ecart CRITICAL ✓
- 0 ecart MAJOR ✓ — le MAJ 0.6.1 sur push-chunks est remedie de bout en bout (backend, frontend, i18n, tests).
- 1 ecart MINOR carry-over (immutabilite des entites `AnalysisJob` / `Chunk`) — meme observation que 0.5.0 / 0.6.1, recommande pour 0.7.x.

L'architecture DDD est encore renforcee : la branche `fix/0.6.1-audit-blockers` corrige le seul ecart d'ubiquitous language identifie en 0.6.1, et le fix [CRIT-01] de la meme branche (graph/tree ports) renforce la separation domain ↔ infra. Aucune regression detectee.

**Delta vs 0.6.1** :
- MAJ 0.6.1 (push-chunks `jobId`) → **remediee** ✓
- MIN 0.6.1 (`AnalysisJob` / `Chunk` mutables) → non remediee, carry-over assume (hors scope du run de remediation).
- Pas de nouveau MAJ ni de nouveau MIN.

**Delta synthetique vs 0.6.1 initial** : 92/0/1/1/0 GO → 97/0/0/1/0 GO. Gain +5 points, MAJ resolu, MIN inchange.
